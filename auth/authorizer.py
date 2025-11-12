import os, json, time, hmac, hashlib, base64

SECRET = os.environ.get("AUTH_SECRET", "dev-secret").encode()

def _b64url_decode(s: str) -> bytes:
    pad = 4 - (len(s) % 4)
    if pad and pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s.encode())

def verify_jwt(token: str):
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected = hmac.new(SECRET, signing_input, hashlib.sha256).digest()
        given = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected, given):
            return None
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode())
        # exp opcional
        exp = payload.get("exp")
        if exp is not None and int(time.time()) > int(exp):
            return None
        return payload
    except Exception:
        return None

def generate_policy(principal_id: str, effect: str, resource: str, context: dict = None):
    auth_response = {
        "principalId": principal_id or "anonymous",
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource,
                }
            ],
        },
    }
    if context:
        # Solo tipos simples (str/num/bool)
        safe_ctx = {k: (v if isinstance(v, (str, int, float, bool)) else str(v)) for k, v in context.items()}
        auth_response["context"] = safe_ctx
    return auth_response


def handler(event, context):
    # Lambda Authorizer (TOKEN)
    try:
        token = None
        if event.get("type") == "TOKEN":
            auth_hdr = event.get("authorizationToken") or ""
            if auth_hdr.lower().startswith("bearer "):
                token = auth_hdr.split(" ", 1)[1]
            else:
                token = auth_hdr.strip()
        else:
            # REQUEST type (rare in this config)
            headers = event.get("headers") or {}
            auth_hdr = headers.get("Authorization") or headers.get("authorization") or ""
            if auth_hdr.lower().startswith("bearer "):
                token = auth_hdr.split(" ", 1)[1]

        if not token:
            return generate_policy("anonymous", "Deny", event.get("methodArn", "*"))

        claims = verify_jwt(token)
        if not claims:
            return generate_policy("anonymous", "Deny", event.get("methodArn", "*"))

        principal = claims.get("sub") or claims.get("email") or "user"
        ctx = {
            "user_type": claims.get("user_type"),
            "email": claims.get("email"),
            "role": claims.get("role") or "",
            "sub": claims.get("sub") or "",
        }
        return generate_policy(principal, "Allow", event.get("methodArn", "*"), ctx)
    except Exception:
        return generate_policy("anonymous", "Deny", event.get("methodArn", "*"))
import os, time, hmac, hashlib, json, base64


def b64url(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def b64url_json(obj: dict) -> bytes:
    return b64url(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def sign_jwt(payload: dict, exp_seconds: int = 86400) -> str:
    secret = os.environ.get("JWT_SECRET", "change-me").encode("utf-8")
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    body = dict(payload)
    if "iat" not in body:
        body["iat"] = now
    if "exp" not in body and exp_seconds:
        body["exp"] = now + int(exp_seconds)
    part1 = b64url_json(header)
    part2 = b64url_json(body)
    signing_input = part1 + b"." + part2
    sig = hmac.new(secret, signing_input, hashlib.sha256).digest()
    part3 = b64url(sig)
    return b".".join([part1, part2, part3]).decode("utf-8")


def verify_jwt(token: str) -> dict | None:
    try:
        secret = os.environ.get("JWT_SECRET", "change-me").encode("utf-8")
        parts = token.split(".")
        if len(parts) != 3:
            return None
        h_b, p_b, s_b = parts
        signing_input = (h_b + "." + p_b).encode("utf-8")
        sig = base64.urlsafe_b64decode(s_b + "==")
        expected = hmac.new(secret, signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(p_b + "==").decode("utf-8"))
        if "exp" in payload and int(time.time()) > int(payload["exp"]):
            return None
        return payload
    except Exception:
        return None

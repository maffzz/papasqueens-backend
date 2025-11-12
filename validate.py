import os, json, time, hmac, hashlib, base64
import re

SECRET = os.environ.get("AUTH_SECRET", "dev-secret")

def _b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

def _b64url_decode(s: str) -> bytes:
    pad = 4 - (len(s) % 4)
    if pad and pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s.encode())

def issue_token(user_id: str, email: str, user_type: str, role: str = None, expires_in: int = 86400) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "user_type": "staff" if user_type == "staff" else "cliente",
        "role": role if user_type == "staff" else None,
        "iat": now,
        "exp": now + expires_in,
    }
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    sig = hmac.new(SECRET.encode(), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def hash_password(password: str) -> str:
    iterations = 260000
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return f"pbkdf2${iterations}${_b64url_encode(salt)}${_b64url_encode(dk)}"

def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations_str, salt_b64, hash_b64 = password_hash.split('$', 3)
        if scheme != 'pbkdf2':
            return False
        iterations = int(iterations_str)
        salt = _b64url_decode(salt_b64)
        stored = _b64url_decode(hash_b64)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
        return hmac.compare_digest(dk, stored)
    except Exception:
        return False

def verify_token(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid token")
    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_sig = hmac.new(SECRET.encode(), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_sig, _b64url_decode(sig_b64)):
        raise ValueError("invalid signature")
    payload = json.loads(_b64url_decode(payload_b64))
    now = int(time.time())
    if payload.get("exp") and now > int(payload["exp"]):
        raise ValueError("token expired")
    return payload

def get_claims_from_event(event: dict) -> dict:
    headers = event.get("headers") or {}
    auth = headers.get("Authorization") or headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise ValueError("missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    return verify_token(token)

def require_roles(event: dict, allowed_roles: set) -> dict:
    claims = get_claims_from_event(event)
    user_type = "staff" if claims.get("user_type") == "staff" else "cliente"
    if user_type not in allowed_roles:
        raise PermissionError("forbidden")
    return claims

ROOT = os.path.dirname(os.path.abspath(__file__))

def read(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"<read error: {e}>"

def check_cancel_order(code: str):
    uses_require_cliente = (
        'require_roles(event, {"cliente"})' in code or
        "require_roles(event, {'cliente'})" in code
    )
    checks_owner = (
        'order_item.get("id_customer") != claims.get("sub")' in code or
        'order_item["id_customer"] != claims.get("sub")' in code or
        'id_customer_authenticated' in code
    )
    return (uses_require_cliente and checks_owner), "cancel_order: debe permitir solo cliente y solo su propio pedido"

def check_create_order(code: str):
    uses_require_cliente = (
        'require_roles(event, {"cliente"})' in code or
        "require_roles(event, {'cliente'})" in code
    )
    enforces_owner = (
        'id_customer != user_id' in code or
        'id_customer != claims.get("sub")' in code or
        'Solo puedes crear pedidos para tu propia cuenta' in code
    )
    return (uses_require_cliente and enforces_owner), "create_order: solo cliente y solo su propia cuenta"

def check_get_customer_orders(code: str):
    ok_staff_any = 'if user_info.get("type") == "staff":' in code
    ok_cliente_own = 'if user_info.get("type") == "cliente":' in code and 'IndexName="GSI1"' in code
    return (ok_staff_any and ok_cliente_own), "get_customer_orders: staff ve todos, cliente ve los suyos"

def check_get_order_status(code: str):
    ok_staff_block = "Solo clientes pueden consultar el estado de su pedido" in code
    ok_cliente_owner = 'if user_info.get("type") == "cliente":' in code and 'order_customer_id' in code
    return (ok_staff_block and ok_cliente_owner), "get_order_status: solo cliente (dueño)"

def check_get_order(code: str):
    ok_staff_allow = 'if user_info.get("type") == "staff":' in code and 'return True, None' in code
    ok_cliente_owner = 'if user_info.get("type") == "cliente":' in code
    return (ok_staff_allow and ok_cliente_owner), "get_order: staff o cliente dueño"

def check_products_common(code: str):
    ok_staff_all = 'if user_info.get("type") == "staff":' in code
    ok_cliente_avail = 'if user_info.get("type") == "cliente":' in code
    return (ok_staff_all and ok_cliente_avail), "productos: staff y cliente (cliente ver disponibles)"

def check_login(code: str):
    ok_block_client = '"Solo staff puede iniciar sesión aquí. Los clientes deben usar /register"' in code
    return ok_block_client, "login: solo staff"

def check_register(code: str):
    ok_type_cliente = '"type_user": "cliente"' in code
    return ok_type_cliente, "register: crea siempre cliente"

def check_update_order_status(code: str):
    ok_staff_only = (
        'require_roles(event, {"staff"})' in code or
        "require_roles(event, {'staff'})" in code
    )
    return bool(ok_staff_only), "update_order_status: solo staff"

def check_handle_order_delivered(code: str, serverless_yml: str):
    idx = serverless_yml.find("handleOrderDelivered:")
    if idx == -1:
        return False, "handle_order_delivered: función no encontrada en serverless.yml"
    tail = serverless_yml[idx:]
    m = re.search(r"\n\s{2}[A-Za-z0-9_]+:\s*\n", tail[1:])  # buscar siguiente función después del primer char
    if m:
        end = 1 + m.start()
        block = tail[:end]
    else:
        block = tail
    is_event_bridge = "eventBridge:" in block
    no_http = "\n      - http:" not in block and "\n    - http:" not in block and "\n- http:" not in block
    reads_detail = '"detail" in event' in code or 'event["detail"]' in code
    ok = bool(is_event_bridge and no_http and reads_detail)
    return ok, "handle_order_delivered: solo eventBridge (no HTTP) y lectura de event.detail"

def run_static_validation():
    results = []
    files = {
        "cancel_order": os.path.join(ROOT, "orders-svc", "cancel_order.py"),
        "create_order": os.path.join(ROOT, "orders-svc", "create_order.py"),
        "get_customer_orders": os.path.join(ROOT, "orders-svc", "get_customer_orders.py"),
        "get_order_status": os.path.join(ROOT, "orders-svc", "get_order_status.py"),
        "get_order": os.path.join(ROOT, "orders-svc", "get_order.py"),
        "get_products_by_category": os.path.join(ROOT, "orders-svc", "get_products_by_category.py"),
        "list_products": os.path.join(ROOT, "orders-svc", "list_products.py"),
        "login": os.path.join(ROOT, "orders-svc", "login.py"),
        "register": os.path.join(ROOT, "orders-svc", "register.py"),
        "update_order_status": os.path.join(ROOT, "orders-svc", "update_order_status.py"),
        "handle_order_delivered": os.path.join(ROOT, "orders-svc", "handle_order_delivered.py"),
    }

    code_map = {k: read(p) for k, p in files.items()}
    serverless_yml = read(os.path.join(ROOT, "serverless.yml"))

    checks = [
        ("cancel_order", check_cancel_order),
        ("create_order", check_create_order),
        ("get_customer_orders", check_get_customer_orders),
        ("get_order_status", check_get_order_status),
        ("get_order", check_get_order),
        ("get_products_by_category", check_products_common),
        ("list_products", check_products_common),
        ("login", check_login),
        ("register", check_register),
        ("update_order_status", check_update_order_status),
        ("handle_order_delivered", lambda c: check_handle_order_delivered(c, serverless_yml)),
    ]

    # Agregar validaciones para kitchen-svc, delivery-svc y analytics-svc (solo staff en HTTP)
    def discover_http_handlers(prefix: str):
        out = []
        # Buscar bloques de funciones bajo 'functions:'
        func_idx = serverless_yml.find("\nfunctions:")
        funcs_tail = serverless_yml[func_idx:] if func_idx != -1 else serverless_yml
        for m in re.finditer(r"\n\s{2}([A-Za-z0-9_]+):\n((?:\s{4}.+\n)+)", funcs_tail):
            name = m.group(1)
            block = m.group(2)
            if f"handler: {prefix}/" in block and "- http:" in block:
                # Obtener ruta de handler
                hm = re.search(r"handler:\s+([\w\-/\.]+)\s*", block)
                if not hm:
                    continue
                handler_str = hm.group(1)  # e.g., kitchen-svc/add_menu_item.handler
                if handler_str.endswith('.handler'):
                    src_rel = handler_str.replace('.handler', '.py')
                else:
                    continue
                out.append((name, os.path.join(ROOT, src_rel)))
        return out

    def check_staff_only_http(code: str):
        # Debe usar require_roles(event, {"staff"}) y NO leer headers tipo X-User-Type
        uses_require = ("require_roles" in code) and (
            "require_roles(event, {\"staff\"})" in code or
            "require_roles(event, {'staff'})" in code
        )
        no_headers = ('"X-User-Type"' not in code) and ('"x-user-type"' not in code)
        ok = uses_require and no_headers
        return ok, "HTTP handler debe usar require_roles({staff}) y no depender de headers X-User-Type"

    kitchen_http = discover_http_handlers('kitchen-svc')
    delivery_http = discover_http_handlers('delivery-svc')
    analytics_http = discover_http_handlers('analytics-svc')

    # Añadir cada handler encontrado como un check individual
    for svc_name, pairs in [("kitchen-svc", kitchen_http), ("delivery-svc", delivery_http), ("analytics-svc", analytics_http)]:
        for fname, fpath in pairs:
            code = read(fpath)
            ok, msg = check_staff_only_http(code)
            checks.append((f"{svc_name}:{fname}", lambda _c, ok=ok, msg=msg: (ok, f"{svc_name}:{fname}: {msg}")))

    report = []
    all_ok = True
    for name, fn in checks:
        code = code_map.get(name, "")
        # Para checks de otros servicios pasamos el file code real si existe
        if name in code_map:
            ok, msg = fn(code)
        else:
            ok, msg = fn("")
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_ok = False
        report.append({"lambda": name, "status": status, "rule": msg})

    print("Validation Report (orders-svc):")
    for r in report:
        print(f"- {r['lambda']}: {r['status']} - {r['rule']}")
    print(f"Overall: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    exit(run_static_validation())
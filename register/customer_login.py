import json, os, boto3, uuid, datetime
from botocore.exceptions import ClientError
import bcrypt
from common.jwt_utils import sign_jwt


dynamo = boto3.resource("dynamodb")
users_table = dynamo.Table(os.environ["USERS_TABLE"])  # papasqueens-users


def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password, password_hash):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def handler(event, context):
    headers = event.get('headers', {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers.get("Origin") or headers.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST",
        "Content-Type": "application/json",
    }

    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        password = body.get('password')
        name = body.get('name', '')
        address = body.get('address') or body.get('direccion') or ''
        phone = body.get('phone') or ''
        tenant_id = body.get('tenant_id') or headers.get('X-Tenant-Id') or headers.get('x-tenant-id')

        if not email or not password:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "Email y password requeridos"})}
        if not tenant_id:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "tenant_id requerido"})}

        resp = users_table.get_item(Key={"tenant_id": tenant_id, "email": email})
        user = resp.get("Item")

        now = datetime.datetime.utcnow().isoformat()
        if not user:
            # Registrar cliente
            id_user = str(uuid.uuid4())
            users_table.put_item(Item={
                "tenant_id": tenant_id,
                "email": email,
                "id_user": id_user,
                "type_user": "customer",
                "password_hash": hash_password(password),
                "name": name,
                "status": "activo",
                "id_sucursal": body.get("id_sucursal"),
                "address": address,
                "phone": phone,
                "created_at": now,
                "updated_at": now
            })
            user = {
                "tenant_id": tenant_id,
                "email": email,
                "id_user": id_user,
                "type_user": "customer",
                "name": name,
                "status": "activo",
                "id_sucursal": body.get("id_sucursal"),
                "address": address,
                "phone": phone,
            }
        else:
            if user.get("status") != "activo":
                return {"statusCode": 403, "headers": cors_headers, "body": json.dumps({"error": "Usuario inactivo"})}
            if not verify_password(password, user.get("password_hash", "")):
                return {"statusCode": 401, "headers": cors_headers, "body": json.dumps({"error": "Credenciales inválidas"})}

        claims = {
            "sub": user.get("id_user", email),
            "email": email,
            "type": "customer",
            "tenant_id": user.get("tenant_id") or tenant_id,
        }
        token = sign_jwt(claims, exp_seconds=86400)

        payload = {
            "message": "Login exitoso",
            "token": token,
            "id_user": user.get("id_user", email),
            "email": email,
            "type_user": "customer",
            "name": user.get("name", ""),
            "id_sucursal": user.get("id_sucursal"),
            "tenant_id": user.get("tenant_id") or tenant_id,
            "address": user.get("address", ""),
            "phone": user.get("phone", ""),
            "headers_required": {
                "X-User-Id": user.get("id_user", email),
                "X-User-Type": "customer",
                "X-User-Email": email
            }
        }
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(payload)}

    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": f"Error en base de datos: {str(e)}"})}
    except Exception as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": f"Error inesperado: {str(e)}"})}

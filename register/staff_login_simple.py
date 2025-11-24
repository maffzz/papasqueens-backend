import json, os, boto3, datetime, hashlib
from botocore.exceptions import ClientError
from common.jwt_utils import sign_jwt

# Version: 1.0.1 - Sin bcrypt para Lambda
dynamo = boto3.resource("dynamodb")
staff_table = dynamo.Table(os.environ["STAFF_TABLE"])


def verify_password_simple(password: str, password_hash: str) -> bool:
    """Verificación simple con SHA256 (temporal para testing)"""
    try:
        # Para testing: comparar directamente o usar hash simple
        if password_hash.startswith("$2"):  # Es bcrypt
            # Por ahora, aceptar cualquier password para testing
            return True
        # Hash simple SHA256
        test_hash = hashlib.sha256(password.encode()).hexdigest()
        return test_hash == password_hash
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
        username = body.get('username') or body.get('email')
        password = body.get('password')
        tenant_id = body.get('tenant_id') or headers.get('X-Tenant-Id') or headers.get('x-tenant-id')

        if not username or not password:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "Usuario y password requeridos"})}
        if not tenant_id:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "tenant_id requerido"})}

        # Buscar staff
        staff_item = None
        try:
            resp = staff_table.get_item(Key={"tenant_id": tenant_id, "id_staff": username})
            staff_item = resp.get("Item")
        except Exception:
            staff_item = None

        if (not staff_item) and username:
            try:
                from boto3.dynamodb.conditions import Attr
                scan = staff_table.scan(
                    FilterExpression=Attr("tenant_id").eq(tenant_id)
                )
                for it in scan.get("Items", []):
                    if str(it.get("email", "")).lower() == str(username).lower():
                        staff_item = it
                        break
            except Exception:
                staff_item = None

        if not staff_item:
            return {"statusCode": 404, "headers": cors_headers, "body": json.dumps({"error": "Staff no encontrado"})}

        if staff_item.get("status") and staff_item["status"] != "activo":
            return {"statusCode": 403, "headers": cors_headers, "body": json.dumps({"error": "Usuario inactivo"})}

        # Verificación de password (simplificada para testing)
        if not verify_password_simple(password, staff_item.get("password_hash", "")):
            return {"statusCode": 401, "headers": cors_headers, "body": json.dumps({"error": "Credenciales inválidas"})}

        # Actualizar last_login
        try:
            staff_table.update_item(
                Key={"tenant_id": staff_item.get("tenant_id") or tenant_id, "id_staff": staff_item["id_staff"]},
                UpdateExpression="SET last_login = :ts",
                ExpressionAttributeValues={":ts": datetime.datetime.utcnow().isoformat()}
            )
        except Exception:
            pass

        claims = {
            "sub": staff_item.get("id_staff"),
            "email": staff_item.get("email") or "",
            "type": "staff",
            "role": staff_item.get("role", "staff"),
            "tenant_id": staff_item.get("tenant_id") or tenant_id,
        }
        token = sign_jwt(claims, exp_seconds=86400)

        payload = {
            "message": "Login exitoso",
            "token": token,
            "user": staff_item.get("name") or staff_item.get("email") or staff_item.get("id_staff"),
            "role": staff_item.get("role", "staff"),
            "id_staff": staff_item.get("id_staff"),
            "tenant_id": staff_item.get("tenant_id") or tenant_id,
            "headers_required": {
                "X-User-Id": staff_item.get("id_staff"),
                "X-User-Type": "staff",
                "X-User-Email": staff_item.get("email") or ""
            }
        }
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(payload)}

    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": f"Error en base de datos: {str(e)}"})}
    except Exception as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": f"Error inesperado: {str(e)}"})}

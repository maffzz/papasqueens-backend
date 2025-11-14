import json, os, boto3, datetime
from botocore.exceptions import ClientError
import bcrypt
from common.jwt_utils import sign_jwt


dynamo = boto3.resource("dynamodb")
staff_table = dynamo.Table(os.environ["STAFF_TABLE"])  # Staff


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        username = body.get('username') or body.get('email')
        password = body.get('password')
        tenant_id = body.get('tenant_id') or event.get('headers', {}).get('X-Tenant-Id') or event.get('headers', {}).get('x-tenant-id')

        if not username or not password:
            return {"statusCode": 400, "body": json.dumps({"error": "Usuario y password requeridos"})}

        # Buscar por email primero; si no, por id_staff
        # Nota: si la tabla staff no tiene índice por email, primero intentamos get por id_staff
        staff_item = None
        try:
            # get por id_staff
            resp = staff_table.get_item(Key={"id_staff": username})
            staff_item = resp.get("Item")
        except Exception:
            staff_item = None

        if (not staff_item) and username:
            # fallback: escaneo por email (costo bajo para PoC)
            try:
                scan = staff_table.scan()
                for it in scan.get("Items", []):
                    if str(it.get("email", "")).lower() == str(username).lower():
                        staff_item = it
                        break
            except Exception:
                staff_item = None

        if not staff_item:
            return {"statusCode": 404, "body": json.dumps({"error": "Staff no encontrado"})}

        if staff_item.get("status") and staff_item["status"] != "activo":
            return {"statusCode": 403, "body": json.dumps({"error": "Usuario inactivo"})}

        if not verify_password(password, staff_item.get("password_hash", "")):
            return {"statusCode": 401, "body": json.dumps({"error": "Credenciales inválidas"})}

        # actualizar last_login
        try:
            staff_table.update_item(
                Key={"id_staff": staff_item["id_staff"]},
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
        return {"statusCode": 200, "body": json.dumps(payload)}

    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": f"Error en base de datos: {str(e)}"})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": f"Error inesperado: {str(e)}"})}

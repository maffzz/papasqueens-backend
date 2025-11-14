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
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        password = body.get('password')
        name = body.get('name', '')
        tenant_id = body.get('tenant_id') or event.get('headers', {}).get('X-Tenant-Id') or event.get('headers', {}).get('x-tenant-id')

        if not email or not password:
            return {"statusCode": 400, "body": json.dumps({"error": "Email y password requeridos"})}

        resp = users_table.get_item(Key={"email": email})
        user = resp.get("Item")

        now = datetime.datetime.utcnow().isoformat()
        if not user:
            # Registrar cliente
            id_user = str(uuid.uuid4())
            users_table.put_item(Item={
                "email": email,
                "id_user": id_user,
                "type_user": "customer",
                "password_hash": hash_password(password),
                "name": name,
                "status": "activo",
                "id_sucursal": body.get("id_sucursal"),
                "created_at": now,
                "updated_at": now
            })
            user = {"email": email, "id_user": id_user, "type_user": "customer", "name": name, "status": "activo", "id_sucursal": body.get("id_sucursal")}
        else:
            if user.get("status") != "activo":
                return {"statusCode": 403, "body": json.dumps({"error": "Usuario inactivo"})}
            if not verify_password(password, user.get("password_hash", "")):
                return {"statusCode": 401, "body": json.dumps({"error": "Credenciales inválidas"})}

        claims = {
            "sub": user.get("id_user", email),
            "email": email,
            "type": "customer",
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
            "headers_required": {
                "X-User-Id": user.get("id_user", email),
                "X-User-Type": "customer",
                "X-User-Email": email
            }
        }
        return {"statusCode": 200, "body": json.dumps(payload)}

    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": f"Error en base de datos: {str(e)}"})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": f"Error inesperado: {str(e)}"})}

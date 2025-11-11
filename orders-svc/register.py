import json, os, boto3, uuid, datetime
import base64, hashlib, hmac
from botocore.exceptions import ClientError


dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["USERS_TABLE"])


def hash_password(password: str) -> str:
    iterations = 260000
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return f"pbkdf2${iterations}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        password = body.get('password')
        name = body.get('name', "")
        id_sucursal = body.get('id_sucursal')

        if not email or not password:
            return {"statusCode": 400, "body": json.dumps({"error": "Email y password requeridos"})}

        resp = table.get_item(Key={"email": email})
        if resp.get("Item"):
            return {"statusCode": 409, "body": json.dumps({"error": "Usuario ya existe"})}

        now = datetime.datetime.utcnow().isoformat()
        id_user = str(uuid.uuid4())
        password_hash = hash_password(password)

        user_item = {
            "email": email,
            "id_user": id_user,
            "type_user": "cliente",
            "role": None,
            "password_hash": password_hash,
            "name": name,
            "status": "activo",
            "id_sucursal": id_sucursal,
            "created_at": now,
            "updated_at": now
        }

        table.put_item(Item=user_item)

        return {
            "statusCode": 201,
            "body": json.dumps({
                "message": "Usuario registrado",
                "id_user": id_user,
                "email": email,
                "type_user": "cliente"
            })
        }
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": f"Error en base de datos: {str(e)}"})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": f"Error inesperado: {str(e)}"})}
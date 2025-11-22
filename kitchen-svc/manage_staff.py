import json, boto3, os, uuid, datetime
from botocore.exceptions import ClientError
import base64
import bcrypt
from common.jwt_utils import verify_jwt

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["STAFF_TABLE"])
eb = boto3.client("events")
s3 = boto3.client("s3")

def _cors(event):
    headers_in = event.get("headers", {}) or {}
    return {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PATCH",
        "Content-Type": "application/json",
    }


def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def manage_staff(event, context):
    cors_headers = _cors(event)
    try:
        # Auth: require staff admin
        headers = event.get("headers", {}) or {}
        authz = headers.get("Authorization") or headers.get("authorization")
        if not authz or not authz.lower().startswith("bearer "):
            return {"statusCode": 401, "headers": cors_headers, "body": json.dumps({"error": "No autorizado"})}
        token = authz.split(" ", 1)[1].strip()
        claims = verify_jwt(token) or {}
        if (claims.get("type") != "staff") or (claims.get("role") != "admin"):
            return {"statusCode": 403, "headers": cors_headers, "body": json.dumps({"error": "Requiere rol admin"})}

        body = json.loads(event.get("body", "{}"))
        id_staff = body.get("id_staff", str(uuid.uuid4()))
        tenant_id = body["tenant_id"]
        name = body["name"]
        role = body["role"]
        email = body["email"]
        status = body.get("status", "activo")
        password = body.get("password")
        dni = body.get("dni")
        phone = body.get("phone")
        id_sucursal = body.get("id_sucursal")

        now = datetime.datetime.utcnow().isoformat()
        
        existing_staff = table.get_item(Key={"id_staff": id_staff}).get("Item")
        is_new = existing_staff is None
        
        # validate role
        if role not in ("staff", "delivery", "admin"):
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "Rol inválido"})}

        item = {
            "id_staff": id_staff,
            "tenant_id": tenant_id,
            "name": name,
            "role": role,
            "email": email,
            "status": status,
            "updated_at": now
        }
        
        if dni:
            item["dni"] = dni
        if phone:
            item["phone"] = phone
        if id_sucursal:
            item["id_sucursal"] = id_sucursal
        
        if is_new:
            item["hire_date"] = now
        elif existing_staff and "hire_date" in existing_staff:
            item["hire_date"] = existing_staff["hire_date"]
        
        if existing_staff and "last_login" in existing_staff:
            item["last_login"] = existing_staff["last_login"]
        
        if password:
            item["password_hash"] = hash_password(password)

        table.put_item(Item=item)

        eb.put_events(
            Entries=[
                {
                    "Source": "kitchen-svc",
                    "DetailType": "Staff.Updated",
                    "Detail": json.dumps({"id_staff": id_staff, "tenant_id": tenant_id, "role": role}),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )

        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": "Staff actualizado", "id_staff": id_staff})}
    except KeyError as e:
        return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": f"Campo faltante: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}


def upload_staff_doc(event, context):
    cors_headers = _cors(event)
    try:
        # Auth: require staff admin
        headers = event.get("headers", {}) or {}
        authz = headers.get("Authorization") or headers.get("authorization")
        if not authz or not authz.lower().startswith("bearer "):
            return {"statusCode": 401, "headers": cors_headers, "body": json.dumps({"error": "No autorizado"})}
        token = authz.split(" ", 1)[1].strip()
        claims = verify_jwt(token) or {}
        if (claims.get("type") != "staff") or (claims.get("role") != "admin"):
            return {"statusCode": 403, "headers": cors_headers, "body": json.dumps({"error": "Requiere rol admin"})}

        body = json.loads(event.get("body", "{}"))
        id_staff = body["id_staff"]
        # tenant_id ya no es necesario para S3, pero se mantiene por compatibilidad del payload
        tenant_id = body.get("tenant_id")
        # Ahora esperamos opcionalmente una URL ya generada desde el frontend u otro servicio
        profile_url = body.get("profile_url")

        table.update_item(
            Key={"id_staff": id_staff},
            UpdateExpression="SET profile_url = :url",
            ExpressionAttributeValues={":url": profile_url}
        )
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"profile_url": profile_url})}
    except Exception as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}


def get_staff_doc(event, context):
    cors_headers = _cors(event)
    try:
        id_staff = event["queryStringParameters"]["id_staff"]
        resp = table.get_item(Key={"id_staff": id_staff})
        item = resp.get("Item")
        if not item or not item.get("profile_url"):
            return {"statusCode": 404, "headers": cors_headers, "body": json.dumps({"error": "No se encontró el documento de staff"})}
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"profile_url": item["profile_url"]})}
    except Exception as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}

def handler(event, context):
    path = event.get("resource", "")
    method = event.get("httpMethod", "GET")
    if path.endswith("/profile") and method == "POST":
        return upload_staff_doc(event, context)
    if path.endswith("/profile") and method == "GET":
        return get_staff_doc(event, context)
    return manage_staff(event, context)
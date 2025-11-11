import json, boto3, os, uuid, datetime
from botocore.exceptions import ClientError
import base64, hashlib, hmac

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["STAFF_TABLE"])
eb = boto3.client("events")
s3 = boto3.client("s3")

def hash_password(password):
    iterations = 260000
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return f"pbkdf2${iterations}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"

def manage_staff(event, context):
    try:
        headers = event.get("headers", {})
        user_type = headers.get("X-User-Type") or headers.get("x-user-type")
        if not user_type:
            qs = event.get("queryStringParameters") or {}
            user_type = qs.get("user_type")
        if user_type != "staff":
            return {"statusCode": 403, "body": json.dumps({"error": "Forbidden"})}

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

        return {"statusCode": 200, "body": json.dumps({"message": "Staff actualizado", "id_staff": id_staff})}
    except KeyError as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"Campo faltante: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

def upload_staff_doc(event, context):
    try:
        headers = event.get("headers", {})
        user_type = headers.get("X-User-Type") or headers.get("x-user-type")
        if not user_type:
            qs = event.get("queryStringParameters") or {}
            user_type = qs.get("user_type")
        if user_type != "staff":
            return {"statusCode": 403, "body": json.dumps({"error": "Forbidden"})}

        body = json.loads(event.get("body", "{}"))
        id_staff = body["id_staff"]
        tenant_id = body["tenant_id"]
        file_data = body["file_data"]
        ext = body.get("ext", "jpg")
        
        file_bytes = base64.b64decode(file_data)
        key = f"{tenant_id}/{id_staff}/profile.{ext}"
        s3.put_object(Bucket=os.environ.get("STAFF_BUCKET"), Key=key, Body=file_bytes, ContentType=f"image/{ext}")
        profile_url = f"https://{os.environ.get('STAFF_BUCKET')}.s3.amazonaws.com/{key}"

        table.update_item(
            Key={"id_staff": id_staff},
            UpdateExpression="SET profile_url = :url",
            ExpressionAttributeValues={":url": profile_url}
        )
        return {"statusCode": 200, "body": json.dumps({"profile_url": profile_url})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

def get_staff_doc(event, context):
    try:
        headers = event.get("headers", {})
        user_type = headers.get("X-User-Type") or headers.get("x-user-type")
        if not user_type:
            qs = event.get("queryStringParameters") or {}
            user_type = qs.get("user_type")
        if user_type != "staff":
            return {"statusCode": 403, "body": json.dumps({"error": "Forbidden"})}

        id_staff = event["queryStringParameters"]["id_staff"]
        resp = table.get_item(Key={"id_staff": id_staff})
        item = resp.get("Item")
        if not item or not item.get("profile_url"):
            return {"statusCode": 404, "body": json.dumps({"error": "No se encontró el documento de staff"})}
        return {"statusCode": 200, "body": json.dumps({"profile_url": item["profile_url"]})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

def handler(event, context):
    path = event.get("resource", "")
    method = event.get("httpMethod", "GET")
    if path.endswith("/profile") and method == "POST":
        return upload_staff_doc(event, context)
    if path.endswith("/profile") and method == "GET":
        return get_staff_doc(event, context)
    return manage_staff(event, context)
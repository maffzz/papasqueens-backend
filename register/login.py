import json, os, boto3, uuid, datetime
from botocore.exceptions import ClientError
import bcrypt

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["USERS_TABLE"])

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
        type_user = body.get('type_user', 'customer')
        
        if not email or not password:
            return {"statusCode": 400, "body": json.dumps({"error": "Email y password requeridos"})}

        resp = table.get_item(Key={"email": email})
        user = resp.get("Item")
        
        if not user:
            id_user = str(uuid.uuid4())
            now = datetime.datetime.utcnow().isoformat()
            
            password_hash = hash_password(password)
            
            new_user = {
                "email": email,
                "id_user": id_user,
                "type_user": type_user,
                "password_hash": password_hash,
                "name": body.get("name", ""),
                "status": "activo",
                "id_sucursal": body.get("id_sucursal", None),
                "role": body.get("role", None) if type_user == "staff" else None,
                "created_at": now,
                "updated_at": now
            }
            
            table.put_item(Item=new_user)
            
            redirect_url = "/dashboard/staff" if type_user == "staff" else "/dashboard/customer"
            
            return {
                "statusCode": 201,
                "body": json.dumps({
                    "message": "Usuario creado exitosamente",
                    "id_user": id_user,
                    "type_user": type_user,
                    "role": new_user.get("role"),
                    "redirect_url": redirect_url,
                    "id_sucursal": new_user.get("id_sucursal")
                })
            }
        
        stored_hash = user.get("password_hash")
        if not stored_hash or not verify_password(password, stored_hash):
            return {"statusCode": 401, "body": json.dumps({"error": "Password incorrecto"})}
        
        if user.get("status") != "activo":
            return {"statusCode": 403, "body": json.dumps({"error": "Usuario inactivo"})}
        
        user_type = user.get("type_user", "customer")
        if user_type == "staff":
            redirect_url = "/dashboard/staff"
            role = user.get("role", "staff")
        else:
            redirect_url = "/dashboard/customer"
            role = None
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Login exitoso",
                "id_user": user.get("id_user", email),
                "email": email,
                "type_user": user_type,
                "role": role,
                "redirect_url": redirect_url,
                "id_sucursal": user.get("id_sucursal"),
                "name": user.get("name", ""),
                "headers_required": {
                    "X-User-Id": user.get("id_user", email),
                    "X-User-Type": user_type,
                    "X-User-Email": email
                }
            })
        }
        
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": f"Error en base de datos: {str(e)}"})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": f"Error inesperado: {str(e)}"})}
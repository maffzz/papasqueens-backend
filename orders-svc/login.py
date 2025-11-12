import json, os, boto3, uuid, datetime
from botocore.exceptions import ClientError
from validate import issue_token, verify_password

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["USERS_TABLE"])

def handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        password = body.get('password')
        
        if not email or not password:
            return {"statusCode": 400, "body": json.dumps({"error": "Email y password requeridos"})}

        resp = table.get_item(Key={"email": email})
        user = resp.get("Item")
        
        if not user:
            return {"statusCode": 404, "body": json.dumps({"error": "Usuario no encontrado"})}
        
        stored_hash = user.get("password_hash")
        if not stored_hash or not verify_password(password, stored_hash):
            return {"statusCode": 401, "body": json.dumps({"error": "Password incorrecto"})}
        
        if user.get("status") != "activo":
            return {"statusCode": 403, "body": json.dumps({"error": "Usuario inactivo"})}
        
        user_type_db = user.get("type_user", "cliente")
        user_type = "staff" if user_type_db == "staff" else "cliente"
        if user_type != "staff":
            return {"statusCode": 403, "body": json.dumps({"error": "Solo staff puede iniciar sesión aquí. Los clientes deben usar /register"})}
        if user_type == "staff":
            redirect_url = "/dashboard/staff"
            role = user.get("role", "staff")
        else:
            redirect_url = "/dashboard/customer"
            role = None
        
        access_token = issue_token(user.get("id_user", email), email, user_type, role=role)

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
                "access_token": access_token,
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
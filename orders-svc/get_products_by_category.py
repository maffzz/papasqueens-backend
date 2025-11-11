import json, os, boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr
from validate import require_roles

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["PRODUCTS_TABLE"])

def get_user_info(event):
    claims = require_roles(event, {"staff", "cliente"})
    user_type = "staff" if claims.get("user_type") == "staff" else "cliente"
    return {"email": claims.get("email"), "type": user_type, "id": claims.get("sub")}

def handler(event, context):
    try:
        user_info = get_user_info(event)
        
        if not user_info.get("type"):
            return {"statusCode": 401, "body": json.dumps({"error": "Información de usuario no proporcionada"})}
        
        categoria = event["pathParameters"]["categoria"]
        
        if user_info.get("type") == "staff":
            resp = table.scan(FilterExpression=Attr("categoria").eq(categoria))
            return {"statusCode": 200, "body": json.dumps(resp.get("Items", []))}
        
        if user_info.get("type") == "cliente":
            resp = table.scan(
                FilterExpression=Attr("categoria").eq(categoria) & Attr("available").eq(True)
            )
            return {"statusCode": 200, "body": json.dumps(resp.get("Items", []))}
        
        return {"statusCode": 403, "body": json.dumps({"error": "Tipo de usuario no válido"})}
    except KeyError as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"Parámetro faltante: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


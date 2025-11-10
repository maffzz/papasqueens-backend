import json, os, boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["PRODUCTS_TABLE"])

def get_user_info(event):
    headers = event.get("headers", {})
    user_email = headers.get("X-User-Email") or headers.get("x-user-email")
    user_type = headers.get("X-User-Type") or headers.get("x-user-type")
    user_id = headers.get("X-User-Id") or headers.get("x-user-id")
    
    if not user_email:
        query_params = event.get("queryStringParameters") or {}
        user_email = query_params.get("user_email")
        user_type = query_params.get("user_type")
        user_id = query_params.get("user_id")
    
    return {
        "email": user_email,
        "type": user_type,
        "id": user_id
    }

def handler(event, context):
    try:
        user_info = get_user_info(event)
        
        if not user_info.get("type"):
            return {"statusCode": 401, "body": json.dumps({"error": "Información de usuario no proporcionada"})}
        
        if user_info.get("type") == "staff":
            resp = table.scan()
            return {"statusCode": 200, "body": json.dumps(resp.get("Items", []))}
        
        if user_info.get("type") == "customer":
            resp = table.scan(FilterExpression=Attr("available").eq(True))
            return {"statusCode": 200, "body": json.dumps(resp.get("Items", []))}
        
        return {"statusCode": 403, "body": json.dumps({"error": "Tipo de usuario no válido"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
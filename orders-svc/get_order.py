import json, os, boto3
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["ORDERS_TABLE"])
users_table = dynamo.Table(os.environ.get("USERS_TABLE", "papasqueens-users"))

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

def check_authorization(user_info, order_item, action="read"):
    """Verifica si el usuario tiene permiso para acceder al pedido"""
    if not user_info.get("type"):
        return False, "Información de usuario no proporcionada"
    
    if user_info.get("type") == "staff":
        return True, None
    
    if user_info.get("type") == "customer":
        order_customer_id = order_item.get("id_customer")
        user_customer_id = user_info.get("id")
        
        if order_customer_id == user_customer_id:
            return True, None
        else:
            return False, "No tienes permiso para acceder a este pedido"
    
    return False, "Tipo de usuario no válido"

def handler(event, context):
    order_id = event["pathParameters"]["order_id"]
    try:
        user_info = get_user_info(event)
        
        response = table.get_item(Key={"id_order": order_id})
        item = response.get("Item")
        if not item:
            return {"statusCode": 404, "body": json.dumps({"error": "Pedido no encontrado"})}
        
        authorized, error_msg = check_authorization(user_info, item)
        if not authorized:
            return {"statusCode": 403, "body": json.dumps({"error": error_msg})}
        
        return {"statusCode": 200, "body": json.dumps(item)}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
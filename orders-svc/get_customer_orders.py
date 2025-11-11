import json, os, boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from validate import require_roles

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["ORDERS_TABLE"])

def get_user_info(event):
    claims = require_roles(event, {"staff", "cliente"})
    user_type = "staff" if claims.get("user_type") == "staff" else "cliente"
    return {"email": claims.get("email"), "type": user_type, "id": claims.get("sub")}

def handler(event, context):
    try:
        user_info = get_user_info(event)
        
        if not user_info.get("type"):
            return {"statusCode": 401, "body": json.dumps({"error": "Información de usuario no proporcionada"})}
        
        if user_info.get("type") == "staff":
            tenant_id = event.get("queryStringParameters", {}).get("tenant_id")
            if tenant_id:
                from boto3.dynamodb.conditions import Attr
                resp = table.scan(FilterExpression=Attr("tenant_id").eq(tenant_id))
            else:
                resp = table.scan()
            return {"statusCode": 200, "body": json.dumps(resp.get("Items", []))}
        
        if user_info.get("type") == "cliente":
            id_customer = user_info.get("id")
            
            if not id_customer:
                return {"statusCode": 400, "body": json.dumps({"error": "ID de cliente no proporcionado"})}
            
            resp = table.query(
                IndexName="GSI1",
                KeyConditionExpression=Key("id_customer").eq(id_customer)
            )
            return {"statusCode": 200, "body": json.dumps(resp.get("Items", []))}
        
        return {"statusCode": 403, "body": json.dumps({"error": "Tipo de usuario no válido"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
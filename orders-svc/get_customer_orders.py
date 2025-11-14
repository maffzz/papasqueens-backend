import json, os, boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["ORDERS_TABLE"])

def get_user_info(event):
    """Extrae información del usuario desde headers o query params"""
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

def get_tenant_id(event):
    headers = event.get("headers", {}) or {}
    tenant_id = headers.get("X-Tenant-Id") or headers.get("x-tenant-id")
    if not tenant_id:
        qs = event.get("queryStringParameters") or {}
        tenant_id = qs.get("tenant_id")
    return tenant_id

def handler(event, context):
    try:
        user_info = get_user_info(event)
        tenant_id = get_tenant_id(event)
        
        if not user_info.get("type"):
            return {"statusCode": 401, "body": json.dumps({"error": "Información de usuario no proporcionada"})}
        
        utype = (user_info.get("type") or '').lower()
        
        # Staff: si especifica tenant_id, solo órdenes de ese tenant; si no, todas (multi-tenant admin)
        if utype == "staff":
            if tenant_id:
                resp = table.query(
                    KeyConditionExpression=Key("tenant_id").eq(tenant_id)
                )
            else:
                resp = table.scan()
            return {"statusCode": 200, "body": json.dumps(resp.get("Items", []))}
        
        # Customer: requiere id_customer y tenant_id; usamos GSI por cliente y filtramos por tenant
        if utype == "customer":
            id_customer = user_info.get("id")
            if not id_customer:
                path_params = event.get("pathParameters") or {}
                id_customer = path_params.get("id_customer")
            
            if not id_customer:
                return {"statusCode": 400, "body": json.dumps({"error": "ID de cliente no proporcionado"})}
            if not tenant_id:
                return {"statusCode": 400, "body": json.dumps({"error": "tenant_id requerido"})}
            
            resp = table.query(
                IndexName="CustomerIndex",
                KeyConditionExpression=Key("id_customer").eq(id_customer)
            )
            items = [x for x in resp.get("Items", []) if x.get("tenant_id") == tenant_id]
            return {"statusCode": 200, "body": json.dumps(items)}
        
        return {"statusCode": 403, "body": json.dumps({"error": "Tipo de usuario no válido"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
import json, os, boto3, datetime
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["ORDERS_TABLE"])
eb = boto3.client("events")

def get_user_info(event):
    """Extrae información del usuario desde headers"""
    headers = event.get("headers", {})
    user_type = headers.get("X-User-Type") or headers.get("x-user-type")
    user_id = headers.get("X-User-Id") or headers.get("x-user-id")
    
    if not user_type:
        query_params = event.get("queryStringParameters") or {}
        user_type = query_params.get("user_type")
        user_id = query_params.get("user_id")
    
    return {
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
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,PATCH",
        "Content-Type": "application/json",
    }

    order_id = event["pathParameters"]["order_id"]
    body = json.loads(event.get("body", "{}"))
    new_status = body.get("status")

    if new_status not in ["en_preparacion","listo_para_entrega","en_camino","entregado"]:
        return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "Estado no válido"})}

    try:
        user_info = get_user_info(event)
        if user_info.get("type") != "staff":
            return {"statusCode": 403, "headers": cors_headers, "body": json.dumps({"error": "Solo el personal autorizado puede actualizar el estado del pedido"})}
        
        tenant_id = get_tenant_id(event)
        if not tenant_id:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "tenant_id requerido"})}
        
        order_resp = table.get_item(Key={"tenant_id": tenant_id, "id_order": order_id})
        if not order_resp.get("Item"):
            return {"statusCode": 404, "headers": cors_headers, "body": json.dumps({"error": "Pedido no encontrado"})}
        
        now = datetime.datetime.utcnow().isoformat()
        table.update_item(
            Key={"tenant_id": tenant_id, "id_order": order_id},
            UpdateExpression="SET #s = :s, updated_at = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": new_status, ":u": now}
        )

        eb.put_events(
            Entries=[
                {
                    "Source": "orders-svc",
                    "DetailType": "Order.Updated",
                    "Detail": json.dumps({"tenant_id": tenant_id, "id_order": order_id, "new_status": new_status}),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": "Estado actualizado"})}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
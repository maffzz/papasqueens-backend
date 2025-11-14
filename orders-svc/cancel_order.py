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
    order_id = event["pathParameters"]["order_id"]
    try:
        user_info = get_user_info(event)
        tenant_id = get_tenant_id(event)
        
        order_resp = table.get_item(Key={"tenant_id": tenant_id, "id_order": order_id})
        order_item = order_resp.get("Item")
        if not order_item:
            return {"statusCode": 404, "body": json.dumps({"error": "Pedido no encontrado"})}
        
        if user_info.get("type") == "staff":
            pass
        elif user_info.get("type") == "customer":
            if order_item.get("id_customer") != user_info.get("id"):
                return {"statusCode": 403, "body": json.dumps({"error": "Solo puedes cancelar tus propios pedidos"})}
        else:
            return {"statusCode": 401, "body": json.dumps({"error": "Información de usuario no válida"})}
        
        current_status = order_item.get("status")
        if current_status in ["en_preparacion", "listo_para_entrega", "en_camino", "entregado"]:
            return {"statusCode": 400, "body": json.dumps({"error": "No se puede cancelar un pedido que ya está en preparación o más avanzado"})}
        
        now = datetime.datetime.utcnow().isoformat()
        table.update_item(
            Key={"tenant_id": tenant_id, "id_order": order_id},
            UpdateExpression="SET #s=:s, updated_at=:u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "cancelado", ":u": now}
        )
        eb.put_events(
            Entries=[
                {
                    "Source": "orders-svc",
                    "DetailType": "Order.Cancelled",
                    "Detail": json.dumps({"tenant_id": tenant_id, "id_order": order_id}),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )
        return {"statusCode": 200, "body": json.dumps({"message": "Pedido cancelado"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
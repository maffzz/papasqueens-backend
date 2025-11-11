import json, os, boto3, datetime
from botocore.exceptions import ClientError
from validate import require_roles

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["ORDERS_TABLE"])
eb = boto3.client("events")

def handler(event, context):
    order_id = event["pathParameters"]["order_id"]
    try:
        claims = require_roles(event, {"cliente"})
        
        order_resp = table.get_item(Key={"id_order": order_id})
        order_item = order_resp.get("Item")
        if not order_item:
            return {"statusCode": 404, "body": json.dumps({"error": "Pedido no encontrado"})}
        
        # Solo clientes, validado por JWT. Verificar que sea dueño del pedido
        if order_item.get("id_customer") != claims.get("sub"):
            return {"statusCode": 403, "body": json.dumps({"error": "Solo puedes cancelar tus propios pedidos"})}
        
        current_status = order_item.get("status")
        if current_status in ["en_preparacion", "listo_para_entrega", "en_camino", "entregado"]:
            return {"statusCode": 400, "body": json.dumps({"error": "No se puede cancelar un pedido que ya está en preparación o más avanzado"})}
        
        now = datetime.datetime.utcnow().isoformat()
        table.update_item(
            Key={"id_order": order_id},
            UpdateExpression="SET #s=:s, updated_at=:u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "cancelado", ":u": now}
        )
        eb.put_events(
            Entries=[
                {
                    "Source": "orders-svc",
                    "DetailType": "Order.Cancelled",
                    "Detail": json.dumps({"id_order": order_id}),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )
        return {"statusCode": 200, "body": json.dumps({"message": "Pedido cancelado"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
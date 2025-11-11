import json, os, boto3, datetime
from botocore.exceptions import ClientError
from validate import require_roles

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["ORDERS_TABLE"])
eb = boto3.client("events")

def get_user_info(event):
    claims = require_roles(event, {"staff"})
    return {"type": "staff", "id": claims.get("sub")}

def handler(event, context):
    order_id = event["pathParameters"]["order_id"]
    body = json.loads(event.get("body", "{}"))
    new_status = body.get("status")

    if new_status not in ["en_preparacion","listo_para_entrega","en_camino","entregado"]:
        return {"statusCode": 400, "body": json.dumps({"error": "Estado no válido"})}

    try:
        _ = require_roles(event, {"staff"})
        
        order_resp = table.get_item(Key={"id_order": order_id})
        if not order_resp.get("Item"):
            return {"statusCode": 404, "body": json.dumps({"error": "Pedido no encontrado"})}
        
        now = datetime.datetime.utcnow().isoformat()
        table.update_item(
            Key={"id_order": order_id},
            UpdateExpression="SET #s = :s, updated_at = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": new_status, ":u": now}
        )

        eb.put_events(
            Entries=[
                {
                    "Source": "orders-svc",
                    "DetailType": "Order.Updated",
                    "Detail": json.dumps({"id_order": order_id, "new_status": new_status}),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )
        return {"statusCode": 200, "body": json.dumps({"message": "Estado actualizado"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
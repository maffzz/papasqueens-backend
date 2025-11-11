import json, boto3, os, datetime
from botocore.exceptions import ClientError
from validate import require_roles

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
eb = boto3.client("events")

def handler(event, context):
    try:
        _ = require_roles(event, {"staff"})

        id_delivery = event["pathParameters"]["id_delivery"]
        body = json.loads(event.get("body", "{}"))
        new_status = body["status"]

        if new_status not in ["asignado", "en_camino", "entregado"]:
            return {"statusCode": 400, "body": json.dumps({"error": "Estado inválido"})}

        delivery_resp = delivery_table.get_item(Key={"id_delivery": id_delivery})
        if not delivery_resp.get("Item"):
            return {"statusCode": 404, "body": json.dumps({"error": "Entrega no encontrada"})}
        
        delivery = delivery_resp["Item"]
        id_order = delivery.get("id_order")
        
        now = datetime.datetime.utcnow().isoformat()
        delivery_table.update_item(
            Key={"id_delivery": id_delivery},
            UpdateExpression="SET #s = :s, updated_at = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": new_status, ":u": now}
        )

        event_type = "Order.EnRoute" if new_status == "en_camino" else "Order.Delivered" if new_status == "entregado" else "Delivery.Updated"
        
        if event_type == "Order.Delivered" and id_order:
            event_detail = {"id_order": id_order, "id_delivery": id_delivery, "status": new_status}
        else:
            event_detail = {"id_delivery": id_delivery, "status": new_status}

        eb.put_events(
            Entries=[
                {
                    "Source": "delivery-svc",
                    "DetailType": event_type,
                    "Detail": json.dumps(event_detail),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )

        return {"statusCode": 200, "body": json.dumps({"message": f"Estado actualizado a {new_status}"})}
    except KeyError as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"Campo faltante: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
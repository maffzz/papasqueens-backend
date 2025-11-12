import json, boto3, os, datetime
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
eb = boto3.client("events")

def handler(event, context):
    try:
        headers = event.get("headers", {}) or {}
        qs = event.get("queryStringParameters") or {}
        id_delivery = event["pathParameters"]["id_delivery"]
        body = json.loads(event.get("body", "{}"))
        new_status = body["status"]
        tenant_id = body.get("tenant_id") or headers.get("X-Tenant-Id") or headers.get("x-tenant-id") or qs.get("tenant_id") or "default"
        actor = body.get("id_staff") or headers.get("X-User-Id") or headers.get("x-user-id")

        if new_status not in ["asignado", "en_camino", "entregado"]:
            return {"statusCode": 400, "body": json.dumps({"error": "Estado inválido"})}

        delivery_resp = delivery_table.get_item(Key={"id_delivery": id_delivery})
        if not delivery_resp.get("Item"):
            return {"statusCode": 404, "body": json.dumps({"error": "Entrega no encontrada"})}
        
        delivery = delivery_resp["Item"]
        if delivery.get("tenant_id") != tenant_id:
            return {"statusCode": 404, "body": json.dumps({"error": "Entrega no pertenece al tenant"})}
        id_order = delivery.get("id_order")
        
        now = datetime.datetime.utcnow().isoformat()
        delivery_table.update_item(
            Key={"id_delivery": id_delivery},
            UpdateExpression="SET #s = :s, status_by = :by, updated_at = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": new_status, ":by": actor or "unknown", ":u": now}
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
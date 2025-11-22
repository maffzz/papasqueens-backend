import json, boto3, os, datetime
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
eb = boto3.client("events")

def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,PATCH",
        "Content-Type": "application/json",
    }

    try:
        headers = event.get("headers", {}) or {}
        qs = event.get("queryStringParameters") or {}
        id_delivery = event["pathParameters"]["id_delivery"]
        body = json.loads(event.get("body", "{}"))
        new_status = body["status"]
        tenant_id = body.get("tenant_id") or headers.get("X-Tenant-Id") or headers.get("x-tenant-id") or qs.get("tenant_id") or "default"
        actor = body.get("id_staff") or headers.get("X-User-Id") or headers.get("x-user-id")

        if new_status not in ["asignado", "en_camino", "entregado"]:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "Estado inválido"})}

        delivery_resp = delivery_table.get_item(Key={"tenant_id": tenant_id, "id_delivery": id_delivery})
        if not delivery_resp.get("Item"):
            return {"statusCode": 404, "headers": cors_headers, "body": json.dumps({"error": "Entrega no encontrada"})}
        
        delivery = delivery_resp["Item"]
        id_order = delivery.get("id_order")
        
        now = datetime.datetime.utcnow().isoformat()

        # Construir dinámicamente el update para registrar tiempos de salida/llegada
        update_expr = "SET #s = :s, status_by = :by, updated_at = :u"
        expr_attr_names = {"#s": "status"}
        expr_attr_values = {":s": new_status, ":by": actor or "unknown", ":u": now}

        if new_status == "en_camino":
            # Marca de salida a reparto
            update_expr += ", tiempo_salida = :ts"
            expr_attr_values[":ts"] = now
        elif new_status == "entregado":
            # Marca de llegada al cliente
            update_expr += ", tiempo_llegada = :tl"
            expr_attr_values[":tl"] = now

        delivery_table.update_item(
            Key={"tenant_id": tenant_id, "id_delivery": id_delivery},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values,
        )

        event_type = "Order.EnRoute" if new_status == "en_camino" else "Order.Delivered" if new_status == "entregado" else "Delivery.Updated"

        # Siempre que exista id_order, incluirlo en el detalle del evento
        event_detail = {"tenant_id": tenant_id, "id_delivery": id_delivery, "status": new_status}
        if id_order:
            event_detail["id_order"] = id_order

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

        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": f"Estado actualizado a {new_status}"})}
    except KeyError as e:
        return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": f"Campo faltante: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
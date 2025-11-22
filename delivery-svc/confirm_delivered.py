import json, boto3, os, datetime, uuid
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr, Key

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
orders_table = dynamo.Table(os.environ["ORDERS_TABLE"])
eb = boto3.client("events")
s3 = boto3.client("s3")

def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST",
        "Content-Type": "application/json",
    }

    try:
        id_order = event["pathParameters"]["id_order"]
        body = json.loads(event.get("body", "{}"))
        headers = event.get("headers", {}) or {}
        qs = event.get("queryStringParameters") or {}
        tenant_id = body.get("tenant_id") or headers.get("X-Tenant-Id") or headers.get("x-tenant-id") or qs.get("tenant_id") or "default"
        staff_id = body.get("id_staff") or headers.get("X-User-Id") or headers.get("x-user-id")

        resp = delivery_table.query(
            IndexName="OrderIndex",
            KeyConditionExpression=Key("id_order").eq(id_order)
        )
        items = [x for x in resp.get("Items", []) if x.get("tenant_id") == tenant_id]
        if not items:
            return {"statusCode": 404, "headers": cors_headers, "body": json.dumps({"error": "Entrega no encontrada"})}

        delivery = items[0]
        id_delivery = delivery["id_delivery"]
        now = datetime.datetime.utcnow().isoformat()

        # Construir un recibo simple de la orden
        receipt_url = None
        try:
            order_resp = orders_table.get_item(Key={"tenant_id": tenant_id, "id_order": id_order})
            order_item = order_resp.get("Item", {}) or {}

            customer_name = order_item.get("customer_name") or order_item.get("name")
            items_list = order_item.get("items") or []

            total = 0.0
            sanitized_items = []
            for it in items_list:
                if not isinstance(it, dict):
                    continue
                precio = it.get("precio") or it.get("price") or 0
                qty = it.get("qty") or 1
                try:
                    total += float(precio) * float(qty)
                except Exception:
                    pass
                sanitized_items.append({
                    "id_producto": it.get("id_producto") or it.get("id") or it.get("sku"),
                    "nombre": it.get("nombre") or it.get("name"),
                    "precio": float(precio) if isinstance(precio, (int, float)) else float(str(precio)) if precio is not None else 0.0,
                    "qty": qty,
                })

            receipt = {
                "id_order": id_order,
                "id_delivery": id_delivery,
                "tenant_id": tenant_id,
                "customer_name": customer_name,
                "total_paid": round(total, 2),
                "currency": "PEN",
                "items": sanitized_items,
                "delivered_at": now,
            }

            bucket = os.environ["RECEIPTS_BUCKET"]
            key = f"{tenant_id}/{id_order}/receipt_{uuid.uuid4()}.json"
            s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(receipt, default=str), ContentType="application/json")
            receipt_url = f"https://{bucket}.s3.amazonaws.com/{key}"
        except Exception:
            # Si falla la generación del recibo, no bloqueamos la confirmación de entrega
            receipt_url = None

        delivery_table.update_item(
            Key={"tenant_id": tenant_id, "id_delivery": id_delivery},
            UpdateExpression="SET #s=:s, tiempo_llegada=:t, delivered_by=:by, receipt_url=:r, updated_at=:u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "entregado",
                ":t": now,
                ":by": staff_id or delivery.get("id_staff", "unknown"),
                ":r": receipt_url,
                ":u": now,
            },
        )

        # Mantener sincronizado el pedido principal en Orders
        try:
            orders_table.update_item(
                Key={"tenant_id": tenant_id, "id_order": id_order},
                UpdateExpression="SET #s = :s, updated_at = :u",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":s": "entregado", ":u": now},
            )
        except Exception:
            # No rompemos el flujo si la actualización de Orders falla por alguna razón
            pass

        eb.put_events(
            Entries=[
                {
                    "Source": "delivery-svc",
                    "DetailType": "Order.Delivered",
                    "Detail": json.dumps({"tenant_id": tenant_id, "id_order": id_order, "id_delivery": id_delivery, "receipt_url": receipt_url}),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": "Entrega confirmada", "receipt_url": receipt_url})}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
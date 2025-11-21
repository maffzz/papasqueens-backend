import json, boto3, os, datetime, base64, uuid
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
        proof_data = body.get("proof_data")
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
        proof_url = None

        if proof_data:
            image_bytes = base64.b64decode(proof_data)
            key = f"{tenant_id}/{id_order}/proof_{uuid.uuid4()}.jpg"
            s3.put_object(Bucket=os.environ["PROOF_BUCKET"], Key=key, Body=image_bytes, ContentType="image/jpeg")
            proof_url = f"https://{os.environ['PROOF_BUCKET']}.s3.amazonaws.com/{key}"

        delivery_table.update_item(
            Key={"tenant_id": tenant_id, "id_delivery": id_delivery},
            UpdateExpression="SET #s=:s, tiempo_llegada=:t, delivered_by=:by, proof_url=:p, updated_at=:u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "entregado",
                ":t": now,
                ":by": staff_id or delivery.get("id_staff", "unknown"),
                ":p": proof_url,
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
                    "Detail": json.dumps({"tenant_id": tenant_id, "id_order": id_order, "id_delivery": id_delivery, "proof_url": proof_url}),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": "Entrega confirmada", "proof_url": proof_url})}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
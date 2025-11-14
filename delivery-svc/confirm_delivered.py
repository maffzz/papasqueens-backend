import json, boto3, os, datetime, base64, uuid
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr, Key

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
eb = boto3.client("events")
s3 = boto3.client("s3")

def handler(event, context):
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
            return {"statusCode": 404, "body": json.dumps({"error": "Entrega no encontrada"})}

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
            UpdateExpression="SET status=:s, tiempo_llegada=:t, delivered_by=:by, proof_url=:p, updated_at=:u",
            ExpressionAttributeValues={":s": "entregado", ":t": now, ":by": staff_id or delivery.get('id_staff', 'unknown'), ":p": proof_url, ":u": now}
        )

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
        return {"statusCode": 200, "body": json.dumps({"message": "Entrega confirmada", "proof_url": proof_url})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
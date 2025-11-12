import json
import boto3
import os
import datetime
import base64
import uuid
from botocore.exceptions import ClientError
from validate import require_roles

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
eb = boto3.client("events")
s3 = boto3.client("s3")

def handler(event, context):
    try:
        _ = require_roles(event, {"staff"})

        id_delivery = event["pathParameters"]["id_delivery"]
        body = json.loads(event.get("body", "{}"))
        proof_data = body.get("proof_data")
        tenant_id = body.get("tenant_id", "default")

        resp = delivery_table.get_item(Key={"id_delivery": id_delivery})
        delivery = resp.get("Item")

        if not delivery:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Entrega no encontrada"})
            }

        tenant_id = delivery.get("tenant_id", tenant_id)
        id_order = delivery.get("id_order")
        now = datetime.datetime.utcnow().isoformat()

        proof_url = None
        if proof_data:
            image_bytes = base64.b64decode(proof_data)
            order_id_for_key = id_order or "unknown_order"
            key = f"{tenant_id}/{order_id_for_key}/proofs/{id_delivery}_{uuid.uuid4()}.jpg"
            s3.put_object(
                Bucket=os.environ["PROOF_BUCKET"],
                Key=key,
                Body=image_bytes,
                ContentType="image/jpeg"
            )
            proof_url = f"https://{os.environ['PROOF_BUCKET']}.s3.amazonaws.com/{key}"

        delivery_table.update_item(
            Key={"id_delivery": id_delivery},
            UpdateExpression="SET #s = :s, tiempo_llegada = :t, proof_url = :p, updated_at = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "entregado",
                ":t": now,
                ":p": proof_url,
                ":u": now
            }
        )

        eb.put_events(
            Entries=[
                {
                    "Source": "delivery-svc",
                    "DetailType": "Order.Delivered",
                    "Detail": json.dumps({
                        "id_delivery": id_delivery,
                        "id_order": id_order,
                        "proof_url": proof_url
                    }),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Entrega confirmada",
                "proof_url": proof_url
            })
        }

    except ClientError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
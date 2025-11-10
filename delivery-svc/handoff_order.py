import json
import boto3
import os
import datetime
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
eb = boto3.client("events")

def handler(event, context):
    try:
        id_delivery = event["pathParameters"]["id_delivery"]
        now = datetime.datetime.utcnow().isoformat()

        resp = delivery_table.get_item(Key={"id_delivery": id_delivery})
        delivery = resp.get("Item")

        if not delivery:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Entrega no encontrada"})
            }

        delivery_table.update_item(
            Key={"id_delivery": id_delivery},
            UpdateExpression="SET #s = :s, tiempo_salida = :t, updated_at = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "en_camino",
                ":t": now,
                ":u": now
            }
        )

        eb.put_events(
            Entries=[
                {
                    "Source": "delivery-svc",
                    "DetailType": "Delivery.EnRoute",
                    "Detail": json.dumps({
                        "id_delivery": id_delivery,
                        "id_order": delivery.get("id_order")
                    }),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Entrega salió a reparto"})
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
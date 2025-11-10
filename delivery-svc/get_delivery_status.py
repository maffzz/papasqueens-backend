import json
import boto3
import os
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def handler(event, context):
    try:
        id_delivery = event["pathParameters"]["id_delivery"]

        resp = delivery_table.get_item(Key={"id_delivery": id_delivery})
        delivery = resp.get("Item")

        if not delivery:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "No se encontró la entrega"})
            }

        if delivery.get("status") == "en_camino":
            last_location = delivery.get("last_location")
            if last_location:
                delivery["location"] = last_location
            elif delivery.get("lat") and delivery.get("lon"):
                delivery["location"] = {
                    "lat": delivery["lat"],
                    "lon": delivery["lon"]
                }
            else:
                delivery["location"] = None

        return {
            "statusCode": 200,
            "body": json.dumps(delivery)
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
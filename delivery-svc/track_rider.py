import json
import boto3
import os
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def handler(event, context):
    try:
        headers = event.get("headers", {})
        user_type = headers.get("X-User-Type") or headers.get("x-user-type")
        if not user_type:
            qs = event.get("queryStringParameters") or {}
            user_type = qs.get("user_type")
        if user_type != "staff":
            return {"statusCode": 403, "body": json.dumps({"error": "Forbidden"})}

        id_delivery = event["pathParameters"]["id_delivery"]

        resp = delivery_table.get_item(Key={"id_delivery": id_delivery})
        delivery = resp.get("Item")

        if not delivery:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Entrega no encontrada"})
            }

        last_location = delivery.get("last_location") or {
            "lat": None,
            "lon": None
        }

        return {
            "statusCode": 200,
            "body": json.dumps(last_location)
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
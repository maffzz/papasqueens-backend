import json, boto3, os
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def handler(event, context):
    try:
        id_delivery = event["pathParameters"]["id_delivery"]
        resp = delivery_table.get_item(Key={"id_delivery": id_delivery})
        delivery = resp.get("Item")
        if not delivery:
            return {"statusCode": 404, "body": json.dumps({"error": "Entrega no encontrada"})}
        last_location = delivery.get("last_location", {"lat": None, "lon": None})
        return {"statusCode": 200, "body": json.dumps(last_location)}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
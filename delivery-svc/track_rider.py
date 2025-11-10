import json, boto3, os
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def handler(event, context):
    try:
        id_order = event["pathParameters"]["id_order"]
        resp = delivery_table.scan(FilterExpression=Attr("id_order").eq(id_order))
        if not resp.get("Items"):
            return {"statusCode": 404, "body": json.dumps({"error": "Pedido no encontrado"})}
        delivery = resp["Items"][0]
        last_location = delivery.get("last_location", {"lat": None, "lon": None})
        return {"statusCode": 200, "body": json.dumps(last_location)}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
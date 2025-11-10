import json, boto3, os
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def handler(event, context):
    try:
        id_order = event["pathParameters"]["id_order"]
        resp = delivery_table.scan(FilterExpression=Attr("id_order").eq(id_order))
        items = resp.get("Items", [])
        if not items:
            return {"statusCode": 404, "body": json.dumps({"error": "No se encontró la entrega"})}
        
        delivery = items[0]
        delivery_status = delivery.get("status", "")
        
        if delivery_status == "en_camino":
            last_location = delivery.get("last_location")
            if last_location:
                delivery["location"] = last_location
            elif delivery.get("lat") and delivery.get("lon"):
                delivery["location"] = {
                    "lat": delivery.get("lat"),
                    "lon": delivery.get("lon")
                }
            else:
                delivery["location"] = None
        
        return {"statusCode": 200, "body": json.dumps(delivery)}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
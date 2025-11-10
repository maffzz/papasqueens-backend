import json, boto3, os, datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
eb = boto3.client("events")

def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        id_order = event["pathParameters"]["id_order"]
        now = datetime.datetime.utcnow().isoformat()

        response = delivery_table.scan(FilterExpression=boto3.dynamodb.conditions.Attr("id_order").eq(id_order))
        items = response.get("Items", [])
        if not items:
            return {"statusCode": 404, "body": json.dumps({"error": "Entrega no encontrada"})}

        delivery = items[0]
        delivery_table.update_item(
            Key={"id_delivery": delivery["id_delivery"]},
            UpdateExpression="SET status=:s, tiempo_salida=:t, updated_at=:u",
            ExpressionAttributeValues={":s": "en_camino", ":t": now, ":u": now}
        )

        eb.put_events(
            Entries=[
                {
                    "Source": "delivery-svc",
                    "DetailType": "Order.EnRoute",
                    "Detail": json.dumps({"id_order": id_order}),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )
        return {"statusCode": 200, "body": json.dumps({"message": "Pedido salió a entrega"})}

    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
import json, boto3, os, datetime
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
eb = boto3.client("events")

def handler(event, context):
    try:
        resp = delivery_table.scan(FilterExpression=Attr("status").eq("entregado"))
        metrics = []
        for item in resp.get("Items", []):
            if item.get("tiempo_salida") and item.get("tiempo_llegada"):
                start = datetime.datetime.fromisoformat(item["tiempo_salida"])
                end = datetime.datetime.fromisoformat(item["tiempo_llegada"])
                dur = (end - start).total_seconds() / 60.0
                metrics.append({
                    "order_id": item["id_order"],
                    "tenant_id": item["tenant_id"],
                    "id_staff": item.get("id_staff"),
                    "tiempo_entrega": dur
                })

        if metrics:
            eb.put_events(
                Entries=[
                    {
                        "Source": "delivery-svc",
                        "DetailType": "Delivery.MetricsUpdated",
                        "Detail": json.dumps(metrics),
                        "EventBusName": os.environ["EVENT_BUS"]
                    }
                ]
            )

        return {"statusCode": 200, "body": json.dumps({"processed": len(metrics)})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
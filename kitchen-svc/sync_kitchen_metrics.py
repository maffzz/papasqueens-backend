import json, boto3, os, datetime
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["KITCHEN_TABLE"])
eb = boto3.client("events")

def handler(event, context):
    try:
        resp = table.scan(FilterExpression=Attr("status").eq("listo_para_entrega"))
        metrics = []
        for item in resp.get("Items", []):
            if item.get("start_time") and item.get("end_time"):
                start = datetime.datetime.fromisoformat(item["start_time"])
                end = datetime.datetime.fromisoformat(item["end_time"])
                dur = (end - start).total_seconds() / 60.0
                metrics.append({
                    "order_id": item["order_id"],
                    "tenant_id": item["tenant_id"],
                    "tiempo_total": dur
                })

        if metrics:
            eb.put_events(
                Entries=[
                    {
                        "Source": "kitchen-svc",
                        "DetailType": "Kitchen.MetricsUpdated",
                        "Detail": json.dumps(metrics),
                        "EventBusName": os.environ["EVENT_BUS"]
                    }
                ]
            )
        return {"statusCode": 200, "body": json.dumps({"processed": len(metrics)})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
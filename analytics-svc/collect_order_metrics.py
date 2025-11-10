import json, boto3, os, datetime, uuid
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
analytics_table = dynamo.Table(os.environ["ANALYTICS_TABLE"])

def handler(event, context):
    try:
        detail = event.get("detail", {})
        order_id = detail["id_order"]
        tenant_id = detail.get("tenant_id", "default")

        now = datetime.datetime.utcnow().isoformat()

        metric_item = {
            "id_metric": str(uuid.uuid4()),
            "id_order": order_id,
            "id_staff": None,
            "status": "recibido",
            "inicio": now,
            "fin": None,
            "tiempo_total": None,
            "tenant_id": tenant_id
        }

        analytics_table.put_item(Item=metric_item)

        return {"statusCode": 200, "body": json.dumps({"message": "Métrica inicial registrada", "id_order": order_id})}

    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
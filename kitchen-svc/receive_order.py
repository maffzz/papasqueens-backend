import json, boto3, os, datetime
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["KITCHEN_TABLE"])

def handler(event, context):
    try:
        # evento desde EventBridge
        detail = event.get("detail", {})
        order_id = detail["id_order"]
        tenant_id = detail["tenant_id"]
        now = datetime.datetime.utcnow().isoformat()

        item = {
            "order_id": order_id,
            "tenant_id": tenant_id,
            "list_id_staff": [],
            "status": "recibido",
            "start_time": None,
            "end_time": None,
            "updated_at": now
        }

        table.put_item(Item=item)
        return {"statusCode": 200, "body": json.dumps({"message": "Pedido recibido en cocina", "order_id": order_id})}

    except KeyError as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"Campo faltante en evento: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
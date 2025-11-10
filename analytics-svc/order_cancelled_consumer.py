import json, boto3, os, datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

dynamo = boto3.resource("dynamodb")
analytics_table = dynamo.Table(os.environ["ANALYTICS_TABLE"])


def handler(event, context):
    try:
        detail = event.get("detail", {})
        order_id = detail["id_order"]
        now = datetime.datetime.utcnow().isoformat()

        resp = analytics_table.query(
            IndexName="OrderIndex",
            KeyConditionExpression=Key("id_order").eq(order_id)
        )
        items = resp.get("Items", [])
        if not items:
            return {"statusCode": 404, "body": json.dumps({"error": "Métrica no encontrada para el pedido"})}

        id_metric = items[0]["id_metric"]
        analytics_table.update_item(
            Key={"id_metric": id_metric},
            UpdateExpression="SET #s=:s, fin=:f",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "cancelado", ":f": now}
        )

        return {"statusCode": 200, "body": json.dumps({"message": "Métrica cancelada", "id_order": order_id})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

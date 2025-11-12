import json, boto3, os
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["KITCHEN_TABLE"])

def handler(event, context):
    try:
        headers = event.get("headers", {}) or {}
        qs = event.get("queryStringParameters") or {}
        tenant_id = headers.get("X-Tenant-Id") or headers.get("x-tenant-id") or qs.get("tenant_id") or "default"

        resp = table.scan(
            FilterExpression=Attr("status").is_in(["recibido", "en_preparacion"]) & Attr("tenant_id").eq(tenant_id)
        )
        items = resp.get("Items", [])
        # Ordenar por created_at o start_time ascendente
        def keyf(x):
            return (x.get("created_at") or x.get("start_time") or "")
        items.sort(key=keyf)
        return {"statusCode": 200, "body": json.dumps(items)}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
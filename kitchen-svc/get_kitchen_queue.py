import json, boto3, os
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["KITCHEN_TABLE"])

def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,GET",
        "Content-Type": "application/json",
    }

    try:
        qs = event.get("queryStringParameters") or {}
        tenant_id = headers_in.get("X-Tenant-Id") or headers_in.get("x-tenant-id") or qs.get("tenant_id") or "default"

        resp = table.scan(
            FilterExpression=Attr("status").is_in(["recibido", "en_preparacion"]) & Attr("tenant_id").eq(tenant_id)
        )
        items = resp.get("Items", [])

        def keyf(x):
            return (x.get("created_at") or x.get("start_time") or "")
        items.sort(key=keyf)

        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(items)}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
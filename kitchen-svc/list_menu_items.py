import json, boto3, os
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["MENU_TABLE"])


def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,GET",
        "Content-Type": "application/json",
    }

    try:
        tenant_id = headers_in.get("X-Tenant-Id") or headers_in.get("x-tenant-id")

        if not tenant_id:
            qs = event.get("queryStringParameters") or {}
            tenant_id = qs.get("tenant_id")

        if not tenant_id:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "tenant_id requerido"})}

        resp = table.query(
            KeyConditionExpression=Key("tenant_id").eq(tenant_id)
        )
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(resp.get("Items", []))}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
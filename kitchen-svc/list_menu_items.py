import json, boto3, os
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["MENU_TABLE"])


def _convert_decimals(obj):
    if isinstance(obj, list):
        return [_convert_decimals(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        # Convert DynamoDB Decimal to float for JSON serialization
        return float(obj)
    return obj


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
        items = resp.get("Items", [])
        safe_items = _convert_decimals(items)
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(safe_items)}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
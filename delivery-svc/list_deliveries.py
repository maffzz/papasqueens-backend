import json, os
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["DELIVERY_TABLE"])


def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,GET",
        "Content-Type": "application/json",
    }

    try:
        params = (event.get("queryStringParameters") or {})
        tenant_id = params.get("tenant_id") or headers_in.get("X-Tenant-Id") or headers_in.get("x-tenant-id")
        status = params.get("status") if params else None
        next_token = params.get("next_token") if params else None

        if not tenant_id:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "tenant_id requerido"})}

        scan_expr = Attr("tenant_id").eq(tenant_id)
        if status:
            scan_expr = scan_expr & Attr("status").eq(status)

        scan_kwargs = {"FilterExpression": scan_expr}
        if next_token:
            scan_kwargs["ExclusiveStartKey"] = json.loads(next_token)

        resp = table.scan(**scan_kwargs)
        items = resp.get("Items", [])
        lek = resp.get("LastEvaluatedKey")

        result = {"items": items}
        if lek:
            result["next_token"] = json.dumps(lek)

        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps(result),
        }
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}

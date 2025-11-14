import json, os
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["DELIVERY_TABLE"])


def handler(event, context):
    try:
        headers = event.get("headers", {}) or {}
        params = (event.get("queryStringParameters") or {})
        tenant_id = params.get("tenant_id") or headers.get("X-Tenant-Id") or headers.get("x-tenant-id")
        status = params.get("status") if params else None
        next_token = params.get("next_token") if params else None

        if not tenant_id:
            return {"statusCode": 400, "body": json.dumps({"error": "tenant_id requerido"})}

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
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result),
        }
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

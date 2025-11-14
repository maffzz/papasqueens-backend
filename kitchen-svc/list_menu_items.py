import json, boto3, os
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["MENU_TABLE"])


def handler(event, context):
    try:
        headers = event.get("headers", {}) or {}
        tenant_id = headers.get("X-Tenant-Id") or headers.get("x-tenant-id")

        if not tenant_id:
            qs = event.get("queryStringParameters") or {}
            tenant_id = qs.get("tenant_id")

        if not tenant_id:
            return {"statusCode": 400, "body": json.dumps({"error": "tenant_id requerido"})}

        resp = table.query(
            KeyConditionExpression=Key("tenant_id").eq(tenant_id)
        )
        return {"statusCode": 200, "body": json.dumps(resp.get("Items", []))}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
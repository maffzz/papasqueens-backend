import json, boto3, os
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
staff_table = dynamo.Table(os.environ["STAFF_TABLE"])

def handler(event, context):
    try:
        headers = event.get("headers", {}) or {}
        qs = event.get("queryStringParameters") or {}
        tenant_id = qs.get("tenant_id") or headers.get("X-Tenant-Id") or headers.get("x-tenant-id")

        if not tenant_id:
            return {"statusCode": 400, "body": json.dumps({"error": "tenant_id requerido"})}

        resp = staff_table.scan(
            FilterExpression=Attr("tenant_id").eq(tenant_id) & Attr("role").eq("repartidor")
        )
        return {"statusCode": 200, "body": json.dumps(resp.get("Items", []))}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
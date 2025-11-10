import json, boto3, os
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
staff_table = dynamo.Table(os.environ["STAFF_TABLE"])

def handler(event, context):
    try:
        headers = event.get("headers", {})
        user_type = headers.get("X-User-Type") or headers.get("x-user-type")
        if not user_type:
            qs = event.get("queryStringParameters") or {}
            user_type = qs.get("user_type")
        if user_type != "staff":
            return {"statusCode": 403, "body": json.dumps({"error": "Forbidden"})}

        tenant_id = event["queryStringParameters"]["tenant_id"]
        resp = staff_table.scan(
            FilterExpression=Attr("tenant_id").eq(tenant_id) & Attr("role").eq("repartidor")
        )
        return {"statusCode": 200, "body": json.dumps(resp.get("Items", []))}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
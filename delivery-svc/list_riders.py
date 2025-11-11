import json, boto3, os
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from validate import require_roles

dynamo = boto3.resource("dynamodb")
staff_table = dynamo.Table(os.environ["STAFF_TABLE"])

def handler(event, context):
    try:
        _ = require_roles(event, {"staff"})

        tenant_id = event["queryStringParameters"]["tenant_id"]
        resp = staff_table.scan(
            FilterExpression=Attr("tenant_id").eq(tenant_id) & Attr("role").eq("repartidor")
        )
        return {"statusCode": 200, "body": json.dumps(resp.get("Items", []))}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
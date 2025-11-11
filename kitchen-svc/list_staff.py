import json, boto3, os
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from validate import require_roles

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["STAFF_TABLE"])

def handler(event, context):
    try:
        _ = require_roles(event, {"staff"})

        tenant_id = event["queryStringParameters"]["tenant_id"]
        resp = table.query(
            IndexName="TenantIndex",
            KeyConditionExpression=Key("tenant_id").eq(tenant_id)
        )
        return {"statusCode": 200, "body": json.dumps(resp.get("Items", []))}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
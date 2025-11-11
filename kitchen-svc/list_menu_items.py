import json, boto3, os
from botocore.exceptions import ClientError
from validate import require_roles

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["MENU_TABLE"])

def handler(event, context):
    try:
        _ = require_roles(event, {"staff"})

        resp = table.scan()
        return {"statusCode": 200, "body": json.dumps(resp.get("Items", []))}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
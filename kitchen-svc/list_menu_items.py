import json, boto3, os
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["MENU_TABLE"])

def handler(event, context):
    try:
        headers = event.get("headers", {})
        user_type = headers.get("X-User-Type") or headers.get("x-user-type")
        if not user_type:
            qs = event.get("queryStringParameters") or {}
            user_type = qs.get("user_type")
        if user_type != "staff":
            return {"statusCode": 403, "body": json.dumps({"error": "Forbidden"})}

        resp = table.scan()
        return {"statusCode": 200, "body": json.dumps(resp.get("Items", []))}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
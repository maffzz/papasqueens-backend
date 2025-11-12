import json, os
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def handler(event, context):
    try:
        params = (event.get("queryStringParameters") or {})
        status = params.get("status") if params else None
        next_token = params.get("next_token") if params else None

        scan_kwargs = {}
        if status:
            scan_kwargs["FilterExpression"] = Attr("status").eq(status)
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

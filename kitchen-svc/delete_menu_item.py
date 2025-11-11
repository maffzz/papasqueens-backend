import json, boto3, os
from botocore.exceptions import ClientError
from validate import require_roles

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["MENU_TABLE"])

def handler(event, context):
    try:
        _ = require_roles(event, {"staff"})

        id_producto = event["pathParameters"]["id_producto"]
        table.update_item(
            Key={"id_producto": id_producto},
            UpdateExpression="SET available = :a",
            ExpressionAttributeValues={":a": False}
        )
        return {"statusCode": 200, "body": json.dumps({"message": "Producto desactivado"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
import json, boto3, os
from common.jwt_utils import verify_jwt
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["MENU_TABLE"])

def handler(event, context):
    try:
        # Auth: require staff admin
        headers = event.get("headers", {}) or {}
        authz = headers.get("Authorization") or headers.get("authorization")
        if not authz or not authz.lower().startswith("bearer "):
            return {"statusCode": 401, "body": json.dumps({"error": "No autorizado"})}
        token = authz.split(" ", 1)[1].strip()
        claims = verify_jwt(token) or {}
        if (claims.get("type") != "staff") or (claims.get("role") != "admin"):
            return {"statusCode": 403, "body": json.dumps({"error": "Requiere rol admin"})}

        id_producto = event["pathParameters"]["id_producto"]
        table.update_item(
            Key={"id_producto": id_producto},
            UpdateExpression="SET available = :a",
            ExpressionAttributeValues={":a": False}
        )
        return {"statusCode": 200, "body": json.dumps({"message": "Producto desactivado"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
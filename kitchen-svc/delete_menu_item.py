import json, boto3, os
from common.jwt_utils import verify_jwt
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["MENU_TABLE"])


def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,DELETE",
        "Content-Type": "application/json",
    }

    try:
        # Auth: require staff admin
        headers = event.get("headers", {}) or {}
        authz = headers.get("Authorization") or headers.get("authorization")
        if not authz or not authz.lower().startswith("bearer "):
            return {"statusCode": 401, "headers": cors_headers, "body": json.dumps({"error": "No autorizado"})}
        token = authz.split(" ", 1)[1].strip()
        claims = verify_jwt(token) or {}
        if (claims.get("type") != "staff") or (claims.get("role") != "admin"):
            return {"statusCode": 403, "headers": cors_headers, "body": json.dumps({"error": "Requiere rol admin"})}

        id_producto = event["pathParameters"]["id_producto"]

        headers = event.get("headers", {}) or {}
        tenant_id = headers.get("X-Tenant-Id") or headers.get("x-tenant-id")

        if not tenant_id:
            qs = event.get("queryStringParameters") or {}
            tenant_id = qs.get("tenant_id")

        if not tenant_id:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "tenant_id requerido"})}

        table.update_item(
            Key={"tenant_id": tenant_id, "id_producto": id_producto},
            UpdateExpression="SET available = :a",
            ExpressionAttributeValues={":a": False}
        )
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": "Producto desactivado"})}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
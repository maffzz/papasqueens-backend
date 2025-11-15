import json, boto3, os
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
staff_table = dynamo.Table(os.environ["STAFF_TABLE"])


def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,PATCH",
        "Content-Type": "application/json",
    }

    try:
        id_staff = event["pathParameters"]["id_staff"]
        body = json.loads(event.get("body", "{}"))
        headers = event.get("headers", {}) or {}
        qs = event.get("queryStringParameters") or {}
        tenant_id = body.get("tenant_id") or headers.get("X-Tenant-Id") or headers.get("x-tenant-id") or qs.get("tenant_id")

        status = body.get("status")
        if status not in ["activo", "inactivo"]:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "Estado inválido"})}
        if not tenant_id:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "tenant_id requerido"})}

        staff_table.update_item(
            Key={"tenant_id": tenant_id, "id_staff": id_staff},
            UpdateExpression="SET #s=:s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": status}
        )
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": "Estado de repartidor actualizado"})}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
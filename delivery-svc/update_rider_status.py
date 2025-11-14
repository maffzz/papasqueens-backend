import json, boto3, os
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
staff_table = dynamo.Table(os.environ["STAFF_TABLE"])


def handler(event, context):
    try:
        id_staff = event["pathParameters"]["id_staff"]
        body = json.loads(event.get("body", "{}"))
        headers = event.get("headers", {}) or {}
        qs = event.get("queryStringParameters") or {}
        tenant_id = body.get("tenant_id") or headers.get("X-Tenant-Id") or headers.get("x-tenant-id") or qs.get("tenant_id")

        status = body.get("status")
        if status not in ["activo", "inactivo"]:
            return {"statusCode": 400, "body": json.dumps({"error": "Estado inválido"})}
        if not tenant_id:
            return {"statusCode": 400, "body": json.dumps({"error": "tenant_id requerido"})}

        staff_table.update_item(
            Key={"tenant_id": tenant_id, "id_staff": id_staff},
            UpdateExpression="SET #s=:s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": status}
        )
        return {"statusCode": 200, "body": json.dumps({"message": "Estado de repartidor actualizado"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
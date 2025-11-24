import json, boto3, os, datetime, uuid
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
analytics_table = dynamo.Table(os.environ["ANALYTICS_TABLE"])

def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST",
        "Content-Type": "application/json",
    }

    try:
        detail = event.get("detail", {})
        staff_id = detail.get("id_staff")
        tenant_id = detail.get("tenant_id", "default")
        role = detail.get("role", "desconocido")
        now = datetime.datetime.utcnow().isoformat()

        metric_item = {
            "id_metric": str(uuid.uuid4()),
            "id_order": None,
            "id_staff": staff_id,
            "status": "activo",
            "inicio": now,
            "fin": None,
            "tiempo_total": None,
            "tenant_id": tenant_id,
            "role": role
        }

        analytics_table.put_item(Item=metric_item)
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": "Métrica de personal actualizada"})}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
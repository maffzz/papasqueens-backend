import json, os
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["DELIVERY_TABLE"])


def to_serializable(obj):
    """Convierte Decimals y estructuras anidadas a tipos JSON-serializables."""
    if isinstance(obj, Decimal):
        try:
            return float(obj)
        except Exception:
            return int(obj)
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_serializable(v) for v in obj]
    return obj


def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,GET",
        "Content-Type": "application/json",
    }

    try:
        params = (event.get("queryStringParameters") or {})
        tenant_id = params.get("tenant_id") or headers_in.get("X-Tenant-Id") or headers_in.get("x-tenant-id")
        status = params.get("status") if params else None
        next_token = params.get("next_token") if params else None

        if not tenant_id:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "tenant_id requerido"})}

        scan_expr = Attr("tenant_id").eq(tenant_id)
        if status:
            scan_expr = scan_expr & Attr("status").eq(status)

        scan_kwargs = {"FilterExpression": scan_expr}
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
            "headers": cors_headers,
            "body": json.dumps(to_serializable(result)),
        }
    except (ClientError, Exception) as e:
        # Cualquier error aquí debe seguir devolviendo cabeceras CORS para que el front pueda verlo
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": str(e)}),
        }

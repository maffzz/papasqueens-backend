import json, boto3, os
from decimal import Decimal
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
kitchen_table = dynamo.Table(os.environ["KITCHEN_TABLE"])
orders_table = dynamo.Table(os.environ["ORDERS_TABLE"])


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
        qs = event.get("queryStringParameters") or {}
        tenant_id = headers_in.get("X-Tenant-Id") or headers_in.get("x-tenant-id") or qs.get("tenant_id") or "default"

        resp = kitchen_table.scan(
            FilterExpression=Attr("status").is_in(["recibido", "en_preparacion"]) & Attr("tenant_id").eq(tenant_id)
        )
        items = resp.get("Items", [])

        # Enriquecer con info de cliente desde Orders si falta
        for it in items:
            has_name = bool(it.get("customer_name") or it.get("customer"))
            has_addr = bool(it.get("delivery_address"))
            if has_name and has_addr:
                continue

            order_id = it.get("order_id") or it.get("id_order") or it.get("id")
            if not order_id:
                continue
            try:
                o_resp = orders_table.get_item(Key={"tenant_id": tenant_id, "id_order": order_id})
                o_item = o_resp.get("Item") or {}
            except Exception:
                o_item = {}

            if o_item:
                if not has_name:
                    name = o_item.get("customer_name") or o_item.get("customer") or o_item.get("name")
                    if name:
                        it["customer_name"] = name
                if not has_addr:
                    addr = o_item.get("delivery_address") or o_item.get("address") or o_item.get("direccion")
                    if addr:
                        it["delivery_address"] = addr

        def keyf(x):
            return (x.get("created_at") or x.get("start_time") or "")
        items.sort(key=keyf)

        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(to_serializable(items))}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
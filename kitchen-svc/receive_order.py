import json, boto3, os, datetime
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
kitchen_table = dynamo.Table(os.environ["KITCHEN_TABLE"])
orders_table = dynamo.Table(os.environ["ORDERS_TABLE"])

def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST",
        "Content-Type": "application/json",
    }

    try:
        # evento desde EventBridge
        detail = event.get("detail", {})
        order_id = detail["id_order"]
        tenant_id = detail["tenant_id"]
        now = datetime.datetime.utcnow().isoformat()

        # Enriquecer con datos del pedido para que cocina vea info del cliente
        try:
            order_resp = orders_table.get_item(Key={"tenant_id": tenant_id, "id_order": order_id})
            order_item = order_resp.get("Item") or {}
        except Exception:
            order_item = {}

        item = {
            "order_id": order_id,
            "tenant_id": tenant_id,
            "list_id_staff": [],
            "status": "recibido",
            "start_time": None,
            "end_time": None,
            "updated_at": now,
        }

        # Copiar algunos campos útiles para la UI de cocina
        if order_item:
            if order_item.get("customer_name"):
                item["customer_name"] = order_item["customer_name"]
            if order_item.get("delivery_address"):
                item["delivery_address"] = order_item["delivery_address"]
            if order_item.get("id_customer"):
                item["id_customer"] = order_item["id_customer"]

        kitchen_table.put_item(Item=item)
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": "Pedido recibido en cocina", "order_id": order_id})}

    except KeyError as e:
        return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": f"Campo faltante en evento: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
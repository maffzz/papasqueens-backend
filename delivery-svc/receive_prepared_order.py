import json, boto3, os, uuid, datetime
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
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
        detail = event.get("detail", {})
        order_id = detail["order_id"]
        tenant_id = detail.get("tenant_id", "default")
        id_delivery = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()

        try:
            order_resp = orders_table.get_item(Key={"tenant_id": tenant_id, "id_order": order_id})
            order_item = order_resp.get("Item", {})
        except ClientError:
            order_item = {}

        direccion = order_item.get("delivery_address") or order_item.get("address") or order_item.get("direccion") or detail.get("direccion") or "por_definir"
        customer_name = order_item.get("customer_name")
        dest_lat = order_item.get("dest_lat")
        dest_lng = order_item.get("dest_lng")

        item = {
            "id_delivery": id_delivery,
            "id_order": order_id,
            "id_staff": None,
            "direccion": direccion,
            "customer_name": customer_name,
            "tiempo_salida": None,
            "tiempo_llegada": None,
            "status": "listo_para_entrega",
            "tenant_id": tenant_id,
            "created_at": now,
            "updated_at": now,
        }

        if dest_lat is not None and dest_lng is not None:
            item["dest_lat"] = dest_lat
            item["dest_lng"] = dest_lng

        delivery_table.put_item(Item=item)
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": "Entrega creada", "id_delivery": id_delivery})}
    except KeyError as e:
        return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": f"Campo faltante: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
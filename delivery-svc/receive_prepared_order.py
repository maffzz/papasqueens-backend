import json, boto3, os, uuid, datetime
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
orders_table = dynamo.Table(os.environ["ORDERS_TABLE"])

def handler(event, context):
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

        delivery_table.put_item(Item=item)
        return {"statusCode": 200, "body": json.dumps({"message": "Entrega creada", "id_delivery": id_delivery})}
    except KeyError as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"Campo faltante: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
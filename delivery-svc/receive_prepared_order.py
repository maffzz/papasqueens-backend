import json, boto3, os, uuid, datetime
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def handler(event, context):
    try:
        detail = event.get("detail", {})
        order_id = detail["order_id"]
        tenant_id = detail.get("tenant_id", "default")
        id_delivery = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()

        item = {
            "id_delivery": id_delivery,
            "id_order": order_id,
            "id_staff": None,
            "direccion": detail.get("direccion", "por_definir"),
            "tiempo_salida": None,
            "tiempo_llegada": None,
            # Estado inicial: listo para que alguien de delivery lo tome/asigne
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
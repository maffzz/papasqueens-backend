import json, uuid, os, datetime
import boto3
from botocore.exceptions import ClientError
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import log_info, log_error
from validate import require_roles

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["ORDERS_TABLE"])
eb = boto3.client("events")


def handler(event, context):
    try:
        log_info("Iniciando creación de pedido", event, context)
        
        claims = require_roles(event, {"cliente"})
        body = json.loads(event.get("body", "{}"))
        tenant_id = body["tenant_id"]
        id_customer = body["id_customer"]
        list_id_products = body["list_id_products"]

        if not list_id_products:
            log_error("Intento de crear pedido sin productos", None, event, context, {"id_customer": id_customer})
            return {"statusCode": 400, "body": json.dumps({"error": "Debe incluir productos"})}
        
        user_id = claims.get("sub")
        if id_customer != user_id:
            log_error("Cliente intenta crear pedido para otro cliente", None, event, context, {
                "id_customer_requested": id_customer,
                "id_customer_authenticated": user_id
            })
            return {"statusCode": 403, "body": json.dumps({"error": "Solo puedes crear pedidos para tu propia cuenta"})}

        order_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()

        item = {
            "id_order": order_id,
            "tenant_id": tenant_id,
            "id_customer": id_customer,
            "list_id_products": list_id_products,
            "status": "recibido",
            "created_at": now,
            "updated_at": now
        }

        log_info("Guardando pedido en DynamoDB", event, context, {"order_id": order_id, "tenant_id": tenant_id})
        table.put_item(Item=item)

        log_info("Enviando evento Order.Created", event, context, {"order_id": order_id})
        eb.put_events(
            Entries=[
                {
                    "Source": "orders-svc",
                    "DetailType": "Order.Created",
                    "Detail": json.dumps({"id_order": order_id, "tenant_id": tenant_id}),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )

        log_info("Pedido creado exitosamente", event, context, {"order_id": order_id})
        return {"statusCode": 201, "body": json.dumps({"id_order": order_id, "status": "recibido"})}

    except KeyError as e:
        log_error(f"Campo faltante en request: {e}", e, event, context)
        return {"statusCode": 400, "body": json.dumps({"error": f"Campo faltante: {e}"})}
    except ClientError as e:
        log_error("Error de DynamoDB al crear pedido", e, event, context)
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    except Exception as e:
        log_error("Error inesperado al crear pedido", e, event, context)
        return {"statusCode": 500, "body": json.dumps({"error": "Error interno del servidor"})}
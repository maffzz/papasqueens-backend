import json, uuid, os, datetime
import boto3
from botocore.exceptions import ClientError
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.logger import log_info, log_error

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["ORDERS_TABLE"])
eb = boto3.client("events")

def get_user_info(event):
    """Extrae información del usuario desde headers"""
    headers = event.get("headers", {})
    user_type = headers.get("X-User-Type") or headers.get("x-user-type")
    user_id = headers.get("X-User-Id") or headers.get("x-user-id")
    
    if not user_type:
        query_params = event.get("queryStringParameters") or {}
        user_type = query_params.get("user_type")
        user_id = query_params.get("user_id")
    
    return {
        "type": user_type,
        "id": user_id
    }

def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST",
        "Content-Type": "application/json",
    }

    try:
        log_info("Iniciando creación de pedido", event, context)
        
        user_info = get_user_info(event)
        body = json.loads(event.get("body", "{}"))
        tenant_id = body["tenant_id"]
        id_customer = body["id_customer"]
        list_id_products = body["list_id_products"]
        items = body.get("items") or []

        if not list_id_products:
            log_error("Intento de crear pedido sin productos", None, event, context, {"id_customer": id_customer})
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "Debe incluir productos"})}
        
        if user_info.get("type") == "customer":
            if id_customer != user_info.get("id"):
                log_error("Cliente intenta crear pedido para otro cliente", None, event, context, {
                    "id_customer_requested": id_customer,
                    "id_customer_authenticated": user_info.get("id")
                })
                return {"statusCode": 403, "headers": cors_headers, "body": json.dumps({"error": "Solo puedes crear pedidos para tu propia cuenta"})}

        order_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()

        item = {
            "id_order": order_id,
            "tenant_id": tenant_id,
            "id_customer": id_customer,
            "list_id_products": list_id_products,
            "status": "recibido",
            "created_at": now,
            "updated_at": now,
        }
        if items:
            item["items"] = items

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

        # Iniciar Step Functions (best-effort): por ARN en env o buscando por nombre
        try:
            sfn = boto3.client('stepfunctions')
            sfn_arn = os.environ.get('ORDER_SFN_ARN')
            if not sfn_arn:
                target_name = os.environ.get('ORDER_SFN_NAME', 'papasqueens-order-workflow')
                paginator = sfn.get_paginator('list_state_machines')
                for page in paginator.paginate():
                    for sm in page.get('stateMachines', []):
                        if sm.get('name') == target_name:
                            sfn_arn = sm.get('stateMachineArn')
                            break
                    if sfn_arn:
                        break
            if sfn_arn:
                sfn_input = {"id_order": order_id, "tenant_id": tenant_id}
                resp = sfn.start_execution(stateMachineArn=sfn_arn, input=json.dumps(sfn_input))
                log_info("State Machine iniciada", event, context, {"executionArn": resp.get('executionArn')})
            else:
                log_error("State Machine no encontrada para iniciar", None, event, context, {"hint": "Defina ORDER_SFN_ARN o ORDER_SFN_NAME"})
        except Exception as e:
            log_error("Fallo al iniciar Step Functions", e, event, context, {"order_id": order_id})

        log_info("Pedido creado exitosamente", event, context, {"order_id": order_id})
        return {"statusCode": 201, "headers": cors_headers, "body": json.dumps({"id_order": order_id, "status": "recibido"})}

    except KeyError as e:
        log_error(f"Campo faltante en request: {e}", e, event, context)
        return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": f"Campo faltante: {e}"})}
    except ClientError as e:
        log_error("Error de DynamoDB al crear pedido", e, event, context)
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
    except Exception as e:
        log_error("Error inesperado al crear pedido", e, event, context)
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": "Error interno del servidor"})}
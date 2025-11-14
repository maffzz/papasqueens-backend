import json, os, boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr, Key

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["ORDERS_TABLE"])
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def get_user_info(event):
    headers = event.get("headers", {})
    user_email = headers.get("X-User-Email") or headers.get("x-user-email")
    user_type = headers.get("X-User-Type") or headers.get("x-user-type")
    user_id = headers.get("X-User-Id") or headers.get("x-user-id")
    
    if not user_email:
        query_params = event.get("queryStringParameters") or {}
        user_email = query_params.get("user_email")
        user_type = query_params.get("user_type")
        user_id = query_params.get("user_id")
    
    return {
        "email": user_email,
        "type": user_type,
        "id": user_id
    }

def get_tenant_id(event):
    headers = event.get("headers", {}) or {}
    tenant_id = headers.get("X-Tenant-Id") or headers.get("x-tenant-id")
    if not tenant_id:
        qs = event.get("queryStringParameters") or {}
        tenant_id = qs.get("tenant_id")
    return tenant_id

def check_authorization(user_info, order_item):
    """Verifica si el usuario tiene permiso para acceder al pedido"""
    if not user_info.get("type"):
        return False, "Información de usuario no proporcionada"
    
    if user_info.get("type") == "staff":
        return True, None
    
    if user_info.get("type") == "customer":
        order_customer_id = order_item.get("id_customer")
        user_customer_id = user_info.get("id")
        
        if order_customer_id == user_customer_id:
            return True, None
        else:
            return False, "No tienes permiso para acceder a este pedido"
    
    return False, "Tipo de usuario no válido"

def handler(event, context):
    order_id = event["pathParameters"]["order_id"]
    try:
        user_info = get_user_info(event)
        tenant_id = get_tenant_id(event)
        if not tenant_id:
            return {"statusCode": 400, "body": json.dumps({"error": "tenant_id requerido"})}
        
        resp = table.get_item(Key={"tenant_id": tenant_id, "id_order": order_id})
        item = resp.get("Item")
        if not item:
            return {"statusCode": 404, "body": json.dumps({"error": "Pedido no encontrado"})}
        
        authorized, error_msg = check_authorization(user_info, item)
        if not authorized:
            return {"statusCode": 403, "body": json.dumps({"error": error_msg})}
        
        delivery_info = None
        order_status = item.get("status", "")
        
        if order_status in ["en_camino", "listo_para_entrega", "entregado"]:
            delivery_resp = delivery_table.query(
                IndexName="OrderIndex",
                KeyConditionExpression=Key("id_order").eq(order_id)
            )
            delivery_items = [x for x in delivery_resp.get("Items", []) if x.get("tenant_id") == tenant_id]
            
            if delivery_items:
                delivery = delivery_items[0]
                delivery_info = {
                    "id_delivery": delivery.get("id_delivery"),
                    "status": delivery.get("status"),
                    "direccion": delivery.get("direccion"),
                    "id_staff": delivery.get("id_staff"),
                    "tiempo_salida": delivery.get("tiempo_salida"),
                    "tiempo_llegada": delivery.get("tiempo_llegada")
                }
                
                # Incluir ubicación GPS si existe (para tracking en mapa)
                last_location = delivery.get("last_location")
                if last_location:
                    delivery_info["location"] = last_location
                elif delivery.get("lat") and delivery.get("lon"):
                    # Formato alternativo de coordenadas
                    delivery_info["location"] = {
                        "lat": delivery.get("lat"),
                        "lon": delivery.get("lon")
                    }
        
        response_data = {
            "id_order": order_id,
            "status": order_status,
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at")
        }
        
        if delivery_info:
            response_data["delivery"] = delivery_info
        
        return {"statusCode": 200, "body": json.dumps(response_data)}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
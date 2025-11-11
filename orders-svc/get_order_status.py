import json, os, boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr
from validate import require_roles

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["ORDERS_TABLE"])
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def get_user_info(event):
    claims = require_roles(event, {"cliente"})
    return {"email": claims.get("email"), "type": "cliente", "id": claims.get("sub")}

def check_authorization(user_info, order_item):
    if not user_info.get("type"):
        return False, "Información de usuario no proporcionada"
    
    if user_info.get("type") == "staff":
        return False, "Solo clientes pueden consultar el estado de su pedido"
    
    if user_info.get("type") == "cliente":
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
        
        resp = table.get_item(Key={"id_order": order_id})
        item = resp.get("Item")
        if not item:
            return {"statusCode": 404, "body": json.dumps({"error": "Pedido no encontrado"})}
        
        authorized, error_msg = check_authorization(user_info, item)
        if not authorized:
            return {"statusCode": 403, "body": json.dumps({"error": error_msg})}
        
        delivery_info = None
        order_status = item.get("status", "")
        
        if order_status in ["en_camino", "listo_para_entrega", "entregado"]:
            delivery_resp = delivery_table.scan(
                FilterExpression=Attr("id_order").eq(order_id)
            )
            delivery_items = delivery_resp.get("Items", [])
            
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
                
                last_location = delivery.get("last_location")
                if last_location:
                    delivery_info["location"] = last_location
                elif delivery.get("lat") and delivery.get("lon"):
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
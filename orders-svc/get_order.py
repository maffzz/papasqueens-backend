import json, os, boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from common.jwt_utils import verify_jwt

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["ORDERS_TABLE"])
users_table = dynamo.Table(os.environ.get("USERS_TABLE", "papasqueens-users"))
kitchen_table = dynamo.Table(os.environ["KITCHEN_TABLE"])
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def get_user_info(event):
    """Extrae información del usuario desde headers o query params"""
    headers = event.get("headers", {})
    user_email = headers.get("X-User-Email") or headers.get("x-user-email")
    user_type = headers.get("X-User-Type") or headers.get("x-user-type")
    user_id = headers.get("X-User-Id") or headers.get("x-user-id")
    if not (user_email and user_type and user_id):
        # Intentar JWT en Authorization: Bearer <token>
        authz = headers.get("Authorization") or headers.get("authorization")
        if authz and authz.lower().startswith("bearer "):
            token = authz.split(" ", 1)[1].strip()
            payload = verify_jwt(token) or {}
            user_email = user_email or payload.get("email")
            user_type = (user_type or payload.get("type"))
            user_id = user_id or payload.get("sub")
    
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

def check_authorization(user_info, order_item, action="read"):
    """Verifica si el usuario tiene permiso para acceder al pedido"""
    if not user_info.get("type"):
        return False, "Información de usuario no proporcionada"
    
    utype = (user_info.get("type") or '').lower()
    if utype == "staff":
        return True, None
    
    if utype in ("customer", "cliente"):
        order_customer_id = order_item.get("id_customer")
        user_customer_id = user_info.get("id")
        
        if order_customer_id == user_customer_id:
            return True, None
        else:
            return False, "No tienes permiso para acceder a este pedido"
    
    return False, "Tipo de usuario no válido"

def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,GET",
        "Content-Type": "application/json",
    }

    order_id = event["pathParameters"]["order_id"]
    try:
        user_info = get_user_info(event)
        tenant_id = get_tenant_id(event)
        if not tenant_id:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "tenant_id requerido"})}
        
        response = table.get_item(Key={"tenant_id": tenant_id, "id_order": order_id})
        item = response.get("Item")
        if not item:
            return {"statusCode": 404, "headers": cors_headers, "body": json.dumps({"error": "Pedido no encontrado"})}
        
        authorized, error_msg = check_authorization(user_info, item)
        if not authorized:
            return {"statusCode": 403, "headers": cors_headers, "body": json.dumps({"error": error_msg})}
        
        # Construir historial a partir de Kitchen y Delivery
        history = []
        if item.get("created_at"):
            history.append({"step": "recibido", "at": item.get("created_at"), "by": item.get("id_customer")})

        # Kitchen (clave: tenant_id + order_id)
        try:
            k_resp = kitchen_table.get_item(Key={"tenant_id": tenant_id, "order_id": order_id})
            k = k_resp.get("Item") or {}
        except Exception:
            k = {}
        if k:
            if k.get("accepted_at"):
                history.append({"step": "aceptado", "at": k.get("accepted_at"), "by": k.get("accepted_by")})
            if k.get("packed_at") or k.get("end_time"):
                history.append({"step": "empacado", "at": k.get("packed_at") or k.get("end_time"), "by": k.get("packed_by")})

        # Delivery (buscar por id_order usando índice y filtrando por tenant)
        try:
            d_query = delivery_table.query(
                IndexName="OrderIndex",
                KeyConditionExpression=Attr("id_order").eq(order_id)
            )
            d_items = [x for x in d_query.get("Items", []) if x.get("tenant_id") == tenant_id]
            d = d_items[0] if d_items else {}
        except Exception:
            d = {}
        if d:
            if d.get("assigned_at"):
                history.append({"step": "asignado", "at": d.get("assigned_at"), "by": d.get("id_staff")})
            if d.get("tiempo_salida"):
                history.append({"step": "salida_reparto", "at": d.get("tiempo_salida"), "by": d.get("handoff_by")})
            if d.get("tiempo_llegada"):
                history.append({"step": "entregado", "at": d.get("tiempo_llegada"), "by": d.get("delivered_by")})

        payload = dict(item)
        payload["workflow"] = {"kitchen": k, "delivery": d}
        payload["history"] = history
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(payload)}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
import json, boto3, os
from decimal import Decimal
from boto3.dynamodb.conditions import Attr, Key
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
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,X-User-Role,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,GET",
        "Content-Type": "application/json",
    }

    try:
        qs = event.get("queryStringParameters") or {}
        tenant_id = headers_in.get("X-Tenant-Id") or headers_in.get("x-tenant-id") or qs.get("tenant_id") or "default"
        user_role = headers_in.get("X-User-Role") or headers_in.get("x-user-role") or qs.get("role")
        user_id = headers_in.get("X-User-Id") or headers_in.get("x-user-id")

        if not user_role:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "X-User-Role requerido"})}

        # Dashboard para COCINERO: pedidos pendientes de aceptar y en preparación
        if user_role == "cocinero":
            # Pedidos recibidos (pendientes de aceptar)
            pendientes = kitchen_table.scan(
                FilterExpression=Attr("status").eq("recibido") & Attr("tenant_id").eq(tenant_id)
            )
            
            # Pedidos que este cocinero está preparando
            en_preparacion = kitchen_table.scan(
                FilterExpression=Attr("status").eq("en_preparacion") 
                    & Attr("tenant_id").eq(tenant_id)
                    & Attr("accepted_by").eq(user_id)
            )
            
            # Pedidos completados por este cocinero (últimos 10)
            completados = kitchen_table.scan(
                FilterExpression=Attr("accepted_by").eq(user_id) 
                    & Attr("tenant_id").eq(tenant_id)
                    & Attr("status").is_in(["listo_para_entrega", "entregado"])
            )
            completados_items = sorted(
                completados.get("Items", []), 
                key=lambda x: x.get("packed_at") or x.get("end_time") or "", 
                reverse=True
            )[:10]

            result = {
                "role": "cocinero",
                "user_id": user_id,
                "tenant_id": tenant_id,
                "pendientes_aceptar": {
                    "count": len(pendientes.get("Items", [])),
                    "items": to_serializable(pendientes.get("Items", []))
                },
                "en_preparacion": {
                    "count": len(en_preparacion.get("Items", [])),
                    "items": to_serializable(en_preparacion.get("Items", []))
                },
                "completados_recientes": {
                    "count": len(completados_items),
                    "items": to_serializable(completados_items)
                }
            }
            return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(result)}

        # Dashboard para EMPAQUETADOR: pedidos listos para empacar
        elif user_role == "empaquetador":
            # Pedidos en preparación (listos para empacar)
            listos_empacar = kitchen_table.scan(
                FilterExpression=Attr("status").eq("en_preparacion") & Attr("tenant_id").eq(tenant_id)
            )
            
            # Pedidos empacados por este usuario
            empacados = kitchen_table.scan(
                FilterExpression=Attr("packed_by").eq(user_id) 
                    & Attr("tenant_id").eq(tenant_id)
                    & Attr("status").eq("listo_para_entrega")
            )
            empacados_items = sorted(
                empacados.get("Items", []), 
                key=lambda x: x.get("packed_at") or "", 
                reverse=True
            )[:10]

            result = {
                "role": "empaquetador",
                "user_id": user_id,
                "tenant_id": tenant_id,
                "listos_para_empacar": {
                    "count": len(listos_empacar.get("Items", [])),
                    "items": to_serializable(listos_empacar.get("Items", []))
                },
                "empacados_recientes": {
                    "count": len(empacados_items),
                    "items": to_serializable(empacados_items)
                }
            }
            return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(result)}

        # Dashboard para DELIVERY: entregas asignadas y pendientes
        elif user_role == "delivery":
            delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
            
            # Entregas asignadas a este repartidor
            mis_entregas = delivery_table.scan(
                FilterExpression=Attr("id_staff").eq(user_id) 
                    & Attr("tenant_id").eq(tenant_id)
                    & Attr("status").is_in(["asignado", "en_camino"])
            )
            
            # Entregas completadas
            completadas = delivery_table.scan(
                FilterExpression=Attr("id_staff").eq(user_id) 
                    & Attr("tenant_id").eq(tenant_id)
                    & Attr("status").eq("entregado")
            )
            completadas_items = sorted(
                completadas.get("Items", []), 
                key=lambda x: x.get("tiempo_llegada") or "", 
                reverse=True
            )[:10]

            result = {
                "role": "delivery",
                "user_id": user_id,
                "tenant_id": tenant_id,
                "entregas_activas": {
                    "count": len(mis_entregas.get("Items", [])),
                    "items": to_serializable(mis_entregas.get("Items", []))
                },
                "entregas_completadas": {
                    "count": len(completadas_items),
                    "items": to_serializable(completadas_items)
                }
            }
            return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(result)}

        # Dashboard para ADMIN: vista completa
        elif user_role == "admin":
            # Resumen general de cocina
            todos_pedidos = kitchen_table.scan(
                FilterExpression=Attr("tenant_id").eq(tenant_id)
            )
            
            por_estado = {}
            for item in todos_pedidos.get("Items", []):
                estado = item.get("status", "desconocido")
                por_estado[estado] = por_estado.get(estado, 0) + 1

            result = {
                "role": "admin",
                "user_id": user_id,
                "tenant_id": tenant_id,
                "resumen_cocina": {
                    "total": len(todos_pedidos.get("Items", [])),
                    "por_estado": por_estado
                },
                "todos_pedidos": to_serializable(todos_pedidos.get("Items", []))
            }
            return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(result)}

        else:
            return {"statusCode": 403, "headers": cors_headers, "body": json.dumps({"error": f"Rol no reconocido: {user_role}"})}

    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}

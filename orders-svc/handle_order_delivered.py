import json, os, boto3, datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["ORDERS_TABLE"])


def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST",
        "Content-Type": "application/json",
    }

    try:
        if "detail" in event:
            if isinstance(event["detail"], str):
                detail = json.loads(event["detail"])
            else:
                detail = event["detail"]
        else:
            detail = event
        
        order_id = detail.get("id_order")
        tenant_id = detail.get("tenant_id")

        if not order_id:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "id_order no proporcionado en el evento"})}

        # Si no llega tenant_id en el evento (compatibilidad hacia atrás), resolverlo buscando la orden
        if not tenant_id:
            scan_resp = table.scan(
                FilterExpression=Attr("id_order").eq(order_id)
            )
            items = scan_resp.get("Items", [])
            if not items:
                return {"statusCode": 404, "headers": cors_headers, "body": json.dumps({"error": "Pedido no encontrado"})}
            tenant_id = items[0]["tenant_id"]

        order_resp = table.get_item(Key={"tenant_id": tenant_id, "id_order": order_id})
        if not order_resp.get("Item"):
            return {"statusCode": 404, "headers": cors_headers, "body": json.dumps({"error": "Pedido no encontrado"})}
        
        now = datetime.datetime.utcnow().isoformat()
        table.update_item(
            Key={"tenant_id": tenant_id, "id_order": order_id},
            UpdateExpression="SET #s=:s, updated_at=:u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "entregado", ":u": now}
        )
        
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": "Pedido marcado como entregado", "order_id": order_id, "tenant_id": tenant_id})}
    except json.JSONDecodeError as e:
        return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": f"Error al parsear evento: {str(e)}"})}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": f"Error en base de datos: {str(e)}"})}
    except Exception as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": f"Error inesperado: {str(e)}"})}
import json, os, boto3, datetime
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["ORDERS_TABLE"])

def handler(event, context):
    try:
        if event.get("httpMethod") or event.get("headers"):
            return {"statusCode": 403, "body": json.dumps({"error": "Solo EventBridge (no HTTP)"})}

        detail_type = event.get("detail-type") or event.get("detailType")
        if detail_type and detail_type != "Order.Delivered":
            return {"statusCode": 400, "body": json.dumps({"error": "Evento no soportado"})}

        if "detail" in event:
            if isinstance(event["detail"], str):
                detail = json.loads(event["detail"])
            else:
                detail = event["detail"]
        else:
            detail = event
        
        order_id = detail.get("id_order")
        if not order_id:
            return {"statusCode": 400, "body": json.dumps({"error": "id_order no proporcionado en el evento"})}
        
        order_resp = table.get_item(Key={"id_order": order_id})
        if not order_resp.get("Item"):
            return {"statusCode": 404, "body": json.dumps({"error": "Pedido no encontrado"})}
        
        now = datetime.datetime.utcnow().isoformat()
        table.update_item(
            Key={"id_order": order_id},
            UpdateExpression="SET #s=:s, updated_at=:u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "entregado", ":u": now}
        )
        
        return {"statusCode": 200, "body": json.dumps({"message": "Pedido marcado como entregado", "order_id": order_id})}
    except json.JSONDecodeError as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"Error al parsear evento: {str(e)}"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": f"Error en base de datos: {str(e)}"})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": f"Error inesperado: {str(e)}"})}
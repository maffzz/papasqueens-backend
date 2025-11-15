import json, boto3, os, datetime
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def handler(event, context):
    """Actualiza la última ubicación GPS del repartidor para un delivery en_camino."""
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST",
        "Content-Type": "application/json",
    }

    try:
        body = json.loads(event.get("body", "{}"))
        headers = event.get("headers", {}) or {}
        qs = event.get("queryStringParameters") or {}
        id_order = body.get("id_order")
        lat = body.get("lat")
        lon = body.get("lon")
        id_staff = body.get("id_staff")
        tenant_id = body.get("tenant_id") or headers.get("X-Tenant-Id") or headers.get("x-tenant-id") or qs.get("tenant_id")

        if not id_order or lat is None or lon is None:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "Faltan campos requeridos: id_order, lat, lon"})}
        if not tenant_id:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "tenant_id requerido"})}
        
        resp = delivery_table.query(
            IndexName="OrderIndex",
            KeyConditionExpression=Key("id_order").eq(id_order)
        )
        items = [x for x in resp.get("Items", []) if x.get("tenant_id") == tenant_id]
        
        if not items:
            return {"statusCode": 404, "headers": cors_headers, "body": json.dumps({"error": "No se encontró la entrega"})}
        
        delivery = items[0]
        delivery_status = delivery.get("status", "")
        
        if delivery_status != "en_camino":
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": f"El delivery no está en_camino (estado actual: {delivery_status})"})}
        
        if id_staff and delivery.get("id_staff") != id_staff:
            return {"statusCode": 403, "headers": cors_headers, "body": json.dumps({"error": "No tienes permiso para actualizar esta entrega"})}
        
        id_delivery = delivery["id_delivery"]
        now = datetime.datetime.utcnow().isoformat()
        
        last_location = {
            "lat": float(lat),
            "lon": float(lon),
            "timestamp": now
        }
        
        delivery_table.update_item(
            Key={"tenant_id": tenant_id, "id_delivery": id_delivery},
            UpdateExpression="SET last_location = :loc, updated_at = :u",
            ExpressionAttributeValues={
                ":loc": last_location,
                ":u": now
            }
        )
        
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps({
                "message": "Ubicación actualizada",
                "id_delivery": id_delivery,
                "location": last_location
            })
        }
    except ValueError as e:
        return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": f"Coordenadas inválidas: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
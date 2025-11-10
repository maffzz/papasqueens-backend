import json, boto3, os, datetime
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def handler(event, context):
    """
    Actualiza la última ubicación GPS del repartidor para un delivery en_camino.
    Esta función debe ser llamada periódicamente desde la app móvil del repartidor.
    """
    try:
        body = json.loads(event.get("body", "{}"))
        id_order = body.get("id_order")
        lat = body.get("lat")
        lon = body.get("lon")
        id_staff = body.get("id_staff")

        if not id_order or lat is None or lon is None:
            return {"statusCode": 400, "body": json.dumps({"error": "Faltan campos requeridos: id_order, lat, lon"})}
        
        resp = delivery_table.scan(FilterExpression=Attr("id_order").eq(id_order))
        items = resp.get("Items", [])
        
        if not items:
            return {"statusCode": 404, "body": json.dumps({"error": "No se encontró la entrega"})}
        
        delivery = items[0]
        delivery_status = delivery.get("status", "")
        
        if delivery_status != "en_camino":
            return {"statusCode": 400, "body": json.dumps({"error": f"El delivery no está en_camino (estado actual: {delivery_status})"})}
        
        if id_staff and delivery.get("id_staff") != id_staff:
            return {"statusCode": 403, "body": json.dumps({"error": "No tienes permiso para actualizar esta entrega"})}
        
        id_delivery = delivery["id_delivery"]
        now = datetime.datetime.utcnow().isoformat()
        
        last_location = {
            "lat": float(lat),
            "lon": float(lon),
            "timestamp": now
        }
        
        delivery_table.update_item(
            Key={"id_delivery": id_delivery},
            UpdateExpression="SET last_location = :loc, updated_at = :u",
            ExpressionAttributeValues={
                ":loc": last_location,
                ":u": now
            }
        )
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Ubicación actualizada",
                "id_delivery": id_delivery,
                "location": last_location
            })
        }
    except ValueError as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"Coordenadas inválidas: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
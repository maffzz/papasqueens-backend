import json, boto3, os
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,GET",
        "Content-Type": "application/json",
    }

    try:
        id_delivery = event["pathParameters"]["id_delivery"]
        headers = event.get("headers", {}) or {}
        qs = event.get("queryStringParameters") or {}
        tenant_id = headers.get("X-Tenant-Id") or headers.get("x-tenant-id") or qs.get("tenant_id")

        if not tenant_id:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "tenant_id requerido"})}

        resp = delivery_table.get_item(Key={"tenant_id": tenant_id, "id_delivery": id_delivery})
        delivery = resp.get("Item")
        if not delivery:
            return {"statusCode": 404, "headers": cors_headers, "body": json.dumps({"error": "Entrega no encontrada"})}

        last_location = delivery.get("last_location")

        # Si no hay ubicación registrada o las coordenadas no son numéricas,
        # devolvemos un objeto vacío de puntos para que el frontend muestre "sin datos".
        if not last_location:
            return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"points": []})}

        lat = last_location.get("lat")
        lon = last_location.get("lon")
        try:
            lat_val = float(lat)
            lon_val = float(lon)
        except (TypeError, ValueError):
            return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"points": []})}

        clean_location = {
            "lat": lat_val,
            "lon": lon_val,
            "timestamp": last_location.get("timestamp"),
        }
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(clean_location)}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
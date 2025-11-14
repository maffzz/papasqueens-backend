import datetime
import json, boto3, os, statistics
from boto3.dynamodb.conditions import Attr
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
        qs = event.get("queryStringParameters") or {}
        tenant_id = qs.get("tenant_id") or headers_in.get("X-Tenant-Id") or headers_in.get("x-tenant-id")
        if not tenant_id:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "tenant_id requerido"})}

        resp = delivery_table.scan(FilterExpression=Attr("tenant_id").eq(tenant_id) & Attr("status").eq("entregado"))
        items = resp.get("Items", [])

        zonas = {}
        tiempos = []
        for i in items:
            zona = i.get("direccion", "desconocida").split(",")[-1].strip()
            tiempos.append((datetime.datetime.fromisoformat(i["tiempo_llegada"]) - datetime.datetime.fromisoformat(i["tiempo_salida"])).total_seconds()/60)
            zonas[zona] = zonas.get(zona, 0) + 1

        promedio_tiempo = statistics.mean(tiempos) if tiempos else 0
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"zonas": zonas, "tiempo_promedio_entrega": promedio_tiempo})}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
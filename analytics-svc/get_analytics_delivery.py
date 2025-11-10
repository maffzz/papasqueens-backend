import datetime
import json, boto3, os, statistics
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def handler(event, context):
    try:
        tenant_id = event["queryStringParameters"]["tenant_id"]
        resp = delivery_table.scan(FilterExpression=Attr("tenant_id").eq(tenant_id) & Attr("status").eq("entregado"))
        items = resp.get("Items", [])

        zonas = {}
        tiempos = []
        for i in items:
            zona = i.get("direccion", "desconocida").split(",")[-1].strip()
            tiempos.append((datetime.datetime.fromisoformat(i["tiempo_llegada"]) - datetime.datetime.fromisoformat(i["tiempo_salida"])).total_seconds()/60)
            zonas[zona] = zonas.get(zona, 0) + 1

        promedio_tiempo = statistics.mean(tiempos) if tiempos else 0
        return {"statusCode": 200, "body": json.dumps({"zonas": zonas, "tiempo_promedio_entrega": promedio_tiempo})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
import json, boto3, os, datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr, Key

dynamo = boto3.resource("dynamodb")
analytics_table = dynamo.Table(os.environ["ANALYTICS_TABLE"])
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def handler(event, context):
    try:
        detail = event.get("detail", {}) or {}

        # Soportar tanto eventos de EventBridge (con detail) como llamadas directas de Step Functions
        order_id = (
            detail.get("id_order")
            or detail.get("order_id")
            or event.get("id_order")
            or event.get("order_id")
        )
        tenant_id = (
            detail.get("tenant_id")
            or event.get("tenant_id")
        )

        if not order_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Evento sin id_order para métricas de delivery"}),
            }

        resp = delivery_table.scan(FilterExpression=Attr("id_order").eq(order_id))
        if not resp.get("Items"):
            return {"statusCode": 404, "body": json.dumps({"error": "Entrega no encontrada"})}
        delivery = resp["Items"][0]

        if not delivery.get("tiempo_salida") or not delivery.get("tiempo_llegada"):
            # Si aún no tenemos tiempos completos, no consideramos esto un error de la
            # máquina de estados: devolvemos 200 con un warning y dejamos pasar los IDs.
            return {
                "statusCode": 200,
                "body": json.dumps({"warning": "Entrega sin tiempos válidos"}),
                "tenant_id": tenant_id,
                "id_order": order_id,
            }

        start = datetime.datetime.fromisoformat(delivery["tiempo_salida"])
        end = datetime.datetime.fromisoformat(delivery["tiempo_llegada"])
        dur = (end - start).total_seconds() / 60.0

        analytics_resp = analytics_table.query(
            IndexName="OrderIndex",
            KeyConditionExpression=Key("id_order").eq(order_id)
        )
        
        if not analytics_resp.get("Items"):
            return {"statusCode": 404, "body": json.dumps({"error": "Métrica no encontrada para este pedido"})}
        
        metric = analytics_resp["Items"][0]
        id_metric = metric["id_metric"]

        analytics_table.update_item(
            Key={"tenant_id": tenant_id, "id_metric": id_metric},
            UpdateExpression="SET #s=:s, fin=:f, tiempo_total=:t, id_staff=:st",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "entregado", ":f": delivery["tiempo_llegada"], ":t": dur, ":st": delivery.get("id_staff")}
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Métrica de entrega actualizada", "tiempo_entrega": dur}),
            "tenant_id": tenant_id,
            "id_order": order_id,
        }
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
import json, boto3, os, datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr, Key

dynamo = boto3.resource("dynamodb")
analytics_table = dynamo.Table(os.environ["ANALYTICS_TABLE"])
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def handler(event, context):
    try:
        detail = event.get("detail", {})
        order_id = detail["id_order"]

        resp = delivery_table.scan(FilterExpression=Attr("id_order").eq(order_id))
        if not resp.get("Items"):
            return {"statusCode": 404, "body": json.dumps({"error": "Entrega no encontrada"})}
        delivery = resp["Items"][0]

        if not delivery.get("tiempo_salida") or not delivery.get("tiempo_llegada"):
            return {"statusCode": 400, "body": json.dumps({"error": "Entrega sin tiempos válidos"})}

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
            Key={"id_metric": id_metric},
            UpdateExpression="SET #s=:s, fin=:f, tiempo_total=:t, id_staff=:st",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "entregado", ":f": delivery["tiempo_llegada"], ":t": dur, ":st": delivery.get("id_staff")}
        )

        return {"statusCode": 200, "body": json.dumps({"message": "Métrica de entrega actualizada", "tiempo_entrega": dur})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
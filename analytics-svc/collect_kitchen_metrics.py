import json, boto3, os, datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr, Key

dynamo = boto3.resource("dynamodb")
analytics_table = dynamo.Table(os.environ["ANALYTICS_TABLE"])
kitchen_table = dynamo.Table(os.environ["KITCHEN_TABLE"])

def handler(event, context):
    try:
        detail = event.get("detail", {})
        order_id = detail["order_id"]

        resp = kitchen_table.scan(FilterExpression=Attr("order_id").eq(order_id))
        if not resp.get("Items"):
            return {"statusCode": 404, "body": json.dumps({"error": "Pedido no encontrado en cocina"})}
        kitchen = resp["Items"][0]

        if not kitchen.get("start_time") or not kitchen.get("end_time"):
            return {"statusCode": 400, "body": json.dumps({"error": "Pedido sin tiempos definidos"})}

        start = datetime.datetime.fromisoformat(kitchen["start_time"])
        end = datetime.datetime.fromisoformat(kitchen["end_time"])
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
            UpdateExpression="SET #s=:s, inicio=:i, fin=:f, tiempo_total=:t",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "listo_para_entrega", ":i": kitchen["start_time"], ":f": kitchen["end_time"], ":t": dur}
        )

        return {"statusCode": 200, "body": json.dumps({"message": "Métrica de cocina actualizada", "tiempo_total": dur})}

    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
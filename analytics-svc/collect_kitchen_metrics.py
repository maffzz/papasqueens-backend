import json, boto3, os, datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr, Key

dynamo = boto3.resource("dynamodb")
analytics_table = dynamo.Table(os.environ["ANALYTICS_TABLE"])
kitchen_table = dynamo.Table(os.environ["KITCHEN_TABLE"])

def handler(event, context):
    try:
        detail = event.get("detail", {})

        def update_metric_for_order(order_id: str, inicio=None, fin=None, tiempo_total=None):
            analytics_resp = analytics_table.query(
                IndexName="OrderIndex",
                KeyConditionExpression=Key("id_order").eq(order_id)
            )
            if not analytics_resp.get("Items"):
                return False
            metric = analytics_resp["Items"][0]
            id_metric = metric["id_metric"]
            expr = ["#s=:s"]
            names = {"#s": "status"}
            values = {":s": "listo_para_entrega"}
            if inicio is not None:
                expr.append("inicio=:i")
                values[":i"] = inicio
            if fin is not None:
                expr.append("fin=:f")
                values[":f"] = fin
            if tiempo_total is not None:
                expr.append("tiempo_total=:t")
                values[":t"] = tiempo_total
            analytics_table.update_item(
                Key={"id_metric": id_metric},
                UpdateExpression="SET " + ", ".join(expr),
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=values
            )
            return True

        # If detail is a list of metrics from Kitchen.MetricsUpdated
        if isinstance(detail, list):
            updated = 0
            for m in detail:
                oid = m.get("order_id")
                if not oid:
                    continue
                tt = m.get("tiempo_total")
                if update_metric_for_order(oid, tiempo_total=tt):
                    updated += 1
            return {"statusCode": 200, "body": json.dumps({"message": "Métricas de cocina actualizadas", "updated": updated})}

        # Fallback: single order_id path
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

        ok = update_metric_for_order(order_id, inicio=kitchen["start_time"], fin=kitchen["end_time"], tiempo_total=dur)
        if not ok:
            return {"statusCode": 404, "body": json.dumps({"error": "Métrica no encontrada para este pedido"})}

        return {"statusCode": 200, "body": json.dumps({"message": "Métrica de cocina actualizada", "tiempo_total": dur})}

    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
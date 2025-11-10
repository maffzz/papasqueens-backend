import json, boto3, os, statistics
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
analytics_table = dynamo.Table(os.environ["ANALYTICS_TABLE"])

def handler(event, context):
    try:
        tenant_id = event["queryStringParameters"]["tenant_id"]
        resp = analytics_table.scan(FilterExpression=Attr("tenant_id").eq(tenant_id) & Attr("id_order").ne(None))
        items = resp.get("Items", [])

        tiempos = [i["tiempo_total"] for i in items if i.get("tiempo_total")]
        promedio = statistics.mean(tiempos) if tiempos else 0

        estados = {}
        for i in items:
            estados[i["status"]] = estados.get(i["status"], 0) + 1

        result = {
            "total_pedidos": len(items),
            "tiempo_promedio": promedio,
            "distribucion_estados": estados
        }
        return {"statusCode": 200, "body": json.dumps(result)}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
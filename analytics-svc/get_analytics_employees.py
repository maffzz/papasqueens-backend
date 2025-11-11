import json, boto3, os
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from validate import require_roles

dynamo = boto3.resource("dynamodb")
analytics_table = dynamo.Table(os.environ["ANALYTICS_TABLE"])

def handler(event, context):
    try:
        _ = require_roles(event, {"staff"})

        tenant_id = event["queryStringParameters"]["tenant_id"]
        resp = analytics_table.scan(FilterExpression=Attr("tenant_id").eq(tenant_id) & Attr("id_staff").ne(None))
        items = resp.get("Items", [])

        metrics = {}
        for i in items:
            staff = i["id_staff"]
            dur = i.get("tiempo_total", 0)
            metrics.setdefault(staff, {"pedidos": 0, "tiempo_total": 0})
            metrics[staff]["pedidos"] += 1
            metrics[staff]["tiempo_total"] += dur

        resumen = []
        for s, m in metrics.items():
            promedio = m["tiempo_total"] / m["pedidos"] if m["pedidos"] else 0
            resumen.append({"id_staff": s, "pedidos": m["pedidos"], "tiempo_promedio": promedio})

        return {"statusCode": 200, "body": json.dumps(resumen)}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
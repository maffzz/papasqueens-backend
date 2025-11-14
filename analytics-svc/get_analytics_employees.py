import json, boto3, os
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
analytics_table = dynamo.Table(os.environ["ANALYTICS_TABLE"])


def handler(event, context):
    try:
        headers = event.get("headers", {}) or {}
        qs = event.get("queryStringParameters") or {}
        tenant_id = qs.get("tenant_id") or headers.get("X-Tenant-Id") or headers.get("x-tenant-id")

        if not tenant_id:
            return {"statusCode": 400, "body": json.dumps({"error": "tenant_id requerido"})}

        resp = analytics_table.query(
            KeyConditionExpression=Key("tenant_id").eq(tenant_id),
            FilterExpression=Attr("id_staff").ne(None)
        )
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
import json, boto3, os, datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

dynamo = boto3.resource("dynamodb")
analytics_table = dynamo.Table(os.environ["ANALYTICS_TABLE"])
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
s3 = boto3.client("s3")

def handler(event, context):
    try:
        headers = event.get("headers", {})
        user_type = headers.get("X-User-Type") or headers.get("x-user-type")
        if not user_type:
            qs = event.get("queryStringParameters") or {}
            user_type = qs.get("user_type")
        if user_type != "staff":
            return {"statusCode": 403, "body": json.dumps({"error": "Forbidden"})}

        tenant_id = event["queryStringParameters"]["tenant_id"]

        # pedidos totales
        pedidos = analytics_table.scan(FilterExpression=Attr("tenant_id").eq(tenant_id) & Attr("id_order").ne(None))
        pedidos_total = len(pedidos.get("Items", []))

        # empleados activos
        empleados = analytics_table.scan(FilterExpression=Attr("tenant_id").eq(tenant_id) & Attr("id_staff").ne(None))
        staff_total = len(set([e["id_staff"] for e in empleados.get("Items", [])]))

        # entregas completadas
        deliveries = delivery_table.scan(FilterExpression=Attr("tenant_id").eq(tenant_id) & Attr("status").eq("entregado"))
        entregas_total = len(deliveries.get("Items", []))

        resumen = {
            "tenant_id": tenant_id,
            "pedidos_total": pedidos_total,
            "empleados_activos": staff_total,
            "entregas_completadas": entregas_total,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

        key = f"{tenant_id}/{datetime.datetime.utcnow().strftime('%Y-%m-%d')}/dashboard.json"
        s3.put_object(
            Bucket=os.environ["ANALYTICS_BUCKET"],
            Key=key,
            Body=json.dumps(resumen),
            ContentType="application/json"
        )

        return {"statusCode": 200, "body": json.dumps(resumen)}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
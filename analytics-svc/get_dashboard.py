import json, boto3, os, datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

dynamo = boto3.resource("dynamodb")
analytics_table = dynamo.Table(os.environ["ANALYTICS_TABLE"])
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
s3 = boto3.client("s3")


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

        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(resumen)}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
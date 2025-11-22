import json, boto3, os, datetime
from decimal import Decimal
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

dynamo = boto3.resource("dynamodb")
analytics_table = dynamo.Table(os.environ["ANALYTICS_TABLE"])
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
orders_table = dynamo.Table(os.environ["ORDERS_TABLE"])
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

        # pedidos totales (métricas registradas)
        pedidos = analytics_table.scan(FilterExpression=Attr("tenant_id").eq(tenant_id) & Attr("id_order").ne(None))
        pedidos_total = len(pedidos.get("Items", []))

        # empleados activos
        empleados = analytics_table.scan(FilterExpression=Attr("tenant_id").eq(tenant_id) & Attr("id_staff").ne(None))
        staff_total = len(set([e["id_staff"] for e in empleados.get("Items", [])]))

        # entregas completadas
        deliveries = delivery_table.scan(FilterExpression=Attr("tenant_id").eq(tenant_id) & Attr("status").eq("entregado"))
        entregas_total = len(deliveries.get("Items", []))

        # métricas financieras básicas a partir de las órdenes entregadas
        # Nota: para simplicidad se usa un scan filtrando por tenant_id y status="entregado".
        # En producción esto podría optimizarse con índices.
        orders_scan = orders_table.scan(
            FilterExpression=Attr("tenant_id").eq(tenant_id) & Attr("status").eq("entregado")
        )
        orders_items = orders_scan.get("Items", [])

        total_ingresos = 0.0
        ordenes_ultimos_7_dias = 0
        now = datetime.datetime.utcnow()
        seven_days_ago = now - datetime.timedelta(days=7)

        for o in orders_items:
            items = o.get("items") or []
            order_total = 0.0
            for it in items:
                if not isinstance(it, dict):
                    continue
                precio = it.get("precio") or it.get("price") or 0
                qty = it.get("qty") or 1
                try:
                    if isinstance(precio, Decimal):
                        precio_val = float(precio)
                    else:
                        precio_val = float(precio)
                    order_total += precio_val * float(qty)
                except Exception:
                    continue
            total_ingresos += order_total

            # contar órdenes entregadas en los últimos 7 días usando updated_at
            updated_raw = o.get("updated_at") or o.get("created_at")
            if updated_raw:
                try:
                    updated_dt = datetime.datetime.fromisoformat(str(updated_raw))
                    if updated_dt >= seven_days_ago:
                        ordenes_ultimos_7_dias += 1
                except Exception:
                    pass

        ticket_promedio = (total_ingresos / len(orders_items)) if orders_items else 0.0

        resumen = {
            "tenant_id": tenant_id,
            "pedidos_total": pedidos_total,
            "empleados_activos": staff_total,
            "entregas_completadas": entregas_total,
            "total_ingresos": round(total_ingresos, 2),
            "ticket_promedio": round(ticket_promedio, 2),
            "ordenes_ultimos_7_dias": ordenes_ultimos_7_dias,
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
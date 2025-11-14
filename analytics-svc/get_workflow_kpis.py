import json, os, boto3, datetime, statistics
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
orders_table = dynamo.Table(os.environ["ORDERS_TABLE"])
kitchen_table = dynamo.Table(os.environ["KITCHEN_TABLE"])
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def parse_iso(ts):
    try:
        return datetime.datetime.fromisoformat(ts)
    except Exception:
        return None

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
        tenant_id = headers_in.get("X-Tenant-Id") or headers_in.get("x-tenant-id") or qs.get("tenant_id") or "default"

        # Cargar datos por tenant
        o_resp = orders_table.scan(FilterExpression=Attr("tenant_id").eq(tenant_id))
        k_resp = kitchen_table.scan(FilterExpression=Attr("tenant_id").eq(tenant_id))
        d_resp = delivery_table.scan(FilterExpression=Attr("tenant_id").eq(tenant_id))
        orders = {o["id_order"]: o for o in o_resp.get("Items", [])}
        kitchen = {k["order_id"]: k for k in k_resp.get("Items", [])}
        delivery_by_order = {}
        for it in d_resp.get("Items", []):
            oid = it.get("id_order")
            if not oid:
                continue
            delivery_by_order[oid] = it

        # Calcular tiempos por paso y ranking por responsables
        t_recv_to_accept = []
        t_accept_to_pack = []
        t_pack_to_out = []
        t_out_to_arrive = []
        accepted_by = {}
        packed_by = {}
        delivered_by = {}

        for oid, o in orders.items():
            created_at = parse_iso(o.get("created_at"))
            k = kitchen.get(oid, {})
            d = delivery_by_order.get(oid, {})

            acc_at = parse_iso(k.get("accepted_at"))
            pac_at = parse_iso(k.get("packed_at") or k.get("end_time"))
            out_at = parse_iso(d.get("tiempo_salida"))
            arr_at = parse_iso(d.get("tiempo_llegada"))

            if created_at and acc_at and acc_at >= created_at:
                t_recv_to_accept.append((acc_at - created_at).total_seconds()/60)
            if acc_at and pac_at and pac_at >= acc_at:
                t_accept_to_pack.append((pac_at - acc_at).total_seconds()/60)
            if pac_at and out_at and out_at >= pac_at:
                t_pack_to_out.append((out_at - pac_at).total_seconds()/60)
            if out_at and arr_at and arr_at >= out_at:
                t_out_to_arrive.append((arr_at - out_at).total_seconds()/60)

            ab = k.get("accepted_by")
            pb = k.get("packed_by")
            db = d.get("delivered_by")
            if ab: accepted_by[ab] = accepted_by.get(ab, 0) + 1
            if pb: packed_by[pb] = packed_by.get(pb, 0) + 1
            if db: delivered_by[db] = delivered_by.get(db, 0) + 1

        def agg(x):
            return {
                "count": len(x),
                "avg_min": (statistics.mean(x) if x else 0),
                "p50_min": (statistics.median(x) if x else 0),
                "p95_min": (sorted(x)[int(0.95*len(x))-1] if x else 0)
            }

        result = {
            "tenant_id": tenant_id,
            "timings": {
                "recibido_a_aceptado": agg(t_recv_to_accept),
                "aceptado_a_empacado": agg(t_accept_to_pack),
                "empacado_a_salida": agg(t_pack_to_out),
                "salida_a_entregado": agg(t_out_to_arrive)
            },
            "responsables": {
                "accepted_by": accepted_by,
                "packed_by": packed_by,
                "delivered_by": delivered_by
            }
        }
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(result)}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}

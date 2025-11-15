import json, boto3, os, datetime
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
staff_table = dynamo.Table(os.environ["STAFF_TABLE"])
eb = boto3.client("events")

def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST",
        "Content-Type": "application/json",
    }

    try:
        body = json.loads(event.get("body", "{}"))
        headers = event.get("headers", {}) or {}
        qs = event.get("queryStringParameters") or {}
        id_delivery = body.get("id_delivery")
        id_order = body.get("id_order")
        tenant_id = body.get("tenant_id") or headers.get("X-Tenant-Id") or headers.get("x-tenant-id") or qs.get("tenant_id") or "default"
        chosen_staff = body.get("id_staff")

        # Resolver id_delivery a partir de id_order si no llega directamente, usando GSI OrderIndex
        if not id_delivery and id_order:
            resp = delivery_table.query(
                IndexName="OrderIndex",
                KeyConditionExpression=Key("id_order").eq(id_order)
            )
            items = [x for x in resp.get("Items", []) if x.get("tenant_id") == tenant_id]
            if not items:
                return {"statusCode": 404, "headers": cors_headers, "body": json.dumps({"error": "Entrega no encontrada para el pedido"})}
            id_delivery = items[0]["id_delivery"]

        if not id_delivery:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "Falta id_delivery o id_order"})}

        # Validar/Seleccionar repartidor con rol delivery
        if chosen_staff:
            st = staff_table.get_item(Key={"tenant_id": tenant_id, "id_staff": chosen_staff}).get("Item") or {}
            if (not st) or (st.get("status") != "activo") or (st.get("role") != "delivery"):
                return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "id_staff inválido: requiere rol 'delivery' activo y tenant válido"})}
        else:
            staff_resp = staff_table.scan(
                FilterExpression=Attr("tenant_id").eq(tenant_id) & Attr("role").eq("delivery") & Attr("status").eq("activo")
            )
            riders = staff_resp.get("Items", [])
            if not riders:
                return {"statusCode": 404, "headers": cors_headers, "body": json.dumps({"error": "No hay repartidores disponibles"})}
            chosen_staff = riders[0]["id_staff"]

        # Validar tenant del delivery
        d_item = delivery_table.get_item(Key={"tenant_id": tenant_id, "id_delivery": id_delivery}).get("Item")
        if not d_item:
            return {"statusCode": 404, "headers": cors_headers, "body": json.dumps({"error": "Entrega no encontrada para el tenant"})}

        now = datetime.datetime.utcnow().isoformat()

        delivery_table.update_item(
            Key={"tenant_id": tenant_id, "id_delivery": id_delivery},
            UpdateExpression="SET id_staff=:s, status=:st, assigned_at=:a, updated_at=:u",
            ExpressionAttributeValues={
                ":s": chosen_staff,
                ":st": "asignado",
                ":a": now,
                ":u": now
            }
        )

        eb.put_events(
            Entries=[
                {
                    "Source": "delivery-svc",
                    "DetailType": "Order.Assigned",
                    "Detail": json.dumps({"tenant_id": tenant_id, "id_delivery": id_delivery, "id_staff": chosen_staff}),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )

        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": "Repartidor asignado", "id_staff": chosen_staff, "id_delivery": id_delivery})}

    except KeyError as e:
        return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": f"Campo faltante: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
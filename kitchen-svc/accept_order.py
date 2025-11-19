import json, boto3, os, datetime
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["KITCHEN_TABLE"])
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
        raw_body = event.get("body")
        if not raw_body:
            raw_body = "{}"
        body = json.loads(raw_body)
        headers = event.get("headers", {}) or {}
        qs = event.get("queryStringParameters") or {}
        order_id = event["pathParameters"]["order_id"]
        staff_id = body.get("id_staff") or headers.get("X-User-Id") or headers.get("x-user-id")
        tenant_id = headers.get("X-Tenant-Id") or headers.get("x-tenant-id") or qs.get("tenant_id")

        if not tenant_id:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "tenant_id requerido"})}

        now = datetime.datetime.utcnow().isoformat()
        table.update_item(
            Key={"tenant_id": tenant_id, "order_id": order_id},
            UpdateExpression="SET #s = :s, list_id_staff = list_append(if_not_exists(list_id_staff, :empty), :sid), start_time = :st, accepted_by = :by, accepted_at = :st, updated_at = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "en_preparacion",
                ":sid": [staff_id],
                ":empty": [],
                ":st": now,
                ":by": staff_id,
                ":u": now
            }
        )

        eb.put_events(
            Entries=[
                {
                    "Source": "kitchen-svc",
                    "DetailType": "Order.Updated",
                    "Detail": json.dumps({"order_id": order_id, "tenant_id": tenant_id, "status": "en_preparacion"}),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )

        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": "Pedido en preparación", "order_id": order_id})}

    except KeyError as e:
        return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": f"Campo faltante: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
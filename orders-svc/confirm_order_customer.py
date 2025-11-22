import json, os, boto3, datetime
from botocore.exceptions import ClientError


dynamo = boto3.resource("dynamodb")
orders_table = dynamo.Table(os.environ["ORDERS_TABLE"])


def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST",
        "Content-Type": "application/json",
    }

    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": cors_headers, "body": ""}

    try:
        path = event.get("pathParameters") or {}
        order_id = path.get("id_order")
        headers = event.get("headers", {}) or {}
        qs = event.get("queryStringParameters") or {}

        tenant_id = headers.get("X-Tenant-Id") or headers.get("x-tenant-id") or qs.get("tenant_id")
        user_type = (headers.get("X-User-Type") or headers.get("x-user-type") or "").lower()
        user_id = headers.get("X-User-Id") or headers.get("x-user-id")

        if not tenant_id or not order_id:
            return {
                "statusCode": 400,
                "headers": cors_headers,
                "body": json.dumps({"error": "tenant_id e id_order requeridos"}),
            }

        if user_type not in ("customer", "cliente"):
            return {
                "statusCode": 403,
                "headers": cors_headers,
                "body": json.dumps({"error": "Solo clientes pueden confirmar recepción"}),
            }

        # Verificar que el pedido pertenezca al cliente autenticado
        resp = orders_table.get_item(Key={"tenant_id": tenant_id, "id_order": order_id})
        item = resp.get("Item") or {}
        if not item:
            return {
                "statusCode": 404,
                "headers": cors_headers,
                "body": json.dumps({"error": "Pedido no encontrado"}),
            }

        if user_id and item.get("id_customer") and item.get("id_customer") != user_id:
            return {
                "statusCode": 403,
                "headers": cors_headers,
                "body": json.dumps({"error": "No puedes confirmar pedidos de otro cliente"}),
            }

        now = datetime.datetime.utcnow().isoformat()
        orders_table.update_item(
            Key={"tenant_id": tenant_id, "id_order": order_id},
            UpdateExpression="SET customer_confirmed_delivered = :v, updated_at = :u",
            ExpressionAttributeValues={":v": True, ":u": now},
        )

        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps({"message": "Cliente confirmó recepción"}),
        }
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}

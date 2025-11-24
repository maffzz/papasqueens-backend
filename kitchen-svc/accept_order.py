import json, boto3, os, datetime
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["KITCHEN_TABLE"])
orders_table = dynamo.Table(os.environ["ORDERS_TABLE"])
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
        
        # Validar que el usuario tenga rol de cocinero
        headers = event.get("headers", {}) or {}
        user_role = headers.get("X-User-Role") or headers.get("x-user-role")
        if user_role and user_role not in ["cocinero", "admin"]:
            return {"statusCode": 403, "headers": cors_headers, "body": json.dumps({"error": "Solo cocineros pueden aceptar pedidos"})}
        
        table.update_item(
            Key={"tenant_id": tenant_id, "order_id": order_id},
            UpdateExpression="SET #s = :s, list_id_staff = list_append(if_not_exists(list_id_staff, :empty), :sid), start_time = :st, accepted_by = :by, accepted_at = :st, updated_at = :u, accepted_by_role = :role",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "en_preparacion",
                ":sid": [staff_id],
                ":empty": [],
                ":st": now,
                ":by": staff_id,
                ":u": now,
                ":role": "cocinero",
            },
        )

        # Mantener sincronizada la tabla Orders con el estado de cocina
        try:
            orders_table.update_item(
                Key={"tenant_id": tenant_id, "id_order": order_id},
                UpdateExpression="SET #s = :s, updated_at = :u",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":s": "en_preparacion", ":u": now},
            )
        except Exception:
            # No rompemos el flujo de cocina si fallara esta actualización
            pass

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

        # Iniciar Step Functions (best-effort) cuando cocina acepta el pedido
        try:
            sfn = boto3.client("stepfunctions")
            sfn_arn = os.environ.get("ORDER_SFN_ARN")
            if not sfn_arn:
                target_name = os.environ.get("ORDER_SFN_NAME", "papasqueens-order-workflow")
                paginator = sfn.get_paginator("list_state_machines")
                for page in paginator.paginate():
                    for sm in page.get("stateMachines", []):
                        if sm.get("name") == target_name:
                            sfn_arn = sm.get("stateMachineArn")
                            break
                    if sfn_arn:
                        break

            if sfn_arn:
                sfn_input = {"id_order": order_id, "tenant_id": tenant_id}
                sfn.start_execution(stateMachineArn=sfn_arn, input=json.dumps(sfn_input))
        except Exception:
            # No romper flujo de cocina si falla Step Functions
            pass

        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": "Pedido en preparación", "order_id": order_id})}

    except KeyError as e:
        return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": f"Campo faltante: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
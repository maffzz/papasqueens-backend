import json, boto3, os, datetime
from botocore.exceptions import ClientError
import base64

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["KITCHEN_TABLE"])
eb = boto3.client("events")

def handler(event, context):
    try:
        order_id = event["pathParameters"]["order_id"]
        now = datetime.datetime.utcnow().isoformat()

        table.update_item(
            Key={"order_id": order_id},
            UpdateExpression="SET #s = :s, end_time = :et, updated_at = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "listo_para_entrega", ":et": now, ":u": now}
        )

        resp = table.get_item(Key={"order_id": order_id})
        pedido = resp.get("Item", {})
        tenant_id = pedido.get("tenant_id", "default")

        recibo = f"""RECIBO DE PEDIDO\nOrder ID: {order_id}\nTenant: {tenant_id}\nEstado: {pedido.get('status')}\nTiempos: {pedido.get('start_time')} a {now}\nPersonal asignado: {','.join(pedido.get('list_id_staff', []))}\n"""

        s3 = boto3.client("s3")
        key = f"{tenant_id}/{order_id}/receipt.txt"
        s3.put_object(
            Bucket=os.environ.get("RECEIPTS_BUCKET"),
            Key=key,
            Body=recibo.encode("utf-8"),
            ContentType="text/plain"
        )

        eb.put_events(
            Entries=[
                {
                    "Source": "kitchen-svc",
                    "DetailType": "Order.Prepared",
                    "Detail": json.dumps({"order_id": order_id, "tenant_id": tenant_id}),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )

        return {"statusCode": 200, "body": json.dumps({"message": "Pedido listo para entrega", "order_id": order_id})}

    except KeyError as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"Campo faltante: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
import json, boto3, os, datetime
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])
staff_table = dynamo.Table(os.environ["STAFF_TABLE"])
eb = boto3.client("events")

def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        id_delivery = body["id_delivery"]
        tenant_id = body["tenant_id"]

        # buscar repartidor disponible
        staff_resp = staff_table.scan(
            FilterExpression=Attr("tenant_id").eq(tenant_id) & Attr("role").eq("repartidor") & Attr("status").eq("activo")
        )
        riders = staff_resp.get("Items", [])
        if not riders:
            return {"statusCode": 404, "body": json.dumps({"error": "No hay repartidores disponibles"})}

        rider = riders[0]
        now = datetime.datetime.utcnow().isoformat()

        delivery_table.update_item(
            Key={"id_delivery": id_delivery},
            UpdateExpression="SET id_staff=:s, status=:st, updated_at=:u",
            ExpressionAttributeValues={
                ":s": rider["id_staff"],
                ":st": "asignado",
                ":u": now
            }
        )

        eb.put_events(
            Entries=[
                {
                    "Source": "delivery-svc",
                    "DetailType": "Order.Assigned",
                    "Detail": json.dumps({"id_delivery": id_delivery, "id_staff": rider["id_staff"]}),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )

        return {"statusCode": 200, "body": json.dumps({"message": "Repartidor asignado", "id_staff": rider["id_staff"]})}

    except KeyError as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"Campo faltante: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
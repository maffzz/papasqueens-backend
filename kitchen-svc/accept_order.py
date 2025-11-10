import json, boto3, os, datetime
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["KITCHEN_TABLE"])
eb = boto3.client("events")

def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        order_id = event["pathParameters"]["order_id"]
        staff_id = body["id_staff"]

        now = datetime.datetime.utcnow().isoformat()
        table.update_item(
            Key={"order_id": order_id},
            UpdateExpression="SET #s = :s, list_id_staff = list_append(if_not_exists(list_id_staff, :empty), :sid), start_time = :st, updated_at = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "en_preparacion",
                ":sid": [staff_id],
                ":empty": [],
                ":st": now,
                ":u": now
            }
        )

        eb.put_events(
            Entries=[
                {
                    "Source": "kitchen-svc",
                    "DetailType": "Order.Updated",
                    "Detail": json.dumps({"order_id": order_id, "status": "en_preparacion"}),
                    "EventBusName": os.environ["EVENT_BUS"]
                }
            ]
        )

        return {"statusCode": 200, "body": json.dumps({"message": "Pedido en preparación", "order_id": order_id})}

    except KeyError as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"Campo faltante: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
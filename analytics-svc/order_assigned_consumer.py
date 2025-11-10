import json, boto3, os, datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

dynamo = boto3.resource("dynamodb")
analytics_table = dynamo.Table(os.environ["ANALYTICS_TABLE"])
delivery_table = dynamo.Table(os.environ["DELIVERY_TABLE"])

def handler(event, context):
    try:
        detail = event.get("detail", {})
        id_delivery = detail["id_delivery"]
        id_staff = detail.get("id_staff")

        dresp = delivery_table.get_item(Key={"id_delivery": id_delivery})
        delivery = dresp.get("Item")
        if not delivery:
            return {"statusCode": 404, "body": json.dumps({"error": "Entrega no encontrada"})}

        order_id = delivery.get("id_order")
        tenant_id = delivery.get("tenant_id", "default")

        aresp = analytics_table.query(
            IndexName="OrderIndex",
            KeyConditionExpression=Key("id_order").eq(order_id)
        )
        items = aresp.get("Items", [])
        if not items:
            analytics_table.put_item(Item={
                "id_metric": f"metric-{order_id}",
                "id_order": order_id,
                "id_staff": id_staff,
                "status": "asignado",
                "inicio": datetime.datetime.utcnow().isoformat(),
                "fin": None,
                "tiempo_total": None,
                "tenant_id": tenant_id
            })
        else:
            id_metric = items[0]["id_metric"]
            analytics_table.update_item(
                Key={"id_metric": id_metric},
                UpdateExpression="SET id_staff=:s, #st=:st, updated_at=:u",
                ExpressionAttributeNames={"#st": "status"},
                ExpressionAttributeValues={":s": id_staff, ":st": "asignado", ":u": datetime.datetime.utcnow().isoformat()}
            )

        return {"statusCode": 200, "body": json.dumps({"message": "Asignación registrada", "id_order": order_id, "id_staff": id_staff})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
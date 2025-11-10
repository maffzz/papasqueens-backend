import json, boto3, os, datetime
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["MENU_TABLE"])

def handler(event, context):
    try:
        id_producto = event["pathParameters"]["id_producto"]
        body = json.loads(event.get("body", "{}"))
        update_expr = []
        expr_names = {}
        expr_values = {}

        for k, v in body.items():
            update_expr.append(f"#{k} = :{k}")
            expr_names[f"#{k}"] = k
            expr_values[f":{k}"] = v

        update_expr.append("updated_at = :u")
        expr_values[":u"] = datetime.datetime.utcnow().isoformat()

        table.update_item(
            Key={"id_producto": id_producto},
            UpdateExpression="SET " + ", ".join(update_expr),
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values
        )

        return {"statusCode": 200, "body": json.dumps({"message": "Producto actualizado"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
import json, boto3, os
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
staff_table = dynamo.Table(os.environ["STAFF_TABLE"])

def handler(event, context):
    try:
        headers = event.get("headers", {})
        user_type = headers.get("X-User-Type") or headers.get("x-user-type")
        if not user_type:
            qs = event.get("queryStringParameters") or {}
            user_type = qs.get("user_type")
        if user_type != "staff":
            return {"statusCode": 403, "body": json.dumps({"error": "Forbidden"})}

        id_staff = event["pathParameters"]["id_staff"]
        body = json.loads(event.get("body", "{}"))
        status = body.get("status")
        if status not in ["activo", "inactivo"]:
            return {"statusCode": 400, "body": json.dumps({"error": "Estado inválido"})}
        staff_table.update_item(
            Key={"id_staff": id_staff},
            UpdateExpression="SET #s=:s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": status}
        )
        return {"statusCode": 200, "body": json.dumps({"message": "Estado de repartidor actualizado"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
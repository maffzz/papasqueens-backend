import json, boto3, os, datetime
from common.jwt_utils import verify_jwt
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["MENU_TABLE"])

def handler(event, context):
    try:
        # Auth: require staff admin
        headers = event.get("headers", {}) or {}
        authz = headers.get("Authorization") or headers.get("authorization")
        if not authz or not authz.lower().startswith("bearer "):
            return {"statusCode": 401, "body": json.dumps({"error": "No autorizado"})}
        token = authz.split(" ", 1)[1].strip()
        claims = verify_jwt(token) or {}
        if (claims.get("type") != "staff") or (claims.get("role") != "admin"):
            return {"statusCode": 403, "body": json.dumps({"error": "Requiere rol admin"})}

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
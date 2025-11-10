import json, boto3, os, uuid, datetime, base64
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
table = dynamo.Table(os.environ["MENU_TABLE"])
s3 = boto3.client("s3")

def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        id_producto = str(uuid.uuid4())
        tenant_id = body["tenant_id"]
        nombre = body["nombre"]
        categoria = body["categoria"]
        precio = body["precio"]
        available = body.get("available", True)
        image_data = body.get("image_data")

        image_url = None
        if image_data:
            image_bytes = base64.b64decode(image_data)
            key = f"{tenant_id}/{id_producto}.jpg"
            s3.put_object(Bucket=os.environ["MENU_BUCKET"], Key=key, Body=image_bytes, ContentType="image/jpeg")
            image_url = f"https://{os.environ['MENU_BUCKET']}.s3.amazonaws.com/{key}"

        now = datetime.datetime.utcnow().isoformat()
        item = {
            "id_producto": id_producto,
            "tenant_id": tenant_id,
            "nombre": nombre,
            "categoria": categoria,
            "precio": precio,
            "available": available,
            "image_url": image_url,
            "created_at": now,
            "updated_at": now
        }
        table.put_item(Item=item)
        return {"statusCode": 201, "body": json.dumps({"message": "Producto agregado", "id_producto": id_producto})}

    except KeyError as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"Campo faltante: {e}"})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
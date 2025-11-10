import json, boto3, os, csv, io, datetime
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamo = boto3.resource("dynamodb")
analytics_table = dynamo.Table(os.environ["ANALYTICS_TABLE"])
s3 = boto3.client("s3")

def handler(event, context):
    try:
        tenant_id = event.get("tenant_id", "default")
        resp = analytics_table.scan(FilterExpression=Attr("tenant_id").eq(tenant_id))
        items = resp.get("Items", [])
        if not items:
            return {"statusCode": 404, "body": json.dumps({"error": "No hay métricas disponibles"})}

        filename = f"{tenant_id}_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=items[0].keys())
        writer.writeheader()
        writer.writerows(items)

        s3.put_object(
            Bucket=os.environ["ANALYTICS_BUCKET"],
            Key=f"{tenant_id}/{filename}",
            Body=csv_buffer.getvalue(),
            ContentType="text/csv"
        )

        return {"statusCode": 200, "body": json.dumps({"message": "Reporte exportado", "file": filename})}
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
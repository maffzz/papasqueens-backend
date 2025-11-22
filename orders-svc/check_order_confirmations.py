import json, os, boto3
from botocore.exceptions import ClientError


dynamo = boto3.resource("dynamodb")
orders_table = dynamo.Table(os.environ["ORDERS_TABLE"])


def handler(event, context):
    """Lambda usada por Step Functions para saber si staff y cliente ya confirmaron.

    Espera un input tipo: {"tenant_id": "...", "id_order": "..."}
    Devuelve: { tenant_id, id_order, staff_confirmed, customer_confirmed, done }
    """
    tenant_id = (event or {}).get("tenant_id")
    order_id = (event or {}).get("id_order")

    if not tenant_id or not order_id:
        return {
            "tenant_id": tenant_id,
            "id_order": order_id,
            "staff_confirmed": False,
            "customer_confirmed": False,
            "done": False,
        }

    try:
        resp = orders_table.get_item(Key={"tenant_id": tenant_id, "id_order": order_id})
        item = resp.get("Item") or {}
    except ClientError:
        item = {}

    staff_ok = bool(item.get("staff_confirmed_delivered"))
    cust_ok = bool(item.get("customer_confirmed_delivered"))

    return {
        "tenant_id": tenant_id,
        "id_order": order_id,
        "staff_confirmed": staff_ok,
        "customer_confirmed": cust_ok,
        "done": staff_ok and cust_ok,
    }

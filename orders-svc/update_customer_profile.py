import json, os, boto3
from decimal import Decimal
from botocore.exceptions import ClientError


dynamo = boto3.resource("dynamodb")
users_table = dynamo.Table(os.environ["USERS_TABLE"])


def to_serializable(obj):
    """Convierte Decimals y estructuras anidadas a tipos JSON-serializables."""
    if isinstance(obj, Decimal):
        try:
            return float(obj)
        except Exception:
            return int(obj)
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_serializable(v) for v in obj]
    return obj


def get_tenant_and_email(event):
    headers = event.get("headers", {}) or {}
    tenant_id = headers.get("X-Tenant-Id") or headers.get("x-tenant-id")
    email = headers.get("X-User-Email") or headers.get("x-user-email")

    # Como respaldo, permitimos tenant_id y email por query params
    if not tenant_id or not email:
        qs = event.get("queryStringParameters") or {}
        tenant_id = tenant_id or qs.get("tenant_id")
        email = email or qs.get("email")

    return tenant_id, email


def handler(event, context):
    headers_in = event.get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,PATCH",
        "Content-Type": "application/json",
    }

    if event.get("httpMethod") == "OPTIONS":
        # Respuesta CORS previa
        return {"statusCode": 200, "headers": cors_headers, "body": ""}

    try:
        tenant_id, email = get_tenant_and_email(event)
        if not tenant_id or not email:
            return {
                "statusCode": 401,
                "headers": cors_headers,
                "body": json.dumps({"error": "tenant_id y email requeridos en headers o query"}),
            }

        body = json.loads(event.get("body", "{}"))
        name = body.get("name")
        address = body.get("address") or body.get("direccion")
        phone = body.get("phone")
        lat = body.get("lat")
        lng = body.get("lng")

        update_expr_parts = []
        expr_attr_names = {}
        expr_attr_values = {}

        if name is not None:
            update_expr_parts.append("#n = :name")
            expr_attr_names["#n"] = "name"
            expr_attr_values[":name"] = name
        if address is not None:
            update_expr_parts.append("address = :address")
            expr_attr_values[":address"] = address
        if phone is not None:
            update_expr_parts.append("phone = :phone")
            expr_attr_values[":phone"] = phone
        if lat is not None:
            try:
                lat_dec = Decimal(str(lat))
                update_expr_parts.append("lat = :lat")
                expr_attr_values[":lat"] = lat_dec
            except Exception:
                # Si no se puede convertir, no romper la actualización completa
                pass
        if lng is not None:
            try:
                lng_dec = Decimal(str(lng))
                update_expr_parts.append("lng = :lng")
                expr_attr_values[":lng"] = lng_dec
            except Exception:
                pass

        if not update_expr_parts:
            return {
                "statusCode": 400,
                "headers": cors_headers,
                "body": json.dumps({"error": "No se proporcionaron campos para actualizar"}),
            }

        update_expr = "SET " + ", ".join(update_expr_parts)

        kwargs = {
            "Key": {"tenant_id": tenant_id, "email": email},
            "UpdateExpression": update_expr,
            "ExpressionAttributeValues": expr_attr_values,
            "ReturnValues": "ALL_NEW",
        }
        if expr_attr_names:
            kwargs["ExpressionAttributeNames"] = expr_attr_names

        resp = users_table.update_item(**kwargs)
        updated = resp.get("Attributes", {})

        payload = {
            "tenant_id": updated.get("tenant_id", tenant_id),
            "email": updated.get("email", email),
            "id_user": updated.get("id_user"),
            "type_user": updated.get("type_user"),
            "name": updated.get("name"),
            "address": updated.get("address"),
            "phone": updated.get("phone"),
            "lat": updated.get("lat"),
            "lng": updated.get("lng"),
            "status": updated.get("status"),
        }

        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(to_serializable(payload))}

    except ClientError as e:
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": f"Error en base de datos: {str(e)}"}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": f"Error inesperado: {str(e)}"}),
        }

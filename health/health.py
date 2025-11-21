import json


def handler(event, context):
    headers_in = (event or {}).get("headers", {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers_in.get("Origin") or headers_in.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,GET",
        "Content-Type": "application/json",
    }

    body = {
        "status": "ok",
        "service": "papasqueens-platform",
    }
    return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(body)}

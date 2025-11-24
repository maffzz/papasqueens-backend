import json

def handler(event, context):
    """Handler de prueba para verificar CORS sin dependencias"""
    headers = event.get('headers', {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": headers.get("Origin") or headers.get("origin") or "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,X-User-Id,X-User-Email,X-User-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST",
        "Content-Type": "application/json",
    }
    
    try:
        body = json.loads(event.get('body', '{}'))
        
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps({
                "message": "CORS Test OK",
                "received": {
                    "body": body,
                    "headers": dict(headers),
                    "method": event.get('httpMethod'),
                    "path": event.get('path')
                }
            })
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": str(e)})
        }

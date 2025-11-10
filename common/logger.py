import json
import logging
import os
import sys
import traceback
from datetime import datetime
from functools import wraps

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def setup_exception_handler():
    def exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        log_data = {
            "level": "ERROR",
            "message": "Excepción no manejada",
            "error_type": exc_type.__name__,
            "error_message": str(exc_value),
            "traceback": ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
            "timestamp": datetime.utcnow().isoformat(),
            "service": os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "unknown")
        }
        logger.error(json.dumps(log_data))
    
    sys.excepthook = exception_handler

def get_log_context(event=None, context=None, extra_data=None):
    """Extrae contexto útil para los logs"""
    context_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "service": os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "unknown"),
    }
    
    if context:
        context_data.update({
            "request_id": context.aws_request_id,
            "function_name": context.function_name,
            "function_version": context.function_version,
            "memory_limit": context.memory_limit_mb,
        })
    
    if event:
        if "pathParameters" in event:
            context_data["path_params"] = event.get("pathParameters", {})
        if "queryStringParameters" in event:
            context_data["query_params"] = event.get("queryStringParameters", {})
        if "headers" in event:
            headers = event.get("headers", {})
            context_data["user_type"] = headers.get("X-User-Type") or headers.get("x-user-type")
            context_data["user_id"] = headers.get("X-User-Id") or headers.get("x-user-id")
    
    if extra_data:
        context_data.update(extra_data)
    
    return context_data

def log_info(message, event=None, context=None, extra=None):
    """Log de información con contexto"""
    log_data = {
        "level": "INFO",
        "message": message,
        **get_log_context(event, context, extra)
    }
    logger.info(json.dumps(log_data))

def log_error(message, error=None, event=None, context=None, extra=None):
    """Log de error con contexto y stack trace"""
    log_data = {
        "level": "ERROR",
        "message": message,
        **get_log_context(event, context, extra)
    }
    
    if error:
        log_data["error_type"] = type(error).__name__
        log_data["error_message"] = str(error)
        try:
            log_data["traceback"] = traceback.format_exc()
        except:
            log_data["traceback"] = "No se pudo obtener traceback"
    
    logger.error(json.dumps(log_data))

def log_warning(message, event=None, context=None, extra=None):
    """Log de advertencia con contexto"""
    log_data = {
        "level": "WARNING",
        "message": message,
        **get_log_context(event, context, extra)
    }
    logger.warning(json.dumps(log_data))

def log_debug(message, event=None, context=None, extra=None):
    """Log de debug con contexto"""
    log_data = {
        "level": "DEBUG",
        "message": message,
        **get_log_context(event, context, extra)
    }
    logger.debug(json.dumps(log_data))

def lambda_handler_wrapper(handler_func):
    @wraps(handler_func)
    def wrapper(event, context):
        try:
            log_info(f"Iniciando ejecución de {handler_func.__name__}", event, context)
            
            result = handler_func(event, context)
            
            log_info(f"Ejecución exitosa de {handler_func.__name__}", event, context)
            
            return result
            
        except Exception as e:
            log_error(
                f"Excepción no manejada en {handler_func.__name__}",
                e,
                event,
                context,
                {"function": handler_func.__name__}
            )
            
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Error interno del servidor",
                    "request_id": context.aws_request_id if context else None
                })
            }
    
    return wrapper
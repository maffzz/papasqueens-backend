#!/usr/bin/env python3
import os
import json
import ast
import sys
import re
from pathlib import Path
from collections import defaultdict

# Colores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

errors = []
warnings = []

def print_success(msg):
    print(f"{GREEN}✓{RESET} {msg}")

def print_error(msg):
    print(f"{RED}✗{RESET} {msg}")
    errors.append(msg)

def print_warning(msg):
    print(f"{YELLOW}⚠{RESET} {msg}")
    warnings.append(msg)

def print_info(msg):
    print(f"{BLUE}ℹ{RESET} {msg}")

def validate_python_syntax(file_path):
    """Valida que el archivo Python tenga sintaxis válida"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        return True
    except SyntaxError as e:
        print_error(f"Sintaxis inválida en {file_path}: {e}")
        return False
    except Exception as e:
        print_error(f"Error leyendo {file_path}: {e}")
        return False

def validate_handler_function(file_path):
    """Valida que el archivo tenga una función handler"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        tree = ast.parse(code)
        has_handler = any(
            isinstance(node, ast.FunctionDef) and node.name == 'handler'
            for node in ast.walk(tree)
        )
        if not has_handler:
            print_error(f"{file_path} no tiene función 'handler'")
            return False
        return True
    except Exception as e:
        print_error(f"Error validando handler en {file_path}: {e}")
        return False

def parse_simple_yaml(file_path):
    """Parser simple de YAML para validación básica"""
    config = {'functions': {}, 'provider': {'environment': {}}, 'resources': {'Resources': {}}}
    current_section = None
    current_key = None
    in_functions = False
    in_provider_env = False
    in_resources = False
    indent_level = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            stripped = line.strip()
            
            if not stripped or stripped.startswith('#'):
                i += 1
                continue
            
            # Detectar nivel de indentación
            indent = len(line) - len(line.lstrip())
            
            # Detectar secciones principales
            if line.startswith('functions:'):
                in_functions = True
                current_section = 'functions'
            elif line.startswith('provider:'):
                in_functions = False
                current_section = 'provider'
            elif line.startswith('resources:'):
                in_functions = False
                current_section = 'resources'
            elif line.startswith('  Resources:'):
                in_resources = True
            elif in_resources and re.match(r'^    [A-Z]\w+:', line):
                # Recurso (tabla, bucket, etc.)
                match = re.match(r'^    ([A-Z]\w+):', line)
                if match:
                    resource_name = match.group(1)
                    # Detectar tipo
                    if i + 1 < len(lines) and 'Type:' in lines[i + 1]:
                        type_line = lines[i + 1]
                        if 'DynamoDB::Table' in type_line:
                            config['resources']['Resources'][resource_name] = {'Type': 'AWS::DynamoDB::Table'}
                        elif 'S3::Bucket' in type_line:
                            config['resources']['Resources'][resource_name] = {'Type': 'AWS::S3::Bucket'}
            elif line.startswith('  #'):
                # Comentario en sección, continuar
                pass
            elif in_functions and re.match(r'^  [a-zA-Z]\w+:', line):
                # Nueva función Lambda (2 espacios de indentación)
                match = re.match(r'^  ([a-zA-Z]\w+):', line)
                if match:
                    current_key = match.group(1)
                    config['functions'][current_key] = {'handler': '', 'events': []}
            elif in_functions and current_key and 'handler:' in line and indent >= 4:
                # Handler de función
                match = re.search(r'handler:\s*(.+)', line)
                if match:
                    handler_value = match.group(1).strip()
                    config['functions'][current_key]['handler'] = handler_value
            elif current_section == 'provider' and 'environment:' in line:
                in_provider_env = True
            elif in_provider_env and indent >= 4 and re.match(r'^\s+[A-Z_]+:', line):
                # Variable de entorno
                match = re.match(r'^\s+([A-Z_]+):\s*(.+)', line)
                if match:
                    var_name = match.group(1)
                    var_value = match.group(2).strip().strip('"').strip("'")
                    config['provider']['environment'][var_name] = var_value
            elif indent < 2 and not line.startswith(' '):
                # Nueva sección de nivel superior, resetear
                in_functions = False
                in_provider_env = False
                in_resources = False
                current_key = None
            
            i += 1
        
        return config
    except Exception as e:
        print_warning(f"Error parseando YAML (usando validación básica): {e}")
        return config

def validate_serverless_yml():
    """Valida el archivo serverless.yml"""
    print_info("Validando serverless.yml...")
    
    yml_path = Path("serverless.yml")
    if not yml_path.exists():
        print_error("serverless.yml no existe")
        return False
    
    # Validación básica: verificar que el archivo existe y es legible
    try:
        with open(yml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Validaciones básicas de estructura
        if 'functions:' not in content:
            print_error("serverless.yml no tiene sección 'functions'")
            return False
        
        if 'provider:' not in content:
            print_error("serverless.yml no tiene sección 'provider'")
            return False
        
        print_success("serverless.yml tiene estructura básica válida")
        
        # Parsear para validación más detallada
        config = parse_simple_yaml(yml_path)
        if not config:
            print_warning("No se pudo parsear completamente serverless.yml (usando validación básica)")
            # Crear estructura mínima para continuar
            config = {'functions': {}, 'provider': {'environment': {}}, 'resources': {'Resources': {}}}
        
        return config
    except Exception as e:
        print_error(f"Error leyendo serverless.yml: {e}")
        return False

def validate_handlers(config):
    """Valida que todos los handlers existan"""
    print_info("Validando handlers...")
    
    handlers_found = []
    handlers_missing = []
    
    for func_name, func_config in config.get('functions', {}).items():
        handler_path = func_config.get('handler', '')
        if not handler_path:
            print_error(f"Función {func_name} no tiene handler definido")
            handlers_missing.append(func_name)
            continue
        
        # Formato: path/to/file.function
        parts = handler_path.split('.')
        if len(parts) != 2:
            print_error(f"Handler inválido en {func_name}: {handler_path}")
            handlers_missing.append(func_name)
            continue
        
        file_path = parts[0] + '.py'
        func_name_in_file = parts[1]
        
        if not Path(file_path).exists():
            print_error(f"Handler {handler_path} no existe (archivo {file_path} no encontrado)")
            handlers_missing.append(func_name)
            continue
        
        # Validar sintaxis Python
        if not validate_python_syntax(file_path):
            handlers_missing.append(func_name)
            continue
        
        # Validar que tenga función handler
        if func_name_in_file == 'handler' and not validate_handler_function(file_path):
            handlers_missing.append(func_name)
            continue
        
        handlers_found.append(func_name)
        print_success(f"Handler {handler_path} válido")
    
    print_info(f"Handlers válidos: {len(handlers_found)}/{len(config.get('functions', {}))}")
    return len(handlers_missing) == 0

def validate_routes(config):
    """Valida que no haya conflictos de rutas"""
    print_info("Validando rutas HTTP...")
    
    # Leer directamente del archivo para validar rutas
    yml_path = Path("serverless.yml")
    try:
        with open(yml_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except:
        return False
    
    routes = defaultdict(list)
    current_function = None
    current_path = None
    current_method = None
    
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        
        # Detectar función Lambda
        if re.match(r'^  [a-zA-Z]\w+:', line):
            match = re.match(r'^  ([a-zA-Z]\w+):', line)
            if match:
                current_function = match.group(1)
        
        # Detectar path
        if 'path:' in line and current_function:
            match = re.search(r'path:\s*(.+)', line)
            if match:
                current_path = match.group(1).strip()
        
        # Detectar method
        if 'method:' in line and current_function and current_path:
            match = re.search(r'method:\s*(\w+)', line)
            if match:
                current_method = match.group(1).upper()
                if current_path and current_method:
                    key = f"{current_method} {current_path}"
                    routes[key].append(current_function)
                    current_path = None
                    current_method = None
        
        i += 1
    
    conflicts = False
    for route, functions in routes.items():
        if len(functions) > 1:
            print_error(f"Conflicto de ruta: {route} usado por {', '.join(functions)}")
            conflicts = True
    
    if not conflicts and routes:
        print_success(f"Sin conflictos de rutas ({len(routes)} rutas únicas)")
    elif not routes:
        print_warning("No se encontraron rutas HTTP")
    
    return not conflicts

def validate_tables(config):
    """Valida que las tablas estén definidas"""
    print_info("Validando tablas DynamoDB...")
    
    # Leer directamente del archivo para validar tablas
    yml_path = Path("serverless.yml")
    try:
        with open(yml_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        content = ""
    
    required_tables = [
        'OrdersTable', 'KitchenTable', 'DeliveryTable', 'AnalyticsTable',
        'StaffTable', 'MenuItemsTable', 'ProductsTable', 'UsersTable', 'SucursalTable'
    ]
    
    missing_tables = []
    for table_name in required_tables:
        if f"{table_name}:" in content and "AWS::DynamoDB::Table" in content:
            # Verificar que esté cerca del nombre
            table_index = content.find(f"{table_name}:")
            type_index = content.find("AWS::DynamoDB::Table", table_index)
            if type_index != -1 and type_index - table_index < 500:
                print_success(f"Tabla {table_name} definida")
            else:
                print_error(f"Tabla requerida {table_name} no está correctamente definida")
                missing_tables.append(table_name)
        else:
            print_error(f"Tabla requerida {table_name} no está definida")
            missing_tables.append(table_name)
    
    return len(missing_tables) == 0

def validate_buckets(config):
    """Valida que los buckets S3 estén definidos"""
    print_info("Validando buckets S3...")
    
    # Leer directamente del archivo para validar buckets
    yml_path = Path("serverless.yml")
    try:
        with open(yml_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        content = ""
    
    required_buckets = [
        'MenuImagesBucket', 'DeliveryProofBucket', 'OrdersReceiptsBucket',
        'StaffDocsBucket', 'AnalyticsExportsBucket'
    ]
    
    missing_buckets = []
    for bucket_name in required_buckets:
        if f"{bucket_name}:" in content and "AWS::S3::Bucket" in content:
            # Verificar que esté cerca del nombre
            bucket_index = content.find(f"{bucket_name}:")
            type_index = content.find("AWS::S3::Bucket", bucket_index)
            if type_index != -1 and type_index - bucket_index < 500:
                print_success(f"Bucket {bucket_name} definido")
            else:
                print_error(f"Bucket requerido {bucket_name} no está correctamente definido")
                missing_buckets.append(bucket_name)
        else:
            print_error(f"Bucket requerido {bucket_name} no está definido")
            missing_buckets.append(bucket_name)
    
    return len(missing_buckets) == 0

def validate_environment_variables(config):
    """Valida que las variables de entorno estén definidas"""
    print_info("Validando variables de entorno...")
    
    env_vars = config.get('provider', {}).get('environment', {})
    
    required_vars = [
        'EVENT_BUS', 'ORDERS_TABLE', 'KITCHEN_TABLE', 'DELIVERY_TABLE',
        'ANALYTICS_TABLE', 'STAFF_TABLE', 'MENU_TABLE', 'PRODUCTS_TABLE',
        'USERS_TABLE', 'SUCURSAL_TABLE', 'MENU_BUCKET', 'PROOF_BUCKET',
        'RECEIPTS_BUCKET', 'STAFF_BUCKET', 'ANALYTICS_BUCKET'
    ]
    
    missing_vars = []
    for var_name in required_vars:
        if var_name not in env_vars:
            print_error(f"Variable de entorno requerida {var_name} no está definida")
            missing_vars.append(var_name)
        else:
            print_success(f"Variable {var_name} definida")
    
    return len(missing_vars) == 0

def validate_all_python_files():
    """Valida sintaxis de todos los archivos Python"""
    print_info("Validando sintaxis de archivos Python...")
    
    python_files = []
    for root, dirs, files in os.walk('.'):
        # Ignorar directorios comunes
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.serverless']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                python_files.append(file_path)
    
    valid_files = 0
    for file_path in python_files:
        if validate_python_syntax(file_path):
            valid_files += 1
    
    print_info(f"Archivos Python válidos: {valid_files}/{len(python_files)}")
    return valid_files == len(python_files)

def validate_logger():
    """Valida que logger.py existe y es importable"""
    print_info("Validando logger.py...")
    
    logger_path = Path("common/logger.py")
    if not logger_path.exists():
        print_error("common/logger.py no existe")
        return False
    
    if not validate_python_syntax(logger_path):
        print_error("common/logger.py tiene errores de sintaxis")
        return False
    
    # Verificar que tiene las funciones necesarias
    try:
        with open(logger_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        required_functions = ['log_info', 'log_error', 'log_warning', 'lambda_handler_wrapper']
        missing = []
        for func in required_functions:
            if f"def {func}" not in code:
                missing.append(func)
        
        if missing:
            print_error(f"logger.py le faltan funciones: {', '.join(missing)}")
            return False
        
        print_success("logger.py válido y completo")
        return True
    except Exception as e:
        print_error(f"Error validando logger.py: {e}")
        return False

def validate_cloudwatch_config(config):
    """Valida configuración de CloudWatch"""
    print_info("Validando configuración de CloudWatch...")
    
    yml_path = Path("serverless.yml")
    try:
        with open(yml_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        content = ""
    
    issues = []
    
    # Validar logs configurados
    if 'logs:' not in content:
        issues.append("Configuración de logs no encontrada")
    elif 'accessLogging: true' not in content:
        issues.append("accessLogging no está habilitado")
    else:
        print_success("Logs de CloudWatch configurados")
    
    # Validar tracing
    if 'tracing:' not in content:
        issues.append("Tracing (X-Ray) no configurado")
    elif 'lambda: true' not in content:
        issues.append("Tracing de Lambda no habilitado")
    else:
        print_success("Tracing (X-Ray) configurado")
    
    # Validar permisos IAM
    if 'logs:PutLogEvents' not in content:
        issues.append("Permiso logs:PutLogEvents no encontrado")
    elif 'cloudwatch:PutMetricData' not in content:
        issues.append("Permiso cloudwatch:PutMetricData no encontrado")
    else:
        print_success("Permisos de CloudWatch configurados")
    
    if issues:
        for issue in issues:
            print_error(issue)
        return False
    
    return True

def validate_new_functions():
    """Valida que las nuevas funciones existan"""
    print_info("Validando nuevas funciones...")
    
    # Validar update_rider_location
    update_location_path = Path("delivery-svc/update_rider_location.py")
    if not update_location_path.exists():
        print_error("delivery-svc/update_rider_location.py no existe")
        return False
    if not validate_python_syntax(update_location_path):
        return False
    if not validate_handler_function(update_location_path):
        return False
    print_success("update_rider_location.py válido")
    
    # Validar que get_order_status tiene funcionalidad de delivery
    get_status_path = Path("orders-svc/get_order_status.py")
    if get_status_path.exists():
        with open(get_status_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if 'delivery_table' in content and 'last_location' in content:
            print_success("get_order_status.py tiene funcionalidad de delivery")
        else:
            print_warning("get_order_status.py puede no tener funcionalidad completa de delivery")
    
    # Validar que get_delivery_status tiene funcionalidad de location
    get_delivery_path = Path("delivery-svc/get_delivery_status.py")
    if get_delivery_path.exists():
        with open(get_delivery_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if 'last_location' in content or 'location' in content:
            print_success("get_delivery_status.py tiene funcionalidad de ubicación")
        else:
            print_warning("get_delivery_status.py puede no tener funcionalidad de ubicación")
    
    return True

def validate_logger_imports():
    """Valida que las funciones que usan logger puedan importarlo"""
    print_info("Validando imports de logger...")
    
    logger_path = Path("common/logger.py")
    if not logger_path.exists():
        print_warning("logger.py no existe, saltando validación de imports")
        return True
    
    # Buscar funciones que importan logger
    functions_with_logger = []
    for service_dir in ['orders-svc', 'kitchen-svc', 'delivery-svc', 'analytics-svc', 'register']:
        if not Path(service_dir).exists():
            continue
        for py_file in Path(service_dir).glob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                if 'from common.logger' in content or 'import common.logger' in content:
                    functions_with_logger.append(py_file)
            except:
                pass
    
    if functions_with_logger:
        print_success(f"{len(functions_with_logger)} funciones usan logger")
        # Verificar que el import sea correcto
        for func_path in functions_with_logger[:3]:  # Verificar primeras 3
            with open(func_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if 'sys.path.append' in content or 'from common.logger' in content:
                print_success(f"{func_path.name} tiene import correcto de logger")
    else:
        print_warning("Ninguna función usa logger aún (opcional)")
    
    return True

def main():
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}VALIDACIÓN DEL PROYECTO SERVERLESS{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    # Validar serverless.yml
    config = validate_serverless_yml()
    if not config:
        print(f"\n{RED}Validación fallida: serverless.yml inválido{RESET}\n")
        sys.exit(1)
    
    print()
    
    # Validar handlers
    if not validate_handlers(config):
        print_warning("Algunos handlers tienen problemas")
    
    print()
    
    # Validar rutas
    if not validate_routes(config):
        print_warning("Hay conflictos de rutas")
    
    print()
    
    # Validar tablas
    if not validate_tables(config):
        print_warning("Faltan algunas tablas")
    
    print()
    
    # Validar buckets
    if not validate_buckets(config):
        print_warning("Faltan algunos buckets")
    
    print()
    
    # Validar variables de entorno
    if not validate_environment_variables(config):
        print_warning("Faltan algunas variables de entorno")
    
    print()
    
    # Validar sintaxis Python
    if not validate_all_python_files():
        print_warning("Algunos archivos Python tienen problemas de sintaxis")
    
    print()
    
    # Validar logger.py
    if not validate_logger():
        print_warning("Problemas con logger.py")
    
    print()
    
    # Validar CloudWatch
    if not validate_cloudwatch_config(config):
        print_warning("Problemas con configuración de CloudWatch")
    
    print()
    
    # Validar nuevas funciones
    if not validate_new_functions():
        print_warning("Problemas con nuevas funciones")
    
    print()
    
    if not validate_logger_imports():
        print_warning("Problemas con imports de logger")
    
    print()
    print(f"{BLUE}{'='*60}{RESET}")
    
    if errors:
        print(f"\n{RED}ERRORES ENCONTRADOS: {len(errors)}{RESET}")
        for error in errors:
            print(f"  {RED}✗{RESET} {error}")
    
    if warnings:
        print(f"\n{YELLOW}ADVERTENCIAS: {len(warnings)}{RESET}")
        for warning in warnings:
            print(f"  {YELLOW}⚠{RESET} {warning}")
    
    if not errors and not warnings:
        print(f"\n{GREEN}✓ TODAS LAS VALIDACIONES PASARON{RESET}\n")
        sys.exit(0)
    elif not errors:
        print(f"\n{YELLOW}Validación completada con advertencias{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{RED}Validación fallida{RESET}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
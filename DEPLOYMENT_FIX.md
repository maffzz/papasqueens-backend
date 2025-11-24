# 🔧 Solución al Error 502 - CORS y Dependencias

## 🎯 Problema Identificado

El error **502 Bad Gateway** ocurre porque:

1. ✅ **CORS está correctamente implementado** en todas las Lambdas (48/48)
2. ❌ **Las dependencias Python no se están empaquetando** correctamente
3. ❌ **bcrypt requiere compilación nativa** para Lambda

## 🛠️ Soluciones

### Opción 1: Usar Serverless Python Requirements Plugin (Recomendado)

1. **Instalar el plugin:**

```bash
npm install --save-dev serverless-python-requirements
```

2. **Agregar al serverless.yml:**

```yaml
plugins:
  - serverless-python-requirements

custom:
  pythonRequirements:
    dockerizePip: true
    layer: true
```

3. **Desplegar:**

```bash
serverless deploy --stage dev
```

### Opción 2: Empaquetar Manualmente con Docker

```bash
# Crear directorio para dependencias
mkdir -p .build/python

# Instalar dependencias usando Docker (para compatibilidad con Lambda)
docker run --rm -v "$PWD":/var/task public.ecr.aws/lambda/python:3.13 \
  pip install -r requirements.txt -t .build/python

# Crear layer
cd .build
zip -r ../python-deps.zip python
cd ..

# Subir layer a AWS Lambda manualmente o via serverless.yml
```

### Opción 3: Usar bcrypt-lambda (Más Simple)

1. **Cambiar requirements.txt:**

```txt
boto3
botocore
bcrypt-lambda
```

2. **Actualizar imports en staff_login.py y customer_login.py:**

```python
# Cambiar:
import bcrypt

# Por:
try:
    import bcrypt
except ImportError:
    # Fallback para Lambda
    import bcrypt_lambda as bcrypt
```

### Opción 4: Desplegar con Dependencias Pre-compiladas

1. **Crear package.sh:**

```bash
#!/bin/bash
# Instalar dependencias en carpeta local
pip install -r requirements.txt -t ./vendor

# Crear zip para cada función
for dir in *-svc register; do
  if [ -d "$dir" ]; then
    cd $dir
    zip -r ../${dir}.zip . -x "*.pyc" -x "__pycache__/*"
    cd ..
    # Agregar vendor al zip
    cd vendor
    zip -r ../${dir}.zip . -x "*.pyc" -x "__pycache__/*"
    cd ..
  fi
done
```

## 🚀 Solución Rápida (Para Probar Ahora)

### Paso 1: Verificar que bcrypt funciona localmente

```bash
python -c "import bcrypt; print('bcrypt OK')"
```

### Paso 2: Desplegar solo la función de login

```bash
serverless deploy function -f staffLogin --stage dev
```

### Paso 3: Ver logs en tiempo real

```bash
serverless logs -f staffLogin --stage dev --tail
```

## 🔍 Diagnóstico del Error 502

El error 502 puede deberse a:

1. **Import Error**: bcrypt no se puede importar
2. **Timeout**: La función tarda más de 29 segundos
3. **Memory Error**: No hay suficiente memoria
4. **Syntax Error**: Error de sintaxis en el código

### Ver logs de CloudWatch:

```bash
# Ver últimos logs
aws logs tail /aws/lambda/papasqueens-platform-dev-staffLogin --follow

# O con serverless
serverless logs -f staffLogin --stage dev
```

## ✅ Verificación Post-Despliegue

1. **Test desde CLI:**

```bash
curl -X POST https://aiu2bl6xja.execute-api.us-east-1.amazonaws.com/dev/auth/staff/login \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:5174" \
  -d '{
    "username": "test@example.com",
    "password": "test123",
    "tenant_id": "default"
  }'
```

2. **Verificar headers CORS en respuesta:**

```bash
curl -I -X OPTIONS https://aiu2bl6xja.execute-api.us-east-1.amazonaws.com/dev/auth/staff/login \
  -H "Origin: http://localhost:5174" \
  -H "Access-Control-Request-Method: POST"
```

## 📝 Cambios Realizados

### ✅ Archivos Corregidos:

- `register/staff_login.py` - cors_headers movido antes del try
- `register/customer_login.py` - cors_headers movido antes del try
- Todos los demás handlers ya tenían CORS correctamente

### 🔄 Próximos Pasos:

1. Elegir una de las opciones de empaquetado
2. Desplegar las funciones
3. Verificar logs de CloudWatch
4. Probar desde el frontend

## 🆘 Si el Problema Persiste

1. **Verificar IAM Role**: Asegúrate de que LabRole tiene permisos para DynamoDB
2. **Verificar Variables de Entorno**: STAFF_TABLE debe estar definida
3. **Verificar Tabla DynamoDB**: La tabla Staff debe existir
4. **Simplificar el handler**: Comentar temporalmente la lógica de bcrypt para aislar el problema

### Handler Simplificado para Testing:

```python
def handler(event, context):
    headers = event.get('headers', {}) or {}
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "*",
        "Content-Type": "application/json",
    }
    
    return {
        "statusCode": 200,
        "headers": cors_headers,
        "body": json.dumps({"message": "Test OK", "event": str(event)[:200]})
    }
```

Despliega esto temporalmente para verificar que CORS funciona, luego restaura la lógica completa.

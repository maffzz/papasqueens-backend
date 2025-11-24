#!/bin/bash

echo "🔍 Verificando bcrypt en diferentes lugares..."
echo ""

# 1. Local (tu máquina)
echo "1️⃣ bcrypt en tu máquina local:"
python -c "import bcrypt; print('   ✅ Instalado:', bcrypt.__version__)" 2>/dev/null || echo "   ❌ NO instalado"
echo ""

# 2. requirements.txt
echo "2️⃣ bcrypt en requirements.txt:"
if grep -q "bcrypt" requirements.txt; then
    echo "   ✅ Listado en requirements.txt"
    grep "bcrypt" requirements.txt
else
    echo "   ❌ NO está en requirements.txt"
fi
echo ""

# 3. Plugin de Serverless
echo "3️⃣ Plugin serverless-python-requirements:"
if [ -d "node_modules/serverless-python-requirements" ]; then
    echo "   ✅ Plugin instalado"
else
    echo "   ❌ Plugin NO instalado - Ejecuta: npm install"
fi
echo ""

# 4. Configuración en serverless.yml
echo "4️⃣ Configuración en serverless.yml:"
if grep -q "serverless-python-requirements" serverless.yml; then
    echo "   ✅ Plugin configurado en serverless.yml"
else
    echo "   ❌ Plugin NO configurado"
fi
echo ""

# 5. Lambda Layer (si ya desplegaste)
echo "5️⃣ Lambda Layer en AWS:"
aws lambda get-function-configuration \
  --function-name papasqueens-platform-dev-staffLogin \
  --query 'Layers' 2>/dev/null && echo "   ✅ Layer encontrado" || echo "   ❌ Sin Layer o función no existe"
echo ""

echo "📋 Resumen:"
echo "- Si todo está ✅ excepto Lambda Layer: Ejecuta 'serverless deploy --stage dev --force'"
echo "- Si el plugin NO está instalado: Ejecuta 'npm install'"
echo "- Si bcrypt NO está local: Ejecuta 'pip install -r requirements.txt'"

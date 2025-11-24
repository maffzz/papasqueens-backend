#!/bin/bash

echo "🔍 Verificando estado del despliegue..."
echo ""

# Verificar si npm install se ejecutó
if [ -d "node_modules" ]; then
    echo "✅ node_modules existe"
else
    echo "❌ node_modules NO existe - Ejecuta: npm install"
fi

# Verificar si serverless está instalado
if command -v serverless &> /dev/null; then
    echo "✅ Serverless CLI instalado"
    serverless --version
else
    echo "❌ Serverless CLI NO instalado"
fi

# Verificar si el plugin está instalado
if [ -d "node_modules/serverless-python-requirements" ]; then
    echo "✅ Plugin serverless-python-requirements instalado"
else
    echo "❌ Plugin serverless-python-requirements NO instalado"
fi

echo ""
echo "📋 Próximos pasos:"
echo "1. npm install"
echo "2. npx serverless deploy --stage dev"
echo ""
echo "O para despliegue rápido de solo login:"
echo "npx serverless deploy function -f staffLogin --stage dev"

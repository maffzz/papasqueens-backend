#!/bin/bash

echo "📋 Obteniendo logs de la función staffLogin..."
echo ""

# Ver últimos logs
npx serverless logs -f staffLogin --stage dev --tail

# Si no funciona, usar AWS CLI directamente
# aws logs tail /aws/lambda/papasqueens-platform-dev-staffLogin --follow

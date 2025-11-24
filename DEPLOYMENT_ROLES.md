# 🚀 Deployment - Separación de Roles

## ✅ Cambios Realizados en el YML

### 1. Nuevo Endpoint: Dashboard por Rol
```yaml
getDashboardByRole:
  handler: kitchen-svc/get_dashboard_by_role.handler
  path: /kitchen/dashboard
  method: GET
```

**Headers requeridos:**
- `X-Tenant-Id`
- `X-User-Id`
- `X-User-Type`
- `X-User-Role` ← **NUEVO**
- `Authorization`

### 2. Headers CORS Actualizados

Se agregó `X-User-Role` a los endpoints que validan roles:

- ✅ `POST /kitchen/orders/{order_id}/accept` (solo cocineros)
- ✅ `POST /kitchen/orders/{order_id}/pack` (solo empaquetadores)
- ✅ `GET /kitchen/dashboard` (todos los roles)

---

## 📦 Archivos Modificados

### Backend (Lambda Functions)
1. ✅ `kitchen-svc/accept_order.py` - Validación de rol cocinero
2. ✅ `kitchen-svc/pack_order.py` - Validación de rol empaquetador
3. ✅ `kitchen-svc/manage_staff.py` - Roles válidos actualizados
4. ✅ `register/staff_login.py` - Retorna X-User-Role en headers_required
5. ✅ `kitchen-svc/get_dashboard_by_role.py` - **NUEVO** Dashboard personalizado

### Configuración
6. ✅ `functions.yml` - Nuevo endpoint y headers CORS
7. ✅ `serverless.yml` - Sin cambios (usa functions.yml)

### Scripts de Seed
8. ✅ `seed_staff.py` - Seed con 4 roles (cocinero, empaquetador, delivery, admin)
9. ✅ `delete_seed_staff.py` - Script para limpiar seed
10. ✅ `clean_all_staff.py` - Limpieza rápida

### Documentación
11. ✅ `ROLES_SEPARATION_GUIDE.md` - Guía completa de roles
12. ✅ `CREDENCIALES_SEED.md` - Credenciales para testing

---

## 🚀 Pasos para Desplegar

### 1. Verificar Cambios
```bash
# Ver qué archivos cambiaron
git status

# Ver diferencias
git diff functions.yml
git diff kitchen-svc/accept_order.py
git diff register/staff_login.py
```

### 2. Desplegar a AWS
```bash
# Desplegar todo
npx serverless deploy --stage dev

# O desplegar solo las funciones modificadas (más rápido)
npx serverless deploy function -f acceptOrder --stage dev
npx serverless deploy function -f packOrder --stage dev
npx serverless deploy function -f staffLogin --stage dev
npx serverless deploy function -f getDashboardByRole --stage dev
```

### 3. Ejecutar Seed
```bash
# Limpiar datos antiguos (opcional)
python delete_seed_staff.py

# Crear nuevo seed con roles correctos
python seed_staff.py
```

### 4. Verificar Deployment
```bash
# Ver logs de una función
npx serverless logs -f staffLogin --stage dev --tail

# Verificar endpoints
curl https://YOUR-API-URL/dev/health
```

---

## 🧪 Testing Post-Deployment

### 1. Test Login con Roles
```bash
# Login como cocinero
curl -X POST https://YOUR-API-URL/dev/auth/staff/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "cocinero1@tenant_pq_barranco.papasqueens.test",
    "password": "123456",
    "tenant_id": "tenant_pq_barranco"
  }'

# Debe retornar:
# {
#   "role": "cocinero",
#   "headers_required": {
#     "X-User-Role": "cocinero"  ← Verificar esto
#   }
# }
```

### 2. Test Dashboard por Rol
```bash
# Dashboard de cocinero
curl -X GET https://YOUR-API-URL/dev/kitchen/dashboard \
  -H "X-Tenant-Id: tenant_pq_barranco" \
  -H "X-User-Id: tenant_pq_barranco_cocinero1" \
  -H "X-User-Type: staff" \
  -H "X-User-Role: cocinero" \
  -H "Authorization: Bearer <token>"

# Debe retornar:
# {
#   "role": "cocinero",
#   "pendientes_aceptar": {...},
#   "en_preparacion": {...}
# }
```

### 3. Test Validación de Permisos
```bash
# Cocinero intenta empacar (debe fallar)
curl -X POST https://YOUR-API-URL/dev/kitchen/orders/ORDER-123/pack \
  -H "X-Tenant-Id: tenant_pq_barranco" \
  -H "X-User-Id: tenant_pq_barranco_cocinero1" \
  -H "X-User-Type: staff" \
  -H "X-User-Role: cocinero" \
  -H "Authorization: Bearer <token>"

# Debe retornar:
# {
#   "statusCode": 403,
#   "error": "Solo empaquetadores pueden empacar pedidos"
# }
```

---

## 📊 Endpoints Nuevos/Modificados

### Nuevo Endpoint
```
GET /kitchen/dashboard
```
**Descripción:** Dashboard personalizado según el rol del usuario
**Roles:** cocinero, empaquetador, delivery, admin
**Response:** Diferente según el rol

### Endpoints con Validación de Rol
```
POST /kitchen/orders/{order_id}/accept
```
**Roles permitidos:** cocinero, admin
**Error 403:** Si el rol no es válido

```
POST /kitchen/orders/{order_id}/pack
```
**Roles permitidos:** empaquetador, admin
**Error 403:** Si el rol no es válido

---

## 🔄 Rollback (si algo falla)

### Opción 1: Rollback completo
```bash
# Ver deployments anteriores
npx serverless deploy list --stage dev

# Rollback al deployment anterior
npx serverless rollback --timestamp TIMESTAMP --stage dev
```

### Opción 2: Rollback de función específica
```bash
# Revertir solo una función
npx serverless rollback function -f getDashboardByRole --stage dev
```

### Opción 3: Revertir código manualmente
```bash
# Volver al commit anterior
git revert HEAD

# Redesplegar
npx serverless deploy --stage dev
```

---

## ⚠️ Troubleshooting

### Error: "X-User-Role header not found"
**Solución:** Asegúrate de que el frontend envíe el header después del login

### Error: "Solo cocineros pueden aceptar pedidos"
**Solución:** Verifica que el usuario tenga role="cocinero" en DynamoDB

### Error: "Dashboard returns empty"
**Solución:** Verifica que haya datos en las tablas Kitchen/Delivery

### Error: "CORS error"
**Solución:** Verifica que X-User-Role esté en la lista de headers CORS

---

## 📝 Checklist de Deployment

- [ ] Código actualizado en todos los archivos
- [ ] `functions.yml` tiene el nuevo endpoint
- [ ] Headers CORS incluyen `X-User-Role`
- [ ] Seed ejecutado con roles correctos
- [ ] Login retorna `X-User-Role` en headers_required
- [ ] Dashboard funciona para cada rol
- [ ] Validaciones de permisos funcionan (403 cuando corresponde)
- [ ] Logs de CloudWatch muestran ejecuciones correctas
- [ ] Frontend actualizado para enviar `X-User-Role`

---

## 🎯 Próximos Pasos

1. **Frontend:** Actualizar para usar `X-User-Role` del login
2. **Testing:** Crear tests automatizados para cada rol
3. **Monitoring:** Configurar alertas para errores 403
4. **Documentación:** Actualizar API docs con nuevos endpoints
5. **Seguridad:** Revisar que JWT incluya el rol

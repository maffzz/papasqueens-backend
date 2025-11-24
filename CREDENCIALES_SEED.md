# 🔐 Credenciales del Seed - Papas Queen's

## 📋 Password Universal
**Todos los usuarios tienen el mismo password:** `123456`

---

## 🏪 Sede: Barranco (UTEC)
**Tenant ID:** `tenant_pq_barranco`

### 👔 Administradores
```
Email:    admin1@tenant_pq_barranco.papasqueens.test
Password: 123456
Role:     admin
```
```
Email:    admin2@tenant_pq_barranco.papasqueens.test
Password: 123456
Role:     admin
```

### 👨‍🍳 Cocineros
```
Email:    cocinero1@tenant_pq_barranco.papasqueens.test
Password: 123456
Role:     cocinero
```
```
Email:    cocinero2@tenant_pq_barranco.papasqueens.test
Password: 123456
Role:     cocinero
```
```
Email:    cocinero3@tenant_pq_barranco.papasqueens.test
Password: 123456
Role:     cocinero
```

### 📦 Empaquetadores
```
Email:    empaquetador1@tenant_pq_barranco.papasqueens.test
Password: 123456
Role:     empaquetador
```
```
Email:    empaquetador2@tenant_pq_barranco.papasqueens.test
Password: 123456
Role:     empaquetador
```

### 🚚 Repartidores
```
Email:    delivery1@tenant_pq_barranco.papasqueens.test
Password: 123456
Role:     delivery
```
```
Email:    delivery2@tenant_pq_barranco.papasqueens.test
Password: 123456
Role:     delivery
```
```
Email:    delivery3@tenant_pq_barranco.papasqueens.test
Password: 123456
Role:     delivery
```

---

## 🏪 Sede: Puruchuco
**Tenant ID:** `tenant_pq_puruchuco`

### 👔 Administradores
```
admin1@tenant_pq_puruchuco.papasqueens.test / 123456
admin2@tenant_pq_puruchuco.papasqueens.test / 123456
```

### 👨‍🍳 Cocineros
```
cocinero1@tenant_pq_puruchuco.papasqueens.test / 123456
cocinero2@tenant_pq_puruchuco.papasqueens.test / 123456
cocinero3@tenant_pq_puruchuco.papasqueens.test / 123456
```

### 📦 Empaquetadores
```
empaquetador1@tenant_pq_puruchuco.papasqueens.test / 123456
empaquetador2@tenant_pq_puruchuco.papasqueens.test / 123456
```

### 🚚 Repartidores
```
delivery1@tenant_pq_puruchuco.papasqueens.test / 123456
delivery2@tenant_pq_puruchuco.papasqueens.test / 123456
delivery3@tenant_pq_puruchuco.papasqueens.test / 123456
```

---

## 🏪 Sede: Villa María
**Tenant ID:** `tenant_pq_villamaria`

### 👔 Administradores
```
admin1@tenant_pq_villamaria.papasqueens.test / 123456
admin2@tenant_pq_villamaria.papasqueens.test / 123456
```

### 👨‍🍳 Cocineros
```
cocinero1@tenant_pq_villamaria.papasqueens.test / 123456
cocinero2@tenant_pq_villamaria.papasqueens.test / 123456
cocinero3@tenant_pq_villamaria.papasqueens.test / 123456
```

### 📦 Empaquetadores
```
empaquetador1@tenant_pq_villamaria.papasqueens.test / 123456
empaquetador2@tenant_pq_villamaria.papasqueens.test / 123456
```

### 🚚 Repartidores
```
delivery1@tenant_pq_villamaria.papasqueens.test / 123456
delivery2@tenant_pq_villamaria.papasqueens.test / 123456
delivery3@tenant_pq_villamaria.papasqueens.test / 123456
```

---

## 🏪 Sede: Jirón
**Tenant ID:** `tenant_pq_jiron`

### 👔 Administradores
```
admin1@tenant_pq_jiron.papasqueens.test / 123456
admin2@tenant_pq_jiron.papasqueens.test / 123456
```

### 👨‍🍳 Cocineros
```
cocinero1@tenant_pq_jiron.papasqueens.test / 123456
cocinero2@tenant_pq_jiron.papasqueens.test / 123456
cocinero3@tenant_pq_jiron.papasqueens.test / 123456
```

### 📦 Empaquetadores
```
empaquetador1@tenant_pq_jiron.papasqueens.test / 123456
empaquetador2@tenant_pq_jiron.papasqueens.test / 123456
```

### 🚚 Repartidores
```
delivery1@tenant_pq_jiron.papasqueens.test / 123456
delivery2@tenant_pq_jiron.papasqueens.test / 123456
delivery3@tenant_pq_jiron.papasqueens.test / 123456
```

---

## 🧪 Ejemplos de Prueba con cURL

### Login como Cocinero
```bash
curl -X POST https://api.papasqueens.com/auth/staff/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "cocinero1@tenant_pq_barranco.papasqueens.test",
    "password": "123456",
    "tenant_id": "tenant_pq_barranco"
  }'
```

### Login como Empaquetador
```bash
curl -X POST https://api.papasqueens.com/auth/staff/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "empaquetador1@tenant_pq_barranco.papasqueens.test",
    "password": "123456",
    "tenant_id": "tenant_pq_barranco"
  }'
```

### Login como Delivery
```bash
curl -X POST https://api.papasqueens.com/auth/staff/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "delivery1@tenant_pq_barranco.papasqueens.test",
    "password": "123456",
    "tenant_id": "tenant_pq_barranco"
  }'
```

### Login como Admin
```bash
curl -X POST https://api.papasqueens.com/auth/staff/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin1@tenant_pq_barranco.papasqueens.test",
    "password": "123456",
    "tenant_id": "tenant_pq_barranco"
  }'
```

---

## 📊 Resumen

| Sede | Tenant ID | Admins | Cocineros | Empaquetadores | Delivery | Total |
|------|-----------|--------|-----------|----------------|----------|-------|
| Barranco | tenant_pq_barranco | 2 | 3 | 2 | 3 | **10** |
| Puruchuco | tenant_pq_puruchuco | 2 | 3 | 2 | 3 | **10** |
| Villa María | tenant_pq_villamaria | 2 | 3 | 2 | 3 | **10** |
| Jirón | tenant_pq_jiron | 2 | 3 | 2 | 3 | **10** |
| **TOTAL** | | **8** | **12** | **8** | **12** | **40** |

---

## 🎯 Casos de Prueba Recomendados

### 1. Flujo Completo de Cocina
```
1. Login como cocinero1@tenant_pq_barranco.papasqueens.test
2. Ver dashboard (debe mostrar pedidos pendientes)
3. Aceptar un pedido
4. Ver dashboard (debe mostrar pedido en preparación)

5. Login como empaquetador1@tenant_pq_barranco.papasqueens.test
6. Ver dashboard (debe mostrar pedido listo para empacar)
7. Empacar el pedido
8. Ver dashboard (debe mostrar pedido empacado)
```

### 2. Validación de Permisos
```
1. Login como cocinero1
2. Intentar empacar un pedido → Debe fallar (403)

3. Login como empaquetador1
4. Intentar aceptar un pedido → Debe fallar (403)
```

### 3. Dashboard por Rol
```
1. Login como cocinero1 → Dashboard muestra solo cocina
2. Login como empaquetador1 → Dashboard muestra solo empaque
3. Login como delivery1 → Dashboard muestra solo entregas
4. Login como admin1 → Dashboard muestra todo
```

---

## 🔑 Patrón de Emails

```
{rol}{numero}@{tenant_id}.papasqueens.test
```

**Ejemplos:**
- `cocinero1@tenant_pq_barranco.papasqueens.test`
- `empaquetador2@tenant_pq_puruchuco.papasqueens.test`
- `delivery3@tenant_pq_villamaria.papasqueens.test`
- `admin1@tenant_pq_jiron.papasqueens.test`

---

## ⚠️ Notas Importantes

1. **Password único:** Todos usan `123456` (solo para desarrollo)
2. **Tenant requerido:** Siempre incluir `tenant_id` en el login
3. **Roles case-sensitive:** Usar exactamente `cocinero`, `empaquetador`, `delivery`, `admin`
4. **Headers requeridos:** Después del login, usar `X-User-Role` en todas las peticiones

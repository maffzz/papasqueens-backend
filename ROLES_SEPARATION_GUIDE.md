# Guía de Separación de Roles: Cocinero y Empaquetador

## 📋 Resumen de Cambios

Se han separado los roles de **cocinero** y **empaquetador** en el sistema Papas Queen's para reflejar mejor el flujo operativo real de la cocina.

---

## 🎭 Roles Disponibles

| Rol | Descripción | Permisos |
|-----|-------------|----------|
| **cocinero** | Prepara los pedidos | Aceptar pedidos, marcar como en preparación |
| **empaquetador** | Empaca pedidos listos | Empacar pedidos preparados, marcar como listo para entrega |
| **delivery** | Entrega pedidos | Asignar entregas, actualizar ubicación, confirmar entrega |
| **admin** | Administrador | Acceso completo a todas las funciones |

---

## 🔐 Login y Autenticación

### Endpoint de Login
```
POST /auth/staff/login
```

### Request Body
```json
{
  "username": "juan.perez@papasqueens.com",
  "password": "miPassword123",
  "tenant_id": "tenant_pq_barranco"
}
```

### Response - Cocinero
```json
{
  "message": "Login exitoso",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": "Juan Pérez",
  "role": "cocinero",
  "id_staff": "staff-001",
  "tenant_id": "tenant_pq_barranco",
  "headers_required": {
    "X-User-Id": "staff-001",
    "X-User-Type": "staff",
    "X-User-Email": "juan.perez@papasqueens.com",
    "X-User-Role": "cocinero"
  }
}
```

### Response - Empaquetador
```json
{
  "message": "Login exitoso",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": "María García",
  "role": "empaquetador",
  "id_staff": "staff-002",
  "tenant_id": "tenant_pq_barranco",
  "headers_required": {
    "X-User-Id": "staff-002",
    "X-User-Type": "staff",
    "X-User-Email": "maria.garcia@papasqueens.com",
    "X-User-Role": "empaquetador"
  }
}
```

### Response - Delivery
```json
{
  "message": "Login exitoso",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": "Carlos Ruiz",
  "role": "delivery",
  "id_staff": "staff-003",
  "tenant_id": "tenant_pq_barranco",
  "headers_required": {
    "X-User-Id": "staff-003",
    "X-User-Type": "staff",
    "X-User-Email": "carlos.ruiz@papasqueens.com",
    "X-User-Role": "delivery"
  }
}
```

---

## 📊 Dashboard por Rol

### Endpoint de Dashboard
```
GET /kitchen/dashboard
```

### Headers Requeridos
```
X-Tenant-Id: tenant_pq_barranco
X-User-Id: staff-001
X-User-Type: staff
X-User-Role: cocinero
Authorization: Bearer <token>
```

---

## 👨‍🍳 Dashboard de Cocinero

### Request
```bash
curl -X GET https://api.papasqueens.com/kitchen/dashboard \
  -H "X-Tenant-Id: tenant_pq_barranco" \
  -H "X-User-Id: staff-001" \
  -H "X-User-Type: staff" \
  -H "X-User-Role: cocinero" \
  -H "Authorization: Bearer <token>"
```

### Response
```json
{
  "role": "cocinero",
  "user_id": "staff-001",
  "tenant_id": "tenant_pq_barranco",
  "pendientes_aceptar": {
    "count": 3,
    "items": [
      {
        "order_id": "order-123",
        "tenant_id": "tenant_pq_barranco",
        "status": "recibido",
        "customer_name": "Cliente A",
        "delivery_address": "Av. Principal 123",
        "created_at": "2025-11-24T10:30:00Z"
      }
    ]
  },
  "en_preparacion": {
    "count": 2,
    "items": [
      {
        "order_id": "order-120",
        "status": "en_preparacion",
        "accepted_by": "staff-001",
        "accepted_at": "2025-11-24T10:15:00Z",
        "customer_name": "Cliente B"
      }
    ]
  },
  "completados_recientes": {
    "count": 5,
    "items": [...]
  }
}
```

### Acciones Permitidas
- ✅ Ver pedidos pendientes de aceptar
- ✅ Aceptar pedidos (`POST /kitchen/orders/{order_id}/accept`)
- ✅ Ver sus pedidos en preparación
- ❌ NO puede empacar pedidos

---

## 📦 Dashboard de Empaquetador

### Request
```bash
curl -X GET https://api.papasqueens.com/kitchen/dashboard \
  -H "X-Tenant-Id: tenant_pq_barranco" \
  -H "X-User-Id: staff-002" \
  -H "X-User-Type: staff" \
  -H "X-User-Role: empaquetador" \
  -H "Authorization: Bearer <token>"
```

### Response
```json
{
  "role": "empaquetador",
  "user_id": "staff-002",
  "tenant_id": "tenant_pq_barranco",
  "listos_para_empacar": {
    "count": 4,
    "items": [
      {
        "order_id": "order-120",
        "tenant_id": "tenant_pq_barranco",
        "status": "en_preparacion",
        "accepted_by": "staff-001",
        "accepted_by_role": "cocinero",
        "customer_name": "Cliente B",
        "delivery_address": "Calle Secundaria 456"
      }
    ]
  },
  "empacados_recientes": {
    "count": 8,
    "items": [
      {
        "order_id": "order-115",
        "status": "listo_para_entrega",
        "packed_by": "staff-002",
        "packed_by_role": "empaquetador",
        "packed_at": "2025-11-24T10:25:00Z"
      }
    ]
  }
}
```

### Acciones Permitidas
- ✅ Ver pedidos listos para empacar (en_preparacion)
- ✅ Empacar pedidos (`POST /kitchen/orders/{order_id}/pack`)
- ✅ Ver sus pedidos empacados
- ❌ NO puede aceptar pedidos nuevos

---

## 🚚 Dashboard de Delivery

### Request
```bash
curl -X GET https://api.papasqueens.com/kitchen/dashboard \
  -H "X-Tenant-Id: tenant_pq_barranco" \
  -H "X-User-Id: staff-003" \
  -H "X-User-Type: staff" \
  -H "X-User-Role: delivery" \
  -H "Authorization: Bearer <token>"
```

### Response
```json
{
  "role": "delivery",
  "user_id": "staff-003",
  "tenant_id": "tenant_pq_barranco",
  "entregas_activas": {
    "count": 1,
    "items": [
      {
        "id_delivery": "del-456",
        "id_order": "order-115",
        "status": "en_camino",
        "direccion": "Av. Los Olivos 789",
        "customer_name": "Cliente C",
        "tiempo_salida": "2025-11-24T10:30:00Z"
      }
    ]
  },
  "entregas_completadas": {
    "count": 12,
    "items": [...]
  }
}
```

### Acciones Permitidas
- ✅ Ver entregas asignadas
- ✅ Actualizar ubicación GPS
- ✅ Confirmar entregas
- ❌ NO puede acceder a funciones de cocina

---

## 👔 Dashboard de Admin

### Request
```bash
curl -X GET https://api.papasqueens.com/kitchen/dashboard \
  -H "X-Tenant-Id: tenant_pq_barranco" \
  -H "X-User-Id: admin-001" \
  -H "X-User-Type: staff" \
  -H "X-User-Role: admin" \
  -H "Authorization: Bearer <token>"
```

### Response
```json
{
  "role": "admin",
  "user_id": "admin-001",
  "tenant_id": "tenant_pq_barranco",
  "resumen_cocina": {
    "total": 25,
    "por_estado": {
      "recibido": 3,
      "en_preparacion": 5,
      "listo_para_entrega": 2,
      "entregado": 15
    }
  },
  "todos_pedidos": [...]
}
```

### Acciones Permitidas
- ✅ Acceso completo a todas las funciones
- ✅ Ver todos los pedidos
- ✅ Gestionar personal
- ✅ Ver métricas y analytics

---

## 🔧 Crear Usuarios con Roles

### Usando create-admin.py
```bash
# Crear cocinero
python create-admin.py tenant_pq_barranco juan.perez@papasqueens.com password123 "Juan Pérez"
# Luego actualizar el rol en DynamoDB a "cocinero"

# Crear empaquetador
python create-admin.py tenant_pq_barranco maria.garcia@papasqueens.com password456 "María García"
# Luego actualizar el rol en DynamoDB a "empaquetador"
```

### Usando API (requiere admin)
```bash
# Crear cocinero
curl -X POST https://api.papasqueens.com/staff \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant_pq_barranco",
    "name": "Juan Pérez",
    "email": "juan.perez@papasqueens.com",
    "role": "cocinero",
    "password": "password123",
    "status": "activo"
  }'

# Crear empaquetador
curl -X POST https://api.papasqueens.com/staff \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant_pq_barranco",
    "name": "María García",
    "email": "maria.garcia@papasqueens.com",
    "role": "empaquetador",
    "password": "password456",
    "status": "activo"
  }'
```

---

## 🔒 Validaciones de Seguridad

### Aceptar Pedido (solo cocineros)
```
POST /kitchen/orders/{order_id}/accept
```
- ✅ Permitido: role = "cocinero" o "admin"
- ❌ Rechazado: role = "empaquetador" o "delivery"
- Error: `403 - Solo cocineros pueden aceptar pedidos`

### Empacar Pedido (solo empaquetadores)
```
POST /kitchen/orders/{order_id}/pack
```
- ✅ Permitido: role = "empaquetador" o "admin"
- ❌ Rechazado: role = "cocinero" o "delivery"
- Error: `403 - Solo empaquetadores pueden empacar pedidos`

---

## 📈 Métricas por Rol

El sistema ahora registra:
- `accepted_by_role`: "cocinero" (quién aceptó el pedido)
- `packed_by_role`: "empaquetador" (quién empacó el pedido)

Esto permite analytics más precisos:
- Tiempo promedio de preparación por cocinero
- Tiempo promedio de empaque por empaquetador
- Eficiencia individual por rol

---

## 🎯 Flujo Completo

```
1. Cliente crea pedido
   ↓
2. Pedido llega a cocina (status: "recibido")
   ↓
3. COCINERO acepta pedido (status: "en_preparacion")
   - Dashboard cocinero: muestra en "mis pedidos en preparación"
   ↓
4. COCINERO termina de cocinar
   - Dashboard empaquetador: pedido aparece en "listos para empacar"
   ↓
5. EMPAQUETADOR empaca pedido (status: "listo_para_entrega")
   - Dashboard delivery: pedido disponible para asignar
   ↓
6. DELIVERY recoge y entrega
   ↓
7. Pedido completado
```

---

## ✅ Ventajas de la Separación

1. **Claridad operativa**: Cada rol ve solo lo que necesita
2. **Métricas precisas**: Saber quién hace qué y cuánto tarda
3. **Seguridad**: Validaciones por rol evitan errores
4. **Escalabilidad**: Fácil agregar más cocineros o empaquetadores
5. **Auditoría**: Trazabilidad completa de quién realizó cada acción

---

## 🚀 Próximos Pasos

1. Actualizar frontend staff para mostrar dashboards específicos por rol
2. Agregar notificaciones push por rol (ej: "Nuevo pedido para cocinar")
3. Implementar métricas de rendimiento individual
4. Crear reportes de productividad por rol

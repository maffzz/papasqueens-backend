# Papas Queen's - Backend 🥔👑

Este backend implementa la plataforma de pedidos de Papas Queen's sobre AWS usando un enfoque **serverless / microservicios** con Lambda, API Gateway, DynamoDB, S3, EventBridge y Step Functions. 🚀

---

## 1. Estructura del backend 🧱

- **`orders-svc/`** 🧾
  - Lógica del ciclo de vida del pedido del cliente (crear, consultar, cancelar, actualizar estado, perfil de cliente).
- **`kitchen-svc/`** 👩‍🍳
  - Cola de cocina, aceptación y empaquetado del pedido, gestión de menú y staff de restaurante, métricas de cocina.
- **`delivery-svc/`** 🛵
  - Asignación de repartidores, tracking del delivery, prueba de entrega, estado de repartidores y entregas.
- **`analytics-svc/`** 📊
  - Recolección de métricas por evento (Order.Created, Order.Prepared, Order.Delivered, Staff.Updated) y APIs de analítica/dashboards.
- **`register/`** 🔐
  - Endpoints de autenticación de staff y clientes.
- **`common/`** 🧩
  - Código compartido entre servicios (utilidades, helpers, modelos comunes, etc.).
- **`serverless.yml`** ⚙️
  - Definición de funciones Lambda, API Gateway, tablas DynamoDB, buckets S3, Step Functions, permisos IAM, etc.
- **`requirements.txt`** 📦
  - Dependencias Python comunes del backend.

Runtime principal: **Python 3.13** (según `serverless.yml`). 🐍

---

## 2. Despliegue en una Máquina Virtual (VM) 🖥️

> 💡 Nota: el backend está diseñado para AWS Lambda + Serverless Framework. Esta sección describe cómo preparar el código y dependencias en una VM (por ejemplo EC2, GCE, o una VM local) para ejecutar scripts de mantenimiento o empaquetar funciones.

### 2.1. Requisitos previos en la VM ✅

- Python 3.11+ (idealmente 3.13 para alinear con Lambda).
- `pip` y `venv` instalados.
- Git (si vas a clonar el repo directamente en la VM).
- (Opcional) Node.js + npm si también quieres desplegar con `serverless` desde la VM.

### 2.2. Clonar el repositorio en la VM 📂

```bash
# Dentro de la VM
cd /opt  # o el directorio que prefieras

git clone <URL_DEL_REPOSITORIO> papasqueens
cd papasqueens/backend
```

### 2.3. Crear y activar un entorno virtual 🌱

```bash
python3 -m venv .venv
source .venv/bin/activate  # En Linux / macOS
# En Windows: .venv\\Scripts\\activate
```

### 2.4. Instalar dependencias globales del backend 📦

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Si necesitas que un microservicio concreto tenga todas las dependencias "empaquetadas" en una carpeta (por ejemplo, para generar un ZIP desplegable tipo Lambda), puedes usar:

```bash
# Desde backend/
mkdir -p build/orders-svc
cp -r orders-svc/* build/orders-svc/

pip install -r requirements.txt -t build/orders-svc

cd build/orders-svc
zip -r ../orders-svc.zip .
```

La idea es:

1. Copiar el código del servicio a una carpeta de build.
2. Ejecutar `pip install -r requirements.txt -t build/<svc>` para instalar dependencias **dentro de la carpeta**.
3. Comprimir todo en un `.zip` que puedes subir a Lambda o mover a otro entorno.

Repite el patrón para `kitchen-svc`, `delivery-svc`, `analytics-svc`, etc., cambiando el destino de la carpeta. 🔁

### 2.5. Ejecutar scripts desde la VM 🧪

Si en algún momento necesitas ejecutar scripts utilitarios (por ejemplo `validate.py` o scripts de migración), basta con:

```bash
cd /ruta/a/papasqueens/backend
source .venv/bin/activate

python validate.py
# o cualquier otro script Python que agregues
```

### 2.6. Despliegue con Serverless Framework (opcional desde la VM) ☁️

Si la VM también actúa como estación de despliegue a AWS:

1. Instalar Node.js y Serverless:

   ```bash
   npm install -g serverless
   ```

2. Configurar credenciales de AWS (perfil con permisos para Lambda, API Gateway, DynamoDB, S3, Step Functions, EventBridge, CloudWatch).

3. Desde `backend/` desplegar:

   ```bash
   cd /ruta/a/papasqueens/backend
   serverless deploy --stage dev
   ```

---

## 3. Arquitectura de alto nivel 🏗️

### 3.1. Componentes principales

- **API Gateway HTTP** 🌐
  - Expone endpoints REST para clientes (frontend customer), staff (frontend staff) y panel de analytics.
- **Lambda Functions (microservicios)** 🧬
  - Implementadas como archivos Python organizados por carpeta de servicio.
- **DynamoDB** (tablas multi-tenant por `tenant_id`) 🗄️
  - `Orders` – pedidos de clientes.
  - `Kitchen` – estado de pedidos en cocina.
  - `Delivery` – asignaciones y estado del delivery.
  - `Analytics` – métricas agregadas.
  - `Staff` – personal y repartidores.
  - `MenuItems` – productos del menú.
  - `papasqueens-users` – usuarios (clientes) para login y perfil.
- **S3 Buckets** 🪣
  - `papasqueens-menu-images` – imágenes de productos del menú.
- **EventBridge (EVENT_BUS)** 📬
  - Bus de eventos `papasqueens-event-bus` para comunicar cambios de estado (`Order.Created`, `Order.Prepared`, `Order.Delivered`, `Staff.Updated`, etc.) entre microservicios.
- **Step Functions (ORDER_SFN_NAME)** 🔁
  - State machine `papasqueens-order-workflow` que orquesta el ciclo de vida de una orden.

### 3.2. Flujo principal de un pedido 📦➡️🛵➡️🏠

1. **Cliente crea pedido** 🧾
   - Frontend customer llama al endpoint `POST /orders` (función `createOrder`).
   - Se valida el pedido y se guarda en la tabla `Orders`.
   - Se dispara un evento `Order.Created` a EventBridge para notificar a cocina y analytics.

2. **Cocina recibe pedido** 👩‍🍳
   - `kitchen-svc/receive_order` está suscrito a `Order.Created` vía EventBridge.
   - Se inserta/actualiza el estado en la tabla `Kitchen`.
   - Staff de cocina consulta la cola con `GET /kitchen/queue`.

3. **Preparación del pedido** 🍟
   - Cocina acepta el pedido (`POST /kitchen/orders/{order_id}/accept`).
   - Una vez listo, lo empaqueta (`POST /kitchen/orders/{order_id}/pack`).
   - Al marcar el pedido como preparado se dispara un evento `Order.Prepared`.

4. **Asignación y delivery** 🛵
   - `delivery-svc/receive_prepared_order` consume `Order.Prepared`.
   - Se asigna un repartidor con `POST /delivery/assign` o automáticamente vía workflow.
   - Se puede rastrear el delivery con `GET /delivery/{id_delivery}/track`.
   - El repartidor actualiza ubicación con `POST /delivery/location` y estado con `PATCH /delivery/{id_delivery}/status`.
   - Al confirmar la entrega (`POST /delivery/orders/{id_order}/delivered`) se genera evento `Order.Delivered`.

5. **Cierre y analytics** 📊
   - `orders-svc/handle_order_delivered` consume `Order.Delivered` para cerrar el pedido.
   - `analytics-svc` tiene múltiples funciones que consumen eventos (`Order.Created`, `Order.Prepared`, `Order.Delivered`, `Staff.Updated`) para poblar la tabla `Analytics`.
   - Se exponen endpoints para dashboards y KPIs.

### 3.3. Step Functions: `papasqueens-order-workflow` 🔄

State machine (simplificado desde `serverless.yml`):

- **ValidateOrder** → Task
  - Llama a Lambda `createOrder` para validar los datos del pedido.
- **SaveOrder** → Task
  - Llama nuevamente a `createOrder` para persistir el pedido.
- **WaitForPrepared** → Wait (60s)
  - Espera a que el pedido esté marcado como `Prepared` en cocina.
- **AssignDelivery** → Task
  - Llama a Lambda `assignDelivery` para asignar repartidor.
- **WaitForDelivered** → Wait (60s)
  - Espera a que el pedido sea marcado como entregado.
- **UpdateAnalytics** → Task
  - Ejecuta `collectDeliveryMetrics` para registrar métricas.
- **CloseOrder** → Task
  - Ejecuta `handleOrderDelivered` para cerrar de forma definitiva la orden.

> 🔎 El Step Function puede evolucionar (por ejemplo, reemplazar waits fijos por waits basados en eventos), pero este README refleja la definición actual en `serverless.yml`.

### 3.4. EventBridge 📬

- Bus: **`papasqueens-event-bus`**.
- Eventos típicos:
  - `Order.Created` – emitido al crear un pedido.
  - `Order.Prepared` – emitido cuando cocina marca el pedido como preparado.
  - `Order.Delivered` – emitido cuando se confirma la entrega al cliente.
  - `Staff.Updated` – emitido cuando hay cambios de estado en staff.
- Suscriptores principales:
  - `kitchen-svc.receive_order` (Order.Created).
  - `kitchen-svc.sync_kitchen_metrics` (Order.Prepared).
  - `delivery-svc.receive_prepared_order` (Order.Prepared).
  - `delivery-svc.delivery_metrics` (Order.Delivered).
  - `orders-svc.handle_order_delivered` (Order.Delivered).
  - `analytics-svc.collect_*` (diferentes tipos de eventos).

---

## 4. Endpoints por microservicio (HTTP) 🌍

> 📡 Los paths se definen en `serverless.yml` bajo `functions:` y se exponen vía API Gateway. Todos soportan CORS y usan headers multi-tenant (`X-Tenant-Id`, `X-User-Id`, etc.).

### 4.1. `orders-svc` 🧾

- `POST /orders` → `createOrder`
- `GET /orders/{id_order}` → `getOrder`
- `GET /orders/{id_order}/status` → `getOrderStatus`
- `GET /orders/customer/{id_customer}` → `getCustomerOrders`
- `PATCH /orders/{id_order}/status` → `updateOrderStatus`
- `POST /orders/{id_order}/cancel` → `cancelOrder`
- `PATCH /auth/customer/profile` → `updateCustomerProfile`

### 4.2. `kitchen-svc` 👩‍🍳

- `GET /kitchen/queue` → `getKitchenQueue`
- `POST /kitchen/orders/{order_id}/accept` → `acceptOrder`
- `POST /kitchen/orders/{order_id}/pack` → `packOrder`
- `GET /menu` → `listMenuItems`
- `POST /menu` → `addMenuItem`
- `PATCH /menu/{id_producto}` → `updateMenuItem`
- `DELETE /menu/{id_producto}` → `deleteMenuItem`
- `POST /staff` → `manageStaff` (crear/registrar staff)
- `PATCH /staff/{id_staff}` → `manageStaff` (actualizar staff)
- `GET /staff` → `listStaff`

### 4.3. `delivery-svc` 🛵

- `POST /delivery/assign` → `assignDelivery`
- `PATCH /delivery/{id_delivery}/status` → `updateDeliveryStatus`
- `POST /delivery/orders/{id_order}/handoff` → `handoffOrder` (entrega al repartidor)
- `POST /delivery/orders/{id_order}/delivered` → `confirmDelivered`
- `GET /delivery/{id_delivery}` → `getDeliveryStatus`
- `GET /delivery/{id_delivery}/track` → `trackRider`
- `GET /delivery` → `listDeliveries`
- `GET /riders` → `listRiders`
- `PATCH /riders/{id_staff}/status` → `updateRiderStatus`
- `POST /delivery/location` → `updateRiderLocation`

### 4.4. `analytics-svc` 📊

- `GET /analytics/orders` → `getAnalyticsOrders`
- `GET /analytics/employees` → `getAnalyticsEmployees`
- `GET /analytics/delivery` → `getAnalyticsDelivery`
- `GET /analytics/dashboard` → `getDashboard`
- `GET /analytics/workflow-kpis` → `getWorkflowKpis`

> ⏱️ Adicionalmente, `exportAnalyticsReport` corre con un **trigger programado** (`schedule: rate(1 day)`), exportando reportes a S3.

### 4.5. `register` (login) 🔐

- `POST /auth/staff/login` → `staffLogin`
- `POST /auth/customer/login` → `customerLogin`

---

## 5. Notas adicionales 📝

- Todas las Lambdas comparten configuraciones comunes desde `provider.environment` en `serverless.yml` (nombres de tablas, buckets, secretos JWT, etc.).
- IAM Role `LabRole` debe tener permisos para:
  - `dynamodb:*`, `s3:*`, `events:PutEvents`, `states:StartExecution`, logs y métricas de CloudWatch.
- Para entornos productivos se recomienda:
  - Ajustar tiempos de espera de Step Functions a eventos reales en lugar de esperas fijas. ⏳
  - Restringir permisos IAM siguiendo el principio de mínimo privilegio. 🔒
  - Mover `JWT_SECRET` a un secreto gestionado (AWS Secrets Manager / SSM Parameter Store) y no dejar el valor por defecto `change-me`. 🤫

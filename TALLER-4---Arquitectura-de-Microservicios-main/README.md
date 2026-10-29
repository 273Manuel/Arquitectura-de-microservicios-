# MicroSim: taller de arquitectura de microservicios

Aplicación full-stack para una tienda virtual, desarrollada con React y tres microservicios independientes en FastAPI. La interfaz permite ejecutar solicitudes REST reales, consultar el estado de cada servicio y comprobar cómo responde el sistema cuando una dependencia no está disponible.

Los datos se almacenan en listas en memoria. No se usa una base de datos y los registros vuelven a su estado inicial al reiniciar los procesos.

## Funcionalidad

- Registro y consulta de productos, clientes y pedidos.
- Operaciones GET, POST, PUT y DELETE para cada recurso.
- Validación de clientes, productos y existencias antes de registrar un pedido.
- Cálculo del total del pedido con el precio obtenido del microservicio de productos.
- Gateway HTTP para exponer las API desde un mismo origen.
- Simulación de caídas y recuperación desde la interfaz.
- Historial de solicitudes con método, ruta, estado HTTP y duración real.
- Prueba automatizada que detiene el proceso de productos y verifica el aislamiento del fallo.

## Tecnologías

| Capa | Tecnología |
| --- | --- |
| Interfaz | React, TypeScript y Vite |
| Microservicios | Python, FastAPI, Pydantic y Uvicorn |
| Comunicación entre servicios | HTTPX y API REST con JSON |
| Gateway | Nginx |
| Ejecución | Docker, Docker Compose y Supervisor |
| Datos | Listas en memoria |

## Arquitectura

| Componente | Puerto | Responsabilidad |
| --- | ---: | --- |
| Gateway y aplicación web | 3000 | Presentar MicroSim y dirigir las solicitudes |
| Productos | 8001 | Gestionar catálogo, precios y existencias |
| Clientes | 8002 | Gestionar el registro y la consulta de clientes |
| Pedidos | 8003 | Gestionar pedidos y validar sus dependencias |

```text
Navegador
    |
    v
Gateway / aplicación web :3000
    |
    +--> Productos :8001
    |
    +--> Clientes :8002
    |
    +--> Pedidos :8003
              |
              +--> consulta Clientes
              |
              +--> consulta Productos
```

Cada microservicio tiene su propio proceso, sus propios datos y sus reglas de negocio. El gateway solo dirige el tráfico.

## Abrir en GitHub Codespaces

1. Haz fork de este repositorio.
2. Crea un Codespace desde la rama que contiene el proyecto.
3. Espera a que la configuración de `.devcontainer` construya e inicie los contenedores definidos en `docker-compose.yml`.
4. Abre la pestaña **Ports** y entra al puerto **3000**, identificado como **MicroSim - Aplicación web**.

Si agregaste la configuración a un Codespace que ya estaba abierto, pulsa `Ctrl+Shift+P` y ejecuta **Dev Containers: Rebuild Container**.

Los puertos 8001, 8002 y 8003 también se reenvían para acceder directamente a cada API.

## Ejecutar con Docker

```bash
# 1. Construir e iniciar la aplicación completa
docker compose up --build

# 2. Detener los contenedores cuando termine la práctica
docker compose down
```

En una ejecución local, la aplicación queda disponible en `http://localhost:3000`.

## Uso de la interfaz

La sección **Repeater** funciona como cliente API:

1. Selecciona un servicio en **TARGET**.
2. Elige el método HTTP.
3. Ajusta la ruta y el cuerpo JSON cuando sea necesario.
4. Pulsa **Send** para ejecutar la solicitud real.

Las demás vistas permiten consultar:

- **Dashboard:** estado y cantidad de registros de cada servicio.
- **Proxy:** correspondencia entre rutas públicas y procesos internos.
- **Logs:** historial de solicitudes ejecutadas durante la sesión.

El botón **Reiniciar datos y servicios** restablece los registros iniciales y limpia el historial de la interfaz.

## Datos iniciales

| Recurso | ID | Datos |
| --- | ---: | --- |
| Producto | 18 | Teclado mecánico, SKU `KB-2025-01`, precio 129,90 y stock 24 |
| Cliente | 42 | Ana García, `ana@example.com`, activo |
| Pedidos | - | Sin registros iniciales |

## API REST

Cada servicio expone las siguientes operaciones sobre su recurso:

| Operación | Ruta |
| --- | --- |
| Listar registros | `GET /api/{servicio}` |
| Consultar un registro | `GET /api/{servicio}/{id}` |
| Crear un registro | `POST /api/{servicio}` |
| Actualizar un registro | `PUT /api/{servicio}/{id}` |
| Eliminar un registro | `DELETE /api/{servicio}/{id}` |

`{servicio}` puede ser `productos`, `clientes` o `pedidos`.

### Rutas de apoyo

| Operación | Ruta |
| --- | --- |
| Consultar estado y registros | `GET /api/{servicio}/salud` |
| Simular o retirar una caída | `POST /api/{servicio}/control/estado` |
| Restablecer datos y estado | `POST /api/{servicio}/control/reiniciar` |
| Abrir documentación interactiva | `GET /api/{servicio}/docs` |

Para cambiar la disponibilidad de un servicio se envía:

```json
{
  "online": false
}
```

### Crear un pedido

```http
POST /api/pedidos
Content-Type: application/json
```

```json
{
  "clienteId": 42,
  "productoId": 18,
  "cantidad": 2,
  "confirmado": false
}
```

Antes de registrar la orden, Pedidos consulta a Clientes y Productos. Comprueba que ambos registros existan y estén activos, que haya existencias suficientes y calcula el total. Con los datos iniciales, el resultado es un pedido por 259,80 en estado `PENDIENTE`.

Si una dependencia necesaria no responde, la operación devuelve `503 Service Unavailable` y no agrega una orden incompleta.

## Prueba de tolerancia a fallos

### Desde la interfaz

1. Crea un pedido mientras los tres servicios estén en línea.
2. Selecciona `productos.local` en **TARGET**.
3. Pulsa **Simular fallo del servicio**.
4. Consulta clientes y pedidos existentes desde **Repeater**.
5. Intenta crear otro pedido.

Resultados esperados:

- Clientes continúa respondiendo.
- Pedidos conserva y devuelve las órdenes existentes.
- La creación de nuevos pedidos devuelve 503 porque necesita consultar Productos.
- Al restablecer Productos, la creación de pedidos vuelve a estar disponible.

### Prueba automatizada

El script `scripts/verificar_taller.py` inicia tres procesos independientes, registra datos, crea un pedido y detiene realmente el proceso de Productos. Los puertos 8001, 8002 y 8003 deben estar libres.

```bash
# 1. Detener los contenedores si estaban en ejecución
docker compose down

# 2. Instalar las dependencias de los tres servicios
python3 -m pip install -r requirements.txt

# 3. Ejecutar la prueba de integración y aislamiento de fallos
python3 scripts/verificar_taller.py
```

Dentro de un Codespace, no uses `docker compose down` porque el espacio de trabajo también pertenece a Compose. Detén únicamente los contenedores de la aplicación:

```bash
# 1. Detener la aplicación sin detener el Codespace
docker compose stop gateway frontend productos clientes pedidos

# 2. Instalar dependencias y ejecutar la prueba
python3 -m pip install -r requirements.txt
python3 scripts/verificar_taller.py

# 3. Volver a iniciar la aplicación
docker compose up -d
```

## Verificación del frontend

```bash
# 1. Instalar dependencias
npm install

# 2. Comprobar tipos
npm run check

# 3. Compilar la aplicación
npm run build
```

## Estructura del proyecto

```text
.
├── .devcontainer/
│   └── devcontainer.json       # Configuración de GitHub Codespaces
├── public/                     # Recursos estáticos
├── scripts/
│   └── verificar_taller.py     # Prueba real de integración y fallos
├── services/
│   ├── productos/              # API, dependencias y Dockerfile de Productos
│   ├── clientes/               # API, dependencias y Dockerfile de Clientes
│   └── pedidos/                # API, dependencias y Dockerfile de Pedidos
├── src/                        # Interfaz React
├── docker-compose.yml          # Orquestación de desarrollo
├── Dockerfile                  # Imagen de producción
├── nginx.conf                  # Gateway para Docker Compose
├── nginx.production.conf       # Gateway y frontend compilado
└── supervisord.conf            # Procesos de la imagen de producción
```

## Persistencia

Este proyecto simplifica el almacenamiento para concentrarse en la arquitectura y la comunicación entre servicios. Los datos solo existen durante la ejecución de cada proceso. Reiniciar un servicio o usar su ruta de restablecimiento elimina los cambios realizados.
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
| Gateway | FastAPI + HTTPX (proxy inverso) |
| Ejecución | Procesos Python (`start.py`) |
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

## Ejecutar localmente

Requisitos: Python 3.12+ y Node 22+.

```bash
./build.sh        # instala dependencias y compila el frontend
python3 start.py  # inicia productos, clientes, pedidos y el gateway
```

La aplicación queda en `http://localhost:3000`. El gateway usa la variable `PORT` si existe.

## Desplegar (Render, Railway, etc.)

Crear un *Web Service* (entorno Python/Node) con:

| Campo | Valor |
| --- | --- |
| Build Command | `./build.sh` |
| Start Command | `python3 start.py` |

El gateway escucha en `$PORT` y los tres microservicios en 8001, 8002 y 8003 dentro de la misma máquina (127.0.0.1). Las URLs internas pueden cambiarse con `PRODUCTOS_URL`, `CLIENTES_URL` y `PEDIDOS_URL`.

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
# 1. Detener start.py si estaba en ejecución

# 2. Instalar las dependencias de los tres servicios
python3 -m pip install -r requirements.txt

# 3. Ejecutar la prueba de integración y aislamiento de fallos
python3 scripts/verificar_taller.py
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
├── gateway/main.py             # Proxy /api/* y servidor del frontend compilado
├── public/                     # Recursos estáticos
├── scripts/verificar_taller.py # Prueba real de integración y fallos
├── services/
│   ├── productos/              # API de Productos
│   ├── clientes/               # API de Clientes
│   └── pedidos/                # API de Pedidos
├── src/                        # Interfaz React
├── build.sh                    # Build: dependencias + frontend
└── start.py                    # Inicia los 4 procesos
```

## Persistencia

Este proyecto simplifica el almacenamiento para concentrarse en la arquitectura y la comunicación entre servicios. Los datos solo existen durante la ejecución de cada proceso. Reiniciar un servicio o usar su ruta de restablecimiento elimina los cambios realizados.
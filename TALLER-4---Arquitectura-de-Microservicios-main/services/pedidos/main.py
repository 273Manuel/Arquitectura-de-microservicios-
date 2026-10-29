import os
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


app = FastAPI(
    title="Microservicio de pedidos",
    version="1.0.0",
    docs_url="/api/pedidos/docs",
    openapi_url="/api/pedidos/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
estado = {"online": True}
CLIENTES_URL = os.getenv("CLIENTES_URL", "http://clientes:8002")
PRODUCTOS_URL = os.getenv("PRODUCTOS_URL", "http://productos:8001")


class PedidoEntrada(BaseModel):
    clienteId: int = Field(gt=0)
    productoId: int = Field(gt=0)
    cantidad: int = Field(gt=0)
    confirmado: bool = False


class Pedido(PedidoEntrada):
    id: int
    total: float
    estado: str
    createdAt: datetime


class EstadoEntrada(BaseModel):
    online: bool


pedidos: list[Pedido] = []


@app.middleware("http")
async def control_disponibilidad(request: Request, call_next):
    ruta = request.url.path
    if not estado["online"] and not ruta.startswith("/api/pedidos/control") and ruta != "/api/pedidos/salud":
        return JSONResponse(
            status_code=503,
            content={"detail": "Servicio de pedidos no disponible", "codigo": "SERVICE_UNAVAILABLE"},
        )
    respuesta = await call_next(request)
    respuesta.headers["X-Service"] = "pedidos"
    return respuesta


async def consultar_dependencia(cliente_http: httpx.AsyncClient, url: str, nombre: str):
    try:
        respuesta = await cliente_http.get(url)
    except httpx.RequestError as error:
        raise HTTPException(status_code=503, detail=f"{nombre} no está disponible") from error
    if respuesta.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Registro no encontrado en {nombre}")
    if respuesta.status_code >= 500:
        raise HTTPException(status_code=503, detail=f"{nombre} no está disponible")
    if respuesta.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Respuesta inválida de {nombre}")
    return respuesta.json()


async def validar_pedido(entrada: PedidoEntrada):
    async with httpx.AsyncClient(timeout=3.0) as cliente_http:
        cliente = await consultar_dependencia(
            cliente_http,
            f"{CLIENTES_URL}/api/clientes/{entrada.clienteId}",
            "El servicio de clientes",
        )
        producto = await consultar_dependencia(
            cliente_http,
            f"{PRODUCTOS_URL}/api/productos/{entrada.productoId}",
            "El servicio de productos",
        )
    if not cliente.get("activo", False):
        raise HTTPException(status_code=409, detail="El cliente está inactivo")
    if not producto.get("activo", False):
        raise HTTPException(status_code=409, detail="El producto está inactivo")
    if producto.get("stock", 0) < entrada.cantidad:
        raise HTTPException(status_code=409, detail="No hay existencias suficientes")
    return round(float(producto["precio"]) * entrada.cantidad, 2)


@app.get("/api/pedidos/salud")
def salud():
    contenido = {"servicio": "pedidos", "estado": "online" if estado["online"] else "offline", "registros": len(pedidos)}
    return JSONResponse(status_code=200 if estado["online"] else 503, content=contenido)


@app.post("/api/pedidos/control/estado")
def cambiar_estado(entrada: EstadoEntrada):
    estado["online"] = entrada.online
    return {"servicio": "pedidos", "online": estado["online"]}


@app.post("/api/pedidos/control/reiniciar")
def reiniciar():
    pedidos.clear()
    estado["online"] = True
    return {"servicio": "pedidos", "online": True, "registros": 0}


@app.get("/api/pedidos")
def listar_pedidos():
    return pedidos


@app.get("/api/pedidos/{pedido_id}")
def obtener_pedido(pedido_id: int):
    pedido = next((item for item in pedidos if item.id == pedido_id), None)
    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return pedido


@app.post("/api/pedidos", status_code=201)
async def crear_pedido(entrada: PedidoEntrada):
    total = await validar_pedido(entrada)
    nuevo_id = max((item.id for item in pedidos), default=1000) + 1
    pedido = Pedido(
        id=nuevo_id,
        total=total,
        estado="CONFIRMADO" if entrada.confirmado else "PENDIENTE",
        createdAt=datetime.now(timezone.utc),
        **entrada.model_dump(),
    )
    pedidos.append(pedido)
    return pedido


@app.put("/api/pedidos/{pedido_id}")
async def actualizar_pedido(pedido_id: int, entrada: PedidoEntrada):
    indice = next((i for i, item in enumerate(pedidos) if item.id == pedido_id), None)
    if indice is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    total = await validar_pedido(entrada)
    actualizado = Pedido(
        id=pedido_id,
        total=total,
        estado="CONFIRMADO" if entrada.confirmado else "PENDIENTE",
        createdAt=pedidos[indice].createdAt,
        **entrada.model_dump(),
    )
    pedidos[indice] = actualizado
    return actualizado


@app.delete("/api/pedidos/{pedido_id}", status_code=204)
def eliminar_pedido(pedido_id: int):
    indice = next((i for i, item in enumerate(pedidos) if item.id == pedido_id), None)
    if indice is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    pedidos.pop(indice)
    return Response(status_code=204)

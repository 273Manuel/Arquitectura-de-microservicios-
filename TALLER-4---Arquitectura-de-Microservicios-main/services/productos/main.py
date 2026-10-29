from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


app = FastAPI(
    title="Microservicio de productos",
    version="1.0.0",
    docs_url="/api/productos/docs",
    openapi_url="/api/productos/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
estado = {"online": True}


class ProductoEntrada(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    sku: str = Field(min_length=3, max_length=40)
    precio: float = Field(gt=0)
    stock: int = Field(ge=0)
    activo: bool = True


class Producto(ProductoEntrada):
    id: int
    createdAt: datetime


class EstadoEntrada(BaseModel):
    online: bool


def semilla() -> Producto:
    return Producto(
        id=18,
        nombre="Teclado mecánico",
        sku="KB-2025-01",
        precio=129.90,
        stock=24,
        activo=True,
        createdAt=datetime.now(timezone.utc),
    )


productos: list[Producto] = [semilla()]


@app.middleware("http")
async def control_disponibilidad(request: Request, call_next):
    ruta = request.url.path
    if not estado["online"] and not ruta.startswith("/api/productos/control") and ruta != "/api/productos/salud":
        return JSONResponse(
            status_code=503,
            content={"detail": "Servicio de productos no disponible", "codigo": "SERVICE_UNAVAILABLE"},
        )
    respuesta = await call_next(request)
    respuesta.headers["X-Service"] = "productos"
    return respuesta


@app.get("/api/productos/salud")
def salud():
    contenido = {"servicio": "productos", "estado": "online" if estado["online"] else "offline", "registros": len(productos)}
    return JSONResponse(status_code=200 if estado["online"] else 503, content=contenido)


@app.post("/api/productos/control/estado")
def cambiar_estado(entrada: EstadoEntrada):
    estado["online"] = entrada.online
    return {"servicio": "productos", "online": estado["online"]}


@app.post("/api/productos/control/reiniciar")
def reiniciar():
    productos[:] = [semilla()]
    estado["online"] = True
    return {"servicio": "productos", "online": True, "registros": len(productos)}


@app.get("/api/productos")
def listar_productos():
    return productos


@app.get("/api/productos/{producto_id}")
def obtener_producto(producto_id: int):
    producto = next((item for item in productos if item.id == producto_id), None)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@app.post("/api/productos", status_code=201)
def crear_producto(entrada: ProductoEntrada):
    if any(item.sku.lower() == entrada.sku.lower() for item in productos):
        raise HTTPException(status_code=409, detail="El SKU ya está registrado")
    nuevo_id = max((item.id for item in productos), default=17) + 1
    producto = Producto(id=nuevo_id, createdAt=datetime.now(timezone.utc), **entrada.model_dump())
    productos.append(producto)
    return producto


@app.put("/api/productos/{producto_id}")
def actualizar_producto(producto_id: int, entrada: ProductoEntrada):
    indice = next((i for i, item in enumerate(productos) if item.id == producto_id), None)
    if indice is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if any(item.id != producto_id and item.sku.lower() == entrada.sku.lower() for item in productos):
        raise HTTPException(status_code=409, detail="El SKU ya está registrado")
    actualizado = Producto(
        id=producto_id,
        createdAt=productos[indice].createdAt,
        **entrada.model_dump(),
    )
    productos[indice] = actualizado
    return actualizado


@app.delete("/api/productos/{producto_id}", status_code=204)
def eliminar_producto(producto_id: int):
    indice = next((i for i, item in enumerate(productos) if item.id == producto_id), None)
    if indice is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    productos.pop(indice)
    return Response(status_code=204)

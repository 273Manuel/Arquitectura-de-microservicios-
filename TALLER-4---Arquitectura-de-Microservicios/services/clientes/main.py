from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field


app = FastAPI(
    title="Microservicio de clientes",
    version="1.0.0",
    docs_url="/api/clientes/docs",
    openapi_url="/api/clientes/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
estado = {"online": True}


class ClienteEntrada(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    email: EmailStr
    plan: str = Field(default="student", min_length=2, max_length=40)
    activo: bool = True


class Cliente(ClienteEntrada):
    id: int
    createdAt: datetime


class EstadoEntrada(BaseModel):
    online: bool


def semilla() -> Cliente:
    return Cliente(
        id=42,
        nombre="Ana García",
        email="ana@example.com",
        plan="student",
        activo=True,
        createdAt=datetime.now(timezone.utc),
    )


clientes: list[Cliente] = [semilla()]


@app.middleware("http")
async def control_disponibilidad(request: Request, call_next):
    ruta = request.url.path
    if not estado["online"] and not ruta.startswith("/api/clientes/control") and ruta != "/api/clientes/salud":
        return JSONResponse(
            status_code=503,
            content={"detail": "Servicio de clientes no disponible", "codigo": "SERVICE_UNAVAILABLE"},
        )
    respuesta = await call_next(request)
    respuesta.headers["X-Service"] = "clientes"
    return respuesta


@app.get("/api/clientes/salud")
def salud():
    contenido = {"servicio": "clientes", "estado": "online" if estado["online"] else "offline", "registros": len(clientes)}
    return JSONResponse(status_code=200 if estado["online"] else 503, content=contenido)


@app.post("/api/clientes/control/estado")
def cambiar_estado(entrada: EstadoEntrada):
    estado["online"] = entrada.online
    return {"servicio": "clientes", "online": estado["online"]}


@app.post("/api/clientes/control/reiniciar")
def reiniciar():
    clientes[:] = [semilla()]
    estado["online"] = True
    return {"servicio": "clientes", "online": True, "registros": len(clientes)}


@app.get("/api/clientes")
def listar_clientes():
    return clientes


@app.get("/api/clientes/{cliente_id}")
def obtener_cliente(cliente_id: int):
    cliente = next((item for item in clientes if item.id == cliente_id), None)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@app.post("/api/clientes", status_code=201)
def crear_cliente(entrada: ClienteEntrada):
    if any(item.email.lower() == entrada.email.lower() for item in clientes):
        raise HTTPException(status_code=409, detail="El correo ya está registrado")
    nuevo_id = max((item.id for item in clientes), default=41) + 1
    cliente = Cliente(id=nuevo_id, createdAt=datetime.now(timezone.utc), **entrada.model_dump())
    clientes.append(cliente)
    return cliente


@app.put("/api/clientes/{cliente_id}")
def actualizar_cliente(cliente_id: int, entrada: ClienteEntrada):
    indice = next((i for i, item in enumerate(clientes) if item.id == cliente_id), None)
    if indice is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if any(item.id != cliente_id and item.email.lower() == entrada.email.lower() for item in clientes):
        raise HTTPException(status_code=409, detail="El correo ya está registrado")
    actualizado = Cliente(id=cliente_id, createdAt=clientes[indice].createdAt, **entrada.model_dump())
    clientes[indice] = actualizado
    return actualizado


@app.delete("/api/clientes/{cliente_id}", status_code=204)
def eliminar_cliente(cliente_id: int):
    indice = next((i for i, item in enumerate(clientes) if item.id == cliente_id), None)
    if indice is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    clientes.pop(indice)
    return Response(status_code=204)

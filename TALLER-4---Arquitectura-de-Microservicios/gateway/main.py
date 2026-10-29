"""Gateway HTTP: expone las tres APIs y la interfaz compilada desde un único puerto."""

import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse

RAIZ = Path(__file__).resolve().parents[1]
DIST = RAIZ / "dist"

DESTINOS = {
    "productos": os.getenv("PRODUCTOS_URL", "http://127.0.0.1:8001"),
    "clientes": os.getenv("CLIENTES_URL", "http://127.0.0.1:8002"),
    "pedidos": os.getenv("PEDIDOS_URL", "http://127.0.0.1:8003"),
}
EXCLUIR = {"host", "content-length", "connection", "transfer-encoding", "content-encoding"}

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
cliente_http = httpx.AsyncClient(timeout=10.0)


@app.api_route("/api/{servicio}/{ruta:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
@app.api_route("/api/{servicio}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy(servicio: str, request: Request, ruta: str = ""):
    base = DESTINOS.get(servicio)
    if base is None:
        return JSONResponse(status_code=404, content={"detail": "Servicio desconocido"})
    destino = f"{base}/api/{servicio}" + (f"/{ruta}" if ruta else "")
    cabeceras = {k: v for k, v in request.headers.items() if k.lower() not in EXCLUIR}
    try:
        r = await cliente_http.request(
            request.method, destino, params=request.query_params, content=await request.body(), headers=cabeceras
        )
    except httpx.RequestError:
        return JSONResponse(
            status_code=503,
            content={"detail": f"Servicio de {servicio} no disponible", "codigo": "SERVICE_UNAVAILABLE"},
        )
    salida = {k: v for k, v in r.headers.items() if k.lower() not in EXCLUIR}
    return Response(content=r.content, status_code=r.status_code, headers=salida)


@app.get("/{ruta:path}")
async def frontend(ruta: str):
    if not DIST.is_dir():
        return JSONResponse(status_code=503, content={"detail": "Falta compilar el frontend: npm run build"})
    archivo = (DIST / ruta).resolve()
    if ruta and archivo.is_file() and DIST.resolve() in archivo.parents:
        return FileResponse(archivo)
    return FileResponse(DIST / "index.html")

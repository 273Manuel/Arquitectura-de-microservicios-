#!/usr/bin/env python3
"""Inicia los tres microservicios y el gateway. El gateway usa $PORT (por defecto 3000)."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PUERTO = os.environ.get("PORT", "3000")

entorno = os.environ.copy()
entorno.setdefault("PRODUCTOS_URL", "http://127.0.0.1:8001")
entorno.setdefault("CLIENTES_URL", "http://127.0.0.1:8002")
entorno.setdefault("PEDIDOS_URL", "http://127.0.0.1:8003")

PROCESOS = [
    ("productos", RAIZ / "services" / "productos", "main:app", "8001"),
    ("clientes", RAIZ / "services" / "clientes", "main:app", "8002"),
    ("pedidos", RAIZ / "services" / "pedidos", "main:app", "8003"),
    ("gateway", RAIZ / "gateway", "main:app", PUERTO),
]

hijos = {}


def lanzar(nombre, directorio, app, puerto):
    host = "0.0.0.0" if nombre == "gateway" else "127.0.0.1"
    hijos[nombre] = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", app, "--host", host, "--port", puerto],
        cwd=directorio, env=entorno,
    )


def detener(*_):
    for p in hijos.values():
        if p.poll() is None:
            p.terminate()
    sys.exit(0)


signal.signal(signal.SIGTERM, detener)
signal.signal(signal.SIGINT, detener)
for definicion in PROCESOS:
    lanzar(*definicion)

while True:
    for definicion in PROCESOS:
        if hijos[definicion[0]].poll() is not None:
            print(f"[start] {definicion[0]} terminó; reiniciando", flush=True)
            lanzar(*definicion)
    time.sleep(2)

#!/usr/bin/env python3
"""Prueba de integración del flujo normal y de la caída real del servicio de productos."""

import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import httpx


RAIZ = Path(__file__).resolve().parents[1]
PUERTOS = {"productos": 8001, "clientes": 8002, "pedidos": 8003}
URLS = {nombre: f"http://127.0.0.1:{puerto}" for nombre, puerto in PUERTOS.items()}
procesos: dict[str, subprocess.Popen] = {}


def iniciar(nombre: str):
    entorno = os.environ.copy()
    entorno["CLIENTES_URL"] = URLS["clientes"]
    entorno["PRODUCTOS_URL"] = URLS["productos"]
    procesos[nombre] = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(PUERTOS[nombre])],
        cwd=RAIZ / "services" / nombre,
        env=entorno,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def esperar(nombre: str):
    for _ in range(60):
        if procesos[nombre].poll() is not None:
            raise RuntimeError(f"El servicio {nombre} terminó durante el arranque")
        try:
            respuesta = httpx.get(f"{URLS[nombre]}/api/{nombre}/salud", timeout=1)
            if respuesta.status_code == 200:
                return
        except httpx.RequestError:
            pass
        time.sleep(0.25)
    raise RuntimeError(f"El servicio {nombre} no respondió a tiempo")


def comprobar(condicion: bool, mensaje: str):
    if not condicion:
        raise AssertionError(mensaje)
    print(f"OK: {mensaje}")


def detener(nombre: str):
    proceso = procesos.get(nombre)
    if proceso and proceso.poll() is None:
        proceso.terminate()
        try:
            proceso.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proceso.kill()
            proceso.wait(timeout=5)


def main():
    cliente = httpx.Client(timeout=6)
    try:
        for nombre in ("productos", "clientes", "pedidos"):
            iniciar(nombre)
            esperar(nombre)
        print("OK: los tres servicios iniciaron como procesos independientes")

        sufijo = uuid.uuid4().hex[:8]
        producto = cliente.post(
            f"{URLS['productos']}/api/productos",
            json={"nombre": "Producto de prueba", "sku": f"TEST-{sufijo}", "precio": 50, "stock": 10, "activo": True},
        )
        comprobar(producto.status_code == 201, "registro de un producto")
        producto_id = producto.json()["id"]

        nuevo_cliente = cliente.post(
            f"{URLS['clientes']}/api/clientes",
            json={"nombre": "Cliente de prueba", "email": f"test-{sufijo}@example.com", "plan": "student", "activo": True},
        )
        comprobar(nuevo_cliente.status_code == 201, "registro de un cliente")
        cliente_id = nuevo_cliente.json()["id"]

        cuerpo_pedido = {"clienteId": cliente_id, "productoId": producto_id, "cantidad": 2, "confirmado": True}
        pedido = cliente.post(f"{URLS['pedidos']}/api/pedidos", json=cuerpo_pedido)
        comprobar(pedido.status_code == 201 and pedido.json()["total"] == 100, "creación de un pedido con validación HTTP")
        pedido_id = pedido.json()["id"]

        detener("productos")
        print("OK: se detuvo realmente el proceso de productos")

        respuesta_clientes = cliente.get(f"{URLS['clientes']}/api/clientes")
        comprobar(respuesta_clientes.status_code == 200, "clientes continúa respondiendo sin productos")

        pedido_existente = cliente.get(f"{URLS['pedidos']}/api/pedidos/{pedido_id}")
        comprobar(pedido_existente.status_code == 200, "pedidos conserva la consulta de órdenes existentes")

        pedido_rechazado = cliente.post(f"{URLS['pedidos']}/api/pedidos", json=cuerpo_pedido)
        comprobar(pedido_rechazado.status_code == 503, "un pedido nuevo devuelve 503 cuando productos está caído")
        print("\nTodas las pruebas del taller pasaron.")
    finally:
        cliente.close()
        for nombre in procesos:
            detener(nombre)


if __name__ == "__main__":
    main()

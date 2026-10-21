"""
HELPERS — Caja de herramientas general
========================================
Funciones pequeñas y genéricas disponibles para todos los módulos.
No contiene lógica del juego, solo utilidades técnicas reutilizables.
"""

import os
import time
from datetime import datetime

def timestamp() -> str:
    """Retorna la fecha y hora actual como string formateado."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def guardar_log(mensaje: str, archivo="logs/bot.log"):
    """Guarda un mensaje en el archivo de log y lo imprime en consola."""
    os.makedirs("logs", exist_ok=True)
    with open(archivo, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp()}] {mensaje}\n")
    print(f"[LOG] {mensaje}")

def esperar(segundos: float):
    """Pausa la ejecución por la cantidad de segundos indicada."""
    print(f"[ESPERA] {segundos}s...")
    time.sleep(segundos)

def calcular_ruta(origen: str, destino: str) -> list:
    """
    Calcula los movimientos necesarios para ir de un mapa a otro.

    Parámetros:
        origen:  coordenadas actuales en formato "X,Y" (ej: "-32,37")
        destino: coordenadas destino en formato "X,Y" (ej: "-30,38")

    Retorna lista de movimientos: ["derecha", "derecha", "abajo"]

    Sistema de coordenadas del juego:
        X aumenta → derecha     X disminuye → izquierda
        Y aumenta → abajo(sur)  Y disminuye → arriba(norte)

    Funciona igual con coordenadas positivas (Brakmar) y negativas (Bonta).
    """
    ox, oy = map(int, origen.split(","))
    dx, dy = map(int, destino.split(","))

    movimientos = []

    diff_x = dx - ox
    diff_y = dy - oy

    # Primero moverse en X, luego en Y
    if diff_x > 0:
        movimientos += ["derecha"]   * diff_x
    elif diff_x < 0:
        movimientos += ["izquierda"] * abs(diff_x)

    if diff_y > 0:
        movimientos += ["abajo"]  * diff_y
    elif diff_y < 0:
        movimientos += ["arriba"] * abs(diff_y)

    return movimientos

# TU TURNO: agregar calcular_ruta(mapa_origen, mapa_destino)
# que retorne una lista de movimientos para ir de un mapa a otro
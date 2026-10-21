"""
CONTROLADOR ADB — El mensajero con el emulador
===============================================
Este módulo es el ÚNICO que habla directamente con LDPlayer via ADB.
Ningún otro módulo debe ejecutar comandos ADB directamente.

RESPONSABILIDAD:
- Conectar y desconectar del emulador
- Ejecutar taps, swipes, taps sostenidos, doble tap
- Tomar capturas de pantalla
- Presionar teclas del sistema Android
"""

import subprocess
import os
from dotenv import load_dotenv

load_dotenv()

ADB_HOST = os.getenv("ADB_HOST", "127.0.0.1")
ADB_PORT = os.getenv("ADB_PORT", "5555")
DEVICE   = f"{ADB_HOST}:{ADB_PORT}"

def conectar() -> bool:
    """Conecta ADB al emulador. Retorna True si la conexión fue exitosa."""
    result = subprocess.run(
        ["adb", "connect", DEVICE],
        capture_output=True, text=True
    )
    print(f"[ADB] {result.stdout.strip()}")
    return "connected" in result.stdout or "already" in result.stdout

def tap(x: int, y: int):
    """Toca la pantalla en las coordenadas (x, y)."""
    subprocess.run(["adb", "-s", DEVICE, "shell", "input", "tap", str(x), str(y)])

def tap_sostenido(x: int, y: int, duracion_ms=2000):
    """Mantiene el toque en (x, y) por duracion_ms milisegundos."""
    subprocess.run([
        "adb", "-s", DEVICE, "shell", "input", "swipe",
        str(x), str(y), str(x), str(y), str(duracion_ms)
    ])

def doble_tap(x: int, y: int):
    """Doble click — usado para activar la pócima de teletransporte."""
    tap(x, y)
    subprocess.run(["adb", "-s", DEVICE, "shell", "sleep", "0.1"])
    tap(x, y)

def swipe(x1: int, y1: int, x2: int, y2: int, duracion_ms=800):
    """Deslizar — usado para drag & drop de dragopavos y navegación en mapas."""
    subprocess.run([
        "adb", "-s", DEVICE, "shell", "input", "swipe",
        str(x1), str(y1), str(x2), str(y2), str(duracion_ms)
    ])

def presionar_tecla(keycode: int):
    """Presiona una tecla del sistema Android por su keycode numérico."""
    subprocess.run(["adb", "-s", DEVICE, "shell", "input", "keyevent", str(keycode)])

def presionar_esc():
    """ESC = keycode 4 (Back) en LDPlayer."""
    presionar_tecla(4)

def tomar_captura(ruta_local="assets/captura.png") -> str:
    """Toma screenshot del emulador y lo guarda localmente. Retorna la ruta."""
    subprocess.run(["adb", "-s", DEVICE, "shell", "screencap", "-p", "/sdcard/captura.png"])
    subprocess.run(["adb", "-s", DEVICE, "pull", "/sdcard/captura.png", ruta_local])
    return ruta_local
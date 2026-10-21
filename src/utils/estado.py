"""
ESTADO — La memoria persistente del bot
=========================================
Guarda el progreso en disco usando JSON para que el bot pueda
retomar desde donde quedó si se interrumpe inesperadamente.

CUÁNDO SE USA:
    - Al inicio: cargar el estado guardado para saber si hay
      una sesión incompleta que retomar
    - Durante la ejecución: guardar después de cada cercado
      para no perder el progreso
    - Al finalizar: limpiar el estado para la próxima ejecución

ESTRUCTURA DEL ESTADO:
    {
        "personaje_actual": "Lsd-Andromeda",
        "ciudad_actual":    "brakmar",
        "cercado_actual":   2,
        "fecha_inicio":     "2026-05-26 18:00:00"
    }

TU TURNO:
    Implementar guardar_estado() con json.dump para escribir en disco.
    Implementar limpiar_estado() para cuando termina una sesión completa.
"""

import json
import os

ARCHIVO_ESTADO = "logs/estado.json"

def cargar_estado() -> dict:
    """
    Carga el estado guardado del archivo JSON.
    Si no existe archivo, retorna estado vacío (primera ejecución).
    """
    if not os.path.exists(ARCHIVO_ESTADO):
        return {
            "personaje_actual": None,
            "ciudad_actual":    None,
            "cercado_actual":   0,
            "fecha_inicio":     None
        }
    with open(ARCHIVO_ESTADO, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_estado(personaje: str, ciudad: str, indice_cercado: int):
    """
    Guarda el progreso actual en disco.
    Se llama después de procesar cada cercado.

    TU TURNO: implementar la escritura usando json.dump
    Pista:
        estado = {
            "personaje_actual": personaje,
            "ciudad_actual":    ciudad,
            "cercado_actual":   indice_cercado,
            "fecha_inicio":     timestamp()
        }
        with open(ARCHIVO_ESTADO, "w", ...) as f:
            json.dump(estado, f, ...)
    """
    pass  # TU TURNO

def limpiar_estado():
    """
    Elimina el archivo de estado al terminar una sesión completa.
    Esto indica que la siguiente ejecución es una sesión nueva.
    """
    if os.path.exists(ARCHIVO_ESTADO):
        os.remove(ARCHIVO_ESTADO)
        print("[ESTADO] Estado limpiado para próxima sesión.")

def guardar_estado(personaje: str, ciudad: str, indice_cercado: int):
    from src.utils.helpers import timestamp
    os.makedirs("logs", exist_ok=True)
    estado = {
        "personaje_actual": personaje,
        "ciudad_actual":    ciudad,
        "cercado_actual":   indice_cercado,
        "fecha_inicio":     timestamp()
    }
    with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
"""
Prueba aislada del cambio de personaje.
Ejecutar desde la raíz del proyecto con:
    python tests/prueba_personaje.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.adb_controller import conectar
from src.core.gestor_personajes import cambiar_personaje

if __name__ == "__main__":
    conectar()
    cambiar_personaje("Pachambary")
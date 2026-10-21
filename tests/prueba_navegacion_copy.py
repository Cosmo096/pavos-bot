# tests/prueba_navegacion.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.adb_controller import conectar
from src.core.navegador_copy import teleport_a_ciudad

if __name__ == "__main__":
    conectar()
    teleport_a_ciudad("brakmar")
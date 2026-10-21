# tests/prueba_navegacion.py
"""
Prueba la navegación inteligente con OCR.
El bot lee la posición actual y decide la ruta más eficiente.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.adb_controller import conectar
from src.core.navegador import leer_posicion_actual, determinar_zona, ir_a_ciudad, _usar_zaapi

if __name__ == "__main__":
    conectar()

    # Paso 1: leer posición actual
    print("Leyendo posición actual...")
    posicion = leer_posicion_actual()
    print(f"Posición: {posicion}")

    if posicion:
        zona = determinar_zona(posicion)
        print(f"Zona detectada: {zona}")

    # Paso 2: navegar a Brakmar
    #ir_a_ciudad("brakmar")
    _usar_zaapi("brakmar")
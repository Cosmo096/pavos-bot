# tests/prueba_menu.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.adb_controller import conectar, presionar_esc, tap, tomar_captura
from src.utils.helpers import esperar

if __name__ == "__main__":
    conectar()

    print("Presionando ESC...")
    presionar_esc()
    esperar(2)

    print("Tomando captura con menú abierto...")
    tomar_captura("assets/debug_menu.png")
    print("Captura guardada — verifica que el menú ESC está visible")

    print("Haciendo click en el dropdown...")
    tap(968, 444)
    esperar(1)

    print("Tomando captura con dropdown abierto...")
    tomar_captura("assets/debug_dropdown.png")
    print("Listo — verifica assets/debug_dropdown.png")
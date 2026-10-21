# tests/coordenadas.py
"""
Imprime las coordenadas X,Y cada vez que haces click en cualquier parte.
Haz click directamente sobre LDPlayer para obtener las coordenadas.
Ctrl+C para detener.
"""
from pynput import mouse

def al_hacer_click(x, y, boton, presionado):
    if presionado:
        print(f"X: {x}, Y: {y}")

print("Haz click sobre los elementos en LDPlayer.")
print("Ctrl+C para detener.\n")

with mouse.Listener(on_click=al_hacer_click) as listener:
    try:
        listener.join()
    except KeyboardInterrupt:
        print("\nListo.")
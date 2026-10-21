"""
GESTOR DE PERSONAJES — Cambio entre cuentas del juego
======================================================
Maneja el flujo de cambio de personaje usando el menú ESC.

FLUJO DE CAMBIO:
    1. Presionar ESC → aparece "Menú principal"
    2. Click en la flecha del dropdown "Cambiar de personaje"
    3. Tomar captura del dropdown abierto
    4. OCR lee todos los nombres visibles y sus posiciones exactas
    5. Click en la posición donde está el nombre buscado
    6. Esperar que cargue el nuevo personaje

POR QUÉ OCR Y NO COORDENADAS FIJAS:
    El orden del dropdown varía según qué personaje está activo,
    por lo que las coordenadas Y de cada opción no son constantes.
    El OCR encuentra el nombre en cualquier posición de la lista.

ZONA DEL DROPDOWN:
    El dropdown se despliega debajo del botón "Cambiar de personaje".
    AJUSTAR: si el recorte no captura todas las opciones, ampliar Y2.
"""

import easyocr
import cv2
from src.core.adb_controller import presionar_esc, tap, tomar_captura
from src.utils.helpers import esperar, guardar_log

# ─── Personajes del juego ─────────────────────────────────────────────────
# El bot los procesa en este orden.
# Los nombres deben coincidir con lo que aparece en el dropdown del juego.
# No importa el orden del dropdown, el OCR lo encuentra en cualquier posición.
PERSONAJES = [
    "Pachambary",
    "Dugtrizi",
    "Jeandings",
    
]

# ─── Coordenadas del menú ESC ─────────────────────────────────────────────
# AJUSTAR: mide en Paint sobre una captura con el menú ESC abierto
COORD_DROPDOWN_FLECHA = (968, 444)   # flecha del dropdown "Cambiar de personaje"

# ─── Zona del dropdown abierto para el OCR ────────────────────────────────
# Esta zona se recorta de la captura para buscar los nombres con OCR.
# Debe incluir todas las opciones del dropdown cuando está desplegado.
# AJUSTAR: amplía Y2 si no captura todos los personajes
DROP_X1, DROP_Y1 = 600, 460
DROP_X2, DROP_Y2 = 950, 720

# EasyOCR inicializado una sola vez
reader = easyocr.Reader(['es', 'en'], gpu=False)

def cambiar_personaje(nombre: str) -> bool:
    """
    Cambia al personaje indicado usando OCR para encontrar su posición.
    Retorna True si encontró y clickeó el nombre, False si no lo encontró.

    El proceso:
        1. Abre el menú ESC y despliega el dropdown
        2. Toma captura del dropdown abierto
        3. OCR lee todos los textos y sus coordenadas en pantalla
        4. Busca el nombre dentro de los textos detectados
        5. Hace click en la posición exacta del nombre encontrado
    """
    guardar_log(f"[PERSONAJES] Buscando personaje: {nombre}")

    # Paso 1: abrir menú ESC y dropdown
    presionar_esc()
    esperar(1)
    tap(*COORD_DROPDOWN_FLECHA)
    esperar(0.8)  # esperar que el dropdown se despliegue completamente

    # Paso 2: captura con el dropdown abierto
    captura_ruta = tomar_captura("assets/debug_dropdown.png")

    # Paso 3: buscar el nombre con OCR
    posicion = _encontrar_nombre_en_dropdown(captura_ruta, nombre)

    if posicion is None:
        guardar_log(f"[PERSONAJES] No se encontró '{nombre}' en el dropdown")
        # Cerrar el menú ESC para no dejarlo abierto
        presionar_esc()
        return False

    # Paso 4: click en la posición encontrada
    tap(*posicion)
    esperar(5)  # esperar carga del personaje
    guardar_log(f"[PERSONAJES] Personaje activo: {nombre}")
    return True

def _encontrar_nombre_en_dropdown(captura_ruta: str, nombre_buscado: str):
    """
    Recorta la zona del dropdown, aplica OCR y retorna las coordenadas
    en pantalla completa donde está el nombre buscado.

    Retorna (x, y) en coordenadas de pantalla completa, o None si no lo encuentra.

    El OCR devuelve bounding boxes relativas al recorte, por eso
    se suma el offset (DROP_X1, DROP_Y1) para obtener coordenadas reales.
    """
    imagen = cv2.imread(captura_ruta)
    if imagen is None:
        return None

    # Recortar solo la zona del dropdown
    recorte = imagen[DROP_Y1:DROP_Y2, DROP_X1:DROP_X2]
    cv2.imwrite("assets/debug_dropdown_recorte.png", recorte)

    # OCR con detail=1 para obtener posición de cada texto
    resultados = reader.readtext(recorte, detail=1)

    nombre_lower = nombre_buscado.lower()

    for (bbox, texto, confianza) in resultados:
        if confianza < 0.3:
            continue

        # Verificar si el nombre buscado está dentro del texto detectado
        # Usamos 'in' porque el dropdown puede mostrar "Nombre (Clase Nivel)"
        if nombre_lower in texto.lower():
            # bbox tiene formato: [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
            # Calculamos el centro del bounding box
            x_centro = int((bbox[0][0] + bbox[2][0]) / 2)
            y_centro = int((bbox[0][1] + bbox[2][1]) / 2)

            # Convertir a coordenadas de pantalla completa sumando el offset
            x_pantalla = DROP_X1 + x_centro
            y_pantalla = DROP_Y1 + y_centro

            guardar_log(f"[PERSONAJES] '{texto}' encontrado en ({x_pantalla}, {y_pantalla})")
            return (x_pantalla, y_pantalla)

    # Si no encontró coincidencia exacta, mostrar qué sí detectó para debug
    textos_detectados = [t for (_, t, c) in resultados if c > 0.3]
    guardar_log(f"[PERSONAJES] Textos detectados en dropdown: {textos_detectados}")
    return None
"""
LECTOR DE DRAGOPAVOS — OCR sobre la ventana de dragopavos
==========================================================
Usa EasyOCR para leer texto de la grilla de dragopavos.

QUÉ LEE:
    - Nombres y niveles de los dragopavos visibles (para el reporte)
    - Contador "Filtro: X / Y" (para saber cuántos aplican al filtro)

CÓMO FUNCIONA EL OCR:
    1. Toma la captura completa del emulador
    2. Recorta solo la zona de la grilla (excluye paneles y filtros)
    3. EasyOCR analiza el texto en esa zona
    4. Se extraen nombres (cortos, alfanuméricos) y niveles (Niv.X)

ZONA DE RECORTE — AJUSTAR:
    Las coordenadas de recorte dependen de tu resolución de LDPlayer.
    Para ajustarlas, abre assets/debug_grilla.png después de una
    ejecución y verifica que el recorte incluye todas las tarjetas
    de dragopavos pero excluye el panel izquierdo de filtros.
"""

import easyocr
import cv2
import re

# Zona de la grilla de dragopavos (excluye panel izquierdo y panel derecho)
# AJUSTAR: debe incluir todas las tarjetas pero no los paneles laterales
GRILLA_X1, GRILLA_Y1 = 265, 85
GRILLA_X2, GRILLA_Y2 = 1195, 540

# Zona del contador "Filtro: X / Y" en la barra superior de la ventana
# AJUSTAR: esta zona está entre el botón Filtro y el botón Todos/Ninguno
CONTADOR_X1, CONTADOR_Y1 = 555, 20
CONTADOR_X2, CONTADOR_Y2 = 760, 50

# EasyOCR se inicializa una sola vez (la primera vez tarda ~5 segundos)
# gpu=False porque LDPlayer usa la GPU, evitamos conflictos
reader = easyocr.Reader(['es', 'en'], gpu=False)

def leer_dragopavos_visibles(captura_ruta: str) -> list:
    """
    Lee los nombres y niveles de los dragopavos en la grilla filtrada.
    Retorna lista de strings: ["fxl Niv.15", "s Niv.8", "pSab Niv.13"]

    Los nombres suelen ser abreviaciones cortas (1-6 caracteres)
    que aparecen en la franja rosada/azul de cada tarjeta.
    Los niveles aparecen como "Niv. X" debajo del nombre.
    """
    imagen = cv2.imread(captura_ruta)
    if imagen is None:
        return []

    recorte = imagen[GRILLA_Y1:GRILLA_Y2, GRILLA_X1:GRILLA_X2]
    cv2.imwrite("assets/debug_grilla.png", recorte)  # para debug visual

    resultados = reader.readtext(recorte, detail=1)
    nombres   = []
    niveles   = []

    for (bbox, texto, confianza) in resultados:
        if confianza < 0.4:
            continue
        texto = texto.strip()

        if re.match(r'Niv\.?\s*\d+', texto, re.IGNORECASE):
            # Es un nivel: normalizar como "Niv.X"
            numero = re.search(r'\d+', texto).group()
            niveles.append(f"Niv.{numero}")
        elif len(texto) <= 8 and texto.replace("-", "").isalnum():
            # Es un nombre de dragopavo (corto y alfanumérico)
            nombres.append(texto)

    # Emparejar nombres con niveles por orden de aparición en la grilla
    dragopavos = []
    for i in range(min(len(nombres), len(niveles))):
        dragopavos.append(f"{nombres[i]} {niveles[i]}")

    print(f"[OCR] {len(dragopavos)} dragopavos detectados: {dragopavos}")
    return dragopavos

def leer_contador_filtro(captura_ruta: str) -> tuple:
    """
    Lee el texto "Filtro: X / Y" y retorna (X, Y) como enteros.
    X = dragopavos que aplican al filtro
    Y = total de dragopavos en el establo

    Retorna (0, 0) si no puede leer el contador.
    """
    imagen = cv2.imread(captura_ruta)
    if imagen is None:
        return (0, 0)

    recorte  = imagen[CONTADOR_Y1:CONTADOR_Y2, CONTADOR_X1:CONTADOR_X2]
    resultado = reader.readtext(recorte, detail=0)
    texto    = " ".join(resultado)

    match = re.search(r'(\d+)\s*/\s*(\d+)', texto)
    if match:
        return (int(match.group(1)), int(match.group(2)))

    return (0, 0)
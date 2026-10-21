"""
DETECTOR DE CERCADO — Los ojos del bot en el mapa y ventanas
=============================================================
Detecta elementos visuales usando OpenCV (template matching).

TEMPLATES NECESARIOS EN assets/templates/:
    puerta_cercado.png  → ícono/puerta del cercado en el mapa
                          (recorta solo la puerta de una captura real)
    ventana_vacia.png   → captura de cuando no hay dragopavos
                          (recorta el área central de la ventana vacía)
    popup_atencion.png  → encabezado "¡Atención!" del popup de límite

CÓMO FUNCIONA EL TEMPLATE MATCHING:
    Compara la imagen de referencia (template) contra la captura actual.
    Si la similitud supera el umbral (0.0 a 1.0), retorna la posición.
    Umbral alto (0.9) = más estricto pero menos falsos positivos.
    Umbral bajo (0.6) = más permisivo pero puede dar falsos positivos.

COORDENADAS ASUMIDAS — AJUSTAR:
    Todas las coordenadas con comentario AJUSTAR deben medirse
    en Paint sobre capturas reales con la ventana de dragopavos abierta.
"""

import cv2
import numpy as np

# Coordenadas de elementos de la ventana de dragopavos
# AJUSTAR según tu resolución de LDPlayer
COORD_CERRAR_VENTANA  = (1256, 14)    # botón X esquina superior derecha
COORD_PANEL_CERCADO   = (1220, 180)   # tab "Cercado (X/10)" panel derecho
COORD_PANEL_ESTABLO   = (1220, 350)   # tab "Establo (X/150)" panel derecho

def detectar_icono(captura_ruta: str, template_ruta: str, umbral=0.8):
    """
    Busca una imagen de referencia dentro de la captura.
    Retorna (x, y) del centro si la encuentra, None si no.

    Este método se usa para detectar cualquier elemento visual:
    puertas, popups, botones específicos, etc.
    """
    captura  = cv2.imread(captura_ruta)
    template = cv2.imread(template_ruta)

    if captura is None or template is None:
        print(f"[DETECTOR] No se pudo leer imagen: {captura_ruta} o {template_ruta}")
        return None

    resultado = cv2.matchTemplate(captura, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(resultado)

    if max_val >= umbral:
        h, w   = template.shape[:2]
        centro = (max_loc[0] + w // 2, max_loc[1] + h // 2)
        print(f"[DETECTOR] Encontrado con confianza {max_val:.2f} en {centro}")
        return centro

    print(f"[DETECTOR] No encontrado (confianza: {max_val:.2f}, umbral: {umbral})")
    return None

def detectar_puerta(captura_ruta: str):
    """
    Detecta la puerta del cercado en el mapa del juego.
    Requiere assets/templates/puerta_cercado.png

    Como los cercados en Brakmar y Bonta tienen puertas diferentes,
    TU TURNO: captura la puerta de cada ciudad y guarda como:
        assets/templates/puerta_cercado_brakmar.png
        assets/templates/puerta_cercado_bonta.png
    """
    # Por ahora busca una template genérica
    # Mejorar cuando tengas templates específicas por ciudad
    return detectar_icono(captura_ruta, "assets/templates/puerta_cercado.png", umbral=0.75)

def ventana_vacia(captura_ruta: str) -> bool:
    """
    Detecta si la ventana de dragopavos no tiene resultados.
    Se activa cuando aparece el texto "X dragopavos no mostrados por el filtro"
    o cuando la ventana del cercado/establo está completamente vacía.
    Requiere assets/templates/ventana_vacia.png
    """
    resultado = detectar_icono(
        captura_ruta,
        "assets/templates/ventana_vacia.png",
        umbral=0.70
    )
    return resultado is not None

def popup_atencion_visible(captura_ruta: str) -> bool:
    """
    Detecta el popup '¡Atención! Solo 10 espacios disponibles'.
    Requiere assets/templates/popup_atencion.png
    """
    return detectar_icono(
        captura_ruta,
        "assets/templates/popup_atencion.png",
        umbral=0.70
    ) is not None
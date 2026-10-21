"""
GESTOR DE FILTROS — Aplica filtros y mueve dragopavos
======================================================
Controla la ventana de filtros de dragopavos:
    - Abre y cierra el panel de filtros
    - Activa los filtros indicados por tipo de cercado
    - Selecciona todos los dragopavos filtrados
    - Arrastra al cercado o al establo mediante swipe

Las coordenadas existentes proceden del emulador anterior y no están
calibradas para scrcpy. La interacción permanece deshabilitada hasta validar
la geometría y cada control en el dispositivo objetivo.
"""

from src.core.adb_controller import swipe, tap, tomar_captura
from src.modules.detector_cercado import popup_atencion_visible
from src.utils.helpers import esperar

# ─── Botones principales de la ventana ────────────────────────────────────
# AJUSTAR según tu resolución
COORD_BOTON_FILTRO      = (325, 30)    # botón "Filtro" (abre/cierra panel)
COORD_TODOS_NINGUNO     = (1144, 30)   # botón "Todos / Ninguno"
COORD_REINICIAR_FILTROS = (133, 541)   # botón "Reiniciar" (limpia todos los filtros)

# ─── Botones de filtro en el panel izquierdo ──────────────────────────────
# Estos botones solo aparecen cuando el panel de filtros está abierto
# AJUSTAR: mide cada botón en Paint con el panel de filtros visible
COORD_FILTROS = {
    "Aguante":   (69,  221),   # botón rojo "Aguante"
    "Amor":      (184, 221),   # botón naranja "Amor"
    "Madurez":   (69,  264),   # botón azul "Madurez"
    "Energia":   (184, 264),   # botón verde "Energía"
    "Serenidad": (400, 64),    # AJUSTAR: aparece como tag activo
    "menos50":   (75,  384),   # botón "< 50%" de cansancio
    "Macho":     (156, 67),    # botón "Macho"
    "Hembra":    (69,  67),    # botón "Hembra"
    "Montable":  (191, 112),   # botón "Montable"
    "Fecunda":   (130, 168),   # botón "Fecunda"
    "Fecundada": (44,  168),   # botón "Fecundada"
    "serenidad_gota": None,
    "serenidad_rayo": None,
    "serenidad_corazon": None,
    "cansancio_menor100": None,
}

# ─── Drag & Drop ──────────────────────────────────────────────────────────
# Punto de origen del arrastre (primer dragopavo de la grilla)
# AJUSTAR: coordenada del primer dragopavo visible en la grilla
COORD_ORIGEN_DRAG     = (355, 160)

# Destinos del arrastre (paneles del lado derecho de la ventana)
# AJUSTAR: mide el centro del tab "Cercado" y "Establo" en el panel derecho
COORD_DESTINO_CERCADO = (1220, 180)   # panel "Cercado (X/10)"
COORD_DESTINO_ESTABLO = (1220, 350)   # panel "Establo (X/150)"

# ─── Popup de confirmación ────────────────────────────────────────────────
# Botón "Sí" del popup "¡Atención! Solo 10 espacios disponibles"
# AJUSTAR según posición real del popup
COORD_BOTON_CONFIRMAR_LIMITE = None
COORDENADAS_UI_CALIBRADAS = False


def _exigir_ui_calibrada() -> None:
    if not COORDENADAS_UI_CALIBRADAS:
        raise RuntimeError(
            "La UI de cercados no está calibrada para scrcpy; no se enviaron acciones."
        )


def _enviar_tap(
    x: int, y: int, personaje: str | None = None
) -> None:
    if not tap(x, y, personaje=personaje):
        raise RuntimeError("Falló el tap de UI; se detuvo la operación.")


def validar_filtros_configurados(lista_filtros: list[str]) -> None:
    """Falla antes de tocar la UI si falta una coordenada calibrada."""
    _exigir_ui_calibrada()
    sin_calibrar = [
        filtro
        for filtro in lista_filtros
        if filtro not in COORD_FILTROS or COORD_FILTROS[filtro] is None
    ]
    if sin_calibrar:
        raise RuntimeError(
            "Filtros sin coordenada calibrada: " + ", ".join(sin_calibrar)
        )


def aplicar_filtros(lista_filtros: list[str], personaje: str | None = None):
    """
    Abre el panel de filtros y activa los filtros indicados.

    lista_filtros: lista de claves del diccionario COORD_FILTROS
    Ejemplo: ["Aguante", "menos50", "Hembra"]

    El sexo (Macho/Hembra) lo agrega bot.py automáticamente
    según la ciudad, no es necesario incluirlo manualmente aquí.
    """
    validar_filtros_configurados(lista_filtros)
    _enviar_tap(*COORD_BOTON_FILTRO, personaje=personaje)   # abrir panel
    esperar(0.5)

    for filtro in lista_filtros:
        coordenada = COORD_FILTROS[filtro]
        if coordenada is None:
            raise RuntimeError(f"El filtro {filtro!r} no tiene coordenada calibrada.")
        _enviar_tap(*coordenada, personaje=personaje)
        esperar(0.3)

    _enviar_tap(*COORD_BOTON_FILTRO, personaje=personaje)   # cerrar panel
    esperar(0.5)

def reiniciar_filtros(personaje: str | None = None):
    """
    Limpia todos los filtros activos presionando el botón Reiniciar.
    Siempre se llama antes de aplicar nuevos filtros para partir limpio.
    """
    _exigir_ui_calibrada()
    _enviar_tap(*COORD_BOTON_FILTRO, personaje=personaje)
    esperar(0.5)
    _enviar_tap(*COORD_REINICIAR_FILTROS, personaje=personaje)
    esperar(0.3)
    _enviar_tap(*COORD_BOTON_FILTRO, personaje=personaje)
    esperar(0.5)

def seleccionar_todos(personaje: str | None = None):
    """
    Click en 'Todos / Ninguno' para seleccionar todos los dragopavos
    que aparecen en la grilla filtrada (borde amarillo en cada tarjeta).
    """
    _exigir_ui_calibrada()
    _enviar_tap(*COORD_TODOS_NINGUNO, personaje=personaje)
    esperar(0.5)

def arrastrar_a_cercado(personaje: str | None = None):
    """
    Arrastra los dragopavos seleccionados al panel Cercado.
    Después verifica si apareció el popup de capacidad.
    """
    _exigir_ui_calibrada()
    _ejecutar_drag(COORD_ORIGEN_DRAG, COORD_DESTINO_CERCADO, personaje=personaje)
    esperar(1.5)
    _confirmar_popup_si_existe(personaje)

def arrastrar_a_establo(personaje: str | None = None):
    """
    Arrastra los dragopavos seleccionados al panel Establo.
    """
    _exigir_ui_calibrada()
    _ejecutar_drag(COORD_ORIGEN_DRAG, COORD_DESTINO_ESTABLO, personaje=personaje)
    esperar(1.5)
    _confirmar_popup_si_existe(personaje)

def _ejecutar_drag(
    origen: tuple[int, int],
    destino: tuple[int, int],
    duracion_ms: int = 1000,
    personaje: str | None = None,
):
    """
    Ejecuta el swipe que simula el drag & drop.
    El swipe lento (1000ms) es necesario para que el juego reconozca
    el arrastre correctamente.
    """
    x1, y1 = origen
    x2, y2 = destino
    if not swipe(x1, y1, x2, y2, duracion_ms, personaje=personaje):
        raise RuntimeError("Falló el swipe de arrastre; se detuvo la operación.")

def _confirmar_popup_si_existe(personaje: str | None = None):
    """
    Verifica si apareció el popup de límite de 10 dragopavos
    y falla de forma segura si el botón de confirmación no está calibrado.
    """
    captura = tomar_captura(personaje=personaje)
    if captura is None:
        raise RuntimeError("Falló la captura al validar el popup de capacidad.")
    if popup_atencion_visible(captura):
        if COORD_BOTON_CONFIRMAR_LIMITE is None:
            raise RuntimeError(
                "Popup de capacidad detectado, pero el botón de confirmación "
                "no está calibrado."
            )
        print("[FILTROS] Popup de capacidad detectado; confirmando.")
        _enviar_tap(*COORD_BOTON_CONFIRMAR_LIMITE, personaje=personaje)
        esperar(1)
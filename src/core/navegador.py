"""
NAVEGADOR DE MAPAS — Navegación inteligente con OCR
=====================================================
Lee la posición actual del personaje desde la esquina superior izquierda
y decide el camino más eficiente para llegar al destino.

LÓGICA DE NAVEGACIÓN INTELIGENTE:
    1. Lee coordenadas actuales con OCR
    2. Determina en qué zona está el personaje:
       - En cercados de Brakmar → navega directo por bordes
       - En cercados de Bonta   → navega directo por bordes
       - En centro de Brakmar   → usa Zaapi directo
       - En centro de Bonta     → usa Zaapi directo
       - En otra ciudad/zona    → usa pócima de teleport
    3. Si ya está en el cercado destino → empieza desde ahí

VENTANA DE POSICIÓN (esquina superior izquierda):
    Muestra algo como:
        "Brakmar (Barrio de los ganaderos)"
        "-32,37, Nivel 10"
    El OCR lee la segunda línea para extraer las coordenadas X,Y.

ZAAPI:
    Presente en todos los mapas. Si el personaje está en cualquier
    mapa de la ciudad, puede usarlo sin necesitar la pócima.
    Se detecta visualmente con template matching.

OFFSET DE COORDENADAS:
    La ventana de LDPlayer está fija en (0,0) de pantalla.
    Coordenada ADB = coordenada_Windows - OFFSET
    OFFSET_X = 172, OFFSET_Y = 56  (calibrado manualmente, estable)
"""

# ============================================================================
# IMPORTS
# ============================================================================
import re
import easyocr
import cv2
import numpy as np
from src.core.adb_controller import tap, doble_tap, tomar_captura, presionar_esc
from src.utils.helpers import esperar, guardar_log, calcular_ruta

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# ─── OCR ──────────────────────────────────────────────────────────────────
reader = easyocr.Reader(['es', 'en'], gpu=False)

# ─── Zona de lectura de posición (esquina superior izquierda) ─────────────
# Recorta el área donde aparece "-32,37, Nivel 10"
# Ampliamos un poco hacia la izquierda (X1=0) y hacia arriba (Y1=45)
# para no cortar el guión negativo que está al borde del recorte
POS_X1, POS_Y1 = 0,   45
POS_X2, POS_Y2 = 400, 120

# ─── Pócimas de teleport ──────────────────────────────────────────────────
# Coordenadas ADB calibradas con offset X-172, Y-56
COORD_POCIMA_BRAKMAR = (1345, 145)
COORD_POCIMA_BONTA   = (1416, 229)

# ─── Zaapi ────────────────────────────────────────────────────────────────
# AJUSTAR con tests/coordenadas.py una vez calibrado
COORD_ZAAPI_BRAKMAR = (1140, 385)   
COORD_ZAAPI_BONTA   = (570, 340)   # PENDIENTE CALIBRAR

# ─── Ventana del Zaapi (misma UI en ambas ciudades) ───────────────────────
# AJUSTAR con tests/coordenadas.py
COORD_TAB_MERCADILLOS     = (705, 235)   
COORD_MERCADILLO_ANIMALES = (665, 435)   
COORD_BOTON_ACEPTAR       = (775, 720)   
COORD_CERRAR_ZAAPI = (1200, 150)  # botón X de la ventana Zaapi — AJUSTAR

# ─── Bordes del mapa ──────────────────────────────────────────────────────
BORDES = {
    "derecha":   (1160, 400),
    "izquierda": (20,   400),
    "arriba":    (580,  20),
    "abajo":     (580,  750),
}

# ─── Zonas geográficas ────────────────────────────────────────────────────
# Rangos de coordenadas del juego que definen cada zona.
# NOTA: en Dofus Touch X puede ser negativo, Y siempre positivo en Brakmar
# y negativo en Bonta. Los rangos son INCLUSIVOS en ambos extremos.
#
# Brakmar cercados: X entre -34 y -28, Y entre 35 y 40
# Bonta cercados:   X entre -40 y -34, Y entre -60 y -54
ZONAS = {
    "cercados_brakmar": {
        "x": (-32, -30),
        "y": ( 37,  38),
    },
    "centro_brakmar": {
    "x": (-27, -25),  # margen de ±1 por si OCR lee -25 o -27
    "y": (35,   37),  # margen de ±1
    },
    "cercados_bonta": {
        "x": (-40, -34),
        "y": (-60, -54),
    },
    "centro_bonta": {
        "x": (-35, -31),
        "y": (-58, -54),
    },
}

# ─── Templates para detección de pócimas ───────────────────────────────────
# Usar template matching en lugar de coordenadas fijas cuando sea posible
TEMPLATE_POCIMA_BRAKMAR = "assets/templates/pocima_brakmar.png"
TEMPLATE_POCIMA_BONTA   = "assets/templates/pocima_bonta.png"
CONFIANZA_TEMPLATE_MIN = 0.65  # 80% de coincidencia mínima
# ============================================================================
# VARIABLES GLOBALES
# ============================================================================

# Mapa actual (se actualiza al navegar)
_mapa_actual = None


# ============================================================================
# HELPERS OCR
# ============================================================================

# ─── Preprocesamiento de imagen para OCR ─────────────────────────────────

def _preprocesar_para_ocr(recorte: np.ndarray) -> np.ndarray:
    """
    Escala y mejora contraste del recorte para que EasyOCR detecte
    correctamente el guión '-' de las coordenadas negativas.

    El guión es muy delgado en resolución original y EasyOCR lo omite.
    Escalar 3x lo hace suficientemente visible para el modelo OCR.

    Guarda debug en assets/debug_posicion_procesada.png para diagnóstico.
    """
    # Escalar 3x — el guión necesita más píxeles para ser reconocido
    alto, ancho = recorte.shape[:2]
    escalada = cv2.resize(
        recorte,
        (ancho * 3, alto * 3),
        interpolation=cv2.INTER_CUBIC
    )

    # Convertir a escala de grises
    gris = cv2.cvtColor(escalada, cv2.COLOR_BGR2GRAY)

    # CLAHE: mejora contraste local sin saturar zonas brillantes
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gris = clahe.apply(gris)

    # Umbral adaptativo: binariza el texto independientemente del fondo
    procesada = cv2.adaptiveThreshold(
        gris, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )

    cv2.imwrite("assets/debug_posicion_procesada.png", procesada)
    return procesada

def _normalizar_guiones(texto: str) -> str:
    """
    EasyOCR a veces lee el guión '-' como '–' (en dash) o '—' (em dash)
    dependiendo del grosor del trazo. Normalizamos todos a '-' estándar.
    También limpia espacios que puedan aparecer entre el guión y el número.
    """
    # Reemplazar variantes de guión
    texto = texto.replace("–", "-").replace("—", "-").replace("‐", "-")
    texto = texto.replace("−", "-").replace("➖", "-")

    # A veces OCR lee "- 32" con espacio, lo normalizamos a "-32"
    texto = re.sub(r'-\s+(\d)', r'-\1', texto)

    return texto

def _extraer_coordenadas(texto: str) -> str | None:
    """
    Extrae el par de coordenadas X,Y de un texto OCR.
    Maneja variantes como:
        "-32,37"    → normal
        "32,37"     → sin guión (OCR lo perdió) — NO se asume negativo
        "-32, 37"   → con espacio
        "- 32,37"   → guión separado
        "–32,37"    → guión largo
    Retorna "X,Y" o None.
    """
    if not texto:
        return None

    texto_norm = _normalizar_guiones(texto)

    # Patrón principal: número opcional con signo, coma, número opcional con signo
    match = re.search(r'(-?\d+)\s*,\s*(-?\d+)', texto_norm)
    if match:
        x = match.group(1)
        y = match.group(2)
        return f"{x},{y}"

    return None

def _inferir_signos(x: int, y: int) -> tuple:
    """
    Aplica conocimiento del dominio para corregir signos negativos
    que el OCR pudo haber omitido.

    Zonas conocidas y sus rangos absolutos:
        Brakmar cercados/centro: |X| en (24,34), Y en (34,40)
        Bonta cercados/centro:   |X| en (31,40), |Y| en (54,60)

    Retorna (x_corregido, y_corregido) o (None, None) si no aplica.
    """
    ax = abs(x)
    ay = abs(y)

    # Zona Brakmar: Y positivo entre 34-40, X negativo entre -24 y -34
    if 34 <= ay <= 40:
        x_corr = -ax  # X siempre negativo en Brakmar
        y_corr =  ay  # Y siempre positivo en Brakmar
        guardar_log(f"[NAV] Inferencia Brakmar: ({x_corr},{y_corr})")
        return x_corr, y_corr

    # Zona Bonta: Y negativo entre -54 y -60, X negativo entre -31 y -40
    if 54 <= ay <= 60:
        x_corr = -ax  # X siempre negativo en Bonta
        y_corr = -ay  # Y siempre negativo en Bonta
        guardar_log(f"[NAV] Inferencia Bonta: ({x_corr},{y_corr})")
        return x_corr, y_corr

    # No coincide con ninguna zona conocida
    guardar_log(f"[NAV] Sin inferencia posible para abs({ax},{ay})")
    return None, None

def _extraer_coordenadas_con_inferencia(texto: str) -> str | None:
    """
    Extrae coordenadas X,Y del texto OCR aplicando:
    1. Normalización de caracteres similares al signo negativo
    2. Filtrado de candidatos válidos (coordenadas del juego max ±100)
    3. Inferencia del signo negativo según valor de Y (conocimiento del dominio)

    Retorna string "X,Y" con signos correctos, o None si no hay match.
    """
    # Paso 1: normalizar caracteres similares al guión
    texto_limpio = texto
    for char in ['~', '—', '–', '‐', '⁻', '−']:
        texto_limpio = texto_limpio.replace(char, '-')

    guardar_log(f"[NAV] Texto normalizado: '{texto_limpio}'")

    # Paso 2: buscar TODOS los pares numéricos en el texto
    # El OCR puede generar números espurios del fondo del juego
    # por eso buscamos todos y filtramos por rango válido
    matches = re.findall(r'(-?\d{1,3})\s*,\s*(-?\d{1,3})', texto_limpio)

    if not matches:
        guardar_log("[NAV] No se encontró ningún patrón numérico")
        return None

    guardar_log(f"[NAV] Todos los matches encontrados: {matches}")

    # Paso 3: filtrar solo pares donde ambos valores <= 100 en valor absoluto
    # Las coordenadas del juego Dofus Touch nunca superan ±100
    candidatos = [
        (int(a), int(b)) for a, b in matches
        if abs(int(a)) <= 100 and abs(int(b)) <= 100
    ]

    if not candidatos:
        guardar_log(f"[NAV] Ningún match dentro del rango válido (±100): {matches}")
        return None

    # Tomar el primer candidato válido
    x, y = candidatos[0]
    guardar_log(f"[NAV] Coordenadas crudas del OCR: x={x}, y={y}")

    # Paso 4: inferir signos negativos según conocimiento del dominio
    x, y = _inferir_signos(x, y)

    if x is None:
        guardar_log(f"[NAV] No se pudo inferir zona para abs({abs(x) if x else '?'},{abs(y) if y else '?'})")
        return None

    resultado = f"{x},{y}"
    guardar_log(f"[NAV] Coord final con signos corregidos: {resultado}")
    return resultado

def _clickear_texto_en_pantalla(texto_buscado: str,timeout: int = 6,confianza_minima: float = 0.3) -> bool:
    """
    Busca el texto en pantalla con OCR y hace click en su posición.
    Más robusto que coordenadas fijas porque funciona sin calibración.
    
    Args:
        texto_buscado: texto a buscar (case-insensitive)
        timeout: segundos máximos de espera
        confianza_minima: confianza mínima del OCR (0-1)
    
    Returns:
        True si encontró y clickeó el texto, False si timeout o no encontró
    """
    import time
    inicio = time.time()
    intervalo = 1.0
    texto_buscado_lower = texto_buscado.lower().strip()
    
    while time.time() - inicio < timeout:
        captura = tomar_captura("assets/debug_click_ocr.png")
        imagen = cv2.imread(captura)
        
        # OCR con detail=1 para obtener posición de cada texto
        resultados = reader.readtext(imagen, detail=1)
        
        for (bbox, texto, confianza) in resultados:
            if confianza < confianza_minima:
                continue
            
            texto_limpio = texto.lower().strip()
            
            # Buscar coincidencia (parcial o exacta)
            if texto_buscado_lower in texto_limpio:
                # Calcular centro del bounding box
                x_centro = int((bbox[0][0] + bbox[2][0]) / 2)
                y_centro = int((bbox[0][1] + bbox[2][1]) / 2)
                
                guardar_log(f"[NAV] Clickeando '{texto}' (conf:{confianza:.2f}) en ({x_centro},{y_centro})")
                tap(x_centro, y_centro)
                time.sleep(0.3)  # Pequeña pausa después del click
                return True
        
        guardar_log(f"[NAV] Buscando '{texto_buscado}'... ({int(time.time()-inicio)}s)")
        time.sleep(intervalo)
    
    guardar_log(f"[NAV] Timeout buscando '{texto_buscado}'")
    return False

# ============================================================================
# HELPERS DE TEMPLATE MATCHING
# ============================================================================

def _encontrar_y_clickear_template(ruta_template: str,timeout: int = 5,max_intentos: int = 2) -> bool:
    """
    Busca un template visual en la pantalla usando template matching.
    Si lo encuentra, hace doble click en su centro.
    
    Args:
        ruta_template: Ruta a la imagen template (ej: "assets/templates/pocima_brakmar.png")
        timeout: Tiempo máximo de búsqueda en segundos
        max_intentos: Número de intentos antes de fallar
    
    Returns:
        True si encontró y clickeó el template, False si no encontró tras los intentos
    
    IMPORTANTE: 
        - La pócima requiere DOBLE CLICK para usarse
        - El template debe coincidir exactamente con el ícono en pantalla
        - Guarda debug en assets/debug_template_match.png
    """
    import time
    import cv2
    import numpy as np
    
    template = cv2.imread(ruta_template)
    if template is None:
        guardar_log(f"[NAV] ERROR: No se pudo cargar template: {ruta_template}")
        return False
    
    template_h, template_w = template.shape[:2]
    inicio = time.time()
    intervalo = 1.0
    
    for intento in range(1, max_intentos + 1):
        guardar_log(f"[NAV] Template matching intento {intento}/{max_intentos} para {ruta_template}")
        
        while time.time() - inicio < timeout:
            # Tomar captura de pantalla completa
            captura = tomar_captura("assets/debug_template_match.png")
            pantalla = cv2.imread(captura)
            
            if pantalla is None:
                guardar_log("[NAV] Error al cargar captura para template matching")
                break
            
            # Template matching con método de correlación
            resultado = cv2.matchTemplate(pantalla, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(resultado)
            
            if max_val >= CONFIANZA_TEMPLATE_MIN:
                # Calcular centro del template
                x_centro = max_loc[0] + template_w // 2
                y_centro = max_loc[1] + template_h // 2
                
                guardar_log(f"[NAV] Template encontrado (confianza: {max_val:.2f}) en ({x_centro},{y_centro})")
                
                # DOBLE CLICK para usar la pócima
                doble_tap(x_centro, y_centro)
                return True
            
            guardar_log(f"[NAV] Buscando template... ({int(time.time()-inicio)}s) confianza: {max_val:.2f}")
            time.sleep(intervalo)
        
        # Reiniciar timeout para siguiente intento
        inicio = time.time()
    
    guardar_log(f"[NAV] No se encontró template tras {max_intentos} intentos: {ruta_template}")
    return False

def _esperar_llegada_centro(ciudad: str, timeout: int = 8) -> bool:
    """
    Espera a que el personaje llegue al centro de la ciudad después de usar pócima.
    
    Args:
        ciudad: 'brakmar' o 'bonta'
        timeout: Tiempo máximo de espera en segundos
    
    Returns:
        True si llegó al centro, False si timeout
    
    NOTA: 
        El teleport puede tardar 4-5 segundos, por eso el timeout es generoso.
        El centro de Brakmar es -26,36
        El centro de Bonta es -33,-56
    """
    import time
    
    centro_esperado = "-26,36" if ciudad == "brakmar" else "-33,-56"
    guardar_log(f"[NAV] Esperando llegada al centro de {ciudad}: {centro_esperado}")
    
    # Pausa inicial para el teleport (mínimo 3 segundos)
    guardar_log("[NAV] Pausa inicial para teleport (3s)...")
    time.sleep(3)
    
    inicio = time.time()
    intervalo = 1.5
    
    while time.time() - inicio < timeout:
        posicion = leer_posicion_actual()
        
        if posicion is None:
            guardar_log(f"[NAV] OCR no leyó posición aún... ({int(time.time()-inicio)}s)")
            time.sleep(intervalo)
            continue
        
        if posicion == centro_esperado:
            guardar_log(f"[NAV] ✓ Llegada confirmada al centro de {ciudad}: {posicion}")
            return True
        
        guardar_log(f"[NAV] Posición actual: {posicion}, esperando {centro_esperado}...")
        time.sleep(intervalo)
    
    guardar_log(f"[NAV] Timeout: No se llegó al centro de {ciudad} tras {timeout}s")
    return False

# ============================================================================
# HELPERS DE NAVEGACIÓN
# ============================================================================

def _esperar_texto_en_pantalla(texto_esperado: str, timeout: int = 6) -> bool:
    """
    Toma capturas periódicas y usa OCR hasta encontrar el texto esperado
    o agotar el timeout.

    Útil para confirmar que una ventana o elemento cargó antes de continuar.
    Retorna True si encontró el texto, False si agotó el tiempo.
    """
    import time
    inicio   = time.time()
    intervalo = 1.0  # segundos entre cada captura
    texto_esperado_lower = texto_esperado.lower().strip()

    while time.time() - inicio < timeout:
        captura    = tomar_captura("assets/debug_espera.png")
        imagen     = cv2.imread(captura)
        resultados = reader.readtext(imagen, detail=0)
        texto_ocr  = " ".join(resultados).lower()

        if texto_esperado_lower in texto_ocr:
            guardar_log(f"[NAV] Texto '{texto_esperado}' confirmado en pantalla")
            return True

        guardar_log(f"[NAV] Esperando '{texto_esperado}'... ({int(time.time()-inicio)}s)")
        time.sleep(intervalo)

    guardar_log(f"[NAV] Timeout esperando '{texto_esperado}'")
    guardar_log(f"[NAV] OCR completo: '{texto_ocr[:100]}'")
    return False

def _esperar_posicion_valida(timeout: int = 10, posicion_anterior: str = None) -> str | None:
    """
    Espera hasta que el OCR lea una posición válida Y diferente
    a la posición anterior, confirmando que el mapa realmente cambió.

    Si posicion_anterior es None, retorna cualquier posición válida.
    """
    import time
    
    # Pausa inicial para dar tiempo al juego a iniciar la carga
    guardar_log("[NAV] Pausa inicial esperando carga del mapa...")
    time.sleep(3)
    
    inicio    = time.time()
    intervalo = 1.5

    while time.time() - inicio < timeout:
        posicion = leer_posicion_actual()
        
        if posicion is None:
            guardar_log(f"[NAV] OCR no leyó posición aún...")
            time.sleep(intervalo)
            continue

        # Si no hay posición anterior, cualquier lectura válida sirve
        if posicion_anterior is None:
            return posicion

        # Verificar que la posición cambió respecto a la anterior
        if posicion != posicion_anterior:
            guardar_log(f"[NAV] Cambio de mapa confirmado: {posicion_anterior} → {posicion}")
            return posicion

        guardar_log(f"[NAV] Posición sin cambio ({posicion}), esperando...")
        time.sleep(intervalo)

    guardar_log("[NAV] Timeout: posición no cambió")
    return None

def _usar_pocima_y_zaapi(ciudad: str):
    """
    Teleporta al centro de la ciudad usando la pócima del inventario
    y luego toma el Zaapi al mercadillo de animales.
    
    ESTRATEGIA DE CLICK (template matching primero, fallback coordenadas):
        1. Intenta encontrar la pócima visualmente con template matching
        2. Si encuentra la pócima, hace doble click y valida llegada al centro con OCR
        3. Si falla template matching (2 intentos), usa coordenada fija como fallback
        4. Después de llegar al centro, usa el Zaapi para ir a cercados
    
    IMPORTANTE:
        - El teleport puede tardar 4-5 segundos
        - Se valida activamente la llegada al centro con OCR
        - Si falla la llegada, se puede reintentar (puede ser que la pócima no se usó)
    """
    global _mapa_actual
    
    guardar_log(f"[NAV] Usando pócima de {ciudad}...")
    
    # Configurar según ciudad
    if ciudad == "brakmar":
        ruta_template = TEMPLATE_POCIMA_BRAKMAR
        coord_fallback = COORD_POCIMA_BRAKMAR
        centro_esperado = "-26,36"
    else:  # bonta
        ruta_template = TEMPLATE_POCIMA_BONTA
        coord_fallback = COORD_POCIMA_BONTA
        centro_esperado = "-33,-56"
    
    # ── INTENTAR CON TEMPLATE MATCHING (2 intentos máximo) ──
    exito_template = False
    
    for intento in range(1, 3):  # 2 intentos
        guardar_log(f"[NAV] Buscando pócima visualmente, intento {intento}/2")
        
        if _encontrar_y_clickear_template(ruta_template, timeout=5, max_intentos=1):
            guardar_log(f"[NAV] ✓ Pócima clickeada con template matching (intento {intento})")
            exito_template = True
            break
        else:
            guardar_log(f"[NAV] ⚠ No se encontró pócima en intento {intento}")
            if intento == 1:
                # Pequeña pausa antes de reintentar
                esperar(1)
    
    # ── FALLBACK: usar coordenada fija si template matching falló ──
    if not exito_template:
        guardar_log(f"[NAV] ⚠ Falló template matching, usando coordenada fija para pócima de {ciudad}")
        doble_tap(*coord_fallback)
    
    # ── ESPERAR Y VALIDAR LLEGADA AL CENTRO ──
    if not _esperar_llegada_centro(ciudad, timeout=8):
        guardar_log(f"[NAV] ERROR: No se detectó llegada al centro de {ciudad}")
        # Intentar leer posición actual como fallback
        posicion_actual = leer_posicion_actual()
        if posicion_actual:
            guardar_log(f"[NAV] Posición actual leída: {posicion_actual}")
            _mapa_actual = posicion_actual
        else:
            # Si no podemos leer posición, asumimos el centro (puede ser riesgoso)
            guardar_log(f"[NAV] Asumiendo centro de {ciudad} por falta de OCR")
            _mapa_actual = centro_esperado
    else:
        # Llegada confirmada al centro
        _mapa_actual = centro_esperado
    
    # ── USAR ZAAPI PARA IR A CERCADOS ──
    guardar_log(f"[NAV] Ahora usando Zaapi desde el centro de {ciudad}...")
    _usar_zaapi(ciudad)

def _usar_zaapi(ciudad: str) -> bool:
    """
    Usa el Zaapi para ir al mercadillo de animales de la ciudad.
    
    ESTRATEGIA DE CLICK (OCR primero, fallback coordenadas):
        1. Intenta buscar el texto y clickear en su posición con OCR
        2. Si OCR falla (timeout o no encuentra), usa coordenada fija
        3. Si coordenada fija también falla, cierra ventana y reintenta
    
    Retorna True si llegó al destino, False si falló tras reintentos.
    """
    global _mapa_actual

    guardar_log(f"[NAV] Usando Zaapi de {ciudad}...")

    destino_esperado = "-32,37" if ciudad == "brakmar" else "-36,-56"
    zona_esperada    = "cercados_brakmar" if ciudad == "brakmar" else "cercados_bonta"
    MAX_INTENTOS     = 2

    for intento in range(1, MAX_INTENTOS + 1):
        guardar_log(f"[NAV] Zaapi intento {intento}/{MAX_INTENTOS}")
        posicion_antes = _mapa_actual

        # ── Paso 1: abrir el Zaapi ──────────────────────────────────────
        if ciudad == "brakmar":
            tap(*COORD_ZAAPI_BRAKMAR)
        else:
            tap(*COORD_ZAAPI_BONTA)

        # Esperar que aparezca la ventana del Zaapi
        if not _esperar_texto_en_pantalla("zaapi", timeout=6):
            guardar_log("[NAV] Zaapi no respondió, reintentando...")
            continue

        # ── Paso 2: click en tab Mercadillos ───────────────────────────
        # Esperar que el texto "mercadillos" exista en pantalla
        if not _esperar_texto_en_pantalla("mercadillos", timeout=5):
            guardar_log("[NAV] Tab Mercadillos no apareció")
            tap(*COORD_CERRAR_ZAAPI)
            esperar(1)
            continue
        
        # INTENTO 1: Usar OCR para encontrar y clickear "mercadillos"
        if _clickear_texto_en_pantalla("mercadillos", timeout=3):
            guardar_log("[NAV] ✓ Click en 'Mercadillos' con OCR exitoso")
        else:
            # INTENTO 2 (FALLBACK): Usar coordenada fija
            guardar_log("[NAV] ⚠ Falló OCR, usando coordenada fija para 'Mercadillos'")
            tap(*COORD_TAB_MERCADILLOS)

        # Esperar que cargue la siguiente pantalla
        if not _esperar_texto_en_pantalla("mercadillo de animales", timeout=5):
            guardar_log("[NAV] Opción 'Mercadillo de animales' no apareció")
            tap(*COORD_CERRAR_ZAAPI)
            esperar(1)
            continue

        # ── Paso 3: click en Mercadillo de animales ────────────────────
        # INTENTO 1: Usar OCR para encontrar y clickear
        if _clickear_texto_en_pantalla("mercadillo de animales", timeout=3):
            guardar_log("[NAV] ✓ Click en 'Mercadillo de animales' con OCR exitoso")
        else:
            # INTENTO 2 (FALLBACK): Usar coordenada fija
            guardar_log("[NAV] ⚠ Falló OCR, usando coordenada fija para 'Mercadillo de animales'")
            tap(*COORD_MERCADILLO_ANIMALES)
        
        esperar(1)

        # ── Paso 4: click en Aceptar ───────────────────────────────────
        # INTENTO 1: Usar OCR para encontrar y clickear
        if _clickear_texto_en_pantalla("aceptar", timeout=3):
            guardar_log("[NAV] ✓ Click en 'Aceptar' con OCR exitoso")
        else:
            # INTENTO 2 (FALLBACK): Usar coordenada fija
            guardar_log("[NAV] ⚠ Falló OCR, usando coordenada fija para 'Aceptar'")
            tap(*COORD_BOTON_ACEPTAR)

        # ── Paso 5: validar llegada ────────────────────────────────────
        guardar_log("[NAV] Esperando carga del mapa destino...")
        posicion_nueva = _esperar_posicion_valida(
            timeout=10,
            posicion_anterior=posicion_antes
        )

        if posicion_nueva is None:
            guardar_log("[NAV] No se pudo leer posición tras teletransporte")
            continue

        zona_nueva = determinar_zona(posicion_nueva)
        guardar_log(f"[NAV] Posición tras Zaapi: {posicion_nueva} → zona: {zona_nueva}")

        if zona_nueva == zona_esperada or posicion_nueva == destino_esperado:
            _mapa_actual = posicion_nueva
            guardar_log(f"[NAV] Llegada confirmada: {posicion_nueva}")
            return True

        guardar_log(f"[NAV] Zona incorrecta ({zona_nueva}), se esperaba {zona_esperada}")

    guardar_log(f"[NAV] Falló llegar a {ciudad} tras {MAX_INTENTOS} intentos")
    return False

def _moverse(direccion: str):
    """
    Toca el borde del mapa en la dirección indicada y actualiza
    la coordenada interna según la convención del juego:
        derecha   → X + 1
        izquierda → X - 1
        abajo     → Y + 1
        arriba    → Y - 1
    """
    global _mapa_actual

    if direccion not in BORDES:
        guardar_log(f"[NAV] Dirección inválida: '{direccion}'")
        return

    tap(*BORDES[direccion])
    esperar(2.5)  # esperar carga del mapa siguiente

    if _mapa_actual:
        try:
            x, y = map(int, _mapa_actual.split(","))
            if   direccion == "derecha":    x += 1
            elif direccion == "izquierda":  x -= 1
            elif direccion == "abajo":      y += 1
            elif direccion == "arriba":     y -= 1
            _mapa_actual = f"{x},{y}"
        except ValueError:
            guardar_log(f"[NAV] Error actualizando _mapa_actual: '{_mapa_actual}'")

# ============================================================================
# FUNCIONES PÚBLICAS DEL MÓDULO
# ============================================================================

# ─── Lectura de posición ──────────────────────────────────────────────────
def leer_posicion_actual() -> str | None:
    """
    Lee las coordenadas actuales del personaje desde la esquina
    superior izquierda de la pantalla usando OCR.

    Retorna coordenadas en formato "X,Y" (ej: "-31,37") o None si no pudo leer.

    IMPORTANTE: Las zonas de Brakmar y Bonta siempre tienen X negativo.
    Si el OCR pierde el signo negativo, se infiere desde el contexto:
        - Si Y está entre 35 y 40  → zona Brakmar → X debe ser negativo
        - Si Y está entre 54 y 60  → zona Bonta   → ambos negativos
        - Si no se puede inferir   → se retorna None

    Estrategia de fallback:
        1. Imagen preprocesada (escala 3x + CLAHE + umbral)
        2. Escala de grises simple escalada 3x
        3. Imagen original sin procesar
    En cada intento se aplica corrección de signo negativo.
    """
    global _mapa_actual

    captura = tomar_captura("assets/debug_posicion.png")
    imagen  = cv2.imread(captura)

    if imagen is None:
        guardar_log("[NAV] ERROR: No se pudo cargar la captura de pantalla")
        return None

    recorte = imagen[POS_Y1:POS_Y2, POS_X1:POS_X2]

    if recorte.size == 0:
        guardar_log("[NAV] ERROR: Recorte vacío, verificar POS_X1/Y1/X2/Y2")
        return None

    cv2.imwrite("assets/debug_posicion_recorte.png", recorte)

    # ── Intento 1: imagen preprocesada ──
    procesada  = _preprocesar_para_ocr(recorte)
    resultados = reader.readtext(procesada, detail=0)
    texto      = " ".join(resultados)
    guardar_log(f"[NAV] OCR (preprocesado): '{texto}'")

    coordenadas = _extraer_coordenadas_con_inferencia(texto)
    if coordenadas:
        _mapa_actual = coordenadas
        guardar_log(f"[NAV] Posición actual: {coordenadas}")
        return coordenadas

    # ── Intento 2: escala de grises simple ──
    guardar_log("[NAV] Intento 2: escala de grises...")
    gris = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    gris_escalada = cv2.resize(
        gris,
        (gris.shape[1] * 3, gris.shape[0] * 3),
        interpolation=cv2.INTER_CUBIC
    )
    cv2.imwrite("assets/debug_posicion_gris.png", gris_escalada)
    resultados2 = reader.readtext(gris_escalada, detail=0)
    texto2      = " ".join(resultados2)
    guardar_log(f"[NAV] OCR (gris): '{texto2}'")

    coordenadas = _extraer_coordenadas_con_inferencia(texto2)
    if coordenadas:
        _mapa_actual = coordenadas
        guardar_log(f"[NAV] Posición actual (fallback gris): {coordenadas}")
        return coordenadas

    # ── Intento 3: imagen original sin procesar ──
    guardar_log("[NAV] Intento 3: original...")
    resultados3 = reader.readtext(recorte, detail=0)
    texto3      = " ".join(resultados3)
    guardar_log(f"[NAV] OCR (original): '{texto3}'")

    coordenadas = _extraer_coordenadas_con_inferencia(texto3)
    if coordenadas:
        _mapa_actual = coordenadas
        guardar_log(f"[NAV] Posición actual (fallback original): {coordenadas}")
        return coordenadas

    guardar_log("[NAV] No se pudo leer posición en ningún intento.")
    return None

def determinar_zona(coordenadas: str) -> str:
    """
    Determina en qué zona del juego está el personaje según sus coordenadas.

    Retorna: 'cercados_brakmar', 'centro_brakmar',
             'cercados_bonta',   'centro_bonta',  o 'otra'

    NOTA IMPORTANTE sobre los rangos:
        Las coordenadas del juego son enteros con signo.
        Para verificar si X=-32 está en rango (-34, -28):
            -34 <= -32 <= -28  →  True  ✓
        Python maneja esto correctamente con <= en enteros negativos.
    """
    if not coordenadas:
        return "otra"

    try:
        partes = coordenadas.split(",")
        if len(partes) != 2:
            return "otra"
        x, y = int(partes[0].strip()), int(partes[1].strip())
    except (ValueError, AttributeError):
        guardar_log(f"[NAV] Error parseando coordenadas: '{coordenadas}'")
        return "otra"

    for zona, rangos in ZONAS.items():
        x_min, x_max = rangos["x"]
        y_min, y_max = rangos["y"]
        if x_min <= x <= x_max and y_min <= y <= y_max:
            guardar_log(f"[NAV] Coord ({x},{y}) → zona '{zona}'")
            return zona

    guardar_log(f"[NAV] Coord ({x},{y}) → zona 'otra' (fuera de rangos conocidos)")
    return "otra"

# ─── Navegación principal ─────────────────────────────────────────────────
def ir_a_ciudad(ciudad: str):
    """
    Navega al mercadillo de animales de la ciudad usando la ruta
    más eficiente según la posición actual del personaje.

    ciudad: 'brakmar' o 'bonta'
    """
    global _mapa_actual

    ciudad = ciudad.lower()
    if ciudad not in ("brakmar", "bonta"):
        guardar_log(f"[NAV] Ciudad inválida: '{ciudad}'")
        return

    posicion = leer_posicion_actual()
    if posicion is None:
        guardar_log("[NAV] No se pudo leer posición, usando pócima por seguridad")
        _usar_pocima_y_zaapi(ciudad)
        return

    zona = determinar_zona(posicion)
    guardar_log(f"[NAV] Posición: {posicion} | Zona: {zona} | Destino: {ciudad}")

    # Ya está en los cercados de la ciudad destino → no necesita nada
    if zona == f"cercados_{ciudad}":
        guardar_log(f"[NAV] Ya en cercados de {ciudad}, navegando directo por bordes")
        _mapa_actual = posicion
        return  # bot.py llamará ir_a_mapa() desde aquí

    # Está en el centro de la ciudad destino → solo Zaapi
    if zona == f"centro_{ciudad}":
        guardar_log(f"[NAV] En centro de {ciudad}, usando Zaapi directo")
        _usar_zaapi(ciudad)
        return

    # Está en la otra ciudad (centro o cercados) → pócima
    otra_ciudad = "bonta" if ciudad == "brakmar" else "brakmar"
    if zona in (f"cercados_{otra_ciudad}", f"centro_{otra_ciudad}"):
        guardar_log(f"[NAV] En {otra_ciudad}, usando pócima para ir a {ciudad}")
        _usar_pocima_y_zaapi(ciudad)
        return

    # Zona desconocida → pócima por seguridad
    guardar_log(f"[NAV] Zona '{zona}' desconocida, usando pócima por seguridad")
    _usar_pocima_y_zaapi(ciudad)

# ─── Navegación por bordes ────────────────────────────────────────────────
def ir_a_mapa(mapa_destino: str):
    """
    Navega desde el mapa actual hasta el destino moviéndose
    por los bordes del mapa (click en borde → carga mapa adyacente).

    mapa_destino: string "X,Y" ej: "-31,37"

    Si _mapa_actual es None, intenta leerlo con OCR primero.
    """
    global _mapa_actual

    if _mapa_actual is None:
        guardar_log("[NAV] _mapa_actual desconocido, leyendo con OCR...")
        _mapa_actual = leer_posicion_actual()

    if _mapa_actual is None:
        guardar_log("[NAV] ERROR: No se puede navegar sin posición inicial conocida")
        return

    if _mapa_actual == mapa_destino:
        guardar_log(f"[NAV] Ya estamos en {mapa_destino}")
        return

    movimientos = calcular_ruta(_mapa_actual, mapa_destino)
    guardar_log(f"[NAV] Ruta: {_mapa_actual} → {mapa_destino} | pasos: {movimientos}")

    for i, movimiento in enumerate(movimientos):
        guardar_log(f"[NAV] Paso {i+1}/{len(movimientos)}: {movimiento}")
        _moverse(movimiento)

    guardar_log(f"[NAV] Llegamos a {mapa_destino}")

# ============================================================================
# FUNCIONES LEGACY / RESPALDO TEMPORAL
# ============================================================================

def _usar_zaapi_TempGuardado(ciudad: str):
    """
    Usa el Zaapi para ir al mercadillo de animales de la ciudad.
    Secuencia: abrir Zaapi → tab Mercadillos → Mercadillo de animales → Aceptar
    """
    global _mapa_actual

    guardar_log(f"[NAV] Usando Zaapi de {ciudad}...")

    if ciudad == "brakmar":
        tap(*COORD_ZAAPI_BRAKMAR)
    else:
        tap(*COORD_ZAAPI_BONTA)

    esperar(4)
    tap(*COORD_TAB_MERCADILLOS)
    esperar(1)
    tap(*COORD_MERCADILLO_ANIMALES)
    esperar(1)
    tap(*COORD_BOTON_ACEPTAR)
    esperar(4)  # esperar carga del mapa destino

    # Actualizamos mapa_actual con el destino conocido del Zaapi
    if ciudad == "brakmar":
        _mapa_actual = "-32,37"
    else:
        _mapa_actual = "-36,-56"

    guardar_log(f"[NAV] Llegamos al mercadillo de {ciudad}: {_mapa_actual}")

def leer_posicion_actual_TempGuardado() -> str | None:
    """
    Lee las coordenadas actuales del personaje desde la esquina
    superior izquierda de la pantalla usando OCR.

    Retorna coordenadas en formato "X,Y" (ej: "-32,37") o None si no pudo leer.

    Estrategia de fallback:
        1. Intenta con imagen preprocesada (escala 3x + CLAHE + umbral)
        2. Si falla, intenta con imagen en escala de grises simple
        3. Si falla, intenta con imagen original sin procesar
    """
    global _mapa_actual

    captura = tomar_captura("assets/debug_posicion.png")
    imagen  = cv2.imread(captura)

    if imagen is None:
        guardar_log("[NAV] ERROR: No se pudo cargar la captura de pantalla")
        return None

    recorte = imagen[POS_Y1:POS_Y2, POS_X1:POS_X2]
    cv2.imwrite("assets/debug_posicion_recorte.png", recorte)

    # ── Intento 1: imagen preprocesada ──
    procesada  = _preprocesar_para_ocr(recorte)
    resultados = reader.readtext(procesada, detail=0)
    texto      = " ".join(resultados)
    guardar_log(f"[NAV] OCR (preprocesado): '{texto}'")

    coordenadas = _extraer_coordenadas(texto)
    if coordenadas:
        _mapa_actual = coordenadas
        guardar_log(f"[NAV] Posición actual: {coordenadas}")
        return coordenadas

    # ── Intento 2: escala de grises simple ──
    guardar_log("[NAV] Intento 2: escala de grises simple...")
    gris = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    gris_escalada = cv2.resize(gris, (gris.shape[1] * 3, gris.shape[0] * 3),
                               interpolation=cv2.INTER_CUBIC)
    cv2.imwrite("assets/debug_posicion_gris.png", gris_escalada)
    resultados2 = reader.readtext(gris_escalada, detail=0)
    texto2      = " ".join(resultados2)
    guardar_log(f"[NAV] OCR (gris): '{texto2}'")

    coordenadas = _extraer_coordenadas(texto2)
    if coordenadas:
        _mapa_actual = coordenadas
        guardar_log(f"[NAV] Posición actual (fallback gris): {coordenadas}")
        return coordenadas

    # ── Intento 3: imagen original sin procesar ──
    guardar_log("[NAV] Intento 3: imagen original sin procesar...")
    resultados3 = reader.readtext(recorte, detail=0)
    texto3      = " ".join(resultados3)
    guardar_log(f"[NAV] OCR (original): '{texto3}'")

    coordenadas = _extraer_coordenadas(texto3)
    if coordenadas:
        _mapa_actual = coordenadas
        guardar_log(f"[NAV] Posición actual (fallback original): {coordenadas}")
        return coordenadas

    guardar_log(f"[NAV] No se pudo leer posición en ningún intento.")
    return None

def _esperar_posicion_valida_TempGuardado(timeout: int = 8) -> str | None:
    """
    Espera hasta que el OCR lea una posición válida en la esquina
    superior izquierda, indicando que el mapa terminó de cargar.

    Retorna la posición en formato "X,Y" o None si agotó el timeout.
    """
    import time
    inicio    = time.time()
    intervalo = 1.5

    while time.time() - inicio < timeout:
        posicion = leer_posicion_actual()
        if posicion is not None:
            return posicion
        guardar_log(f"[NAV] Esperando posición válida... ({int(time.time()-inicio)}s)")
        time.sleep(intervalo)

    return None

def _usar_pocima_y_zaapi_TempGuardado(ciudad: str):
    """
    Teleporta al centro de la ciudad usando la pócima del inventario
    y luego toma el Zaapi al mercadillo de animales.
    """
    global _mapa_actual

    guardar_log(f"[NAV] Usando pócima de {ciudad}...")

    if ciudad == "brakmar":
        doble_tap(*COORD_POCIMA_BRAKMAR)
        _mapa_actual = "-26,36"
    else:
        doble_tap(*COORD_POCIMA_BONTA)
        _mapa_actual = "-33,-56"

    esperar(3)  # esperar carga del mapa
    _usar_zaapi(ciudad)




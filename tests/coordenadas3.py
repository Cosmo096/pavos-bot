# tests/coordenadas.py
"""
Captura coordenadas ADB correctas para LDPlayer en Windows.

═══════════════════════════════════════════════════════════════
  POR QUÉ FUNCIONA ASÍ
═══════════════════════════════════════════════════════════════

  LDPlayer tiene dos sistemas de coordenadas:
    • Windows: lo que ve el mouse (1920x1080 en tu pantalla)
    • ADB:     lo que ve el juego (1600x900, resolución lógica del emulador)

  La relación entre ambos NO es una escala sino un OFFSET:
    ADB_x = Windows_x - OFFSET_X
    ADB_y = Windows_y - OFFSET_Y

  Esto es así porque LDPlayer mapea 1:1 sus píxeles internos a la pantalla
  (no escala), simplemente el área de juego empieza después de los bordes
  y barras de la ventana.

  Tu ventana está fija en la esquina (0,0) de pantalla, entonces:
    OFFSET_X = 172  (borde izquierdo de LDPlayer + barra lateral interna)
    OFFSET_Y = 56   (barra de título Windows + barra superior de LDPlayer)

  Verificado empíricamente: COORD_POCIMA_BRAKMAR = (1346, 173) ADB
  corresponde al ítem en el panel derecho del juego, y funciona.

═══════════════════════════════════════════════════════════════
  CUÁNDO RECALIBRAR
═══════════════════════════════════════════════════════════════

  Solo necesitas recalibrar si cambias el TAMAÑO de la ventana de LDPlayer.
  Si solo MUEVES la ventana → NO recalibrar, el script la detecta solo.
  Si la ventana sigue en la esquina (0,0) → OFFSET_X/Y son correctos siempre.

  Para recalibrar:
    1. Corre este script
    2. Haz click en un elemento cuya coordenada ADB ya conoces
       (ej: la pócima de Brakmar → debería dar ADB ≈ 1346, 173)
    3. Si hay desfase, ajusta MARGEN_INTERNO_X / MARGEN_INTERNO_Y
       (no toques OFFSET_X/Y directamente, se calculan solos)

═══════════════════════════════════════════════════════════════
  USO
═══════════════════════════════════════════════════════════════

  1. Corre: python tests/coordenadas.py
  2. Haz click sobre elementos en LDPlayer
  3. Las coordenadas ADB aparecen en consola
  4. Copia esos valores a los módulos que corresponda
  5. Ctrl+C para detener

"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import subprocess
from pynput import mouse

# ─── Márgenes internos de LDPlayer ───────────────────────────────────────
# El área de juego empieza DESPUÉS de los bordes de la ventana Windows
# más la barra de herramientas interna de LDPlayer.
# Estos valores son constantes mientras no cambies el TAMAÑO de la ventana.
#
# Verificado: con ventana en (0,0), ADB = Windows - (MARGEN_X, MARGEN_Y)
MARGEN_INTERNO_X = 172   # píxeles desde el borde izquierdo de la ventana
MARGEN_INTERNO_Y = 56    # píxeles desde el borde superior de la ventana

# ─── Resolución lógica ADB ───────────────────────────────────────────────
# Verificar con: adb shell wm size
ADB_W = 1600
ADB_H = 900


# ─── Detección de posición de ventana ────────────────────────────────────

def detectar_posicion_ventana() -> tuple[int, int] | None:
    """
    Detecta la posición actual de la esquina superior izquierda de la
    ventana de LDPlayer en coordenadas de pantalla.

    Si la ventana está en (0,0) → retorna (0, 0).
    Si la ventana fue movida    → retorna la nueva posición.
    Si no se puede detectar     → retorna None (se usará (0,0) por defecto).
    """
    cmd = r'''
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class LDDetect {
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
}
public struct RECT { public int Left, Top, Right, Bottom; }
"@
$proc = Get-Process | Where-Object {
    $_.MainWindowTitle -like "*LDPlayer*"  -or
    $_.MainWindowTitle -like "*LDMultiPlayer*" -or
    $_.ProcessName     -like "*dnplayer*"
} | Sort-Object { $_.MainWindowTitle.Length } -Descending | Select-Object -First 1

if ($proc) {
    $rect = New-Object RECT
    [LDDetect]::GetWindowRect($proc.MainWindowHandle, [ref]$rect) | Out-Null
    $ancho = $rect.Right - $rect.Left
    $alto  = $rect.Bottom - $rect.Top
    Write-Output "$($rect.Left),$($rect.Top),$ancho,$alto"
} else {
    Write-Output "NOT_FOUND"
}
'''
    try:
        resultado = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True, text=True, timeout=5
        )
        salida = resultado.stdout.strip()

        if salida == "NOT_FOUND" or not salida:
            return None

        partes = list(map(int, salida.split(",")))
        left, top, ancho, alto = partes

        # Sanity check: la ventana debe tener tamaño razonable
        if ancho < 800 or alto < 500:
            print(f"[WARN] Tamaño de ventana sospechoso: {ancho}x{alto}")
            return None

        return left, top

    except Exception as e:
        print(f"[WARN] No se pudo detectar ventana LDPlayer: {e}")
        return None


# ─── Inicialización ───────────────────────────────────────────────────────

pos_ventana = detectar_posicion_ventana()

if pos_ventana is not None:
    win_left, win_top = pos_ventana
    print(f"[OK]  Ventana LDPlayer detectada en: ({win_left}, {win_top})")
else:
    win_left, win_top = 0, 0
    print(f"[WARN] No se detectó ventana LDPlayer, asumiendo posición (0, 0)")

# Offset final = posición de la ventana + márgenes internos de LDPlayer
OFFSET_X = win_left + MARGEN_INTERNO_X
OFFSET_Y = win_top  + MARGEN_INTERNO_Y

print(f"[OK]  Resolución ADB: {ADB_W}x{ADB_H}")
print(f"[OK]  Offset activo: X={OFFSET_X}, Y={OFFSET_Y}")
print(f"      (ventana en ({win_left},{win_top}) + márgenes internos ({MARGEN_INTERNO_X},{MARGEN_INTERNO_Y}))")
print()
print("─" * 55)
print("  Haz click sobre elementos en LDPlayer.")
print("  Las coordenadas ADB aparecen a continuación.")
print("  Ctrl+C para detener.")
print("─" * 55)
print()

# Referencia de verificación rápida
print("  REFERENCIA (verificar que estos valores sean correctos):")
print(f"  Pócima Brakmar esperada → ADB(1346, 173)")
print(f"  Pócima Bonta   esperada → ADB(1416, 229)")
print()


# ─── Listener de clicks ───────────────────────────────────────────────────

def al_hacer_click(x, y, boton, presionado):
    if not presionado:
        return

    x_adb = x - OFFSET_X
    y_adb = y - OFFSET_Y

    # Detectar si el click fue fuera del área de juego
    fuera = ""
    if x_adb < 0 or x_adb > ADB_W or y_adb < 0 or y_adb > ADB_H:
        fuera = "  ← FUERA DEL ÁREA DE JUEGO"

    boton_str = "izq" if boton == mouse.Button.left else "der"
    print(f"  [{boton_str}]  Windows({x:5d}, {y:5d})  →  ADB({x_adb:5d}, {y_adb:5d}){fuera}")


with mouse.Listener(on_click=al_hacer_click) as listener:
    try:
        listener.join()
    except KeyboardInterrupt:
        print("\n[OK] Listo.")
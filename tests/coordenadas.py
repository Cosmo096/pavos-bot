# tests/coordenadas.py
"""
Captura coordenadas ADB correctas para LDPlayer.

CÓMO FUNCIONA:
    LDPlayer tiene resolución lógica 1600x900 (confirmar con: adb shell wm size)
    La ventana Windows empieza en una posición variable en pantalla.
    El offset (WIN_X, WIN_Y) es la esquina superior izquierda del área
    de juego dentro de la ventana de LDPlayer (excluye bordes y barra de título).

    Coordenada ADB = (click_windows_x - WIN_X, click_windows_y - WIN_Y)
    No hay escala porque LDPlayer mapea 1:1 dentro del área de juego.

CALIBRACIÓN (hacer una vez si las coords se desfasan):
    1. Corre este script
    2. Haz click en una esquina conocida del juego (ej: esquina superior izquierda)
    3. Ajusta OFFSET_X y OFFSET_Y hasta que el ADB coincida con lo esperado

OFFSET ACTUAL: X=172, Y=56  (calibrado manualmente, funciona con ventana maximizada)
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pynput import mouse
import subprocess

# ─── Offset calibrado manualmente ────────────────────────────────────────
# Estos valores corresponden al borde izquierdo y superior del área
# de juego dentro de la ventana LDPlayer, en coordenadas Windows.
# Si LDPlayer se mueve o cambia de tamaño, recalibrar corriendo este script
# y ajustando los valores hasta que los taps caigan donde se espera.
OFFSET_X = 172
OFFSET_Y = 56

# ─── Detección automática de posición de ventana (opcional) ──────────────
def detectar_offset_ventana():
    """
    Intenta detectar automáticamente el offset usando GetWindowRect.
    Si falla o da valores incoherentes, usa el offset manual.
    """
    cmd = r'''
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
}
public struct RECT { public int Left, Top, Right, Bottom; }
"@
$proc = Get-Process | Where-Object {
    $_.MainWindowTitle -like "*LDPlayer*" -or
    $_.MainWindowTitle -like "*LDMultiPlayer*" -or
    $_.ProcessName     -like "*dnplayer*"
} | Select-Object -First 1
if ($proc) {
    $rect = New-Object RECT
    [Win32]::GetWindowRect($proc.MainWindowHandle, [ref]$rect) | Out-Null
    Write-Output "$($rect.Left),$($rect.Top),$($rect.Right),$($rect.Bottom)"
}
'''
    try:
        resultado = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True, text=True, timeout=5
        )
        partes = list(map(int, resultado.stdout.strip().split(",")))
        left, top, right, bottom = partes
        ancho = right - left
        alto  = bottom - top

        # Sanity check: la ventana debe ser razonablemente grande
        if ancho < 800 or alto < 500:
            return None

        print(f"[AUTO] Ventana detectada: pos=({left},{top}) tamaño={ancho}x{alto}")
        return left, top, ancho, alto
    except Exception as e:
        print(f"[AUTO] Detección automática falló: {e}")
        return None


# ─── Inicialización ───────────────────────────────────────────────────────
info = detectar_offset_ventana()

if info:
    win_left, win_top, win_w, win_h = info
    # GetWindowRect incluye bordes y barra de título de Windows.
    # LDPlayer en Windows 11 tiene aprox 7px de borde y 30px de título,
    # pero varía. Usamos el offset manual como referencia más confiable.
    # Si la detección automática da un left/top razonable, lo usamos;
    # si no, caemos al offset manual.
    #
    # Nota: cuando la ventana está en (-7,-7) como en tu caso,
    # LDPlayer está "maximizado sin bordes" — el área de juego empieza
    # en (OFFSET_X, OFFSET_Y) desde (0,0) de pantalla.
    if win_left < 0:
        # Ventana semi-maximizada, usar offset manual
        print(f"[INFO] Ventana en posición negativa ({win_left},{win_top}), usando offset manual")
        ox, oy = OFFSET_X, OFFSET_Y
    else:
        ox, oy = win_left + (OFFSET_X - 0), win_top + (OFFSET_Y - 0)
        # En realidad si la ventana se movió, el offset cambia proporcionalmente
        # Fórmula: offset_real = posicion_ventana + margen_interno
        # El margen interno es constante (~172, ~56 desde el borde de la ventana)
        ox = win_left + 172   # margen interno horizontal (borde + toolbar LDPlayer)
        oy = win_top  + 56    # margen interno vertical   (barra de título LDPlayer)
else:
    print("[INFO] No se detectó ventana, usando offset manual")
    ox, oy = OFFSET_X, OFFSET_Y

print(f"[INFO] Offset activo: X={ox}, Y={oy}")
print(f"[INFO] Resolución ADB esperada: 1600x900")
print()
print("Haz click directamente sobre LDPlayer.")
print("Las coordenadas ADB aparecen en consola.")
print("Ctrl+C para detener.\n")


# ─── Listener ────────────────────────────────────────────────────────────
def al_hacer_click(x, y, boton, presionado):
    if presionado:
        x_adb = x - ox
        y_adb = y - oy
        print(f"  Windows({x:4d},{y:4d})  →  ADB({x_adb:4d},{y_adb:4d})")

with mouse.Listener(on_click=al_hacer_click) as listener:
    try:
        listener.join()
    except KeyboardInterrupt:
        print("\nListo.")
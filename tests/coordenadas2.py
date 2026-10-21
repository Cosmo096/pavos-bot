# tests/coordenadas.py
"""
Captura coordenadas ADB correctas usando la resolución real de LDPlayer.
Ejecuta primero: adb shell wm size  → debe dar 1600x900

Uso: corre el script, haz click sobre elementos en LDPlayer,
las coordenadas ADB aparecen en consola. Ctrl+C para detener.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pynput import mouse
import subprocess

# Resolución real del dispositivo ADB
ADB_W, ADB_H = 1310, 782
#ADB_W, ADB_H = 1536, 816

def obtener_posicion_ventana_ldplayer():
    cmd = '''
    Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    public class Win32 {
        [DllImport("user32.dll")]
        public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
        [DllImport("user32.dll")]
        public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    }
    public struct RECT { public int Left, Top, Right, Bottom; }
"@
    $processes = Get-Process | Where-Object { $_.MainWindowTitle -like "*LDPlayer*" -or $_.MainWindowTitle -like "*LDMultiPlayer*" -or $_.ProcessName -like "*dnplayer*" }
    if ($processes) {
        $hwnd = $processes[0].MainWindowHandle
        $rect = New-Object RECT
        [Win32]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
        Write-Output "$($rect.Left),$($rect.Top),$($rect.Right),$($rect.Bottom)"
    }
    '''
    resultado = subprocess.run(
        ["powershell", "-Command", cmd],
        capture_output=True, text=True
    )
    try:
        partes = list(map(int, resultado.stdout.strip().split(",")))
        left, top, right, bottom = partes
        ancho = right - left
        alto  = bottom - top
        if ancho > 0 and alto > 0:
            return left, top, ancho, alto
        return None
    except:
        return None
    
# Obtener posición de la ventana al iniciar
info = obtener_posicion_ventana_ldplayer()
if info:
    WIN_X, WIN_Y, WIN_W, WIN_H = info
    print(f"Ventana LDPlayer: pos=({WIN_X},{WIN_Y}) tamaño={WIN_W}x{WIN_H}")
    print(f"Resolución ADB: {ADB_W}x{ADB_H}")
    ESCALA_X = ADB_W / WIN_W
    ESCALA_Y = ADB_H / WIN_H
    print(f"Escala: {ESCALA_X:.3f}x, {ESCALA_Y:.3f}y\n")
else:
    print("No se pudo detectar ventana LDPlayer, usando offset manual")
    WIN_X, WIN_Y = 172, 56
    ESCALA_X, ESCALA_Y = 1.0, 1.0

def al_hacer_click(x, y, boton, presionado):
    if presionado:
        x_adb = int((x - WIN_X) * ESCALA_X)
        y_adb = int((y - WIN_Y) * ESCALA_Y)
        print(f"Windows({x},{y}) → ADB({x_adb},{y_adb})")

print("Haz click directamente sobre LDPlayer.")
print("Ctrl+C para detener.\n")

with mouse.Listener(on_click=al_hacer_click) as listener:
    try:
        listener.join()
    except KeyboardInterrupt:
        print("\nListo.")
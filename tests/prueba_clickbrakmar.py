#!/usr/bin/env python3
"""
PRUEBA DE PÓCIMA BRAKMAR POR COORDENADAS
=========================================
Usa coordenadas fijas + validación visual para confirmar que es la pócima correcta.
"""

import sys
import os
import time
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.adb_controller import tap, doble_tap, tomar_captura
from src.core.navegador import leer_posicion_actual, determinar_zona, _esperar_llegada_centro
from src.utils.helpers import guardar_log

# Coordenadas de las pócimas en el inventario (AJUSTAR según tu juego)
# Estas coordenadas DEBEN ser calibradas manualmente
COORD_POCIMA_BRAKMAR_INVENTARIO = (1345, 145)  # Ajustar según dónde aparezca en tu pantalla
COORD_POCIMA_BONTA_INVENTARIO = (1416, 229)    # Ajustar según dónde aparezca en tu pantalla

def validar_pocima_visualmente(coordenada, color_esperado="rojo"):
    """
    Toma una captura en la coordenada y analiza el color para confirmar
    que es la pócima correcta antes de clickear.
    """
    captura = tomar_captura("assets/debug_validar_pocima.png")
    imagen = cv2.imread(captura)
    
    x, y = coordenada
    # Tomar una muestra pequeña alrededor de la coordenada
    tamaño = 30
    x1 = max(0, x - tamaño//2)
    y1 = max(0, y - tamaño//2)
    x2 = x1 + tamaño
    y2 = y1 + tamaño
    
    region = imagen[y1:y2, x1:x2]
    
    # Calcular color promedio en la región
    promedio_bgr = cv2.mean(region)[:3]
    # Convertir BGR a HSV para mejor detección de color
    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    promedio_hsv = cv2.mean(hsv)[:3]
    
    guardar_log(f"[VALIDACION] Color BGR: {promedio_bgr}")
    guardar_log(f"[VALIDACION] Color HSV: {promedio_hsv}")
    
    # Rango de rojo en HSV: H entre 0-10 o 160-180
    # Rango de azul en HSV: H entre 100-130
    h = promedio_hsv[0]
    
    if color_esperado == "rojo":
        es_rojo = (h < 15) or (h > 160)
        if es_rojo:
            guardar_log("[VALIDACION] ✓ Color rojo detectado, parece ser pócima Brakmar")
            return True
        else:
            guardar_log(f"[VALIDACION] ✗ No es rojo (H={h}), no es la pócima Brakmar")
            return False
    else:  # azul
        es_azul = 100 < h < 130
        if es_azul:
            guardar_log("[VALIDACION] ✓ Color azul detectado, parece ser pócima Bonta")
            return True
        else:
            guardar_log(f"[VALIDACION] ✗ No es azul (H={h}), no es la pócima Bonta")
            return False

def clickear_pocima_segura(ciudad, usar_coordenadas=True, validar_color=True):
    """
    Clickea la pócima de forma segura:
    1. Primero intenta con coordenadas + validación de color
    2. Si falla, intenta template matching
    3. Si falla, reporta error
    """
    guardar_log(f"[POCIMA] Intentando usar pócima de {ciudad}")
    
    if ciudad == "brakmar":
        coord = COORD_POCIMA_BRAKMAR_INVENTARIO
        color = "rojo"
    else:
        coord = COORD_POCIMA_BONTA_INVENTARIO
        color = "azul"
    
    # Estrategia 1: Coordenadas + validación visual
    if usar_coordenadas:
        guardar_log(f"[POCIMA] Usando coordenadas: {coord}")
        
        if validar_color:
            guardar_log(f"[POCIMA] Validando color {color}...")
            if validar_pocima_visualmente(coord, color):
                guardar_log("[POCIMA] ✓ Validación visual exitosa, clickeando...")
                doble_tap(*coord)
                return True
            else:
                guardar_log("[POCIMA] ✗ Validación visual falló, el color no coincide")
        else:
            # Sin validación, click directo (peligroso)
            doble_tap(*coord)
            return True
    
    # Estrategia 2: Template matching (fallback)
    guardar_log("[POCIMA] Intentando template matching como fallback...")
    from src.core.navegador import _encontrar_y_clickear_template, TEMPLATE_POCIMA_BRAKMAR, TEMPLATE_POCIMA_BONTA
    
    if ciudad == "brakmar":
        resultado = _encontrar_y_clickear_template(TEMPLATE_POCIMA_BRAKMAR, timeout=3, max_intentos=1)
    else:
        resultado = _encontrar_y_clickear_template(TEMPLATE_POCIMA_BONTA, timeout=3, max_intentos=1)
    
    return resultado

def main():
    print("\n" + "="*60)
    print("PRUEBA SEGURA: PÓCIMA DE BRAKMAR")
    print("="*60)
    
    print("\n⚠ ATENCIÓN:")
    print("  - Este script USARÁ COORDENADAS para clickear la pócima")
    print("  - Validará el COLOR antes de clickear (evita clicks erróneos)")
    print("  - Debes tener el INVENTARIO ABIERTO")
    
    respuesta = input("\n¿Continuar? (s/n): ")
    if respuesta.lower() != 's':
        print("Prueba cancelada.")
        return
    
    # Primero, mostrar dónde va a clickear
    print(f"\n📍 Coordenada a clickear: {COORD_POCIMA_BRAKMAR_INVENTARIO}")
    print("   (Ajusta en el código si es necesario)")
    
    input("\nPresiona ENTER para continuar con el test...")
    
    # Validar visualmente antes de clickear
    print("\n🔍 Validando que sea la pócima correcta...")
    if validar_pocima_visualmente(COORD_POCIMA_BRAKMAR_INVENTARIO, "rojo"):
        print("✅ Color rojo detectado, parece correcto")
        
        print("\n💊 Click en pócima...")
        doble_tap(*COORD_POCIMA_BRAKMAR_INVENTARIO)
        
        print("\n⏳ Esperando teleport (5 segundos)...")
        time.sleep(5)
        
        print("\n📡 Verificando posición...")
        posicion = leer_posicion_actual()
        if posicion:
            zona = determinar_zona(posicion)
            print(f"📍 Posición: {posicion}")
            print(f"📍 Zona: {zona}")
            
            if zona == "centro_brakmar":
                print("\n🎉 ÉXITO COMPLETO: Llegaste al centro de Brakmar!")
            else:
                print(f"\n⚠ Llegaste a {zona}")
        else:
            print("⚠ No se pudo leer la posición")
    else:
        print("\n❌ La coordenada NO contiene la pócima roja de Brakmar")
        print("   Posibles soluciones:")
        print("   1. Ajusta COORD_POCIMA_BRAKMAR_INVENTARIO en el código")
        print("   2. Asegúrate de que el inventario está abierto")
        print("   3. La pócima puede estar en otro slot")

if __name__ == "__main__":
    main()
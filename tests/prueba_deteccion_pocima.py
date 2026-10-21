#!/usr/bin/env python3
"""
PRUEBA DE DETECCIÓN DE PÓCIMAS
===============================
Valida que el template matching encuentra las pócimas en el inventario.

REQUISITOS:
1. El personaje debe tener las pócimas en el inventario
2. El inventario debe estar abierto
3. Los templates deben existir en assets/templates/

USO:
    python tests/prueba_deteccion_pocima.py
"""

import sys
import os

# Añadir el directorio raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.navegador import _encontrar_y_clickear_template, TEMPLATE_POCIMA_BRAKMAR, TEMPLATE_POCIMA_BONTA
from src.utils.helpers import guardar_log

def main():
    print("\n" + "="*60)
    print("PRUEBA DE DETECCIÓN DE PÓCIMAS")
    print("="*60)
    
    # Verificar que los templates existen
    print("\n[1] Verificando archivos de template...")
    
    templates = {
        "Brakmar": TEMPLATE_POCIMA_BRAKMAR,
        "Bonta": TEMPLATE_POCIMA_BONTA
    }
    
    for nombre, ruta in templates.items():
        if os.path.exists(ruta):
            print(f"  ✓ Template {nombre}: {ruta}")
        else:
            print(f"  ✗ Template {nombre} NO existe: {ruta}")
    
    print("\n[2] Probando detección de pócimas (sin click)...")
    print("    IMPORTANTE: Abre el inventario en el juego antes de continuar")
    
    input("\nPresiona ENTER cuando el inventario esté abierto...")
    
    # Probar detección de pócima Brakmar
    print("\n🔍 Buscando pócima de Brakmar...")
    if _encontrar_y_clickear_template(TEMPLATE_POCIMA_BRAKMAR, timeout=3):
        print("  ✓ Pócima de Brakmar DETECTADA correctamente")
    else:
        print("  ✗ Pócima de Brakmar NO detectada")
        print("    Posibles causas:")
        print("    1. La pócima no está visible en el inventario")
        print("    2. El template no coincide exactamente (tamaño/color diferente)")
        print("    3. La ventana del juego no está enfocada")
    
    # Probar detección de pócima Bonta
    print("\n🔍 Buscando pócima de Bonta...")
    if _encontrar_y_clickear_template(TEMPLATE_POCIMA_BONTA, timeout=3):
        print("  ✓ Pócima de Bonta DETECTADA correctamente")
    else:
        print("  ✗ Pócima de Bonta NO detectada")
    
    print("\n" + "="*60)
    print("Prueba completada")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
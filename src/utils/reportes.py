"""
REPORTES — Generador de archivos TXT por personaje
====================================================
Genera un archivo TXT por cada personaje por cada iteración del bot.

NOMBRE DEL ARCHIVO:
    logs/reportes/NombrePersonaje_2026-05-26_18-00.txt

CONTENIDO DEL REPORTE:
    - Encabezado con personaje, fecha y hora de inicio
    - Por cada cercado: nombre, mapa, lista de dragopavos colocados
    - Pie de página con duración total de la sesión

FUTURAS MEJORAS (puedes agregar cuando lo necesites):
    - Estadísticas por característica (cuántos de amor, resistencia, etc.)
    - Comparativa con sesión anterior
    - Alertas si algún cercado quedó vacío inesperadamente
"""

import os
from datetime import datetime

CARPETA_REPORTES = "logs/reportes"

class Reporte:
    def __init__(self, nombre_personaje: str):
        """
        Crea un nuevo reporte para el personaje indicado.
        El archivo se crea inmediatamente con el encabezado.
        """
        self.personaje = nombre_personaje
        self.inicio    = datetime.now()
        self.lineas    = []

        os.makedirs(CARPETA_REPORTES, exist_ok=True)
        fecha         = self.inicio.strftime("%Y-%m-%d_%H-%M")
        self.archivo  = f"{CARPETA_REPORTES}/{nombre_personaje}_{fecha}.txt"

        self._escribir_encabezado()

    def _escribir_encabezado(self):
        """Escribe la cabecera del reporte con datos del personaje y sesión."""
        self.lineas.append("=" * 52)
        self.lineas.append(f"  REPORTE DE DRAGOPAVOS")
        self.lineas.append(f"  Personaje : {self.personaje}")
        self.lineas.append(f"  Fecha     : {self.inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        self.lineas.append("=" * 52)
        self.lineas.append("")

    def registrar_cercado(self, nombre: str, mapa: str, dragopavos: list):
        """
        Registra el resultado de un cercado en el reporte.

        nombre:     nombre del cercado (ej: "Amor Brakmar")
        mapa:       coordenadas del mapa (ej: "-30,37")
        dragopavos: lista de strings con nombre y nivel
                    (ej: ["fxl Niv.15", "s Niv.8"])
        """
        self.lineas.append(f"▸ {nombre} (Mapa {mapa})")
        if dragopavos:
            for pavo in dragopavos:
                self.lineas.append(f"    - {pavo}")
            self.lineas.append(f"    Total: {len(dragopavos)}")
        else:
            self.lineas.append(f"    (Sin dragopavos colocados)")
        self.lineas.append("")

    def guardar(self):
        """
        Escribe el reporte completo en el archivo TXT.
        Agrega el resumen de duración al final.
        Se llama una sola vez al terminar todos los cercados del personaje.
        """
        duracion = (datetime.now() - self.inicio).seconds
        minutos  = duracion // 60
        segundos = duracion % 60

        self.lineas.append("-" * 52)
        self.lineas.append(f"  Duración: {minutos} min {segundos} seg")
        self.lineas.append("=" * 52)

        with open(self.archivo, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lineas))

        print(f"[REPORTE] Guardado: {self.archivo}")
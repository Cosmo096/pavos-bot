"""
CONFIGURACIÓN COMPARTIDA — dispositivos, perfiles y convención de ventanas
==========================================================================
Este archivo es la ÚNICA fuente de verdad para:
- Qué dispositivos existen (alias -> ID adb)
- Qué personajes (perfiles) existen y en qué dispositivo corren
- Cómo se nombran las ventanas de scrcpy
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

# ---------------------------------------------------------------
# DISPOSITIVOS: alias -> ID adb  (ver `adb devices`)
# ---------------------------------------------------------------
DISPOSITIVOS = {
    "Tablet": os.getenv("ADB_DEVICE_TABLET", "").strip(),
    "TabletPro": os.getenv("ADB_DEVICE_TABLET_PRO", "").strip(),
}
ALIAS_POR_ID = {
    device_id: alias
    for alias, device_id in DISPOSITIVOS.items()
    if device_id
}

# ---------------------------------------------------------------
# PREFIJO DE TÍTULO DE VENTANA según el tipo de script.
# El título final de la ventana es: PREFIJO[tipo] + nombre
#   p. ej. "ventana2Panda".  Debe coincidir con lo que hace cada script.
# ---------------------------------------------------------------
PREFIJO = {"bat": "ventana1", "ps1": "ventana2"}
SCRCPY_DISPLAY_SIZE = "2560x1440/320"
SCRCPY_WINDOW_SIZE = (1920, 1080)
SCRCPY_WINDOW_POSITION = (15, 15)

# ---------------------------------------------------------------
# PERFILES (personajes)
#   nombre:      nombre del personaje (el que usarás en el controlador)
#   dispositivo: ID adb del dispositivo donde corre
#   tipo:        "bat" -> ventana1 | "ps1" -> ventana2
#   activo:      valor inicial del checkbox del lanzador
#   maximizar:   si el lanzador maximiza la ventana al abrirse
# ---------------------------------------------------------------
perfiles = [
    {"id": "panda-secondary", "nombre": "Panda", "dispositivo_alias": "TabletPro", "tipo": "ps1", "activo": True, "maximizar": True},
    {"id": "zobal-primary", "nombre": "Zobal", "dispositivo_alias": "TabletPro", "tipo": "bat", "activo": True, "maximizar": True},
    {"id": "steamer-primary", "nombre": "Steamer", "dispositivo_alias": "Tablet", "tipo": "bat", "activo": True, "maximizar": True},
    {"id": "eni-secondary", "nombre": "Eni", "dispositivo_alias": "Tablet", "tipo": "ps1", "activo": True, "maximizar": True},
    {"id": "steamer-secondary", "nombre": "Steamer", "dispositivo_alias": "TabletPro", "tipo": "ps1", "activo": False, "maximizar": True},
    {"id": "eni-primary", "nombre": "Eni", "dispositivo_alias": "Tablet", "tipo": "bat", "activo": False, "maximizar": True},
    {"id": "ocra-secondary", "nombre": "Ocra", "dispositivo_alias": "Tablet", "tipo": "ps1", "activo": False, "maximizar": True},
]

for perfil in perfiles:
    perfil["dispositivo"] = DISPOSITIVOS[perfil["dispositivo_alias"]]
    perfil["ventana_titulo"] = f"{PREFIJO[perfil['tipo']]}{perfil['nombre']}"

# Perfiles disponibles en cada superficie; se mantienen los lanzamientos
# diferentes que ya existían sin duplicar sus dispositivos o títulos.
PERFILES_LOTE = (
    "steamer-secondary",
    "zobal-primary",
    "eni-primary",
    "ocra-secondary",
)
PERFILES_GUI = (
    "panda-secondary",
    "zobal-primary",
    "steamer-primary",
    "eni-secondary",
)

# ---------------------------------------------------------------
# LOG DONDE SE LEE EL DISPLAY ID
# tablets.bat y tablets.ps1 guardan el log de scrcpy de cada personaje en
#   <proyecto>\lanzador\logs\scrcpy_{alias}_{titulo}.log
# Marcadores disponibles:
#   {alias}  -> alias del dispositivo (Tablet, TabletPro...)
#   {titulo} -> título de la ventana (ventana1Panda, ventana2Eni...)
#   {nombre} -> nombre del personaje | {dispositivo} -> ID adb
# None = no se lee ningún log (entonces usa fijar_display() o REQUIERE_DISPLAY=False).
# ---------------------------------------------------------------
PLANTILLA_LOG = str(
    ROOT_DIR / "lanzador" / "logs" / "scrcpy_{alias}_{titulo}.log"
)

# Tus scripts lanzan cada personaje con --new-display (display virtual propio).
# True  = si no se puede determinar el display del personaje, se lanza ErrorVentana
#         (evita que un tap caiga en la pantalla principal de la tablet).
# False = en ese caso se usa el display por defecto.
REQUIERE_DISPLAY: bool = True


def validar_dispositivos_configurados() -> None:
    """Falla antes de lanzar si falta algún serial requerido en el entorno."""
    faltantes = [
        variable
        for alias, variable in (
            ("Tablet", "ADB_DEVICE_TABLET"),
            ("TabletPro", "ADB_DEVICE_TABLET_PRO"),
        )
        if not DISPOSITIVOS[alias]
    ]
    if faltantes:
        raise RuntimeError(
            "Faltan variables de dispositivo en el archivo .env: "
            + ", ".join(faltantes)
        )


def validar_dispositivo_configurado(alias: str) -> None:
    """Valida solo el dispositivo necesario para el perfil seleccionado."""
    variables = {
        "Tablet": "ADB_DEVICE_TABLET",
        "TabletPro": "ADB_DEVICE_TABLET_PRO",
    }
    if alias not in variables:
        raise ValueError(f"Alias de dispositivo desconocido: {alias}")
    if not DISPOSITIVOS[alias]:
        raise RuntimeError(
            f"Falta la variable {variables[alias]} en el archivo .env."
        )
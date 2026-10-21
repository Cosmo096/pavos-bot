from __future__ import annotations

import os
from pathlib import Path

from src.config.config_perfiles import (
    SCRCPY_DISPLAY_SIZE,
    SCRCPY_WINDOW_POSITION,
    SCRCPY_WINDOW_SIZE,
    validar_dispositivo_configurado,
)

LAUNCHER_DIR = Path(__file__).resolve().parent
SCRCPY_DIR = Path(os.getenv("SCRCPY_DIR", "")).expanduser()
BAT = LAUNCHER_DIR / "tablets.bat"
PS1 = LAUNCHER_DIR / "tablets.ps1"


def validar_ruta_scrcpy() -> None:
    if not SCRCPY_DIR.is_dir() or not (SCRCPY_DIR / "scrcpy.exe").is_file():
        raise RuntimeError(
            "SCRCPY_DIR debe apuntar a una carpeta local que contenga scrcpy.exe."
        )


def construir_comando(perfil: dict) -> list[str]:
    validar_dispositivo_configurado(perfil["dispositivo_alias"])
    if not perfil["dispositivo"]:
        raise RuntimeError(
            f"El perfil {perfil['id']} no tiene un dispositivo configurado."
        )

    args_geometria = [
        SCRCPY_DISPLAY_SIZE,
        str(SCRCPY_WINDOW_SIZE[0]),
        str(SCRCPY_WINDOW_SIZE[1]),
        str(SCRCPY_WINDOW_POSITION[0]),
        str(SCRCPY_WINDOW_POSITION[1]),
    ]
    device_id = perfil["dispositivo"]
    name = perfil["nombre"]
    title = perfil["ventana_titulo"]
    alias = perfil["dispositivo_alias"]

    if perfil["tipo"] == "bat":
        return [
            "cmd", "/c", str(BAT), device_id, name, alias, title, *args_geometria
        ]
    if perfil["tipo"] == "ps1":
        return [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(PS1),
            "-Device", device_id,
            "-Name", name,
            "-DeviceName", alias,
            "-Title", title,
            "-DisplaySize", args_geometria[0],
            "-WindowWidth", args_geometria[1],
            "-WindowHeight", args_geometria[2],
            "-WindowX", args_geometria[3],
            "-WindowY", args_geometria[4],
        ]
    raise ValueError(f"Tipo desconocido: {perfil['tipo']}")

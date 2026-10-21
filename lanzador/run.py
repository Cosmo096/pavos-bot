import subprocess
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.config_perfiles import (
    PERFILES_LOTE,
    perfiles,
)
from lanzador.comandos import SCRCPY_DIR, construir_comando, validar_ruta_scrcpy

PAUSA_ENTRE_PERFILES = 10


procesos = []
perfiles_por_id = {perfil["id"]: perfil for perfil in perfiles}
seleccionados = [perfiles_por_id[profile_id] for profile_id in PERFILES_LOTE]
validar_ruta_scrcpy()

for i, perfil in enumerate(seleccionados):
    p = subprocess.Popen(
        [str(arg) for arg in construir_comando(perfil)],
        cwd=SCRCPY_DIR,  # el cwd sigue siendo donde vive scrcpy.exe
        creationflags=subprocess.CREATE_NO_WINDOW,  # sin ventana de consola
    )
    procesos.append(p)
    print(f"{perfil['nombre']} lanzado ({perfil['ventana_titulo']}, PID {p.pid})")

    # Pausa entre perfiles, pero no después del último
    if i < len(seleccionados) - 1:
        time.sleep(PAUSA_ENTRE_PERFILES)

print(f"{len(procesos)} perfil(es) solicitados.")
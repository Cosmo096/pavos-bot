import ctypes
import json
import subprocess
import threading
import time
import tkinter as tk
import sys
from ctypes import wintypes
from pathlib import Path
from tkinter import ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.config_perfiles import (
    PERFILES_GUI,
    perfiles,
)
from lanzador.comandos import (
    SCRCPY_DIR,
    construir_comando,
    validar_ruta_scrcpy,
)
from lanzador.seleccion import migrar_seleccion

PAUSA_ENTRE_PERFILES = 10
LAUNCHER_DIR = Path(__file__).resolve().parent
perfiles_gui = [
    perfil for perfil in perfiles if perfil["id"] in PERFILES_GUI
]
SELECCION_JSON = LAUNCHER_DIR / "seleccion.json"


def titulo_ventana(perfil: dict[str, object]) -> str:
    """Título que scrcpy le pone a la ventana (prefijo según tipo + nombre)."""
    return str(perfil["ventana_titulo"])


# ---------------------------------------------------------------
# MAXIMIZAR (API de Windows)
# ---------------------------------------------------------------
user32 = ctypes.windll.user32
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
SW_MAXIMIZE = 3


def maximizar_ventana(titulo: str, timeout: int = 45) -> bool:
    """Espera a que exista una ventana con ese título exacto y la maximiza."""
    limite = time.time() + timeout
    while time.time() < limite:
        hwnd = user32.FindWindowW(None, titulo)  # busca por título exacto
        if hwnd:
            time.sleep(1)                        # margen para que scrcpy termine de inicializar
            user32.ShowWindow(hwnd, SW_MAXIMIZE)
            return True
        time.sleep(0.5)
    return False


# ---------------------------------------------------------------
# VENTANA (Tkinter)
# ---------------------------------------------------------------
class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Lanzador scrcpy")
        self.vars = {}  # nombre-perfil -> BooleanVar

        guardado = self.cargar_seleccion()

        marco = ttk.Frame(root, padding=10)
        marco.grid(sticky="nsew")

        # Un checkbox por cada perfil de la lista
        for i, perfil in enumerate(perfiles_gui):
            clave = str(perfil["id"])
            var = tk.BooleanVar(value=guardado.get(clave, perfil.get("activo", False)))
            self.vars[clave] = var
            alias = perfil["dispositivo_alias"]
            texto = f"{perfil['nombre']}  ·  {alias}  ·  {titulo_ventana(perfil)}"
            ttk.Checkbutton(marco, text=texto, variable=var).grid(row=i, column=0, sticky="w", pady=2)

        fila = len(perfiles_gui)
        botones = ttk.Frame(marco)
        botones.grid(row=fila, column=0, pady=(10, 0), sticky="w")
        ttk.Button(botones, text="Todos", command=lambda: self.marcar(True)).pack(side="left")
        ttk.Button(botones, text="Ninguno", command=lambda: self.marcar(False)).pack(side="left", padx=5)
        self.btn_lanzar = ttk.Button(botones, text="Lanzar seleccionados", command=self.lanzar)
        self.btn_lanzar.pack(side="left", padx=5)

        # Área de mensajes
        self.log_box = tk.Text(marco, height=8, width=60, state="disabled")
        self.log_box.grid(row=fila + 1, column=0, pady=(10, 0))

    def marcar(self, valor: bool):
        for v in self.vars.values():
            v.set(valor)

    def log(self, msg: str):
        """Escribe en el cuadro de texto (seguro para llamarse desde el hilo)."""
        def _escribir():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.root.after(0, _escribir)

    # --- persistencia de la selección ---
    def cargar_seleccion(self) -> dict:
        try:
            with open(SELECCION_JSON, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return {}
        return migrar_seleccion(data, perfiles_gui)

    def guardar_seleccion(self):
        with open(SELECCION_JSON, "w", encoding="utf-8") as f:
            json.dump({k: v.get() for k, v in self.vars.items()}, f, indent=2)

    # --- lanzamiento ---
    def lanzar(self):
        elegidos = [
            perfil
            for perfil in perfiles_gui
            if self.vars[perfil["id"]].get()
        ]
        if not elegidos:
            self.log("No hay perfiles seleccionados.")
            return
        self.guardar_seleccion()
        self.btn_lanzar.configure(state="disabled")
        # Hilo aparte: los sleep no congelan la ventana
        threading.Thread(target=self.lanzar_en_hilo, args=(elegidos,), daemon=True).start()

    def lanzar_en_hilo(self, elegidos: list):
        try:
            validar_ruta_scrcpy()
            for i, perfil in enumerate(elegidos):
                titulo = titulo_ventana(perfil)
                p = subprocess.Popen(
                    construir_comando(perfil),
                    cwd=SCRCPY_DIR,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                self.log(f"{titulo} lanzado (PID {p.pid})")

                if perfil.get("maximizar"):
                    threading.Thread(
                        target=self.maximizar_y_avisar,
                        args=(titulo,),
                        daemon=True,
                    ).start()

                if i < len(elegidos) - 1:
                    time.sleep(PAUSA_ENTRE_PERFILES)

            self.log(f"{len(elegidos)} perfil(es) lanzados.")
        except (OSError, RuntimeError, ValueError) as error:
            self.log(f"Error al lanzar perfiles: {error}")
        finally:
            self.root.after(0, lambda: self.btn_lanzar.configure(state="normal"))

    def maximizar_y_avisar(self, titulo: str):
        ok = maximizar_ventana(titulo)
        self.log(f"{titulo} maximizada" if ok else f"{titulo}: no se encontró la ventana para maximizar")


if __name__ == "__main__":
    raiz = tk.Tk()
    App(raiz)
    raiz.mainloop()
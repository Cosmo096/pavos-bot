"""
CONTROLADOR ADB — El mensajero con los dispositivos (scrcpy)
============================================================
Este módulo es el ÚNICO que habla directamente con ADB.
Ningún otro módulo debe ejecutar comandos ADB directamente.

IDEA CENTRAL
------------
Cada personaje tiene una ventana de scrcpy (p. ej. "ventana2Panda") y vive en
un dispositivo concreto. Todos los métodos aceptan `personaje=None` (último
parámetro). El controlador:

  1. Resuelve la VENTANA de ese personaje (debe estar abierta).
  2. De ahí saca el dispositivo (serial) y, si se puede, el display_id.
  3. Ejecuta el comando SOLO sobre ese dispositivo/display.

¿Qué ventana se usa cuando NO se indica personaje?
  a) El fijado con usar_personaje("Panda"), si existe.
  b) Si no, la única ventana scrcpy abierta.
  c) Si hay varias abiertas, la que esté en primer plano.
  d) Si ninguna está en primer plano -> ErrorVentana (no se adivina).

REGLA DE ERRORES
----------------
- Problemas al RESOLVER la ventana (cerrada, ambigua, no existe) -> ErrorVentana.
- No se puede determinar el display del personaje (con REQUIERE_DISPLAY=True) -> ErrorVentana.
- Problemas al EJECUTAR el comando adb (fallo, timeout)        -> retorna False.

REQUISITOS: Windows, `adb` en el PATH, y config_perfiles.py junto a este archivo.
Las coordenadas (x, y) son del DISPOSITIVO (o del display), no de la ventana de Windows.
"""

from __future__ import annotations

import ctypes
import re
import subprocess
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

from src.config.config_perfiles import (
    ALIAS_POR_ID,
    PLANTILLA_LOG,
    PREFIJO,
    REQUIERE_DISPLAY,
    validar_dispositivo_configurado,
)
from src.config.config_perfiles import perfiles as PERFILES_CONFIG

if not hasattr(ctypes, "WinDLL"):
    raise ImportError("controlador_adb requiere Windows (usa la API de ventanas de user32).")

# ---------------------------------------------------------------
# CONSTANTES AJUSTABLES
# ---------------------------------------------------------------
ADB = "adb"                       # o la ruta completa a adb.exe
TIMEOUT_DEFECTO_S = 15.0          # tiempo máximo por comando adb
KEYCODE_BACK = 4                  # "Atrás". (ESC real sería 111)
PATRON_DISPLAY = re.compile(r"New display:.*\(id=(\d+)\)")  # mismo patrón que usa tablets.ps1

# Instancia PROPIA de user32: no tocamos la que usa el lanzador (evita efectos cruzados).
_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
_user32.FindWindowW.restype = wintypes.HWND
_user32.GetForegroundWindow.argtypes = []
_user32.GetForegroundWindow.restype = wintypes.HWND


# ---------------------------------------------------------------
# TIPOS
# ---------------------------------------------------------------
class ErrorVentana(RuntimeError):
    """No se pudo determinar de forma segura qué ventana/personaje usar."""


@dataclass(frozen=True)
class ContextoVentana:
    """Todo lo necesario para enviar comandos a UN personaje."""
    nombre: str               # "Panda"
    titulo: str               # "ventana2Panda"
    hwnd: int                 # identificador de la ventana en Windows
    serial: str               # ID adb del dispositivo
    display_id: int | None    # display virtual (None = display por defecto)


def listar_dispositivos(adb: str = ADB) -> dict[str, str]:
    """Retorna {serial: estado} según `adb devices` (device, offline, unauthorized...)."""
    r = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=10)
    dispositivos: dict[str, str] = {}
    for linea in r.stdout.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith(("List of", "*")):
            continue
        partes = linea.split()
        if len(partes) >= 2:
            dispositivos[partes[0]] = partes[1]
    return dispositivos


# ---------------------------------------------------------------
# CONTROLADOR
# ---------------------------------------------------------------
class ControladorADB:
    def __init__(
        self,
        perfiles: list[dict] | None = None,
        adb: str = ADB,
        timeout_s: float = TIMEOUT_DEFECTO_S,
    ) -> None:
        self.perfiles = list(perfiles if perfiles is not None else PERFILES_CONFIG)
        self.adb = adb
        self.timeout_s = timeout_s
        self._personaje_actual: str | None = None      # fijado con usar_personaje()
        self._display_fijo: dict[str, int] = {}        # overrides manuales por nombre
        self._cache_display: dict[int, int] = {}       # hwnd -> display_id leído del log

    # ==============================================================
    # 1) SELECCIÓN DE PERSONAJE / VENTANA
    # ==============================================================
    @staticmethod
    def _titulo(perfil: dict) -> str:
        """Título de ventana = prefijo según tipo + nombre (igual que el lanzador)."""
        return f"{PREFIJO[perfil['tipo']]}{perfil['nombre']}"

    def _coincide(self, perfil: dict, clave: str) -> bool:
        """¿El texto (en minúsculas) corresponde al nombre o al título completo del perfil?"""
        return clave in (perfil["nombre"].casefold(), self._titulo(perfil).casefold())

    def _abiertas(self) -> list[tuple[dict, str, int]]:
        """Perfiles cuya ventana scrcpy existe ahora mismo: [(perfil, titulo, hwnd)]."""
        abiertas = []
        for perfil in self.perfiles:
            titulo = self._titulo(perfil)
            hwnd = _user32.FindWindowW(None, titulo)  # búsqueda por título exacto
            if hwnd:
                abiertas.append((perfil, titulo, int(hwnd)))
        return abiertas

    def ventanas_abiertas(self) -> list[str]:
        """Títulos de las ventanas scrcpy abiertas (útil para depurar)."""
        return [titulo for _, titulo, _ in self._abiertas()]

    def usar_personaje(self, personaje: str | None) -> None:
        """
        Fija el personaje por defecto para las llamadas SIN `personaje`.
        None = volver al modo automático (ventana única / en primer plano).
        Ojo: es estado compartido; con varios hilos pasa `personaje` explícito.
        """
        if personaje is not None and not any(
            self._coincide(p, personaje.casefold()) for p in self.perfiles
        ):
            raise ErrorVentana(f"'{personaje}' no existe en perfiles.")
        self._personaje_actual = personaje

    def fijar_display(self, personaje: str, display_id: int | None) -> None:
        """Fuerza manualmente el display_id de un personaje (None = quitar el override)."""
        clave = personaje.casefold()
        if display_id is None:
            self._display_fijo.pop(clave, None)
        else:
            self._display_fijo[clave] = display_id

    def resolver(self, personaje: str | None = None) -> ContextoVentana:
        """Determina la ventana/dispositivo a usar según las reglas del encabezado."""
        objetivo = personaje if personaje is not None else self._personaje_actual
        abiertas = self._abiertas()
        lista_abiertas = ", ".join(t for _, t, _ in abiertas) or "ninguna"

        if objetivo is not None:
            clave = objetivo.casefold()
            if not any(self._coincide(p, clave) for p in self.perfiles):
                nombres = ", ".join(p["nombre"] for p in self.perfiles)
                raise ErrorVentana(f"'{objetivo}' no existe en perfiles. Disponibles: {nombres}")
            candidatas = [c for c in abiertas if self._coincide(c[0], clave)]
            if not candidatas:
                raise ErrorVentana(
                    f"La ventana de '{objetivo}' no está abierta. Abiertas: {lista_abiertas}"
                )
            if len(candidatas) > 1:
                raise ErrorVentana(
                    f"'{objetivo}' coincide con varias ventanas ({lista_abiertas}). "
                    "Usa el título completo (p. ej. 'ventana2Panda')."
                )
            elegida = candidatas[0]
        else:
            if not abiertas:
                raise ErrorVentana("No hay ninguna ventana scrcpy abierta.")
            if len(abiertas) == 1:
                elegida = abiertas[0]
            else:
                activa = _user32.GetForegroundWindow()
                elegida = next((c for c in abiertas if c[2] == activa), None)
                if elegida is None:
                    raise ErrorVentana(
                        f"Hay varias ventanas abiertas ({lista_abiertas}) y ninguna en "
                        "primer plano. Indica `personaje` o usa usar_personaje()."
                    )

        perfil, titulo, hwnd = elegida
        if not perfil["dispositivo"]:
            validar_dispositivo_configurado(perfil["dispositivo_alias"])
        display = self._display_de(perfil, hwnd)
        if display is None and REQUIERE_DISPLAY:
            # Tus scripts usan --new-display: sin display, el tap iría a la pantalla
            # principal de la tablet y no al juego. Mejor fallar que tocar donde no es.
            raise ErrorVentana(
                f"No se pudo determinar el display de '{perfil['nombre']}'. "
                f"Log revisado: {self._ruta_log(perfil) or 'PLANTILLA_LOG no configurado'}. "
                "Revisa el log, usa fijar_display() o pon REQUIERE_DISPLAY = False."
            )
        return ContextoVentana(
            nombre=perfil["nombre"],
            titulo=titulo,
            hwnd=hwnd,
            serial=perfil["dispositivo"],
            display_id=display,
        )

    # ==============================================================
    # 2) DISPLAY ID (opcional)
    # ==============================================================
    def _display_de(self, perfil: dict, hwnd: int) -> int | None:
        """Override manual > caché > log. None si no se puede determinar."""
        manual = self._display_fijo.get(perfil["nombre"].casefold())
        if manual is not None:
            return manual
        if hwnd in self._cache_display:      # misma ventana = misma sesión de scrcpy
            return self._cache_display[hwnd]
        display = self._leer_display_de_log(perfil)
        if display is not None:              # solo se cachea si se encontró
            self._cache_display[hwnd] = display
        return display

    @staticmethod
    def _ruta_log(perfil: dict) -> Path | None:
        """Ruta del log de scrcpy del personaje según PLANTILLA_LOG (None si no está)."""
        if not PLANTILLA_LOG:
            return None
        return Path(PLANTILLA_LOG.format(
            nombre=perfil["nombre"],
            titulo=ControladorADB._titulo(perfil),
            alias=ALIAS_POR_ID.get(perfil["dispositivo"], perfil["dispositivo"]),
            dispositivo=perfil["dispositivo"],
        ))

    @staticmethod
    def _leer_display_de_log(perfil: dict) -> int | None:
        """
        Último 'New display: ... (id=N)' del log del personaje.
        tablets.ps1 separa stdout (.log) y stderr (_err.log); tablets.bat los mezcla
        en el .log. Se leen ambos y se toma la ÚLTIMA coincidencia.
        """
        ruta = ControladorADB._ruta_log(perfil)
        if ruta is None:
            return None
        texto = ""
        for archivo in (ruta, ruta.with_name(f"{ruta.stem}_err{ruta.suffix}")):
            try:
                datos = archivo.read_bytes()
            except OSError:
                continue  # el archivo puede no existir todavía
            # PowerShell suele guardar en UTF-16 (con BOM); si no, asumimos UTF-8.
            cod = "utf-16" if datos[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8"
            texto += datos.decode(cod, errors="replace") + "\n"
        coincidencias = PATRON_DISPLAY.findall(texto)
        return int(coincidencias[-1]) if coincidencias else None

    # ==============================================================
    # 3) EJECUCIÓN ADB (internos)
    # ==============================================================
    def _run(
        self, ctx: ContextoVentana, args: list[str], timeout_s: float | None = None
    ) -> subprocess.CompletedProcess[bytes] | None:
        """Ejecuta `adb -s <serial> ...`. None si hubo timeout o adb no existe."""
        cmd = [self.adb, "-s", ctx.serial, *args]
        try:
            return subprocess.run(
                cmd, capture_output=True, timeout=timeout_s or self.timeout_s
            )
        except subprocess.TimeoutExpired:
            print(f"[ADB][{ctx.nombre}] Timeout: {' '.join(args)}")
        except FileNotFoundError:
            print(f"[ADB] No se encontró '{self.adb}'. ¿Está en el PATH?")
        return None

    def _ok(self, ctx: ContextoVentana, args: list[str], timeout_s: float | None = None) -> bool:
        r = self._run(ctx, args, timeout_s)
        if r is None:
            return False
        if r.returncode != 0:
            err = (r.stderr or r.stdout).decode(errors="replace").strip()
            print(f"[ADB][{ctx.nombre}] Error ({r.returncode}): {err}")
            return False
        return True

    @staticmethod
    def _input_args(ctx: ContextoVentana, *args: str) -> list[str]:
        """Arma `input [-d display] <args>`; el -d solo se agrega si hay display_id."""
        base = ["input"]
        if ctx.display_id is not None:
            base += ["-d", str(ctx.display_id)]
        return [*base, *args]

    # ==============================================================
    # 4) API PÚBLICA — todos con `personaje` opcional al final
    # ==============================================================
    def verificar_conexion(self, personaje: str | None = None) -> bool:
        """
        True si el dispositivo del personaje aparece en `adb devices` como 'device'.
        Con personaje explícito (o fijado) NO exige la ventana abierta: sirve para
        comprobar antes de lanzar. Sin personaje, usa la ventana abierta.
        """
        objetivo = personaje if personaje is not None else self._personaje_actual
        if objetivo is not None:
            clave = objetivo.casefold()
            perfiles = [p for p in self.perfiles if self._coincide(p, clave)]
            if len(perfiles) != 1:
                raise ErrorVentana(f"'{objetivo}' no identifica un único perfil.")
            perfil = perfiles[0]
            if not perfil["dispositivo"]:
                validar_dispositivo_configurado(perfil["dispositivo_alias"])
            serial = perfil["dispositivo"]
            nombre = perfil["nombre"]
        else:
            contexto = self.resolver(None)
            serial = contexto.serial
            nombre = contexto.nombre
        estado = listar_dispositivos(self.adb).get(serial)
        print(f"[ADB][{nombre}] {estado or 'no encontrado'}")
        return estado == "device"

    def consultar_propiedades_display(
        self, personaje: str
    ) -> dict[str, tuple[bool, str]]:
        """Consulta resolución y densidad sin modificar el dispositivo."""
        ctx = self.resolver(personaje)
        if ctx.display_id is None:
            raise ErrorVentana(
                f"No se puede inspeccionar el display de '{ctx.nombre}' sin display_id."
            )

        consultas = {
            "wm size": ["shell", "wm", "size", "-d", str(ctx.display_id)],
            "wm density": ["shell", "wm", "density", "-d", str(ctx.display_id)],
        }
        resultados = {}
        for nombre, args in consultas.items():
            respuesta = self._run(ctx, args)
            if respuesta is None:
                resultados[nombre] = (False, "ADB no respondió.")
            elif respuesta.returncode != 0:
                detalle = (respuesta.stderr or respuesta.stdout).decode(
                    errors="replace"
                ).strip()
                resultados[nombre] = (False, detalle or "Comando no disponible.")
            else:
                resultados[nombre] = (
                    True,
                    respuesta.stdout.decode(errors="replace").strip(),
                )
        return resultados

    def tap(self, x: int, y: int, personaje: str | None = None) -> bool:
        """Toca la pantalla en (x, y)."""
        ctx = self.resolver(personaje)
        return self._ok(ctx, ["shell", *self._input_args(ctx, "tap", str(int(x)), str(int(y)))])

    def tap_sostenido(
        self, x: int, y: int, duracion_ms: int = 2000, personaje: str | None = None
    ) -> bool:
        """Mantiene el toque en (x, y) durante duracion_ms (un swipe sin movimiento)."""
        ctx = self.resolver(personaje)
        args = self._input_args(
            ctx, "swipe", str(int(x)), str(int(y)), str(int(x)), str(int(y)), str(duracion_ms)
        )
        # El timeout se alarga para no cortar el gesto antes de que termine.
        return self._ok(ctx, ["shell", *args], timeout_s=self.timeout_s + duracion_ms / 1000)

    def doble_tap(self, x: int, y: int, pausa_ms: int = 100, personaje: str | None = None) -> bool:
        """Doble tap en UNA sola llamada de shell; la pausa se mide en el dispositivo."""
        ctx = self.resolver(personaje)
        tap = " ".join(self._input_args(ctx, "tap", str(int(x)), str(int(y))))
        return self._ok(ctx, ["shell", f"{tap}; sleep {pausa_ms / 1000}; {tap}"])

    def swipe(
        self, x1: int, y1: int, x2: int, y2: int, duracion_ms: int = 800,
        personaje: str | None = None,
    ) -> bool:
        """Deslizar de (x1, y1) a (x2, y2): drag & drop, navegación en mapas."""
        ctx = self.resolver(personaje)
        args = self._input_args(
            ctx, "swipe", str(int(x1)), str(int(y1)), str(int(x2)), str(int(y2)), str(duracion_ms)
        )
        return self._ok(ctx, ["shell", *args], timeout_s=self.timeout_s + duracion_ms / 1000)

    def presionar_tecla(self, keycode: int, personaje: str | None = None) -> bool:
        """Presiona una tecla Android por su keycode numérico."""
        ctx = self.resolver(personaje)
        return self._ok(ctx, ["shell", *self._input_args(ctx, "keyevent", str(keycode))])

    def presionar_esc(self, personaje: str | None = None) -> bool:
        """Keycode 4 (KEYCODE_BACK), igual que el módulo original."""
        return self.presionar_tecla(KEYCODE_BACK, personaje)

    def tomar_captura(
        self,
        ruta_local: str = "assets/captura.png",
        personaje: str | None = None,
        display_captura: str | None = None,
    ) -> str | None:
        """
        Screenshot del dispositivo del personaje, guardado en ruta_local.
        Retorna la ruta, o None si falla.

        - Si capturas varios personajes, pasa una ruta distinta por cada uno
          (el valor por defecto se sobrescribe).
        - display_captura: ID para `screencap -d`.
            None   = display principal de la tablet (NO es el juego: corre en un
                     display virtual).
            "auto" = usa el display_id del personaje. SIN VERIFICAR: no sé si
                     `screencap -d` acepta los displays virtuales de scrcpy; pruébalo.
        """
        ctx = self.resolver(personaje)
        args = ["exec-out", "screencap", "-p"]
        if display_captura == "auto":
            display_captura = None if ctx.display_id is None else str(ctx.display_id)
        if display_captura is not None:
            args += ["-d", display_captura]

        r = self._run(ctx, args)
        if r is None or r.returncode != 0 or not r.stdout.startswith(b"\x89PNG"):
            detalle = r.stderr.decode(errors="replace").strip() if r else "sin respuesta"
            print(f"[ADB][{ctx.nombre}] Captura fallida: {detalle}")
            return None

        ruta = Path(ruta_local)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(r.stdout)
        return str(ruta)


# ===================================================================
# INTERFAZ DE MÓDULO (compatibilidad con el estilo original)
# ===================================================================
# Permite `import controlador_adb as adb; adb.tap(100, 200, "Panda")`
# usando una instancia compartida, igual que el módulo original.
_ctrl = ControladorADB()

usar_personaje = _ctrl.usar_personaje
fijar_display = _ctrl.fijar_display
ventanas_abiertas = _ctrl.ventanas_abiertas
resolver = _ctrl.resolver
verificar_conexion = _ctrl.verificar_conexion
conectar = verificar_conexion      # nombre del módulo original
tap = _ctrl.tap
tap_sostenido = _ctrl.tap_sostenido
doble_tap = _ctrl.doble_tap
swipe = _ctrl.swipe
presionar_tecla = _ctrl.presionar_tecla
presionar_esc = _ctrl.presionar_esc
tomar_captura = _ctrl.tomar_captura
"""
CEREBRO DEL BOT — Orquestador principal
========================================
Coordina todos los módulos para ejecutar el ciclo completo
de revisión de cercados para cada personaje.

FLUJO COMPLETO:
    Para cada personaje:
        1. Cambiar al personaje
        2. Crear archivo de reporte
        3. Para cada ciudad (brakmar, bonta):
            a. Teleportar al mercadillo de animales
            b. Para cada cercado en orden:
                i.   Navegar al mapa del cercado
                ii.  Detectar y abrir la puerta
                iii. Vaciar el cercado (mover todo al establo)
                iv.  Aplicar filtros según tipo y ciudad
                v.   Seleccionar todos y arrastrar al cercado
                vi.  Registrar en el reporte
        4. Guardar el reporte del personaje
        5. Guardar estado (progreso en disco)
"""

from src.core.adb_controller import conectar, tomar_captura, tap
from src.core.gestor_personajes import PERSONAJES, cambiar_personaje
from src.core.navegador import ir_a_ciudad, ir_a_mapa
from src.modules.gestor_filtros import (
    aplicar_filtros, reiniciar_filtros,
    seleccionar_todos, arrastrar_a_cercado, arrastrar_a_establo,
    validar_filtros_configurados,
)
from src.modules.detector_cercado import (
    detectar_puerta, ventana_vacia, COORD_CERRAR_VENTANA,
    COORD_PANEL_CERCADO, COORD_PANEL_ESTABLO
)
from src.modules.lector_dragopavos import leer_dragopavos_visibles, leer_contador_filtro
from src.config.cercados import CIUDADES
from src.config.filtros import FILTROS_POR_CERCADO
from src.utils.reportes import Reporte
from src.utils.estado import guardar_estado, limpiar_estado
from src.utils.helpers import guardar_log, esperar

# Solo se habilita cuando el flujo visual por tarjeta y la validación en
# dispositivo estén integrados y aceptados.
AUTOMATIZACION_REAL_LISTA = False

class DragoPavoBot:
    def __init__(self):
        self.activo = False

    def iniciar(self):
        if not AUTOMATIZACION_REAL_LISTA:
            raise RuntimeError(
                "La automatización real está bloqueada: falta integrar y validar "
                "la revalidación visual individual antes de mover dragopavos."
            )
        self._validar_configuracion_filtros()
        print("[BOT] Iniciando DragoPavo Bot...")
        if not conectar():
            print("[BOT] No se pudo conectar al emulador.")
            return
        self.activo = True
        self._ciclo_principal()

    @staticmethod
    def _validar_configuracion_filtros():
        for config_ciudad in CIUDADES.values():
            for cercado in config_ciudad["cercados"]:
                filtros = FILTROS_POR_CERCADO.get(cercado["id"])
                if filtros is None:
                    raise RuntimeError(
                        f"No hay filtros configurados para {cercado['id']}."
                    )
                filtros_con_sexo = list(filtros)
                if cercado["solo_sexo"] == "hembra":
                    filtros_con_sexo.append("Hembra")
                elif cercado["solo_sexo"] == "macho":
                    filtros_con_sexo.append("Macho")
                validar_filtros_configurados(filtros_con_sexo)

    def _ciclo_principal(self):
        for nombre_personaje in PERSONAJES:
            if not self.activo:
                break

            guardar_log(f"[BOT] ══════════════════════════════")
            guardar_log(f"[BOT] Personaje: {nombre_personaje}")
            guardar_log(f"[BOT] ══════════════════════════════")

            cambiar_personaje(nombre_personaje)
            esperar(3)

            reporte = Reporte(nombre_personaje)

            for ciudad, config in CIUDADES.items():
                if not config["cercados"]:
                    continue

                guardar_log(f"[BOT] Ciudad: {ciudad.upper()}")
                ir_a_ciudad(ciudad)
                esperar(2)

                self._procesar_cercados(
                    cercados=config["cercados"],
                    ciudad=ciudad,
                    reporte=reporte
                )

            reporte.guardar()
            limpiar_estado()
            guardar_log(f"[BOT] Fin personaje: {nombre_personaje}\n")

        print("[BOT] Todos los personajes procesados.")

    def _procesar_cercados(self, cercados: list, ciudad: str, reporte: Reporte):
        for i, cercado in enumerate(cercados):
            if not self.activo:
                break

            guardar_log(f"[BOT] → {cercado['nombre']} en {cercado['mapa']}")
            guardar_estado(reporte.personaje, ciudad, i)

            # Navegar al mapa del cercado
            ir_a_mapa(cercado["mapa"])
            esperar(1)

            # Detectar y abrir la puerta del cercado
            captura = tomar_captura()
            puerta  = detectar_puerta(captura)
            if not puerta:
                guardar_log(f"[BOT] Puerta no encontrada en {cercado['nombre']}")
                reporte.registrar_cercado(cercado["nombre"], cercado["mapa"], [])
                continue

            tap(*puerta)
            esperar(1.5)

            # Vaciar el cercado: mover dragopavos existentes al establo
            self._vaciar_cercado()

            # Armar la lista de filtros para este cercado
            # Los filtros base vienen de filtros.py según el tipo
            # El sexo se agrega automáticamente según la ciudad
            filtros = list(FILTROS_POR_CERCADO[cercado["id"]])

            if cercado["solo_sexo"] == "hembra":
                filtros.append("Hembra")
            elif cercado["solo_sexo"] == "macho":
                filtros.append("Macho")

            # Aplicar filtros y revisar si hay dragopavos que aplican
            reiniciar_filtros()
            if filtros:
                aplicar_filtros(filtros)
            esperar(1)

            captura  = tomar_captura()
            filtrados, _ = leer_contador_filtro(captura)

            if filtrados == 0 or ventana_vacia(captura):
                guardar_log(f"[BOT] Sin dragopavos para {cercado['nombre']}")
                reporte.registrar_cercado(cercado["nombre"], cercado["mapa"], [])
            else:
                # Seleccionar todos y mover al cercado
                seleccionar_todos()
                esperar(0.5)
                arrastrar_a_cercado()
                esperar(1.5)

                # Leer qué quedó en el cercado para el reporte
                captura     = tomar_captura()
                dragopavos  = leer_dragopavos_visibles(captura)
                reporte.registrar_cercado(cercado["nombre"], cercado["mapa"], dragopavos)
                guardar_log(f"[BOT] {len(dragopavos)} dragopavos colocados")

            # Cerrar la ventana del cercado
            tap(*COORD_CERRAR_VENTANA)
            esperar(1)

    def _vaciar_cercado(self):
        """
        Mueve todos los dragopavos que están en el cercado de vuelta al establo.
        Se ejecuta siempre antes de colocar dragopavos nuevos.

        Flujo:
            1. Ir al tab "Cercado" del panel derecho
            2. Si hay dragopavos, seleccionar todos y arrastrar al establo
            3. Volver al tab "Establo" para ver los disponibles
        """
        # Click en el tab Cercado para ver qué hay dentro
        tap(*COORD_PANEL_CERCADO)
        esperar(0.5)

        captura = tomar_captura()
        if not ventana_vacia(captura):
            seleccionar_todos()
            esperar(0.3)
            arrastrar_a_establo()
            esperar(1)
            guardar_log("[BOT] Cercado vaciado → dragopavos movidos al establo")

        # Volver al tab Establo para ver los disponibles
        tap(*COORD_PANEL_ESTABLO)
        esperar(0.5)

    def detener(self):
        self.activo = False
        print("[BOT] Bot detenido.")
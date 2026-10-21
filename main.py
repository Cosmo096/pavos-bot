"""
PUNTO DE ENTRADA
=================
La ejecución real permanece bloqueada hasta completar y validar las fases
visuales. Ejecuta el diagnóstico de scrcpy por separado cuando corresponda.
"""

from src.core.bot import DragoPavoBot

if __name__ == "__main__":
    bot = DragoPavoBot()
    try:
        bot.iniciar()
    except KeyboardInterrupt:
        print("\n[MAIN] Deteniendo bot...")
        bot.detener()
    except RuntimeError as error:
        raise SystemExit(f"[MAIN] {error}") from error
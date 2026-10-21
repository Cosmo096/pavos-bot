import unittest
from unittest.mock import patch

from src.config.cercados import CIUDADES
from src.config.filtros import FILTROS_POR_CERCADO
from src.modules import gestor_filtros


class FilterConfigurationTests(unittest.TestCase):
    def test_each_fence_has_a_separate_filter_rule(self):
        cercados = [
            cercado
            for ciudad in CIUDADES.values()
            for cercado in ciudad["cercados"]
        ]

        self.assertEqual(len(FILTROS_POR_CERCADO), len(cercados))
        self.assertEqual(
            {cercado["id"] for cercado in cercados},
            set(FILTROS_POR_CERCADO),
        )

    def test_uncalibrated_filter_fails_before_touching_ui(self):
        with patch.object(gestor_filtros, "tap") as tap:
            with self.assertRaisesRegex(RuntimeError, "no está calibrada"):
                gestor_filtros.aplicar_filtros(["serenidad_gota"])

        tap.assert_not_called()

    def test_other_ui_actions_fail_before_touching_device(self):
        with (
            patch.object(gestor_filtros, "tap") as tap,
            patch.object(gestor_filtros, "swipe") as swipe,
        ):
            for accion in (
                gestor_filtros.reiniciar_filtros,
                gestor_filtros.seleccionar_todos,
                gestor_filtros.arrastrar_a_cercado,
                gestor_filtros.arrastrar_a_establo,
            ):
                with self.subTest(accion=accion.__name__):
                    with self.assertRaisesRegex(RuntimeError, "no está calibrada"):
                        accion()

        tap.assert_not_called()
        swipe.assert_not_called()

    def test_failed_tap_stops_filter_sequence(self):
        with (
            patch.object(gestor_filtros, "COORDENADAS_UI_CALIBRADAS", True),
            patch.object(gestor_filtros, "tap", return_value=False) as tap,
        ):
            with self.assertRaisesRegex(RuntimeError, "Falló el tap"):
                gestor_filtros.reiniciar_filtros()

        tap.assert_called_once()

    def test_failed_swipe_is_reported(self):
        with patch.object(gestor_filtros, "swipe", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "Falló el swipe"):
                gestor_filtros._ejecutar_drag((1, 2), (3, 4))

    def test_capacity_popup_fails_closed_without_confirm_button(self):
        with (
            patch.object(gestor_filtros, "tomar_captura", return_value="capture.png"),
            patch.object(gestor_filtros, "popup_atencion_visible", return_value=True),
            patch.object(gestor_filtros, "tap") as tap,
        ):
            with self.assertRaisesRegex(RuntimeError, "no está calibrado"):
                gestor_filtros._confirmar_popup_si_existe()

        tap.assert_not_called()


if __name__ == "__main__":
    unittest.main()

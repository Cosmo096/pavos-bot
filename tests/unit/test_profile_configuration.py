import unittest
from unittest.mock import patch

from lanzador.comandos import construir_comando
from lanzador.seleccion import migrar_seleccion
from src.config import config_perfiles
from src.config.config_perfiles import (
    ALIAS_POR_ID,
    PERFILES_GUI,
    PERFILES_LOTE,
    PREFIJO,
    perfiles,
)


class ProfileConfigurationTests(unittest.TestCase):
    def test_profile_titles_match_launch_modes(self):
        for profile in perfiles:
            self.assertEqual(
                profile["ventana_titulo"],
                f"{PREFIJO[profile['tipo']]}{profile['nombre']}",
            )

    def test_profile_ids_are_unique_and_batch_profiles_exist(self):
        profile_ids = {profile["id"] for profile in perfiles}
        titles = [profile["ventana_titulo"] for profile in perfiles]

        self.assertEqual(len(profile_ids), len(perfiles))
        self.assertEqual(len(titles), len(set(titles)))
        self.assertTrue(set(PERFILES_LOTE).issubset(profile_ids))
        self.assertTrue(set(PERFILES_GUI).issubset(profile_ids))

    def test_empty_device_configuration_does_not_create_alias(self):
        self.assertNotIn("", ALIAS_POR_ID)

    def test_launcher_command_uses_shared_title_and_display_geometry(self):
        profile = {
            "id": "unit-test",
            "nombre": "Test",
            "dispositivo_alias": "Tablet",
            "dispositivo": "unit-test-device",
            "tipo": "bat",
            "ventana_titulo": "ventana1Test",
        }

        with patch.dict(config_perfiles.DISPOSITIVOS, {"Tablet": "unit-test-device"}):
            command = construir_comando(profile)

        self.assertIn("ventana1Test", command)
        self.assertIn(config_perfiles.SCRCPY_DISPLAY_SIZE, command)
        self.assertIn(str(config_perfiles.SCRCPY_WINDOW_SIZE[0]), command)
        self.assertIn(str(config_perfiles.SCRCPY_WINDOW_POSITION[1]), command)
        self.assertIn("unit-test-device", command)

    def test_missing_device_configuration_fails_closed(self):
        with patch.dict(config_perfiles.DISPOSITIVOS, {"Tablet": ""}):
            with self.assertRaisesRegex(RuntimeError, "ADB_DEVICE_TABLET"):
                config_perfiles.validar_dispositivo_configurado("Tablet")

    def test_launcher_command_builds_secondary_user_arguments(self):
        profile = {
            "id": "unit-test",
            "nombre": "Test",
            "dispositivo_alias": "Tablet",
            "dispositivo": "unit-test-device",
            "tipo": "ps1",
            "ventana_titulo": "ventana2Test",
        }

        with patch.dict(config_perfiles.DISPOSITIVOS, {"Tablet": "unit-test-device"}):
            command = construir_comando(profile)

        self.assertIn("-Title", command)
        self.assertEqual(command[command.index("-Title") + 1], "ventana2Test")
        self.assertIn("-DisplaySize", command)

    def test_selection_migrates_legacy_keys_without_device_id(self):
        profile = {
            "id": "test-secondary",
            "nombre": "Test",
            "tipo": "ps1",
        }

        selected = migrar_seleccion(
            {"Test|local-device-identifier|ps1": True},
            [profile],
        )

        self.assertEqual(selected, {"test-secondary": True})

    def test_selection_rejects_ambiguous_legacy_keys(self):
        profile = {
            "id": "test-secondary",
            "nombre": "Test",
            "tipo": "ps1",
        }

        with self.assertRaises(ValueError):
            migrar_seleccion(
                {
                    "Test|device-a|ps1": True,
                    "Test|device-b|ps1": False,
                },
                [profile],
            )


if __name__ == "__main__":
    unittest.main()

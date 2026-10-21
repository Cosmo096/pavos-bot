import unittest

from src.domain.dragopavos import EstadoCandidato, revalidar_candidato


class FenceRuleTests(unittest.TestCase):
    def test_shared_boundaries_belong_to_maturity(self):
        for value in (-1999, 1999):
            with self.subTest(value=value):
                self.assertTrue(
                    revalidar_candidato(
                        "madurez", EstadoCandidato(value, 99)
                    ).aceptado
                )

        self.assertFalse(
            revalidar_candidato(
                "resistencia", EstadoCandidato(-1999, 99)
            ).aceptado
        )
        self.assertFalse(
            revalidar_candidato(
                "amor", EstadoCandidato(1999, 99)
            ).aceptado
        )

    def test_directional_ranges_exclude_their_cutoff(self):
        self.assertFalse(
            revalidar_candidato(
                "tristeza", EstadoCandidato(-1999, 99)
            ).aceptado
        )
        self.assertTrue(
            revalidar_candidato(
                "tristeza", EstadoCandidato(-1998, 99)
            ).aceptado
        )
        self.assertTrue(
            revalidar_candidato(
                "felicidad", EstadoCandidato(1998, 99)
            ).aceptado
        )
        self.assertFalse(
            revalidar_candidato(
                "felicidad", EstadoCandidato(1999, 99)
            ).aceptado
        )

    def test_cansancio_must_be_read_and_below_one_hundred(self):
        for fatigue in (None, 100, 101):
            with self.subTest(fatigue=fatigue):
                result = revalidar_candidato(
                    "madurez", EstadoCandidato(0, fatigue)
                )
                self.assertFalse(result.aceptado)

        self.assertTrue(
            revalidar_candidato(
                "madurez", EstadoCandidato(0, 99.9)
            ).aceptado
        )

    def test_unread_or_invalid_serenity_is_rejected(self):
        for serenity in (None, -10001, 10001):
            with self.subTest(serenity=serenity):
                result = revalidar_candidato(
                    "amor", EstadoCandidato(serenity, 50)
                )
                self.assertFalse(result.aceptado)

    def test_unknown_fence_type_is_an_error(self):
        with self.assertRaises(ValueError):
            revalidar_candidato("unknown", EstadoCandidato(0, 0))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rango:
    minimo: int
    maximo: int
    incluir_minimo: bool
    incluir_maximo: bool

    def contiene(self, valor: int) -> bool:
        inferior = valor >= self.minimo if self.incluir_minimo else valor > self.minimo
        superior = valor <= self.maximo if self.incluir_maximo else valor < self.maximo
        return inferior and superior


@dataclass(frozen=True)
class EstadoCandidato:
    serenidad: int | None
    cansancio_pct: float | None


@dataclass(frozen=True)
class ResultadoValidacion:
    aceptado: bool
    motivos: tuple[str, ...]


RANGOS_SERENIDAD = {
    "bajar_serenidad": Rango(-1999, 10000, False, True),
    "subir_serenidad": Rango(-10000, 1999, True, False),
    "resistencia": Rango(-10000, -1999, True, False),
    "madurez": Rango(-1999, 1999, True, True),
    "amor": Rango(1999, 10000, False, True),
}

REGLA_POR_TIPO_CERCADO = {
    "tristeza": "bajar_serenidad",
    "felicidad": "subir_serenidad",
    "resistencia": "resistencia",
    "madurez": "madurez",
    "amor": "amor",
}


def revalidar_candidato(
    tipo_cercado: str, estado: EstadoCandidato
) -> ResultadoValidacion:
    """Revalida serenidad y cansancio; lecturas incompletas nunca son elegibles."""
    regla = REGLA_POR_TIPO_CERCADO.get(tipo_cercado)
    if regla is None:
        raise ValueError(f"Tipo de cercado desconocido: {tipo_cercado}")

    motivos = []
    serenidad = estado.serenidad
    cansancio = estado.cansancio_pct

    if serenidad is None:
        motivos.append("serenidad_no_leida")
    elif not -10000 <= serenidad <= 10000:
        motivos.append("serenidad_fuera_de_rango")
    elif not RANGOS_SERENIDAD[regla].contiene(serenidad):
        motivos.append("serenidad_no_corresponde_al_cercado")

    if cansancio is None:
        motivos.append("cansancio_no_leido")
    elif not 0 <= cansancio <= 100:
        motivos.append("cansancio_fuera_de_rango")
    elif cansancio >= 100:
        motivos.append("cansancio_maximo")

    return ResultadoValidacion(
        aceptado=not motivos,
        motivos=tuple(motivos),
    )

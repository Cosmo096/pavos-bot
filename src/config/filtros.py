"""Filtros lógicos configurados individualmente para cada cercado."""

_FILTROS_POR_TIPO = {
    "madurez": ("Madurez", "serenidad_gota", "cansancio_menor100"),
    "felicidad": (
        "Amor",
        "serenidad_rayo",
        "serenidad_gota",
        "cansancio_menor100",
    ),
    "tristeza": (
        "Aguante",
        "serenidad_gota",
        "serenidad_corazon",
        "cansancio_menor100",
    ),
    "resistencia": ("Aguante", "serenidad_rayo", "cansancio_menor100"),
    "amor": ("Amor", "serenidad_corazon", "cansancio_menor100"),
}

FILTROS_POR_CERCADO = {
    f"{ciudad}_{tipo}": filtros
    for ciudad in ("brakmar", "bonta")
    for tipo, filtros in _FILTROS_POR_TIPO.items()
}

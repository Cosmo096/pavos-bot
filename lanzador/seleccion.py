from __future__ import annotations


def migrar_seleccion(data: object, perfiles: list[dict]) -> dict[str, bool]:
    """Convierte selecciones antiguas a IDs estables sin conservar seriales."""
    if not isinstance(data, dict):
        raise ValueError("La selección guardada debe contener un objeto JSON.")

    seleccion: dict[str, bool] = {}
    for perfil in perfiles:
        profile_id = perfil["id"]
        if profile_id in data:
            value = data[profile_id]
            if not isinstance(value, bool):
                raise ValueError(
                    f"La selección guardada para {profile_id} no es booleana."
                )
            seleccion[profile_id] = value
            continue

        prefix = f"{perfil['nombre']}|"
        suffix = f"|{perfil['tipo']}"
        legacy_keys = [
            key
            for key in data
            if isinstance(key, str)
            and key.startswith(prefix)
            and key.endswith(suffix)
        ]
        if len(legacy_keys) > 1:
            raise ValueError(
                f"La selección antigua para {perfil['nombre']}|{perfil['tipo']} "
                "es ambigua; conserva una sola entrada para ese perfil."
            )
        if legacy_keys:
            value = data[legacy_keys[0]]
            if not isinstance(value, bool):
                raise ValueError(
                    f"La selección guardada para {perfil['nombre']} no es booleana."
                )
            seleccion[profile_id] = value
    return seleccion

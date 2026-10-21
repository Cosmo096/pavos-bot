"""
CONFIGURACIÓN DE CERCADOS POR CIUDAD
======================================
Este archivo es el único lugar donde defines la geografía del juego.
Cada vez que necesites agregar, quitar o cambiar un cercado,
lo haces aquí sin tocar ningún otro módulo.

ESTRUCTURA DE CADA CERCADO:
    nombre:    nombre descriptivo para el reporte
    tipo:      tipo de cercado (madurez/felicidad/tristeza/resistencia/amor)
               este tipo se usa para buscar los filtros en filtros.py
    mapa:      coordenadas del mapa donde está la puerta "X,Y"
    solo_sexo: None = sin restricción, "hembra" o "macho"
               REGLA: amor y resistencia en Brakmar = hembra
                      amor y resistencia en Bonta   = macho

ORDEN DE VISITA:
    El bot visita los cercados en el orden en que están en esta lista.
    Orden definido: madurez → felicidad → tristeza → resistencia → amor

CIUDADES:
    Brakmar: centro en -26,36 / zaapi lleva a -32,37
    Bonta:   centro en -33,-56 / zaapi lleva a -36,-56
             (requiere un movimiento izquierda adicional al llegar)
"""

CERCADOS_BRAKMAR = [
    {
        "id":        "brakmar_madurez",
        "nombre":    "Madurez Brakmar",
        "tipo":      "madurez",
        "mapa":      "-31,37",
        "solo_sexo": None,
    },
    {
        "id":        "brakmar_felicidad",
        "nombre":    "Felicidad Brakmar",
        "tipo":      "felicidad",
        "mapa":      "-30,38",
        "solo_sexo": None,
    },
    {
        "id":        "brakmar_tristeza",
        "nombre":    "Tristeza Brakmar",
        "tipo":      "tristeza",
        "mapa":      "-32,38",
        "solo_sexo": None,
    },
    {
        "id":        "brakmar_resistencia",
        "nombre":    "Resistencia Brakmar",
        "tipo":      "resistencia",
        "mapa":      "-31,38",
        "solo_sexo": "hembra",   # ← solo hembras en Brakmar
    },
    {
        "id":        "brakmar_amor",
        "nombre":    "Amor Brakmar",
        "tipo":      "amor",
        "mapa":      "-30,37",
        "solo_sexo": "hembra",   # ← solo hembras en Brakmar
    },
]

CERCADOS_BONTA = [
    {
        "id":        "bonta_madurez",
        "nombre":    "Madurez Bonta",
        "tipo":      "madurez",
        "mapa":      "-36,-57",
        "solo_sexo": None,
    },
    {
        "id":        "bonta_felicidad",
        "nombre":    "Felicidad Bonta",
        "tipo":      "felicidad",
        "mapa":      "-37,-57",
        "solo_sexo": None,
    },
    {
        "id":        "bonta_tristeza",
        "nombre":    "Tristeza Bonta",
        "tipo":      "tristeza",
        "mapa":      "-38,-57",
        "solo_sexo": None,
    },
    {
        "id":        "bonta_resistencia",
        "nombre":    "Resistencia Bonta",
        "tipo":      "resistencia",
        "mapa":      "-38,-56",
        "solo_sexo": "macho",    # ← solo machos en Bonta
    },
    {
        "id":        "bonta_amor",
        "nombre":    "Amor Bonta",
        "tipo":      "amor",
        "mapa":      "-37,-56",
        "solo_sexo": "macho",    # ← solo machos en Bonta
    },
]

# Mapa completo para el bot
CIUDADES = {
    "brakmar": {
        "cercados":          CERCADOS_BRAKMAR,
        "coord_centro":      "-26,36",
        "coord_zaapi_llegada": "-32,37",
        "movimiento_extra":  None,          # Brakmar llega directo al primer mapa
    },
    "bonta": {
        "cercados":          CERCADOS_BONTA,
        "coord_centro":      "-33,-56",
        "coord_zaapi_llegada": "-36,-56",
        "movimiento_extra":  None,          # navegamos por coordenadas, no por borde
    },
}
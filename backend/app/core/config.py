"""Configuracion de la aplicacion y variables de entorno.

Unico lugar donde se lee el entorno. Ningun otro modulo llama a os.getenv:
si algo necesita un valor de configuracion, lo importa de aca.

Los valores por defecto son deliberadamente de DESARROLLO, elegidos para que
en local no haga falta configurar nada: se clona, se instala y se levanta.
En produccion esos mismos valores son inaceptables, y por eso existe
verificar_configuracion_produccion() (ver el final del archivo).

Las variables que consume el proyecto estan documentadas en
documentacion/04_Infraestructura.md, seccion 2.3.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------- identidad --

NOMBRE_APP = "SMART Building"
VERSION = "0.1.0"
PREFIJO_API = "/api"

# --------------------------------------------------------------- entorno ----

# Vercel define esta variable sola en sus despliegues. Es la unica senal de que
# estamos en produccion: no se deduce del dominio ni de la cadena de conexion.
ES_PRODUCCION = bool(os.getenv("VERCEL"))


# --------------------------------------------------------- base de datos ----

# Ruta absoluta a partir de la ubicacion de ESTE archivo, no del directorio
# desde el que se ejecuta uvicorn: si dependiera del directorio actual, levantar
# el backend desde la raiz del proyecto crearia una segunda base vacia, y el
# login fallaria con usuarios que "existen" en la otra.
# config.py -> core -> app -> backend/
_DIRECTORIO_BACKEND = Path(__file__).resolve().parent.parent.parent
_SQLITE_LOCAL = f"sqlite:///{_DIRECTORIO_BACKEND / 'smart_building.db'}"

DATABASE_URL = os.getenv("DATABASE_URL", _SQLITE_LOCAL)

# Verdadero cuando corremos sobre el SQLite de desarrollo. Lo usa la guarda de
# produccion y, mas adelante, el engine, que necesita argumentos distintos
# segun el motor (02_Documento_Tecnico.md, seccion 1.4).
USA_SQLITE = DATABASE_URL.startswith("sqlite")


# ------------------------------------------------------------------- JWT ----

# Valor conocido y publico, a proposito: si este secreto llega a produccion, la
# guarda de abajo lo detecta por comparacion exacta y no deja arrancar.
JWT_SECRETO_DESARROLLO = "clave-de-desarrollo-no-usar-en-produccion"

JWT_SECRETO = os.getenv("JWT_SECRETO", JWT_SECRETO_DESARROLLO)
JWT_ALGORITMO = "HS256"

# Sesion corta: no hay refresh token todavia, se vuelve a iniciar sesion.
# Se revisita si la friccion lo justifica (02_Documento_Tecnico.md, seccion 7).
JWT_MINUTOS_EXPIRACION = 60


# ------------------------------------------------------------------ CORS ----

# Los puertos del desarrollo local: 8090 es el servidor estatico del frontend
# (frontend/servidor_dev.py) y 8000 el propio backend.
_ORIGENES_LOCALES = [
    "http://localhost:8090",
    "http://127.0.0.1:8090",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


def _leer_origenes_extra() -> list[str]:
    """Dominios adicionales permitidos, separados por coma.

    Se lee como texto y se parte a mano a proposito: una lista declarada como
    tal en una libreria de configuracion espera JSON en la variable de entorno
    (`["https://..."]`), y quien la carga desde el panel de Vercel escribe una
    lista separada por comas. Esa diferencia falla al arrancar y el mensaje de
    error no dice que el problema es el formato.
    """
    crudo = os.getenv("CORS_ORIGENES_EXTRA", "")
    return [origen.strip() for origen in crudo.split(",") if origen.strip()]


# En produccion los origenes locales NO entran: la whitelist queda reducida a
# los dominios reales que se hayan declarado. Dejar localhost habilitado contra
# la API de produccion es una puerta que no hace falta tener abierta, y la
# guarda de mas abajo ya exige que CORS_ORIGENES_EXTRA venga cargado.
CORS_ORIGENES = (
    _leer_origenes_extra()
    if ES_PRODUCCION
    else _ORIGENES_LOCALES + _leer_origenes_extra()
)


# -------------------------------------------------- guarda de produccion ----


class ConfiguracionInsegura(RuntimeError):
    """La aplicacion esta en produccion con configuracion de desarrollo."""


def verificar_configuracion_produccion() -> None:
    """Falla fuerte si detecta produccion mal configurada.

    Se llama al iniciar la aplicacion, antes de atender el primer request. Es
    preferible que el despliegue no arranque a que arranque inseguro sin que
    nadie lo note: un backend caido se ve enseguida, un backend firmando tokens
    con un secreto publico puede pasar meses sin que nadie lo advierta.

    En desarrollo no hace absolutamente nada.
    """
    if not ES_PRODUCCION:
        return

    problemas: list[str] = []

    if JWT_SECRETO == JWT_SECRETO_DESARROLLO:
        problemas.append(
            "JWT_SECRETO tiene el valor de desarrollo. Cualquiera que lea el "
            "codigo puede firmar un token valido y hacerse pasar por cualquier "
            "usuario. Defini JWT_SECRETO en las variables de entorno."
        )

    if USA_SQLITE:
        problemas.append(
            "DATABASE_URL apunta a SQLite. El entorno serverless no tiene disco "
            "persistente: todo lo que se escriba se pierde al terminar la "
            "invocacion. Defini DATABASE_URL apuntando al PostgreSQL de "
            "Supabase, a traves del connection pooler."
        )

    if not _leer_origenes_extra():
        problemas.append(
            "CORS_ORIGENES_EXTRA esta vacio. Solo estan permitidos los origenes "
            "de desarrollo, asi que el frontend desplegado no va a poder hablar "
            "con la API. Defini el dominio real del frontend."
        )

    if problemas:
        detalle = "\n".join(f"  - {p}" for p in problemas)
        raise ConfiguracionInsegura(
            f"{NOMBRE_APP} no puede arrancar en produccion:\n{detalle}"
        )

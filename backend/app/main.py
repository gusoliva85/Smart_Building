"""Punto de entrada de la API de SMART Building.

Arma la aplicacion, monta CORS, prepara el esquema al arrancar y expone el
endpoint de salud. Los routers de cada dominio se van montando aca, uno por
fase, a medida que el Roadmap los construye.

Se levanta con:  uvicorn app.main:app --reload   (desde backend/)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import config
from app.core.migraciones import sincronizar_esquema

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("smart_building")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Lo que pasa al arrancar, antes de atender el primer request.

    El orden importa: primero se verifica la configuracion y recien despues se
    toca la base. Si el despliegue esta mal configurado conviene que falle sin
    haber abierto una sola conexion.
    """
    logger.info(
        "Iniciando %s %s en modo %s",
        config.NOMBRE_APP,
        config.VERSION,
        "PRODUCCION" if config.ES_PRODUCCION else "desarrollo",
    )

    # Falla fuerte si estamos en produccion con configuracion de desarrollo.
    # Es preferible que el despliegue no arranque a que arranque inseguro.
    config.verificar_configuracion_produccion()

    sincronizar_esquema()

    logger.info("Origenes CORS permitidos: %s", ", ".join(config.CORS_ORIGENES) or "(ninguno)")
    logger.info("API lista en %s", config.PREFIJO_API)

    yield

    logger.info("Deteniendo %s", config.NOMBRE_APP)


app = FastAPI(
    title=f"{config.NOMBRE_APP} — API",
    version=config.VERSION,
    description=(
        "API de gestion integral de consorcios. La documentacion interactiva "
        "esta disponible solo en desarrollo."
    ),
    lifespan=ciclo_de_vida,
    # La documentacion interactiva se apaga en produccion. Abierta, deja el
    # esquema completo de la API —todas las rutas y todos los campos de cada
    # modelo— a la vista de cualquier visitante anonimo. En desarrollo, en
    # cambio, es la herramienta con la que se prueba y se aprueba cada tarea
    # de backend antes de que exista su pantalla, asi que ahi queda activa.
    docs_url=None if config.ES_PRODUCCION else "/docs",
    redoc_url=None if config.ES_PRODUCCION else "/redoc",
    openapi_url=None if config.ES_PRODUCCION else "/openapi.json",
)

# Whitelist explicita de origenes, nunca un comodin. En produccion la lista
# son los dominios reales; en desarrollo, los puertos locales (config.py).
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGENES,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(f"{config.PREFIJO_API}/salud", tags=["Sistema"])
def salud() -> dict:
    """Confirma que la API esta viva.

    Lo usa el indicador de conexion del frontend y sirve como primera
    verificacion despues de cada despliegue.

    En produccion devuelve lo minimo indispensable: es un endpoint publico,
    sin autenticacion, y no hay razon para contarle a un visitante anonimo
    sobre que motor de base corre el sistema.
    """
    respuesta = {
        "estado": "ok",
        "aplicacion": config.NOMBRE_APP,
        "version": config.VERSION,
    }

    if not config.ES_PRODUCCION:
        respuesta["entorno"] = "desarrollo"
        respuesta["base_de_datos"] = "sqlite" if config.USA_SQLITE else "postgresql"

    return respuesta

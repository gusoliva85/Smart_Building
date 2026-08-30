"""Configuración central del backend: rutas, base de datos, CORS y secretos.

Lee de variables de entorno cuando existen (Vercel, en producción) y cae a
los mismos valores de siempre para desarrollo local — así no hace falta
ningún archivo `.env` ni configuración extra para seguir trabajando en la
máquina de siempre exactamente igual que hasta ahora.
"""

import os
from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parent.parent.parent
RUTA_BASE_DATOS = RAIZ_BACKEND / "smart_building.db"

NOMBRE_APP = "SMART Building API"

# DATABASE_URL: si existe (Vercel → Supabase/Postgres), se usa esa. Si no
# (desarrollo local), se arma la de SQLite de siempre — el resto del
# código (database.py) no necesita saber cuál de las dos es.
DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{RUTA_BASE_DATOS}"

# Puertos de convención del proyecto en desarrollo local: backend en 8000,
# frontend estático en 8090 (README.md explica cómo levantar cada uno a
# mano). CORS_ORIGENES_EXTRA permite sumar el dominio real del frontend en
# Vercel sin tocar código, vía variable de entorno (coma-separado).
ORIGENES_CORS = [
    "http://127.0.0.1:8090",
    "http://localhost:8090",
] + [origen.strip() for origen in os.environ.get("CORS_ORIGENES_EXTRA", "").split(",") if origen.strip()]

# Nota de seguridad (Documento Técnico, sección 19): el valor por default es
# válido únicamente para el modo test/desarrollo local. En Vercel, la
# variable de entorno JWT_SECRETO (generada, nunca este valor trivial)
# tiene que estar configurada — production_ok() más abajo lo verifica.
JWT_SECRETO = os.environ.get("JWT_SECRETO", "smart-building-dev-secret-no-usar-en-produccion")
JWT_ALGORITMO = "HS256"
JWT_MINUTOS_EXPIRACION = 60

ES_PRODUCCION = os.environ.get("VERCEL") == "1"


def verificar_configuracion_produccion():
    """Se llama una vez al arrancar (main.py). Si corre en Vercel con el
    secreto de desarrollo todavía puesto, falla fuerte en vez de arrancar
    con una configuración insegura sin que nadie lo note."""
    if ES_PRODUCCION and JWT_SECRETO == "smart-building-dev-secret-no-usar-en-produccion":
        raise RuntimeError(
            "Falta configurar la variable de entorno JWT_SECRETO en Vercel "
            "(no se puede desplegar a producción con el secreto de desarrollo)."
        )

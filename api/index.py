"""Punto de entrada de la API en Vercel.

Vercel busca las funciones serverless en la carpeta `api/` de la raiz del
repositorio, no dentro de `backend/`. Este archivo es el unico puente entre
esa convencion y la estructura del proyecto: **no tiene logica propia y no
debe tenerla nunca**. Todo lo que hace es poner `backend/` en el path de
importacion y exponer la aplicacion que ya existe.

En desarrollo este archivo no participa: ahi se levanta `uvicorn app.main:app`
directo desde `backend/`. Si algo funciona en local y falla en produccion, mirar
primero aca y en `vercel.json`, que son las dos unicas piezas que difieren.
"""

import sys
from pathlib import Path

# api/index.py -> raiz del repositorio -> backend/
_BACKEND = Path(__file__).resolve().parent.parent / "backend"

# insert(0) y no append: si por lo que sea existiera otro paquete llamado
# "app" en el entorno, queremos el nuestro.
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.main import app  # noqa: E402  (el path tiene que armarse antes del import)

# Vercel detecta la variable `app` como aplicacion ASGI y la sirve.
# El nombre importa: renombrarla rompe el despliegue sin dar un error claro.
__all__ = ["app"]

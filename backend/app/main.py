"""Punto de entrada de la aplicación FastAPI.

Instancia la app, habilita CORS para el frontend de desarrollo, y expone
un endpoint de salud. Los routers de cada dominio (usuarios, edificios,
reclamos, ...) se incluyen acá a medida que las fases siguientes los van
creando.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — registra todos los modelos en Base.metadata
from app.core.config import NOMBRE_APP, ORIGENES_CORS
from app.database import Base, engine
from app.routers import auth, edificios, usuarios

app = FastAPI(title=NOMBRE_APP)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_CORS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(edificios.router)

# Crea, al arrancar, cualquier tabla que todavía no exista en la base real
# (idempotente: no toca las que ya están). Para que funcione, todo modelo
# nuevo tiene que quedar importado antes de esta línea — lo garantiza el
# import de los routers de arriba, que a su vez importan sus modelos.
Base.metadata.create_all(bind=engine)


@app.get("/api/salud")
def leer_salud():
    return {"estado": "ok", "mensaje": f"{NOMBRE_APP} activa"}

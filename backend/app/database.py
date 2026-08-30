"""Conexión a la base de datos vía SQLAlchemy — SQLite en desarrollo local,
Postgres (Supabase) en producción (Vercel), según `DATABASE_URL`.

Expone el engine, la fábrica de sesiones y la Base declarativa que heredan
todos los modelos (Usuario, Edificio, ...). El resto del proyecto (modelos,
routers, servicios) nunca toca este archivo ni sabe cuál de las dos bases
está usando — es exactamente la ventaja de haber elegido SQLAlchemy desde
el día uno (Documento Técnico, sección 2.2).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import DATABASE_URL

# check_same_thread=False es una opción específica de SQLite (por default
# solo permite usar la conexión desde el thread que la abrió, y FastAPI
# atiende cada request en un thread propio) — no aplica a Postgres, así
# que solo se pasa cuando la URL es efectivamente de SQLite.
argumentos_conexion = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=argumentos_conexion)

SesionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def obtener_db():
    """Dependencia de FastAPI: entrega una sesión por request y la cierra al final."""
    db = SesionLocal()
    try:
        yield db
    finally:
        db.close()

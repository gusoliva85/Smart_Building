"""Conexión a la base de datos SQLite vía SQLAlchemy.

Expone el engine, la fábrica de sesiones y la Base declarativa que van
a heredar todos los modelos (Usuario, Edificio, ...) a partir de la Fase 1.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import RUTA_BASE_DATOS

# check_same_thread=False: SQLite por default solo permite usar la conexión
# desde el thread que la abrió; FastAPI atiende cada request en un thread
# propio, así que hace falta desactivar esa restricción para no romper
# la primera consulta real que llegue por HTTP.
engine = create_engine(
    f"sqlite:///{RUTA_BASE_DATOS}",
    connect_args={"check_same_thread": False},
)

SesionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def obtener_db():
    """Dependencia de FastAPI: entrega una sesión por request y la cierra al final."""
    db = SesionLocal()
    try:
        yield db
    finally:
        db.close()

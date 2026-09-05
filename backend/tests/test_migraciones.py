"""Tests de `agregar_columnas_faltantes` — el mecanismo que reemplaza a
Alembic en este proyecto para el único caso que hace falta: sumarle una
columna nueva a una tabla que ya existe (y puede tener datos reales).
"""

import pytest
from sqlalchemy import CheckConstraint, Column, Integer, Numeric, String, create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.migraciones import agregar_columnas_faltantes


@pytest.fixture()
def engine_con_tabla_vieja():
    """Simula el escenario real: una tabla creada con un esquema viejo
    (sin `coeficiente`), con una fila real ya cargada — como pasa hoy con
    `departamentos` en desarrollo y en producción."""
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conexion:
        conexion.execute(text("CREATE TABLE cosa (id INTEGER PRIMARY KEY, nombre VARCHAR)"))
        conexion.execute(text("INSERT INTO cosa (id, nombre) VALUES (1, 'ya existía')"))
    return engine


def _modelo_nuevo():
    """El modelo `Cosa` "actualizado", con un campo nuevo (`coeficiente`)
    que la tabla real todavía no tiene."""
    Base = declarative_base()

    class Cosa(Base):
        __tablename__ = "cosa"
        id = Column(Integer, primary_key=True)
        nombre = Column(String)
        coeficiente = Column(Numeric(6, 3), nullable=True)

    return Base, Cosa


def test_agrega_la_columna_faltante_sin_tocar_los_datos_existentes(engine_con_tabla_vieja):
    Base, Cosa = _modelo_nuevo()

    agregar_columnas_faltantes(engine_con_tabla_vieja, Base)

    Sesion = sessionmaker(bind=engine_con_tabla_vieja)
    db = Sesion()
    fila = db.get(Cosa, 1)

    assert fila.nombre == "ya existía"  # el dato real no se perdió
    assert fila.coeficiente is None  # la columna nueva entra vacía para filas viejas


def test_es_idempotente_correrlo_dos_veces_no_rompe_nada(engine_con_tabla_vieja):
    Base, Cosa = _modelo_nuevo()

    agregar_columnas_faltantes(engine_con_tabla_vieja, Base)
    agregar_columnas_faltantes(engine_con_tabla_vieja, Base)  # no debe fallar ni duplicar la columna

    Sesion = sessionmaker(bind=engine_con_tabla_vieja)
    db = Sesion()
    fila = db.get(Cosa, 1)
    assert fila.nombre == "ya existía"


def test_tabla_completamente_nueva_no_se_toca(engine_con_tabla_vieja):
    # Una tabla que no existe todavía en la base no es responsabilidad de
    # esta función — la crea create_all(), no esto.
    Base, Cosa = _modelo_nuevo()

    class OtraCosa(Base):
        __tablename__ = "otra_cosa"
        id = Column(Integer, primary_key=True)

    agregar_columnas_faltantes(engine_con_tabla_vieja, Base)

    from sqlalchemy import inspect
    assert not inspect(engine_con_tabla_vieja).has_table("otra_cosa")


def test_columna_nueva_puede_escribirse_despues_de_agregada(engine_con_tabla_vieja):
    Base, Cosa = _modelo_nuevo()
    agregar_columnas_faltantes(engine_con_tabla_vieja, Base)

    Sesion = sessionmaker(bind=engine_con_tabla_vieja)
    db = Sesion()
    nueva = Cosa(id=2, nombre="fila nueva", coeficiente=33.333)
    db.add(nueva)
    db.commit()

    recuperada = db.get(Cosa, 2)
    assert float(recuperada.coeficiente) == 33.333


def test_columna_nueva_con_check_constraint_se_agrega_y_se_respeta(engine_con_tabla_vieja):
    # Caso real: Departamento.coeficiente va a llevar un CHECK. Importante
    # lo que reveló ESTE test al escribirlo por primera vez: un
    # `CheckConstraint` en `__table_args__` (constraint de TABLA) no viaja
    # con `CreateColumn` — hay que declararlo pegado a la columna misma
    # (como argumento posicional de `Column(...)`) para que la migración
    # lo incluya en el propio `ADD COLUMN`, que es la única forma en que
    # SQLite acepta un CHECK agregado después de crear la tabla.
    Base = declarative_base()

    class Cosa(Base):
        __tablename__ = "cosa"
        id = Column(Integer, primary_key=True)
        nombre = Column(String)
        coeficiente = Column(
            Numeric(6, 3),
            CheckConstraint("coeficiente IS NULL OR (coeficiente > 0 AND coeficiente <= 100)", name="ck_cosa_coeficiente_valido"),
            nullable=True,
        )

    agregar_columnas_faltantes(engine_con_tabla_vieja, Base)

    Sesion = sessionmaker(bind=engine_con_tabla_vieja)
    db = Sesion()
    db.add(Cosa(id=3, nombre="valido", coeficiente=45.5))
    db.commit()

    db.add(Cosa(id=4, nombre="invalido", coeficiente=150))
    with pytest.raises(IntegrityError):
        db.commit()

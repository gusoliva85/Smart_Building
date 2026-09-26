"""El mecanismo aditivo de evolucion del esquema.

Lo que se prueba no es solo que agregue lo que falta, sino sobre todo **que no
toque nada mas**: es lo que permite reiniciar la aplicacion contra una base con
datos reales sin miedo.
"""

import pytest
from sqlalchemy import Column, Integer, String, Table, create_engine, inspect, text

from app.core.migraciones import sincronizar_esquema
from app.database import Base

TABLA = "edificios_de_prueba"


@pytest.fixture
def engine():
    """Base SQLite en un archivo temporal.

    En disco y no en memoria a proposito: cada llamada a `sincronizar_esquema`
    abre su propia conexion, y lo que se esta probando es justamente que los
    datos sobrevivan entre una y otra.
    """
    from tempfile import TemporaryDirectory
    from pathlib import Path

    with TemporaryDirectory() as carpeta:
        motor = create_engine(f"sqlite:///{Path(carpeta) / 'prueba.db'}")
        try:
            yield motor
        finally:
            motor.dispose()


@pytest.fixture
def tabla():
    """Declara una tabla de juguete y la saca de los modelos al terminar.

    Sin la limpieza, la tabla quedaria registrada en `Base.metadata` para el
    resto de la suite y aparecerian tablas fantasma en otros tests.
    """
    definicion = Table(
        TABLA,
        Base.metadata,
        Column("id", Integer, primary_key=True),
        Column("nombre", String(80), nullable=False),
    )
    try:
        yield definicion
    finally:
        Base.metadata.remove(definicion)


def _columnas(engine) -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns(TABLA)}


def _cargar_datos(engine) -> None:
    with engine.begin() as conexion:
        conexion.execute(text(f"INSERT INTO {TABLA} (nombre) VALUES ('Torre Belgrano')"))
        conexion.execute(text(f"INSERT INTO {TABLA} (nombre) VALUES ('Edificio Palermo')"))


# ------------------------------------------------------------ crear tablas --


def test_crea_la_tabla_que_falta(engine, tabla):
    resumen = sincronizar_esquema(engine)

    assert TABLA in resumen.tablas_creadas
    assert _columnas(engine) == {"id", "nombre"}


def test_no_hace_nada_si_la_base_ya_coincide(engine, tabla):
    sincronizar_esquema(engine)

    resumen = sincronizar_esquema(engine)

    assert resumen.hubo_cambios is False
    assert resumen.tablas_creadas == []
    assert resumen.columnas_agregadas == []


# --------------------------------------------------------- agregar columnas --


def test_agrega_una_columna_anulable_sin_perder_datos(engine, tabla):
    """El caso que define la tarea: sumar un campo a un modelo y reiniciar."""
    sincronizar_esquema(engine)
    _cargar_datos(engine)

    tabla.append_column(Column("cp", String(10)))
    resumen = sincronizar_esquema(engine)

    assert resumen.columnas_agregadas == [f"{TABLA}.cp"]
    with engine.connect() as conexion:
        filas = conexion.execute(text(f"SELECT nombre, cp FROM {TABLA} ORDER BY id")).all()
    assert filas == [("Torre Belgrano", None), ("Edificio Palermo", None)]


def test_agrega_una_columna_obligatoria_si_trae_valor_por_defecto(engine, tabla):
    sincronizar_esquema(engine)
    _cargar_datos(engine)

    tabla.append_column(Column("recargo_mora", Integer, server_default="8", nullable=False))
    resumen = sincronizar_esquema(engine)

    assert resumen.columnas_agregadas == [f"{TABLA}.recargo_mora"]
    with engine.connect() as conexion:
        valores = conexion.execute(text(f"SELECT recargo_mora FROM {TABLA}")).scalars().all()
    assert valores == [8, 8]


def test_omite_una_columna_obligatoria_sin_valor_por_defecto(engine, tabla):
    """No hay nada que poner en las filas que ya existen, y el motor rechaza
    la operacion. Se informa en vez de fallar el arranque entero."""
    sincronizar_esquema(engine)
    _cargar_datos(engine)

    tabla.append_column(Column("cuit", String(13), nullable=False))
    resumen = sincronizar_esquema(engine)

    assert resumen.columnas_omitidas == [f"{TABLA}.cuit"]
    assert resumen.columnas_agregadas == []
    assert "cuit" not in _columnas(engine)


# ------------------------------------------------------- lo que NO se toca --


def test_una_columna_que_ya_no_esta_en_el_modelo_se_conserva_y_se_informa(engine, tabla):
    """Es exactamente como se ve, desde adentro, un esquema que se separo de
    los modelos: el caso de la base de produccion de Supabase (F13-T01)."""
    sincronizar_esquema(engine)
    with engine.begin() as conexion:
        conexion.execute(text(f"ALTER TABLE {TABLA} ADD COLUMN ciudad VARCHAR(80)"))
        conexion.execute(text(f"INSERT INTO {TABLA} (nombre, ciudad) VALUES ('Vieja', 'CABA')"))

    resumen = sincronizar_esquema(engine)

    assert resumen.columnas_sobrantes == [f"{TABLA}.ciudad"]
    assert "ciudad" in _columnas(engine)
    with engine.connect() as conexion:
        assert conexion.execute(text(f"SELECT ciudad FROM {TABLA}")).scalar() == "CABA"


def test_no_borra_ni_vacia_una_tabla_existente(engine, tabla):
    sincronizar_esquema(engine)
    _cargar_datos(engine)

    sincronizar_esquema(engine)
    sincronizar_esquema(engine)

    with engine.connect() as conexion:
        assert conexion.execute(text(f"SELECT count(*) FROM {TABLA}")).scalar() == 2

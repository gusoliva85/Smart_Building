"""El esquema tiene que ser valido en PostgreSQL, no solo en SQLite.

============================================================================
POR QUE EXISTE ESTE ARCHIVO
============================================================================

Por un error real que tiro produccion entera el 2026-11-13, y que la suite
completa no vio porque **los tests corren contra SQLite**.

`Fondo.activo` y `Caja.activo` se declararon con `server_default=text("1")`.
SQLite acepta `DEFAULT 1` en una columna booleana sin chistar. PostgreSQL la
rechaza:

    column "activo" is of type boolean but default expression is of type integer

Y como el esquema **se sincroniza al arrancar la aplicacion**, la creacion de
la tabla fallaba, el arranque fallaba, y la funcion no levantaba:
`FUNCTION_INVOCATION_FAILED`. En desarrollo, perfecto. En produccion, la
aplicacion entera caida.

La leccion no es "acordate de usar expression.true()": es que **cualquier
diferencia entre los dos motores se descubre en produccion**, porque es el
unico lugar donde corre PostgreSQL. Asi que este archivo compila el esquema
completo contra el dialecto de PostgreSQL y revisa lo que esa compilacion no
puede ver sola.

No hace falta una base PostgreSQL para esto: el compilador de SQLAlchemy genera
el DDL exacto que se le mandaria al motor, y con eso alcanza para ver un
`DEFAULT 1` en una columna booleana.
"""

import re

import pytest
from sqlalchemy import Boolean, Numeric
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.database import Base
from app.models import *  # noqa: F401,F403  (registra las tablas en el metadata)

TABLAS = sorted(Base.metadata.tables.values(), key=lambda t: t.name)

# Lo que PostgreSQL acepta como valor por defecto de un booleano.
BOOLEANOS_VALIDOS = {"true", "false"}


def _ddl(tabla) -> str:
    return str(CreateTable(tabla).compile(dialect=postgresql.dialect()))


def test_hay_tablas_para_revisar():
    """Si el agregador de modelos dejara de importar algo, este archivo pasaria
    en verde sin revisar nada. Mejor que falle."""
    assert len(TABLAS) >= 15


@pytest.mark.parametrize("tabla", TABLAS, ids=lambda t: t.name)
def test_la_tabla_compila_para_postgres(tabla):
    """El DDL se genera sin que el compilador se queje.

    Ataja el caso mas grosero: un tipo o una construccion que el dialecto de
    PostgreSQL no sabe escribir.
    """
    assert "CREATE TABLE" in _ddl(tabla)


@pytest.mark.parametrize("tabla", TABLAS, ids=lambda t: t.name)
def test_sus_indices_compilan_para_postgres(tabla):
    for indice in tabla.indexes:
        # "CREATE INDEX" o "CREATE UNIQUE INDEX": se busca el final, que es lo
        # comun a los dos.
        assert "INDEX" in str(
            CreateIndex(indice).compile(dialect=postgresql.dialect())
        )


@pytest.mark.parametrize("tabla", TABLAS, ids=lambda t: t.name)
def test_ninguna_columna_booleana_tiene_default_numerico(tabla):
    """**El error exacto que tiro produccion.**

    PostgreSQL no convierte solo de entero a booleano en un `DEFAULT`. La forma
    correcta es `expression.true()` / `expression.false()`, que el compilador
    escribe como `true` en PostgreSQL y como `1` en SQLite: cada motor recibe
    lo que entiende.
    """
    for columna in tabla.columns:
        if not isinstance(columna.type, Boolean):
            continue
        if columna.server_default is None:
            continue

        texto = str(columna.server_default.arg).strip().lower().strip("'")
        assert texto in BOOLEANOS_VALIDOS, (
            "%s.%s es booleana y su server_default es %r. PostgreSQL lo "
            "rechaza: usa expression.true() o expression.false()."
            % (tabla.name, columna.name, texto)
        )


@pytest.mark.parametrize("tabla", TABLAS, ids=lambda t: t.name)
def test_ninguna_columna_de_plata_es_float(tabla):
    """La regla de toda la Fase 2, verificada sobre el esquema entero y no
    modelo por modelo.

    Una columna de plata declarada `Float` guarda montos "casi" exactos, y cien
    montos casi exactos sumados dan un total que no cierra con ninguno de los
    dos lados. Se revisa por nombre porque es lo unico que distingue una
    columna de plata de cualquier otro numero.
    """
    DE_PLATA = ("monto", "total", "saldo", "recargo", "esperado", "recaudado")

    for columna in tabla.columns:
        if not any(palabra in columna.name for palabra in DE_PLATA):
            continue
        tipo = str(columna.type).upper()
        assert "FLOAT" not in tipo and "REAL" not in tipo and "DOUBLE" not in tipo, (
            "%s.%s es una columna de plata de tipo %s. Tiene que ser Numeric."
            % (tabla.name, columna.name, tipo)
        )
        assert isinstance(columna.type, Numeric), (
            "%s.%s tendria que ser Numeric y es %s" % (tabla.name, columna.name, tipo)
        )


@pytest.mark.parametrize("tabla", TABLAS, ids=lambda t: t.name)
def test_los_defaults_de_texto_van_entre_comillas(tabla):
    """Un `DEFAULT borrador` sin comillas seria un nombre de columna para
    PostgreSQL, no un texto.

    SQLAlchemy entrecomilla sola una cadena de Python, asi que esto hoy pasa;
    el test existe para el dia que alguien escriba el default con `text()` a
    mano y se olvide las comillas de adentro, que es el error facil.
    """
    for linea in _ddl(tabla).splitlines():
        if "DEFAULT" not in linea or "VARCHAR" not in linea:
            continue
        valor = re.search(r"DEFAULT\s+(\S+)", linea)
        if not valor:
            continue
        crudo = valor.group(1)
        # Las funciones del motor no llevan comillas y estan bien.
        if crudo.upper().startswith(("CURRENT_", "NOW(")):
            continue
        assert crudo.startswith("'"), (
            "%s: el default de texto %s no esta entre comillas, asi que "
            "PostgreSQL lo va a leer como un identificador. Linea: %s"
            % (tabla.name, crudo, linea.strip())
        )

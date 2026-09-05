"""Agrega a mano las columnas nuevas que `Base.metadata.create_all()` NO
puede crear.

`create_all()` es idempotente para TABLAS enteras: si la tabla ya existe,
no la toca — pero tampoco le agrega columnas nuevas que un modelo haya
sumado después. Hasta ahora nunca hizo falta nada más, porque cada
modelo nuevo de este proyecto fue siempre una tabla nueva. La primera
vez que un modelo YA EXISTENTE con datos reales (`Departamento`, para
sumarle `coeficiente`) necesita un campo nuevo, hace falta un `ALTER
TABLE` real — y como el proyecto no usa Alembic (deliberadamente, para
no sumar una dependencia más a un stack chico), se resuelve acá con el
mínimo necesario: comparar columnas del modelo contra las que ya tiene
la tabla real, y agregar solo las que falten, usando el propio
compilador de DDL de SQLAlchemy (que ya sabe traducir el tipo/CHECK
correctamente para SQLite en desarrollo y Postgres en producción).

Se llama una sola vez al arrancar, justo después de `create_all()`.
"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateColumn


def agregar_columnas_faltantes(engine: Engine, base) -> None:
    inspector = inspect(engine)
    with engine.begin() as conexion:
        for tabla in base.metadata.sorted_tables:
            if not inspector.has_table(tabla.name):
                continue  # tabla nueva: create_all() ya la creó completa
            columnas_existentes = {c["name"] for c in inspector.get_columns(tabla.name)}
            for columna in tabla.columns:
                if columna.name in columnas_existentes:
                    continue
                ddl_columna = CreateColumn(columna).compile(dialect=engine.dialect)
                conexion.execute(text(f"ALTER TABLE {tabla.name} ADD COLUMN {ddl_columna}"))

"""Evolucion del esquema de base de datos, al arrancar la aplicacion.

El proyecto NO usa Alembic. El esquema evoluciona con dos mecanismos que
corren cuando la aplicacion se inicia, y los dos son **puramente aditivos**:

1. Se crean las tablas que todavia no existen.
2. Se agregan las columnas que un modelo declara y la tabla real no tiene.

Nada mas. Este modulo no modifica, no renombra y no borra absolutamente nada,
por diseno: es la unica forma de que un arranque automatico sea seguro contra
una base con datos.

============================================================================
LIMITES EXACTOS — entenderlos evita corromper datos
============================================================================

| Cambio en el modelo                                  | Lo resuelve solo |
|------------------------------------------------------|------------------|
| Agregar una columna nueva anulable                     | SI               |
| Agregar una columna nueva con valor por defecto        | SI               |
| Agregar una columna obligatoria a una tabla con filas  | NO               |
| Agregar una clave foranea o un CHECK a columna existente | NO             |
| Cambiar el tipo de una columna                         | NO               |
| Renombrar o eliminar una columna                       | NO (se ignora)   |

Todo lo que cae en "NO" necesita una migracion pensada y escrita a mano para
ese caso puntual. Los dos casos concretos del Roadmap que van a caer aca son
la formalizacion de `OrdenTrabajo.activo_id` (F4-T03) y la de los cuatro
`proveedor_id` sueltos (F7-T10): la columna ya existe con datos, asi que
agregarle la clave foranea no lo resuelve este mecanismo.

============================================================================
LA CONSECUENCIA MAS IMPORTANTE
============================================================================

Que sea aditivo significa que, contra una base cuyo esquema NO coincide con
los modelos, esto **no corrige la diferencia y tampoco da error**: deja la
tabla vieja como esta y la aplicacion trabaja contra una forma que no es la
que declaro. Es exactamente el riesgo de la base de produccion de Supabase,
que hoy conserva el esquema del codigo eliminado — ver 04_Infraestructura.md,
seccion 3, y la tarea F13-T01 del Roadmap.

Cuando haya datos reales de clientes que no se puedan perder, conviene migrar
a Alembic. No antes: seria infraestructura sin uso.
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.schema import Column

from app.database import Base

logger = logging.getLogger(__name__)


@dataclass
class ResumenEsquema:
    """Que hizo (y que decidio no hacer) la sincronizacion del esquema."""

    tablas_creadas: list[str] = field(default_factory=list)
    columnas_agregadas: list[str] = field(default_factory=list)
    columnas_omitidas: list[str] = field(default_factory=list)
    columnas_sobrantes: list[str] = field(default_factory=list)

    @property
    def hubo_cambios(self) -> bool:
        return bool(self.tablas_creadas or self.columnas_agregadas)


def _citar(engine: Engine, identificador: str) -> str:
    """Escapa un nombre de tabla o columna segun las reglas del motor."""
    return engine.dialect.identifier_preparer.quote(identificador)


def _clausula_ddl(engine: Engine, columna: Column) -> str | None:
    """Arma el fragmento DDL de una columna, o None si no se puede agregar.

    Devuelve None cuando la columna es obligatoria y no trae un valor por
    defecto del lado del servidor: no hay ningun valor que poner en las filas
    que ya existen, y tanto SQLite como PostgreSQL rechazan la operacion. Ese
    caso necesita una migracion escrita a mano.
    """
    if not columna.nullable and columna.server_default is None:
        return None

    tipo = columna.type.compile(dialect=engine.dialect)
    ddl = f"{_citar(engine, columna.name)} {tipo}"

    if columna.server_default is not None:
        ddl += f" DEFAULT {columna.server_default.arg}"
    if not columna.nullable:
        ddl += " NOT NULL"

    return ddl


def _crear_tablas_faltantes(engine: Engine, resumen: ResumenEsquema) -> None:
    """Crea las tablas que no existen. No toca las que ya estan.

    `create_all` es idempotente y por si solo ya ignora las existentes; se
    calcula la diferencia antes unicamente para poder informar que se creo.
    """
    existentes = set(inspect(engine).get_table_names())
    declaradas = set(Base.metadata.tables)

    resumen.tablas_creadas = sorted(declaradas - existentes)
    Base.metadata.create_all(bind=engine)


def _agregar_columnas_faltantes(engine: Engine, resumen: ResumenEsquema) -> None:
    """Agrega, tabla por tabla, las columnas que el modelo declara y faltan."""
    inspector = inspect(engine)
    tablas_reales = set(inspector.get_table_names())

    for nombre_tabla, tabla in Base.metadata.tables.items():
        # Recien creada por el paso anterior: nace completa, no hay nada que comparar.
        if nombre_tabla not in tablas_reales or nombre_tabla in resumen.tablas_creadas:
            continue

        columnas_reales = {c["name"] for c in inspector.get_columns(nombre_tabla)}
        columnas_declaradas = {c.name for c in tabla.columns}

        # Una columna que esta en la base y ya no en el modelo se deja donde
        # esta, a proposito. Se informa porque suele ser la senal de que el
        # esquema viejo y los modelos se separaron.
        for sobrante in sorted(columnas_reales - columnas_declaradas):
            resumen.columnas_sobrantes.append(f"{nombre_tabla}.{sobrante}")

        for columna in tabla.columns:
            if columna.name in columnas_reales:
                continue

            referencia = f"{nombre_tabla}.{columna.name}"
            fragmento = _clausula_ddl(engine, columna)

            if fragmento is None:
                resumen.columnas_omitidas.append(referencia)
                logger.warning(
                    "Esquema: NO se agrego %s. Es obligatoria y no tiene valor "
                    "por defecto, asi que no hay nada que poner en las filas que "
                    "ya existen. Resolvelo con una migracion escrita a mano, o "
                    "declarala anulable.",
                    referencia,
                )
                continue

            sentencia = f"ALTER TABLE {_citar(engine, nombre_tabla)} ADD COLUMN {fragmento}"
            with engine.begin() as conexion:
                conexion.execute(text(sentencia))

            resumen.columnas_agregadas.append(referencia)
            logger.info("Esquema: columna agregada %s", referencia)


def sincronizar_esquema(engine: Engine | None = None) -> ResumenEsquema:
    """Deja la base al dia con los modelos, de forma aditiva.

    Se llama una vez al iniciar la aplicacion. Recibe el engine por parametro
    para poder ejecutarla contra una base de prueba sin tocar la real.
    """
    from app.database import engine as engine_por_defecto

    engine = engine or engine_por_defecto

    # Importar el paquete de modelos registra TODAS las tablas en Base.metadata.
    # Sin esto, un modelo que nadie importo todavia no existe para SQLAlchemy y
    # su tabla simplemente no se crea — el error aparece recien al primer uso,
    # lejos de la causa.
    import app.models  # noqa: F401

    resumen = ResumenEsquema()
    _crear_tablas_faltantes(engine, resumen)
    _agregar_columnas_faltantes(engine, resumen)

    if resumen.tablas_creadas:
        logger.info("Esquema: tablas creadas -> %s", ", ".join(resumen.tablas_creadas))
    if resumen.columnas_sobrantes:
        logger.info(
            "Esquema: columnas presentes en la base y ausentes en los modelos "
            "(se dejan como estan) -> %s",
            ", ".join(resumen.columnas_sobrantes),
        )
    if not resumen.hubo_cambios:
        logger.info("Esquema: sin cambios, la base ya coincide con los modelos.")

    return resumen

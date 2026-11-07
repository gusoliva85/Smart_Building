"""m001 — El CHECK de `usuarios.rol` tiene que aceptar `pendiente`.

============================================================================
QUE ARREGLA Y DE DONDE SALIO
============================================================================

`F1-T16A` agrego el rol `pendiente`, que es el que recibe una cuenta creada
por el registro publico. La columna `rol` tiene un CheckConstraint que lista
los valores permitidos, armado desde `autorizacion.ROLES`.

Toda tabla `usuarios` creada ANTES de esa tarea tiene el CHECK con ocho
valores. Contra esa tabla, el INSERT del registro se rechaza. Y eso no se nota
al arrancar: `core/migraciones.py` es aditivo, no toca lo que ya existe, e
informa "sin cambios" porque las columnas estan todas.

El sintoma con el que aparecio: el registro devolvia **202 sin crear nada**.
La causa inmediata fue un `except IntegrityError` demasiado ancho en el
endpoint —ya corregido, y con un test que lo fija—, pero el desfasaje de
esquema es un problema propio y es el que arregla esto.

**Hay que correrla una vez por base de datos que exista desde antes de
`F1-T16A`**: la de desarrollo de cada maquina y la de produccion. Una base
recien creada ya nace con el CHECK correcto y esta migracion no hace nada.

============================================================================
POR QUE DOS CAMINOS SEGUN EL MOTOR
============================================================================

PostgreSQL sabe cambiar una restriccion: se borra y se vuelve a crear, en una
transaccion, sin tocar los datos. Son dos sentencias.

SQLite no: no tiene `ALTER TABLE ... DROP CONSTRAINT`. Un CHECK solo se puede
cambiar reconstruyendo la tabla — crear la nueva, copiar las filas, borrar la
vieja, renombrar. Es el procedimiento que recomienda la propia documentacion
de SQLite, y el DDL de la tabla nueva se genera **desde el modelo**, no escrito
a mano: asi la tabla reconstruida es exactamente la que declara el codigo, con
este CHECK y con los que vengan despues, sin que haya que acordarse de
actualizar esta migracion cada vez que cambie una columna.
"""

import logging
import sys

from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateIndex, CreateTable

from app.database import SessionLocal, engine as motor
from app.models.usuario import Usuario
from app.services import autorizacion

logger = logging.getLogger(__name__)

NOMBRE_CHECK = "ck_usuarios_rol_valido"
TABLA = "usuarios"


# ---------------------------------------------------------------- deteccion --


def _ya_esta_aplicada(conexion) -> bool:
    """¿El CHECK de la tabla real ya acepta `pendiente`?

    Se pregunta por el **texto de la restriccion** y no por un registro de
    migraciones corridas, porque no hay tal registro: esta carpeta se lleva a
    mano. Preguntarle a la base por su propio estado es lo unico que no se
    puede desincronizar.

    ========================================================================
    SE PREGUNTA QUE MOTOR ES, NO SE PRUEBAN LAS DOS CONSULTAS
    ========================================================================

    La primera version probaba la consulta de SQLite, atrapaba el error y
    pasaba a la de PostgreSQL. **Rompia en PostgreSQL**, y el motivo vale
    tenerlo escrito porque se repite en cualquier codigo que hable con los dos
    motores: en PostgreSQL una sentencia que falla **aborta la transaccion
    entera**, asi que todo lo que se manda despues —incluida la segunda
    consulta y el conteo de filas de `migrar()`— responde "current transaction
    is aborted" hasta que alguien haga rollback. SQLite no se comporta asi, y
    por eso el error no aparecio en desarrollo.

    Atrapar el error y hacer rollback ahi tambien funcionaria, pero sigue
    siendo provocar una falla a proposito para averiguar algo que SQLAlchemy ya
    sabe. Preguntar el dialecto es mas corto y no deja la transaccion en un
    estado que haya que reparar.
    """
    motor_nombre = conexion.engine.dialect.name

    if motor_nombre == "sqlite":
        # El DDL completo de la tabla, tal como se creo.
        fila = conexion.execute(
            text(
                "SELECT sql FROM sqlite_master "
                "WHERE type = 'table' AND name = :t"
            ),
            {"t": TABLA},
        ).scalar()
    else:
        # PostgreSQL: la definicion de la restriccion, por nombre.
        fila = conexion.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = :c"
            ),
            {"c": NOMBRE_CHECK},
        ).scalar()

    # Sin fila no hay con que responder —la tabla no existe, o la restriccion
    # no tiene ese nombre—, y entonces se asume que falta: es mas seguro
    # intentar una migracion idempotente de mas que saltearla.
    if not fila:
        return False

    return autorizacion.PENDIENTE in fila


# -------------------------------------------------------------- PostgreSQL --


def _migrar_postgres(conexion) -> None:
    """Borra la restriccion y la vuelve a crear con la lista actual.

    `IF EXISTS` en el DROP para que funcione tambien si alguien la borro a
    mano y quedo sin ninguna: el objetivo es dejar la correcta, no castigar el
    estado del que se parte.
    """
    valores = ", ".join(f"'{rol}'" for rol in autorizacion.ROLES)
    conexion.execute(
        text(f"ALTER TABLE {TABLA} DROP CONSTRAINT IF EXISTS {NOMBRE_CHECK}")
    )
    conexion.execute(
        text(
            f"ALTER TABLE {TABLA} ADD CONSTRAINT {NOMBRE_CHECK} "
            f"CHECK (rol IN ({valores}))"
        )
    )


# ------------------------------------------------------------------ SQLite --


def _migrar_sqlite(conexion) -> None:
    """Reconstruye la tabla con el DDL que declara el modelo.

    El procedimiento es el que documenta SQLite, y el orden importa:

      1. Se apagan las claves foraneas. `asignacion_edificio.usuario_id`
         apunta a esta tabla, y el DROP intermedio la dejaria colgada por un
         instante. Se apagan ANTES de abrir la transaccion porque
         `PRAGMA foreign_keys` es una operacion sin efecto dentro de una.
      2. Se crea la tabla nueva con nombre temporal.
      3. Se copian las filas **nombrando las columnas**, no con `SELECT *`:
         si el orden de las columnas difiere entre la tabla vieja y el modelo,
         un `SELECT *` las mete corridas y el dato queda en la columna
         equivocada sin que falle nada.
      4. Se borra la vieja y se renombra la nueva.
      5. Se recrean los indices, que se fueron con el DROP.
      6. Se verifica la integridad de las claves foraneas antes de confirmar.

    El paso 6 es el que convierte esto en algo que se puede correr sin miedo:
    si la reconstruccion dejo una referencia rota, se entera antes del commit
    y no despues.
    """
    tabla = Usuario.__table__
    temporal = f"{TABLA}_m001"

    columnas = ", ".join(c.name for c in tabla.columns)

    ddl = str(CreateTable(tabla).compile(conexion.engine))
    ddl_temporal = ddl.replace(
        f"CREATE TABLE {TABLA} ", f"CREATE TABLE {temporal} ", 1
    )
    if temporal not in ddl_temporal:
        raise RuntimeError(
            "No se pudo renombrar la tabla en el DDL generado. Abortado sin "
            "tocar nada: reconstruir con el nombre equivocado borraria la "
            "tabla original."
        )

    # Se cierra la transaccion que SQLAlchemy abrio sola en las consultas de
    # deteccion. Sin esto, el PRAGMA de abajo cae dentro de una transaccion y
    # SQLite lo ignora en silencio — que es la peor forma de que falle, porque
    # el DROP intermedio dejaria la clave foranea colgada sin avisar.
    conexion.rollback()
    conexion.exec_driver_sql("PRAGMA foreign_keys = OFF")
    try:
        conexion.exec_driver_sql(f"DROP TABLE IF EXISTS {temporal}")
        conexion.exec_driver_sql(ddl_temporal)
        conexion.exec_driver_sql(
            f"INSERT INTO {temporal} ({columnas}) "
            f"SELECT {columnas} FROM {TABLA}"
        )
        conexion.exec_driver_sql(f"DROP TABLE {TABLA}")
        conexion.exec_driver_sql(
            f"ALTER TABLE {temporal} RENAME TO {TABLA}"
        )
        for indice in tabla.indexes:
            conexion.execute(CreateIndex(indice))

        rotas = conexion.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        if rotas:
            raise RuntimeError(
                f"La reconstruccion dejo {len(rotas)} referencia(s) rota(s). "
                "Se revierte todo y no se cambia nada."
            )
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.exec_driver_sql("PRAGMA foreign_keys = ON")


# -------------------------------------------------------------------- main --


def migrar() -> bool:
    """Aplica la migracion si hace falta. Devuelve True si cambio algo."""
    inspector = inspect(motor)
    if TABLA not in inspector.get_table_names():
        print(
            f"La tabla '{TABLA}' no existe en esta base. No hay nada que "
            "migrar: al arrancar la aplicacion se va a crear ya con el CHECK "
            "correcto."
        )
        return False

    with motor.connect() as conexion:
        if _ya_esta_aplicada(conexion):
            print(
                f"El CHECK de '{TABLA}.rol' ya acepta "
                f"'{autorizacion.PENDIENTE}'. No se modifico nada."
            )
            return False

        antes = conexion.execute(text(f"SELECT count(*) FROM {TABLA}")).scalar()

        motor_nombre = conexion.engine.dialect.name
        print(f"Motor: {motor_nombre}. Filas en '{TABLA}': {antes}.")

        if motor_nombre == "sqlite":
            _migrar_sqlite(conexion)
        else:
            try:
                _migrar_postgres(conexion)
                conexion.commit()
            except Exception:
                conexion.rollback()
                raise

    # Se verifica contra una conexion NUEVA, no contra la que hizo el cambio:
    # lo que importa es que quede escrito, no que la transaccion creyera que
    # lo escribio.
    with motor.connect() as conexion:
        if not _ya_esta_aplicada(conexion):
            raise RuntimeError(
                "La migracion corrio sin error pero el CHECK sigue sin "
                "aceptar el rol nuevo. No usar esta base hasta revisarlo."
            )
        despues = conexion.execute(
            text(f"SELECT count(*) FROM {TABLA}")
        ).scalar()

    if despues != antes:
        raise RuntimeError(
            f"La tabla tenia {antes} filas y quedo con {despues}. "
            "Revisar la base antes de usarla."
        )

    print(f"Listo. El CHECK acepta los {len(autorizacion.ROLES)} roles.")
    print(f"Las {despues} filas estan intactas.")
    return True


def _probar_el_insert() -> None:
    """Comprueba el resultado como lo va a usar la aplicacion.

    Que el DDL diga lo correcto y que la base acepte el INSERT son dos cosas
    distintas, y la segunda es la que importa. Se inserta una fila con el rol
    nuevo y se borra; es la unica excepcion a "los usuarios no se borran",
    porque esta fila no es un usuario: no existe fuera de esta comprobacion.
    """
    sesion = SessionLocal()
    try:
        sonda = Usuario(
            nombre="Sonda de migracion",
            email="__m001__@verificacion.invalida",
            password_hash="no-es-un-hash-valido-a-proposito",
            rol=autorizacion.PENDIENTE,
        )
        sesion.add(sonda)
        sesion.commit()
        sesion.delete(sonda)
        sesion.commit()
        print("Verificado: la base acepta un INSERT con el rol nuevo.")
    except Exception as error:
        sesion.rollback()
        print(f"LA BASE SIGUE RECHAZANDO EL ROL NUEVO: {error}")
        raise
    finally:
        sesion.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    try:
        migrar()
        _probar_el_insert()
    except Exception as error:  # noqa: BLE001
        print(f"\nFALLO: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""m002 — le pone a `asignacion_edificio.edificio_id` la clave foranea que le falta.

============================================================================
QUE ARREGLA
============================================================================

`asignacion_edificio` nacio en `F1-T03` con `edificio_id` como entero suelto,
sin clave foranea. No fue un olvido: `edificios` no existia como modelo
todavia, y declarar una FK contra una tabla ausente hace fallar la creacion del
esquema entero al arrancar la aplicacion. Quedo anotado en el propio modelo y
en el Roadmap que se formalizaba en `F1-T18`, que es esta tarea.

Sin la FK, la base acepta una asignacion que apunta a un edificio que no
existe. Eso no se manifiesta como un error: se manifiesta como un auditor que
tiene un edificio asignado y no ve nada, o como un alcance que devuelve una
lista vacia sin motivo visible.

============================================================================
POR QUE ESTA MIGRACION PUEDE BORRAR LA TABLA, Y NINGUNA OTRA PODRIA
============================================================================

Agregar una clave foranea a una columna que ya existe no lo hace
`core/migraciones.py`, que es puramente aditivo (ver su modulo). Y SQLite no
tiene `ALTER TABLE ADD CONSTRAINT` en absoluto: la unica forma de agregarle una
restriccion a una tabla existente es recrearla.

Aca se puede recrear sin perder nada porque la tabla esta **vacia** en todas
las bases: lo primero que escribe una asignacion es la pantalla de `F11-T05`,
que no existe todavia. Entonces "borrar y dejar que se vuelva a crear" no es
migrar datos, es recrear una tabla vacia.

Eso igual no se asume: **se cuenta las filas y, si hay una sola, la migracion
se niega a hacer nada.** Si eso llega a pasar, la tabla ya tiene datos reales y
hace falta una migracion escrita para ese caso, que preserve las filas — el
mismo trabajo que necesitan `OrdenTrabajo.activo_id` (`F4-T03`) y los cuatro
`proveedor_id` sueltos (`F7-T10`).

============================================================================
COMO SE CORRE
============================================================================

    cd backend
    venv\\Scripts\\python.exe -m app.migraciones_manuales.m002_fk_asignacion_edificio

Y contra produccion, con `DATABASE_URL` apuntada al pooler de Supabase, igual
que el seed y que `m001`. Es idempotente: correrla dos veces es seguro, la
segunda vez no hace nada y lo dice.

Se puede correr **antes o despues** de desplegar el codigo nuevo. La propia
migracion recrea la tabla con la FK declarada y crea `edificios` si todavia no
existe, asi que no deja la base a medio camino en ningun orden.
"""

import logging
import sys

from sqlalchemy import inspect, text

import app.models  # noqa: F401 — registra TODAS las tablas en Base.metadata
from app.database import Base, engine as motor
from app.models.usuario import AsignacionEdificio

TABLA = AsignacionEdificio.__tablename__
COLUMNA = "edificio_id"
TABLA_DESTINO = "edificios"


def _ya_tiene_la_fk(inspector) -> bool:
    """¿La columna ya declara su clave foranea a `edificios`?

    Se le pregunta al inspector de SQLAlchemy en vez de leer el DDL o
    `pg_constraint` a mano: es la unica forma que da la misma respuesta en
    SQLite y en PostgreSQL sin escribir dos consultas distintas. `m001` tuvo
    que hacerlo a mano porque preguntaba por el texto de un CHECK, que el
    inspector no expone; una clave foranea si la expone.
    """
    for fk in inspector.get_foreign_keys(TABLA):
        if COLUMNA in (fk.get("constrained_columns") or []):
            return True
    return False


def migrar() -> bool:
    """Aplica la migracion si hace falta. Devuelve True si cambio algo."""
    inspector = inspect(motor)

    if TABLA not in inspector.get_table_names():
        print(
            f"La tabla '{TABLA}' no existe en esta base. No hay nada que "
            "migrar: al arrancar la aplicacion se va a crear ya con la clave "
            "foranea declarada."
        )
        return False

    if _ya_tiene_la_fk(inspector):
        print(
            f"'{TABLA}.{COLUMNA}' ya tiene su clave foranea a "
            f"'{TABLA_DESTINO}'. No se modifico nada."
        )
        return False

    motor_nombre = motor.dialect.name

    with motor.connect() as conexion:
        filas = conexion.execute(text(f"SELECT count(*) FROM {TABLA}")).scalar()

    print(f"Motor: {motor_nombre}. Filas en '{TABLA}': {filas}.")

    if filas:
        raise RuntimeError(
            f"'{TABLA}' tiene {filas} fila(s) y esta migracion solo puede "
            "recrear una tabla vacia. Hace falta una migracion escrita para "
            "este caso, que preserve las filas. No se toco nada."
        )

    # Se borra y se deja que el metadata la vuelva a crear. `create_all` es
    # el MISMO camino que usa el arranque de la aplicacion, asi que la tabla
    # queda exactamente como la declara el modelo y no como la escribiria un
    # DDL a mano en esta migracion — que es justo la clase de duplicado que se
    # desincroniza. `checkfirst` (el default) hace que ademas se cree
    # `edificios` si falta, y que no se toque ninguna otra tabla existente.
    AsignacionEdificio.__table__.drop(bind=motor)
    Base.metadata.create_all(bind=motor)

    # Se verifica con un inspector NUEVO: lo que importa es que quede escrito
    # en la base, no que la operacion no haya dado error.
    inspector = inspect(motor)

    if TABLA_DESTINO not in inspector.get_table_names():
        raise RuntimeError(
            f"La tabla '{TABLA_DESTINO}' sigue sin existir. No usar esta base "
            "hasta revisarlo."
        )

    if not _ya_tiene_la_fk(inspector):
        raise RuntimeError(
            f"La migracion corrio sin error pero '{TABLA}.{COLUMNA}' sigue sin "
            "clave foranea. No usar esta base hasta revisarlo."
        )

    with motor.connect() as conexion:
        filas = conexion.execute(text(f"SELECT count(*) FROM {TABLA}")).scalar()

    if filas:
        raise RuntimeError(
            f"'{TABLA}' quedo con {filas} fila(s) despues de recrearse vacia. "
            "Revisar la base antes de usarla."
        )

    print(f"Listo. '{TABLA}.{COLUMNA}' referencia a '{TABLA_DESTINO}.id'.")
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    try:
        migrar()
    except Exception as error:  # noqa: BLE001
        print(f"\nFALLO: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()

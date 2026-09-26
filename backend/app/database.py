"""Conexion a la base de datos: engine, sesion y base declarativa.

Tres cosas viven aca y nada mas:

- ``engine``       — la conexion, configurada distinto segun el motor.
- ``SessionLocal`` — la fabrica de sesiones.
- ``Base``         — la base declarativa de la que heredan TODOS los modelos.

Mas la dependencia ``obtener_db()``, que es la unica forma en que un endpoint
obtiene una sesion. Ningun router crea una sesion a mano.

El mismo codigo corre sobre SQLite en desarrollo y sobre PostgreSQL en
produccion — esa portabilidad es la razon de usar un ORM y dejo de ser
hipotetica: es exactamente lo que pasa hoy (02_Documento_Tecnico.md, 1.4).
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core import config

# ---------------------------------------------------------------- engine ----


def _argumentos_del_engine() -> dict:
    """Devuelve la configuracion del engine segun el motor y el entorno.

    Son tres escenarios distintos y cada uno necesita algo diferente:
    """
    # 1. SQLite en desarrollo. Por defecto prohibe usar una conexion desde un
    #    hilo distinto del que la creo, y el servidor de desarrollo atiende
    #    requests en varios hilos: sin esto, la primera consulta concurrente
    #    falla con "SQLite objects created in a thread can only be used in
    #    that same thread".
    if config.USA_SQLITE:
        return {"connect_args": {"check_same_thread": False}}

    # 2. PostgreSQL en produccion (serverless, a traves del pooler de Supabase).
    #    La aplicacion NO mantiene su propio pool: cada invocacion serverless es
    #    un proceso efimero, asi que un pool local no se reutiliza nunca y solo
    #    deja conexiones colgadas que el pooler tiene que reciclar. NullPool
    #    abre y cierra la conexion en cada uso y deja el trabajo de agrupar a
    #    quien corresponde, que es el pooler.
    #
    #    Esto resuelve el punto abierto de 04_Infraestructura.md, seccion 3.2:
    #    la configuracion por defecto de SQLAlchemy contra un pooler puede
    #    reutilizar conexiones ya muertas entre invocaciones, y se manifiesta
    #    como errores de conexion intermitentes — no como una falla constante,
    #    que seria mas facil de diagnosticar.
    if config.ES_PRODUCCION:
        return {"poolclass": NullPool}

    # 3. PostgreSQL fuera de produccion (por ejemplo, apuntando a Supabase desde
    #    la maquina local para reproducir un problema). Aca si conviene un pool
    #    normal, porque el proceso vive; pool_pre_ping descarta la conexion
    #    muerta antes de usarla en vez de fallar el request.
    return {"pool_pre_ping": True}


engine = create_engine(config.DATABASE_URL, **_argumentos_del_engine())


# --------------------------------------------------------------- sesion -----

# autoflush desactivado a proposito: con el por defecto, SQLAlchemy puede
# emitir un INSERT a mitad de una funcion solo porque se hizo una consulta,
# y un error de validacion posterior deja rastro de algo que nunca se confirmo.
# Que el momento de escribir sea siempre explicito (commit) hace el codigo
# mas facil de seguir.
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ------------------------------------------------- base de los modelos ------


class Base(DeclarativeBase):
    """Base declarativa de la que hereda todo modelo del proyecto.

    Todo modelo nuevo tiene que estar importado antes de que se cree el
    esquema al arrancar; si no, su tabla no existe y el error aparece recien
    al primer uso. Eso se garantiza con un modulo agregador que los importa a
    todos (F0-T06).
    """


# --------------------------------------------------------- dependencia ------


def obtener_db() -> Generator[Session, None, None]:
    """Entrega una sesion al endpoint y la cierra pase lo que pase.

    Es la unica via por la que un endpoint accede a la base. No hace commit:
    decidir cuando se confirma una operacion es responsabilidad de quien la
    ejecuta, no de la dependencia que presta la conexion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

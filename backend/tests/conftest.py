"""Andamio de pruebas de SMART Building.

Este archivo define el patron de test de integracion que se copia tal cual
durante toda la vida del proyecto. Vale la pena leerlo entero una vez: cada
decision de aca abajo evita un error concreto.

============================================================================
QUE SE PRUEBA Y QUE NO
============================================================================

No se escriben tests de CRUD trivial. Si se prueba, siempre y en la misma
tarea que la crea:

  - toda logica de servicio (funciones puras de services/),
  - toda regla de autorizacion,
  - todo flujo de estados,
  - todo calculo financiero.

Y una regla que no se negocia: **se prueba siempre el caso permitido Y el
prohibido.** Un endpoint sin test de 403 es un endpoint sin control de acceso
probado.

============================================================================
ANTES DE DAR UNA TAREA POR TERMINADA SE CORRE LA SUITE COMPLETA
============================================================================

No alcanza con correr el archivo que se esta escribiendo. Dos regresiones
reales de la iteracion anterior pasaron los tests del archivo nuevo y
rompieron archivos ajenos: un campo que quedo obligatorio sin querer en un
esquema de entrada, y una consulta con columnas explicitas que no incluia una
columna nueva.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, obtener_db
from app.main import app

# ---------------------------------------------------------------------------
# LISTA EXPLICITA DE TABLAS
#
# Las pruebas crean SOLO estas tablas, nunca `Base.metadata.create_all()` a
# secas. Es deliberado y tiene dos ventajas: hace visible que depende de que,
# y falla ruidosamente cuando falta una en vez de arrastrar una tabla que la
# prueba no deberia necesitar.
#
# Cada fase agrega aca los modelos que crea.
# ---------------------------------------------------------------------------
from app.models.usuario import AsignacionEdificio, Usuario  # noqa: E402

TABLAS_DE_PRUEBA: list = [
    Usuario.__table__,
    AsignacionEdificio.__table__,
]


@pytest.fixture
def engine_prueba():
    """Base SQLite en memoria, nueva y vacia para cada test.

    `StaticPool` es imprescindible: sin el, cada conexion a `sqlite://` abre
    una base en memoria DISTINTA, asi que la tabla que creo el fixture no
    existe para el request que hace el test. Falla de una forma
    desconcertante ("no such table") justo despues de haberla creado.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tablas = [t for t in TABLAS_DE_PRUEBA] or None
    Base.metadata.create_all(bind=engine, tables=tablas)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db(engine_prueba):
    """Sesion contra la base de prueba."""
    SesionDePrueba = sessionmaker(bind=engine_prueba, autocommit=False, autoflush=False)
    sesion = SesionDePrueba()
    try:
        yield sesion
    finally:
        sesion.close()


@pytest.fixture
def cliente(db):
    """Cliente HTTP con la base real reemplazada por la de prueba.

    Se sobrescribe la dependencia de sesion y **se limpia al terminar**: si no
    se limpiara, el reemplazo quedaria activo para los tests siguientes y el
    origen del problema seria imposible de adivinar.

    El cliente se construye sin `with` a proposito: el ciclo de vida de la
    aplicacion sincroniza el esquema contra la base REAL de desarrollo, y una
    prueba no tiene por que tocarla.
    """

    def obtener_db_de_prueba():
        yield db

    app.dependency_overrides[obtener_db] = obtener_db_de_prueba
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# HELPER DE AUTENTICACION
#
# `como(rol)` crea un usuario de ese rol, se autentica de verdad contra el
# endpoint de login y devuelve el header `Authorization` listo para usar.
#
# Pasa por el login real en vez de fabricar el token a mano con
# `crear_token_de_acceso`. Es a proposito: un token fabricado salteando el
# login probaria los endpoints contra una sesion que el sistema nunca emitio,
# y el dia que el login cambie —que valide algo mas, que arme el token
# distinto— los tests seguirian pasando contra algo que en la aplicacion real
# ya no funciona.
# ---------------------------------------------------------------------------

PASSWORD_DE_PRUEBA = "Prueba123!"


@pytest.fixture
def como(db, cliente):
    """Devuelve el header de autenticacion de un usuario del rol que se pida.

    Se usa asi:

        def test_algo(cliente, como):
            respuesta = cliente.get("/api/algo", headers=como("encargado"))

    Cada llamada crea un usuario distinto, asi que un mismo test puede pedir
    dos roles —o dos usuarios del mismo rol— sin que choquen por el email.
    """
    from app.core import security
    from app.models.usuario import Usuario

    creados: list[Usuario] = []

    def autenticarse(rol: str, activo: bool = True) -> dict[str, str]:
        # El dominio NO puede ser `.local`, `.test` ni `.example`:
        # `email-validator` rechaza los dominios de uso reservado, asi que un
        # email asi falla en cualquier esquema que lo valide.
        email = f"{rol}-{len(creados)}@prueba.com.ar"
        usuario = Usuario(
            nombre=f"Usuario {rol}",
            email=email,
            password_hash=security.hashear_password(PASSWORD_DE_PRUEBA),
            rol=rol,
            activo=activo,
        )
        db.add(usuario)
        db.commit()
        creados.append(usuario)

        respuesta = cliente.post(
            "/api/auth/login",
            data={"username": email, "password": PASSWORD_DE_PRUEBA},
        )
        # Si el login falla, conviene enterarse aca y con el motivo, no tres
        # lineas despues con un 401 del endpoint que el test queria probar.
        assert respuesta.status_code == 200, respuesta.text

        return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}

    return autenticarse

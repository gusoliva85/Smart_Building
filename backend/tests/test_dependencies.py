"""Tests de core/dependencies.py — la regla de autorización central.

`requerir_acceso_edificio` todavía no la consume ningún endpoint real (el
primer router que la va a usar es el de Edificios, en la próxima tarea de
esta fase) — se prueba llamándola directamente como la función Python que
es, construyendo el `UsuarioAutenticado` a mano. Es el mismo patrón que ya
funcionó para `services/autorizacion.py`: lógica pura, testeable sin un
servidor HTTP real corriendo.
"""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.dependencies import UsuarioAutenticado, obtener_usuario_actual, requerir_acceso_edificio
from app.core.security import crear_token_acceso, hashear_password
from app.database import Base
from app.models.usuario import Usuario


@pytest.fixture()
def sesion():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[Usuario.__table__])
    Sesion = sessionmaker(bind=engine)
    db = Sesion()

    db.add(Usuario(nombre="Ana", email="ana@test.com", password_hash=hashear_password("x"), rol="admin_general"))
    db.add(Usuario(nombre="Beto", email="beto@test.com", password_hash=hashear_password("x"), rol="propietario", activo=False))
    db.commit()

    yield db
    db.close()


def _credenciales(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_obtener_usuario_actual_con_token_valido(sesion):
    token = crear_token_acceso({"sub": "ana@test.com", "rol": "admin_general", "edificios": [1, 2]})
    actual = obtener_usuario_actual(credenciales=_credenciales(token), db=sesion)
    assert isinstance(actual, UsuarioAutenticado)
    assert actual.usuario.email == "ana@test.com"
    assert actual.edificios == [1, 2]


def test_obtener_usuario_actual_con_token_invalido_lanza_401(sesion):
    with pytest.raises(HTTPException) as exc:
        obtener_usuario_actual(credenciales=_credenciales("token-basura"), db=sesion)
    assert exc.value.status_code == 401


def test_obtener_usuario_actual_de_usuario_desactivado_lanza_401(sesion):
    token = crear_token_acceso({"sub": "beto@test.com", "rol": "propietario", "edificios": []})
    with pytest.raises(HTTPException) as exc:
        obtener_usuario_actual(credenciales=_credenciales(token), db=sesion)
    assert exc.value.status_code == 401


def test_requerir_acceso_edificio_admin_general_entra_a_cualquiera():
    actual = UsuarioAutenticado(usuario=Usuario(rol="admin_general"), edificios=[])
    resultado = requerir_acceso_edificio(edificio_id=999, actual=actual)
    assert resultado is actual


def test_requerir_acceso_edificio_propietario_solo_a_los_suyos():
    actual = UsuarioAutenticado(usuario=Usuario(rol="propietario"), edificios=[5, 8])
    assert requerir_acceso_edificio(edificio_id=5, actual=actual) is actual
    with pytest.raises(HTTPException) as exc:
        requerir_acceso_edificio(edificio_id=999, actual=actual)
    assert exc.value.status_code == 403

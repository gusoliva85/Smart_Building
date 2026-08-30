"""Tests del router de usuarios — flujo HTTP completo, login incluido.

Se loguea de verdad contra `/api/auth/login` para obtener un token real
(en vez de fabricar uno a mano), y con ese token se ejercitan los
endpoints de `/api/usuarios` — el mismo camino que va a recorrer el
frontend en la próxima tarea.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hashear_password
from app.database import Base, obtener_db
from app.main import app
from app.models.usuario import Usuario


@pytest.fixture()
def cliente():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[Usuario.__table__])
    SesionTest = sessionmaker(bind=engine)

    db = SesionTest()
    db.add(Usuario(nombre="Admin", email="admin@test.com", password_hash=hashear_password("clave"), rol="admin_general"))
    db.add(Usuario(nombre="Prop", email="prop@test.com", password_hash=hashear_password("clave"), rol="propietario"))
    db.commit()
    db.close()

    def _override_obtener_db():
        sesion = SesionTest()
        try:
            yield sesion
        finally:
            sesion.close()

    app.dependency_overrides[obtener_db] = _override_obtener_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _token(cliente, email, password="clave"):
    respuesta = cliente.post("/api/auth/login", json={"email": email, "password": password})
    return respuesta.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_alta_de_usuario_como_admin_general(cliente):
    token = _token(cliente, "admin@test.com")
    respuesta = cliente.post(
        "/api/usuarios",
        json={"nombre": "Nueva Encargada", "email": "encargada@test.com", "password": "clave2", "rol": "encargado"},
        headers=_headers(token),
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["email"] == "encargada@test.com"
    assert cuerpo["activo"] is True
    assert "password_hash" not in cuerpo
    assert "password" not in cuerpo


def test_alta_con_email_duplicado_devuelve_400(cliente):
    token = _token(cliente, "admin@test.com")
    respuesta = cliente.post(
        "/api/usuarios",
        json={"nombre": "Otro", "email": "admin@test.com", "password": "x", "rol": "encargado"},
        headers=_headers(token),
    )
    assert respuesta.status_code == 400


def test_alta_con_rol_invalido_devuelve_422_no_500(cliente):
    token = _token(cliente, "admin@test.com")
    respuesta = cliente.post(
        "/api/usuarios",
        json={"nombre": "Malo", "email": "malo@test.com", "password": "x", "rol": "super_admin_inventado"},
        headers=_headers(token),
    )
    assert respuesta.status_code == 422


def test_alta_como_propietario_devuelve_403(cliente):
    token = _token(cliente, "prop@test.com")
    respuesta = cliente.post(
        "/api/usuarios",
        json={"nombre": "X", "email": "x@test.com", "password": "x", "rol": "inquilino"},
        headers=_headers(token),
    )
    assert respuesta.status_code == 403


def test_alta_sin_token_devuelve_401(cliente):
    respuesta = cliente.post(
        "/api/usuarios",
        json={"nombre": "X", "email": "x@test.com", "password": "x", "rol": "inquilino"},
    )
    assert respuesta.status_code == 401


def test_listado_incluye_los_usuarios_existentes(cliente):
    token = _token(cliente, "admin@test.com")
    respuesta = cliente.get("/api/usuarios", headers=_headers(token))
    assert respuesta.status_code == 200
    emails = {u["email"] for u in respuesta.json()}
    assert {"admin@test.com", "prop@test.com"} <= emails


def test_edicion_cambia_nombre_y_rol(cliente):
    token = _token(cliente, "admin@test.com")
    listado = cliente.get("/api/usuarios", headers=_headers(token)).json()
    id_prop = next(u["id"] for u in listado if u["email"] == "prop@test.com")

    respuesta = cliente.patch(
        f"/api/usuarios/{id_prop}",
        json={"nombre": "Propietario Editado", "rol": "inquilino"},
        headers=_headers(token),
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Propietario Editado"
    assert cuerpo["rol"] == "inquilino"


def test_baja_logica_desactiva_sin_borrar(cliente):
    token = _token(cliente, "admin@test.com")
    listado = cliente.get("/api/usuarios", headers=_headers(token)).json()
    id_prop = next(u["id"] for u in listado if u["email"] == "prop@test.com")

    respuesta = cliente.post(f"/api/usuarios/{id_prop}/desactivar", headers=_headers(token))
    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False

    # la fila sigue existiendo — reaparece en el listado, solo que inactiva
    listado_despues = cliente.get("/api/usuarios", headers=_headers(token)).json()
    emails = {u["email"] for u in listado_despues}
    assert "prop@test.com" in emails


def test_editar_usuario_inexistente_devuelve_404(cliente):
    token = _token(cliente, "admin@test.com")
    respuesta = cliente.patch("/api/usuarios/9999", json={"nombre": "X"}, headers=_headers(token))
    assert respuesta.status_code == 404

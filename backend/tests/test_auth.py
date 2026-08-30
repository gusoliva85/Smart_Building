"""Tests del router de autenticación (POST /api/auth/login, GET /api/auth/me).

Corre contra la app real de FastAPI (`app.main.app`), pero con la
dependencia `obtener_db` reemplazada por una base SQLite en memoria — así
se prueba el flujo HTTP completo (request → validación → JWT → respuesta)
sin tocar `smart_building.db`.
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
    # StaticPool: una sola conexión compartida para todo el engine. Sin esto,
    # cada Session() nueva (incluida la que abre el override de obtener_db
    # en cada request del TestClient) recibiría su PROPIA base ":memory:"
    # vacía — SQLite en memoria es "una base por conexión", no una sola
    # base compartida por default.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[Usuario.__table__])
    SesionTest = sessionmaker(bind=engine)

    db = SesionTest()
    db.add(Usuario(
        nombre="Ana Admin",
        email="ana@test.com",
        password_hash=hashear_password("clave-correcta"),
        rol="admin_general",
    ))
    db.add(Usuario(
        nombre="Inactivo Test",
        email="inactivo@test.com",
        password_hash=hashear_password("clave-correcta"),
        rol="propietario",
        activo=False,
    ))
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


def test_login_con_credenciales_correctas_devuelve_token(cliente):
    respuesta = cliente.post("/api/auth/login", json={"email": "ana@test.com", "password": "clave-correcta"})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    assert len(cuerpo["access_token"]) > 20


def test_login_con_password_incorrecta_devuelve_401(cliente):
    respuesta = cliente.post("/api/auth/login", json={"email": "ana@test.com", "password": "incorrecta"})
    assert respuesta.status_code == 401


def test_login_con_email_inexistente_devuelve_401_no_500(cliente):
    # Nunca debe filtrarse si el email existe o no en el mensaje de error.
    respuesta = cliente.post("/api/auth/login", json={"email": "no-existe@test.com", "password": "cualquiera"})
    assert respuesta.status_code == 401


def test_login_de_usuario_desactivado_devuelve_401(cliente):
    respuesta = cliente.post("/api/auth/login", json={"email": "inactivo@test.com", "password": "clave-correcta"})
    assert respuesta.status_code == 401


def test_me_sin_token_devuelve_401(cliente):
    respuesta = cliente.get("/api/auth/me")
    assert respuesta.status_code in (401, 403)  # FastAPI/HTTPBearer devuelve 403 si falta el header


def test_me_con_token_valido_devuelve_los_datos_del_usuario(cliente):
    login = cliente.post("/api/auth/login", json={"email": "ana@test.com", "password": "clave-correcta"})
    token = login.json()["access_token"]

    respuesta = cliente.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["email"] == "ana@test.com"
    assert cuerpo["rol"] == "admin_general"
    assert "password_hash" not in cuerpo  # nunca se filtra el hash


def test_me_con_token_invalido_devuelve_401(cliente):
    respuesta = cliente.get("/api/auth/me", headers={"Authorization": "Bearer token-inventado"})
    assert respuesta.status_code == 401

"""Tests del router de edificios (POST /api/edificios) — flujo HTTP completo."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hashear_password
from app.database import Base, obtener_db
from app.main import app
from app.models.edificio import Cochera, Departamento, Edificio, EspacioComun, Piso
from app.models.usuario import Usuario


@pytest.fixture()
def cliente():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[
        Usuario.__table__, Edificio.__table__, Piso.__table__,
        Departamento.__table__, Cochera.__table__, EspacioComun.__table__,
    ])
    SesionTest = sessionmaker(bind=engine)

    db = SesionTest()
    db.add(Usuario(nombre="Admin", email="admin@test.com", password_hash=hashear_password("clave"), rol="admin_general"))
    db.add(Usuario(nombre="Beto Consorcio", email="beto@test.com", password_hash=hashear_password("clave"), rol="admin_consorcio"))
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
    return cliente.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_alta_de_edificio_genera_estructura_completa(cliente):
    token = _token(cliente, "admin@test.com")
    respuesta = cliente.post(
        "/api/edificios",
        json={"nombre": "Torre Central", "direccion": "Av. Siempre Viva 742", "cantidad_pisos": 3, "unidades_por_piso": 4},
        headers=_headers(token),
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()

    assert cuerpo["nombre"] == "Torre Central"
    assert cuerpo["activo"] is True
    assert len(cuerpo["pisos"]) == 3
    # orden de apilado: piso 1 primero (coincide con Piso.orden)
    assert [p["numero"] for p in cuerpo["pisos"]] == ["1", "2", "3"]
    assert [d["identificador"] for d in cuerpo["pisos"][0]["departamentos"]] == ["1A", "1B", "1C", "1D"]
    assert all(d["ocupado"] is False for d in cuerpo["pisos"][0]["departamentos"])


def test_departamentos_generados_no_tienen_dueno_todavia(cliente):
    token = _token(cliente, "admin@test.com")
    respuesta = cliente.post(
        "/api/edificios",
        json={"nombre": "Torre Norte", "direccion": "Calle Falsa 123", "cantidad_pisos": 1, "unidades_por_piso": 2},
        headers=_headers(token),
    )
    depto = respuesta.json()["pisos"][0]["departamentos"][0]
    assert depto["ocupado"] is False
    assert depto["propietario_id"] is None
    assert depto["inquilino_id"] is None


def test_alta_con_admin_consorcio_valido(cliente):
    token = _token(cliente, "admin@test.com")
    listado_ids = cliente.get("/api/usuarios", headers=_headers(token)).json()
    beto_id = next(u["id"] for u in listado_ids if u["email"] == "beto@test.com")

    respuesta = cliente.post(
        "/api/edificios",
        json={"nombre": "Torre Sur", "direccion": "Otra Calle 456", "cantidad_pisos": 1, "unidades_por_piso": 1, "admin_consorcio_id": beto_id},
        headers=_headers(token),
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["admin_consorcio_id"] == beto_id


def test_alta_con_admin_consorcio_de_rol_incorrecto_devuelve_400(cliente):
    token = _token(cliente, "admin@test.com")
    listado = cliente.get("/api/usuarios", headers=_headers(token)).json()
    prop_id = next(u["id"] for u in listado if u["email"] == "prop@test.com")

    respuesta = cliente.post(
        "/api/edificios",
        json={"nombre": "Torre Este", "direccion": "Bulevar 789", "cantidad_pisos": 1, "unidades_por_piso": 1, "admin_consorcio_id": prop_id},
        headers=_headers(token),
    )
    assert respuesta.status_code == 400


def test_alta_como_propietario_devuelve_403(cliente):
    token = _token(cliente, "prop@test.com")
    respuesta = cliente.post(
        "/api/edificios",
        json={"nombre": "X", "direccion": "Y", "cantidad_pisos": 1, "unidades_por_piso": 1},
        headers=_headers(token),
    )
    assert respuesta.status_code == 403


@pytest.mark.parametrize("campo,valor", [("cantidad_pisos", 0), ("unidades_por_piso", 0), ("unidades_por_piso", 27)])
def test_alta_con_valores_fuera_de_rango_devuelve_422(cliente, campo, valor):
    token = _token(cliente, "admin@test.com")
    payload = {"nombre": "X", "direccion": "Y", "cantidad_pisos": 2, "unidades_por_piso": 2}
    payload[campo] = valor
    respuesta = cliente.post("/api/edificios", json=payload, headers=_headers(token))
    assert respuesta.status_code == 422

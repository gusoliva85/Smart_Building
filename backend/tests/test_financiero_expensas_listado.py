"""Tests de GET /api/edificios/{id}/expensas y GET .../expensas/{id} —
faltaban desde la Tarea 8 (solo existía el POST de generación); el hueco
apareció al construir la pestaña "Expensas" del frontend."""

import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hashear_password
from app.database import Base, obtener_db
from app.main import app
from app.models.edificio import Cochera, Departamento, Edificio, EspacioComun, Piso
from app.models.expensa import Expensa, ExpensaDepartamento, ExpensaDetalle
from app.models.gasto import Gasto
from app.models.pago import Pago
from app.models.usuario import Usuario


@pytest.fixture()
def entorno():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[
        Usuario.__table__, Edificio.__table__, Piso.__table__, Departamento.__table__,
        Cochera.__table__, EspacioComun.__table__, Gasto.__table__,
        Expensa.__table__, ExpensaDetalle.__table__, ExpensaDepartamento.__table__, Pago.__table__,
    ])
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
    cliente = TestClient(app)
    headers_admin = {"Authorization": f"Bearer {cliente.post('/api/auth/login', json={'email': 'admin@test.com', 'password': 'clave'}).json()['access_token']}"}
    headers_prop = {"Authorization": f"Bearer {cliente.post('/api/auth/login', json={'email': 'prop@test.com', 'password': 'clave'}).json()['access_token']}"}

    r = cliente.post(
        "/api/edificios",
        json={"nombre": "Torre Expensas", "direccion": "Calle 1", "cantidad_pisos": 1, "unidades_por_piso": 2},
        headers=headers_admin,
    )
    edificio_id = r.json()["id"]
    deptos = r.json()["pisos"][0]["departamentos"]

    db2 = SesionTest()
    db2.get(Departamento, deptos[0]["id"]).coeficiente = 60
    db2.get(Departamento, deptos[1]["id"]).coeficiente = 40
    db2.commit()
    db2.close()

    yield {
        "cliente": cliente, "headers_admin": headers_admin, "headers_prop": headers_prop,
        "edificio_id": edificio_id, "deptos": deptos,
    }
    app.dependency_overrides.clear()


def test_listado_vacio_sin_expensas_generadas(entorno):
    r = entorno["cliente"].get(f"/api/edificios/{entorno['edificio_id']}/expensas", headers=entorno["headers_admin"])
    assert r.status_code == 200
    assert r.json() == []


def test_listar_expensas_generadas_ordenadas_de_mas_reciente_a_mas_vieja(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    cliente.post(f"/api/edificios/{eid}/gastos", json={"rubro": "Limpieza", "monto": 10000, "fecha": "2026-07-05"}, headers=headers)
    cliente.post(f"/api/edificios/{eid}/expensas", json={"anio": 2026, "mes": 7}, headers=headers)
    cliente.post(f"/api/edificios/{eid}/gastos", json={"rubro": "Limpieza", "monto": 20000, "fecha": "2026-08-05"}, headers=headers)
    cliente.post(f"/api/edificios/{eid}/expensas", json={"anio": 2026, "mes": 8}, headers=headers)

    r = cliente.get(f"/api/edificios/{eid}/expensas", headers=headers)
    cuerpo = r.json()
    assert len(cuerpo) == 2
    assert (cuerpo[0]["anio"], cuerpo[0]["mes"]) == (2026, 8)  # más reciente primero
    assert (cuerpo[1]["anio"], cuerpo[1]["mes"]) == (2026, 7)


def test_detalle_de_expensa_incluye_identificador_del_departamento(entorno):
    cliente, headers, eid, deptos = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"], entorno["deptos"]
    cliente.post(f"/api/edificios/{eid}/gastos", json={"rubro": "Limpieza", "monto": 10000, "fecha": "2026-08-05"}, headers=headers)
    expensa = cliente.post(f"/api/edificios/{eid}/expensas", json={"anio": 2026, "mes": 8}, headers=headers).json()

    r = cliente.get(f"/api/edificios/{eid}/expensas/{expensa['id']}", headers=headers)
    assert r.status_code == 200
    identificadores = {d["identificador"] for d in r.json()["por_departamento"]}
    assert identificadores == {deptos[0]["identificador"], deptos[1]["identificador"]}


def test_expensa_de_otro_edificio_devuelve_404(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    cliente.post(f"/api/edificios/{eid}/gastos", json={"rubro": "Limpieza", "monto": 10000, "fecha": "2026-08-05"}, headers=headers)
    expensa = cliente.post(f"/api/edificios/{eid}/expensas", json={"anio": 2026, "mes": 8}, headers=headers).json()

    eid2 = cliente.post(
        "/api/edificios", json={"nombre": "Torre Ajena", "direccion": "Calle 2", "cantidad_pisos": 1, "unidades_por_piso": 1},
        headers=headers,
    ).json()["id"]

    r = cliente.get(f"/api/edificios/{eid2}/expensas/{expensa['id']}", headers=headers)
    assert r.status_code == 404


def test_propietario_no_puede_listar_expensas_del_edificio(entorno):
    r = entorno["cliente"].get(f"/api/edificios/{entorno['edificio_id']}/expensas", headers=entorno["headers_prop"])
    assert r.status_code == 403

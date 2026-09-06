"""Tests de GET /api/edificios/{id}/reportes/financiero — Documento
Técnico, sección 8. Consolida recaudado vs. esperado, gastos por rubro y
morosidad, reutilizando cálculos ya probados en tareas anteriores."""

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
from app.models.fondo import Caja, Fondo, MovimientoCaja, MovimientoFondo
from app.models.gasto import Gasto
from app.models.pago import Pago
from app.models.presupuesto import Factura, Presupuesto
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
        Fondo.__table__, MovimientoFondo.__table__, Caja.__table__, MovimientoCaja.__table__,
        Presupuesto.__table__, Factura.__table__,
    ])
    SesionTest = sessionmaker(bind=engine)

    db = SesionTest()
    db.add(Usuario(nombre="Admin", email="admin@test.com", password_hash=hashear_password("clave"), rol="admin_general"))
    db.add(Usuario(nombre="Prop", email="prop@test.com", password_hash=hashear_password("clave"), rol="propietario"))
    db.commit()
    prop_id = db.query(Usuario).filter_by(email="prop@test.com").first().id
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
        json={"nombre": "Torre Reportes", "direccion": "Calle 1", "cantidad_pisos": 1, "unidades_por_piso": 2},
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
        "edificio_id": edificio_id, "deptos": deptos, "SesionTest": SesionTest,
    }
    app.dependency_overrides.clear()


def test_reporte_vacio_sin_ninguna_expensa_generada(entorno):
    r = entorno["cliente"].get(f"/api/edificios/{entorno['edificio_id']}/reportes/financiero", headers=entorno["headers_admin"])
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["recaudado_vs_esperado"] == []
    assert cuerpo["gastos_por_rubro"] == []
    assert cuerpo["deuda_total_actual"] == 0
    assert cuerpo["cantidad_deudores"] == 0


def test_recaudado_vs_esperado_con_pago_parcial_confirmado(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    cliente.post(f"/api/edificios/{eid}/gastos", json={"rubro": "Limpieza", "monto": 100000, "fecha": "2026-08-05"}, headers=headers)
    cliente.post(f"/api/edificios/{eid}/expensas", json={"anio": 2026, "mes": 8}, headers=headers)

    depto_id = entorno["deptos"][0]["id"]  # coeficiente 60% -> le corresponden 60.000
    expensa_id = 1
    db = entorno["SesionTest"]()
    db.add(Pago(departamento_id=depto_id, expensa_id=expensa_id, monto=40000, medio_pago="transferencia", estado="confirmado"))
    db.add(Pago(departamento_id=depto_id, expensa_id=expensa_id, monto=999999, medio_pago="transferencia", estado="pendiente"))  # no debe contar
    db.commit()
    db.close()

    r = cliente.get(f"/api/edificios/{eid}/reportes/financiero", headers=headers)
    periodo = r.json()["recaudado_vs_esperado"][0]
    assert periodo == {"anio": 2026, "mes": 8, "esperado": 100000, "recaudado": 40000}


def test_gastos_por_rubro_y_periodo_agrupados(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    cliente.post(f"/api/edificios/{eid}/gastos", json={"rubro": "Limpieza", "monto": 10000, "fecha": "2026-07-05"}, headers=headers)
    cliente.post(f"/api/edificios/{eid}/gastos", json={"rubro": "Limpieza", "monto": 5000, "fecha": "2026-07-20"}, headers=headers)
    cliente.post(f"/api/edificios/{eid}/gastos", json={"rubro": "Seguridad", "monto": 30000, "fecha": "2026-08-05"}, headers=headers)

    r = cliente.get(f"/api/edificios/{eid}/reportes/financiero", headers=headers)
    filas = r.json()["gastos_por_rubro"]
    assert {"rubro": "Limpieza", "anio": 2026, "mes": 7, "monto": 15000} in filas  # dos gastos del mismo rubro/mes sumados
    assert {"rubro": "Seguridad", "anio": 2026, "mes": 8, "monto": 30000} in filas


def test_morosidad_reutiliza_el_calculo_de_deudores(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    cliente.post(f"/api/edificios/{eid}/gastos", json={"rubro": "Limpieza", "monto": 100000, "fecha": "2026-08-05"}, headers=headers)
    cliente.post(f"/api/edificios/{eid}/expensas", json={"anio": 2026, "mes": 8}, headers=headers)

    r_deudores = cliente.get(f"/api/edificios/{eid}/deudores", headers=headers)
    r_reporte = cliente.get(f"/api/edificios/{eid}/reportes/financiero", headers=headers)

    total_esperado = round(sum(d["deuda_total"] for d in r_deudores.json()), 2)
    assert r_reporte.json()["deuda_total_actual"] == total_esperado
    assert r_reporte.json()["cantidad_deudores"] == len(r_deudores.json())
    assert r_reporte.json()["cantidad_deudores"] == 2  # ninguno pagó nada


def test_propietario_no_puede_ver_el_reporte(entorno):
    cliente = entorno["cliente"]
    r = cliente.get(f"/api/edificios/{entorno['edificio_id']}/reportes/financiero", headers=entorno["headers_prop"])
    assert r.status_code == 403

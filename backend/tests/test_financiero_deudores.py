"""Tests de GET /api/edificios/{id}/deudores — Documento Técnico 5.2.

Vista calculada: nunca hay una tabla `deudores` propia, se arma
recorriendo `ExpensaDepartamento` menos los `Pago` `confirmado`. La
regla de severidad (Documento General 6.3) es 1 mes de atraso -> amarillo,
más de 1 -> rojo — acá solo se prueba `meses_atraso`, el color en sí lo
calcula el Dashboard Visual en la Fase 5.
"""

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
    token_admin = cliente.post("/api/auth/login", json={"email": "admin@test.com", "password": "clave"}).json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    r = cliente.post(
        "/api/edificios",
        json={"nombre": "Torre Deudores", "direccion": "Calle 1", "cantidad_pisos": 1, "unidades_por_piso": 2},
        headers=headers_admin,
    )
    edificio_id = r.json()["id"]
    deptos = r.json()["pisos"][0]["departamentos"]
    depto_moroso_id, depto_al_dia_id = deptos[0]["id"], deptos[1]["id"]

    db2 = SesionTest()
    db2.get(Departamento, depto_moroso_id).propietario_id = prop_id
    db2.get(Departamento, depto_moroso_id).coeficiente = 50
    db2.get(Departamento, depto_al_dia_id).coeficiente = 50
    db2.commit()
    db2.close()

    def _generar_expensa(anio, mes, monto=10000):
        db3 = SesionTest()
        db3.add(Gasto(edificio_id=edificio_id, rubro="Limpieza", monto=monto, fecha=datetime.date(anio, mes, 5)))
        db3.commit()
        db3.close()
        r = cliente.post(f"/api/edificios/{edificio_id}/expensas", json={"anio": anio, "mes": mes}, headers=headers_admin)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    yield {
        "cliente": cliente, "headers_admin": headers_admin, "edificio_id": edificio_id,
        "depto_moroso_id": depto_moroso_id, "depto_al_dia_id": depto_al_dia_id,
        "generar_expensa": _generar_expensa, "SesionTest": SesionTest,
    }
    app.dependency_overrides.clear()


def _confirmar_pago(entorno, depto_id, expensa_id, monto):
    db = entorno["SesionTest"]()
    db.add(Pago(departamento_id=depto_id, expensa_id=expensa_id, monto=monto, medio_pago="transferencia", estado="confirmado"))
    db.commit()
    db.close()


def test_sin_deuda_devuelve_lista_vacia(entorno):
    # ExpensaDepartamento se genera para TODAS las unidades con
    # coeficiente, tengan o no propietario asignado — hay que confirmar
    # el pago de las dos para que de verdad no quede ningún deudor.
    expensa_id = entorno["generar_expensa"](2026, 8)
    _confirmar_pago(entorno, entorno["depto_moroso_id"], expensa_id, 5000)
    _confirmar_pago(entorno, entorno["depto_al_dia_id"], expensa_id, 5000)

    r = entorno["cliente"].get(f"/api/edificios/{entorno['edificio_id']}/deudores", headers=entorno["headers_admin"])
    assert r.status_code == 200
    assert r.json() == []


def test_deuda_del_mes_corriente_no_cuenta_como_atrasada(entorno):
    entorno["generar_expensa"](2026, 8)
    r = entorno["cliente"].get(
        f"/api/edificios/{entorno['edificio_id']}/deudores?hoy=2026-08-15", headers=entorno["headers_admin"]
    )
    cuerpo = r.json()
    deudor = next(d for d in cuerpo if d["departamento_id"] == entorno["depto_moroso_id"])
    assert deudor["meses_atraso"] == 0
    assert deudor["deuda_total"] == 5000  # 50% de 10.000, sin pagar


def test_un_mes_de_atraso(entorno):
    entorno["generar_expensa"](2026, 8)
    r = entorno["cliente"].get(
        f"/api/edificios/{entorno['edificio_id']}/deudores?hoy=2026-09-10", headers=entorno["headers_admin"]
    )
    deudor = next(d for d in r.json() if d["departamento_id"] == entorno["depto_moroso_id"])
    assert deudor["meses_atraso"] == 1


def test_mas_de_un_mes_de_atraso_con_dos_periodos_impagos(entorno):
    entorno["generar_expensa"](2026, 7)
    entorno["generar_expensa"](2026, 8)
    r = entorno["cliente"].get(
        f"/api/edificios/{entorno['edificio_id']}/deudores?hoy=2026-09-10", headers=entorno["headers_admin"]
    )
    deudor = next(d for d in r.json() if d["departamento_id"] == entorno["depto_moroso_id"])
    assert deudor["meses_atraso"] == 2  # desde julio
    assert len(deudor["expensas_impagas"]) == 2
    assert deudor["deuda_total"] == 10000  # 50% de 10.000 x 2 meses


def test_pago_confirmado_saca_al_departamento_de_deudores(entorno):
    expensa_id = entorno["generar_expensa"](2026, 8)
    _confirmar_pago(entorno, entorno["depto_moroso_id"], expensa_id, 5000)

    r = entorno["cliente"].get(
        f"/api/edificios/{entorno['edificio_id']}/deudores?hoy=2026-09-10", headers=entorno["headers_admin"]
    )
    ids_deudores = [d["departamento_id"] for d in r.json()]
    assert entorno["depto_moroso_id"] not in ids_deudores


def test_departamento_al_dia_nunca_aparece(entorno):
    expensa_julio = entorno["generar_expensa"](2026, 7)
    expensa_agosto = entorno["generar_expensa"](2026, 8)
    # depto_al_dia paga las dos, depto_moroso ninguna
    _confirmar_pago(entorno, entorno["depto_al_dia_id"], expensa_julio, 5000)
    _confirmar_pago(entorno, entorno["depto_al_dia_id"], expensa_agosto, 5000)

    r = entorno["cliente"].get(
        f"/api/edificios/{entorno['edificio_id']}/deudores?hoy=2026-09-10", headers=entorno["headers_admin"]
    )
    ids_deudores = [d["departamento_id"] for d in r.json()]
    assert entorno["depto_al_dia_id"] not in ids_deudores
    assert entorno["depto_moroso_id"] in ids_deudores


def test_orden_de_mas_atrasado_a_menos(entorno):
    # depto_moroso: julio+agosto sin pagar (2 meses de atraso).
    # depto_al_dia: paga julio, debe solo agosto (1 mes de atraso).
    expensa_julio = entorno["generar_expensa"](2026, 7)
    expensa_agosto = entorno["generar_expensa"](2026, 8)
    _confirmar_pago(entorno, entorno["depto_al_dia_id"], expensa_julio, 5000)

    r = entorno["cliente"].get(
        f"/api/edificios/{entorno['edificio_id']}/deudores?hoy=2026-09-10", headers=entorno["headers_admin"]
    )
    cuerpo = r.json()
    assert cuerpo[0]["departamento_id"] == entorno["depto_moroso_id"]  # el más atrasado primero
    assert cuerpo[0]["meses_atraso"] == 2
    assert cuerpo[1]["meses_atraso"] == 1


def test_propietario_no_puede_ver_deudores(entorno):
    cliente = entorno["cliente"]
    token_prop = cliente.post("/api/auth/login", json={"email": "prop@test.com", "password": "clave"}).json()["access_token"]
    entorno["generar_expensa"](2026, 8)
    r = cliente.get(
        f"/api/edificios/{entorno['edificio_id']}/deudores", headers={"Authorization": f"Bearer {token_prop}"}
    )
    assert r.status_code == 403

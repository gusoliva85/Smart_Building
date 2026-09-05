"""Tests de medio de pago (CBU/alias/QR) y registro de pagos con
conciliación — investigado en documentacion/Pagos_y_Conciliacion.md
antes de implementar."""

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
    db.add(Usuario(nombre="Inquilino", email="inquilino@test.com", password_hash=hashear_password("clave"), rol="inquilino"))
    db.add(Usuario(nombre="Prop Ajeno", email="ajeno@test.com", password_hash=hashear_password("clave"), rol="propietario"))
    db.commit()
    admin_id = db.query(Usuario).filter_by(email="admin@test.com").first().id
    prop_id = db.query(Usuario).filter_by(email="prop@test.com").first().id
    inquilino_id = db.query(Usuario).filter_by(email="inquilino@test.com").first().id
    db.close()

    def _override_obtener_db():
        sesion = SesionTest()
        try:
            yield sesion
        finally:
            sesion.close()

    app.dependency_overrides[obtener_db] = _override_obtener_db
    cliente = TestClient(app)

    def _token(email):
        return cliente.post("/api/auth/login", json={"email": email, "password": "clave"}).json()["access_token"]

    headers_admin = {"Authorization": f"Bearer {_token('admin@test.com')}"}

    r = cliente.post(
        "/api/edificios",
        json={"nombre": "Torre Pagos", "direccion": "Calle 1", "cantidad_pisos": 1, "unidades_por_piso": 2},
        headers=headers_admin,
    )
    edificio_id = r.json()["id"]
    deptos = r.json()["pisos"][0]["departamentos"]
    depto_prop_id, depto_otro_id = deptos[0]["id"], deptos[1]["id"]

    db2 = SesionTest()
    db2.get(Departamento, depto_prop_id).propietario_id = prop_id
    db2.get(Departamento, depto_prop_id).inquilino_id = inquilino_id
    db2.get(Departamento, depto_prop_id).coeficiente = 60
    db2.get(Departamento, depto_otro_id).coeficiente = 40
    db2.add(Gasto(edificio_id=edificio_id, rubro="Limpieza", monto=100000, fecha=datetime.date(2026, 8, 5)))
    db2.commit()
    db2.close()

    cliente.post(f"/api/edificios/{edificio_id}/expensas", json={"anio": 2026, "mes": 8}, headers=headers_admin)

    yield {
        "cliente": cliente,
        "headers_admin": headers_admin,
        "headers_prop": {"Authorization": f"Bearer {_token('prop@test.com')}"},
        "headers_inquilino": {"Authorization": f"Bearer {_token('inquilino@test.com')}"},
        "headers_ajeno": {"Authorization": f"Bearer {_token('ajeno@test.com')}"},
        "edificio_id": edificio_id,
        "depto_prop_id": depto_prop_id,
        "depto_otro_id": depto_otro_id,
        "SesionTest": SesionTest,
    }
    app.dependency_overrides.clear()


def _expensa_id_de(entorno, depto_id):
    db = entorno["SesionTest"]()
    fila = db.query(ExpensaDepartamento).filter_by(departamento_id=depto_id).first()
    db.close()
    return fila.expensa_id


# ------------------------------- medio de pago -------------------------------

def test_medio_pago_sin_cbu_cargado_devuelve_nulos(entorno):
    cliente, headers_admin = entorno["cliente"], entorno["headers_admin"]
    r = cliente.get(f"/api/edificios/{entorno['edificio_id']}/medio-pago", headers=headers_admin)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["cbu"] is None and cuerpo["alias_cbu"] is None
    assert "qr_base64" not in cuerpo  # sin QR — decisión final del usuario


def test_admin_carga_cbu_y_alias(entorno):
    cliente, headers_admin = entorno["cliente"], entorno["headers_admin"]
    r = cliente.patch(
        f"/api/edificios/{entorno['edificio_id']}",
        json={"cbu": "0000003100000000000001", "alias_cbu": "torre.pagos.test"},
        headers=headers_admin,
    )
    assert r.status_code == 200

    r = cliente.get(f"/api/edificios/{entorno['edificio_id']}/medio-pago", headers=headers_admin)
    cuerpo = r.json()
    assert cuerpo["cbu"] == "0000003100000000000001"
    assert cuerpo["alias_cbu"] == "torre.pagos.test"


def test_propietario_de_una_unidad_puede_ver_el_medio_de_pago(entorno):
    cliente = entorno["cliente"]
    r = cliente.get(f"/api/edificios/{entorno['edificio_id']}/medio-pago", headers=entorno["headers_prop"])
    assert r.status_code == 200


def test_propietario_ajeno_no_puede_ver_el_medio_de_pago(entorno):
    cliente = entorno["cliente"]
    r = cliente.get(f"/api/edificios/{entorno['edificio_id']}/medio-pago", headers=entorno["headers_ajeno"])
    assert r.status_code == 403


# ------------------------------- mis-departamentos -------------------------------

def test_mis_departamentos_muestra_expensa_y_saldo_completo_sin_pagos(entorno):
    cliente = entorno["cliente"]
    r = cliente.get("/api/mis-departamentos", headers=entorno["headers_prop"])
    assert r.status_code == 200
    cuerpo = r.json()
    assert len(cuerpo) == 1
    expensa = cuerpo[0]["expensas"][0]
    assert expensa["monto"] == 60000  # 60% de 100.000
    assert expensa["pagado_confirmado"] == 0
    assert expensa["saldo"] == 60000


def test_propietario_ajeno_no_tiene_departamentos(entorno):
    cliente = entorno["cliente"]
    r = cliente.get("/api/mis-departamentos", headers=entorno["headers_ajeno"])
    assert r.status_code == 200
    assert r.json() == []


# ------------------------------- registrar pago -------------------------------

def test_registrar_pago_nace_pendiente(entorno):
    cliente = entorno["cliente"]
    expensa_id = _expensa_id_de(entorno, entorno["depto_prop_id"])

    r = cliente.post(
        "/api/pagos",
        json={
            "departamento_id": entorno["depto_prop_id"], "expensa_id": expensa_id,
            "monto": 60000, "fecha": "2026-08-15", "medio_pago": "transferencia",
            "comprobante_url": "https://ejemplo.test/comprobante.jpg",
        },
        headers=entorno["headers_prop"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["estado"] == "pendiente"


def test_inquilino_tambien_puede_pagar_la_misma_unidad(entorno):
    cliente = entorno["cliente"]
    expensa_id = _expensa_id_de(entorno, entorno["depto_prop_id"])
    r = cliente.post(
        "/api/pagos",
        json={"departamento_id": entorno["depto_prop_id"], "expensa_id": expensa_id, "monto": 30000, "fecha": "2026-08-10", "medio_pago": "efectivo"},
        headers=entorno["headers_inquilino"],
    )
    assert r.status_code == 201


def test_no_se_puede_registrar_un_pago_de_un_departamento_ajeno(entorno):
    cliente = entorno["cliente"]
    expensa_id = _expensa_id_de(entorno, entorno["depto_prop_id"])
    r = cliente.post(
        "/api/pagos",
        json={"departamento_id": entorno["depto_prop_id"], "expensa_id": expensa_id, "monto": 60000, "fecha": "2026-08-15", "medio_pago": "transferencia"},
        headers=entorno["headers_ajeno"],
    )
    assert r.status_code == 403


def test_expensa_inexistente_para_el_departamento_devuelve_400(entorno):
    # Un id de expensa que no tiene ningún ExpensaDepartamento para esta
    # unidad (acá, directamente inexistente) — el pago no puede cargarse
    # contra algo que nunca se generó para ese departamento.
    cliente = entorno["cliente"]
    r = cliente.post(
        "/api/pagos",
        json={"departamento_id": entorno["depto_prop_id"], "expensa_id": 999999, "monto": 60000, "fecha": "2026-08-15", "medio_pago": "transferencia"},
        headers=entorno["headers_prop"],
    )
    assert r.status_code == 400


# ------------------------------- conciliar (PATCH estado) -------------------------------

def test_admin_confirma_un_pago_y_el_saldo_baja(entorno):
    cliente = entorno["cliente"]
    expensa_id = _expensa_id_de(entorno, entorno["depto_prop_id"])
    pago = cliente.post(
        "/api/pagos",
        json={"departamento_id": entorno["depto_prop_id"], "expensa_id": expensa_id, "monto": 60000, "fecha": "2026-08-15", "medio_pago": "transferencia"},
        headers=entorno["headers_prop"],
    ).json()

    r = cliente.patch(f"/api/pagos/{pago['id']}/estado", json={"estado": "confirmado"}, headers=entorno["headers_admin"])
    assert r.status_code == 200
    assert r.json()["estado"] == "confirmado"

    estado_cuenta = cliente.get("/api/mis-departamentos", headers=entorno["headers_prop"]).json()
    assert estado_cuenta[0]["expensas"][0]["saldo"] == 0


def test_pago_pendiente_no_descuenta_saldo(entorno):
    cliente = entorno["cliente"]
    expensa_id = _expensa_id_de(entorno, entorno["depto_prop_id"])
    cliente.post(
        "/api/pagos",
        json={"departamento_id": entorno["depto_prop_id"], "expensa_id": expensa_id, "monto": 60000, "fecha": "2026-08-15", "medio_pago": "transferencia"},
        headers=entorno["headers_prop"],
    )
    estado_cuenta = cliente.get("/api/mis-departamentos", headers=entorno["headers_prop"]).json()
    assert estado_cuenta[0]["expensas"][0]["saldo"] == 60000  # no confirmado todavía


def test_el_propio_residente_no_puede_confirmar_su_pago(entorno):
    cliente = entorno["cliente"]
    expensa_id = _expensa_id_de(entorno, entorno["depto_prop_id"])
    pago = cliente.post(
        "/api/pagos",
        json={"departamento_id": entorno["depto_prop_id"], "expensa_id": expensa_id, "monto": 60000, "fecha": "2026-08-15", "medio_pago": "transferencia"},
        headers=entorno["headers_prop"],
    ).json()

    r = cliente.patch(f"/api/pagos/{pago['id']}/estado", json={"estado": "confirmado"}, headers=entorno["headers_prop"])
    assert r.status_code == 403


def test_estado_invalido_en_el_patch_devuelve_422(entorno):
    cliente = entorno["cliente"]
    expensa_id = _expensa_id_de(entorno, entorno["depto_prop_id"])
    pago = cliente.post(
        "/api/pagos",
        json={"departamento_id": entorno["depto_prop_id"], "expensa_id": expensa_id, "monto": 60000, "fecha": "2026-08-15", "medio_pago": "transferencia"},
        headers=entorno["headers_prop"],
    ).json()

    r = cliente.patch(f"/api/pagos/{pago['id']}/estado", json={"estado": "pendiente"}, headers=entorno["headers_admin"])
    assert r.status_code == 422

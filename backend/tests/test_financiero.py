"""Tests del router financiero — POST /api/edificios/{id}/expensas."""

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

    token = cliente.post("/api/auth/login", json={"email": "admin@test.com", "password": "clave"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    respuesta = cliente.post(
        "/api/edificios",
        json={"nombre": "Torre Financiero", "direccion": "Calle 1", "cantidad_pisos": 1, "unidades_por_piso": 3},
        headers=headers,
    )
    edificio_id = respuesta.json()["id"]
    deptos = respuesta.json()["pisos"][0]["departamentos"]

    db2 = SesionTest()
    for depto, coeficiente in zip(deptos, [50, 30, 20]):
        d = db2.get(Departamento, depto["id"])
        d.coeficiente = coeficiente
    db2.add(Gasto(edificio_id=edificio_id, rubro="Limpieza", monto=60000, fecha=datetime.date(2026, 8, 5)))
    db2.add(Gasto(edificio_id=edificio_id, rubro="Seguridad", monto=40000, fecha=datetime.date(2026, 8, 20)))
    db2.commit()
    db2.close()

    yield cliente, headers, edificio_id, [d["id"] for d in deptos], SesionTest
    app.dependency_overrides.clear()


def test_generar_expensa_mensual_de_punta_a_punta(entorno):
    cliente, headers, edificio_id, deptos_ids, _ = entorno

    respuesta = cliente.post(f"/api/edificios/{edificio_id}/expensas", json={"anio": 2026, "mes": 8}, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["total"] == 100000
    rubros = {d["rubro"]: d["monto"] for d in cuerpo["detalles"]}
    assert rubros == {"Limpieza": 60000, "Seguridad": 40000}

    montos = {d["departamento_id"]: d["monto"] for d in cuerpo["por_departamento"]}
    assert montos[deptos_ids[0]] == 50000
    assert montos[deptos_ids[1]] == 30000
    assert montos[deptos_ids[2]] == 20000


def test_generar_dos_veces_el_mismo_periodo_sin_confirmar_devuelve_409(entorno):
    # Es la ÚLTIMA expensa del edificio (la única, en este caso) — pedir
    # el mismo período de nuevo sin confirmar avisa que se va a reemplazar,
    # no la bloquea de una — ver test_regenerar_la_ultima_expensa_confirmada.
    cliente, headers, edificio_id, _, _ = entorno

    r1 = cliente.post(f"/api/edificios/{edificio_id}/expensas", json={"anio": 2026, "mes": 8}, headers=headers)
    assert r1.status_code == 201

    r2 = cliente.post(f"/api/edificios/{edificio_id}/expensas", json={"anio": 2026, "mes": 8}, headers=headers)
    assert r2.status_code == 409
    assert "8/2026" in r2.json()["detail"] or "existe" in r2.json()["detail"].lower()


def test_sin_gastos_en_el_periodo_devuelve_400(entorno):
    cliente, headers, edificio_id, _, _ = entorno

    respuesta = cliente.post(f"/api/edificios/{edificio_id}/expensas", json={"anio": 2026, "mes": 1}, headers=headers)
    assert respuesta.status_code == 400


def test_propietario_no_puede_generar_expensas(entorno):
    cliente, _, edificio_id, _, _ = entorno
    token_prop = cliente.post("/api/auth/login", json={"email": "prop@test.com", "password": "clave"}).json()["access_token"]

    respuesta = cliente.post(
        f"/api/edificios/{edificio_id}/expensas", json={"anio": 2026, "mes": 8},
        headers={"Authorization": f"Bearer {token_prop}"},
    )
    assert respuesta.status_code == 403


def test_edificio_inexistente_devuelve_404(entorno):
    cliente, headers, _, _, _ = entorno
    respuesta = cliente.post("/api/edificios/9999/expensas", json={"anio": 2026, "mes": 8}, headers=headers)
    assert respuesta.status_code == 404


def test_expensa_ya_generada_no_cambia_si_el_coeficiente_cambia_despues(entorno):
    # Confirma la decisión de diseño de Prorrateo.md sección 6: una
    # expensa emitida es una foto fija, no se recalcula con datos nuevos.
    cliente, headers, edificio_id, deptos_ids, SesionTest = entorno

    respuesta = cliente.post(f"/api/edificios/{edificio_id}/expensas", json={"anio": 2026, "mes": 8}, headers=headers)
    monto_original = next(d["monto"] for d in respuesta.json()["por_departamento"] if d["departamento_id"] == deptos_ids[0])
    assert monto_original == 50000

    db = SesionTest()
    depto = db.get(Departamento, deptos_ids[0])
    depto.coeficiente = 90  # cambia el coeficiente DESPUÉS de emitida la expensa
    db.commit()
    db.close()

    db = SesionTest()
    fila = db.query(ExpensaDepartamento).filter(ExpensaDepartamento.departamento_id == deptos_ids[0]).first()
    assert float(fila.monto) == 50000  # la expensa vieja no cambió
    db.close()


# ------------------ Regenerar la última expensa (excepción a la foto fija) ------------------

def test_regenerar_la_ultima_expensa_confirmada(entorno):
    # Se corrige un gasto (o se agrega uno nuevo) DESPUÉS de generar la
    # expensa, y hay que volver a liquidar ese mismo período — pedido
    # explícito del usuario, con confirmación obligatoria.
    cliente, headers, edificio_id, deptos_ids, SesionTest = entorno

    primera = cliente.post(f"/api/edificios/{edificio_id}/expensas", json={"anio": 2026, "mes": 8}, headers=headers).json()
    assert primera["total"] == 100000

    db = SesionTest()
    db.add(Gasto(edificio_id=edificio_id, rubro="Ascensor", monto=50000, fecha=datetime.date(2026, 8, 25)))
    db.commit()
    db.close()

    r = cliente.post(
        f"/api/edificios/{edificio_id}/expensas",
        json={"anio": 2026, "mes": 8, "confirmar_reemplazo": True},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    regenerada = r.json()
    assert regenerada["id"] == primera["id"]  # mismo registro, no uno nuevo
    assert regenerada["total"] == 150000
    montos = {d["departamento_id"]: d["monto"] for d in regenerada["por_departamento"]}
    assert montos[deptos_ids[0]] == 75000  # 50% de 150.000


def test_regenerar_sin_confirmar_no_borra_la_expensa_existente(entorno):
    cliente, headers, edificio_id, _, _ = entorno
    primera = cliente.post(f"/api/edificios/{edificio_id}/expensas", json={"anio": 2026, "mes": 8}, headers=headers).json()

    r = cliente.post(f"/api/edificios/{edificio_id}/expensas", json={"anio": 2026, "mes": 8}, headers=headers)
    assert r.status_code == 409

    aun_existe = cliente.get(f"/api/edificios/{edificio_id}/expensas/{primera['id']}", headers=headers)
    assert aun_existe.status_code == 200
    assert aun_existe.json()["total"] == 100000  # intacta


def test_no_se_puede_regenerar_una_expensa_que_no_es_la_ultima(entorno):
    cliente, headers, edificio_id, _, SesionTest = entorno
    cliente.post(f"/api/edificios/{edificio_id}/expensas", json={"anio": 2026, "mes": 8}, headers=headers)

    db = SesionTest()
    db.add(Gasto(edificio_id=edificio_id, rubro="Limpieza", monto=30000, fecha=datetime.date(2026, 9, 5)))
    db.commit()
    db.close()
    cliente.post(f"/api/edificios/{edificio_id}/expensas", json={"anio": 2026, "mes": 9}, headers=headers)

    # Agosto ya no es la última (septiembre sí) — ni siquiera confirmando se puede regenerar.
    r = cliente.post(
        f"/api/edificios/{edificio_id}/expensas",
        json={"anio": 2026, "mes": 8, "confirmar_reemplazo": True},
        headers=headers,
    )
    assert r.status_code == 400
    assert "última" in r.json()["detail"].lower() or "no se puede regenerar" in r.json()["detail"].lower()


def test_regenerar_no_invalida_un_pago_ya_cargado(entorno):
    # El Pago referencia Expensa.id directo — al reusar el mismo id en la
    # regeneración, un pago ya cargado antes de regenerar tiene que seguir
    # siendo válido y visible después.
    cliente, headers, edificio_id, deptos_ids, SesionTest = entorno
    primera = cliente.post(f"/api/edificios/{edificio_id}/expensas", json={"anio": 2026, "mes": 8}, headers=headers).json()

    db = SesionTest()
    db.get(Departamento, deptos_ids[0]).propietario_id = (
        db.query(Usuario).filter_by(email="prop@test.com").first().id
    )
    db.commit()
    db.close()

    token_prop = cliente.post("/api/auth/login", json={"email": "prop@test.com", "password": "clave"}).json()["access_token"]
    headers_prop = {"Authorization": f"Bearer {token_prop}"}
    pago = cliente.post(
        "/api/pagos",
        json={
            "departamento_id": deptos_ids[0], "expensa_id": primera["id"],
            "monto": 50000, "fecha": "2026-08-15", "medio_pago": "transferencia",
        },
        headers=headers_prop,
    ).json()

    cliente.post(
        f"/api/edificios/{edificio_id}/expensas",
        json={"anio": 2026, "mes": 8, "confirmar_reemplazo": True},
        headers=headers,
    )

    # El pago sigue apuntando a un id de expensa real (no quedó huérfano).
    estado_cuenta = cliente.get("/api/mis-departamentos", headers=headers_prop).json()
    expensa_vista = next(e for d in estado_cuenta for e in d["expensas"] if e["expensa_id"] == primera["id"])
    assert expensa_vista["pendiente_de_confirmacion"] == 50000
    assert pago["expensa_id"] == primera["id"]

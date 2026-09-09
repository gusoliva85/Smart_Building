"""Tests del CRUD anidado bajo edificio: Gastos, Fondos, Caja,
Presupuestos y Facturas (Documento General 6.4-6.8)."""

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
    db.add(Usuario(nombre="Encargado", email="encargado@test.com", password_hash=hashear_password("clave"), rol="encargado"))
    db.add(Usuario(nombre="Prop", email="prop@test.com", password_hash=hashear_password("clave"), rol="propietario"))
    db.commit()
    encargado_id = db.query(Usuario).filter_by(email="encargado@test.com").first().id
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
        json={"nombre": "Torre CRUD", "direccion": "Calle 1", "cantidad_pisos": 1, "unidades_por_piso": 1},
        headers=headers_admin,
    )
    edificio_id = r.json()["id"]

    yield {
        "cliente": cliente, "headers_admin": headers_admin,
        "headers_prop": {"Authorization": f"Bearer {_token('prop@test.com')}"},
        "edificio_id": edificio_id, "encargado_id": encargado_id,
    }
    app.dependency_overrides.clear()


# --------------------------------- Gastos ---------------------------------

def test_crear_y_listar_gasto(entorno):
    cliente, headers = entorno["cliente"], entorno["headers_admin"]
    r = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/gastos",
        json={"rubro": "Limpieza", "monto": 15000, "fecha": "2026-08-05", "descripcion": "Insumos"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["rubro"] == "Limpieza"

    r = cliente.get(f"/api/edificios/{entorno['edificio_id']}/gastos", headers=headers)
    assert len(r.json()) == 1


def test_filtrar_gastos_por_periodo(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    cliente.post(f"/api/edificios/{eid}/gastos", json={"rubro": "Limpieza", "monto": 1000, "fecha": "2026-08-05"}, headers=headers)
    cliente.post(f"/api/edificios/{eid}/gastos", json={"rubro": "Seguridad", "monto": 2000, "fecha": "2026-07-05"}, headers=headers)

    r = cliente.get(f"/api/edificios/{eid}/gastos?anio=2026&mes=8", headers=headers)
    cuerpo = r.json()
    assert len(cuerpo) == 1
    assert cuerpo[0]["rubro"] == "Limpieza"


def test_propietario_no_puede_crear_gasto(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/gastos",
        json={"rubro": "Limpieza", "monto": 1000, "fecha": "2026-08-05"},
        headers=entorno["headers_prop"],
    )
    assert r.status_code == 403


def test_editar_gasto_corrige_solo_lo_enviado(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    gasto = cliente.post(
        f"/api/edificios/{eid}/gastos",
        json={"rubro": "Limpieza", "monto": 1000, "fecha": "2026-08-05", "descripcion": "Insumos"},
        headers=headers,
    ).json()

    r = cliente.patch(
        f"/api/edificios/{eid}/gastos/{gasto['id']}",
        json={"monto": 1500},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["monto"] == 1500
    assert cuerpo["rubro"] == "Limpieza"  # no se tocó
    assert cuerpo["descripcion"] == "Insumos"  # no se tocó


def test_editar_gasto_puede_limpiar_la_descripcion(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    gasto = cliente.post(
        f"/api/edificios/{eid}/gastos",
        json={"rubro": "Limpieza", "monto": 1000, "fecha": "2026-08-05", "descripcion": "Insumos"},
        headers=headers,
    ).json()

    r = cliente.patch(
        f"/api/edificios/{eid}/gastos/{gasto['id']}",
        json={"descripcion": None},
        headers=headers,
    )
    assert r.json()["descripcion"] is None


def test_editar_gasto_de_otro_edificio_devuelve_404(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    otro_edificio_id = cliente.post(
        "/api/edificios",
        json={"nombre": "Torre Ajena", "direccion": "Calle 2", "cantidad_pisos": 1, "unidades_por_piso": 1},
        headers=headers,
    ).json()["id"]
    gasto = cliente.post(
        f"/api/edificios/{eid}/gastos",
        json={"rubro": "Limpieza", "monto": 1000, "fecha": "2026-08-05"},
        headers=headers,
    ).json()

    r = cliente.patch(f"/api/edificios/{otro_edificio_id}/gastos/{gasto['id']}", json={"monto": 500}, headers=headers)
    assert r.status_code == 404


def test_editar_gasto_monto_invalido_devuelve_422(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    gasto = cliente.post(
        f"/api/edificios/{eid}/gastos",
        json={"rubro": "Limpieza", "monto": 1000, "fecha": "2026-08-05"},
        headers=headers,
    ).json()

    r = cliente.patch(f"/api/edificios/{eid}/gastos/{gasto['id']}", json={"monto": -50}, headers=headers)
    assert r.status_code == 422


def test_propietario_no_puede_editar_gasto(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    gasto = cliente.post(
        f"/api/edificios/{eid}/gastos",
        json={"rubro": "Limpieza", "monto": 1000, "fecha": "2026-08-05"},
        headers=headers,
    ).json()

    r = cliente.patch(f"/api/edificios/{eid}/gastos/{gasto['id']}", json={"monto": 500}, headers=entorno["headers_prop"])
    assert r.status_code == 403


def test_editar_gasto_no_altera_una_expensa_ya_generada(entorno):
    # Documento Técnico / Prorrateo.md sección 6: ExpensaDetalle es una foto
    # fija — corregir el Gasto de origen después no reescribe lo ya emitido.
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    cliente.post(f"/api/edificios/{eid}/coeficientes/auto", json={"criterio": "partes_iguales"}, headers=headers)
    gasto = cliente.post(
        f"/api/edificios/{eid}/gastos",
        json={"rubro": "Limpieza", "monto": 1000, "fecha": "2026-08-05"},
        headers=headers,
    ).json()
    expensa = cliente.post(f"/api/edificios/{eid}/expensas", json={"anio": 2026, "mes": 8}, headers=headers).json()
    assert expensa["total"] == 1000

    cliente.patch(f"/api/edificios/{eid}/gastos/{gasto['id']}", json={"monto": 5000}, headers=headers)

    expensa_recargada = cliente.get(f"/api/edificios/{eid}/expensas/{expensa['id']}", headers=headers).json()
    assert expensa_recargada["total"] == 1000  # sigue como se emitió, no 5000


# --------------------------------- Fondos ---------------------------------

def test_crear_fondo_con_movimientos_y_saldo_calculado(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    r = cliente.post(f"/api/edificios/{eid}/fondos", json={"nombre": "Fondo de Reserva"}, headers=headers)
    assert r.status_code == 201
    fondo_id = r.json()["id"]
    assert r.json()["saldo"] == 0

    cliente.post(f"/api/edificios/{eid}/fondos/{fondo_id}/movimientos", json={"tipo": "ingreso", "monto": 50000}, headers=headers)
    cliente.post(f"/api/edificios/{eid}/fondos/{fondo_id}/movimientos", json={"tipo": "egreso", "monto": 12000}, headers=headers)

    r = cliente.get(f"/api/edificios/{eid}/fondos", headers=headers)
    assert r.json()[0]["saldo"] == 38000

    r = cliente.get(f"/api/edificios/{eid}/fondos/{fondo_id}/movimientos", headers=headers)
    assert len(r.json()) == 2


def test_movimiento_de_fondo_de_otro_edificio_devuelve_404(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    r2 = cliente.post(
        "/api/edificios", json={"nombre": "Torre Ajena", "direccion": "Calle 2", "cantidad_pisos": 1, "unidades_por_piso": 1},
        headers=headers,
    )
    eid2 = r2.json()["id"]
    fondo = cliente.post(f"/api/edificios/{eid2}/fondos", json={"nombre": "Fondo Ajeno"}, headers=headers).json()

    r = cliente.post(f"/api/edificios/{eid}/fondos/{fondo['id']}/movimientos", json={"tipo": "ingreso", "monto": 1000}, headers=headers)
    assert r.status_code == 404


def test_tipo_de_movimiento_invalido_devuelve_422(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    fondo = cliente.post(f"/api/edificios/{eid}/fondos", json={"nombre": "Fondo X"}, headers=headers).json()
    r = cliente.post(f"/api/edificios/{eid}/fondos/{fondo['id']}/movimientos", json={"tipo": "transferencia", "monto": 1000}, headers=headers)
    assert r.status_code == 422


# ---------------------------------- Caja ----------------------------------

def test_crear_caja_y_agregar_movimientos(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    r = cliente.post(f"/api/edificios/{eid}/caja", json={"responsable_id": entorno["encargado_id"], "monto_fijo": 20000}, headers=headers)
    assert r.status_code == 201
    assert r.json()["saldo"] == 0

    cliente.post(f"/api/edificios/{eid}/caja/movimientos", json={"tipo": "egreso", "monto": 3000, "descripcion": "Insumos"}, headers=headers)
    cliente.post(f"/api/edificios/{eid}/caja/movimientos", json={"tipo": "ingreso", "monto": 3000, "descripcion": "Reposición"}, headers=headers)

    r = cliente.get(f"/api/edificios/{eid}/caja", headers=headers)
    assert r.json()["saldo"] == 0

    r = cliente.get(f"/api/edificios/{eid}/caja/movimientos", headers=headers)
    assert len(r.json()) == 2


def test_no_se_puede_crear_dos_cajas_para_el_mismo_edificio(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    cliente.post(f"/api/edificios/{eid}/caja", json={"responsable_id": entorno["encargado_id"], "monto_fijo": 20000}, headers=headers)
    r = cliente.post(f"/api/edificios/{eid}/caja", json={"responsable_id": entorno["encargado_id"], "monto_fijo": 10000}, headers=headers)
    assert r.status_code == 400


def test_caja_inexistente_devuelve_404(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    r = cliente.get(f"/api/edificios/{eid}/caja", headers=headers)
    assert r.status_code == 404


def test_configurar_caja_cambia_monto_fijo(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    cliente.post(f"/api/edificios/{eid}/caja", json={"responsable_id": entorno["encargado_id"], "monto_fijo": 20000}, headers=headers)
    r = cliente.patch(f"/api/edificios/{eid}/caja", json={"monto_fijo": 30000}, headers=headers)
    assert r.status_code == 200
    assert r.json()["monto_fijo"] == 30000


# ------------------------------ Presupuestos ------------------------------

def test_crear_presupuesto_nace_pendiente(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    r = cliente.post(f"/api/edificios/{eid}/presupuestos", json={"descripcion": "Pintura", "monto": 50000}, headers=headers)
    assert r.status_code == 201
    assert r.json()["estado"] == "pendiente"
    assert r.json()["gasto_id"] is None


def test_aprobar_presupuesto_lo_vincula_a_un_gasto(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    presupuesto = cliente.post(f"/api/edificios/{eid}/presupuestos", json={"descripcion": "Pintura", "monto": 50000}, headers=headers).json()
    gasto = cliente.post(f"/api/edificios/{eid}/gastos", json={"rubro": "Mantenimiento", "monto": 50000, "fecha": "2026-08-10"}, headers=headers).json()

    r = cliente.patch(
        f"/api/edificios/{eid}/presupuestos/{presupuesto['id']}/estado",
        json={"estado": "aprobado", "gasto_id": gasto["id"]},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "aprobado"
    assert r.json()["gasto_id"] == gasto["id"]


def test_rechazar_presupuesto_sin_gasto(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    presupuesto = cliente.post(f"/api/edificios/{eid}/presupuestos", json={"descripcion": "Pintura", "monto": 50000}, headers=headers).json()
    r = cliente.patch(f"/api/edificios/{eid}/presupuestos/{presupuesto['id']}/estado", json={"estado": "rechazado"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "rechazado"


def test_aprobar_presupuesto_con_gasto_de_otro_edificio_devuelve_400(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    presupuesto = cliente.post(f"/api/edificios/{eid}/presupuestos", json={"descripcion": "Pintura", "monto": 50000}, headers=headers).json()
    eid2 = cliente.post(
        "/api/edificios", json={"nombre": "Torre Ajena 2", "direccion": "Calle 3", "cantidad_pisos": 1, "unidades_por_piso": 1},
        headers=headers,
    ).json()["id"]
    gasto_ajeno = cliente.post(f"/api/edificios/{eid2}/gastos", json={"rubro": "Mantenimiento", "monto": 50000, "fecha": "2026-08-10"}, headers=headers).json()

    r = cliente.patch(
        f"/api/edificios/{eid}/presupuestos/{presupuesto['id']}/estado",
        json={"estado": "aprobado", "gasto_id": gasto_ajeno["id"]},
        headers=headers,
    )
    assert r.status_code == 400


def test_estado_de_presupuesto_invalido_devuelve_422(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    presupuesto = cliente.post(f"/api/edificios/{eid}/presupuestos", json={"descripcion": "Pintura", "monto": 50000}, headers=headers).json()
    r = cliente.patch(f"/api/edificios/{eid}/presupuestos/{presupuesto['id']}/estado", json={"estado": "pendiente"}, headers=headers)
    assert r.status_code == 422


# -------------------------------- Facturas --------------------------------

def test_crear_y_listar_factura_vinculada_a_su_gasto(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    gasto = cliente.post(f"/api/edificios/{eid}/gastos", json={"rubro": "Mantenimiento", "monto": 50000, "fecha": "2026-08-10"}, headers=headers).json()

    r = cliente.post(
        f"/api/edificios/{eid}/facturas",
        json={"gasto_id": gasto["id"], "numero": "B 0001-00000123", "monto": 50000},
        headers=headers,
    )
    assert r.status_code == 201

    r = cliente.get(f"/api/edificios/{eid}/facturas", headers=headers)
    assert len(r.json()) == 1
    assert r.json()[0]["numero"] == "B 0001-00000123"


def test_factura_con_gasto_de_otro_edificio_devuelve_400(entorno):
    cliente, headers, eid = entorno["cliente"], entorno["headers_admin"], entorno["edificio_id"]
    eid2 = cliente.post(
        "/api/edificios", json={"nombre": "Torre Ajena 3", "direccion": "Calle 4", "cantidad_pisos": 1, "unidades_por_piso": 1},
        headers=headers,
    ).json()["id"]
    gasto_ajeno = cliente.post(f"/api/edificios/{eid2}/gastos", json={"rubro": "Mantenimiento", "monto": 50000, "fecha": "2026-08-10"}, headers=headers).json()

    r = cliente.post(
        f"/api/edificios/{eid}/facturas",
        json={"gasto_id": gasto_ajeno["id"], "numero": "B 0001-1", "monto": 50000},
        headers=headers,
    )
    assert r.status_code == 400

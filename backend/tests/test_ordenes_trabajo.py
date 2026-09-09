"""Tests de integración de la generación de una OrdenTrabajo desde un
Reclamo (`routers/ordentrabajo.py`), y de `sincronizar_reclamo_al_resolver_ot()`
— probada directo (llamándola a mano), porque el endpoint real que cambia
el estado de una OT todavía no existe (es la próxima tarea de la fase)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hashear_password
from app.database import Base, obtener_db
from app.main import app
from app.models.edificio import Cochera, Departamento, Edificio, EspacioComun, Piso
from app.models.ordentrabajo import OrdenTrabajo, OtEvidencia
from app.models.reclamo import Reclamo, ReclamoComentario, ReclamoFoto
from app.models.usuario import Usuario
from app.routers.ordentrabajo import sincronizar_reclamo_al_resolver_ot


@pytest.fixture()
def entorno():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[
        Usuario.__table__, Edificio.__table__, Piso.__table__, Departamento.__table__,
        Cochera.__table__, EspacioComun.__table__, Reclamo.__table__, ReclamoFoto.__table__,
        ReclamoComentario.__table__, OrdenTrabajo.__table__, OtEvidencia.__table__,
    ])
    SesionTest = sessionmaker(bind=engine)

    db = SesionTest()
    admin_general = Usuario(nombre="Admin", email="admin@test.com", password_hash=hashear_password("clave"), rol="admin_general")
    encargado = Usuario(nombre="Cami", email="cami@test.com", password_hash=hashear_password("clave"), rol="encargado")
    otro_encargado = Usuario(nombre="Dani", email="dani@test.com", password_hash=hashear_password("clave"), rol="encargado")
    propietario = Usuario(nombre="Prop", email="prop@test.com", password_hash=hashear_password("clave"), rol="propietario")
    db.add_all([admin_general, encargado, otro_encargado, propietario])
    db.commit()
    ids_usuarios = {u.email: u.id for u in [admin_general, encargado, otro_encargado, propietario]}
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
        json={"nombre": "Torre OT", "direccion": "Calle 1", "cantidad_pisos": 1, "unidades_por_piso": 2},
        headers=headers_admin,
    )
    edificio_id = r.json()["id"]
    depto_id = r.json()["pisos"][0]["departamentos"][0]["id"]
    cliente.patch(f"/api/edificios/{edificio_id}", json={"encargado_id": ids_usuarios["cami@test.com"]}, headers=headers_admin)

    db2 = SesionTest()
    db2.get(Departamento, depto_id).propietario_id = ids_usuarios["prop@test.com"]
    db2.commit()
    db2.close()

    headers_encargado = {"Authorization": f"Bearer {_token('cami@test.com')}"}
    headers_prop = {"Authorization": f"Bearer {_token('prop@test.com')}"}

    reclamo_id = cliente.post(
        f"/api/edificios/{edificio_id}/reclamos",
        json={"departamento_id": depto_id, "descripcion": "Pérdida de agua", "prioridad": "medio"},
        headers=headers_prop,
    ).json()["id"]

    yield {
        "cliente": cliente,
        "SesionTest": SesionTest,
        "headers_admin": headers_admin,
        "headers_encargado": headers_encargado,
        "headers_otro_encargado": {"Authorization": f"Bearer {_token('dani@test.com')}"},
        "headers_prop": headers_prop,
        "edificio_id": edificio_id,
        "depto_id": depto_id,
        "reclamo_id": reclamo_id,
        "id_encargado": ids_usuarios["cami@test.com"],
        "id_prop": ids_usuarios["prop@test.com"],
    }
    app.dependency_overrides.clear()


# ------------------------------- generación desde reclamo -------------------------------

def test_gestion_genera_ot_y_reclamo_pasa_a_asignado(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "correctivo"},
        headers=entorno["headers_encargado"],
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["estado"] == "pendiente"
    assert cuerpo["reclamo_id"] == entorno["reclamo_id"]
    assert cuerpo["prioridad"] == "medio"  # heredada del reclamo
    assert cuerpo["descripcion"] == "Pérdida de agua"  # heredada del reclamo

    reclamo = cliente.get(f"/api/reclamos/{entorno['reclamo_id']}", headers=entorno["headers_encargado"]).json()
    assert reclamo["estado"] == "asignado"


def test_prioridad_y_descripcion_explicitas_no_se_pisan_por_las_del_reclamo(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "correctivo", "prioridad": "critico", "descripcion": "Cambiar la válvula"},
        headers=entorno["headers_encargado"],
    )
    assert r.status_code == 201
    assert r.json()["prioridad"] == "critico"
    assert r.json()["descripcion"] == "Cambiar la válvula"


def test_creador_del_reclamo_no_puede_generar_ot(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "correctivo"},
        headers=entorno["headers_prop"],
    )
    assert r.status_code == 403


def test_encargado_de_otro_edificio_no_puede_generar_ot(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "correctivo"},
        headers=entorno["headers_otro_encargado"],
    )
    assert r.status_code == 403


def test_tipo_invalido_devuelve_422(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "no_existe"},
        headers=entorno["headers_encargado"],
    )
    assert r.status_code == 422


def test_encargado_id_con_rol_incorrecto_devuelve_400(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "correctivo", "encargado_id": entorno["id_prop"]},
        headers=entorno["headers_encargado"],
    )
    assert r.status_code == 400


def test_encargado_id_real_se_asigna(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "correctivo", "encargado_id": entorno["id_encargado"]},
        headers=entorno["headers_encargado"],
    )
    assert r.status_code == 201
    assert r.json()["encargado_id"] == entorno["id_encargado"]


def test_no_se_puede_generar_una_segunda_ot_activa_para_el_mismo_reclamo(entorno):
    cliente = entorno["cliente"]
    cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "correctivo"},
        headers=entorno["headers_encargado"],
    )
    r = cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "preventivo"},
        headers=entorno["headers_encargado"],
    )
    assert r.status_code == 400


def test_no_se_puede_generar_ot_para_reclamo_resuelto_o_cerrado(entorno):
    cliente = entorno["cliente"]
    for estado in ("asignado", "en_curso", "resuelto"):
        cliente.patch(f"/api/reclamos/{entorno['reclamo_id']}/estado", json={"estado": estado}, headers=entorno["headers_encargado"])

    r = cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "correctivo"},
        headers=entorno["headers_encargado"],
    )
    assert r.status_code == 400

    cliente.patch(f"/api/reclamos/{entorno['reclamo_id']}/estado", json={"estado": "cerrado"}, headers=entorno["headers_encargado"])
    r2 = cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "correctivo"},
        headers=entorno["headers_encargado"],
    )
    assert r2.status_code == 400


def test_reclamo_inexistente_devuelve_404(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        "/api/reclamos/99999/orden-trabajo",
        json={"tipo": "correctivo"},
        headers=entorno["headers_encargado"],
    )
    assert r.status_code == 404


def test_ot_ya_resuelta_no_bloquea_una_ot_nueva_para_el_mismo_reclamo(entorno):
    """Un reclamo reabierto (resuelto → en_curso) puede necesitar una OT
    nueva — la anterior, ya resuelta, no cuenta como 'activa'."""
    cliente = entorno["cliente"]
    SesionTest = entorno["SesionTest"]

    primera_ot_id = cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "correctivo"},
        headers=entorno["headers_encargado"],
    ).json()["id"]

    db = SesionTest()
    db.get(OrdenTrabajo, primera_ot_id).estado = "resuelta"
    db.commit()
    db.close()

    for estado in ("en_curso", "resuelto"):
        cliente.patch(f"/api/reclamos/{entorno['reclamo_id']}/estado", json={"estado": estado}, headers=entorno["headers_encargado"])
    cliente.patch(f"/api/reclamos/{entorno['reclamo_id']}/estado", json={"estado": "en_curso"}, headers=entorno["headers_prop"])

    r = cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "correctivo"},
        headers=entorno["headers_encargado"],
    )
    assert r.status_code == 201


# ------------------------------- sincronizar_reclamo_al_resolver_ot -------------------------------

def test_sincronizar_pasa_el_reclamo_a_resuelto(entorno):
    cliente = entorno["cliente"]
    SesionTest = entorno["SesionTest"]

    ot_id = cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "correctivo"},
        headers=entorno["headers_encargado"],
    ).json()["id"]
    cliente.patch(f"/api/reclamos/{entorno['reclamo_id']}/estado", json={"estado": "en_curso"}, headers=entorno["headers_encargado"])

    db = SesionTest()
    orden = db.get(OrdenTrabajo, ot_id)
    orden.estado = "resuelta"
    sincronizar_reclamo_al_resolver_ot(orden, db)
    db.commit()
    db.close()

    reclamo = cliente.get(f"/api/reclamos/{entorno['reclamo_id']}", headers=entorno["headers_encargado"]).json()
    assert reclamo["estado"] == "resuelto"


def test_sincronizar_no_fuerza_si_el_reclamo_ya_esta_cerrado(entorno):
    cliente = entorno["cliente"]
    SesionTest = entorno["SesionTest"]

    ot_id = cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "correctivo"},
        headers=entorno["headers_encargado"],
    ).json()["id"]
    for estado in ("en_curso", "resuelto", "cerrado"):
        cliente.patch(f"/api/reclamos/{entorno['reclamo_id']}/estado", json={"estado": estado}, headers=entorno["headers_encargado"])

    db = SesionTest()
    orden = db.get(OrdenTrabajo, ot_id)
    orden.estado = "resuelta"
    sincronizar_reclamo_al_resolver_ot(orden, db)
    db.commit()

    reclamo = db.get(Reclamo, entorno["reclamo_id"])
    assert reclamo.estado == "cerrado"
    db.close()


def test_sincronizar_no_hace_nada_si_la_ot_no_tiene_reclamo(entorno):
    SesionTest = entorno["SesionTest"]
    db = SesionTest()
    orden_manual = OrdenTrabajo(
        edificio_id=entorno["edificio_id"], tipo="preventivo", prioridad="leve", estado="resuelta",
    )
    db.add(orden_manual)
    db.commit()

    # No debe lanzar ni tocar nada — simplemente no hay reclamo que sincronizar.
    sincronizar_reclamo_al_resolver_ot(orden_manual, db)
    db.commit()
    db.close()

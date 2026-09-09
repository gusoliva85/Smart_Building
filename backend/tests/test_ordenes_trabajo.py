"""Tests de integración del router de órdenes de trabajo
(`routers/ordentrabajo.py`): generación desde un reclamo, creación
manual, listado, detalle, asignación, cambio de estado y evidencia."""

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
        "id_otro_encargado": ids_usuarios["dani@test.com"],
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


# ------------------------------- creación manual -------------------------------

def test_gestion_crea_ot_manual_sin_reclamo(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve", "descripcion": "Service anual del ascensor"},
        headers=entorno["headers_encargado"],
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["estado"] == "pendiente"
    assert cuerpo["reclamo_id"] is None


def test_propietario_no_puede_crear_ot_manual(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve"},
        headers=entorno["headers_prop"],
    )
    assert r.status_code == 403


def test_ot_manual_con_espacio_comun_de_otro_edificio_devuelve_400(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve", "espacio_comun_id": 99999},
        headers=entorno["headers_encargado"],
    )
    assert r.status_code == 400


def test_ot_manual_con_encargado_de_rol_incorrecto_devuelve_400(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve", "encargado_id": entorno["id_prop"]},
        headers=entorno["headers_encargado"],
    )
    assert r.status_code == 400


# ------------------------------- listado y detalle -------------------------------

def test_listar_ordenes_trabajo_del_edificio(entorno):
    cliente = entorno["cliente"]
    cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve"},
        headers=entorno["headers_encargado"],
    )
    cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "correctivo"},
        headers=entorno["headers_encargado"],
    )
    r = cliente.get(f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo", headers=entorno["headers_encargado"])
    assert r.status_code == 200
    assert len(r.json()) == 2

    r_filtrado = cliente.get(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo?tipo=preventivo", headers=entorno["headers_encargado"]
    )
    assert len(r_filtrado.json()) == 1


def test_propietario_no_puede_listar_ordenes_trabajo(entorno):
    cliente = entorno["cliente"]
    r = cliente.get(f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo", headers=entorno["headers_prop"])
    assert r.status_code == 403


def test_gestion_ve_el_detalle_un_tercero_no(entorno):
    cliente = entorno["cliente"]
    ot_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve"},
        headers=entorno["headers_encargado"],
    ).json()["id"]

    assert cliente.get(f"/api/ordenes-trabajo/{ot_id}", headers=entorno["headers_encargado"]).status_code == 200
    assert cliente.get(f"/api/ordenes-trabajo/{ot_id}", headers=entorno["headers_prop"]).status_code == 403
    assert cliente.get(f"/api/ordenes-trabajo/{ot_id}", headers=entorno["headers_otro_encargado"]).status_code == 403


def test_orden_trabajo_inexistente_devuelve_404(entorno):
    cliente = entorno["cliente"]
    assert cliente.get("/api/ordenes-trabajo/99999", headers=entorno["headers_admin"]).status_code == 404


# ------------------------------- asignación -------------------------------

def test_asignar_encargado_a_una_ot_sin_asignar(entorno):
    cliente = entorno["cliente"]
    ot_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve"},
        headers=entorno["headers_encargado"],
    ).json()["id"]

    r = cliente.patch(
        f"/api/ordenes-trabajo/{ot_id}/asignacion", json={"encargado_id": entorno["id_encargado"]}, headers=entorno["headers_encargado"]
    )
    assert r.status_code == 200
    assert r.json()["encargado_id"] == entorno["id_encargado"]


def test_desasignar_mandando_null_explicito(entorno):
    cliente = entorno["cliente"]
    ot_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve", "encargado_id": entorno["id_encargado"]},
        headers=entorno["headers_encargado"],
    ).json()["id"]

    r = cliente.patch(f"/api/ordenes-trabajo/{ot_id}/asignacion", json={"encargado_id": None}, headers=entorno["headers_encargado"])
    assert r.status_code == 200
    assert r.json()["encargado_id"] is None


def test_no_mandar_un_campo_lo_deja_como_esta(entorno):
    cliente = entorno["cliente"]
    ot_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve", "encargado_id": entorno["id_encargado"]},
        headers=entorno["headers_encargado"],
    ).json()["id"]

    r = cliente.patch(f"/api/ordenes-trabajo/{ot_id}/asignacion", json={"proveedor_id": 42}, headers=entorno["headers_encargado"])
    assert r.status_code == 200
    assert r.json()["encargado_id"] == entorno["id_encargado"]
    assert r.json()["proveedor_id"] == 42


def test_no_se_puede_reasignar_una_ot_ya_resuelta(entorno):
    cliente = entorno["cliente"]
    ot_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve", "encargado_id": entorno["id_encargado"]},
        headers=entorno["headers_encargado"],
    ).json()["id"]
    cliente.patch(f"/api/ordenes-trabajo/{ot_id}/estado", json={"estado": "en_curso"}, headers=entorno["headers_encargado"])
    cliente.patch(f"/api/ordenes-trabajo/{ot_id}/estado", json={"estado": "resuelta"}, headers=entorno["headers_encargado"])

    r = cliente.patch(f"/api/ordenes-trabajo/{ot_id}/asignacion", json={"encargado_id": None}, headers=entorno["headers_encargado"])
    assert r.status_code == 400


# ------------------------------- cambio de estado -------------------------------

def test_no_se_puede_pasar_a_en_curso_sin_nadie_asignado(entorno):
    cliente = entorno["cliente"]
    ot_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve"},
        headers=entorno["headers_encargado"],
    ).json()["id"]

    r = cliente.patch(f"/api/ordenes-trabajo/{ot_id}/estado", json={"estado": "en_curso"}, headers=entorno["headers_encargado"])
    assert r.status_code == 400


def test_pasar_a_en_curso_con_proveedor_suelto_alcanza(entorno):
    cliente = entorno["cliente"]
    ot_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve", "proveedor_id": 7},
        headers=entorno["headers_encargado"],
    ).json()["id"]

    r = cliente.patch(f"/api/ordenes-trabajo/{ot_id}/estado", json={"estado": "en_curso"}, headers=entorno["headers_encargado"])
    assert r.status_code == 200
    assert r.json()["fecha_inicio"] is not None


def test_transicion_invalida_de_ot_devuelve_400(entorno):
    cliente = entorno["cliente"]
    ot_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve", "encargado_id": entorno["id_encargado"]},
        headers=entorno["headers_encargado"],
    ).json()["id"]

    r = cliente.patch(f"/api/ordenes-trabajo/{ot_id}/estado", json={"estado": "resuelta"}, headers=entorno["headers_encargado"])
    assert r.status_code == 400


def test_estado_ot_invalido_devuelve_422(entorno):
    cliente = entorno["cliente"]
    ot_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve"},
        headers=entorno["headers_encargado"],
    ).json()["id"]
    r = cliente.patch(f"/api/ordenes-trabajo/{ot_id}/estado", json={"estado": "cancelada"}, headers=entorno["headers_encargado"])
    assert r.status_code == 422


def test_resolver_ot_carga_costo_y_fecha_de_cierre(entorno):
    cliente = entorno["cliente"]
    ot_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve", "encargado_id": entorno["id_encargado"]},
        headers=entorno["headers_encargado"],
    ).json()["id"]
    cliente.patch(f"/api/ordenes-trabajo/{ot_id}/estado", json={"estado": "en_curso"}, headers=entorno["headers_encargado"])

    r = cliente.patch(f"/api/ordenes-trabajo/{ot_id}/estado", json={"estado": "resuelta", "costo": 15000.50}, headers=entorno["headers_encargado"])
    assert r.status_code == 200
    assert float(r.json()["costo"]) == 15000.50
    assert r.json()["fecha_cierre"] is not None


def test_resolver_la_ot_de_un_reclamo_pasa_el_reclamo_a_resuelto(entorno):
    cliente = entorno["cliente"]
    ot_id = cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "correctivo", "encargado_id": entorno["id_encargado"]},
        headers=entorno["headers_encargado"],
    ).json()["id"]
    cliente.patch(f"/api/ordenes-trabajo/{ot_id}/estado", json={"estado": "en_curso"}, headers=entorno["headers_encargado"])
    cliente.patch(f"/api/ordenes-trabajo/{ot_id}/estado", json={"estado": "resuelta"}, headers=entorno["headers_encargado"])

    reclamo = cliente.get(f"/api/reclamos/{entorno['reclamo_id']}", headers=entorno["headers_encargado"]).json()
    assert reclamo["estado"] == "resuelto"


def test_resolver_ot_no_fuerza_un_reclamo_ya_cerrado(entorno):
    """El reclamo llega a 'cerrado' por otra vía (manual) antes de que la
    OT se resuelva — sincronizar_reclamo_al_resolver_ot() nunca lo
    fuerza de vuelta a 'resuelto'."""
    cliente = entorno["cliente"]
    ot_id = cliente.post(
        f"/api/reclamos/{entorno['reclamo_id']}/orden-trabajo",
        json={"tipo": "correctivo", "encargado_id": entorno["id_encargado"]},
        headers=entorno["headers_encargado"],
    ).json()["id"]
    cliente.patch(f"/api/ordenes-trabajo/{ot_id}/estado", json={"estado": "en_curso"}, headers=entorno["headers_encargado"])

    # El reclamo llega a "cerrado" por su propio cambio de estado manual,
    # antes de que la OT se resuelva.
    for estado in ("resuelto", "cerrado"):
        cliente.patch(f"/api/reclamos/{entorno['reclamo_id']}/estado", json={"estado": estado}, headers=entorno["headers_encargado"])

    cliente.patch(f"/api/ordenes-trabajo/{ot_id}/estado", json={"estado": "resuelta"}, headers=entorno["headers_encargado"])

    reclamo = cliente.get(f"/api/reclamos/{entorno['reclamo_id']}", headers=entorno["headers_encargado"]).json()
    assert reclamo["estado"] == "cerrado"


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


# ------------------------------- evidencia -------------------------------

def test_agregar_evidencia_a_una_ot(entorno):
    cliente = entorno["cliente"]
    ot_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve"},
        headers=entorno["headers_encargado"],
    ).json()["id"]

    r1 = cliente.post(
        f"/api/ordenes-trabajo/{ot_id}/evidencia",
        json={"url": "https://ejemplo.test/antes.jpg", "momento": "antes"},
        headers=entorno["headers_encargado"],
    )
    assert r1.status_code == 201
    r2 = cliente.post(
        f"/api/ordenes-trabajo/{ot_id}/evidencia",
        json={"url": "https://ejemplo.test/despues.jpg", "momento": "despues"},
        headers=entorno["headers_encargado"],
    )
    assert r2.status_code == 201

    detalle = cliente.get(f"/api/ordenes-trabajo/{ot_id}", headers=entorno["headers_encargado"]).json()
    assert len(detalle["evidencias"]) == 2


def test_momento_de_evidencia_invalido_devuelve_422(entorno):
    cliente = entorno["cliente"]
    ot_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve"},
        headers=entorno["headers_encargado"],
    ).json()["id"]
    r = cliente.post(
        f"/api/ordenes-trabajo/{ot_id}/evidencia",
        json={"url": "https://ejemplo.test/x.jpg", "momento": "durante"},
        headers=entorno["headers_encargado"],
    )
    assert r.status_code == 422


def test_propietario_no_puede_agregar_evidencia(entorno):
    cliente = entorno["cliente"]
    ot_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/ordenes-trabajo",
        json={"tipo": "preventivo", "prioridad": "leve"},
        headers=entorno["headers_encargado"],
    ).json()["id"]
    r = cliente.post(
        f"/api/ordenes-trabajo/{ot_id}/evidencia",
        json={"url": "https://ejemplo.test/x.jpg", "momento": "antes"},
        headers=entorno["headers_prop"],
    )
    assert r.status_code == 403

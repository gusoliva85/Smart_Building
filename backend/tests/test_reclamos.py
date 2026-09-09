"""Tests de integración del router de reclamos (`routers/reclamos.py`) —
crear, listar, consultar, comentar y cambiar de estado, contra un backend
real (TestClient), no solo el modelo en memoria."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hashear_password
from app.database import Base, obtener_db
from app.main import app
from app.models.edificio import Cochera, Departamento, Edificio, EspacioComun, Piso
from app.models.reclamo import Reclamo, ReclamoComentario, ReclamoFoto
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
        Cochera.__table__, EspacioComun.__table__, Reclamo.__table__, ReclamoFoto.__table__,
        ReclamoComentario.__table__,
    ])
    SesionTest = sessionmaker(bind=engine)

    db = SesionTest()
    admin_general = Usuario(nombre="Admin", email="admin@test.com", password_hash=hashear_password("clave"), rol="admin_general")
    admin_consorcio = Usuario(nombre="Beto", email="beto@test.com", password_hash=hashear_password("clave"), rol="admin_consorcio")
    encargado = Usuario(nombre="Cami", email="cami@test.com", password_hash=hashear_password("clave"), rol="encargado")
    otro_encargado = Usuario(nombre="Dani", email="dani@test.com", password_hash=hashear_password("clave"), rol="encargado")
    propietario = Usuario(nombre="Prop", email="prop@test.com", password_hash=hashear_password("clave"), rol="propietario")
    ajeno = Usuario(nombre="Ajeno", email="ajeno@test.com", password_hash=hashear_password("clave"), rol="propietario")
    db.add_all([admin_general, admin_consorcio, encargado, otro_encargado, propietario, ajeno])
    db.commit()
    ids_usuarios = {u.email: u.id for u in [admin_general, admin_consorcio, encargado, otro_encargado, propietario, ajeno]}
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
        json={
            "nombre": "Torre Reclamos", "direccion": "Calle 1", "cantidad_pisos": 1, "unidades_por_piso": 2,
            "admin_consorcio_id": ids_usuarios["beto@test.com"],
        },
        headers=headers_admin,
    )
    edificio_id = r.json()["id"]
    depto_id = r.json()["pisos"][0]["departamentos"][0]["id"]

    cliente.patch(f"/api/edificios/{edificio_id}", json={"encargado_id": ids_usuarios["cami@test.com"]}, headers=headers_admin)

    db2 = SesionTest()
    db2.get(Departamento, depto_id).propietario_id = ids_usuarios["prop@test.com"]
    espacio = EspacioComun(edificio_id=edificio_id, nombre="SUM")
    db2.add(espacio)
    db2.commit()
    espacio_id = espacio.id
    db2.close()

    yield {
        "cliente": cliente,
        "headers_admin": headers_admin,
        "headers_consorcio": {"Authorization": f"Bearer {_token('beto@test.com')}"},
        "headers_encargado": {"Authorization": f"Bearer {_token('cami@test.com')}"},
        "headers_otro_encargado": {"Authorization": f"Bearer {_token('dani@test.com')}"},
        "headers_prop": {"Authorization": f"Bearer {_token('prop@test.com')}"},
        "headers_ajeno": {"Authorization": f"Bearer {_token('ajeno@test.com')}"},
        "edificio_id": edificio_id,
        "depto_id": depto_id,
        "espacio_id": espacio_id,
    }
    app.dependency_overrides.clear()


# ------------------------------- encargado_id de edificio -------------------------------

def test_configurar_encargado_con_rol_incorrecto_devuelve_400(entorno):
    cliente, headers = entorno["cliente"], entorno["headers_admin"]
    r = cliente.patch(f"/api/edificios/{entorno['edificio_id']}", json={"encargado_id": 99999}, headers=headers)
    assert r.status_code == 400


# ------------------------------- crear reclamo -------------------------------

def test_propietario_crea_reclamo_sobre_su_unidad(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={"departamento_id": entorno["depto_id"], "descripcion": "Pérdida de agua", "prioridad": "medio"},
        headers=entorno["headers_prop"],
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["estado"] == "recibido"
    assert cuerpo["creado_por_id"] is not None


def test_propietario_ajeno_no_puede_crear_reclamo(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={"descripcion": "x", "prioridad": "leve"},
        headers=entorno["headers_ajeno"],
    )
    assert r.status_code == 403


def test_reclamo_sobre_el_edificio_en_general(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={"descripcion": "Se corta la luz seguido", "prioridad": "critico"},
        headers=entorno["headers_prop"],
    )
    assert r.status_code == 201
    assert r.json()["departamento_id"] is None
    assert r.json()["espacio_comun_id"] is None


def test_reclamo_con_unidad_y_espacio_a_la_vez_devuelve_422(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={
            "departamento_id": entorno["depto_id"], "espacio_comun_id": entorno["espacio_id"],
            "descripcion": "x", "prioridad": "leve",
        },
        headers=entorno["headers_prop"],
    )
    assert r.status_code == 422


def test_encargado_tambien_puede_crear_un_reclamo(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={"espacio_comun_id": entorno["espacio_id"], "descripcion": "Luz quemada", "prioridad": "leve"},
        headers=entorno["headers_encargado"],
    )
    assert r.status_code == 201


def test_reclamo_con_fotos(entorno):
    cliente = entorno["cliente"]
    r = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={
            "departamento_id": entorno["depto_id"], "descripcion": "Con foto", "prioridad": "leve",
            "fotos": ["https://ejemplo.test/foto1.jpg", "https://ejemplo.test/foto2.jpg"],
        },
        headers=entorno["headers_prop"],
    )
    assert r.status_code == 201
    assert len(r.json()["fotos"]) == 2


# ------------------------------- listar / consultar -------------------------------

def test_mis_reclamos_devuelve_solo_los_propios(entorno):
    cliente = entorno["cliente"]
    cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={"departamento_id": entorno["depto_id"], "descripcion": "x", "prioridad": "leve"},
        headers=entorno["headers_prop"],
    )
    r = cliente.get("/api/mis-reclamos", headers=entorno["headers_prop"])
    assert len(r.json()) == 1

    r_ajeno = cliente.get("/api/mis-reclamos", headers=entorno["headers_ajeno"])
    assert r_ajeno.json() == []


def test_propietario_no_puede_listar_todos_los_reclamos_del_edificio(entorno):
    cliente = entorno["cliente"]
    r = cliente.get(f"/api/edificios/{entorno['edificio_id']}/reclamos", headers=entorno["headers_prop"])
    assert r.status_code == 403


def test_encargado_del_edificio_puede_listar(entorno):
    cliente = entorno["cliente"]
    cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={"departamento_id": entorno["depto_id"], "descripcion": "x", "prioridad": "leve"},
        headers=entorno["headers_prop"],
    )
    r = cliente.get(f"/api/edificios/{entorno['edificio_id']}/reclamos", headers=entorno["headers_encargado"])
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_encargado_de_otro_edificio_no_puede_listar(entorno):
    cliente = entorno["cliente"]
    r = cliente.get(f"/api/edificios/{entorno['edificio_id']}/reclamos", headers=entorno["headers_otro_encargado"])
    assert r.status_code == 403


def test_creador_puede_ver_su_reclamo_un_tercero_no(entorno):
    cliente = entorno["cliente"]
    reclamo_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={"departamento_id": entorno["depto_id"], "descripcion": "x", "prioridad": "leve"},
        headers=entorno["headers_prop"],
    ).json()["id"]

    assert cliente.get(f"/api/reclamos/{reclamo_id}", headers=entorno["headers_prop"]).status_code == 200
    assert cliente.get(f"/api/reclamos/{reclamo_id}", headers=entorno["headers_encargado"]).status_code == 200
    assert cliente.get(f"/api/reclamos/{reclamo_id}", headers=entorno["headers_ajeno"]).status_code == 403


# ------------------------------- cambiar estado -------------------------------

def test_gestion_mueve_el_flujo_normal(entorno):
    cliente = entorno["cliente"]
    reclamo_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={"departamento_id": entorno["depto_id"], "descripcion": "x", "prioridad": "leve"},
        headers=entorno["headers_prop"],
    ).json()["id"]

    r = cliente.patch(f"/api/reclamos/{reclamo_id}/estado", json={"estado": "asignado"}, headers=entorno["headers_encargado"])
    assert r.status_code == 200
    assert r.json()["estado"] == "asignado"


def test_creador_no_puede_mover_el_flujo_normal(entorno):
    cliente = entorno["cliente"]
    reclamo_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={"departamento_id": entorno["depto_id"], "descripcion": "x", "prioridad": "leve"},
        headers=entorno["headers_prop"],
    ).json()["id"]

    r = cliente.patch(f"/api/reclamos/{reclamo_id}/estado", json={"estado": "asignado"}, headers=entorno["headers_prop"])
    assert r.status_code == 403


def test_transicion_invalida_devuelve_400(entorno):
    cliente = entorno["cliente"]
    reclamo_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={"departamento_id": entorno["depto_id"], "descripcion": "x", "prioridad": "leve"},
        headers=entorno["headers_prop"],
    ).json()["id"]

    r = cliente.patch(f"/api/reclamos/{reclamo_id}/estado", json={"estado": "resuelto"}, headers=entorno["headers_encargado"])
    assert r.status_code == 400


def test_creador_puede_reabrir_un_reclamo_resuelto(entorno):
    cliente = entorno["cliente"]
    reclamo_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={"departamento_id": entorno["depto_id"], "descripcion": "x", "prioridad": "leve"},
        headers=entorno["headers_prop"],
    ).json()["id"]

    for estado in ("asignado", "en_curso", "resuelto"):
        cliente.patch(f"/api/reclamos/{reclamo_id}/estado", json={"estado": estado}, headers=entorno["headers_encargado"])

    r = cliente.patch(f"/api/reclamos/{reclamo_id}/estado", json={"estado": "en_curso"}, headers=entorno["headers_prop"])
    assert r.status_code == 200
    assert r.json()["estado"] == "en_curso"


def test_un_tercero_ajeno_no_puede_reabrir(entorno):
    cliente = entorno["cliente"]
    reclamo_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={"departamento_id": entorno["depto_id"], "descripcion": "x", "prioridad": "leve"},
        headers=entorno["headers_prop"],
    ).json()["id"]
    for estado in ("asignado", "en_curso", "resuelto"):
        cliente.patch(f"/api/reclamos/{reclamo_id}/estado", json={"estado": estado}, headers=entorno["headers_encargado"])

    r = cliente.patch(f"/api/reclamos/{reclamo_id}/estado", json={"estado": "en_curso"}, headers=entorno["headers_ajeno"])
    assert r.status_code == 403


def test_estado_invalido_devuelve_422(entorno):
    cliente = entorno["cliente"]
    reclamo_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={"departamento_id": entorno["depto_id"], "descripcion": "x", "prioridad": "leve"},
        headers=entorno["headers_prop"],
    ).json()["id"]
    r = cliente.patch(f"/api/reclamos/{reclamo_id}/estado", json={"estado": "en_camino"}, headers=entorno["headers_encargado"])
    assert r.status_code == 422


# ------------------------------- comentarios -------------------------------

def test_creador_y_gestion_pueden_comentar(entorno):
    cliente = entorno["cliente"]
    reclamo_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={"departamento_id": entorno["depto_id"], "descripcion": "x", "prioridad": "leve"},
        headers=entorno["headers_prop"],
    ).json()["id"]

    r1 = cliente.post(f"/api/reclamos/{reclamo_id}/comentarios", json={"texto": "¿Alguna novedad?"}, headers=entorno["headers_prop"])
    assert r1.status_code == 201
    r2 = cliente.post(f"/api/reclamos/{reclamo_id}/comentarios", json={"texto": "Ya lo asignamos"}, headers=entorno["headers_encargado"])
    assert r2.status_code == 201

    detalle = cliente.get(f"/api/reclamos/{reclamo_id}", headers=entorno["headers_prop"]).json()
    assert len(detalle["comentarios"]) == 2


def test_un_tercero_ajeno_no_puede_comentar(entorno):
    cliente = entorno["cliente"]
    reclamo_id = cliente.post(
        f"/api/edificios/{entorno['edificio_id']}/reclamos",
        json={"departamento_id": entorno["depto_id"], "descripcion": "x", "prioridad": "leve"},
        headers=entorno["headers_prop"],
    ).json()["id"]

    r = cliente.post(f"/api/reclamos/{reclamo_id}/comentarios", json={"texto": "x"}, headers=entorno["headers_ajeno"])
    assert r.status_code == 403


def test_reclamo_inexistente_devuelve_404(entorno):
    cliente = entorno["cliente"]
    assert cliente.get("/api/reclamos/99999", headers=entorno["headers_admin"]).status_code == 404
    assert cliente.patch("/api/reclamos/99999/estado", json={"estado": "asignado"}, headers=entorno["headers_admin"]).status_code == 404
    assert cliente.post("/api/reclamos/99999/comentarios", json={"texto": "x"}, headers=entorno["headers_admin"]).status_code == 404

"""Tests de PATCH /api/edificios/{id}, CRUD anidado (pisos, departamentos,
cocheras, espacios comunes) y asignación de propietario/inquilino.
"""

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
def contexto():
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
    admin_general = Usuario(nombre="Admin", email="admin@test.com", password_hash=hashear_password("clave"), rol="admin_general")
    admin_consorcio = Usuario(nombre="Beto", email="beto@test.com", password_hash=hashear_password("clave"), rol="admin_consorcio")
    otro_admin_consorcio = Usuario(nombre="Cami", email="cami@test.com", password_hash=hashear_password("clave"), rol="admin_consorcio")
    propietario = Usuario(nombre="Prop", email="prop@test.com", password_hash=hashear_password("clave"), rol="propietario")
    inquilino = Usuario(nombre="Inq", email="inq@test.com", password_hash=hashear_password("clave"), rol="inquilino")
    db.add_all([admin_general, admin_consorcio, otro_admin_consorcio, propietario, inquilino])
    db.commit()

    edificio = Edificio(nombre="Torre Test", direccion="Calle 1", admin_consorcio_id=admin_consorcio.id)
    db.add(edificio)
    db.commit()
    piso = Piso(edificio_id=edificio.id, numero="1", orden=1)
    db.add(piso)
    db.commit()
    depto = Departamento(piso_id=piso.id, identificador="1A")
    db.add(depto)
    db.commit()

    ids = {
        "edificio_id": edificio.id, "piso_id": piso.id, "departamento_id": depto.id,
        "propietario_id": propietario.id, "inquilino_id": inquilino.id,
        "otro_admin_consorcio_id": otro_admin_consorcio.id,
    }
    db.close()

    def _override_obtener_db():
        sesion = SesionTest()
        try:
            yield sesion
        finally:
            sesion.close()

    app.dependency_overrides[obtener_db] = _override_obtener_db
    yield TestClient(app), ids
    app.dependency_overrides.clear()


def _token(cliente, email, password="clave"):
    return cliente.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_admin_consorcio_del_edificio_puede_configurarlo(contexto):
    cliente, ids = contexto
    token = _token(cliente, "beto@test.com")
    respuesta = cliente.patch(
        f"/api/edificios/{ids['edificio_id']}",
        json={"contacto_emergencia_nombre": "Portería", "contacto_emergencia_telefono": "011-555-0000", "dias_vencimiento_expensas": 15},
        headers=_headers(token),
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["contacto_emergencia_nombre"] == "Portería"
    assert cuerpo["dias_vencimiento_expensas"] == 15


def test_admin_consorcio_de_otro_edificio_no_puede_configurarlo(contexto):
    cliente, ids = contexto
    token = _token(cliente, "cami@test.com")  # admin_consorcio pero de OTRO edificio
    respuesta = cliente.patch(f"/api/edificios/{ids['edificio_id']}", json={"dias_vencimiento_expensas": 20}, headers=_headers(token))
    assert respuesta.status_code == 403


def test_roles_habilitados_default_son_todos_hasta_que_se_configure(contexto):
    cliente, ids = contexto
    token = _token(cliente, "admin@test.com")
    respuesta = cliente.get(f"/api/edificios/{ids['edificio_id']}/pisos", headers=_headers(token))
    assert respuesta.status_code == 200  # confirma que el edificio existe y responde


def test_configurar_roles_habilitados_y_volver_a_leerlos(contexto):
    cliente, ids = contexto
    token = _token(cliente, "admin@test.com")
    respuesta = cliente.patch(
        f"/api/edificios/{ids['edificio_id']}",
        json={"roles_habilitados": ["admin_consorcio", "propietario", "inquilino", "encargado"]},
        headers=_headers(token),
    )
    assert respuesta.status_code == 200
    assert set(respuesta.json()["roles_habilitados"]) == {"admin_consorcio", "propietario", "inquilino", "encargado"}


def test_configurar_con_rol_invalido_devuelve_422(contexto):
    cliente, ids = contexto
    token = _token(cliente, "admin@test.com")
    respuesta = cliente.patch(
        f"/api/edificios/{ids['edificio_id']}",
        json={"roles_habilitados": ["rol_que_no_existe"]},
        headers=_headers(token),
    )
    assert respuesta.status_code == 422


def test_alta_manual_de_piso_y_departamento(contexto):
    cliente, ids = contexto
    token = _token(cliente, "admin@test.com")

    piso_nuevo = cliente.post(
        f"/api/edificios/{ids['edificio_id']}/pisos", json={"numero": "2", "orden": 2}, headers=_headers(token)
    )
    assert piso_nuevo.status_code == 201

    depto_nuevo = cliente.post(
        f"/api/edificios/{ids['edificio_id']}/departamentos",
        json={"piso_id": piso_nuevo.json()["id"], "identificador": "2A", "m2": 55},
        headers=_headers(token),
    )
    assert depto_nuevo.status_code == 201
    assert depto_nuevo.json()["identificador"] == "2A"

    listado = cliente.get(f"/api/edificios/{ids['edificio_id']}/pisos", headers=_headers(token)).json()
    assert len(listado) == 2  # el piso 1 original + el 2 recién creado


def test_departamento_en_piso_de_otro_edificio_devuelve_400(contexto):
    cliente, ids = contexto
    token = _token(cliente, "admin@test.com")

    otro_edificio = cliente.post(
        "/api/edificios",
        json={"nombre": "Otra Torre", "direccion": "Calle 2", "cantidad_pisos": 1, "unidades_por_piso": 1},
        headers=_headers(token),
    ).json()
    piso_ajeno_id = otro_edificio["pisos"][0]["id"]

    respuesta = cliente.post(
        f"/api/edificios/{ids['edificio_id']}/departamentos",
        json={"piso_id": piso_ajeno_id, "identificador": "X"},
        headers=_headers(token),
    )
    assert respuesta.status_code == 400


def test_asignar_propietario_e_inquilino_marca_ocupado(contexto):
    cliente, ids = contexto
    token = _token(cliente, "admin@test.com")

    respuesta = cliente.patch(
        f"/api/edificios/departamentos/{ids['departamento_id']}/asignacion",
        json={"propietario_id": ids["propietario_id"], "inquilino_id": ids["inquilino_id"]},
        headers=_headers(token),
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["propietario_id"] == ids["propietario_id"]
    assert cuerpo["inquilino_id"] == ids["inquilino_id"]
    assert cuerpo["ocupado"] is True


def test_desvincular_propietario_marca_desocupado_si_no_hay_inquilino(contexto):
    cliente, ids = contexto
    token = _token(cliente, "admin@test.com")

    cliente.patch(
        f"/api/edificios/departamentos/{ids['departamento_id']}/asignacion",
        json={"propietario_id": ids["propietario_id"]},
        headers=_headers(token),
    )
    respuesta = cliente.patch(
        f"/api/edificios/departamentos/{ids['departamento_id']}/asignacion",
        json={"propietario_id": None},
        headers=_headers(token),
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["propietario_id"] is None
    assert respuesta.json()["ocupado"] is False


def test_asignar_con_usuario_de_rol_incorrecto_devuelve_400(contexto):
    cliente, ids = contexto
    token = _token(cliente, "admin@test.com")
    respuesta = cliente.patch(
        f"/api/edificios/departamentos/{ids['departamento_id']}/asignacion",
        json={"propietario_id": ids["inquilino_id"]},  # es inquilino, no propietario
        headers=_headers(token),
    )
    assert respuesta.status_code == 400


def test_alta_y_listado_de_cochera_y_espacio_comun(contexto):
    cliente, ids = contexto
    token = _token(cliente, "admin@test.com")

    cochera = cliente.post(
        f"/api/edificios/{ids['edificio_id']}/cocheras",
        json={"numero": "12", "tipo": "fija", "departamento_id": ids["departamento_id"]},
        headers=_headers(token),
    )
    assert cochera.status_code == 201

    espacio = cliente.post(
        f"/api/edificios/{ids['edificio_id']}/espacios-comunes",
        json={"nombre": "SUM", "capacidad": 40},
        headers=_headers(token),
    )
    assert espacio.status_code == 201

    assert len(cliente.get(f"/api/edificios/{ids['edificio_id']}/cocheras", headers=_headers(token)).json()) == 1
    assert len(cliente.get(f"/api/edificios/{ids['edificio_id']}/espacios-comunes", headers=_headers(token)).json()) == 1


def test_cochera_con_tipo_invalido_devuelve_422(contexto):
    cliente, ids = contexto
    token = _token(cliente, "admin@test.com")
    respuesta = cliente.post(
        f"/api/edificios/{ids['edificio_id']}/cocheras",
        json={"numero": "1", "tipo": "voladora"},
        headers=_headers(token),
    )
    assert respuesta.status_code == 422


def test_configurar_edificio_inexistente_devuelve_404(contexto):
    cliente, ids = contexto
    token = _token(cliente, "admin@test.com")
    respuesta = cliente.patch("/api/edificios/9999", json={"dias_vencimiento_expensas": 5}, headers=_headers(token))
    assert respuesta.status_code == 404

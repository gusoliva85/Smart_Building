"""Tests de rendimiento del router de edificios — no de comportamiento.

Se detectó (analizando una queja real de lentitud) que `GET /api/edificios`
y `GET /api/edificios/{id}` disparaban un N+1 real: una consulta SQL
extra por cada piso, y otra por cada departamento de cada piso — 29
consultas para listar 7 edificios de prueba, 6 consultas para el detalle
de uno solo con 3 pisos. Invisible en SQLite local (cada consulta tarda
microsegundos), pero en producción (Postgres/Supabase) cada una es un
viaje de red real — medido en producción: ~1.5 segundos para un listado
con un solo edificio de prueba.

Estos tests cuentan las consultas SQL reales que dispara cada endpoint
(vía el evento `before_cursor_execute` de SQLAlchemy) y confirman que la
cantidad queda FIJA sin importar cuántos edificios/pisos/departamentos
haya — si alguien reintroduce un N+1 a futuro, estos tests lo detectan
sin depender de medir tiempos (poco confiable en CI).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hashear_password
from app.database import Base, obtener_db
from app.main import app
from app.models.edificio import Cochera, Departamento, Edificio, EspacioComun, Piso
from app.models.usuario import Usuario


@pytest.fixture()
def entorno():
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
    db.add(Usuario(nombre="Admin", email="admin@test.com", password_hash=hashear_password("clave"), rol="admin_general"))
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

    def _crear_edificio(nombre, cantidad_pisos, unidades_por_piso):
        r = cliente.post(
            "/api/edificios",
            json={"nombre": nombre, "direccion": "X", "cantidad_pisos": cantidad_pisos, "unidades_por_piso": unidades_por_piso},
            headers=headers,
        )
        assert r.status_code == 201, r.text
        return r.json()

    def _contar_queries(func):
        queries = []

        def _contar(conn, cursor, statement, parameters, context, executemany):
            queries.append(statement)

        event.listen(engine, "before_cursor_execute", _contar)
        try:
            resultado = func()
        finally:
            event.remove(engine, "before_cursor_execute", _contar)
        return resultado, len(queries)

    yield cliente, headers, _crear_edificio, _contar_queries
    app.dependency_overrides.clear()


def test_listado_no_crece_con_la_cantidad_de_pisos_y_departamentos(entorno):
    cliente, headers, crear_edificio, contar_queries = entorno

    crear_edificio("Torre Chica", 1, 1)
    _, queries_chico = contar_queries(lambda: cliente.get("/api/edificios", headers=headers))

    crear_edificio("Torre Grande", 8, 6)  # 8 pisos x 6 unidades = 48 departamentos
    respuesta, queries_grande = contar_queries(lambda: cliente.get("/api/edificios", headers=headers))

    assert respuesta.status_code == 200
    # Antes del fix esto escalaba linealmente con pisos/departamentos —
    # ahora tiene que ser UNA sola consulta agregada, sin importar el
    # tamaño real de los edificios.
    assert queries_grande == queries_chico
    assert queries_grande <= 2  # 1 query de negocio (+ alguna de sesión/transacción como máximo)


def test_listado_devuelve_resumen_con_conteos_correctos_sin_pisos_anidados(entorno):
    cliente, headers, crear_edificio, _ = entorno
    crear_edificio("Torre Resumen", 3, 4)  # 3 pisos x 4 = 12 departamentos

    respuesta = cliente.get("/api/edificios", headers=headers)
    cuerpo = respuesta.json()[0]

    assert cuerpo["cantidad_pisos"] == 3
    assert cuerpo["cantidad_unidades"] == 12
    assert "pisos" not in cuerpo  # el listado ya no trae la estructura completa


def test_detalle_no_crece_con_la_cantidad_de_pisos(entorno):
    cliente, headers, crear_edificio, contar_queries = entorno

    chico = crear_edificio("Torre Chica", 1, 1)
    _, queries_chico = contar_queries(lambda: cliente.get(f"/api/edificios/{chico['id']}", headers=headers))

    grande = crear_edificio("Torre Grande", 10, 5)  # 10 pisos
    respuesta, queries_grande = contar_queries(lambda: cliente.get(f"/api/edificios/{grande['id']}", headers=headers))

    assert respuesta.status_code == 200
    assert len(respuesta.json()["pisos"]) == 10
    # Antes: 1 query de departamentos POR piso (6 consultas para 3 pisos).
    # Ahora: selectinload trae TODOS los pisos en una consulta y TODOS los
    # departamentos de esos pisos en otra — fijo, no importa cuántos pisos haya.
    assert queries_grande == queries_chico

"""Tests de los modelos Reclamo, ReclamoFoto y ReclamoComentario.

Todavía sin endpoints (llegan en tareas posteriores de esta misma fase) —
acá solo se confirma que el modelo persiste bien, que el objetivo puntual
(unidad/espacio común/edificio en general) se resuelve como se definió en
el Roadmap, y sus reglas de integridad básicas contra `services/reclamos.py`.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.security import hashear_password
from app.database import Base
from app.models.edificio import Departamento, Edificio, EspacioComun, Piso
from app.models.reclamo import Reclamo, ReclamoComentario, ReclamoFoto
from app.models.usuario import Usuario


@pytest.fixture()
def sesion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[
        Usuario.__table__, Edificio.__table__, Piso.__table__, Departamento.__table__,
        EspacioComun.__table__, Reclamo.__table__, ReclamoFoto.__table__, ReclamoComentario.__table__,
    ])
    Sesion = sessionmaker(bind=engine)
    db = Sesion()
    yield db
    db.close()


@pytest.fixture()
def contexto(sesion):
    edificio = Edificio(nombre="Torre Central", direccion="Av. Siempre Viva 742")
    inquilino = Usuario(nombre="Inq", email="inq@test.com", password_hash=hashear_password("clave"), rol="inquilino")
    sesion.add_all([edificio, inquilino])
    sesion.commit()
    piso = Piso(edificio_id=edificio.id, numero="1", orden=1)
    sesion.add(piso)
    sesion.commit()
    depto = Departamento(piso_id=piso.id, identificador="1A")
    espacio = EspacioComun(edificio_id=edificio.id, nombre="SUM", capacidad=30)
    sesion.add_all([depto, espacio])
    sesion.commit()
    return edificio, inquilino, depto, espacio


def test_reclamo_sobre_una_unidad(sesion, contexto):
    edificio, inquilino, depto, _ = contexto
    reclamo = Reclamo(
        edificio_id=edificio.id, departamento_id=depto.id,
        descripcion="Pérdida de agua en el baño", prioridad="medio", creado_por_id=inquilino.id,
    )
    sesion.add(reclamo)
    sesion.commit()

    assert reclamo.id is not None
    assert reclamo.estado == "recibido"  # nace así por defecto
    assert reclamo.espacio_comun_id is None
    assert depto.reclamos == [reclamo]


def test_reclamo_sobre_un_espacio_comun(sesion, contexto):
    edificio, inquilino, _, espacio = contexto
    reclamo = Reclamo(
        edificio_id=edificio.id, espacio_comun_id=espacio.id,
        descripcion="Luz quemada en el SUM", prioridad="leve", creado_por_id=inquilino.id,
    )
    sesion.add(reclamo)
    sesion.commit()

    assert reclamo.departamento_id is None
    assert espacio.reclamos == [reclamo]


def test_reclamo_sobre_el_edificio_en_general(sesion, contexto):
    # Documento General 11.1: la 3ra opción real, ni unidad ni espacio
    # común puntual — no debe rechazarse por tener ambos en NULL.
    edificio, inquilino, _, _ = contexto
    reclamo = Reclamo(
        edificio_id=edificio.id,
        descripcion="Se corta la luz de todo el edificio seguido", prioridad="critico", creado_por_id=inquilino.id,
    )
    sesion.add(reclamo)
    sesion.commit()

    assert reclamo.departamento_id is None
    assert reclamo.espacio_comun_id is None
    assert reclamo.id in [r.id for r in edificio.reclamos]


def test_no_puede_tener_unidad_y_espacio_comun_a_la_vez(sesion, contexto):
    edificio, inquilino, depto, espacio = contexto
    sesion.add(Reclamo(
        edificio_id=edificio.id, departamento_id=depto.id, espacio_comun_id=espacio.id,
        descripcion="Ambiguo a propósito", prioridad="leve", creado_por_id=inquilino.id,
    ))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_prioridad_invalida_rechazada_por_la_base(sesion, contexto):
    edificio, inquilino, _, _ = contexto
    sesion.add(Reclamo(edificio_id=edificio.id, descripcion="x", prioridad="urgente", creado_por_id=inquilino.id))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_estado_invalido_rechazado_por_la_base(sesion, contexto):
    edificio, inquilino, _, _ = contexto
    sesion.add(Reclamo(
        edificio_id=edificio.id, descripcion="x", prioridad="leve", estado="en_camino", creado_por_id=inquilino.id,
    ))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_reclamo_sin_creado_por_rechazado(sesion, contexto):
    edificio, _, _, _ = contexto
    sesion.add(Reclamo(edificio_id=edificio.id, descripcion="x", prioridad="leve"))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_fotos_en_tabla_propia_no_en_un_campo_de_texto(sesion, contexto):
    edificio, inquilino, depto, _ = contexto
    reclamo = Reclamo(
        edificio_id=edificio.id, departamento_id=depto.id,
        descripcion="Con fotos", prioridad="medio", creado_por_id=inquilino.id,
    )
    sesion.add(reclamo)
    sesion.commit()
    sesion.add_all([
        ReclamoFoto(reclamo_id=reclamo.id, url="https://ejemplo.test/foto1.jpg"),
        ReclamoFoto(reclamo_id=reclamo.id, url="https://ejemplo.test/foto2.jpg"),
    ])
    sesion.commit()

    assert len(reclamo.fotos) == 2
    assert reclamo.fotos[0].url == "https://ejemplo.test/foto1.jpg"


def test_hilo_de_comentarios(sesion, contexto):
    edificio, inquilino, depto, _ = contexto
    reclamo = Reclamo(
        edificio_id=edificio.id, departamento_id=depto.id,
        descripcion="Con comentarios", prioridad="leve", creado_por_id=inquilino.id,
    )
    sesion.add(reclamo)
    sesion.commit()
    sesion.add(ReclamoComentario(reclamo_id=reclamo.id, autor_id=inquilino.id, texto="¿Alguna novedad?"))
    sesion.commit()

    assert len(reclamo.comentarios) == 1
    assert reclamo.comentarios[0].autor_id == inquilino.id
    assert reclamo.comentarios[0].texto == "¿Alguna novedad?"

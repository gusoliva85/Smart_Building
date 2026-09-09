"""Tests de los modelos OrdenTrabajo y OtEvidencia.

Todavía sin endpoints (llegan en tareas posteriores de esta misma fase) —
acá solo se confirma que el modelo persiste bien, que puede nacer con o
sin reclamo previo, con Encargado real o con un proveedor_id suelto, y
sus reglas de integridad básicas contra `services/reclamos.py`.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.security import hashear_password
from app.database import Base
from app.models.edificio import Departamento, Edificio, EspacioComun, Piso
from app.models.ordentrabajo import OrdenTrabajo, OtEvidencia
from app.models.reclamo import Reclamo
from app.models.usuario import Usuario


@pytest.fixture()
def sesion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[
        Usuario.__table__, Edificio.__table__, Piso.__table__, Departamento.__table__,
        EspacioComun.__table__, Reclamo.__table__, OrdenTrabajo.__table__, OtEvidencia.__table__,
    ])
    Sesion = sessionmaker(bind=engine)
    db = Sesion()
    yield db
    db.close()


@pytest.fixture()
def contexto(sesion):
    edificio = Edificio(nombre="Torre Central", direccion="Av. Siempre Viva 742")
    encargado = Usuario(nombre="Beto", email="beto@test.com", password_hash=hashear_password("clave"), rol="encargado")
    inquilino = Usuario(nombre="Inq", email="inq@test.com", password_hash=hashear_password("clave"), rol="inquilino")
    sesion.add_all([edificio, encargado, inquilino])
    sesion.commit()
    espacio = EspacioComun(edificio_id=edificio.id, nombre="Ascensor")
    sesion.add(espacio)
    sesion.commit()
    reclamo = Reclamo(
        edificio_id=edificio.id, espacio_comun_id=espacio.id,
        descripcion="El ascensor hace ruido", prioridad="medio", creado_por_id=inquilino.id,
    )
    sesion.add(reclamo)
    sesion.commit()
    return edificio, encargado, espacio, reclamo


def test_ot_manual_sin_reclamo_previo(sesion, contexto):
    edificio, encargado, espacio, _ = contexto
    ot = OrdenTrabajo(
        edificio_id=edificio.id, espacio_comun_id=espacio.id, tipo="preventivo",
        prioridad="leve", encargado_id=encargado.id,
    )
    sesion.add(ot)
    sesion.commit()

    assert ot.id is not None
    assert ot.estado == "pendiente"  # nace así por defecto
    assert ot.reclamo_id is None
    assert ot.encargado.nombre == "Beto"


def test_ot_generada_desde_un_reclamo(sesion, contexto):
    edificio, encargado, espacio, reclamo = contexto
    ot = OrdenTrabajo(
        edificio_id=edificio.id, espacio_comun_id=espacio.id, reclamo_id=reclamo.id,
        tipo="correctivo", prioridad=reclamo.prioridad, encargado_id=encargado.id,
    )
    sesion.add(ot)
    sesion.commit()

    assert reclamo.ordenes_trabajo == [ot]


def test_ot_con_proveedor_id_suelto_sin_encargado(sesion, contexto):
    # Decisión consultada con el usuario: proveedor_id es un entero suelto
    # sin FK real hasta la Fase 7 — el modelo no debe objetar cualquier valor.
    edificio, _, espacio, _ = contexto
    ot = OrdenTrabajo(
        edificio_id=edificio.id, espacio_comun_id=espacio.id, tipo="emergencia",
        prioridad="critico", proveedor_id=9999,
    )
    sesion.add(ot)
    sesion.commit()

    assert ot.encargado_id is None
    assert ot.proveedor_id == 9999


def test_tipo_invalido_rechazado_por_la_base(sesion, contexto):
    edificio, _, espacio, _ = contexto
    sesion.add(OrdenTrabajo(edificio_id=edificio.id, espacio_comun_id=espacio.id, tipo="urgente", prioridad="leve"))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_estado_invalido_rechazado_por_la_base(sesion, contexto):
    edificio, _, espacio, _ = contexto
    sesion.add(OrdenTrabajo(
        edificio_id=edificio.id, espacio_comun_id=espacio.id, tipo="preventivo", prioridad="leve", estado="asignado",
    ))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_costo_negativo_rechazado_por_la_base(sesion, contexto):
    edificio, _, espacio, _ = contexto
    sesion.add(OrdenTrabajo(
        edificio_id=edificio.id, espacio_comun_id=espacio.id, tipo="preventivo", prioridad="leve", costo=-500,
    ))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_evidencia_antes_y_despues(sesion, contexto):
    edificio, encargado, espacio, _ = contexto
    ot = OrdenTrabajo(edificio_id=edificio.id, espacio_comun_id=espacio.id, tipo="correctivo", prioridad="medio")
    sesion.add(ot)
    sesion.commit()
    sesion.add_all([
        OtEvidencia(orden_trabajo_id=ot.id, url="https://ejemplo.test/antes.jpg", momento="antes", subido_por_id=encargado.id),
        OtEvidencia(orden_trabajo_id=ot.id, url="https://ejemplo.test/despues.jpg", momento="despues", subido_por_id=encargado.id),
    ])
    sesion.commit()

    assert len(ot.evidencias) == 2
    assert {e.momento for e in ot.evidencias} == {"antes", "despues"}


def test_evidencia_con_momento_invalido_rechazada(sesion, contexto):
    edificio, encargado, espacio, _ = contexto
    ot = OrdenTrabajo(edificio_id=edificio.id, espacio_comun_id=espacio.id, tipo="correctivo", prioridad="medio")
    sesion.add(ot)
    sesion.commit()
    sesion.add(OtEvidencia(orden_trabajo_id=ot.id, url="https://ejemplo.test/x.jpg", momento="durante", subido_por_id=encargado.id))
    with pytest.raises(IntegrityError):
        sesion.commit()

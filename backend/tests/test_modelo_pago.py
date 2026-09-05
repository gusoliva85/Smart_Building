"""Tests del modelo Pago.

Todavía sin el endpoint de registro ni la conciliación (saldada/parcial)
— eso llega en una tarea posterior de esta misma fase. Acá solo se
confirma que el modelo persiste bien, que soporta pago parcial (monto
menor al total de la expensa) sin objetar nada, y sus reglas de
integridad básicas.
"""

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.edificio import Departamento, Edificio, Piso
from app.models.expensa import Expensa
from app.models.pago import Pago


@pytest.fixture()
def sesion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[
        Edificio.__table__, Piso.__table__, Departamento.__table__, Expensa.__table__, Pago.__table__,
    ])
    Sesion = sessionmaker(bind=engine)
    db = Sesion()
    yield db
    db.close()


@pytest.fixture()
def contexto(sesion):
    edificio = Edificio(nombre="Torre Central", direccion="Av. Siempre Viva 742")
    sesion.add(edificio)
    sesion.commit()
    piso = Piso(edificio_id=edificio.id, numero="1", orden=1)
    sesion.add(piso)
    sesion.commit()
    depto = Departamento(piso_id=piso.id, identificador="1A")
    expensa = Expensa(edificio_id=edificio.id, anio=2026, mes=8, total=10000)
    sesion.add_all([depto, expensa])
    sesion.commit()
    return depto, expensa


def test_pago_total_de_una_expensa(sesion, contexto):
    depto, expensa = contexto
    pago = Pago(departamento_id=depto.id, expensa_id=expensa.id, monto=10000, medio_pago="transferencia")
    sesion.add(pago)
    sesion.commit()

    assert pago.id is not None
    assert pago.fecha == datetime.date.today()
    assert pago.comprobante_url is None
    assert depto.pagos == [pago]
    assert expensa.pagos == [pago]


def test_pago_parcial_no_es_rechazado_por_el_modelo(sesion, contexto):
    # La conciliación (si queda "saldada" o "parcial") es de una tarea
    # futura — el modelo por sí solo no debe objetar un monto menor al
    # total de la expensa.
    depto, expensa = contexto
    pago = Pago(departamento_id=depto.id, expensa_id=expensa.id, monto=4000, medio_pago="efectivo")
    sesion.add(pago)
    sesion.commit()

    assert float(pago.monto) < float(expensa.total)


def test_varios_pagos_parciales_contra_la_misma_expensa(sesion, contexto):
    depto, expensa = contexto
    sesion.add_all([
        Pago(departamento_id=depto.id, expensa_id=expensa.id, monto=4000, medio_pago="efectivo",
             fecha=datetime.date(2026, 8, 5)),
        Pago(departamento_id=depto.id, expensa_id=expensa.id, monto=6000, medio_pago="transferencia",
             fecha=datetime.date(2026, 8, 20), comprobante_url="https://ejemplo.com/comprobante.pdf"),
    ])
    sesion.commit()

    assert len(expensa.pagos) == 2
    assert sum(float(p.monto) for p in expensa.pagos) == float(expensa.total)
    assert expensa.pagos[1].comprobante_url == "https://ejemplo.com/comprobante.pdf"


def test_monto_cero_o_negativo_rechazado_por_la_base(sesion, contexto):
    depto, expensa = contexto
    sesion.add(Pago(departamento_id=depto.id, expensa_id=expensa.id, monto=0, medio_pago="efectivo"))
    with pytest.raises(IntegrityError):
        sesion.commit()
    sesion.rollback()

    sesion.add(Pago(departamento_id=depto.id, expensa_id=expensa.id, monto=-100, medio_pago="efectivo"))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_pago_sin_departamento_o_sin_expensa_rechazado(sesion, contexto):
    depto, expensa = contexto

    sesion.add(Pago(expensa_id=expensa.id, monto=1000, medio_pago="efectivo"))
    with pytest.raises(IntegrityError):
        sesion.commit()
    sesion.rollback()

    sesion.add(Pago(departamento_id=depto.id, monto=1000, medio_pago="efectivo"))
    with pytest.raises(IntegrityError):
        sesion.commit()

"""Tests de los modelos Presupuesto y Factura.

Todavía sin el endpoint que "aprueba" un presupuesto y genera el Gasto
real (llega en una tarea posterior) — acá solo se confirma que los
modelos persisten bien, que se pueden comparar varios presupuestos para
un mismo gasto potencial, y las reglas de integridad básicas.
"""

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.edificio import Edificio
from app.models.gasto import Gasto
from app.models.presupuesto import Factura, Presupuesto


@pytest.fixture()
def sesion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[
        Edificio.__table__, Gasto.__table__, Presupuesto.__table__, Factura.__table__,
    ])
    Sesion = sessionmaker(bind=engine)
    db = Sesion()
    yield db
    db.close()


@pytest.fixture()
def edificio(sesion):
    edificio = Edificio(nombre="Torre Central", direccion="Av. Siempre Viva 742")
    sesion.add(edificio)
    sesion.commit()
    return edificio


def test_presupuesto_pendiente_por_defecto_sin_gasto_asociado(sesion, edificio):
    presupuesto = Presupuesto(edificio_id=edificio.id, descripcion="Pintura de palier", monto=50000)
    sesion.add(presupuesto)
    sesion.commit()

    assert presupuesto.estado == "pendiente"
    assert presupuesto.gasto_id is None
    assert presupuesto.proveedor_id is None


def test_varios_presupuestos_para_comparar_el_mismo_trabajo(sesion, edificio):
    # No hay obligación legal de una cantidad mínima/máxima — el modelo
    # tiene que permitir cero, uno o varios sin objetar nada.
    sesion.add_all([
        Presupuesto(edificio_id=edificio.id, descripcion="Pintura de palier", monto=50000, proveedor_id=1),
        Presupuesto(edificio_id=edificio.id, descripcion="Pintura de palier", monto=47000, proveedor_id=2),
        Presupuesto(edificio_id=edificio.id, descripcion="Pintura de palier", monto=61000, proveedor_id=3),
    ])
    sesion.commit()

    assert len(edificio.presupuestos) == 3


def test_aprobar_un_presupuesto_lo_vincula_al_gasto_real(sesion, edificio):
    gasto = Gasto(edificio_id=edificio.id, rubro="Mantenimiento", monto=47000, fecha=datetime.date.today())
    sesion.add(gasto)
    sesion.commit()

    elegido = Presupuesto(edificio_id=edificio.id, descripcion="Pintura de palier", monto=47000, proveedor_id=2)
    rechazado = Presupuesto(edificio_id=edificio.id, descripcion="Pintura de palier", monto=50000, proveedor_id=1)
    sesion.add_all([elegido, rechazado])
    sesion.commit()

    elegido.estado = "aprobado"
    elegido.gasto_id = gasto.id
    rechazado.estado = "rechazado"
    sesion.commit()

    assert gasto.presupuestos == [elegido]
    assert rechazado.gasto_id is None


def test_estado_invalido_rechazado_por_la_base(sesion, edificio):
    sesion.add(Presupuesto(edificio_id=edificio.id, descripcion="Pintura", monto=1000, estado="en_revision"))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_factura_vinculada_a_su_gasto(sesion, edificio):
    gasto = Gasto(edificio_id=edificio.id, rubro="Mantenimiento", monto=47000, fecha=datetime.date.today())
    sesion.add(gasto)
    sesion.commit()

    factura = Factura(gasto_id=gasto.id, numero="B 0001-00000123", monto=47000)
    sesion.add(factura)
    sesion.commit()

    assert gasto.facturas == [factura]
    assert factura.archivo_url is None


def test_factura_sin_gasto_rechazada_por_la_base(sesion, edificio):
    sesion.add(Factura(numero="B 0001-00000123", monto=1000))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_monto_cero_o_negativo_rechazado_en_ambos_modelos(sesion, edificio):
    sesion.add(Presupuesto(edificio_id=edificio.id, descripcion="Pintura", monto=0))
    with pytest.raises(IntegrityError):
        sesion.commit()
    sesion.rollback()

    gasto = Gasto(edificio_id=edificio.id, rubro="Mantenimiento", monto=1000, fecha=datetime.date.today())
    sesion.add(gasto)
    sesion.commit()
    sesion.add(Factura(gasto_id=gasto.id, numero="B 0001-1", monto=-100))
    with pytest.raises(IntegrityError):
        sesion.commit()

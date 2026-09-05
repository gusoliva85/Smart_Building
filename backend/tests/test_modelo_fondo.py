"""Tests de los modelos Fondo, MovimientoFondo y Caja.

Todavía sin endpoints ni cálculo de saldo (el saldo se resuelve sumando
movimientos, en una tarea posterior) — acá solo se confirma que los tres
modelos persisten bien, con sus reglas de integridad básicas.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.edificio import Edificio
from app.models.fondo import Caja, Fondo, MovimientoFondo
from app.models.usuario import Usuario


@pytest.fixture()
def sesion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[
        Usuario.__table__, Edificio.__table__, Fondo.__table__, MovimientoFondo.__table__, Caja.__table__,
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


def test_fondo_con_ingresos_y_egresos(sesion, edificio):
    fondo = Fondo(edificio_id=edificio.id, nombre="Fondo de Reserva")
    sesion.add(fondo)
    sesion.commit()

    sesion.add_all([
        MovimientoFondo(fondo_id=fondo.id, tipo="ingreso", monto=50000, descripcion="Aporte mensual"),
        MovimientoFondo(fondo_id=fondo.id, tipo="egreso", monto=12000, descripcion="Reparación de bomba"),
    ])
    sesion.commit()

    assert len(fondo.movimientos) == 2
    saldo = sum(
        float(m.monto) if m.tipo == "ingreso" else -float(m.monto)
        for m in fondo.movimientos
    )
    assert saldo == 38000


def test_dos_fondos_distintos_en_el_mismo_edificio(sesion, edificio):
    sesion.add_all([
        Fondo(edificio_id=edificio.id, nombre="Fondo de Reserva"),
        Fondo(edificio_id=edificio.id, nombre="Fondo de Obras"),
    ])
    sesion.commit()

    assert {f.nombre for f in edificio.fondos} == {"Fondo de Reserva", "Fondo de Obras"}


def test_tipo_de_movimiento_invalido_rechazado_por_la_base(sesion, edificio):
    fondo = Fondo(edificio_id=edificio.id, nombre="Fondo de Reserva")
    sesion.add(fondo)
    sesion.commit()

    sesion.add(MovimientoFondo(fondo_id=fondo.id, tipo="transferencia", monto=1000))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_monto_de_movimiento_cero_o_negativo_rechazado(sesion, edificio):
    fondo = Fondo(edificio_id=edificio.id, nombre="Fondo de Reserva")
    sesion.add(fondo)
    sesion.commit()

    sesion.add(MovimientoFondo(fondo_id=fondo.id, tipo="ingreso", monto=0))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_caja_con_responsable(sesion, edificio):
    encargado = Usuario(nombre="Encargado", email="encargado@test.com", password_hash="x", rol="encargado")
    sesion.add(encargado)
    sesion.commit()

    caja = Caja(edificio_id=edificio.id, responsable_id=encargado.id)
    sesion.add(caja)
    sesion.commit()

    assert edificio.caja.responsable.nombre == "Encargado"


def test_un_edificio_no_puede_tener_dos_cajas(sesion, edificio):
    encargado = Usuario(nombre="Encargado", email="encargado@test.com", password_hash="x", rol="encargado")
    sesion.add(encargado)
    sesion.commit()

    sesion.add(Caja(edificio_id=edificio.id, responsable_id=encargado.id))
    sesion.commit()

    sesion.add(Caja(edificio_id=edificio.id, responsable_id=encargado.id))
    with pytest.raises(IntegrityError):
        sesion.commit()

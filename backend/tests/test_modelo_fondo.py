"""Tests de los modelos Fondo, MovimientoFondo, Caja y MovimientoCaja.

Todavía sin endpoints ni cálculo de saldo expuesto por API (el saldo se
resuelve sumando movimientos, en una tarea posterior) — acá solo se
confirma que los modelos persisten bien, con sus reglas de integridad
básicas. `Caja`/`MovimientoCaja` siguen el sistema de "fondo fijo"
investigado en `documentacion/Caja_chica.md`.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.edificio import Edificio
from app.models.fondo import Caja, Fondo, MovimientoCaja, MovimientoFondo
from app.models.usuario import Usuario


@pytest.fixture()
def sesion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[
        Usuario.__table__, Edificio.__table__, Fondo.__table__, MovimientoFondo.__table__,
        Caja.__table__, MovimientoCaja.__table__,
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


@pytest.fixture()
def encargado(sesion):
    encargado = Usuario(nombre="Encargado", email="encargado@test.com", password_hash="x", rol="encargado")
    sesion.add(encargado)
    sesion.commit()
    return encargado


def test_caja_con_responsable_y_monto_fijo(sesion, edificio, encargado):
    caja = Caja(edificio_id=edificio.id, responsable_id=encargado.id, monto_fijo=20000)
    sesion.add(caja)
    sesion.commit()

    assert edificio.caja.responsable.nombre == "Encargado"
    assert float(edificio.caja.monto_fijo) == 20000


def test_un_edificio_no_puede_tener_dos_cajas(sesion, edificio, encargado):
    sesion.add(Caja(edificio_id=edificio.id, responsable_id=encargado.id, monto_fijo=20000))
    sesion.commit()

    sesion.add(Caja(edificio_id=edificio.id, responsable_id=encargado.id, monto_fijo=20000))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_monto_fijo_cero_o_negativo_rechazado(sesion, edificio, encargado):
    sesion.add(Caja(edificio_id=edificio.id, responsable_id=encargado.id, monto_fijo=0))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_caja_con_egresos_y_reposicion(sesion, edificio, encargado):
    # Escenario real del sistema de fondo fijo: se gasta, baja el
    # efectivo disponible, y se repone con un ingreso hasta volver cerca
    # del monto_fijo original.
    caja = Caja(edificio_id=edificio.id, responsable_id=encargado.id, monto_fijo=20000)
    sesion.add(caja)
    sesion.commit()

    sesion.add_all([
        MovimientoCaja(caja_id=caja.id, tipo="egreso", monto=3000, descripcion="Insumos de limpieza"),
        MovimientoCaja(caja_id=caja.id, tipo="egreso", monto=2000, descripcion="Ferretería"),
        MovimientoCaja(caja_id=caja.id, tipo="ingreso", monto=5000, descripcion="Reposición"),
    ])
    sesion.commit()

    assert len(caja.movimientos) == 3
    saldo = sum(
        float(m.monto) if m.tipo == "ingreso" else -float(m.monto)
        for m in caja.movimientos
    )
    assert saldo == 0  # se repuso exactamente lo gastado


def test_tipo_de_movimiento_de_caja_invalido_rechazado(sesion, edificio, encargado):
    caja = Caja(edificio_id=edificio.id, responsable_id=encargado.id, monto_fijo=20000)
    sesion.add(caja)
    sesion.commit()

    sesion.add(MovimientoCaja(caja_id=caja.id, tipo="transferencia", monto=1000))
    with pytest.raises(IntegrityError):
        sesion.commit()

"""Tests del modelo Gasto — primera pieza de datos real de la Fase 2.

`proveedor_id`/`activo_id` se guardan como columnas sueltas (sin FK real
todavía, ver models/gasto.py) porque esas tablas no existen hasta las
Fases 7 y 4 — acá solo se confirma que el dato persiste sin exigir que
apunte a nada.
"""

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.edificio import Edificio
from app.models.gasto import Gasto


@pytest.fixture()
def sesion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[Edificio.__table__, Gasto.__table__])
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


def test_gasto_minimo_sin_proveedor_ni_activo(sesion, edificio):
    gasto = Gasto(edificio_id=edificio.id, rubro="Limpieza", monto=15000, fecha=datetime.date(2026, 8, 1))
    sesion.add(gasto)
    sesion.commit()

    assert gasto.id is not None
    assert gasto.descripcion is None
    assert gasto.proveedor_id is None
    assert gasto.activo_id is None
    assert gasto.creado_en is not None


def test_gasto_con_proveedor_y_activo_sueltos(sesion, edificio):
    # Números cualquiera — todavía no hay tabla real de proveedores/activos
    # que los valide, es exactamente el comportamiento esperado hoy.
    gasto = Gasto(
        edificio_id=edificio.id, rubro="Ascensor", monto=48000.50,
        fecha=datetime.date(2026, 8, 5), descripcion="Service trimestral",
        proveedor_id=99, activo_id=7,
    )
    sesion.add(gasto)
    sesion.commit()

    assert float(gasto.monto) == 48000.50
    assert gasto.proveedor_id == 99
    assert gasto.activo_id == 7


def test_gasto_con_monto_cero_o_negativo_rechazado_por_la_base(sesion, edificio):
    sesion.add(Gasto(edificio_id=edificio.id, rubro="Limpieza", monto=0, fecha=datetime.date.today()))
    with pytest.raises(IntegrityError):
        sesion.commit()
    sesion.rollback()

    sesion.add(Gasto(edificio_id=edificio.id, rubro="Limpieza", monto=-500, fecha=datetime.date.today()))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_gasto_sin_edificio_rechazado_por_la_base(sesion):
    sesion.add(Gasto(rubro="Limpieza", monto=1000, fecha=datetime.date.today()))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_varios_gastos_de_un_edificio_via_relacion(sesion, edificio):
    sesion.add_all([
        Gasto(edificio_id=edificio.id, rubro="Limpieza", monto=15000, fecha=datetime.date(2026, 8, 1)),
        Gasto(edificio_id=edificio.id, rubro="Seguridad", monto=32000, fecha=datetime.date(2026, 8, 3)),
    ])
    sesion.commit()

    assert len(edificio.gastos) == 2
    assert {g.rubro for g in edificio.gastos} == {"Limpieza", "Seguridad"}

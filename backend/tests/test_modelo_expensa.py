"""Tests de los modelos Expensa y ExpensaDetalle.

Todavía sin servicio de generación (llega en una tarea posterior de esta
misma fase) — acá solo se confirma que el modelo persiste bien y que sus
reglas de integridad (período único, mes válido, montos positivos)
funcionan como se espera.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.edificio import Edificio
from app.models.expensa import Expensa, ExpensaDetalle


@pytest.fixture()
def sesion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[Edificio.__table__, Expensa.__table__, ExpensaDetalle.__table__])
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


def test_expensa_con_detalle_por_rubro(sesion, edificio):
    expensa = Expensa(edificio_id=edificio.id, anio=2026, mes=8, total=47000)
    sesion.add(expensa)
    sesion.commit()

    sesion.add_all([
        ExpensaDetalle(expensa_id=expensa.id, rubro="Limpieza", monto=15000),
        ExpensaDetalle(expensa_id=expensa.id, rubro="Seguridad", monto=32000),
    ])
    sesion.commit()

    assert len(expensa.detalles) == 2
    assert sum(float(d.monto) for d in expensa.detalles) == float(expensa.total)
    assert [d.rubro for d in expensa.detalles] == ["Limpieza", "Seguridad"]  # orden alfabético


def test_no_se_puede_liquidar_el_mismo_periodo_dos_veces(sesion, edificio):
    sesion.add(Expensa(edificio_id=edificio.id, anio=2026, mes=8, total=1000))
    sesion.commit()

    sesion.add(Expensa(edificio_id=edificio.id, anio=2026, mes=8, total=2000))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_mismo_edificio_distintos_periodos_no_choca(sesion, edificio):
    sesion.add_all([
        Expensa(edificio_id=edificio.id, anio=2026, mes=7, total=1000),
        Expensa(edificio_id=edificio.id, anio=2026, mes=8, total=1100),
    ])
    sesion.commit()

    assert len(edificio.expensas) == 2


def test_mes_fuera_de_rango_rechazado_por_la_base(sesion, edificio):
    sesion.add(Expensa(edificio_id=edificio.id, anio=2026, mes=13, total=1000))
    with pytest.raises(IntegrityError):
        sesion.commit()
    sesion.rollback()

    sesion.add(Expensa(edificio_id=edificio.id, anio=2026, mes=0, total=1000))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_total_y_monto_de_detalle_cero_o_negativo_rechazados(sesion, edificio):
    sesion.add(Expensa(edificio_id=edificio.id, anio=2026, mes=8, total=0))
    with pytest.raises(IntegrityError):
        sesion.commit()
    sesion.rollback()

    expensa = Expensa(edificio_id=edificio.id, anio=2026, mes=8, total=1000)
    sesion.add(expensa)
    sesion.commit()

    sesion.add(ExpensaDetalle(expensa_id=expensa.id, rubro="Limpieza", monto=-500))
    with pytest.raises(IntegrityError):
        sesion.commit()

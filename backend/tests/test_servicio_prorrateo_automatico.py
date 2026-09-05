"""Tests de `calcular_prorrateo_periodo` — la versión "automática" del
prorrateo, que sí toca la base real (a diferencia del resto de
services/finanzas.py). Se prueba el flujo completo: departamentos con
coeficiente real + gastos reales de un período -> monto por
departamento, incluyendo los casos que tienen que fallar con un mensaje
claro (coeficientes incompletos, sin gastos cargados).
"""

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.edificio import Departamento, Edificio, Piso
from app.models.gasto import Gasto
from app.services.finanzas import calcular_prorrateo_periodo


@pytest.fixture()
def sesion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[
        Edificio.__table__, Piso.__table__, Departamento.__table__, Gasto.__table__,
    ])
    Sesion = sessionmaker(bind=engine)
    db = Sesion()
    yield db
    db.close()


@pytest.fixture()
def edificio_con_coeficientes(sesion):
    """3 departamentos con coeficientes reales (50/30/20), como en el
    caso típico ya probado en la lógica pura de prorratear_gasto."""
    edificio = Edificio(nombre="Torre Prorrateo", direccion="Calle 1")
    sesion.add(edificio)
    sesion.commit()
    piso = Piso(edificio_id=edificio.id, numero="1", orden=1)
    sesion.add(piso)
    sesion.commit()
    sesion.add_all([
        Departamento(piso_id=piso.id, identificador="1A", coeficiente=50),
        Departamento(piso_id=piso.id, identificador="1B", coeficiente=30),
        Departamento(piso_id=piso.id, identificador="1C", coeficiente=20),
    ])
    sesion.commit()
    return edificio


def test_prorrateo_automatico_de_punta_a_punta(sesion, edificio_con_coeficientes):
    edificio = edificio_con_coeficientes
    sesion.add_all([
        Gasto(edificio_id=edificio.id, rubro="Limpieza", monto=60000, fecha=datetime.date(2026, 8, 5)),
        Gasto(edificio_id=edificio.id, rubro="Seguridad", monto=40000, fecha=datetime.date(2026, 8, 20)),
    ])
    sesion.commit()

    resultado = calcular_prorrateo_periodo(sesion, edificio.id, 2026, 8)

    deptos = {d.identificador: d.id for d in edificio.pisos[0].departamentos}
    assert resultado[deptos["1A"]] == 50000  # 50% de 100.000
    assert resultado[deptos["1B"]] == 30000
    assert resultado[deptos["1C"]] == 20000
    assert sum(resultado.values()) == 100000  # nunca se pierden centavos


def test_gastos_de_otro_periodo_no_se_incluyen(sesion, edificio_con_coeficientes):
    edificio = edificio_con_coeficientes
    sesion.add_all([
        Gasto(edificio_id=edificio.id, rubro="Limpieza", monto=100000, fecha=datetime.date(2026, 8, 5)),
        Gasto(edificio_id=edificio.id, rubro="Limpieza", monto=999999, fecha=datetime.date(2026, 7, 5)),  # julio, no agosto
        Gasto(edificio_id=edificio.id, rubro="Limpieza", monto=999999, fecha=datetime.date(2025, 8, 5)),  # 2025, no 2026
    ])
    sesion.commit()

    resultado = calcular_prorrateo_periodo(sesion, edificio.id, 2026, 8)
    assert sum(resultado.values()) == 100000


def test_gastos_de_otro_edificio_no_se_incluyen(sesion, edificio_con_coeficientes):
    edificio = edificio_con_coeficientes
    otro_edificio = Edificio(nombre="Torre Ajena", direccion="Calle 2")
    sesion.add(otro_edificio)
    sesion.commit()

    sesion.add_all([
        Gasto(edificio_id=edificio.id, rubro="Limpieza", monto=100000, fecha=datetime.date(2026, 8, 5)),
        Gasto(edificio_id=otro_edificio.id, rubro="Limpieza", monto=999999, fecha=datetime.date(2026, 8, 5)),
    ])
    sesion.commit()

    resultado = calcular_prorrateo_periodo(sesion, edificio.id, 2026, 8)
    assert sum(resultado.values()) == 100000


def test_departamento_sin_coeficiente_lanza_error_claro(sesion, edificio_con_coeficientes):
    edificio = edificio_con_coeficientes
    piso = edificio.pisos[0]
    sesion.add(Departamento(piso_id=piso.id, identificador="1D"))  # sin coeficiente
    sesion.add(Gasto(edificio_id=edificio.id, rubro="Limpieza", monto=1000, fecha=datetime.date(2026, 8, 5)))
    sesion.commit()

    with pytest.raises(ValueError, match="1D"):
        calcular_prorrateo_periodo(sesion, edificio.id, 2026, 8)


def test_coeficientes_que_no_suman_100_lanza_error(sesion):
    edificio = Edificio(nombre="Torre Mal Configurada", direccion="Calle 3")
    sesion.add(edificio)
    sesion.commit()
    piso = Piso(edificio_id=edificio.id, numero="1", orden=1)
    sesion.add(piso)
    sesion.commit()
    sesion.add_all([
        Departamento(piso_id=piso.id, identificador="1A", coeficiente=50),
        Departamento(piso_id=piso.id, identificador="1B", coeficiente=30),  # suma 80, no 100
    ])
    sesion.add(Gasto(edificio_id=edificio.id, rubro="Limpieza", monto=1000, fecha=datetime.date(2026, 8, 5)))
    sesion.commit()

    with pytest.raises(ValueError, match="100"):
        calcular_prorrateo_periodo(sesion, edificio.id, 2026, 8)


def test_sin_gastos_en_el_periodo_lanza_error_claro(sesion, edificio_con_coeficientes):
    edificio = edificio_con_coeficientes
    with pytest.raises(ValueError, match="8/2026"):
        calcular_prorrateo_periodo(sesion, edificio.id, 2026, 8)


def test_edificio_sin_departamentos_lanza_error(sesion):
    edificio = Edificio(nombre="Torre Vacía", direccion="Calle 4")
    sesion.add(edificio)
    sesion.commit()

    with pytest.raises(ValueError):
        calcular_prorrateo_periodo(sesion, edificio.id, 2026, 8)

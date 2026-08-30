"""Tests de Piso, Departamento, Cochera y EspacioComun.

Se crea un edificio de prueba completo — piso con departamentos, uno de
ellos con propietario e inquilino asignados, una cochera fija vinculada a
ese departamento, y un espacio común — para confirmar que todo el dominio
"Edificios" funciona junto, no solo cada tabla por separado.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.edificio import Cochera, Departamento, Edificio, EspacioComun, Piso
from app.models.usuario import Usuario


@pytest.fixture()
def sesion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[
        Usuario.__table__, Edificio.__table__, Piso.__table__,
        Departamento.__table__, Cochera.__table__, EspacioComun.__table__,
    ])
    Sesion = sessionmaker(bind=engine)
    db = Sesion()
    yield db
    db.close()


def test_estructura_completa_de_un_edificio_de_prueba(sesion):
    edificio = Edificio(nombre="Torre Central", direccion="Av. Siempre Viva 742")
    sesion.add(edificio)
    sesion.commit()

    piso = Piso(edificio_id=edificio.id, numero="7", orden=7)
    sesion.add(piso)
    sesion.commit()

    propietario = Usuario(nombre="C. Ortega", email="ortega@test.com", password_hash="x", rol="propietario")
    inquilino = Usuario(nombre="F. Bianchi", email="bianchi@test.com", password_hash="x", rol="inquilino")
    sesion.add_all([propietario, inquilino])
    sesion.commit()

    depto = Departamento(
        piso_id=piso.id, identificador="7A", m2=70,
        propietario_id=propietario.id, inquilino_id=inquilino.id, ocupado=True,
    )
    depto_vacio = Departamento(piso_id=piso.id, identificador="7B", m2=54)
    sesion.add_all([depto, depto_vacio])
    sesion.commit()

    assert depto.ocupado is True
    assert depto_vacio.ocupado is False  # default
    assert depto_vacio.propietario_id is None

    cochera = Cochera(edificio_id=edificio.id, numero="12", tipo="fija", departamento_id=depto.id)
    sesion.add(cochera)
    sesion.commit()
    assert cochera.departamento_id == depto.id

    sum_ = EspacioComun(edificio_id=edificio.id, nombre="SUM", capacidad=40, reglas_uso="Reservar con 48hs de anticipación")
    sesion.add(sum_)
    sesion.commit()
    assert sum_.capacidad == 40


def test_cochera_con_tipo_invalido_rechazada_por_la_base(sesion):
    edificio = Edificio(nombre="Torre Norte", direccion="Calle Falsa 123")
    sesion.add(edificio)
    sesion.commit()

    sesion.add(Cochera(edificio_id=edificio.id, numero="1", tipo="voladora"))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_cochera_puede_no_estar_vinculada_a_un_departamento(sesion):
    edificio = Edificio(nombre="Torre Sur", direccion="Otra Calle 456")
    sesion.add(edificio)
    sesion.commit()

    cochera = Cochera(edificio_id=edificio.id, numero="5", tipo="rotativa")
    sesion.add(cochera)
    sesion.commit()

    assert cochera.departamento_id is None


def test_departamento_sin_asignar_queda_libre_para_generacion_automatica(sesion):
    # Coherencia con services/edificios.py: la estructura recién generada
    # no tiene propietario/inquilino ni está ocupada.
    edificio = Edificio(nombre="Torre Este", direccion="Bulevar 789")
    sesion.add(edificio)
    sesion.commit()
    piso = Piso(edificio_id=edificio.id, numero="1", orden=1)
    sesion.add(piso)
    sesion.commit()

    depto = Departamento(piso_id=piso.id, identificador="1A")
    sesion.add(depto)
    sesion.commit()

    assert depto.propietario_id is None
    assert depto.inquilino_id is None
    assert depto.ocupado is False

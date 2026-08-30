"""Tests del modelo `Edificio` — y cierre de la verificación pendiente de
`UsuarioEdificio` (dejada documentada como "estructura verificada, tabla
real pendiente" en la Tarea 2 de esta fase).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.edificio import Edificio
from app.models.usuario import Usuario
from app.models.usuario_edificio import UsuarioEdificio


@pytest.fixture()
def sesion():
    engine = create_engine("sqlite:///:memory:")
    # Ahora sí se pueden crear las TRES tablas juntas: usuario_edificio
    # tiene una FK a edificios, que hasta esta tarea no existía.
    Base.metadata.create_all(bind=engine, tables=[Usuario.__table__, Edificio.__table__, UsuarioEdificio.__table__])
    Sesion = sessionmaker(bind=engine)
    db = Sesion()
    yield db
    db.close()


def test_crear_edificio_con_valores_por_defecto(sesion):
    edificio = Edificio(nombre="Torre Central", direccion="Av. Siempre Viva 742")
    sesion.add(edificio)
    sesion.commit()

    assert edificio.id is not None
    assert edificio.activo is True
    assert edificio.dias_vencimiento_expensas == 10
    assert edificio.recargo_mora_porcentual == 0


def test_edificio_vinculado_a_un_administrador_de_consorcio(sesion):
    admin = Usuario(nombre="Beto Admin", email="beto@test.com", password_hash="x", rol="admin_consorcio")
    sesion.add(admin)
    sesion.commit()

    edificio = Edificio(nombre="Torre Norte", direccion="Calle Falsa 123", admin_consorcio_id=admin.id)
    sesion.add(edificio)
    sesion.commit()

    assert edificio.admin_consorcio_id == admin.id


def test_usuario_edificio_ya_se_puede_crear_de_verdad_en_la_base(sesion):
    # Esta es la verificación que quedó pendiente en la Tarea 2 de esta
    # fase: ahora que `edificios` existe, la fila real de usuario_edificio
    # se puede insertar y consultar, no solo inspeccionar su estructura.
    propietario = Usuario(nombre="Ana Prop", email="ana@test.com", password_hash="x", rol="propietario")
    edificio = Edificio(nombre="Torre Sur", direccion="Otra Calle 456")
    sesion.add_all([propietario, edificio])
    sesion.commit()

    vinculo = UsuarioEdificio(usuario_id=propietario.id, edificio_id=edificio.id, rol_efectivo="propietario")
    sesion.add(vinculo)
    sesion.commit()

    guardado = sesion.query(UsuarioEdificio).first()
    assert guardado.usuario_id == propietario.id
    assert guardado.edificio_id == edificio.id
    assert guardado.rol_efectivo == "propietario"

"""Tests de los modelos `Usuario` y `UsuarioEdificio`.

`Usuario` se prueba contra una base SQLite en memoria (aislada de
`smart_building.db`, para no ensuciar datos reales con filas de test).
`UsuarioEdificio` todavía no puede crear su tabla real (su FK apunta a
`edificios`, que se crea recién en la próxima tarea de esta fase) — se
verifica su estructura sin emitir DDL.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.usuario import Usuario
from app.models.usuario_edificio import UsuarioEdificio


@pytest.fixture()
def sesion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[Usuario.__table__])
    Sesion = sessionmaker(bind=engine)
    db = Sesion()
    yield db
    db.close()


def test_crear_usuario_con_rol_valido(sesion):
    usuario = Usuario(nombre="Ana Test", email="ana@test.com", password_hash="hash", rol="admin_general")
    sesion.add(usuario)
    sesion.commit()

    assert usuario.id is not None
    assert usuario.activo is True  # default
    assert usuario.creado_en is not None  # default


def test_rol_invalido_rechazado_por_la_base(sesion):
    usuario = Usuario(nombre="Malo", email="malo@test.com", password_hash="hash", rol="rol_inventado")
    sesion.add(usuario)
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_email_duplicado_rechazado(sesion):
    sesion.add(Usuario(nombre="A", email="dup@test.com", password_hash="hash", rol="propietario"))
    sesion.commit()

    sesion.add(Usuario(nombre="B", email="dup@test.com", password_hash="hash", rol="inquilino"))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_estructura_usuario_edificio_sin_crear_tabla_todavia():
    columnas = set(UsuarioEdificio.__table__.columns.keys())
    assert columnas == {"id", "usuario_id", "edificio_id", "rol_efectivo"}

    fk_usuario = next(iter(UsuarioEdificio.__table__.c.usuario_id.foreign_keys))
    fk_edificio = next(iter(UsuarioEdificio.__table__.c.edificio_id.foreign_keys))
    assert fk_usuario.target_fullname == "usuarios.id"
    assert fk_edificio.target_fullname == "edificios.id"

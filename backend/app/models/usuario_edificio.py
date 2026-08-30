"""Modelo `UsuarioEdificio` — tabla puente (Documento Técnico, sección 5.1).

Un mismo `Usuario` puede estar vinculado a más de un `Edificio` (un
Administrador General con cartera, un Propietario con unidades en dos
edificios distintos), con un rol EFECTIVO propio de ese vínculo puntual
— por eso el rol vive acá y no solo en `Usuario`.

Nota de orden de implementación: el modelo `Edificio` recién se crea en la
próxima sub-sección de esta misma fase ("Estructura del edificio"), así que
la clave foránea `edificio_id` apunta a una tabla que todavía no existe en
el momento de escribir este archivo. Esto es válido en SQLAlchemy: la
referencia se resuelve al emitir el `CREATE TABLE`, no al importar la clase.
Por eso la tabla `usuario_edificio` no se crea todavía en la base real — se
verifica por ahora solo su estructura (columnas y FKs), y su creación real
en la base de datos queda para cuando `Edificio` ya exista.
"""

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String

from app.database import Base
from app.services.autorizacion import ROLES

_ROLES_SQL = ", ".join(f"'{rol}'" for rol in ROLES)


class UsuarioEdificio(Base):
    __tablename__ = "usuario_edificio"
    __table_args__ = (
        CheckConstraint(f"rol_efectivo IN ({_ROLES_SQL})", name="ck_usuario_edificio_rol_valido"),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    edificio_id = Column(Integer, ForeignKey("edificios.id"), nullable=False)
    rol_efectivo = Column(String, nullable=False)

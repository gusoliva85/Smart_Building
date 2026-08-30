"""Modelo `Usuario` — Documento Técnico, sección 5.1.

Tabla base de todo el sistema de permisos. El rol se valida a nivel de base
de datos contra la misma lista de `services/autorizacion.py` (ROLES) que ya
quedó definida y probada en la tarea de lógica anterior — no se vuelve a
escribir la lista de roles a mano en un segundo lugar.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, String

from app.database import Base
from app.services.autorizacion import ROLES

_ROLES_SQL = ", ".join(f"'{rol}'" for rol in ROLES)


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(f"rol IN ({_ROLES_SQL})", name="ck_usuarios_rol_valido"),
    )

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    rol = Column(String, nullable=False)
    telefono = Column(String, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

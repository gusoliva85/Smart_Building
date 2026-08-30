"""Esquemas Pydantic del router de usuarios."""

from pydantic import BaseModel, ConfigDict, field_validator

from app.services.autorizacion import ROLES


def _validar_rol(valor: str) -> str:
    if valor not in ROLES:
        raise ValueError(f"Rol inválido: {valor!r}. Roles válidos: {ROLES}")
    return valor


class UsuarioEntrada(BaseModel):
    nombre: str
    email: str
    password: str
    rol: str
    telefono: str | None = None

    _validar_rol = field_validator("rol")(_validar_rol)


class UsuarioEdicion(BaseModel):
    nombre: str | None = None
    telefono: str | None = None
    rol: str | None = None
    activo: bool | None = None

    @field_validator("rol")
    @classmethod
    def _validar_rol_opcional(cls, valor):
        return _validar_rol(valor) if valor is not None else valor


class UsuarioSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str
    rol: str
    telefono: str | None
    activo: bool

"""Esquemas Pydantic de entrada/salida del router de autenticación.

Separados del modelo `Usuario` (SQLAlchemy) a propósito — buena práctica que
ya fija el Documento Técnico, sección 2.2: nunca se filtra `password_hash`
ni ningún campo interno en una respuesta de la API.
"""

from pydantic import BaseModel, ConfigDict


class LoginEntrada(BaseModel):
    email: str
    password: str


class TokenSalida(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioActual(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str
    rol: str
    activo: bool

"""Hash de contraseñas y utilidades JWT — Documento Técnico, secciones 3.2 y 19.

Regla no negociable del proyecto: ninguna contraseña se guarda ni se
loguea en texto plano en ningún punto del código, ni siquiera en modo
test — el hash con bcrypt (vía passlib) es siempre el único formato en el
que una contraseña toca la base de datos. El token de sesión es un JWT de
corta duración (python-jose), sin estado en el servidor: el backend no
guarda sesiones, solo firma y valida.
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import JWT_ALGORITMO, JWT_MINUTOS_EXPIRACION, JWT_SECRETO

_contexto_password = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hashear_password(password: str) -> str:
    return _contexto_password.hash(password)


def verificar_password(password: str, password_hash: str) -> bool:
    return _contexto_password.verify(password, password_hash)


class TokenInvalido(Exception):
    """Token vencido, alterado o mal formado — nunca se decodifica en silencio."""


def crear_token_acceso(datos: dict, minutos_expiracion: int = JWT_MINUTOS_EXPIRACION) -> str:
    """Genera un JWT firmado a partir de `datos` (típicamente
    {"sub": email, "rol": ..., "edificios": [...]}) — lo que la próxima
    tarea (login) y la dependencia de autorización van a leer en cada
    request sin volver a consultar la base para saber "quién es".
    """
    a_codificar = dict(datos)
    a_codificar["exp"] = datetime.now(timezone.utc) + timedelta(minutes=minutos_expiracion)
    return jwt.encode(a_codificar, JWT_SECRETO, algorithm=JWT_ALGORITMO)


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRETO, algorithms=[JWT_ALGORITMO])
    except JWTError as error:
        raise TokenInvalido(str(error)) from error

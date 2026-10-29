"""Autenticacion: iniciar sesion y saber quien soy.

Dos endpoints, y son la base de todo lo demas:

- ``POST /api/auth/login`` — email y contrasenia a cambio de un token.
- ``GET  /api/auth/me``    — el usuario de la sesion.

`/auth/me` es lo que el frontend pide al cargar cualquier pantalla autenticada
para armar la navegacion segun el rol (F1-T11). Por eso devuelve, ademas de los
datos del usuario, la fila de la matriz de permisos que le corresponde: asi la
interfaz no tiene que declarar su propia copia de la matriz.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.dependencies import UsuarioActual
from app.database import obtener_db
from app.models.usuario import Usuario
from app.schemas.usuario import Token, UsuarioRespuesta, normalizar_email

router = APIRouter(prefix="/auth", tags=["Autenticacion"])


@router.post("/login", response_model=Token)
def login(
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(obtener_db)],
) -> Token:
    """Valida las credenciales y devuelve el token de sesion.

    **El campo se llama `username` y lleva el email.** Es el nombre que fija el
    estandar de OAuth2, y respetarlo es lo que hace que el boton "Authorize" de
    /docs funcione — que es la herramienta con la que se prueba cada endpoint
    protegido antes de que exista su pantalla. Renombrarlo a `email` obligaria
    a escribir el login a mano en /docs para cada prueba.

    El email se normaliza con la MISMA funcion que el alta. Sin eso, quien se
    da de alta como `Ana@...` queda guardado en minusculas y despues no entra
    escribiendo exactamente lo mismo que puso al registrarse.
    """
    email = normalizar_email(formulario.username)
    usuario = db.scalar(select(Usuario).where(Usuario.email == email))

    # Un unico mensaje y un unico codigo para los tres casos: el usuario no
    # existe, la contrasenia esta mal, o el usuario esta desactivado.
    #
    # Es deliberado. Si "ese email no existe" y "esa contrasenia es incorrecta"
    # dieran respuestas distintas, el login se convertiria en una herramienta
    # para averiguar que direcciones estan registradas en el sistema, probando
    # emails de a uno. Y distinguir al usuario inactivo le confirmaria a quien
    # pruebe que esa cuenta existe.
    #
    # La verificacion de la contrasenia se corre IGUAL cuando el usuario no
    # existe, contra un hash descartable. Si se cortara antes, la respuesta del
    # caso "no existe" seria notablemente mas rapida que la del caso
    # "contrasenia incorrecta", y esa diferencia de tiempos alcanza para
    # distinguirlos aunque el mensaje sea el mismo.
    if usuario is None:
        security.verificar_password(formulario.password, _HASH_DESCARTABLE)
        raise _CREDENCIALES_INVALIDAS

    if not security.verificar_password(formulario.password, usuario.password_hash):
        raise _CREDENCIALES_INVALIDAS

    # Un usuario inactivo no inicia sesion. Y como `obtener_usuario_actual`
    # vuelve a verificar `activo` en cada request, tampoco sigue operando con
    # un token que ya tenia: la baja es efectiva en el momento, no cuando el
    # token vence.
    if not usuario.activo:
        raise _CREDENCIALES_INVALIDAS

    return Token(access_token=security.crear_token_de_acceso(usuario.id))


@router.get("/me", response_model=UsuarioRespuesta)
def yo(usuario: UsuarioActual) -> Usuario:
    """El usuario de la sesion, con la fila de la matriz que le corresponde.

    Es el primer pedido de toda pantalla autenticada: el frontend lo usa para
    saber que accesos mostrar en el sidebar. Y es, de paso, la forma mas simple
    de verificar que un token sigue valiendo.
    """
    return usuario


_CREDENCIALES_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Email o contrasenia incorrectos.",
    headers={"WWW-Authenticate": "Bearer"},
)

# Un hash real de una contrasenia que no le sirve a nadie, calculado una sola
# vez al importar el modulo. Existe solo para que el caso "el email no existe"
# pague el mismo costo de verificacion que el caso "la contrasenia esta mal".
_HASH_DESCARTABLE = security.hashear_password("hash-descartable-para-igualar-tiempos")

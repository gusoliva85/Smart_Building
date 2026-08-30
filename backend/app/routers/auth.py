"""Router de autenticación — Documento Técnico, sección 3.2.

`POST /api/auth/login`: valida email + password contra la base (comparando
el hash con bcrypt, nunca la contraseña en texto plano) y devuelve un JWT.
`GET /api/auth/me`: dado ese JWT, devuelve los datos del usuario logueado
— es lo que el frontend va a usar para saber "quién soy" sin volver a pedir
la contraseña en cada pantalla.

Nota de alcance: el JWT ya incluye una lista `edificios` (vacía por ahora)
para que su forma quede fija desde el día uno — se completa de verdad
recién cuando `UsuarioEdificio` tenga su tabla real (próxima tarea de esta
fase, "Estructura del edificio").
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.core.security import crear_token_acceso, verificar_password
from app.database import obtener_db
from app.models.usuario import Usuario
from app.schemas.auth import LoginEntrada, TokenSalida, UsuarioActual

router = APIRouter(prefix="/api/auth", tags=["auth"])

_ERROR_CREDENCIALES = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Email o contraseña incorrectos",
)


@router.post("/login", response_model=TokenSalida)
def login(datos: LoginEntrada, db: Session = Depends(obtener_db)):
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if not usuario or not verificar_password(datos.password, usuario.password_hash):
        raise _ERROR_CREDENCIALES
    if not usuario.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario desactivado")

    token = crear_token_acceso({"sub": usuario.email, "rol": usuario.rol, "edificios": []})
    return TokenSalida(access_token=token)


@router.get("/me", response_model=UsuarioActual)
def leer_usuario_actual(actual: UsuarioAutenticado = Depends(obtener_usuario_actual)):
    return actual.usuario

"""Dependencia de autorización central — Documento Técnico, sección 3.2 y 6.2.

Cada endpoint protegido de acá en adelante depende de `obtener_usuario_actual`
(identifica quién es, a partir del JWT) o, si además necesita validar acceso
a un edificio puntual, de `requerir_acceso_edificio`. La regla de alcance
—Administrador General accede a todo; el resto solo a sus propios
edificios— se define una única vez acá, reutilizando `tiene_acceso_a_edificio()`
de `services/autorizacion.py`, y la reutiliza cada router nuevo en vez de
repetir el chequeo a mano.
"""

from dataclasses import dataclass, field

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import TokenInvalido, decodificar_token
from app.database import obtener_db
from app.models.usuario import Usuario
from app.services.autorizacion import tiene_acceso_a_edificio

_esquema_bearer = HTTPBearer()


@dataclass
class UsuarioAutenticado:
    """Usuario ya identificado a partir del JWT, junto con los edificios a
    los que tiene acceso (Documento Técnico, sección 5.1). `edificios`
    todavía es siempre `[]` en la práctica: se completa de verdad recién
    cuando `UsuarioEdificio` tenga su tabla real (próxima tarea)."""

    usuario: Usuario
    edificios: list = field(default_factory=list)


def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(_esquema_bearer),
    db: Session = Depends(obtener_db),
) -> UsuarioAutenticado:
    try:
        datos = decodificar_token(credenciales.credentials)
    except TokenInvalido:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o vencido")

    usuario = db.query(Usuario).filter(Usuario.email == datos.get("sub")).first()
    if not usuario or not usuario.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado o inactivo")

    return UsuarioAutenticado(usuario=usuario, edificios=datos.get("edificios", []))


def requerir_acceso_edificio(
    edificio_id: int,
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
) -> UsuarioAutenticado:
    """Se agrega como dependencia a cualquier endpoint cuya ruta incluya
    `{edificio_id}` (FastAPI resuelve el parámetro automáticamente por
    nombre) — aplica la regla de alcance de la sección 6.2 sin que el
    router tenga que volver a escribirla."""
    if not tiene_acceso_a_edificio(actual.usuario.rol, actual.edificios, edificio_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenés acceso a este edificio")
    return actual

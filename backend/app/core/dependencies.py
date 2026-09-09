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
from app.models.edificio import Departamento, Edificio, Piso
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


def requerir_acceso_financiero_edificio(
    edificio_id: int,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
) -> UsuarioAutenticado:
    """Primer caso real de un propietario/inquilino necesitando acceso de
    verdad a algo de SU edificio (ver el medio de pago) — `edificios` del
    JWT todavía está siempre vacío (ver `UsuarioAutenticado`), así que acá
    no se puede usar `tiene_acceso_a_edificio()`. Se resuelve consultando
    directo si el usuario tiene al menos un departamento (como propietario
    o inquilino) en ese edificio — el mismo dato que ya determina si "le
    corresponde" ver algo financiero de esa unidad."""
    if actual.usuario.rol == "admin_general":
        return actual

    if actual.usuario.rol == "admin_consorcio":
        edificio = db.get(Edificio, edificio_id)
        if edificio and edificio.admin_consorcio_id == actual.usuario.id:
            return actual

    if actual.usuario.rol in ("propietario", "inquilino"):
        tiene_unidad = (
            db.query(Departamento)
            .join(Piso, Piso.id == Departamento.piso_id)
            .filter(
                Piso.edificio_id == edificio_id,
                (Departamento.propietario_id == actual.usuario.id) | (Departamento.inquilino_id == actual.usuario.id),
            )
            .first()
        )
        if tiene_unidad:
            return actual

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenés acceso a este edificio")


def requerir_gestion_reclamos_edificio(
    edificio_id: int,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
) -> UsuarioAutenticado:
    """Quién GESTIONA los reclamos/OT de un edificio (ver todos, cambiar
    de estado, asignar) — Documento General 11.4: "Administrador/
    Encargado". Administrador General siempre; Administrador de Consorcio
    o Encargado, solo si son los de ESE edificio puntual
    (`Edificio.admin_consorcio_id`/`encargado_id`, este último agregado
    recién en esta tarea — antes no existía ningún vínculo real entre un
    Encargado y un edificio). Nunca el propio Propietario/Inquilino que
    reclamó — su acceso a SU reclamo puntual es otra cosa, ver
    `requerir_acceso_a_reclamo` en `routers/reclamos.py`."""
    if actual.usuario.rol == "admin_general":
        return actual

    edificio = db.get(Edificio, edificio_id)
    if not edificio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edificio no encontrado")

    if actual.usuario.rol == "admin_consorcio" and edificio.admin_consorcio_id == actual.usuario.id:
        return actual
    if actual.usuario.rol == "encargado" and edificio.encargado_id == actual.usuario.id:
        return actual

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No administrás este edificio")


def requerir_acceso_para_crear_reclamo(
    edificio_id: int,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
) -> UsuarioAutenticado:
    """Quién puede CARGAR un reclamo nuevo: cualquiera con una unidad en
    el edificio (Documento General 11.1: "el propietario o inquilino
    carga el reclamo") o quien lo gestiona (Administrador/Encargado —
    pueden notar algo y cargarlo sin esperar a que un residente lo haga).
    Superset de `requerir_gestion_reclamos_edificio`, reutilizada
    directamente en vez de repetir su lógica.

    También reutilizada, sin cambios, por `routers/edificios.py::listar_espacios_comunes`
    (Fase 3, "creación de reclamo"): el mismo grupo de gente que puede
    cargar un reclamo es exactamente el que necesita poder VER la lista
    de espacios comunes de un edificio (para reportar sobre uno) — antes
    ese GET era admin-only por error, bloqueaba a Propietario/Inquilino/
    Encargado."""
    try:
        return requerir_gestion_reclamos_edificio(edificio_id=edificio_id, db=db, actual=actual)
    except HTTPException:
        pass

    if actual.usuario.rol in ("propietario", "inquilino"):
        tiene_unidad = (
            db.query(Departamento)
            .join(Piso, Piso.id == Departamento.piso_id)
            .filter(
                Piso.edificio_id == edificio_id,
                (Departamento.propietario_id == actual.usuario.id) | (Departamento.inquilino_id == actual.usuario.id),
            )
            .first()
        )
        if tiene_unidad:
            return actual

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenés acceso a este edificio")

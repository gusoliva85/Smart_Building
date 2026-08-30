"""Router de gestión de usuarios — Documento General, sección 3.

Alta, edición, listado y baja lógica. Nunca se borra un usuario de verdad
(`DELETE`): se desactiva (`activo=False`), para no perder trazabilidad de
quién estuvo vinculado a qué edificio/unidad en el pasado.

Nota de alcance de esta tarea: por ahora solo el Administrador General
gestiona usuarios. El Documento Técnico prevé que el Administrador de
Consorcio también pueda hacerlo, acotado a su propio edificio — pero esa
restricción necesita `UsuarioEdificio` con datos reales para saber "cuál es
su edificio", y ese modelo recién se completa en la próxima tarea de esta
fase ("Estructura del edificio"). Se deja documentado acá para no perderlo
de vista, en vez de simular un alcance que hoy no se puede verificar.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.core.security import hashear_password
from app.database import obtener_db
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioEdicion, UsuarioEntrada, UsuarioSalida

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])


def _requerir_admin_general(
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
) -> UsuarioAutenticado:
    if actual.usuario.rol != "admin_general":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Por ahora solo el Administrador General gestiona usuarios",
        )
    return actual


@router.post("", response_model=UsuarioSalida, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    datos: UsuarioEntrada,
    db: Session = Depends(obtener_db),
    _: UsuarioAutenticado = Depends(_requerir_admin_general),
):
    if db.query(Usuario).filter(Usuario.email == datos.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un usuario con ese email")

    usuario = Usuario(
        nombre=datos.nombre,
        email=datos.email,
        password_hash=hashear_password(datos.password),
        rol=datos.rol,
        telefono=datos.telefono,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("", response_model=list[UsuarioSalida])
def listar_usuarios(
    db: Session = Depends(obtener_db),
    _: UsuarioAutenticado = Depends(_requerir_admin_general),
):
    return db.query(Usuario).order_by(Usuario.id).all()


@router.patch("/{usuario_id}", response_model=UsuarioSalida)
def editar_usuario(
    usuario_id: int,
    datos: UsuarioEdicion,
    db: Session = Depends(obtener_db),
    _: UsuarioAutenticado = Depends(_requerir_admin_general),
):
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(usuario, campo, valor)

    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/{usuario_id}/desactivar", response_model=UsuarioSalida)
def desactivar_usuario(
    usuario_id: int,
    db: Session = Depends(obtener_db),
    _: UsuarioAutenticado = Depends(_requerir_admin_general),
):
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    usuario.activo = False  # baja lógica — nunca se borra la fila
    db.commit()
    db.refresh(usuario)
    return usuario

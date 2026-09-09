"""Router del dominio "Reclamos" — Documento General, sección 11.

Ciclo de vida completo: crear, consultar, comentar, cambiar de estado.
La generación de una `OrdenTrabajo` a partir de un reclamo es la PRÓXIMA
tarea de esta fase — acá el reclamo vive por sí solo, sin tocar OT.

Reglas de acceso (Documento General 11.4 + decisión de esta tarea):
- **Crear**: cualquiera con una unidad en el edificio, o quien lo
  gestiona (Administrador/Encargado) — `requerir_acceso_para_crear_reclamo`.
- **Gestionar** (ver todos, cambiar el flujo normal): Administrador
  General, Administrador de Consorcio o Encargado del edificio —
  `requerir_gestion_reclamos_edificio`.
- **Un reclamo puntual** (detalle, comentar): quien lo creó, o gestión.
- **Cambiar de estado**: gestión mueve el flujo normal completo; la
  excepción `resuelto → en_curso` (reabrir) la puede hacer TAMBIÉN quien
  lo creó, no solo gestión.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import (
    UsuarioAutenticado,
    obtener_usuario_actual,
    requerir_acceso_para_crear_reclamo,
    requerir_gestion_reclamos_edificio,
)
from app.database import obtener_db
from app.models.edificio import Departamento, EspacioComun
from app.models.reclamo import Reclamo, ReclamoComentario, ReclamoFoto
from app.schemas.reclamo import (
    ReclamoComentarioEntrada,
    ReclamoComentarioSalida,
    ReclamoEntrada,
    ReclamoEstadoEntrada,
    ReclamoSalida,
)
from app.services.reclamos import transicion_valida

router = APIRouter(prefix="/api/edificios", tags=["reclamos"])
router_reclamos = APIRouter(prefix="/api", tags=["reclamos"])


@router.post("/{edificio_id}/reclamos", response_model=ReclamoSalida, status_code=status.HTTP_201_CREATED)
def crear_reclamo(
    edificio_id: int,
    datos: ReclamoEntrada,
    actual: UsuarioAutenticado = Depends(requerir_acceso_para_crear_reclamo),
    db: Session = Depends(obtener_db),
):
    if datos.departamento_id is not None:
        depto = db.get(Departamento, datos.departamento_id)
        if not depto or depto.piso.edificio_id != edificio_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="departamento_id debe pertenecer a este edificio")
    if datos.espacio_comun_id is not None:
        espacio = db.get(EspacioComun, datos.espacio_comun_id)
        if not espacio or espacio.edificio_id != edificio_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="espacio_comun_id debe pertenecer a este edificio")

    reclamo = Reclamo(
        edificio_id=edificio_id,
        departamento_id=datos.departamento_id,
        espacio_comun_id=datos.espacio_comun_id,
        descripcion=datos.descripcion,
        prioridad=datos.prioridad,
        creado_por_id=actual.usuario.id,
    )
    db.add(reclamo)
    db.flush()
    for url in datos.fotos:
        db.add(ReclamoFoto(reclamo_id=reclamo.id, url=url))
    db.commit()
    db.refresh(reclamo)
    return reclamo


@router.get("/{edificio_id}/reclamos", response_model=list[ReclamoSalida])
def listar_reclamos_del_edificio(
    edificio_id: int,
    estado: str | None = None,
    prioridad: str | None = None,
    actual: UsuarioAutenticado = Depends(requerir_gestion_reclamos_edificio),
    db: Session = Depends(obtener_db),
):
    """Solo gestión (Administrador/Encargado) — el listado completo del
    edificio, nunca lo ve un Propietario/Inquilino de a uno (ellos usan
    `GET /api/mis-reclamos`)."""
    consulta = db.query(Reclamo).filter(Reclamo.edificio_id == edificio_id)
    if estado is not None:
        consulta = consulta.filter(Reclamo.estado == estado)
    if prioridad is not None:
        consulta = consulta.filter(Reclamo.prioridad == prioridad)
    return consulta.order_by(Reclamo.creado_en.desc()).all()


@router_reclamos.get("/mis-reclamos", response_model=list[ReclamoSalida])
def listar_mis_reclamos(
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    """Documento General 11.4: "visible en todo momento para quien lo
    cargó" — cualquier rol puede tener reclamos propios (un Administrador
    o Encargado también pueden haber cargado uno)."""
    return (
        db.query(Reclamo)
        .filter(Reclamo.creado_por_id == actual.usuario.id)
        .order_by(Reclamo.creado_en.desc())
        .all()
    )


def _obtener_reclamo_o_404(reclamo_id: int, db: Session) -> Reclamo:
    reclamo = db.get(Reclamo, reclamo_id)
    if not reclamo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reclamo no encontrado")
    return reclamo


def _es_gestion_del_edificio(edificio_id: int, actual: UsuarioAutenticado, db: Session) -> bool:
    try:
        requerir_gestion_reclamos_edificio(edificio_id=edificio_id, db=db, actual=actual)
        return True
    except HTTPException:
        return False


def _verificar_acceso_a_reclamo(reclamo: Reclamo, actual: UsuarioAutenticado, db: Session) -> bool:
    """Quien lo creó, o quien gestiona el edificio — nunca un tercero
    ajeno. Documento General 11.6 también menciona al "proveedor
    asignado", que queda fuera hasta que exista un vínculo real
    Proveedor↔Usuario (Fase 7, ver nota de la Tarea 3 de esta fase)."""
    if reclamo.creado_por_id == actual.usuario.id:
        return True
    return _es_gestion_del_edificio(reclamo.edificio_id, actual, db)


@router_reclamos.get("/reclamos/{reclamo_id}", response_model=ReclamoSalida)
def obtener_reclamo(
    reclamo_id: int,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    reclamo = _obtener_reclamo_o_404(reclamo_id, db)
    if not _verificar_acceso_a_reclamo(reclamo, actual, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenés acceso a este reclamo")
    return reclamo


@router_reclamos.patch("/reclamos/{reclamo_id}/estado", response_model=ReclamoSalida)
def cambiar_estado_reclamo(
    reclamo_id: int,
    datos: ReclamoEstadoEntrada,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    reclamo = _obtener_reclamo_o_404(reclamo_id, db)

    if not transicion_valida(reclamo.estado, datos.estado):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede pasar de '{reclamo.estado}' a '{datos.estado}'",
        )

    es_gestion = _es_gestion_del_edificio(reclamo.edificio_id, actual, db)
    es_reapertura = reclamo.estado == "resuelto" and datos.estado == "en_curso"

    if es_reapertura:
        # Única excepción: además de gestión, quien lo creó puede reabrir
        # confirmando que el problema sigue (Fase 3, Tarea 1).
        es_creador = reclamo.creado_por_id == actual.usuario.id
        if not (es_gestion or es_creador):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No podés reabrir este reclamo")
    elif not es_gestion:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el Administrador o Encargado del edificio puede mover este reclamo")

    reclamo.estado = datos.estado
    db.commit()
    db.refresh(reclamo)
    return reclamo


@router_reclamos.post(
    "/reclamos/{reclamo_id}/comentarios",
    response_model=ReclamoComentarioSalida,
    status_code=status.HTTP_201_CREATED,
)
def comentar_reclamo(
    reclamo_id: int,
    datos: ReclamoComentarioEntrada,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    reclamo = _obtener_reclamo_o_404(reclamo_id, db)
    if not _verificar_acceso_a_reclamo(reclamo, actual, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenés acceso a este reclamo")

    comentario = ReclamoComentario(reclamo_id=reclamo.id, autor_id=actual.usuario.id, texto=datos.texto)
    db.add(comentario)
    db.commit()
    db.refresh(comentario)
    return comentario

"""Router del dominio "Órdenes de trabajo" — Documento General, sección 10;
Documento Técnico, sección 12.

Por ahora, en esta tarea, solo la generación de una OT a partir de un
reclamo existente (Documento General 10.2: una de las tres formas de
originar una orden, junto con la manual y la automática por vencimiento
de un `Activo` — esas dos quedan para la próxima tarea de esta fase,
"gestión de órdenes de trabajo").

También vive acá `sincronizar_reclamo_al_resolver_ot()`: cuando una OT
pasa a `resuelta` y está vinculada a un `Reclamo`, el reclamo pasa
automáticamente a `resuelto` — mismo mecanismo que un cambio de estado
manual (usa `transicion_valida()`, nunca fuerza la transición si el
reclamo ya quedó en otro estado terminal por otra vía). Queda lista acá
aunque el único lugar que hoy la puede disparar de verdad — el endpoint
que cambia el estado de una OT — es tarea de la próxima entrada del
Roadmap; mientras tanto se prueba llamándola directo (`test_ordenes_
trabajo.py`).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.database import obtener_db
from app.models.ordentrabajo import OrdenTrabajo
from app.models.reclamo import Reclamo
from app.models.usuario import Usuario
from app.routers.reclamos import _es_gestion_del_edificio, _obtener_reclamo_o_404
from app.schemas.ordentrabajo import OrdenTrabajoDesdeReclamoEntrada, OrdenTrabajoSalida
from app.services.reclamos import transicion_valida

router = APIRouter(prefix="/api", tags=["ordenes_trabajo"])


def sincronizar_reclamo_al_resolver_ot(orden: OrdenTrabajo, db: Session) -> None:
    """No comitea — es responsabilidad de quien llama (mismo criterio que
    el resto de las funciones de sincronización del proyecto)."""
    if orden.reclamo_id is None:
        return
    reclamo = db.get(Reclamo, orden.reclamo_id)
    if reclamo and transicion_valida(reclamo.estado, "resuelto"):
        reclamo.estado = "resuelto"


@router.post(
    "/reclamos/{reclamo_id}/orden-trabajo",
    response_model=OrdenTrabajoSalida,
    status_code=status.HTTP_201_CREATED,
)
def generar_orden_trabajo_desde_reclamo(
    reclamo_id: int,
    datos: OrdenTrabajoDesdeReclamoEntrada,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    reclamo = _obtener_reclamo_o_404(reclamo_id, db)
    if not _es_gestion_del_edificio(reclamo.edificio_id, actual, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el Administrador o Encargado del edificio puede generar una orden de trabajo",
        )

    if reclamo.estado in ("resuelto", "cerrado"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede generar una orden de trabajo para un reclamo en estado '{reclamo.estado}'",
        )

    ot_activa = (
        db.query(OrdenTrabajo)
        .filter(OrdenTrabajo.reclamo_id == reclamo.id, OrdenTrabajo.estado != "resuelta")
        .first()
    )
    if ot_activa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una orden de trabajo activa para este reclamo",
        )

    if datos.encargado_id is not None:
        encargado = db.get(Usuario, datos.encargado_id)
        if not encargado or encargado.rol != "encargado":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="encargado_id debe corresponder a un usuario con rol encargado",
            )

    orden = OrdenTrabajo(
        edificio_id=reclamo.edificio_id,
        espacio_comun_id=reclamo.espacio_comun_id,
        reclamo_id=reclamo.id,
        tipo=datos.tipo,
        prioridad=datos.prioridad or reclamo.prioridad,
        descripcion=datos.descripcion or reclamo.descripcion,
        encargado_id=datos.encargado_id,
        proveedor_id=datos.proveedor_id,
    )
    db.add(orden)

    # Generar la OT es, en los hechos, el acto de asignar el reclamo — si
    # todavía estaba "recibido", pasa a "asignado" acá mismo (nunca se
    # fuerza si ya estaba en otro estado por otra vía).
    if transicion_valida(reclamo.estado, "asignado"):
        reclamo.estado = "asignado"

    db.commit()
    db.refresh(orden)
    return orden

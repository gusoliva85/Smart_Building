"""Router del dominio "Órdenes de trabajo" — Documento General, sección 10;
Documento Técnico, sección 12.

Dos formas de originar una orden (la tercera, automática por vencimiento
de un `Activo`, llega recién en la Fase 4): **desde un reclamo**
(`generar_orden_trabajo_desde_reclamo`, Fase 3 Tarea 5) y **manual**
(`crear_orden_trabajo_manual`, esta tarea) — Documento General 10.2.
De acá en más, gestión completa: listar, ver detalle, asignar/reasignar,
cambiar de estado (`pendiente`/`en_curso`/`resuelta`, propio de OT — ver
nota del modelo) y cargar evidencia.

Acceso — igual que reclamos, reutilizando la misma dependencia
(`requerir_gestion_reclamos_edificio` ya está documentada para cubrir
"reclamos/OT de un edificio" desde que se escribió, Fase 3 Tarea 4):
Administrador General, Administrador de Consorcio o Encargado del
edificio. Nunca un Propietario/Inquilino — una OT es una herramienta
interna de gestión, no algo que el residente vea directo (su ventana es
el reclamo, que sí sigue siendo suyo).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import UsuarioAutenticado, obtener_usuario_actual, requerir_gestion_reclamos_edificio
from app.database import obtener_db
from app.models.edificio import EspacioComun
from app.models.ordentrabajo import OrdenTrabajo, OtEvidencia
from app.models.reclamo import Reclamo
from app.models.usuario import Usuario
from app.routers.reclamos import _es_gestion_del_edificio, _obtener_reclamo_o_404
from app.schemas.ordentrabajo import (
    OrdenTrabajoAsignacionEntrada,
    OrdenTrabajoDesdeReclamoEntrada,
    OrdenTrabajoEstadoEntrada,
    OrdenTrabajoManualEntrada,
    OrdenTrabajoSalida,
    OtEvidenciaEntrada,
    OtEvidenciaSalida,
)
from app.services.reclamos import transicion_valida, transicion_valida_ot

router = APIRouter(prefix="/api", tags=["ordenes_trabajo"])
router_edificio = APIRouter(prefix="/api/edificios", tags=["ordenes_trabajo"])


def _sincronizar_reclamo_con_ot(orden: OrdenTrabajo, estado_nuevo: str, db: Session) -> None:
    """No comitea — es responsabilidad de quien llama (mismo criterio que
    el resto de las funciones de sincronización del proyecto)."""
    if orden.reclamo_id is None:
        return
    reclamo = db.get(Reclamo, orden.reclamo_id)
    if reclamo and transicion_valida(reclamo.estado, estado_nuevo):
        reclamo.estado = estado_nuevo


def sincronizar_reclamo_al_resolver_ot(orden: OrdenTrabajo, db: Session) -> None:
    """Cuando la OT pasa a `resuelta`, el reclamo vinculado pasa a
    `resuelto` — pero eso solo es una transición válida si el reclamo ya
    estaba `en_curso` (ver `TRANSICIONES_VALIDAS` de `Reclamo`); por eso
    `cambiar_estado_orden_trabajo` también sincroniza al pasar la OT a
    `en_curso` (`asignado → en_curso`), para que el reclamo vaya
    caminando en paralelo y esto tenga efecto real en el camino feliz."""
    _sincronizar_reclamo_con_ot(orden, "resuelto", db)


def _validar_encargado_o_400(encargado_id: int, db: Session) -> None:
    encargado = db.get(Usuario, encargado_id)
    if not encargado or encargado.rol != "encargado":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="encargado_id debe corresponder a un usuario con rol encargado",
        )


def _obtener_ot_o_404(orden_id: int, db: Session) -> OrdenTrabajo:
    orden = db.get(OrdenTrabajo, orden_id)
    if not orden:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de trabajo no encontrada")
    return orden


def _verificar_gestion_de_la_ot(orden: OrdenTrabajo, actual: UsuarioAutenticado, db: Session) -> None:
    if not _es_gestion_del_edificio(orden.edificio_id, actual, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el Administrador o Encargado del edificio puede gestionar esta orden de trabajo",
        )


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
        _validar_encargado_o_400(datos.encargado_id, db)

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


@router_edificio.post(
    "/{edificio_id}/ordenes-trabajo",
    response_model=OrdenTrabajoSalida,
    status_code=status.HTTP_201_CREATED,
)
def crear_orden_trabajo_manual(
    edificio_id: int,
    datos: OrdenTrabajoManualEntrada,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(requerir_gestion_reclamos_edificio),
):
    """Sin reclamo previo — mantenimiento preventivo/programado, o
    cualquier trabajo que gestión decide cargar directo."""
    if datos.espacio_comun_id is not None:
        espacio = db.get(EspacioComun, datos.espacio_comun_id)
        if not espacio or espacio.edificio_id != edificio_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="espacio_comun_id debe pertenecer a este edificio")
    if datos.encargado_id is not None:
        _validar_encargado_o_400(datos.encargado_id, db)

    orden = OrdenTrabajo(
        edificio_id=edificio_id,
        espacio_comun_id=datos.espacio_comun_id,
        activo_id=datos.activo_id,
        tipo=datos.tipo,
        prioridad=datos.prioridad,
        descripcion=datos.descripcion,
        encargado_id=datos.encargado_id,
        proveedor_id=datos.proveedor_id,
    )
    db.add(orden)
    db.commit()
    db.refresh(orden)
    return orden


@router_edificio.get("/{edificio_id}/ordenes-trabajo", response_model=list[OrdenTrabajoSalida])
def listar_ordenes_trabajo(
    edificio_id: int,
    estado: str | None = None,
    tipo: str | None = None,
    prioridad: str | None = None,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(requerir_gestion_reclamos_edificio),
):
    consulta = db.query(OrdenTrabajo).filter(OrdenTrabajo.edificio_id == edificio_id)
    if estado is not None:
        consulta = consulta.filter(OrdenTrabajo.estado == estado)
    if tipo is not None:
        consulta = consulta.filter(OrdenTrabajo.tipo == tipo)
    if prioridad is not None:
        consulta = consulta.filter(OrdenTrabajo.prioridad == prioridad)
    return consulta.order_by(OrdenTrabajo.creado_en.desc()).all()


@router.get("/ordenes-trabajo/{orden_id}", response_model=OrdenTrabajoSalida)
def obtener_orden_trabajo(
    orden_id: int,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    orden = _obtener_ot_o_404(orden_id, db)
    _verificar_gestion_de_la_ot(orden, actual, db)
    return orden


@router.patch("/ordenes-trabajo/{orden_id}/asignacion", response_model=OrdenTrabajoSalida)
def asignar_orden_trabajo(
    orden_id: int,
    datos: OrdenTrabajoAsignacionEntrada,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    """Asignar o reasignar en cualquier momento del ciclo de vida (salvo
    ya `resuelta`, que queda archivada tal cual se cerró — mismo criterio
    de "el antecedente no se reescribe" que rige el resto del proyecto).
    Mandar un campo en `null` desasigna de verdad; no mandarlo lo deja
    como está (`exclude_unset`)."""
    orden = _obtener_ot_o_404(orden_id, db)
    _verificar_gestion_de_la_ot(orden, actual, db)
    if orden.estado == "resuelta":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede reasignar una orden de trabajo ya resuelta")

    cambios = datos.model_dump(exclude_unset=True)
    if cambios.get("encargado_id") is not None:
        _validar_encargado_o_400(cambios["encargado_id"], db)
    for campo, valor in cambios.items():
        setattr(orden, campo, valor)

    db.commit()
    db.refresh(orden)
    return orden


@router.patch("/ordenes-trabajo/{orden_id}/estado", response_model=OrdenTrabajoSalida)
def cambiar_estado_orden_trabajo(
    orden_id: int,
    datos: OrdenTrabajoEstadoEntrada,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    orden = _obtener_ot_o_404(orden_id, db)
    _verificar_gestion_de_la_ot(orden, actual, db)

    if not transicion_valida_ot(orden.estado, datos.estado):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede pasar de '{orden.estado}' a '{datos.estado}'",
        )

    if datos.estado == "en_curso":
        if orden.encargado_id is None and orden.proveedor_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede pasar a 'en_curso' sin un encargado o proveedor asignado",
            )
        orden.fecha_inicio = datetime.now(timezone.utc)
        _sincronizar_reclamo_con_ot(orden, "en_curso", db)

    orden.estado = datos.estado

    if datos.estado == "resuelta":
        orden.fecha_cierre = datetime.now(timezone.utc)
        if datos.costo is not None:
            orden.costo = datos.costo
        sincronizar_reclamo_al_resolver_ot(orden, db)

    db.commit()
    db.refresh(orden)
    return orden


@router.post(
    "/ordenes-trabajo/{orden_id}/evidencia",
    response_model=OtEvidenciaSalida,
    status_code=status.HTTP_201_CREATED,
)
def agregar_evidencia_orden_trabajo(
    orden_id: int,
    datos: OtEvidenciaEntrada,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    orden = _obtener_ot_o_404(orden_id, db)
    _verificar_gestion_de_la_ot(orden, actual, db)

    evidencia = OtEvidencia(orden_trabajo_id=orden.id, url=datos.url, momento=datos.momento, subido_por_id=actual.usuario.id)
    db.add(evidencia)
    db.commit()
    db.refresh(evidencia)
    return evidencia

"""Presupuestos y facturas (`F2-T15`, segunda mitad).

Seis endpoints:

- ``GET    /edificios/{id}/presupuestos``                   — listar, con filtro
- ``POST   /edificios/{id}/presupuestos``                   — cargar una cotizacion
- ``PATCH  /edificios/{id}/presupuestos/{pres}``            — aprobar o rechazar
- ``DELETE /edificios/{id}/presupuestos/{pres}``            — borrar uno pendiente
- ``GET    /edificios/{id}/gastos/{gasto}/facturas``        — los comprobantes
- ``POST   /edificios/{id}/gastos/{gasto}/facturas`` · ``DELETE``

============================================================================
LAS FACTURAS CUELGAN DEL GASTO, NO DEL EDIFICIO
============================================================================

Y eso se ve en la ruta. Una factura sin gasto no existe — lo que se audita es
el gasto y la factura es lo que lo respalda— asi que la ruta pasa por el gasto
y de ahi sale el edificio. Un endpoint `/edificios/{id}/facturas` permitiria
cargar una factura sin decir de que gasto es, que es exactamente lo que el
modelo prohibe.

============================================================================
CARGAR UNA FACTURA ES OPCIONAL
============================================================================

Confirmado el 2026-11-13: **un gasto sin comprobante es un gasto valido**.
Muchos gastos reales de un consorcio no tienen uno formal — el arreglo que hizo
un vecino, el flete en efectivo— y lo que se carga no tiene que ser una factura
fiscal: un recibo, un remito, un ticket. Hasta el numero es opcional.

Nada en estos endpoints exige una factura para nada, y ningun listado trata la
ausencia como un problema.
"""

import logging
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core import errores
from app.core.dependencies import SesionDB, SoloAdministradores
from app.models.edificio import Edificio
from app.models.finanzas import Factura, Gasto, Presupuesto
from app.routers.edificios import buscar_edificio_que_administra
from app.routers.gastos import _buscar_gasto
from app.schemas.tesoreria import (
    FacturaCrear,
    FacturaLeer,
    ListadoDeFacturas,
    ListadoDePresupuestos,
    PresupuestoCrear,
    PresupuestoDecidir,
    PresupuestoLeer,
)
from app.services import presupuestos as servicio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edificios", tags=["Presupuestos y facturas"])

CERO = Decimal("0.00")


# ===========================================================================
# HELPERS
# ===========================================================================


def _leer_presupuesto(presupuesto: Presupuesto) -> PresupuestoLeer:
    return PresupuestoLeer(
        id=presupuesto.id,
        descripcion=presupuesto.descripcion,
        monto=presupuesto.monto,
        fecha=presupuesto.fecha,
        estado=presupuesto.estado,
        estados_siguientes=list(servicio.estados_siguientes(presupuesto.estado)),
        proveedor_id=presupuesto.proveedor_id,
        gasto_id=presupuesto.gasto_id,
        # El monto del gasto viaja al lado del presupuestado: la comparacion
        # entre lo que se cotizo y lo que se pago es para lo que existe el
        # vinculo, y pedirla en otra consulta la volveria opcional.
        monto_del_gasto=presupuesto.gasto.monto if presupuesto.gasto else None,
        decidido_por=(
            presupuesto.decidido_por.nombre if presupuesto.decidido_por else None
        ),
        decidido_en=presupuesto.decidido_en,
        creado_en=presupuesto.creado_en,
    )


def _buscar_presupuesto(
    db: Session, edificio: Edificio, presupuesto_id: int
) -> Presupuesto:
    presupuesto = db.scalars(
        select(Presupuesto).where(
            Presupuesto.id == presupuesto_id,
            Presupuesto.edificio_id == edificio.id,
        )
    ).first()

    if presupuesto is None:
        raise errores.ErrorDeNegocio(
            errores.NO_ENCONTRADO_EN_EL_EDIFICIO, que="ese presupuesto"
        )

    return presupuesto


def _guardar(db: Session, que: str, descripcion: str) -> None:
    try:
        db.commit()
    except (IntegrityError, SQLAlchemyError):
        db.rollback()
        logger.exception("Fallo al guardar: %s", descripcion)
        raise errores.ErrorDeNegocio(errores.ERROR_AL_GUARDAR, que=que) from None


# ===========================================================================
# PRESUPUESTOS
# ===========================================================================


@router.get(
    "/{edificio_id}/presupuestos",
    response_model=ListadoDePresupuestos,
    summary="Los presupuestos del edificio",
)
def listar(
    edificio_id: int,
    quien_consulta: SoloAdministradores,
    db: SesionDB,
    estado: str | None = None,
) -> ListadoDePresupuestos:
    """Los presupuestos, de la cotizacion mas nueva a la mas vieja.

    `pendientes` viaja aparte del total porque es el numero que importa: son
    los que estan esperando una decision, y es lo que la pantalla muestra como
    aviso. Contarlos en el navegador daria el total de lo que se mostro.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_consulta)

    if estado is not None and not servicio.es_estado_valido(estado):
        raise errores.ErrorDeNegocio(errores.ESTADO_DE_PRESUPUESTO_INVALIDO)

    consulta = select(Presupuesto).where(Presupuesto.edificio_id == edificio.id)
    if estado is not None:
        consulta = consulta.where(Presupuesto.estado == estado)

    filas = db.scalars(
        consulta.order_by(Presupuesto.fecha.desc(), Presupuesto.id.desc())
    ).all()

    return ListadoDePresupuestos(
        cantidad=len(filas),
        pendientes=sum(1 for f in filas if f.estado == servicio.PENDIENTE),
        presupuestos=[_leer_presupuesto(f) for f in filas],
    )


@router.post(
    "/{edificio_id}/presupuestos",
    response_model=PresupuestoLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Cargar un presupuesto recibido",
)
def crear(
    edificio_id: int,
    datos: PresupuestoCrear,
    quien_carga: SoloAdministradores,
    db: SesionDB,
) -> PresupuestoLeer:
    """Carga una cotizacion. **Nace pendiente, siempre.**

    **No se exige ninguna cantidad de presupuestos ni se objeta tener varios
    del mismo arreglo**, que es justamente para lo que sirven: compararlos.
    Ninguna norma argentina pide un minimo antes de aprobar un gasto — lo fija
    el reglamento de cada consorcio— asi que el sistema no impone nada.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_carga)

    presupuesto = Presupuesto(
        edificio_id=edificio.id,
        descripcion=datos.descripcion,
        monto=datos.monto,
        fecha=datos.fecha,
        proveedor_id=datos.proveedor_id,
        estado=servicio.PENDIENTE,
    )
    db.add(presupuesto)
    _guardar(db, "el presupuesto", f"alta de presupuesto en el edificio {edificio_id}")

    logger.info(
        "Presupuesto %s cargado en el edificio %s (%s) por %s",
        presupuesto.id,
        edificio_id,
        presupuesto.monto,
        quien_carga.email,
    )
    return _leer_presupuesto(presupuesto)


@router.patch(
    "/{edificio_id}/presupuestos/{presupuesto_id}",
    response_model=PresupuestoLeer,
    summary="Aprobar o rechazar un presupuesto",
)
def decidir(
    edificio_id: int,
    presupuesto_id: int,
    datos: PresupuestoDecidir,
    quien_decide: SoloAdministradores,
    db: SesionDB,
) -> PresupuestoLeer:
    """Registra la decision, y con ella quien la tomo y cuando.

    **La decision no se cambia despues.** Si se aprobo el equivocado, lo que
    corresponde es cargar el presupuesto nuevo y decidir sobre ese: cual se
    habia elegido es informacion que un consorcista puede pedir ver, y
    reescribirla la borra.

    `gasto_id` es opcional y **solo se admite al aprobar**. Un presupuesto
    rechazado ligado a un gasto diria "no elegimos esto" y "esto es lo que
    gastamos" a la vez — lo ataja tambien un CHECK de la base, pero el error de
    aca explica por que.

    Se puede aprobar ahora y vincular despues: el gasto normalmente se carga
    cuando llega la factura, no cuando se acepta el presupuesto.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_decide)
    presupuesto = _buscar_presupuesto(db, edificio, presupuesto_id)

    if not servicio.transicion_valida(presupuesto.estado, datos.estado):
        raise errores.ErrorDeNegocio(
            errores.PRESUPUESTO_YA_DECIDIDO, estado=presupuesto.estado
        )

    if datos.gasto_id is not None:
        if not servicio.puede_vincularse_a_un_gasto(datos.estado):
            raise errores.ErrorDeNegocio(errores.PRESUPUESTO_SIN_APROBAR)
        # El gasto se busca dentro del edificio ya verificado, igual que en
        # todos los demas modulos: un gasto de otro consorcio no entra.
        _buscar_gasto(db, edificio, datos.gasto_id)

    presupuesto.estado = datos.estado
    presupuesto.gasto_id = datos.gasto_id
    presupuesto.decidido_por_id = quien_decide.id
    presupuesto.decidido_en = datetime.now()

    _guardar(db, "la decisión", f"decision sobre el presupuesto {presupuesto_id}")

    logger.info(
        "Presupuesto %s del edificio %s %s por %s%s",
        presupuesto_id,
        edificio_id,
        datos.estado,
        quien_decide.email,
        f" (gasto {datos.gasto_id})" if datos.gasto_id else "",
    )
    return _leer_presupuesto(presupuesto)


@router.delete(
    "/{edificio_id}/presupuestos/{presupuesto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Borrar un presupuesto que todavía no se decidió",
)
def borrar(
    edificio_id: int,
    presupuesto_id: int,
    quien_borra: SoloAdministradores,
    db: SesionDB,
) -> None:
    """Borra un presupuesto **pendiente**, para el caso de haberlo cargado mal.

    **Uno ya decidido no se borra**, y es la misma razon por la que la decision
    no se reescribe: el registro de que se cotizo y que se eligio es lo que
    permite explicar un gasto meses despues. Borrar el rechazado dejaria la
    aprobacion sin contexto — "aprobamos este" sin los otros dos no dice nada.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_borra)
    presupuesto = _buscar_presupuesto(db, edificio, presupuesto_id)

    if presupuesto.esta_decidido:
        raise errores.ErrorDeNegocio(
            errores.PRESUPUESTO_YA_DECIDIDO, estado=presupuesto.estado
        )

    db.delete(presupuesto)
    _guardar(db, "el presupuesto", f"baja del presupuesto {presupuesto_id}")

    logger.info(
        "Presupuesto %s del edificio %s borrado por %s",
        presupuesto_id,
        edificio_id,
        quien_borra.email,
    )


# ===========================================================================
# FACTURAS
# ===========================================================================


@router.get(
    "/{edificio_id}/gastos/{gasto_id}/facturas",
    response_model=ListadoDeFacturas,
    summary="Los comprobantes de un gasto",
)
def listar_facturas(
    edificio_id: int,
    gasto_id: int,
    quien_consulta: SoloAdministradores,
    db: SesionDB,
) -> ListadoDeFacturas:
    """Los comprobantes cargados y lo que suman contra el monto del gasto.

    **Una lista vacia es una respuesta normal, no un problema.** Cargar un
    comprobante es opcional.

    El total facturado viaja al lado del monto del gasto porque **la diferencia
    entre los dos es informacion**: una factura puede traer un ajuste, y un
    gasto puede cubrirse con dos facturas. No se valida que coincidan.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_consulta)
    gasto = _buscar_gasto(db, edificio, gasto_id)

    filas = db.scalars(
        select(Factura)
        .where(Factura.gasto_id == gasto.id)
        .order_by(Factura.fecha.desc(), Factura.id.desc())
    ).all()

    return ListadoDeFacturas(
        cantidad=len(filas),
        total_facturado=sum((f.monto for f in filas), CERO),
        monto_del_gasto=gasto.monto,
        facturas=[FacturaLeer.model_validate(f) for f in filas],
    )


@router.post(
    "/{edificio_id}/gastos/{gasto_id}/facturas",
    response_model=FacturaLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Cargar un comprobante de un gasto",
)
def crear_factura(
    edificio_id: int,
    gasto_id: int,
    datos: FacturaCrear,
    quien_carga: SoloAdministradores,
    db: SesionDB,
) -> FacturaLeer:
    """Carga un comprobante contra el gasto.

    **Casi todo es opcional**: el numero, el proveedor y el archivo. Lo unico
    que hace falta es el monto y la fecha. Un recibo escrito a mano no tiene
    numero, y exigirlo haria que alguien escriba "sin numero" para poder
    guardar el dato que si tiene.

    Lo que si se ataja es **el mismo numero dos veces en el mismo gasto**: es el
    error de doble carga mas facil de cometer, dos personas archivando el mismo
    papel. Con numero vacio no aplica, porque dos recibos sin numero son dos
    comprobantes distintos.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_carga)
    gasto = _buscar_gasto(db, edificio, gasto_id)

    if datos.numero is not None:
        repetida = db.scalars(
            select(Factura).where(
                Factura.gasto_id == gasto.id, Factura.numero == datos.numero
            )
        ).first()
        if repetida is not None:
            raise errores.ErrorDeNegocio(
                errores.FACTURA_REPETIDA, numero=datos.numero
            )

    factura = Factura(
        gasto_id=gasto.id,
        numero=datos.numero,
        monto=datos.monto,
        fecha=datos.fecha,
        proveedor_id=datos.proveedor_id,
        archivo_url=datos.archivo_url,
    )
    db.add(factura)
    _guardar(db, "el comprobante", f"alta de factura del gasto {gasto_id}")

    logger.info(
        "Factura %s cargada en el gasto %s del edificio %s por %s",
        factura.id,
        gasto_id,
        edificio_id,
        quien_carga.email,
    )
    return FacturaLeer.model_validate(factura)


@router.delete(
    "/{edificio_id}/gastos/{gasto_id}/facturas/{factura_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Borrar un comprobante mal cargado",
)
def borrar_factura(
    edificio_id: int,
    gasto_id: int,
    factura_id: int,
    quien_borra: SoloAdministradores,
    db: SesionDB,
) -> None:
    """Saca un comprobante del gasto.

    Se borra de verdad, igual que un gasto mal cargado: un comprobante cargado
    por error no es un hecho historico que convenga conservar. **El gasto no se
    toca**: borrar su factura no lo anula ni lo modifica — son dos cosas
    distintas, y el gasto puede existir sin comprobante.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_borra)
    gasto = _buscar_gasto(db, edificio, gasto_id)

    factura = db.scalars(
        select(Factura).where(
            Factura.id == factura_id, Factura.gasto_id == gasto.id
        )
    ).first()
    if factura is None:
        raise errores.ErrorDeNegocio(
            errores.NO_ENCONTRADO_EN_EL_EDIFICIO, que="ese comprobante"
        )

    db.delete(factura)
    _guardar(db, "el comprobante", f"baja de la factura {factura_id}")

    logger.info(
        "Factura %s del gasto %s borrada por %s",
        factura_id,
        gasto_id,
        quien_borra.email,
    )

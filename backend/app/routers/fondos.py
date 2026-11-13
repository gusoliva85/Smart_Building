"""Fondos y caja chica (`F2-T15`, primera mitad).

Siete endpoints, todos bajo el edificio:

- ``GET    /edificios/{id}/fondos``                      — listar con saldo
- ``POST   /edificios/{id}/fondos``                      — crear un fondo
- ``PATCH  /edificios/{id}/fondos/{fondo}``              — editar / desactivar
- ``GET    /edificios/{id}/fondos/{fondo}/movimientos``  — el historial
- ``POST   /edificios/{id}/fondos/{fondo}/movimientos``  — registrar uno
- ``DELETE /edificios/{id}/fondos/{fondo}/movimientos/{mov}`` — corregir
- ``GET    /edificios/{id}/caja`` · ``PUT`` · ``POST /caja/movimientos`` · ``DELETE``

============================================================================
LOS DOS JUNTOS, Y POR QUE
============================================================================

Un fondo y una caja chica comparten el mecanismo — movimientos de ingreso y
egreso con el mismo catalogo de tipos— y se diferencian **solo en contra que se
mide el resultado**: un fondo acumula, una caja se compara con su monto fijo.
Separarlos en dos routers duplicaria las mismas cuatro operaciones.

============================================================================
NINGUN SALDO SE GUARDA
============================================================================

Cada respuesta calcula el saldo desde los movimientos, en el momento. No hay
columna que mantener ni que pueda desincronizarse. El costo es una suma por
fondo, que para la cantidad de movimientos que tiene un consorcio es nada.

============================================================================
UN MOVIMIENTO SE BORRA, NO SE EDITA
============================================================================

Hay `DELETE` y no hay `PATCH`. Un movimiento mal cargado es un error de tipeo y
lo que corresponde es sacarlo y volver a cargarlo bien; editarle el monto o el
tipo a un movimiento ya registrado es reescribir el historial de la plata, y
ese historial es justamente para lo que existe el libro de movimientos. Es el
mismo criterio que el borrado de un gasto.
"""

import logging
from decimal import Decimal

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core import errores
from app.core.dependencies import SesionDB, SoloAdministradores
from app.models.edificio import Edificio
from app.models.finanzas import Caja, Fondo, MovimientoCaja, MovimientoFondo
from app.models.usuario import Usuario
from app.routers.edificios import buscar_edificio_que_administra
from app.schemas.tesoreria import (
    CajaGuardar,
    CajaLeer,
    FondoCrear,
    FondoEditar,
    FondoLeer,
    ListadoDeFondos,
    MovimientoCrear,
    MovimientoLeer,
)
from app.services import autorizacion, caja as servicio_caja, fondos

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edificios", tags=["Fondos y caja"])

CERO = Decimal("0.00")


# ===========================================================================
# HELPERS
# ===========================================================================


def _a_movimientos(filas) -> list[fondos.Movimiento]:
    """Pasa filas del ORM a la estructura que entiende el servicio.

    El servicio no sabe que existe SQLAlchemy — por eso se puede probar con
    numeros escritos a mano— asi que la traduccion vive aca.
    """
    return [fondos.Movimiento(tipo=f.tipo, monto=f.monto) for f in filas]


def _leer_movimiento(movimiento) -> MovimientoLeer:
    return MovimientoLeer(
        id=movimiento.id,
        tipo=movimiento.tipo,
        tipo_etiqueta=fondos.etiqueta(movimiento.tipo),
        monto=movimiento.monto,
        fecha=movimiento.fecha,
        descripcion=movimiento.descripcion,
        registrado_por=(
            movimiento.registrado_por.nombre if movimiento.registrado_por else ""
        ),
        creado_en=movimiento.creado_en,
    )


def _leer_fondo(fondo: Fondo) -> FondoLeer:
    saldo = fondos.calcular_saldo(_a_movimientos(fondo.movimientos))
    return FondoLeer(
        id=fondo.id,
        nombre=fondo.nombre,
        descripcion=fondo.descripcion,
        activo=fondo.activo,
        ingresos=saldo.ingresos,
        egresos=saldo.egresos,
        saldo=saldo.saldo,
        cantidad_movimientos=saldo.cantidad_movimientos,
        esta_en_rojo=saldo.esta_en_rojo,
    )


def _buscar_fondo(db: Session, edificio: Edificio, fondo_id: int) -> Fondo:
    """El fondo, si es de ese edificio. Si no, 404."""
    fondo = db.scalars(
        select(Fondo).where(Fondo.id == fondo_id, Fondo.edificio_id == edificio.id)
    ).first()

    if fondo is None:
        raise errores.ErrorDeNegocio(
            errores.NO_ENCONTRADO_EN_EL_EDIFICIO, que="ese fondo"
        )

    return fondo


def _buscar_caja(db: Session, edificio: Edificio) -> Caja:
    caja = db.scalars(select(Caja).where(Caja.edificio_id == edificio.id)).first()
    if caja is None:
        raise errores.ErrorDeNegocio(errores.SIN_CAJA)
    return caja


def _guardar(db: Session, que: str, descripcion: str) -> None:
    try:
        db.commit()
    except (IntegrityError, SQLAlchemyError):
        db.rollback()
        logger.exception("Fallo al guardar: %s", descripcion)
        raise errores.ErrorDeNegocio(errores.ERROR_AL_GUARDAR, que=que) from None


# ===========================================================================
# FONDOS
# ===========================================================================


@router.get(
    "/{edificio_id}/fondos",
    response_model=ListadoDeFondos,
    summary="Los fondos del edificio con su saldo",
)
def listar_fondos(
    edificio_id: int,
    quien_consulta: SoloAdministradores,
    db: SesionDB,
    incluir_inactivos: bool = False,
) -> ListadoDeFondos:
    """Los fondos con su saldo calculado y el total de lo guardado.

    Los inactivos quedan afuera por defecto: un fondo desactivado no admite
    movimientos nuevos, asi que no tiene por que ocupar lugar en la pantalla de
    todos los dias. **Pero su plata sigue existiendo**, asi que cuando se los
    incluye entran tambien en el total — no se puede dar por perdido el saldo de
    un fondo solo porque se dejo de usar.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_consulta)

    consulta = select(Fondo).where(Fondo.edificio_id == edificio.id)
    if not incluir_inactivos:
        consulta = consulta.where(Fondo.activo.is_(True))

    leidos = [
        _leer_fondo(fondo)
        for fondo in db.scalars(consulta.order_by(Fondo.nombre)).all()
    ]

    return ListadoDeFondos(
        total=sum((f.saldo for f in leidos), CERO),
        cantidad=len(leidos),
        fondos=leidos,
    )


@router.post(
    "/{edificio_id}/fondos",
    response_model=FondoLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un fondo",
)
def crear_fondo(
    edificio_id: int,
    datos: FondoCrear,
    quien_crea: SoloAdministradores,
    db: SesionDB,
) -> FondoLeer:
    """Crea un fondo vacio.

    **Nace sin movimientos y con saldo cero**, que es lo correcto: la plata
    entra cuando se registra el ingreso, no al crear la bolsa. Un fondo que
    naciera con un saldo inicial seria plata sin movimiento que la respalde.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_crea)

    repetido = db.scalars(
        select(Fondo).where(
            Fondo.edificio_id == edificio.id, Fondo.nombre == datos.nombre
        )
    ).first()
    if repetido is not None:
        raise errores.ErrorDeNegocio(errores.FONDO_REPETIDO, nombre=datos.nombre)

    fondo = Fondo(
        edificio_id=edificio.id,
        nombre=datos.nombre,
        descripcion=datos.descripcion,
    )
    db.add(fondo)
    _guardar(db, "el fondo", f"alta de fondo en el edificio {edificio_id}")

    logger.info(
        "Fondo %s (%r) creado en el edificio %s por %s",
        fondo.id,
        fondo.nombre,
        edificio_id,
        quien_crea.email,
    )
    return _leer_fondo(fondo)


@router.patch(
    "/{edificio_id}/fondos/{fondo_id}",
    response_model=FondoLeer,
    summary="Editar o desactivar un fondo",
)
def editar_fondo(
    edificio_id: int,
    fondo_id: int,
    datos: FondoEditar,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> FondoLeer:
    """Cambia el nombre, la descripcion o el estado del fondo.

    **No hay `DELETE` de un fondo, y es deliberado:** tiene historial, y el
    historial de la plata de un consorcio no se tira. Desactivarlo lo saca de
    la pantalla de todos los dias y le cierra la puerta a movimientos nuevos,
    sin perder nada.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)
    fondo = _buscar_fondo(db, edificio, fondo_id)

    cambios = {
        campo: valor
        for campo, valor in datos.model_dump(exclude_unset=True).items()
        if getattr(fondo, campo) != valor
    }
    if not cambios:
        raise errores.ErrorDeNegocio(errores.SIN_CAMBIOS)

    if "nombre" in cambios:
        repetido = db.scalars(
            select(Fondo).where(
                Fondo.edificio_id == edificio.id,
                Fondo.nombre == cambios["nombre"],
                Fondo.id != fondo.id,
            )
        ).first()
        if repetido is not None:
            raise errores.ErrorDeNegocio(
                errores.FONDO_REPETIDO, nombre=cambios["nombre"]
            )

    for campo, valor in cambios.items():
        setattr(fondo, campo, valor)

    _guardar(db, "el fondo", f"edicion del fondo {fondo_id}")

    logger.info(
        "Fondo %s del edificio %s editado por %s (%s)",
        fondo_id,
        edificio_id,
        quien_edita.email,
        ", ".join(sorted(cambios)),
    )
    return _leer_fondo(fondo)


@router.get(
    "/{edificio_id}/fondos/{fondo_id}/movimientos",
    response_model=list[MovimientoLeer],
    summary="El historial de movimientos de un fondo",
)
def listar_movimientos(
    edificio_id: int,
    fondo_id: int,
    quien_consulta: SoloAdministradores,
    db: SesionDB,
) -> list[MovimientoLeer]:
    """Los movimientos del fondo, del mas reciente al mas viejo.

    Es el libro del fondo: lo que permite explicar el saldo. Sin este listado,
    un saldo es un numero que nadie puede auditar.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_consulta)
    fondo = _buscar_fondo(db, edificio, fondo_id)

    filas = db.scalars(
        select(MovimientoFondo)
        .where(MovimientoFondo.fondo_id == fondo.id)
        .order_by(MovimientoFondo.fecha.desc(), MovimientoFondo.id.desc())
    ).all()

    return [_leer_movimiento(f) for f in filas]


@router.post(
    "/{edificio_id}/fondos/{fondo_id}/movimientos",
    response_model=FondoLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un movimiento en un fondo",
)
def crear_movimiento(
    edificio_id: int,
    fondo_id: int,
    datos: MovimientoCrear,
    quien_registra: SoloAdministradores,
    db: SesionDB,
) -> FondoLeer:
    """Registra un ingreso o un egreso y devuelve **como quedo el fondo**.

    Devolver el fondo completo y no el movimiento es a proposito: quien carga un
    movimiento quiere ver el saldo nuevo, y pedirlo aparte seria el doble de
    pedidos para el dato que importa. Es el mismo criterio que la carga de
    coeficientes.

    **Un egreso que deja el fondo en rojo se acepta** y se informa con
    `esta_en_rojo`. Casi siempre significa que falta cargar el ingreso que lo
    financio, y bloquearlo obligaria a inventarlo para registrar un gasto que ya
    ocurrio.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_registra)
    fondo = _buscar_fondo(db, edificio, fondo_id)

    if not fondo.activo:
        raise errores.ErrorDeNegocio(errores.FONDO_INACTIVO)

    fondo.movimientos.append(
        MovimientoFondo(
            tipo=datos.tipo,
            monto=datos.monto,
            fecha=datos.fecha,
            descripcion=datos.descripcion,
            registrado_por_id=quien_registra.id,
        )
    )
    _guardar(db, "el movimiento", f"movimiento en el fondo {fondo_id}")

    logger.info(
        "Movimiento de %s por %s en el fondo %s del edificio %s, por %s",
        datos.tipo,
        datos.monto,
        fondo_id,
        edificio_id,
        quien_registra.email,
    )
    return _leer_fondo(fondo)


@router.delete(
    "/{edificio_id}/fondos/{fondo_id}/movimientos/{movimiento_id}",
    response_model=FondoLeer,
    summary="Borrar un movimiento mal cargado",
)
def borrar_movimiento(
    edificio_id: int,
    fondo_id: int,
    movimiento_id: int,
    quien_borra: SoloAdministradores,
    db: SesionDB,
) -> FondoLeer:
    """Saca un movimiento del fondo y devuelve como queda el saldo.

    **No hay edicion de un movimiento.** Un movimiento mal cargado es un error
    de tipeo: se saca y se vuelve a cargar bien. Editarle el monto o el tipo a
    uno ya registrado es reescribir el historial de la plata, y ese historial
    es justamente para lo que existe el libro de movimientos.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_borra)
    fondo = _buscar_fondo(db, edificio, fondo_id)

    movimiento = db.scalars(
        select(MovimientoFondo).where(
            MovimientoFondo.id == movimiento_id,
            MovimientoFondo.fondo_id == fondo.id,
        )
    ).first()
    if movimiento is None:
        raise errores.ErrorDeNegocio(
            errores.NO_ENCONTRADO_EN_EL_EDIFICIO, que="ese movimiento"
        )

    db.delete(movimiento)
    _guardar(db, "el movimiento", f"baja del movimiento {movimiento_id}")

    logger.info(
        "Movimiento %s del fondo %s borrado por %s",
        movimiento_id,
        fondo_id,
        quien_borra.email,
    )

    db.refresh(fondo)
    return _leer_fondo(fondo)


# ===========================================================================
# CAJA CHICA
# ===========================================================================


def _leer_caja(caja: Caja) -> CajaLeer:
    estado = servicio_caja.calcular_estado(
        caja.monto_fijo, _a_movimientos(caja.movimientos)
    )
    return CajaLeer(
        id=caja.id,
        monto_fijo=caja.monto_fijo,
        responsable_id=caja.responsable_id,
        responsable=caja.responsable.nombre if caja.responsable else "",
        activo=caja.activo,
        ingresos=estado.ingresos,
        egresos=estado.egresos,
        disponible=estado.disponible,
        pendiente_de_reposicion=estado.pendiente_de_reposicion,
        reposicion_sugerida=servicio_caja.reposicion_sugerida(estado),
        cantidad_movimientos=estado.cantidad_movimientos,
        necesita_reposicion=estado.necesita_reposicion,
        esta_en_rojo=estado.esta_en_rojo,
        excede_el_fondo_fijo=estado.excede_el_fondo_fijo,
    )


def _exigir_responsable_del_edificio(
    db: Session, edificio: Edificio, responsable_id: int
) -> None:
    """El responsable de la caja tiene que trabajar en ese edificio.

    Vale el Encargado (es quien suele tener el efectivo) y quien administra el
    consorcio. **No vale un residente**: el efectivo del edificio no lo maneja
    un vecino, y no vale alguien de otro edificio, que seria darle la caja a
    quien no pisa el lugar.
    """
    responsable = db.get(Usuario, responsable_id)

    if responsable is None or not responsable.activo:
        raise errores.ErrorDeNegocio(errores.RESPONSABLE_DE_CAJA_INVALIDO)

    if responsable.rol == autorizacion.ADMIN_GENERAL:
        return
    if (
        responsable.rol == autorizacion.ADMIN_CONSORCIO
        and edificio.admin_consorcio_id == responsable.id
    ):
        return
    if (
        responsable.rol == autorizacion.ENCARGADO
        and edificio.encargado_id == responsable.id
    ):
        return

    raise errores.ErrorDeNegocio(errores.RESPONSABLE_DE_CAJA_INVALIDO)


@router.get(
    "/{edificio_id}/caja",
    response_model=CajaLeer,
    summary="El estado de la caja chica",
)
def ver_caja(
    edificio_id: int,
    quien_consulta: SoloAdministradores,
    db: SesionDB,
) -> CajaLeer:
    """Cuanto queda disponible, cuanto hay que reponer y si conviene rendir.

    Devuelve 404 si el edificio todavia no configuro su caja, que es un estado
    normal y no un problema: no todo consorcio maneja efectivo.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_consulta)
    return _leer_caja(_buscar_caja(db, edificio))


@router.post(
    "/{edificio_id}/caja",
    response_model=CajaLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Configurar la caja chica del edificio",
)
def crear_caja(
    edificio_id: int,
    datos: CajaGuardar,
    quien_crea: SoloAdministradores,
    db: SesionDB,
) -> CajaLeer:
    """Crea la caja con su monto fijo y su responsable.

    **Una por edificio.** Si ya existe, el error lo dice y sugiere editarla, en
    vez de contestar un conflicto generico que obliga a adivinar.

    Nace **sin movimientos**, asi que arranca con todo pendiente de reposicion:
    el efectivo se le entrega al responsable con un movimiento de ingreso, que
    es exactamente lo que pasa en la realidad.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_crea)

    if db.scalars(select(Caja).where(Caja.edificio_id == edificio.id)).first():
        raise errores.ErrorDeNegocio(errores.CAJA_YA_EXISTE)

    _exigir_responsable_del_edificio(db, edificio, datos.responsable_id)

    caja = Caja(
        edificio_id=edificio.id,
        monto_fijo=datos.monto_fijo,
        responsable_id=datos.responsable_id,
    )
    db.add(caja)
    _guardar(db, "la caja", f"alta de caja en el edificio {edificio_id}")

    logger.info(
        "Caja chica del edificio %s creada por %s (monto fijo %s)",
        edificio_id,
        quien_crea.email,
        caja.monto_fijo,
    )
    return _leer_caja(caja)


@router.patch(
    "/{edificio_id}/caja",
    response_model=CajaLeer,
    summary="Cambiar el monto fijo o el responsable de la caja",
)
def editar_caja(
    edificio_id: int,
    datos: CajaGuardar,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> CajaLeer:
    """Cambia el monto fijo o el responsable.

    **Cambiar el monto fijo no mueve ni un peso**, y conviene tenerlo claro:
    cambia el objetivo contra el que se mide el disponible, asi que lo que
    cambia es cuanto hay que reponer. Si se subio el fondo fijo, la diferencia
    aparece como pendiente de reposicion hasta que se entregue el efectivo —
    que es, de nuevo, un movimiento de ingreso.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)
    caja = _buscar_caja(db, edificio)

    if (
        caja.monto_fijo == datos.monto_fijo
        and caja.responsable_id == datos.responsable_id
    ):
        raise errores.ErrorDeNegocio(errores.SIN_CAMBIOS)

    if caja.responsable_id != datos.responsable_id:
        _exigir_responsable_del_edificio(db, edificio, datos.responsable_id)

    caja.monto_fijo = datos.monto_fijo
    caja.responsable_id = datos.responsable_id
    _guardar(db, "la caja", f"edicion de la caja del edificio {edificio_id}")

    logger.info(
        "Caja chica del edificio %s editada por %s", edificio_id, quien_edita.email
    )
    return _leer_caja(caja)


@router.get(
    "/{edificio_id}/caja/movimientos",
    response_model=list[MovimientoLeer],
    summary="El libro de la caja chica",
)
def listar_movimientos_de_caja(
    edificio_id: int,
    quien_consulta: SoloAdministradores,
    db: SesionDB,
) -> list[MovimientoLeer]:
    """Los movimientos de la caja, del mas reciente al mas viejo.

    Es el libro de registro que la rendicion de cuentas necesita: sin el no hay
    forma de saber contra que se gasto el efectivo.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_consulta)
    caja = _buscar_caja(db, edificio)

    filas = db.scalars(
        select(MovimientoCaja)
        .where(MovimientoCaja.caja_id == caja.id)
        .order_by(MovimientoCaja.fecha.desc(), MovimientoCaja.id.desc())
    ).all()

    return [_leer_movimiento(f) for f in filas]


@router.post(
    "/{edificio_id}/caja/movimientos",
    response_model=CajaLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un gasto o una reposición de la caja",
)
def crear_movimiento_de_caja(
    edificio_id: int,
    datos: MovimientoCrear,
    quien_registra: SoloAdministradores,
    db: SesionDB,
) -> CajaLeer:
    """Registra un movimiento y devuelve el estado nuevo de la caja.

    **Una reposicion es un movimiento de tipo `ingreso`**, no una operacion
    aparte: no hay endpoint de "reponer" porque la reposicion **es** el
    movimiento que trae el disponible de vuelta al monto fijo. La pantalla
    propone el importe con `reposicion_sugerida`.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_registra)
    caja = _buscar_caja(db, edificio)

    caja.movimientos.append(
        MovimientoCaja(
            tipo=datos.tipo,
            monto=datos.monto,
            fecha=datos.fecha,
            descripcion=datos.descripcion,
            registrado_por_id=quien_registra.id,
        )
    )
    _guardar(db, "el movimiento", f"movimiento en la caja del edificio {edificio_id}")

    logger.info(
        "Movimiento de caja (%s por %s) en el edificio %s, por %s",
        datos.tipo,
        datos.monto,
        edificio_id,
        quien_registra.email,
    )
    return _leer_caja(caja)


@router.delete(
    "/{edificio_id}/caja/movimientos/{movimiento_id}",
    response_model=CajaLeer,
    summary="Borrar un movimiento de caja mal cargado",
)
def borrar_movimiento_de_caja(
    edificio_id: int,
    movimiento_id: int,
    quien_borra: SoloAdministradores,
    db: SesionDB,
) -> CajaLeer:
    """Mismo criterio que en los fondos: se borra, no se edita."""
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_borra)
    caja = _buscar_caja(db, edificio)

    movimiento = db.scalars(
        select(MovimientoCaja).where(
            MovimientoCaja.id == movimiento_id,
            MovimientoCaja.caja_id == caja.id,
        )
    ).first()
    if movimiento is None:
        raise errores.ErrorDeNegocio(
            errores.NO_ENCONTRADO_EN_EL_EDIFICIO, que="ese movimiento"
        )

    db.delete(movimiento)
    _guardar(db, "el movimiento", f"baja del movimiento de caja {movimiento_id}")

    logger.info(
        "Movimiento de caja %s del edificio %s borrado por %s",
        movimiento_id,
        edificio_id,
        quien_borra.email,
    )

    db.refresh(caja)
    return _leer_caja(caja)

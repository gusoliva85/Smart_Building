"""Gastos del consorcio (`F2-T02`).

Cinco endpoints:

- ``GET    /gastos/rubros``                  — el catalogo, para el desplegable
- ``POST   /edificios/{id}/gastos``          — cargar un gasto
- ``GET    /edificios/{id}/gastos``          — listar, con filtro de periodo
- ``PATCH  /edificios/{id}/gastos/{gasto}``  — corregir uno
- ``DELETE /edificios/{id}/gastos/{gasto}``  — borrarlo

============================================================================
POR QUE LA EDICION ESTA DESDE EL PRIMER DIA
============================================================================

Lo pide el Roadmap y tiene una historia atras: sin edicion, un monto mal
cargado obliga a borrar el gasto y cargarlo de nuevo. Eso pierde la fecha de
carga original, y en la iteracion anterior termino en recargar el edificio
entero a mano. Un gasto se tipea a las apuradas con la factura en la mano: que
se pueda corregir no es una comodidad, es parte del flujo normal.

============================================================================
QUIEN PUEDE, Y POR QUE EL QUE NO PUEDE VE UN 404
============================================================================

Solo los administradores, con el alcance de siempre: el Administrador General
sobre toda la cartera, el Administrador de Consorcio solo sobre su edificio.
Eso lo resuelve `buscar_edificio_que_administra`, que devuelve **404 y no
403** cuando el edificio existe pero no es suyo: un 403 confirmaria que ese
edificio existe, y un administrador no tiene por que enterarse de la cartera
de otro.

El mismo criterio se aplica al gasto: se lo busca **siempre dentro del
edificio** que se acaba de verificar. Buscarlo por id suelto y comparar
despues es el error que deja pasar el id de un gasto ajeno.

============================================================================
LO QUE ESTA TAREA TODAVIA NO PUEDE HACER
============================================================================

Falta el aviso de "este gasto es de un periodo cuya expensa ya se publico, asi
que no va a aparecer en esa liquidacion". No se puede construir todavia porque
las expensas no existen: llega con `F2-T05`, que es donde quedo escrita la
regla, y lo muestra la pantalla en `F2-T17`.
"""

import logging
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core import errores
from app.core.dependencies import SesionDB, SoloAdministradores
from app.models.edificio import Edificio
from app.models.finanzas import Gasto
from app.routers.edificios import buscar_edificio_que_administra
from app.schemas.finanzas import (
    GastoCrear,
    GastoEditar,
    GastoLeer,
    ListadoDeGastos,
    RubroLeer,
)
from app.services import rubros

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Gastos"])


# ===========================================================================
# HELPERS
# ===========================================================================


def _leer(gasto: Gasto) -> GastoLeer:
    """Arma la respuesta de un gasto, con la etiqueta de su rubro resuelta."""
    return GastoLeer(
        id=gasto.id,
        rubro=gasto.rubro,
        rubro_etiqueta=rubros.etiqueta(gasto.rubro),
        monto=gasto.monto,
        fecha=gasto.fecha,
        descripcion=gasto.descripcion,
    )


def _buscar_gasto(db: Session, edificio: Edificio, gasto_id: int) -> Gasto:
    """El gasto, si pertenece a ese edificio. Si no, 404.

    El `where` del edificio es la mitad que importa: sin el, el id de un gasto
    de otro consorcio entraria igual.
    """
    gasto = db.scalars(
        select(Gasto).where(Gasto.id == gasto_id, Gasto.edificio_id == edificio.id)
    ).first()

    if gasto is None:
        raise errores.ErrorDeNegocio(
            errores.NO_ENCONTRADO_EN_EL_EDIFICIO, que="ese gasto"
        )

    return gasto


def _guardar(db: Session, descripcion: str) -> None:
    """Confirma la transaccion y traduce cualquier fallo al catalogo.

    El `IntegrityError` que puede llegar aca es el de los dos CHECK de la
    tabla —monto positivo y rubro del catalogo—, que el esquema ya valido
    antes. Si saltara, significa que el esquema y la tabla dejaron de estar de
    acuerdo: se registra con traza completa y al usuario se le muestra el error
    generico, porque el texto de un CHECK nombra tablas y columnas (`FX-T11`).
    """
    try:
        db.commit()
    except (IntegrityError, SQLAlchemyError):
        db.rollback()
        logger.exception("Fallo al guardar: %s", descripcion)
        raise errores.ErrorDeNegocio(
            errores.ERROR_AL_GUARDAR, que="el gasto"
        ) from None


# ===========================================================================
# EL CATALOGO DE RUBROS
# ===========================================================================


@router.get(
    "/gastos/rubros",
    response_model=list[RubroLeer],
    summary="Los rubros de gasto disponibles",
)
def listar_rubros(quien_consulta: SoloAdministradores) -> list[RubroLeer]:
    """El catalogo cerrado de rubros, en el orden en que se muestra.

    Lo sirve el backend en vez de que el frontend tenga su propia copia: una
    copia en JavaScript es exactamente lo que queda viejo el dia que se agrega
    un rubro, y el sintoma seria un desplegable al que le falta una opcion sin
    que nada falle.

    El orden no es alfabetico a proposito: es el de una liquidacion real, de lo
    que mas pesa a lo que menos.
    """
    return [
        RubroLeer(
            nombre=rubro.nombre,
            etiqueta=rubro.etiqueta,
            descripcion=rubro.descripcion,
        )
        for rubro in rubros.CATALOGO
    ]


# ===========================================================================
# EL CRUD
# ===========================================================================


@router.post(
    "/edificios/{edificio_id}/gastos",
    response_model=GastoLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Cargar un gasto del consorcio",
)
def crear(
    edificio_id: int,
    datos: GastoCrear,
    quien_carga: SoloAdministradores,
    db: SesionDB,
) -> GastoLeer:
    """Carga un gasto en el edificio.

    **No se valida que la fecha no sea futura, y es deliberado.** Una factura
    de seguro o un abono se cargan con la fecha de vencimiento, que todavia no
    llego; rechazarlas obligaria a esperar al dia exacto para cargar algo que
    ya esta sobre el escritorio.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_carga)

    gasto = Gasto(
        edificio_id=edificio.id,
        rubro=datos.rubro,
        monto=datos.monto,
        fecha=datos.fecha,
        descripcion=datos.descripcion,
    )
    db.add(gasto)
    _guardar(db, f"alta de un gasto del edificio {edificio_id}")

    logger.info(
        "Gasto %s cargado en el edificio %s (%s, %s) por %s",
        gasto.id,
        edificio_id,
        gasto.rubro,
        gasto.monto,
        quien_carga.email,
    )

    return _leer(gasto)


@router.get(
    "/edificios/{edificio_id}/gastos",
    response_model=ListadoDeGastos,
    summary="Listar los gastos del edificio, con filtro por período y rubro",
)
def listar(
    edificio_id: int,
    quien_consulta: SoloAdministradores,
    db: SesionDB,
    anio: int | None = Query(default=None, ge=2000, le=2100),
    mes: int | None = Query(default=None, ge=1, le=12),
    rubro: str | None = Query(default=None),
) -> ListadoDeGastos:
    """Los gastos del edificio, filtrados por periodo y por rubro.

    **El filtro de periodo se arma por rango de fechas y no extrayendo el anio
    y el mes de la columna.** Un `EXTRACT(MONTH FROM fecha)` no puede usar el
    indice `(edificio_id, fecha)` —la base tiene que calcular la funcion fila
    por fila— y ademas se escribe distinto en SQLite y en PostgreSQL, que son
    los dos motores que este proyecto usa. Comparar la fecha contra dos limites
    funciona igual en los dos y entra por el indice.

    `mes` sin `anio` se rechaza: "los gastos de marzo" de un edificio con tres
    anios de historia son tres marzos distintos, y devolver los tres cuando se
    pidio uno es peor que pedir el dato que falta.

    El rubro se filtra con el valor interno, no con la etiqueta. La pantalla ya
    tiene los dos (`GET /gastos/rubros`), asi que manda el que no cambia nunca.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_consulta)

    if mes is not None and anio is None:
        raise errores.ErrorDeNegocio(errores.MES_SIN_ANIO)

    if rubro is not None and not rubros.es_rubro_valido(rubro):
        raise errores.ErrorDeNegocio(
            errores.RUBRO_INVALIDO, cuales=", ".join(rubros.RUBROS)
        )

    consulta = select(Gasto).where(Gasto.edificio_id == edificio.id)

    if anio is not None:
        desde, hasta = _rango_del_periodo(anio, mes)
        consulta = consulta.where(Gasto.fecha >= desde, Gasto.fecha < hasta)

    if rubro is not None:
        consulta = consulta.where(Gasto.rubro == rubro)

    # Mas reciente primero: cargar gastos es una tarea de todos los dias y lo
    # que se acaba de cargar es lo que se quiere ver. El id desempata para que
    # dos gastos del mismo dia salgan siempre en el mismo orden; sin ese
    # desempate, el orden lo elige la base y puede cambiar entre dos llamadas.
    consulta = consulta.order_by(Gasto.fecha.desc(), Gasto.id.desc())

    gastos = list(db.scalars(consulta).all())

    # El total se suma en Python sobre los `Decimal` ya cargados, no con un
    # `SUM()` aparte: son las mismas filas que se estan devolviendo, asi que un
    # segundo viaje a la base solo agregaria la posibilidad de que los dos
    # numeros no coincidan.
    total = sum((gasto.monto for gasto in gastos), Decimal("0.00"))

    return ListadoDeGastos(
        total=total,
        cantidad=len(gastos),
        gastos=[_leer(gasto) for gasto in gastos],
    )


def _rango_del_periodo(anio: int, mes: int | None) -> tuple[date, date]:
    """El periodo como `[desde, hasta)`, con el limite de arriba excluido.

    Medio abierto a proposito: el ultimo dia del mes no se calcula nunca. Con
    `<= 31 de marzo` habria que saber cuantos dias tiene cada mes y acordarse
    de los bisiestos; con `< 1 de abril` no hay nada que acordarse y febrero
    deja de ser un caso especial.
    """
    if mes is None:
        return date(anio, 1, 1), date(anio + 1, 1, 1)
    if mes == 12:
        return date(anio, 12, 1), date(anio + 1, 1, 1)
    return date(anio, mes, 1), date(anio, mes + 1, 1)


@router.patch(
    "/edificios/{edificio_id}/gastos/{gasto_id}",
    response_model=GastoLeer,
    summary="Corregir un gasto",
)
def editar(
    edificio_id: int,
    gasto_id: int,
    datos: GastoEditar,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> GastoLeer:
    """Corrige los campos que se manden, y deja el resto como estaba.

    **`exclude_unset` es lo que hace que esto sea un PATCH y no un PUT
    disfrazado.** Sin el, los campos que no se mandan llegan en `None` y
    borrarian lo que habia: editar solo el monto dejaria el gasto sin fecha.
    Y es lo que permite distinguir "no mandaste descripcion" de "mandaste
    descripcion vacia", que son dos cosas distintas y las dos son validas.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)
    gasto = _buscar_gasto(db, edificio, gasto_id)

    cambios = datos.model_dump(exclude_unset=True)

    # Lo que ya vale lo mismo no es un cambio. Avisar en vez de guardar sin
    # hacer nada: un "guardado" que no guardo nada es la forma mas facil de
    # creer que se corrigio algo que sigue mal.
    aplicables = {
        campo: valor
        for campo, valor in cambios.items()
        if getattr(gasto, campo) != valor
    }

    if not aplicables:
        raise errores.ErrorDeNegocio(errores.SIN_CAMBIOS)

    for campo, valor in aplicables.items():
        setattr(gasto, campo, valor)

    _guardar(db, f"edicion del gasto {gasto_id}")

    logger.info(
        "Gasto %s del edificio %s editado por %s (%s)",
        gasto_id,
        edificio_id,
        quien_edita.email,
        ", ".join(sorted(aplicables)),
    )

    return _leer(gasto)


@router.delete(
    "/edificios/{edificio_id}/gastos/{gasto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Borrar un gasto",
)
def borrar(
    edificio_id: int,
    gasto_id: int,
    quien_borra: SoloAdministradores,
    db: SesionDB,
) -> None:
    """Borra el gasto del edificio.

    Se borra de verdad, no se marca como inactivo. Un gasto mal cargado no es
    un hecho historico que convenga conservar: es un error de tipeo, y
    arrastrarlo con una marca obligaria a filtrarlo en cada consulta y en cada
    suma, que es exactamente donde despues falta el filtro.

    **Lo que si es historico es la expensa**, y por eso no se toca: la
    liquidacion guarda sus montos copiados (`F2-T05`), asi que borrar un gasto
    nunca puede alterar una expensa ya emitida.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_borra)
    gasto = _buscar_gasto(db, edificio, gasto_id)

    db.delete(gasto)
    _guardar(db, f"baja del gasto {gasto_id}")

    logger.info(
        "Gasto %s del edificio %s borrado por %s",
        gasto_id,
        edificio_id,
        quien_borra.email,
    )

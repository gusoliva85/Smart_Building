"""Generacion y publicacion de la expensa del periodo (`F2-T05`).

Dos endpoints, y son dos pasos deliberadamente separados:

- ``POST /edificios/{id}/expensas``            — generar (queda en borrador)
- ``POST /edificios/{id}/expensas/{id}/publicar`` — publicarla

============================================================================
POR QUE GENERAR Y PUBLICAR SON DOS COSAS
============================================================================

Decidido el 2026-11-13. Generar calcula; publicar es el acto de decirle al
edificio "esto es lo que hay que pagar".

Mientras la expensa esta en **borrador** nadie la vio: no aparece en Mi
cuenta, no genera deuda, no pinta nada en el Dashboard Visual y el vencimiento
no empezo a correr. Se puede regenerar cuantas veces haga falta, que es
exactamente lo que hay que hacer cuando aparece un gasto que faltaba o uno que
se cargo mal.

**Publicar cierra esa puerta para siempre.** No "para la expensa anterior":
para siempre y para esa expensa. Los residentes ya tienen su comprobante y ya
empezaron a pagar, y cambiarles el monto abajo de los pies es inaceptable. Un
error descubierto despues de publicar se corrige en la liquidacion siguiente,
que es como se corrige en la realidad del rubro.

La regla anterior era "se regenera la ultima". Es debil: la ultima puede llevar
quince dias publicada y con la mitad del edificio pagando.

============================================================================
TODO PASA EN UNA SOLA TRANSACCION
============================================================================

Generar escribe tres tablas: la expensa, su apertura por rubro y una fila por
unidad. Si falla a mitad de camino **no queda nada a medio crear**: una expensa
con la apertura cargada y la mitad de las unidades repartidas no suma el total
y nadie se daria cuenta hasta que un propietario llame. Es el caso de rollback
documentado que `FX-T01` venia esperando.

Al **regenerar se conserva la identidad de la expensa**: se vacian su detalle y
su reparto y se vuelven a llenar, en vez de borrarla y crear otra. Con la regla
de publicacion no deberia haber pagos contra un borrador, pero conservar el id
mantiene estables las referencias y evita un agujero si alguna vez se carga un
pago adelantado.

============================================================================
LO QUE ESTA TAREA DEJA PREPARADO Y TODAVIA NO PUEDE CALCULAR
============================================================================

El **recargo por mora** y el **saldo a favor** se calculan sobre lo que cada
unidad debe vencido e impago y sobre lo que pago de mas: las dos cosas
necesitan el modelo `Pago`, que llega en `F2-T08`, despues de esta tarea.

La logica esta escrita completa en `services/expensas.liquidar()`, que los
recibe como argumentos. Hoy este endpoint le pasa dos diccionarios vacios, con
lo cual los dos dan cero — que es exactamente el comportamiento correcto con
`recargo_mora_porcentual` en su valor por defecto. Cuando los pagos existan se
le pasan los datos reales y no hay que tocar la logica. Los dos lugares estan
marcados abajo con el comentario `PENDIENTE F2-T08`.
"""

import logging
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core import alcance, errores
from app.core.dependencies import (
    SesionDB,
    SoloAdministradores,
    UsuarioActual,
)
from app.models.edificio import Departamento, Edificio, Piso
from app.models.finanzas import (
    Expensa,
    ExpensaDepartamento,
    ExpensaDetalle,
    Gasto,
)
from app.routers.edificios import buscar_edificio_que_administra
from app.routers.gastos import _rango_del_periodo
from app.schemas.finanzas import (
    DetalleLeer,
    ExpensaDeUnidad,
    ExpensaGenerar,
    ExpensaLeer,
    ExpensaResumen,
    UnidadLiquidadaLeer,
)
from app.services import expensas, finanzas, rubros

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edificios", tags=["Expensas"])

# Cuantas unidades se nombran cuando faltan coeficientes. Las mismas cinco que
# usa la pantalla de coeficientes: un edificio de 160 unidades recien cargado
# daria un mensaje ilegible, y "faltan coeficientes" sin decir cuales obliga a
# ir a buscarlos a mano.
UNIDADES_EN_EL_MENSAJE = 5


# ===========================================================================
# LO QUE SE VA A BUSCAR ANTES DE CALCULAR
# ===========================================================================


def _unidades_del_edificio(
    db: Session, edificio: Edificio
) -> list[Departamento]:
    """Las unidades en orden estable: por piso y, dentro del piso, por nombre.

    El orden no es cosmetico. El prorrateo reparte los centavos sobrantes por
    resto mayor y desempata **por posicion**, asi que un orden que cambie entre
    dos corridas daria liquidaciones distintas con los mismos datos. Es el
    mismo orden que usa la pantalla de coeficientes y el detalle del edificio,
    asi que lo que se ve y lo que se calcula coinciden.
    """
    return list(
        db.scalars(
            select(Departamento)
            .join(Piso, Piso.id == Departamento.piso_id)
            .where(Piso.edificio_id == edificio.id)
            .order_by(Piso.orden, Departamento.identificador)
        ).all()
    )


def _exigir_coeficientes(unidades: list[Departamento]) -> None:
    """Se niega a liquidar si los coeficientes no estan completos y en 100%.

    No es una formalidad. Con 99,9% el consorcio reparte menos de lo que gasto
    y la diferencia no la paga nadie; con una unidad sin coeficiente, su parte
    se la reparten los demas sin que nadie lo decida.

    La pantalla de coeficientes viene avisando desde `F1-T24` justamente para
    que esto no sorprenda aca, y los dos mensajes son distintos porque se
    arreglan distinto: uno dice que unidades completar, el otro cuanto suman.
    """
    if not unidades:
        raise errores.ErrorDeNegocio(errores.EDIFICIO_SIN_UNIDADES)

    sin_cargar = [u.identificador for u in unidades if u.coeficiente is None]
    if sin_cargar:
        primeros = ", ".join(sin_cargar[:UNIDADES_EN_EL_MENSAJE])
        resto = len(sin_cargar) - UNIDADES_EN_EL_MENSAJE
        if resto > 0:
            primeros += f" y {resto} mas"
        una_sola = len(sin_cargar) == 1
        raise errores.ErrorDeNegocio(
            errores.COEFICIENTES_INCOMPLETOS,
            cuantas=f"{len(sin_cargar)} {'unidad' if una_sola else 'unidades'}",
            cuales=primeros,
        )

    coeficientes = [u.coeficiente for u in unidades]
    if not finanzas.validar_coeficientes(coeficientes):
        suma = sum(coeficientes, Decimal(0)).quantize(finanzas.PASO_COEFICIENTE)
        raise errores.ErrorDeNegocio(errores.COEFICIENTES_NO_SUMAN_CIEN, suma=suma)


def _gastos_por_rubro(
    db: Session, edificio: Edificio, anio: int, mes: int
) -> list[tuple[str, Decimal]]:
    """Los gastos del periodo agrupados por rubro, de mayor a menor.

    Agrupa **la base y no Python**: es la unica consulta de este modulo que
    puede traer muchas filas, y sumar diez mil gastos en memoria para quedarse
    con diez numeros es trabajo al dolor. El filtro por rango de fechas es el
    mismo de `F2-T02`, reutilizado tal cual para que las dos pantallas —el
    listado de gastos y la liquidacion— no puedan discrepar sobre que gastos
    son de noviembre.
    """
    desde, hasta = _rango_del_periodo(anio, mes)

    filas = db.execute(
        select(Gasto.rubro, func.sum(Gasto.monto))
        .where(
            Gasto.edificio_id == edificio.id,
            Gasto.fecha >= desde,
            Gasto.fecha < hasta,
        )
        .group_by(Gasto.rubro)
    ).all()

    # El orden lo pone el catalogo, no el monto ni el alfabeto: la liquidacion
    # se lee siempre con los rubros en el mismo orden, mes a mes, asi que
    # comparar dos meses es mirar la misma fila.
    por_rubro = {rubro: monto for rubro, monto in filas}
    return [
        (nombre, por_rubro[nombre]) for nombre in rubros.RUBROS if nombre in por_rubro
    ]


def _buscar_expensa_del_periodo(
    db: Session, edificio: Edificio, anio: int, mes: int
) -> Expensa | None:
    return db.scalars(
        select(Expensa).where(
            Expensa.edificio_id == edificio.id,
            Expensa.anio == anio,
            Expensa.mes == mes,
        )
    ).first()


def _buscar_expensa(db: Session, edificio: Edificio, expensa_id: int) -> Expensa:
    """La liquidacion, si pertenece a ese edificio. Si no, 404.

    El `where` del edificio es la mitad que importa: sin el, el id de una
    liquidacion de otro consorcio entraria igual.
    """
    expensa = db.scalars(
        select(Expensa).where(
            Expensa.id == expensa_id,
            Expensa.edificio_id == edificio.id,
        )
    ).first()

    if expensa is None:
        raise errores.ErrorDeNegocio(errores.EXPENSA_NO_ENCONTRADA)

    return expensa


def _guardar(db: Session, descripcion: str) -> None:
    try:
        db.commit()
    except (IntegrityError, SQLAlchemyError):
        db.rollback()
        logger.exception("Fallo al guardar: %s", descripcion)
        raise errores.ErrorDeNegocio(
            errores.ERROR_AL_GUARDAR, que="la liquidación"
        ) from None


def _leer(expensa: Expensa, unidades: dict[int, str]) -> ExpensaLeer:
    """Arma la respuesta completa de una liquidacion.

    `unidades` mapea id de departamento a su identificador, para que la
    respuesta diga "1A" y no solo un numero: el id es interno y no le sirve a
    nadie del otro lado de la pantalla (`FX-T11`).
    """
    return ExpensaLeer(
        id=expensa.id,
        anio=expensa.anio,
        mes=expensa.mes,
        periodo=expensa.periodo,
        total=expensa.total,
        estado=expensa.estado,
        publicada_en=expensa.publicada_en,
        cantidad_unidades=len(expensa.por_departamento),
        detalle=[
            DetalleLeer(
                rubro=linea.rubro,
                rubro_etiqueta=rubros.etiqueta(linea.rubro),
                monto=linea.monto,
            )
            for linea in expensa.detalle
        ],
        unidades=[
            UnidadLiquidadaLeer(
                departamento_id=fila.departamento_id,
                identificador=unidades.get(fila.departamento_id, ""),
                coeficiente=fila.coeficiente,
                monto_expensa=fila.monto_expensa,
                recargo_mora=fila.recargo_mora,
                saldo_a_favor_aplicado=fila.saldo_a_favor_aplicado,
                total_a_pagar=fila.total_a_pagar,
            )
            for fila in expensa.por_departamento
        ],
    )


# ===========================================================================
# GENERAR
# ===========================================================================


@router.post(
    "/{edificio_id}/expensas",
    response_model=ExpensaLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Generar la expensa de un período (queda en borrador)",
)
def generar(
    edificio_id: int,
    datos: ExpensaGenerar,
    quien_genera: SoloAdministradores,
    db: SesionDB,
) -> ExpensaLeer:
    """Calcula la liquidacion del periodo y la deja en borrador.

    El orden de las verificaciones esta elegido: primero lo que el usuario
    puede arreglar solo (que haya gastos, que los coeficientes esten) y recien
    despues lo que necesita una decision suya (reemplazar un borrador). Pedir
    una confirmacion para despues fallar por falta de coeficientes seria
    hacerle confirmar algo que no iba a pasar.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_genera)
    periodo = f"{datos.mes:02d}/{datos.anio}"

    lineas = _gastos_por_rubro(db, edificio, datos.anio, datos.mes)
    if not lineas:
        raise errores.ErrorDeNegocio(errores.PERIODO_SIN_GASTOS, periodo=periodo)

    unidades = _unidades_del_edificio(db, edificio)
    _exigir_coeficientes(unidades)

    total = sum((monto for _, monto in lineas), Decimal("0.00"))

    # ------------------------------------------------ el borrador anterior ---
    existente = _buscar_expensa_del_periodo(db, edificio, datos.anio, datos.mes)

    if existente is not None:
        if existente.esta_publicada:
            raise errores.ErrorDeNegocio(
                errores.EXPENSA_YA_PUBLICADA, periodo=periodo
            )
        if not datos.confirmar:
            # El 409 es el "necesito que confirmes" de este proyecto: el
            # envoltorio de `fetch` del frontend lo convierte en
            # `error.necesitaConfirmacion` y abre el dialogo. El mensaje dice
            # por cuanto era la que se reemplaza, que es el dato con el que
            # alguien decide si seguir.
            raise errores.ErrorDeNegocio(
                errores.EXPENSA_SE_REGENERA,
                periodo=periodo,
                total=existente.total,
            )

    # -------------------------------------------------------- el calculo ----
    #
    # PENDIENTE F2-T08: aca van a entrar la deuda vencida y el saldo a favor
    # de cada unidad, que hoy no se pueden averiguar porque el modelo `Pago`
    # todavia no existe. Con los diccionarios vacios el recargo y el saldo dan
    # cero, que es el comportamiento correcto mientras el recargo configurado
    # sea cero. La logica ya esta escrita y probada en `services/expensas.py`.
    partes = expensas.liquidar(
        total,
        [(unidad.id, unidad.coeficiente) for unidad in unidades],
        porcentaje_mora=Decimal(0),
        vencido_por_unidad={},
        saldo_a_favor_por_unidad={},
    )

    # ------------------------------------------- escribir, todo o nada ------
    if existente is None:
        expensa = Expensa(
            edificio_id=edificio.id,
            anio=datos.anio,
            mes=datos.mes,
            total=total,
        )
        db.add(expensa)
        regenerada = False
    else:
        # Se conserva la identidad: se vacian las colecciones y se vuelven a
        # llenar. `delete-orphan` borra las filas viejas en el mismo flush.
        expensa = existente
        expensa.total = total
        expensa.detalle.clear()
        expensa.por_departamento.clear()

        # ESTE `flush` NO ES OPCIONAL, y es un error real que costo encontrar.
        #
        # Vaciar las colecciones marca las filas viejas para borrar, pero no
        # las borra: SQLAlchemy decide el orden de las operaciones al hacer el
        # flush, y agrupa **todos los INSERT de una tabla juntos**, antes de
        # los DELETE. Al regenerar, eso significa insertar la fila nueva de la
        # unidad 1A cuando la vieja todavia existe, y el UNIQUE
        # (expensa_id, departamento_id) la rechaza. El sintoma es un 500 al
        # regenerar y nada al generar por primera vez.
        #
        # Con el flush explicito los DELETE salen primero y despues se agregan
        # las filas nuevas. Sigue siendo **una sola transaccion**: un flush no
        # confirma nada, solo ordena lo que ya hay pendiente.
        db.flush()
        regenerada = True

    for rubro, monto in lineas:
        expensa.detalle.append(ExpensaDetalle(rubro=rubro, monto=monto))

    for parte in partes:
        expensa.por_departamento.append(
            ExpensaDepartamento(
                departamento_id=parte.departamento_id,
                coeficiente=parte.coeficiente,
                monto_expensa=parte.monto_expensa,
                recargo_mora=parte.recargo_mora,
                saldo_a_favor_aplicado=parte.saldo_a_favor_aplicado,
            )
        )

    _guardar(db, f"expensa {periodo} del edificio {edificio_id}")

    logger.info(
        "Expensa %s del edificio %s %s por %s: total %s, %d unidades, %d rubros",
        periodo,
        edificio_id,
        "regenerada" if regenerada else "generada",
        quien_genera.email,
        total,
        len(partes),
        len(lineas),
    )

    return _leer(expensa, {u.id: u.identificador for u in unidades})


# ===========================================================================
# PUBLICAR
# ===========================================================================


@router.post(
    "/{edificio_id}/expensas/{expensa_id}/publicar",
    response_model=ExpensaLeer,
    summary="Publicar la liquidación: la ven los residentes y ya no se regenera",
)
def publicar(
    edificio_id: int,
    expensa_id: int,
    quien_publica: SoloAdministradores,
    db: SesionDB,
) -> ExpensaLeer:
    """Pasa la expensa de borrador a publicada. **No se puede deshacer.**

    Desde este momento la ven los residentes, cuenta como deuda, pinta el
    Dashboard Visual y empieza a correr el vencimiento configurado del
    edificio.

    No existe "despublicar", y no es una limitacion tecnica: lo que habria que
    deshacer no esta en la base, esta en la cabeza de cuarenta propietarios que
    ya anotaron cuanto tenian que pagar.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_publica)
    expensa = _buscar_expensa(db, edificio, expensa_id)

    # La transicion se le pregunta al servicio y no se compara el estado aca.
    # Es la misma funcion que contesta "se puede regenerar", asi que las dos
    # mitades de la regla no pueden quedar desalineadas.
    if not expensas.transicion_valida(expensa.estado, expensas.PUBLICADA):
        raise errores.ErrorDeNegocio(
            errores.EXPENSA_NO_SE_PUEDE_PUBLICAR, periodo=expensa.periodo
        )

    expensa.estado = expensas.PUBLICADA
    expensa.publicada_en = datetime.now()
    _guardar(db, f"publicacion de la expensa {expensa_id}")

    logger.info(
        "Expensa %s del edificio %s publicada por %s",
        expensa.periodo,
        edificio_id,
        quien_publica.email,
    )

    identificadores = {
        unidad.id: unidad.identificador
        for unidad in _unidades_del_edificio(db, edificio)
    }
    return _leer(expensa, identificadores)


# ===========================================================================
# CONSULTAR (`F2-T06`)
# ===========================================================================


@router.get(
    "/{edificio_id}/expensas",
    response_model=list[ExpensaResumen],
    summary="Listar las liquidaciones del edificio",
)
def listar(
    edificio_id: int,
    quien_consulta: SoloAdministradores,
    db: SesionDB,
    anio: int | None = Query(default=None, ge=2000, le=2100),
) -> list[ExpensaResumen]:
    """Las liquidaciones del edificio, de la mas nueva a la mas vieja.

    Trae los borradores tambien, y eso es deliberado: **una expensa en borrador
    que nadie publico es plata que no se esta cobrando**, asi que tiene que
    estar a la vista de la administracion y no escondida.

    `se_puede_regenerar` viaja calculado por el servidor en vez de dejar que la
    pantalla lo deduzca del estado. La regla es del backend; una pantalla que
    la reimplemente es una pantalla que algun dia ofrece un boton que el
    servidor va a rechazar.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_consulta)

    consulta = select(Expensa).where(Expensa.edificio_id == edificio.id)
    if anio is not None:
        consulta = consulta.where(Expensa.anio == anio)

    liquidaciones = list(
        db.scalars(consulta.order_by(Expensa.anio.desc(), Expensa.mes.desc())).all()
    )

    return [
        ExpensaResumen(
            id=expensa.id,
            anio=expensa.anio,
            mes=expensa.mes,
            periodo=expensa.periodo,
            total=expensa.total,
            estado=expensa.estado,
            publicada_en=expensa.publicada_en,
            cantidad_unidades=len(expensa.por_departamento),
            cantidad_rubros=len(expensa.detalle),
            se_puede_regenerar=expensa.se_puede_regenerar,
        )
        for expensa in liquidaciones
    ]


@router.get(
    "/{edificio_id}/expensas/{expensa_id}",
    response_model=ExpensaLeer,
    summary="Una liquidación con su apertura por rubro y su reparto por unidad",
)
def ver(
    edificio_id: int,
    expensa_id: int,
    quien_consulta: SoloAdministradores,
    db: SesionDB,
) -> ExpensaLeer:
    """El detalle completo de una liquidacion.

    Es la misma forma que devuelve generar, a proposito: la pantalla que
    muestra una expensa recien generada y la que muestra una vieja son la misma
    pantalla, asi que si las dos respuestas fueran distintas habria que
    escribirla dos veces.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_consulta)
    expensa = _buscar_expensa(db, edificio, expensa_id)

    identificadores = {
        unidad.id: unidad.identificador
        for unidad in _unidades_del_edificio(db, edificio)
    }
    return _leer(expensa, identificadores)


@router.get(
    "/{edificio_id}/departamentos/{departamento_id}/expensas",
    response_model=list[ExpensaDeUnidad],
    summary="Las liquidaciones de una unidad, con la apertura por rubro",
)
def ver_de_una_unidad(
    edificio_id: int,
    departamento_id: int,
    quien_consulta: UsuarioActual,
    db: SesionDB,
) -> list[ExpensaDeUnidad]:
    """Lo que esta unidad pago y debe, periodo por periodo.

    **Esto es lo que consume "Mi cuenta" del residente**, y por eso es el unico
    endpoint del modulo que no pide `SoloAdministradores`: lo abre tambien el
    propietario y el inquilino de **esa** unidad. Quien decide es
    `alcance.puede_ver_unidad()`, que deja afuera al Encargado a proposito
    —puede ver el edificio porque trabaja ahi, pero cuanto debe el 3B es
    informacion economica de una familia— y al Auditor hasta `F11-T05`.

    **El residente ve solo las publicadas.** Un borrador no existe para el:
    mostrarselo seria anticiparle un monto que la administracion todavia puede
    cambiar, y despues reclamaria por la diferencia. La administracion ve las
    dos cosas.

    Cada periodo viene con **la apertura por rubro del edificio**, no solo con
    lo que le toca pagar. Es la transparencia que pide el Documento General
    (6.1): el consorcista tiene derecho a ver en que se gasto.
    """
    unidad = db.get(Departamento, departamento_id)

    # Se verifica tambien que la unidad este en el edificio de la ruta. Sin
    # eso, `/edificios/1/departamentos/99/expensas` con una unidad del
    # edificio 2 contestaria igual, y el id del edificio en la ruta seria
    # decorativo.
    if unidad is not None:
        piso = db.get(Piso, unidad.piso_id)
        if piso is None or piso.edificio_id != edificio_id:
            unidad = None

    if unidad is None or not alcance.puede_ver_unidad(db, quien_consulta, unidad):
        # Un 404 y no un 403: con un 403, probar ids seria una forma de
        # averiguar que unidades existen.
        raise errores.ErrorDeNegocio(
            errores.NO_ENCONTRADO_EN_EL_EDIFICIO, que="esa unidad"
        )

    solo_publicadas = not alcance.administra_el_edificio_de(db, quien_consulta, unidad)

    consulta = (
        select(ExpensaDepartamento, Expensa)
        .join(Expensa, Expensa.id == ExpensaDepartamento.expensa_id)
        .where(ExpensaDepartamento.departamento_id == unidad.id)
    )
    if solo_publicadas:
        consulta = consulta.where(Expensa.estado == expensas.PUBLICADA)

    filas = db.execute(
        consulta.order_by(Expensa.anio.desc(), Expensa.mes.desc())
    ).all()

    return [
        ExpensaDeUnidad(
            expensa_id=expensa.id,
            anio=expensa.anio,
            mes=expensa.mes,
            periodo=expensa.periodo,
            estado=expensa.estado,
            publicada_en=expensa.publicada_en,
            total_edificio=expensa.total,
            coeficiente=fila.coeficiente,
            monto_expensa=fila.monto_expensa,
            recargo_mora=fila.recargo_mora,
            saldo_a_favor_aplicado=fila.saldo_a_favor_aplicado,
            total_a_pagar=fila.total_a_pagar,
            detalle=[
                DetalleLeer(
                    rubro=linea.rubro,
                    rubro_etiqueta=rubros.etiqueta(linea.rubro),
                    monto=linea.monto,
                )
                for linea in expensa.detalle
            ],
        )
        for fila, expensa in filas
    ]

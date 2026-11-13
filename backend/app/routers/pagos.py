"""Carga de pagos por el residente y su estado de cuenta (`F2-T08`).

Tres endpoints:

- ``GET  /pagos/medios``   — el catalogo, para el desplegable
- ``GET  /mis-unidades``   — mis unidades con su estado de cuenta
- ``POST /mis-pagos``      — cargo un pago mio

============================================================================
POR QUE LAS RUTAS EMPIEZAN CON "MIS" Y NO CUELGAN DEL EDIFICIO
============================================================================

Porque el residente **no tiene por que saber en que edificio esta su unidad
dentro del sistema**, ni cual es el id de su piso. Entra, ve lo que debe, y
paga. Todo lo demas lo resuelve el backend a partir de quien esta logueado.

Esto no es comodidad: una pantalla que le pide al propietario elegir
"edificio" y despues "piso" y despues "unidad" para pagar su propia expensa es
una pantalla hecha desde la forma de la base de datos y no desde la persona.
En la iteracion anterior ese formulario existia, y lo primero que preguntaba
era un numero que el residente no podia averiguar.

============================================================================
EL PAGO SIEMPRE NACE PENDIENTE, Y EL CLIENTE NO PUEDE DECIR OTRA COSA
============================================================================

El esquema de entrada **no tiene campo `estado`**. Si lo tuviera, un pago
podria llegar confirmado desde el navegador y la conciliacion dejaria de
existir como control. Es la misma razon por la que el esquema tampoco acepta
`cargado_por_id`: eso sale del token, no del cuerpo del pedido.
"""

import logging
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core import errores
from app.core.dependencies import SesionDB, SoloAdministradores, UsuarioActual
from app.models.edificio import Departamento, Edificio, Piso
from app.models.finanzas import Expensa, ExpensaDepartamento, Pago
from app.models.usuario import Usuario
from app.routers.edificios import buscar_edificio_que_administra
from app.schemas.finanzas import (
    ColaDeConciliacion,
    CuentaDeUnidadLeer,
    DeudorLeer,
    ListadoDeDeudores,
    MedioDePagoLeer,
    PagoCargar,
    PagoConciliar,
    PagoDeGestionLeer,
    PagoLeer,
    PeriodoDeCuentaLeer,
)
from app.services import autorizacion, deudores, expensas, pagos

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Pagos"])

CERO = Decimal("0.00")


# ===========================================================================
# MIS UNIDADES
# ===========================================================================


def _mis_unidades(db: Session, usuario: Usuario) -> list[tuple[Departamento, Edificio, str]]:
    """Las unidades de esa persona, con su edificio y en que calidad.

    Devuelve el vinculo —propietario o inquilino— porque la pantalla lo
    muestra y porque **no son lo mismo**: un propietario puede tener varias
    unidades y hasta en varios edificios; un inquilino, una.

    Un administrador puede tambien ser propietario de una unidad, y en ese caso
    aparece aca. Es el caso del administrador que vive en el edificio, el mismo
    que la regla de `F2-T07` tiene en cuenta.
    """
    filas = db.execute(
        select(Departamento, Edificio)
        .join(Piso, Piso.id == Departamento.piso_id)
        .join(Edificio, Edificio.id == Piso.edificio_id)
        .where(
            (Departamento.propietario_id == usuario.id)
            | (Departamento.inquilino_id == usuario.id)
        )
        .order_by(Edificio.nombre, Piso.orden, Departamento.identificador)
    ).all()

    return [
        (
            departamento,
            edificio,
            autorizacion.PROPIETARIO
            if departamento.propietario_id == usuario.id
            else autorizacion.INQUILINO,
        )
        for departamento, edificio in filas
    ]


def periodos_publicados_de(
    db: Session,
    departamento_id: int,
    dias_vencimiento: int | None = None,
) -> list[pagos.PeriodoDeCuenta]:
    """Los periodos liquidados de una unidad, con lo pagado y lo pendiente.

    **Sin underscore a proposito: la usan dos routers.** Este modulo la expone
    para que la generacion de expensas (`F2-T05`) pueda calcular el recargo y
    el saldo a favor con exactamente la misma lectura que el estado de cuenta
    del residente. Dos consultas paralelas serian dos saldos distintos para el
    mismo propietario, y la que estaria mal seria siempre la que nadie reviso.

    Solo las expensas **publicadas**: un borrador no se le puede cobrar a
    nadie, asi que no entra en la cuenta. Es la misma regla de `F2-T06`.

    Los dos totales de pagos se suman **en la base y en una sola consulta por
    estado**, no trayendo todos los pagos y sumandolos en Python: una unidad
    con cinco anios de historia tiene cientos de filas y lo que se necesita son
    dos numeros por periodo.
    """
    liquidados = db.execute(
        select(ExpensaDepartamento, Expensa)
        .join(Expensa, Expensa.id == ExpensaDepartamento.expensa_id)
        .where(
            ExpensaDepartamento.departamento_id == departamento_id,
            Expensa.estado == expensas.PUBLICADA,
        )
        .order_by(Expensa.anio.desc(), Expensa.mes.desc())
    ).all()

    if not liquidados:
        return []

    # Un solo viaje para todos los periodos: {(expensa_id, estado): suma}.
    sumas = {
        (expensa_id, estado): total
        for expensa_id, estado, total in db.execute(
            select(Pago.expensa_id, Pago.estado, func.sum(Pago.monto))
            .where(Pago.departamento_id == departamento_id)
            .group_by(Pago.expensa_id, Pago.estado)
        ).all()
    }

    return [
        pagos.PeriodoDeCuenta(
            expensa_id=expensa.id,
            anio=expensa.anio,
            mes=expensa.mes,
            total_a_pagar=fila.total_a_pagar,
            pagado_confirmado=sumas.get((expensa.id, pagos.CONFIRMADO), CERO),
            pendiente_de_confirmar=sumas.get((expensa.id, pagos.PENDIENTE), CERO),
            monto_expensa=fila.monto_expensa,
            recargo_mora=fila.recargo_mora,
            # Solo se calcula si se pidieron los dias de vencimiento. El estado
            # de cuenta del residente no los necesita; el calculo de deudores
            # si, porque es lo que decide que esta atrasado.
            vence_el=(
                deudores.fecha_de_vencimiento(expensa.publicada_en, dias_vencimiento)
                if dias_vencimiento is not None
                else None
            ),
        )
        for fila, expensa in liquidados
    ]


@router.get(
    "/pagos/medios",
    response_model=list[MedioDePagoLeer],
    summary="Los medios de pago disponibles",
)
def listar_medios(quien_consulta: UsuarioActual) -> list[MedioDePagoLeer]:
    """El catalogo cerrado de medios de pago, en el orden en que se muestra.

    Primero el que se usa en el 90% de los casos. Lo sirve el backend para que
    la pantalla no tenga su propia copia, igual que con los rubros.
    """
    return [
        MedioDePagoLeer(nombre=medio.nombre, etiqueta=medio.etiqueta)
        for medio in pagos.MEDIOS
    ]


@router.get(
    "/mis-unidades",
    response_model=list[CuentaDeUnidadLeer],
    summary="Mis unidades con su estado de cuenta",
)
def mis_unidades(
    quien_consulta: UsuarioActual,
    db: SesionDB,
) -> list[CuentaDeUnidadLeer]:
    """Lo que debo, lo que tengo a favor y lo que cargue y falta confirmar.

    **Los tres totales van por separado.** Netearlos mezclaria plata verificada
    con plata declarada, que es la distincion que todo este modulo existe para
    mantener: lo pendiente **no** reduce la deuda, pero se muestra, porque si
    no el residente ve su saldo intacto y vuelve a pagar.

    Devuelve lista vacia si esa persona no tiene unidades, y no un error: un
    administrador que no vive en ningun edificio del sistema es completamente
    normal.

    El CBU y el alias viajan en la respuesta porque son lo que la persona vino
    a buscar. Son los datos de cobro del consorcio, no de nadie en particular
    (`F2-T10`).
    """
    cuentas: list[CuentaDeUnidadLeer] = []

    for departamento, edificio, vinculo in _mis_unidades(db, quien_consulta):
        cuenta = pagos.armar_cuenta(periodos_publicados_de(db, departamento.id))

        cuentas.append(
            CuentaDeUnidadLeer(
                departamento_id=departamento.id,
                identificador=departamento.identificador,
                edificio_id=edificio.id,
                edificio_nombre=edificio.nombre,
                vinculo=vinculo,
                deuda=cuenta.deuda,
                saldo_a_favor=cuenta.saldo_a_favor,
                pendiente_de_confirmar=cuenta.pendiente_de_confirmar,
                esta_al_dia=cuenta.esta_al_dia,
                cbu=edificio.cbu,
                alias_cbu=edificio.alias_cbu,
                periodos=[
                    PeriodoDeCuentaLeer(
                        expensa_id=periodo.expensa_id,
                        periodo=periodo.periodo,
                        total_a_pagar=periodo.total_a_pagar,
                        pagado_confirmado=periodo.pagado_confirmado,
                        pendiente_de_confirmar=periodo.pendiente_de_confirmar,
                        saldo=periodo.saldo,
                        esta_pago=periodo.esta_pago,
                    )
                    for periodo in cuenta.periodos
                ],
            )
        )

    return cuentas


# ===========================================================================
# CARGAR UN PAGO
# ===========================================================================


def _mensaje_del_pago(estado: str, motivo: str | None = None) -> str:
    """Lo que el residente tiene que leer, en palabras.

    El texto lo arma el servidor y no la pantalla. Es la misma razon por la que
    los errores salen del catalogo: tres pantallas armando el mismo texto a
    partir del estado son tres textos que algun dia dicen cosas distintas.

    **En el rechazo, el motivo va dentro del mensaje.** Un rechazo que dice
    "hablalo con la administracion" obliga a llamar por telefono; uno que dice
    "el monto no coincide con el comprobante" se resuelve solo.
    """
    if estado == pagos.PENDIENTE:
        return (
            "Ya cargaste este pago. El saldo se actualiza cuando la "
            "administración lo confirme."
        )
    if estado == pagos.CONFIRMADO:
        return "La administración confirmó este pago."

    if motivo:
        return (
            f"La administración rechazó este pago: {motivo}. Corregilo y "
            "cargalo de nuevo."
        )
    return (
        "La administración rechazó este pago. Hablalo con la administración y "
        "cargalo de nuevo."
    )


def _leer(pago: Pago, identificador: str, periodo: str) -> PagoLeer:
    return PagoLeer(
        id=pago.id,
        expensa_id=pago.expensa_id,
        periodo=periodo,
        departamento_id=pago.departamento_id,
        identificador=identificador,
        monto=pago.monto,
        fecha=pago.fecha,
        medio_pago=pago.medio_pago,
        medio_pago_etiqueta=pagos.etiqueta_del_medio(pago.medio_pago),
        comprobante_url=pago.comprobante_url,
        estado=pago.estado,
        mensaje=_mensaje_del_pago(pago.estado, pago.motivo_rechazo),
        motivo_rechazo=pago.motivo_rechazo,
        estados_siguientes=list(pagos.estados_siguientes(pago.estado)),
    )


@router.post(
    "/mis-pagos",
    response_model=PagoLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Cargar un pago de una de mis unidades",
)
def cargar(
    datos: PagoCargar,
    quien_carga: UsuarioActual,
    db: SesionDB,
) -> PagoLeer:
    """Carga un pago contra una liquidacion de una unidad mia.

    **Queda pendiente**, y eso es el punto: el saldo no se mueve hasta que la
    administracion lo concilie contra el extracto (`F2-T09`). La respuesta trae
    el texto que explica eso, para que el residente no crea que no se guardo.

    Que se acepta y que no:

    - La expensa tiene que estar **publicada**. Un borrador no se le cobro a
      nadie todavia.
    - La unidad tiene que ser **mia**, y se resuelve sola si tengo una sola en
      ese edificio. Con mas de una, el servidor pide cual y **dice cuales
      son** — "elegí una unidad" sin la lista obliga a adivinar.
    - **Los pagos parciales estan permitidos**, y pagar de mas tambien: el
      excedente queda como saldo a favor y se descuenta de la liquidacion
      siguiente. Ninguna de las dos cosas se rechaza, porque las dos pasan en
      la realidad del rubro.
    """
    mias = _mis_unidades(db, quien_carga)
    if not mias:
        raise errores.ErrorDeNegocio(errores.SIN_UNIDADES)

    expensa = db.get(Expensa, datos.expensa_id)
    if expensa is None:
        raise errores.ErrorDeNegocio(errores.EXPENSA_NO_ENCONTRADA)

    # Las unidades mias en el edificio de ESA liquidacion. Si la expensa no es
    # de ningun edificio mio, la lista queda vacia y contesta lo mismo que una
    # expensa inexistente: un 404 que no confirma que esa liquidacion existe.
    candidatas = [
        departamento
        for departamento, edificio, _ in mias
        if edificio.id == expensa.edificio_id
    ]
    if not candidatas:
        raise errores.ErrorDeNegocio(errores.EXPENSA_NO_ENCONTRADA)

    if not expensa.esta_publicada:
        raise errores.ErrorDeNegocio(errores.EXPENSA_EN_BORRADOR)

    if datos.departamento_id is None:
        if len(candidatas) > 1:
            raise errores.ErrorDeNegocio(
                errores.ELEGI_UNA_UNIDAD,
                cuales=", ".join(u.identificador for u in candidatas),
            )
        unidad = candidatas[0]
    else:
        elegida = [u for u in candidatas if u.id == datos.departamento_id]
        if not elegida:
            # No es mia, o no es de ese edificio. 404 y no 403: con un 403,
            # probar ids seria una forma de averiguar que unidades existen.
            raise errores.ErrorDeNegocio(
                errores.NO_ENCONTRADO_EN_EL_EDIFICIO, que="esa unidad"
            )
        unidad = elegida[0]

    pago = Pago(
        departamento_id=unidad.id,
        expensa_id=expensa.id,
        monto=datos.monto,
        fecha=datos.fecha,
        medio_pago=datos.medio_pago,
        comprobante_url=datos.comprobante_url,
        estado=pagos.PENDIENTE,
        cargado_por_id=quien_carga.id,
    )
    db.add(pago)

    try:
        db.commit()
    except (IntegrityError, SQLAlchemyError):
        db.rollback()
        logger.exception("Fallo al guardar un pago de la unidad %s", unidad.id)
        raise errores.ErrorDeNegocio(errores.ERROR_AL_GUARDAR, que="el pago") from None

    logger.info(
        "Pago %s cargado por %s: unidad %s, expensa %s, %s por %s",
        pago.id,
        quien_carga.email,
        unidad.identificador,
        expensa.periodo,
        pago.monto,
        pago.medio_pago,
    )

    return _leer(pago, unidad.identificador, expensa.periodo)


# ===========================================================================
# LA CONCILIACION (`F2-T09`)
# ===========================================================================
#
# Es el paso humano que convierte una declaracion en un hecho: alguien de la
# administracion mira el extracto bancario y dice "esta plata entro". Hasta
# entonces el saldo no se movio.
#
# **El listado es parte de esta tarea y no un agregado posterior**, y el
# Roadmap lo subraya con razon: sin el, la cola de conciliacion no existe como
# pantalla y la funcion de confirmar no tiene desde donde invocarse.


def _leer_de_gestion(
    pago: Pago,
    identificador: str,
    periodo: str,
    quien_mira: Usuario,
) -> PagoDeGestionLeer:
    return PagoDeGestionLeer(
        id=pago.id,
        expensa_id=pago.expensa_id,
        periodo=periodo,
        departamento_id=pago.departamento_id,
        identificador=identificador,
        monto=pago.monto,
        fecha=pago.fecha,
        medio_pago=pago.medio_pago,
        medio_pago_etiqueta=pagos.etiqueta_del_medio(pago.medio_pago),
        comprobante_url=pago.comprobante_url,
        estado=pago.estado,
        estados_siguientes=list(pagos.estados_siguientes(pago.estado)),
        cargado_por=pago.cargado_por.nombre if pago.cargado_por else "",
        cargado_en=pago.creado_en,
        conciliado_por=pago.conciliado_por.nombre if pago.conciliado_por else None,
        conciliado_en=pago.conciliado_en,
        motivo_rechazo=pago.motivo_rechazo,
        puedo_conciliarlo=(
            pago.estado == pagos.PENDIENTE
            and pagos.puede_confirmar(quien_mira.id, pago.cargado_por_id)
        ),
    )


def _buscar_pago(db: Session, edificio: Edificio, pago_id: int) -> Pago:
    """El pago, si es de una unidad de ese edificio. Si no, 404.

    El salto por `Piso` es lo que ata el pago al edificio: la tabla de pagos no
    tiene `edificio_id` — cuelga de la unidad, que es de donde sale el dinero.
    Sin este join, el id de un pago de otro consorcio entraria igual.
    """
    pago = db.scalars(
        select(Pago)
        .join(Departamento, Departamento.id == Pago.departamento_id)
        .join(Piso, Piso.id == Departamento.piso_id)
        .where(Pago.id == pago_id, Piso.edificio_id == edificio.id)
    ).first()

    if pago is None:
        raise errores.ErrorDeNegocio(errores.PAGO_NO_ENCONTRADO)

    return pago


@router.get(
    "/edificios/{edificio_id}/pagos",
    response_model=ColaDeConciliacion,
    summary="La cola de conciliación: los pagos del edificio, con filtros",
)
def listar(
    edificio_id: int,
    quien_consulta: SoloAdministradores,
    db: SesionDB,
    estado: str | None = None,
    departamento_id: int | None = None,
) -> ColaDeConciliacion:
    """Los pagos del edificio, filtrables por estado y por unidad.

    **El orden es el mas viejo primero**, al revés que todos los demas listados
    de este proyecto, y es a proposito: esto es una cola de trabajo. El pago que
    lleva cinco dias esperando es el que hay que mirar, no el que entro hace un
    minuto. En un listado historico el orden seria el otro, y por eso la
    pantalla filtra por estado antes de mirar el orden.

    Sin filtro de estado trae todos: el historico es la otra mitad de la misma
    pantalla (`F2-T19`).
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_consulta)

    if estado is not None and not pagos.es_estado_valido(estado):
        raise errores.ErrorDeNegocio(errores.ESTADO_DE_PAGO_INVALIDO)

    consulta = (
        select(Pago, Departamento, Expensa)
        .join(Departamento, Departamento.id == Pago.departamento_id)
        .join(Piso, Piso.id == Departamento.piso_id)
        .join(Expensa, Expensa.id == Pago.expensa_id)
        .where(Piso.edificio_id == edificio.id)
    )

    if estado is not None:
        consulta = consulta.where(Pago.estado == estado)
    if departamento_id is not None:
        consulta = consulta.where(Pago.departamento_id == departamento_id)

    filas = db.execute(consulta.order_by(Pago.fecha, Pago.id)).all()

    return ColaDeConciliacion(
        cantidad=len(filas),
        total=sum((pago.monto for pago, _, _ in filas), CERO),
        pagos=[
            _leer_de_gestion(
                pago, departamento.identificador, expensa.periodo, quien_consulta
            )
            for pago, departamento, expensa in filas
        ],
    )


@router.patch(
    "/edificios/{edificio_id}/pagos/{pago_id}",
    response_model=PagoDeGestionLeer,
    summary="Conciliar un pago: confirmarlo o rechazarlo",
)
def conciliar(
    edificio_id: int,
    pago_id: int,
    datos: PagoConciliar,
    quien_concilia: SoloAdministradores,
    db: SesionDB,
) -> PagoDeGestionLeer:
    """Confirma o rechaza un pago. **Es el acto que mueve el saldo.**

    Tres verificaciones, y ninguna es redundante:

    1. **El pago es de este edificio**, resuelto en la consulta y no
       comparando despues.
    2. **La transicion es valida**, preguntandole a `services/pagos.py`. Un
       pago ya conciliado no se vuelve a conciliar: si se confirmo por
       equivocacion, lo que corresponde es registrar el movimiento que lo
       corrige, no reescribir el historial.
    3. **Quien cargo el pago no lo concilia**, aunque sea administrador. Es la
       separacion de funciones de `F2-T07`, y el caso que de verdad pasa es el
       administrador que vive en el edificio: concilia los pagos de sus
       vecinos, no el suyo.

    Queda registrado **quien** concilio y **cuando**. Un circuito de dinero sin
    ese nombre no se puede auditar.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_concilia)
    pago = _buscar_pago(db, edificio, pago_id)

    if not pagos.transicion_valida(pago.estado, datos.estado):
        raise errores.ErrorDeNegocio(errores.PAGO_YA_CONCILIADO, estado=pago.estado)

    if not pagos.puede_confirmar(quien_concilia.id, pago.cargado_por_id):
        raise errores.ErrorDeNegocio(errores.NO_PODES_CONCILIAR_TU_PAGO)

    pago.estado = datos.estado
    pago.conciliado_por_id = quien_concilia.id
    pago.conciliado_en = datetime.now()
    # `None` cuando se confirma, y el esquema ya garantizo que al rechazar hay
    # motivo. Se asigna siempre y no solo al rechazar: si un dia se permitiera
    # alguna transicion mas, un motivo viejo colgado seria peor que ninguno.
    pago.motivo_rechazo = datos.motivo

    try:
        db.commit()
    except (IntegrityError, SQLAlchemyError):
        db.rollback()
        logger.exception("Fallo al conciliar el pago %s", pago_id)
        raise errores.ErrorDeNegocio(
            errores.ERROR_AL_GUARDAR, que="la conciliación"
        ) from None

    unidad = db.get(Departamento, pago.departamento_id)
    expensa = db.get(Expensa, pago.expensa_id)

    logger.info(
        "Pago %s de la unidad %s (%s, %s) %s por %s%s",
        pago.id,
        unidad.identificador,
        expensa.periodo,
        pago.monto,
        datos.estado,
        quien_concilia.email,
        f": {datos.motivo}" if datos.motivo else "",
    )

    return _leer_de_gestion(
        pago, unidad.identificador, expensa.periodo, quien_concilia
    )


# ===========================================================================
# DEUDORES (`F2-T11`)
# ===========================================================================
#
# **Vista calculada, no tabla.** Una tabla de deudores tendria que mantenerse
# al dia con cada pago conciliado, cada expensa publicada y **cada dia que
# pasa** —porque la antiguedad de una deuda cambia sola con el calendario— y el
# dia que ese proceso no corra le diria a un propietario que esta al dia cuando
# no lo esta. El porque completo esta en `services/deudores.py`.
#
# Es **siempre de solo lectura**: no hay forma de "saldar" una deuda desde aca.
# La unica forma de que baje es conciliar el pago correspondiente.


@router.get(
    "/edificios/{edificio_id}/deudores",
    response_model=ListadoDeDeudores,
    summary="Quién debe, cuánto y desde cuándo",
)
def listar_deudores(
    edificio_id: int,
    quien_consulta: SoloAdministradores,
    db: SesionDB,
    solo_vencidos: bool = False,
) -> ListadoDeDeudores:
    """Las unidades con deuda, de la mas atrasada a la menos.

    `solo_vencidos` filtra las que estan **en termino**: una unidad que debe la
    expensa publicada hace tres dias, con diez dias de vencimiento, aparece en
    el listado completo con saldo y con cero meses de atraso — porque hay que
    cobrarle— pero no es una deudora. La pantalla de cobranza quiere las
    atrasadas; el resumen del edificio, todas.

    **Lo que devuelve es lo que alimenta el amarillo y el rojo del Dashboard
    Visual** (Fase 5): un mes de atraso pinta amarillo, mas de uno rojo, y la
    severidad la decide el backend para que las dos pantallas no puedan pintar
    la misma unidad de colores distintos.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_consulta)

    unidades = db.execute(
        select(Departamento, Piso.numero)
        .join(Piso, Piso.id == Departamento.piso_id)
        .where(Piso.edificio_id == edificio.id)
        .order_by(Piso.orden, Departamento.identificador)
    ).all()

    filas: list[DeudorLeer] = []
    total = CERO
    total_vencido = CERO

    for unidad, piso_numero in unidades:
        deudor = deudores.armar_deudor(
            unidad.id,
            unidad.identificador,
            periodos_publicados_de(db, unidad.id, edificio.dias_vencimiento_expensas),
        )

        if not deudor.debe:
            continue
        if solo_vencidos and deudor.meses_de_atraso == 0:
            continue

        total += deudor.saldo
        total_vencido += deudor.vencido

        filas.append(
            DeudorLeer(
                departamento_id=deudor.departamento_id,
                identificador=deudor.identificador,
                piso_numero=piso_numero,
                propietario=unidad.propietario.nombre if unidad.propietario else None,
                inquilino=unidad.inquilino.nombre if unidad.inquilino else None,
                saldo=deudor.saldo,
                vencido=deudor.vencido,
                meses_de_atraso=deudor.meses_de_atraso,
                periodo_mas_viejo=deudor.periodo_mas_viejo,
                periodos_impagos=list(deudor.periodos_impagos),
                severidad=deudor.severidad,
            )
        )

    # El orden lo decide el servicio, no este endpoint: es una regla de
    # negocio —primero la que debe desde hace mas tiempo— y no una preferencia
    # de presentacion.
    ordenados = sorted(
        filas,
        key=lambda d: (-d.meses_de_atraso, -d.saldo, d.identificador),
    )

    return ListadoDeDeudores(
        cantidad_deudores=len(ordenados),
        cantidad_unidades=len(unidades),
        total=total,
        total_vencido=total_vencido,
        deudores=ordenados,
    )

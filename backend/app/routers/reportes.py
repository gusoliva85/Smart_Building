"""Reporte financiero consolidado (`F2-T16`).

Un endpoint: ``GET /edificios/{id}/reportes/financiero``.

Devuelve, para un rango de meses: lo gastado, lo esperado y lo recaudado de
cada periodo, la evolucion de los gastos por rubro, la foto de la morosidad de
hoy y lo que el consorcio tiene guardado en sus fondos.

============================================================================
CONSOLIDA, NO RECALCULA — Y SE VE EN LOS IMPORTS
============================================================================

Este modulo no tiene una sola consulta propia de morosidad ni de agrupacion por
rubro. Reutiliza, tal cual:

- `routers.expensas._gastos_por_rubro` para los gastos agrupados — la misma
  funcion que arma la apertura de una liquidacion.
- `routers.pagos.periodos_publicados_de` + `services.deudores` para la
  morosidad — las mismas que usan la vista de deudores y Mi cuenta.
- `services.fondos.calcular_saldo` para los fondos.

Si cada reporte tuviera sus propias consultas, el dia que cambie una regla
—que es "vencido", que pago cuenta— habria dos respuestas distintas a la
misma pregunta, y la que estaria mal seria la del reporte, porque es la que
nadie mira todos los dias.

============================================================================
LA MOROSIDAD ES UNA FOTO DE HOY, NO DEL PERIODO
============================================================================

Y es la unica parte del reporte que no se mueve con el rango de meses que se
pida. No es un descuido: **la deuda no tiene periodo**. Una unidad que debe
marzo sigue debiendolo en noviembre, y preguntar "cuanta morosidad habia en
marzo" obligaria a reconstruir que estaba pagado en ese momento — algo que el
sistema puede responder solo si guardara un historial de saldos, que es
exactamente lo que se decidio no hacer.

Asi que la morosidad del reporte dice **como esta la cartera ahora**, y el
reporte lo declara en el nombre del campo para que nadie lo lea como una serie.
"""

import logging
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.dependencies import SesionDB, SoloAdministradores
from app.models.edificio import Departamento, Piso
from app.models.finanzas import Expensa, ExpensaDepartamento, Fondo, Pago
from app.routers.edificios import buscar_edificio_que_administra
from app.routers.expensas import _gastos_por_rubro
from app.routers.pagos import periodos_publicados_de
from app.schemas.reportes import (
    MorosidadLeer,
    PeriodoLeer,
    ReporteFinanciero,
    ResumenLeer,
    RubroLeer,
)
from app.services import deudores, expensas as servicio_expensas, fondos, reportes, rubros

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edificios", tags=["Reportes"])

CERO = Decimal("0.00")

MESES_POR_DEFECTO = 6
"""Cuantos meses trae el reporte si no se pide otra cosa.

Seis es medio ano: suficiente para ver una tendencia y poco para leerlo de un
vistazo en una pantalla. Doce se puede pedir, y es lo que se mira al cierre del
ejercicio.
"""


def _periodos_hacia_atras(hasta: date, cantidad: int) -> list[tuple[int, int]]:
    """Los ultimos `cantidad` periodos, del mas viejo al mas nuevo.

    Del mas viejo al mas nuevo porque es el orden de un grafico de evolucion —
    el tiempo va hacia la derecha— al contrario de los listados, que muestran lo
    ultimo primero. Es una diferencia deliberada y por eso esta escrita.

    La resta de meses se hace a mano y no con una libreria de fechas: restar un
    mes a enero es diciembre del ano anterior, y es la unica regla que hay.
    """
    periodos: list[tuple[int, int]] = []
    anio, mes = hasta.year, hasta.month

    for _ in range(cantidad):
        periodos.append((anio, mes))
        mes -= 1
        if mes == 0:
            mes = 12
            anio -= 1

    return list(reversed(periodos))


@router.get(
    "/{edificio_id}/reportes/financiero",
    response_model=ReporteFinanciero,
    summary="Reporte financiero consolidado: recaudación, gastos y morosidad",
)
def financiero(
    edificio_id: int,
    quien_consulta: SoloAdministradores,
    db: SesionDB,
    meses: int = Query(default=MESES_POR_DEFECTO, ge=1, le=36),
    hasta_anio: int | None = Query(default=None, ge=2000, le=2100),
    hasta_mes: int | None = Query(default=None, ge=1, le=12),
) -> ReporteFinanciero:
    """La data cruda de la que despues vive la Analitica de la Fase 6.

    `hasta_anio` y `hasta_mes` permiten mirar hacia atras desde un mes que no
    es el actual — util al cerrar un ejercicio. Sin ellos, el rango termina
    en el mes de hoy.

    **Solo cuentan las expensas publicadas.** Un borrador no se le cobro a
    nadie, asi que incluirlo en "lo esperado" inflaria el numero con plata que
    todavia nadie debe.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_consulta)

    hoy = date.today()
    hasta = date(
        hasta_anio or hoy.year,
        hasta_mes or hoy.month,
        1,
    )
    periodos = _periodos_hacia_atras(hasta, meses)

    # ------------------------------------------------ gastos por periodo ---
    #
    # Una consulta por periodo, con la MISMA funcion que agrupa los gastos al
    # generar una expensa. Son `meses` consultas chicas y agrupadas por la
    # base; traer todos los gastos del rango y agruparlos en Python seria mas
    # rapido de escribir y daria un segundo lugar donde se decide que gasto es
    # de noviembre.
    gastos_por_periodo: dict[tuple[int, int], dict[str, Decimal]] = {}
    for anio, mes in periodos:
        gastos_por_periodo[(anio, mes)] = {
            rubro: monto
            for rubro, monto in _gastos_por_rubro(db, edificio, anio, mes)
        }

    # ----------------------------------------- expensas y pagos por periodo --
    filas = db.execute(
        select(
            Expensa.anio,
            Expensa.mes,
            Expensa.id,
            Expensa.total,
        ).where(
            Expensa.edificio_id == edificio.id,
            Expensa.estado == servicio_expensas.PUBLICADA,
        )
    ).all()

    publicadas = {(f.anio, f.mes): (f.id, f.total) for f in filas}
    ids = [valor[0] for valor in publicadas.values()]

    esperado_por_expensa: dict[int, Decimal] = {}
    if ids:
        for expensa_id, fila in db.execute(
            select(ExpensaDepartamento.expensa_id, ExpensaDepartamento).where(
                ExpensaDepartamento.expensa_id.in_(ids)
            )
        ).all():
            esperado_por_expensa[expensa_id] = (
                esperado_por_expensa.get(expensa_id, CERO) + fila.total_a_pagar
            )

    # Los pagos se imputan **al periodo de su expensa y no a su fecha de
    # pago**, que es la pregunta que el reporte contesta: "cuanto de la expensa
    # de noviembre se cobro". Alguien que paga noviembre en enero suma a
    # noviembre, no a enero.
    pagos_por_expensa: dict[tuple[int, str], Decimal] = {}
    if ids:
        for expensa_id, estado, total in db.execute(
            select(Pago.expensa_id, Pago.estado, Pago.monto)
            .where(Pago.expensa_id.in_(ids))
        ).all():
            clave = (expensa_id, estado)
            pagos_por_expensa[clave] = pagos_por_expensa.get(clave, CERO) + total

    armados: list[reportes.PeriodoDelReporte] = []
    for anio, mes in periodos:
        expensa = publicadas.get((anio, mes))
        expensa_id, total = expensa if expensa else (None, CERO)

        armados.append(
            reportes.PeriodoDelReporte(
                anio=anio,
                mes=mes,
                gastos=sum(gastos_por_periodo[(anio, mes)].values(), CERO),
                esperado=(
                    esperado_por_expensa.get(expensa_id, CERO)
                    if expensa_id
                    else CERO
                ),
                recaudado=pagos_por_expensa.get((expensa_id, "confirmado"), CERO),
                pendiente_de_confirmar=pagos_por_expensa.get(
                    (expensa_id, "pendiente"), CERO
                ),
            )
        )

    # ------------------------------------------------------ la morosidad ---
    #
    # Con las mismas funciones que la vista de deudores. Ver la cabecera: es
    # una foto de hoy y no una serie.
    unidades = db.scalars(
        select(Departamento)
        .join(Piso, Piso.id == Departamento.piso_id)
        .where(Piso.edificio_id == edificio.id)
    ).all()

    deuda_total = CERO
    vencido_total = CERO
    con_deuda = 0
    con_atraso = 0

    for unidad in unidades:
        deudor = deudores.armar_deudor(
            unidad.id,
            unidad.identificador,
            periodos_publicados_de(
                db, unidad.id, edificio.dias_vencimiento_expensas
            ),
        )
        if not deudor.debe:
            continue
        con_deuda += 1
        deuda_total += deudor.saldo
        vencido_total += deudor.vencido
        if deudor.meses_de_atraso > 0:
            con_atraso += 1

    # --------------------------------------------------------- los fondos ---
    total_en_fondos = CERO
    for fondo in db.scalars(
        select(Fondo).where(Fondo.edificio_id == edificio.id)
    ).all():
        saldo = fondos.calcular_saldo(
            fondos.Movimiento(tipo=m.tipo, monto=m.monto) for m in fondo.movimientos
        )
        total_en_fondos += saldo.saldo

    # ------------------------------------------------------- la respuesta ---
    series = reportes.armar_evolucion(
        periodos,
        gastos_por_periodo,
        {r.nombre: r.etiqueta for r in rubros.CATALOGO},
        rubros.RUBROS,
    )
    total_de_gastos = sum((s.total for s in series), CERO)
    resumen = reportes.resumir(armados)

    logger.info(
        "Reporte financiero del edificio %s (%d meses) pedido por %s",
        edificio_id,
        meses,
        quien_consulta.email,
    )

    return ReporteFinanciero(
        desde=armados[0].periodo,
        hasta=armados[-1].periodo,
        resumen=ResumenLeer(
            gastos=resumen.gastos,
            esperado=resumen.esperado,
            recaudado=resumen.recaudado,
            pendiente_de_confirmar=resumen.pendiente_de_confirmar,
            por_cobrar=resumen.por_cobrar,
            porcentaje_recaudado=resumen.porcentaje_recaudado,
            total_en_fondos=total_en_fondos,
        ),
        periodos=[
            PeriodoLeer(
                anio=p.anio,
                mes=p.mes,
                periodo=p.periodo,
                gastos=p.gastos,
                esperado=p.esperado,
                recaudado=p.recaudado,
                pendiente_de_confirmar=p.pendiente_de_confirmar,
                por_cobrar=p.por_cobrar,
                porcentaje_recaudado=p.porcentaje_recaudado,
                liquidada=(p.anio, p.mes) in publicadas,
            )
            for p in armados
        ],
        gastos_por_rubro=[
            RubroLeer(
                rubro=s.rubro,
                etiqueta=s.etiqueta,
                total=s.total,
                por_periodo=list(s.por_periodo),
                participacion=reportes.porcentaje(s.total, total_de_gastos),
            )
            for s in series
        ],
        morosidad_de_hoy=MorosidadLeer(
            cantidad_unidades=len(unidades),
            unidades_con_deuda=con_deuda,
            unidades_con_atraso=con_atraso,
            total=deuda_total,
            total_vencido=vencido_total,
            porcentaje_unidades_con_atraso=reportes.porcentaje(
                Decimal(con_atraso), Decimal(len(unidades))
            ),
        ),
    )

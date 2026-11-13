# -*- coding: utf-8 -*-
"""Consolidacion de los reportes financieros — logica pura (`F2-T16`).

============================================================================
CONSOLIDA, NO RECALCULA
============================================================================

Es la instruccion de la tarea y vale la pena explicar por que. Todos los
numeros de este reporte **ya los calcula alguien**: la morosidad sale de la
vista de deudores (`F2-T11`), los gastos agrupados por rubro de la misma
funcion que arma la apertura de la expensa (`F2-T05`), y lo recaudado de los
pagos confirmados (`F2-T09`).

Si este modulo volviera a calcularlos con sus propias consultas, el dia que una
regla cambie —que es "vencido", que pago cuenta— habria **dos respuestas
distintas a la misma pregunta**, y la que estaria mal seria siempre la del
reporte, porque es la que nadie revisa todos los dias. Un reporte que no
coincide con la pantalla de la que sale es peor que no tener reporte.

Asi que lo unico que hay aca son las cuentas que **nadie mas hace**: los
porcentajes y las comparaciones entre numeros que vienen de otros lados.

============================================================================
"ESPERADO" NO ES EL TOTAL DE LA EXPENSA
============================================================================

Y es la distincion que mas confunde de todo el modulo. El `total` de una
expensa son **los gastos del periodo**. Lo que el consorcio espera cobrar es la
suma de lo que debe cada unidad, que incluye ademas su recargo por mora y le
resta su saldo a favor.

Los dos numeros son correctos y responden preguntas distintas: "cuanto gastamos
este mes" y "cuanto tenemos que cobrar este mes". El reporte trae **los dos**,
porque mostrar uno solo hace que alguien saque conclusiones del que no
corresponde.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence

CERO = Decimal("0.00")
CIEN = Decimal("100.00")


def porcentaje(parte: Decimal, total: Decimal) -> Decimal | None:
    """Que proporcion del total representa la parte, con dos decimales.

    **Devuelve `None` cuando el total es cero, y no cero.** La diferencia
    importa: "se recaudo el 0%" dice que nadie pago, y "no hay nada que
    recaudar" dice que no hubo liquidacion. Un cero en lugar de un hueco es la
    forma mas facil de que un grafico muestre una caida que nunca existio.
    """
    if total <= 0:
        return None
    return (parte * CIEN / total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PeriodoDelReporte:
    """Un mes del reporte: lo que se gasto, lo que se espera y lo que entro."""

    anio: int
    mes: int

    # Los gastos del consorcio en el periodo. Es el total de la expensa.
    gastos: Decimal

    # Lo que hay que cobrar: la suma de lo que debe cada unidad, que incluye
    # recargos y descuenta saldos a favor. **No es lo mismo que `gastos`.**
    esperado: Decimal

    # Pagos confirmados contra las expensas de este periodo.
    recaudado: Decimal

    # Cargados por los residentes y sin conciliar. **No cuentan como
    # recaudado** — es la regla fundamental de `F2-T07`— pero se muestran,
    # porque un reporte que los esconde hace que la administracion crea que
    # falta cobrar plata que en realidad falta conciliar.
    pendiente_de_confirmar: Decimal

    @property
    def periodo(self) -> str:
        return f"{self.mes:02d}/{self.anio}"

    @property
    def porcentaje_recaudado(self) -> Decimal | None:
        return porcentaje(self.recaudado, self.esperado)

    @property
    def por_cobrar(self) -> Decimal:
        """Lo que falta cobrar de este periodo. Nunca negativo."""
        return max(CERO, self.esperado - self.recaudado)


@dataclass(frozen=True)
class RubroDelReporte:
    """Un rubro con su total y su evolucion mes a mes.

    `por_periodo` tiene **un valor por cada periodo del reporte, en el mismo
    orden**, con cero donde no hubo gasto de ese rubro. Es lo que permite
    graficarlo sin que el frontend tenga que rellenar huecos — y el relleno en
    el cliente es como se termina con dos series desalineadas.
    """

    rubro: str
    etiqueta: str
    total: Decimal
    por_periodo: tuple[Decimal, ...]

    @property
    def participacion(self) -> Decimal | None:
        """Se completa afuera: depende del total de todos los rubros."""
        return None


def armar_evolucion(
    periodos: Sequence[tuple[int, int]],
    gastos_por_periodo: dict[tuple[int, int], dict[str, Decimal]],
    etiquetas: dict[str, str],
    orden_de_rubros: Sequence[str],
) -> tuple[RubroDelReporte, ...]:
    """Arma la serie de cada rubro a lo largo de los periodos pedidos.

    `periodos` llega en el orden en que se va a mostrar y **manda**: cada rubro
    devuelve exactamente esa cantidad de valores, con cero donde no hubo gasto.

    El orden de los rubros es el del catalogo y no el del monto: la liquidacion
    y el reporte se leen con los rubros en el mismo orden mes a mes, asi que
    comparar dos meses es mirar la misma fila. Solo se devuelven los rubros que
    tuvieron al menos un gasto — diez filas en cero no son informacion.
    """
    series: list[RubroDelReporte] = []

    for rubro in orden_de_rubros:
        valores = tuple(
            gastos_por_periodo.get(periodo, {}).get(rubro, CERO)
            for periodo in periodos
        )
        total = sum(valores, CERO)
        if total <= 0:
            continue
        series.append(
            RubroDelReporte(
                rubro=rubro,
                etiqueta=etiquetas.get(rubro, rubro),
                total=total,
                por_periodo=valores,
            )
        )

    return tuple(series)


@dataclass(frozen=True)
class ResumenDelReporte:
    """Los totales de todo el rango, para el encabezado de la pantalla."""

    gastos: Decimal
    esperado: Decimal
    recaudado: Decimal
    pendiente_de_confirmar: Decimal

    @property
    def porcentaje_recaudado(self) -> Decimal | None:
        return porcentaje(self.recaudado, self.esperado)

    @property
    def por_cobrar(self) -> Decimal:
        return max(CERO, self.esperado - self.recaudado)


def resumir(periodos: Sequence[PeriodoDelReporte]) -> ResumenDelReporte:
    """Suma los periodos del rango.

    El porcentaje del resumen **se calcula sobre los totales y no es el
    promedio de los porcentajes mensuales**. Son dos numeros distintos: un mes
    con 100% de recaudacion sobre una expensa chica no compensa un mes con 50%
    sobre una grande, y promediarlos diria que se recaudo el 75% cuando no es
    cierto.
    """
    return ResumenDelReporte(
        gastos=sum((p.gastos for p in periodos), CERO),
        esperado=sum((p.esperado for p in periodos), CERO),
        recaudado=sum((p.recaudado for p in periodos), CERO),
        pendiente_de_confirmar=sum(
            (p.pendiente_de_confirmar for p in periodos), CERO
        ),
    )

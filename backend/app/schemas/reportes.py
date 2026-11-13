"""Esquemas del reporte financiero consolidado (`F2-T16`).

============================================================================
TRES NUMEROS QUE PARECEN EL MISMO Y NO LO SON
============================================================================

El reporte trae los tres a proposito, porque mostrar uno solo hace que alguien
saque conclusiones del que no corresponde:

- **`gastos`**: lo que gasto el consorcio en el periodo. Es el total de la
  expensa.
- **`esperado`**: lo que hay que cobrar. Es la suma de lo que debe cada unidad,
  que incluye su recargo por mora y le descuenta su saldo a favor. **No es
  igual a `gastos`.**
- **`recaudado`**: lo que efectivamente entro, contando **solo pagos
  confirmados**.

Y un cuarto que no se suma a ninguno: **`pendiente_de_confirmar`**, lo que los
residentes cargaron y la administracion no concilio. No cuenta como recaudado
—es la regla fundamental del modulo— pero se muestra, porque un reporte que lo
esconde hace creer que falta **cobrar** plata que en realidad falta
**conciliar**.

============================================================================
LOS PORCENTAJES PUEDEN SER NULOS, Y ESO SIGNIFICA ALGO
============================================================================

`None` quiere decir "no hay nada contra que medir" — un mes sin liquidacion— y
es distinto de `0`, que quiere decir "no se cobro nada". Un cero en lugar de un
hueco es la forma mas facil de que un grafico muestre una caida que nunca
existio.
"""

from decimal import Decimal

from pydantic import BaseModel


class ResumenLeer(BaseModel):
    """Los totales de todo el rango, para el encabezado de la pantalla.

    `porcentaje_recaudado` se calcula **sobre los totales y no es el promedio
    de los porcentajes mensuales**: un mes al 100% sobre una expensa chica no
    compensa uno al 50% sobre una grande.
    """

    gastos: Decimal
    esperado: Decimal
    recaudado: Decimal
    pendiente_de_confirmar: Decimal
    por_cobrar: Decimal
    porcentaje_recaudado: Decimal | None

    # Lo que el consorcio tiene guardado, que no es del periodo: es de hoy.
    total_en_fondos: Decimal


class PeriodoLeer(BaseModel):
    """Un mes del reporte.

    `liquidada` dice si ese periodo tiene expensa **publicada**. Un mes con
    gastos cargados y sin liquidar muestra `gastos` y `esperado` en cero, y sin
    este campo pareceria un mes en el que nadie pago — cuando lo que falta es
    generar la expensa.
    """

    anio: int
    mes: int
    periodo: str
    gastos: Decimal
    esperado: Decimal
    recaudado: Decimal
    pendiente_de_confirmar: Decimal
    por_cobrar: Decimal
    porcentaje_recaudado: Decimal | None
    liquidada: bool


class RubroLeer(BaseModel):
    """Un rubro con su total, su participacion y su evolucion.

    `por_periodo` trae **un valor por cada periodo del reporte, en el mismo
    orden**, con cero donde no hubo gasto: la pantalla lo grafica sin tener que
    rellenar huecos, y el relleno en el cliente es como se terminan
    desalineando dos series.
    """

    rubro: str
    etiqueta: str
    total: Decimal
    por_periodo: list[Decimal]
    participacion: Decimal | None


class MorosidadLeer(BaseModel):
    """La foto de la cartera **hoy**, no del periodo del reporte.

    El nombre del campo que la contiene lo dice (`morosidad_de_hoy`) para que
    nadie la lea como una serie: **la deuda no tiene periodo**. Una unidad que
    debe marzo sigue debiendolo en noviembre.

    `unidades_con_deuda` y `unidades_con_atraso` son dos numeros distintos: la
    primera incluye a quien debe la expensa publicada hace tres dias, que hay
    que cobrarle pero no esta atrasado. El color del Dashboard lo decide la
    segunda.
    """

    cantidad_unidades: int
    unidades_con_deuda: int
    unidades_con_atraso: int
    total: Decimal
    total_vencido: Decimal
    porcentaje_unidades_con_atraso: Decimal | None


class ReporteFinanciero(BaseModel):
    """Todo junto, en un solo pedido.

    Es un solo endpoint y no cuatro porque la pantalla los muestra juntos: con
    cuatro pedidos, la pantalla puede quedar con la recaudacion de un rango y
    los gastos de otro si uno falla, y eso es peor que no mostrar nada.
    """

    desde: str
    hasta: str
    resumen: ResumenLeer
    periodos: list[PeriodoLeer]
    gastos_por_rubro: list[RubroLeer]
    morosidad_de_hoy: MorosidadLeer

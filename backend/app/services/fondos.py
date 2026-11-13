# -*- coding: utf-8 -*-
"""Fondos del consorcio: tipos de movimiento y saldo — logica pura (`F2-T12`).

============================================================================
EL SIGNO LO DA EL TIPO, NUNCA EL NUMERO
============================================================================

Hay dos tipos de movimiento, `ingreso` y `egreso`, y **el monto siempre se
guarda positivo**. La alternativa —guardar egresos en negativo y un solo
campo— parece mas simple y es la fuente del error clasico del rubro: un egreso
cargado por error en positivo **suma en vez de restar**, y la unica forma de
notarlo es que el saldo no cierre, meses despues, sin pista de que fila fue.

Con un tipo explicito ese error no se puede cometer: no hay signo que cargar.
Y la traduccion de tipo a signo existe **una sola vez en todo el sistema**,
en `con_signo()`. Repetir `if tipo == "ingreso"` en cada consulta es como se
termina con un reporte que resta lo que otro suma.

============================================================================
EL SALDO SE CALCULA, NO SE GUARDA
============================================================================

Es la misma decision que ya rige para el saldo de una unidad y para la vista de
deudores, y por el mismo motivo: un saldo guardado hay que actualizarlo en cada
movimiento, y el dia que alguien inserte uno sin pasar por el endpoint el
numero queda mal **sin que nada falle**. Un saldo calculado no puede
desincronizarse.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Sequence

INGRESO = "ingreso"
EGRESO = "egreso"

TIPOS_DE_MOVIMIENTO: tuple[str, ...] = (INGRESO, EGRESO)
"""Los dos tipos posibles.

El CHECK de la tabla se arma desde esta tupla, asi que la base y la aplicacion
no pueden quedar en desacuerdo.
"""

ETIQUETAS: dict[str, str] = {
    INGRESO: "Ingreso",
    EGRESO: "Egreso",
}

CERO = Decimal("0.00")


def es_tipo_valido(tipo: str) -> bool:
    return tipo in TIPOS_DE_MOVIMIENTO


def etiqueta(tipo: str) -> str:
    """Como se lee el tipo en pantalla."""
    if tipo not in ETIQUETAS:
        raise ValueError(
            f"Tipo de movimiento invalido: {tipo!r}. Los validos son: "
            f"{', '.join(TIPOS_DE_MOVIMIENTO)}."
        )
    return ETIQUETAS[tipo]


def con_signo(tipo: str, monto: Decimal) -> Decimal:
    """El monto con el signo que le corresponde a su tipo.

    **La unica traduccion de tipo a signo del sistema.** Revienta con un tipo
    desconocido en vez de devolver cero: un movimiento que el sistema no sabe
    interpretar no puede valer cero en un saldo, porque desapareceria del total
    sin que nadie lo note.
    """
    if tipo == INGRESO:
        return monto
    if tipo == EGRESO:
        return -monto
    raise ValueError(f"Tipo de movimiento invalido: {tipo!r}.")


@dataclass(frozen=True)
class Movimiento:
    """Un movimiento, con lo justo para calcular un saldo.

    Entra con los datos ya leidos de la base, asi esta logica se puede probar
    con numeros escritos a mano.
    """

    tipo: str
    monto: Decimal


@dataclass(frozen=True)
class SaldoDeFondo:
    """El estado de un fondo: cuanto entro, cuanto salio y cuanto queda.

    Los tres por separado y no solo el saldo, porque responden preguntas
    distintas: "cuanto junto el consorcio para la obra" no es lo mismo que
    "cuanto queda disponible", y un fondo con mucho movimiento y saldo chico es
    una situacion muy distinta de uno que nunca se uso.
    """

    ingresos: Decimal
    egresos: Decimal
    saldo: Decimal
    cantidad_movimientos: int

    @property
    def esta_en_rojo(self) -> bool:
        """Si se gasto mas de lo que entro.

        **No se impide, se informa.** Un saldo negativo en un fondo significa
        casi siempre que falta cargar un ingreso — la transferencia que lo
        financio, el aporte extraordinario que se cobro en la expensa— y
        bloquear el egreso obligaria a inventar el ingreso para poder registrar
        un gasto que ya ocurrio. Lo que corresponde es mostrarlo.
        """
        return self.saldo < 0


def calcular_saldo(movimientos: Iterable[Movimiento]) -> SaldoDeFondo:
    """El saldo de un fondo a partir de sus movimientos.

    Suma los ingresos, suma los egresos y resta. Trabaja con `Decimal` de
    punta a punta: la regla de toda la fase.
    """
    ingresos = CERO
    egresos = CERO
    cantidad = 0

    for movimiento in movimientos:
        if not es_tipo_valido(movimiento.tipo):
            raise ValueError(
                f"Tipo de movimiento invalido: {movimiento.tipo!r}."
            )
        if movimiento.tipo == INGRESO:
            ingresos += movimiento.monto
        else:
            egresos += movimiento.monto
        cantidad += 1

    return SaldoDeFondo(
        ingresos=ingresos,
        egresos=egresos,
        saldo=ingresos - egresos,
        cantidad_movimientos=cantidad,
    )


def total_de_los_fondos(saldos: Sequence[SaldoDeFondo]) -> Decimal:
    """Cuanta plata tiene guardada el consorcio, sumando todos sus fondos.

    Es el numero que va al resumen del edificio y al Dashboard General. Se
    calcula aca y no en el endpoint para que la suma sea la misma en las dos
    pantallas que la muestran.
    """
    return sum((saldo.saldo for saldo in saldos), CERO)

# -*- coding: utf-8 -*-
"""Quien debe, cuanto y desde cuando — logica pura (`F2-T11`).

============================================================================
DEUDORES ES UNA VISTA CALCULADA, NO UNA TABLA
============================================================================

No hay tabla de deudores y no va a haberla. La deuda es lo liquidado y
publicado menos los pagos confirmados, y eso se calcula cada vez que se
pregunta.

Una tabla de deudores tendria que mantenerse al dia con cada pago que se
concilia, cada expensa que se publica y cada dia que pasa — porque la
antiguedad de una deuda cambia sola con el calendario. El dia que ese proceso
no corra, el sistema le dice a un propietario que esta al dia cuando no lo
esta, o lo pinta de rojo cuando ya pago. **Un dato que se puede calcular y se
guarda es un dato que algun dia miente.**

============================================================================
LA DEUDA DEL MES CORRIENTE NO ES ATRASO
============================================================================

Una expensa publicada el 1 con diez dias de vencimiento no esta atrasada el
dia 5: esta en termino. Recien pasado el vencimiento configurado del edificio
(`dias_vencimiento_expensas`, de `F1-T22`) cuenta como atraso, pinta el
Dashboard Visual y genera recargo.

Esto hace que **la misma deuda cambie de categoria sola, con el paso de los
dias, sin que nadie toque nada**. Es exactamente la razon por la que esto no
puede ser una tabla.

============================================================================
EL SEMAFORO: UN MES AMARILLO, MAS DE UNO ROJO
============================================================================

Los nombres de los estados son los del sistema de diseno (`--ok`, `--warn`,
`--crit`), porque es el mismo semaforo que pinta el edificio en la Fase 5 y no
una escala paralela. **La severidad se decide aca, en el backend**, y no en el
JavaScript: si la pantalla la calculara, el Dashboard Visual y la pantalla de
Deudores podrian pintar la misma unidad de colores distintos.

El naranja (`--pend`) no participa: esta reservado para mantenimiento en curso.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Sequence

from app.services.pagos import PeriodoDeCuenta

AL_DIA = "ok"
UN_MES = "warn"
VARIOS_MESES = "crit"

CERO = Decimal("0.00")


def fecha_de_vencimiento(publicada_en: datetime | None, dias: int) -> date | None:
    """Cuando vence una liquidacion publicada.

    Devuelve `None` si todavia no se publico: **una expensa en borrador no
    vence**, porque el vecino no tuvo forma de pagarla. Esa es la misma regla
    que decide que no se le muestre (`F2-T06`).

    Los dias se cuentan desde la publicacion y no desde el fin del periodo
    liquidado, porque es desde la publicacion que el residente puede pagar. Si
    la administracion liquida noviembre el 20 de diciembre, los diez dias
    corren desde el 20.
    """
    if publicada_en is None:
        return None
    return (publicada_en + timedelta(days=dias)).date()


def esta_vencida(vence_el: date | None, hoy: date | None = None) -> bool:
    """Si ya paso la fecha de vencimiento.

    El dia del vencimiento **todavia no es atraso**: se vence al dia
    siguiente. Pagar el ultimo dia del plazo es pagar en termino, y la
    comparacion estricta es lo que evita marcar en rojo a quien pago el mismo
    dia que vencia.
    """
    if vence_el is None:
        return False
    return (hoy or date.today()) > vence_el


def severidad(meses_de_atraso: int) -> str:
    """El color del semaforo para esa cantidad de meses atrasados.

    Un mes amarillo, mas de uno rojo, ninguno verde. Lo decide el backend para
    que el Dashboard Visual y la pantalla de Deudores no puedan pintar la
    misma unidad de colores distintos.
    """
    if meses_de_atraso <= 0:
        return AL_DIA
    if meses_de_atraso == 1:
        return UN_MES
    return VARIOS_MESES


@dataclass(frozen=True)
class Deudor:
    """Una unidad con su deuda, lista para mostrar o para pintar.

    `saldo` es **todo lo que debe** — capital mas recargos ya cargados, de
    periodos vencidos y del corriente. `vencido` es solo la parte atrasada, que
    es la que decide el color y la que genera recargo nuevo.

    Los dos van por separado porque responden preguntas distintas: "cuanto hay
    que cobrarle" y "que tan mal esta".
    """

    departamento_id: int
    identificador: str
    saldo: Decimal
    vencido: Decimal
    capital_vencido: Decimal
    meses_de_atraso: int
    periodo_mas_viejo: str | None
    periodos_impagos: tuple[str, ...]

    @property
    def severidad(self) -> str:
        return severidad(self.meses_de_atraso)

    @property
    def debe(self) -> bool:
        return self.saldo > 0


def armar_deudor(
    departamento_id: int,
    identificador: str,
    periodos: Sequence[PeriodoDeCuenta],
    hoy: date | None = None,
) -> Deudor:
    """El estado de deuda de una unidad a partir de sus periodos publicados.

    Tres totales distintos, y la diferencia entre ellos es la tarea:

      - `saldo`: todo lo impago, vencido o no. Es lo que hay que cobrarle.
      - `vencido`: solo lo que paso su fecha de vencimiento. **Decide el
        color.**
      - `capital_vencido`: lo vencido **sin los recargos ya cargados**. Es la
        base de un recargo nuevo, y por eso se calcula aparte — cobrar
        recargo sobre el recargo multiplica una deuda chica sola.

    `meses_de_atraso` cuenta **periodos vencidos con saldo**, no meses de
    calendario. Una unidad que debe marzo y mayo y pago abril tiene dos meses
    de atraso: el calendario diria tres.
    """
    saldo = CERO
    vencido = CERO
    capital_vencido = CERO
    impagos: list[str] = []

    # Del mas viejo al mas nuevo, para que el primero impago sea el mas viejo
    # sin tener que ordenar despues.
    for periodo in sorted(periodos, key=lambda p: (p.anio, p.mes)):
        if periodo.saldo <= 0:
            continue

        saldo += periodo.saldo

        if esta_vencida(periodo.vence_el, hoy):
            vencido += periodo.saldo
            capital_vencido += periodo.capital_impago
            impagos.append(periodo.periodo)

    return Deudor(
        departamento_id=departamento_id,
        identificador=identificador,
        saldo=saldo,
        vencido=vencido,
        capital_vencido=capital_vencido,
        meses_de_atraso=len(impagos),
        periodo_mas_viejo=impagos[0] if impagos else None,
        periodos_impagos=tuple(impagos),
    )


def ordenar(deudores: Sequence[Deudor]) -> list[Deudor]:
    """De mas a menos atrasada, y a igual atraso, de mayor a menor saldo.

    Es el orden de una pantalla de cobranza: lo primero que hay que atender es
    la unidad que debe desde hace mas tiempo, y entre dos que deben lo mismo,
    la que debe mas plata. El identificador desempata para que el listado no
    cambie de orden entre dos consultas identicas.
    """
    return sorted(
        deudores,
        key=lambda d: (-d.meses_de_atraso, -d.saldo, d.identificador),
    )

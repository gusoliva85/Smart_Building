# -*- coding: utf-8 -*-
"""La caja chica como sistema de fondo fijo — logica pura (`F2-T13`).

============================================================================
NO ES UNA CUENTA DE SALDO LIBRE, Y ESA ES TODA LA TAREA
============================================================================

Una caja chica no funciona como un fondo. Un fondo **acumula**: entra plata,
sale plata, y el saldo es lo que quedo. Una caja chica tiene un **monto fijo**
asignado — se gasta contra ella durante el mes, y cuando el efectivo baja, el
responsable rinde los comprobantes y se la **repone hasta ese monto original**.

La consecuencia practica es que las preguntas que se le hacen a una caja son
otras. A un fondo se le pregunta "cuanto hay". A una caja se le pregunta:

  - **cuanto queda disponible** (el efectivo que tiene hoy),
  - **cuanto hay que reponer** para volver al monto fijo — que es, exactamente,
    lo que el responsable ya gasto y todavia no le devolvieron,
  - y **si ya es momento de rendir**.

El fundamento, con las fuentes consultadas, esta en
`investigaciones/Caja_chica.md`. Ese documento tambien registra el error del
primer diseno: una `Caja` que solo guardaba "este edificio tiene esta persona
responsable", **sin movimientos**. No podia calcular saldo, no podia rendir
cuentas y no podia reponerse: le faltaba justamente el mecanismo que le da
sentido.

============================================================================
UNA REPOSICION ES UN MOVIMIENTO, NO UNA OPERACION ESPECIAL
============================================================================

Reponer la caja es cargar un `MovimientoCaja` de tipo `ingreso`. No hay
endpoint de "reponer" ni campo de "ultima reposicion": es exactamente como
funciona en la practica — la reposicion **es** un movimiento mas, el que trae
el disponible de vuelta al monto fijo.

Por eso los tipos de movimiento son **los mismos** que los de un fondo
(`services/fondos.py`) y no una tupla paralela. Es el mismo concepto — entra
plata o sale plata— y dos catalogos con los mismos dos valores es el camino
corto a que un reporte sume lo que otro resta.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from app.services.fondos import (  # noqa: F401  (se reexportan a proposito)
    EGRESO,
    INGRESO,
    TIPOS_DE_MOVIMIENTO,
    Movimiento,
    es_tipo_valido,
    etiqueta,
)

CERO = Decimal("0.00")

UMBRAL_DE_REPOSICION = Decimal("0.30")
"""Por debajo de que proporcion del monto fijo conviene rendir y reponer.

**Es un valor elegido, no una regla contable.** Las fuentes dicen "cuando el
efectivo baja a un minimo" sin fijar cual, porque depende de cada
administracion. Un 30% es un aviso temprano: deja margen para seguir operando
mientras se junta la rendicion, y evita el caso molesto de quedarse sin
efectivo el dia que aparece un gasto chico urgente.

Si alguna vez hace falta que sea configurable por edificio, es una columna en
`cajas` y este valor pasa a ser el default — no hay que tocar la logica.
"""


@dataclass(frozen=True)
class EstadoDeCaja:
    """Lo que hay que saber de una caja chica, todo derivado.

    Nada de esto se guarda: sale del monto fijo y de los movimientos. Un
    "disponible" guardado hay que actualizarlo en cada gasto, y el dia que
    alguien cargue un movimiento sin pasar por el endpoint el numero queda mal
    sin que nada falle.
    """

    monto_fijo: Decimal
    ingresos: Decimal
    egresos: Decimal
    disponible: Decimal
    cantidad_movimientos: int

    @property
    def pendiente_de_reposicion(self) -> Decimal:
        """Cuanto falta para volver al monto fijo.

        **Es tambien lo que el responsable gasto y todavia no le devolvieron**,
        que es la cifra que se mira al rendir. Nunca negativo: si la caja tiene
        mas de su monto fijo, no hay nada que reponer.
        """
        return max(CERO, self.monto_fijo - self.disponible)

    @property
    def necesita_reposicion(self) -> bool:
        """Si el disponible bajo del umbral y conviene rendir."""
        if self.monto_fijo <= 0:
            return False
        return self.disponible < self.monto_fijo * UMBRAL_DE_REPOSICION

    @property
    def esta_en_rojo(self) -> bool:
        """Si se gasto mas efectivo del que la caja tenia.

        **No se impide, se informa.** Casi siempre significa que falta cargar
        la reposicion con la que se financio el gasto, y bloquear el egreso
        obligaria a inventarla para poder registrar algo que ya se pago.
        """
        return self.disponible < 0

    @property
    def excede_el_fondo_fijo(self) -> bool:
        """Si la caja tiene mas plata que su monto fijo.

        Tambien se informa y no se impide, pero conviene mirarlo: significa que
        se repuso de mas, o que el fondo fijo del edificio cambio en la
        practica y nadie actualizo `monto_fijo`. Una caja chica que crece sola
        deja de ser una caja chica.
        """
        return self.disponible > self.monto_fijo


def calcular_estado(
    monto_fijo: Decimal,
    movimientos: Iterable[Movimiento],
) -> EstadoDeCaja:
    """El estado de una caja a partir de su monto fijo y sus movimientos.

    El disponible es ingresos menos egresos, igual que el saldo de un fondo.
    Lo que cambia no es la cuenta: es **contra que se la compara**.
    """
    ingresos = CERO
    egresos = CERO
    cantidad = 0

    for movimiento in movimientos:
        if not es_tipo_valido(movimiento.tipo):
            raise ValueError(f"Tipo de movimiento invalido: {movimiento.tipo!r}.")
        if movimiento.tipo == INGRESO:
            ingresos += movimiento.monto
        else:
            egresos += movimiento.monto
        cantidad += 1

    return EstadoDeCaja(
        monto_fijo=monto_fijo,
        ingresos=ingresos,
        egresos=egresos,
        disponible=ingresos - egresos,
        cantidad_movimientos=cantidad,
    )


def reposicion_sugerida(estado: EstadoDeCaja) -> Decimal:
    """Cuanto habria que reponer ahora para volver al monto fijo.

    Es `pendiente_de_reposicion`, expuesto como funcion porque es lo que la
    pantalla pone **como valor por defecto** en el formulario de reposicion:
    quien repone casi nunca quiere poner otro numero, y tipearlo a mano es la
    forma de equivocarse.
    """
    return estado.pendiente_de_reposicion

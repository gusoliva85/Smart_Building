# -*- coding: utf-8 -*-
"""Los dos estados de una expensa — logica pura, sin ORM y sin HTTP.

============================================================================
POR QUE UNA EXPENSA TIENE ESTADO, Y POR QUE SON DOS Y NO MAS
============================================================================

Decidido el 2026-11-13, y es la pieza que sostiene toda la regla de
regeneracion de `F2-T05`.

El Roadmap decia que se podia regenerar "la ultima" expensa del edificio. Es
una regla debil: la ultima puede llevar quince dias emitida y con la mitad del
edificio ya pagando, y regenerarla les cambia el monto abajo de los pies. La
regla que importa no es cual es la ultima, es **si alguien la vio**.

  - `borrador`: la generó la administración y **nadie más la vio**. No aparece
    en Mi cuenta, no genera deuda, no pinta nada en el Dashboard Visual y no
    cuenta el vencimiento. Se puede regenerar cuantas veces haga falta, que es
    exactamente lo que hay que hacer cuando se descubre un gasto mal cargado.
  - `publicada`: los residentes ya la tienen y ya pueden pagar. **No se
    regenera nunca mas**, sea la ultima o no.

No hay un tercer estado. "Vencida" y "pagada" **no son estados de la expensa**:
son cosas que se calculan. Vencida sale de comparar la fecha de publicacion con
los dias de vencimiento del edificio, y pagada sale de los pagos confirmados
contra ella, unidad por unidad —una expensa puede estar pagada por la mitad del
edificio y no por la otra, asi que no es un estado del documento. Guardarlos
como estado obligaria a mantenerlos al dia con un proceso que corra todos los
dias, y el dia que ese proceso no corra el sistema miente.

============================================================================
LA TRANSICION ES DE IDA
============================================================================

`borrador → publicada`, y nada mas. No existe "despublicar": una expensa que
los residentes ya vieron no se puede hacer invisible, porque lo que hay que
deshacer no esta en la base, esta en la cabeza de cuarenta propietarios que ya
anotaron cuanto tenian que pagar.

Un error descubierto despues de publicar se corrige en la liquidacion
siguiente, que es como se corrige en la realidad del rubro.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Mapping, Sequence

from app.services import finanzas

BORRADOR = "borrador"
PUBLICADA = "publicada"

ESTADOS: tuple[str, ...] = (BORRADOR, PUBLICADA)
"""Los estados posibles, en el orden en que ocurren.

El CHECK de la tabla se arma desde esta tupla, asi que la base y la aplicacion
no pueden quedar en desacuerdo sobre que es un estado valido.
"""

# Las transiciones permitidas. Un diccionario y no una cadena de `if`: la
# pregunta "que puede pasar despues de esto" se contesta leyendo una linea, y
# agregar un estado algun dia es agregar una entrada.
_TRANSICIONES: dict[str, tuple[str, ...]] = {
    BORRADOR: (PUBLICADA,),
    PUBLICADA: (),
}


def es_estado_valido(estado: str) -> bool:
    """Si ese valor se puede guardar en la columna."""
    return estado in ESTADOS


def transicion_valida(desde: str, hacia: str) -> bool:
    """Si una expensa puede pasar de un estado al otro.

    Devuelve `False` tambien cuando `desde` no es un estado conocido: una fila
    con un estado que el sistema no entiende no habilita nada.

    Pasar al mismo estado tampoco es una transicion valida. Publicar una
    expensa ya publicada no es inofensivo: volveria a escribir la fecha de
    publicacion y con eso correria el vencimiento de todo el edificio.
    """
    return hacia in _TRANSICIONES.get(desde, ())


def se_puede_regenerar(estado: str) -> bool:
    """Si una expensa en ese estado se puede volver a generar.

    Existe como funcion propia, y no como `estado == BORRADOR` escrito en el
    endpoint, porque es **la** regla de la fase: el dia que haya que revisarla,
    se revisa en un solo lugar y los tests la cubren una sola vez.
    """
    return estado == BORRADOR


def es_visible_para_el_residente(estado: str) -> bool:
    """Si el residente puede ver esa expensa.

    La otra cara de la misma regla: lo que se puede regenerar es, exactamente,
    lo que el residente todavia no vio. Son dos preguntas distintas con la
    misma respuesta, y escribirlas por separado es lo que evita que un dia se
    cambie una y no la otra.
    """
    return estado == PUBLICADA


# ===========================================================================
# EL CALCULO DE LA LIQUIDACION (`F2-T05`)
# ===========================================================================
#
# Todo esto es una funcion pura. No toca la base, no sabe que existe HTTP, y
# recibe como argumentos las tres cosas que el endpoint tiene que ir a buscar:
# el total a repartir, los coeficientes de las unidades, y —por unidad— cuanto
# debe vencido y cuanto tiene a favor.
#
# ============================================================================
# POR QUE LA DEUDA Y EL SALDO A FAVOR ENTRAN COMO ARGUMENTOS
# ============================================================================
#
# Porque todavia no se pueden averiguar. El recargo se calcula sobre lo que
# quedo vencido **e impago**, y el saldo a favor sobre lo que se pago **de
# mas**: las dos cosas necesitan el modelo `Pago`, que llega en `F2-T08`,
# despues de esta tarea.
#
# Asi que el calculo se escribe entero ahora y el endpoint le pasa hoy dos
# diccionarios vacios: con eso el recargo y el saldo dan cero, que es
# exactamente el comportamiento correcto con `recargo_mora_porcentual` en su
# valor por defecto. Cuando los pagos existan, se le pasan los datos reales y
# **no hay que tocar una linea de esta logica**. La costura queda en un solo
# lugar, probada, en vez de aparecer despues como un agregado.


@dataclass(frozen=True)
class ParteDeUnidad:
    """Lo que le toca a una unidad en una liquidacion, ya calculado.

    Es exactamente lo que despues se guarda en una fila de
    `ExpensaDepartamento`, con los mismos nombres: el endpoint copia campo por
    campo y no tiene que decidir nada.
    """

    departamento_id: int
    coeficiente: Decimal
    monto_expensa: Decimal
    recargo_mora: Decimal
    saldo_a_favor_aplicado: Decimal

    @property
    def total_a_pagar(self) -> Decimal:
        return self.monto_expensa + self.recargo_mora - self.saldo_a_favor_aplicado


def calcular_recargo(saldo_vencido: Decimal, porcentaje: Decimal) -> Decimal:
    """El recargo por mora sobre un saldo vencido, redondeado al centavo.

    **Se calcula sobre el capital atrasado y nada mas**, asi que no hay recargo
    sobre el recargo. Es la regla que evita el absurdo: con interes compuesto
    una deuda chica se multiplica sola y el numero deja de tener relacion con
    lo que se debe.

    Redondea al centavo mas cercano (`ROUND_HALF_UP`, el redondeo comercial que
    espera cualquiera que haga la cuenta a mano) en vez de truncar: truncar
    siempre favorece al mismo lado, y a lo largo de un ano eso es plata.

    Con `porcentaje` en cero devuelve cero, que es el caso por defecto de todo
    edificio que no configuro nada.
    """
    if saldo_vencido <= 0 or porcentaje <= 0:
        return Decimal("0.00")

    bruto = saldo_vencido * porcentaje / Decimal(100)
    return bruto.quantize(finanzas.CENTAVO, rounding=ROUND_HALF_UP)


def liquidar(
    total: Decimal,
    unidades: Sequence[tuple[int, Decimal]],
    *,
    porcentaje_mora: Decimal = Decimal(0),
    vencido_por_unidad: Mapping[int, Decimal] | None = None,
    saldo_a_favor_por_unidad: Mapping[int, Decimal] | None = None,
) -> tuple[ParteDeUnidad, ...]:
    """Calcula la liquidacion completa: que paga cada unidad y por que.

    `unidades` son pares `(departamento_id, coeficiente)` **en el orden en que
    se van a guardar**. El orden importa porque el prorrateo reparte los
    centavos sobrantes por resto mayor y desempata por posicion: con un orden
    estable, regenerar la misma expensa da el mismo resultado.

    `total` es **solo los gastos del periodo**. El recargo y el saldo a favor
    se aplican despues, unidad por unidad, y por eso no cambian el total de la
    expensa ni su apertura por rubro.

    ======================================================================
    EL ORDEN DE LAS TRES OPERACIONES, QUE NO ES INTERCAMBIABLE
    ======================================================================

    1. **Se prorratea** el total entre las unidades por coeficiente. Es lo
       unico que tiene que cerrar exacto contra el total.
    2. **Se suma el recargo** de cada unidad, calculado sobre lo que esa unidad
       debe vencido.
    3. **Se aplica el saldo a favor**, como maximo hasta cubrir lo que esa
       unidad tiene que pagar este mes.

    El saldo a favor va al final a proposito: si se aplicara antes del recargo,
    estaria pagando el recargo con plata que el vecino adelanto para sus
    expensas, y el recargo quedaria cancelado sin que nadie decidiera
    perdonarlo.

    ======================================================================
    EL SALDO A FAVOR NO SE SOBREGIRA
    ======================================================================

    Se aplica el minimo entre lo que hay a favor y lo que hay que pagar, asi
    que `total_a_pagar` **nunca da negativo**: a lo sumo da cero. El excedente
    que queda sin usar sigue siendo saldo a favor para el periodo siguiente, y
    quien lleva esa cuenta es `F2-T08`, no esta funcion — aca no se guarda
    estado.
    """
    vencido = vencido_por_unidad or {}
    a_favor = saldo_a_favor_por_unidad or {}

    coeficientes = [coeficiente for _, coeficiente in unidades]
    montos = finanzas.prorratear(total, coeficientes)

    partes: list[ParteDeUnidad] = []

    for (departamento_id, coeficiente), monto in zip(unidades, montos, strict=True):
        recargo = calcular_recargo(
            vencido.get(departamento_id, Decimal("0.00")),
            porcentaje_mora,
        )

        disponible = a_favor.get(departamento_id, Decimal("0.00"))
        if disponible < 0:
            raise ValueError(
                "Un saldo a favor negativo no es un saldo a favor: es deuda."
            )

        aplicado = min(disponible, monto + recargo)

        partes.append(
            ParteDeUnidad(
                departamento_id=departamento_id,
                coeficiente=coeficiente,
                monto_expensa=monto,
                recargo_mora=recargo,
                saldo_a_favor_aplicado=aplicado,
            )
        )

    return tuple(partes)

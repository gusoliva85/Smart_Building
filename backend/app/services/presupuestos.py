# -*- coding: utf-8 -*-
"""Estados de un presupuesto — logica pura (`F2-T14`).

============================================================================
PARA QUE SIRVE EL ESTADO
============================================================================

Para registrar **cual de varios presupuestos se eligio**. Sin estado, tres
presupuestos cargados para el mismo arreglo son tres filas indistinguibles y la
decision — la parte que importa— no queda escrita en ningun lado.

============================================================================
LA CADENA, Y POR QUE ES MAS CORTA QUE EL ESTANDAR
============================================================================

`Presupuesto → Gasto → Factura → Pago`. La practica formal de compras
(*procure-to-pay*) tiene mas pasos — requisicion, orden de compra, recepcion de
la mercaderia, cotejo de tres vias— pero un consorcio no los tiene: no hay
orden de compra formal ni recepcion como proceso separado. El **gasto** ya
cumple el rol de "lo que se decidio contratar", asi que agregar una entidad de
orden de compra seria sobre-modelar un proceso que en este dominio es mucho mas
chico. El fundamento, con las fuentes consultadas, esta en
`investigaciones/Presupuestos_y_Facturas.md`.

============================================================================
NO SE EXIGE NINGUNA CANTIDAD DE PRESUPUESTOS
============================================================================

Ni la Ley de Propiedad Horizontal ni el Codigo Civil y Comercial exigen un
minimo de presupuestos antes de aprobar un gasto: es buena practica de gestion,
y en la realidad lo fija el reglamento de cada consorcio ("a partir de tal
monto, pedir tres"). **El modelo no impone nada**: cero, uno o varios, y el
sistema no objeta.

Si alguna vez se pide la regla de "a partir de tal monto, exigir N", eso es una
configuracion del edificio — como `dias_vencimiento_expensas`— y no una
constante de codigo.
"""

from __future__ import annotations

PENDIENTE = "pendiente"
APROBADO = "aprobado"
RECHAZADO = "rechazado"

ESTADOS: tuple[str, ...] = (PENDIENTE, APROBADO, RECHAZADO)
"""Los tres estados posibles.

El CHECK de la tabla se arma desde esta tupla.
"""

# Las dos transiciones que existen. Una decision tomada sobre un presupuesto es
# un hecho registrado: se eligio este y no aquel, y eso no se reescribe.
_TRANSICIONES: dict[str, tuple[str, ...]] = {
    PENDIENTE: (APROBADO, RECHAZADO),
    APROBADO: (),
    RECHAZADO: (),
}


def es_estado_valido(estado: str) -> bool:
    return estado in ESTADOS


def transicion_valida(desde: str, hacia: str) -> bool:
    """Si un presupuesto puede pasar de un estado al otro.

    **Ninguna transicion vuelve.** Si se aprobo el presupuesto equivocado, lo
    que corresponde es rechazar el gasto que se generó y cargar la decision
    nueva, no reescribir cual se habia elegido — esa es justamente la
    informacion que un consorcista puede pedir ver.

    Pasar al mismo estado tampoco vale: aprobar dos veces no es inofensivo si
    en el medio se vinculo un gasto.
    """
    return hacia in _TRANSICIONES.get(desde, ())


def estados_siguientes(estado: str) -> tuple[str, ...]:
    """A que estados puede pasar, para que la pantalla sepa que botones poner.

    Mismo criterio que en pagos: el JavaScript no tiene su propia copia de la
    tabla de transiciones, porque esa copia es la que un dia ofrece un boton
    que el servidor rechaza.
    """
    return _TRANSICIONES.get(estado, ())


def esta_decidido(estado: str) -> bool:
    """Si alguien ya se pronuncio sobre este presupuesto.

    Sirve para contestar "¿esto sigue esperando una decision?" sin preguntar
    por los dos estados finales por separado, que es como se termina olvidando
    uno de los dos.
    """
    return estado in (APROBADO, RECHAZADO)


def puede_vincularse_a_un_gasto(estado: str) -> bool:
    """Si corresponde ligar este presupuesto al gasto que genero.

    **Solo el aprobado.** Un presupuesto rechazado vinculado a un gasto es una
    contradiccion: dice "no elegimos esto" y al mismo tiempo "esto es lo que
    gastamos". Y uno pendiente todavia no decidio nada.

    Es la regla que cierra la comparacion entre **lo que se presupuesto** y
    **lo que finalmente se pago**, que es para lo que existe el vinculo.
    """
    return estado == APROBADO

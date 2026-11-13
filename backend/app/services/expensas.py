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

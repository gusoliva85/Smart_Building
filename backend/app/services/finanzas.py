# -*- coding: utf-8 -*-
"""Estructura del edificio y coeficientes — logica pura, sin ORM y sin HTTP.

Dos cosas que parecen lejanas y van juntas: la **forma** del edificio (cuantos
pisos, cuantas unidades en cada uno) y el **porcentual** de cada unidad. Van
juntas porque la primera decide cuantos porcentuales hay que repartir, y porque
las dos se resuelven en el mismo momento real: cuando alguien da de alta un
edificio nuevo.

========================================================================
LA REGLA QUE FIJA TODO ESTE MODULO: EL COEFICIENTE ES EL DATO, NO EL CRITERIO
========================================================================

La ley argentina (Codigo Civil y Comercial, Libro Cuarto, Titulo V, articulos
2037 y siguientes) **no deja elegir un criterio de prorrateo por edificio**.
Lo que establece es que cada unidad funcional tiene un **porcentual fijo**,
calculado al redactarse el reglamento de propiedad horizontal y registrado ahi.
Ese numero es el dato legalmente vinculante, y los porcentuales de un edificio
suman 100%. No se recalcula en cada liquidacion: solo cambia si el reglamento
mismo cambia.

Entonces `calcular_partes_iguales()` y `calcular_por_metros_cuadrados()`
**no son criterios de prorrateo**: son atajos para no tener que tipear veinte
porcentuales a mano la primera vez. Despues de aplicarlos, cada unidad se edita
sola, y en la practica hace falta, porque un reglamento real casi nunca es
matematicamente parejo. El fundamento completo, con las fuentes consultadas,
esta en `documentacion/investigaciones/Prorrateo.md`.

========================================================================
LA PRECISION ES TRES DECIMALES, Y NO ES UN DETALLE
========================================================================

`Departamento.coeficiente` se guarda como `Numeric(6,3)`: **tres decimales**.
En la iteracion anterior estas dos funciones redondeaban a cuatro, asi que cada
valor perdia un decimal al guardarse y la suma real en la base dejaba de dar
100% aunque la funcion, en memoria, sumara perfecto. Se detecto en un edificio
de 28 unidades, que daba 99,989%.

Por eso la precision es `DECIMALES_COEFICIENTE`, una constante de este modulo,
y el reparto se hace **contando pasos enteros de 0,001 en vez de dividiendo
decimales**: con enteros no hay redondeo que acumule error, y la suma da 100%
exacto por construccion, no por suerte. Si alguna vez cambia la precision de la
columna, se cambia esa constante y nada mas.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Sequence

# ------------------------------------------------------------ precision ----

DECIMALES_COEFICIENTE = 3
"""Cuantos decimales guarda `Departamento.coeficiente` (`Numeric(6,3)`).

Redondear a mas decimales que los que la columna guarda rompe la suma al
persistir. Ver la cabecera del modulo.
"""

PASO_COEFICIENTE = Decimal(1).scaleb(-DECIMALES_COEFICIENTE)
"""El incremento mas chico representable: 0,001."""

TOTAL_COEFICIENTES = Decimal(100)
"""Los coeficientes de un edificio suman esto, exacto."""

PASOS_EN_EL_TOTAL = 100 * 10 ** DECIMALES_COEFICIENTE
"""El total expresado en pasos enteros: 100000.

Todo el reparto se hace en esta unidad. Repartir 100000 enteros entre N
unidades es exacto siempre; repartir `Decimal(100)` no lo es.
"""

# ------------------------------------------------- limites de estructura ----

MAX_PISOS = 40
MAX_UNIDADES_POR_PISO = 15
"""Techos deliberados de la generacion automatica.

Son un freno a que un numero tipeado mal genere miles de filas: `F1-T20` crea
toda la estructura en una sola transaccion, asi que un cero de mas no es un
dato raro, es una transaccion enorme.

Los dos valores se bajaron el 2026-11-09 (eran 60 y 40) para que esten cerca
de la realidad del rubro: un consorcio de mas de 40 pisos no existe en la
cartera que este sistema administra, y 40 unidades en un mismo piso es
directamente imposible. Un tope ajustado ataja el error de tipeo mucho mejor
que uno holgado — con 40 unidades por piso permitidas, escribir 14 en vez de 4
pasaba sin que nada avise.

Consecuencia de bajar el segundo: con 15 unidades por piso como maximo, la
numeracion nunca pasa de la letra O, asi que la continuacion `AA`, `AB` de
`_letra()` **ya no es alcanzable desde la API**. Se deja igual —es correcta y
esta probada aparte— porque el dia que haya que subir el tope tiene que seguir
funcionando; lo que no se deja es un test que la ejercite generando un piso de
28 unidades, porque ese piso ahora se rechaza.

Si algun dia hace falta un edificio mas grande, se sube la constante a
conciencia.
"""


# ==========================================================================
# LA ESTRUCTURA VACIA
# ==========================================================================


@dataclass(frozen=True)
class UnidadProyectada:
    """Un departamento que todavia no existe en la base.

    Solo trae lo que se puede saber sin preguntarle nada a nadie: como se
    llama y en que orden va. Los metros cuadrados, el propietario y el
    coeficiente se cargan despues, unidad por unidad.
    """

    identificador: str
    orden: int


@dataclass(frozen=True)
class PisoProyectado:
    """Un piso que todavia no existe en la base, con sus unidades."""

    numero: int
    orden: int
    unidades: tuple[UnidadProyectada, ...]


def generar_estructura(
    cantidad_pisos: int,
    unidades_por_piso: int,
) -> tuple[PisoProyectado, ...]:
    """La estructura vacia de un edificio: pisos numerados con sus unidades.

    Devuelve una proyeccion, no filas: este modulo no conoce los modelos. El
    alta de edificio (`F1-T20`) recorre esto y crea `Piso` y `Departamento`
    dentro de una sola transaccion.

    `numero` y `orden` nacen iguales a proposito. Son dos campos distintos
    porque el nombre de un piso y su lugar en la pila no siempre coinciden
    —planta baja, entrepiso, un edificio que saltea el 13—, pero eso es una
    correccion posterior del administrador: la generacion automatica no tiene
    con que adivinarlo, asi que arranca por el caso parejo.

    El identificador de la unidad es el numero de piso mas una letra: `1A`,
    `1B`, `2A`. Pasada la Z sigue con `AA`, que es la convencion de cualquier
    planilla de calculo y la unica que no se queda sin nombres.
    """
    if cantidad_pisos < 1:
        raise ValueError("Un edificio tiene al menos un piso.")
    if unidades_por_piso < 1:
        raise ValueError("Un piso tiene al menos una unidad.")
    if cantidad_pisos > MAX_PISOS:
        raise ValueError(
            "La generacion automatica admite hasta %d pisos." % MAX_PISOS
        )
    if unidades_por_piso > MAX_UNIDADES_POR_PISO:
        raise ValueError(
            "La generacion automatica admite hasta %d unidades por piso."
            % MAX_UNIDADES_POR_PISO
        )

    pisos = []
    for numero in range(1, cantidad_pisos + 1):
        unidades = tuple(
            UnidadProyectada(
                identificador="%d%s" % (numero, _letra(indice)),
                orden=indice + 1,
            )
            for indice in range(unidades_por_piso)
        )
        pisos.append(PisoProyectado(numero=numero, orden=numero, unidades=unidades))

    return tuple(pisos)


def contar_unidades(estructura: Sequence[PisoProyectado]) -> int:
    """Cuantas unidades tiene una estructura proyectada.

    Existe para que quien genera la estructura y despues pide coeficientes no
    tenga que multiplicar pisos por unidades de nuevo y arriesgarse a que las
    dos cuentas se desincronicen.
    """
    return sum(len(piso.unidades) for piso in estructura)


def _letra(indice: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA, 27 -> AB."""
    letras = ""
    resto = indice
    while True:
        letras = chr(ord("A") + resto % 26) + letras
        resto = resto // 26 - 1
        if resto < 0:
            return letras


# ==========================================================================
# LOS DOS ATAJOS DE CARGA INICIAL
# ==========================================================================


def calcular_partes_iguales(cantidad_unidades: int) -> tuple[Decimal, ...]:
    """Atajo: reparte 100% entre todas las unidades lo mas parejo posible.

    "Lo mas parejo posible" y no "igual" porque 100 casi nunca se divide exacto
    en tres decimales. Con 28 unidades, 100/28 = 3,571428..., que a tres
    decimales es 3,571, y veintiocho veces 3,571 dan 99,988: faltan doce pasos
    de 0,001.

    Esos doce pasos se reparten entre doce unidades distintas, que quedan en
    3,572. **No se le cargan todos a la ultima.** En el prorrateo de un monto
    si se hace asi —la ultima unidad se lleva el resto exacto para que no se
    pierda un centavo—, pero ahi se reparte el gasto de un mes. Un coeficiente
    es permanente: dejar una unidad en 3,583 mientras las otras veintisiete
    estan en 3,571 es una diferencia que ese propietario paga todos los meses,
    y no hace falta. Repartido de a un paso, nadie queda a mas de 0,001 de su
    vecino y la suma igual da 100% exacto.
    """
    if cantidad_unidades < 1:
        raise ValueError("Hace falta al menos una unidad para repartir el 100%.")

    return _pasos_a_coeficientes(
        _repartir_pasos([Fraction(1)] * cantidad_unidades)
    )


def calcular_por_metros_cuadrados(
    metros_cuadrados: Sequence[Decimal | int | str],
) -> tuple[Decimal, ...]:
    """Atajo: coeficiente proporcional a la superficie de cada unidad.

    Es el criterio con el que suele calcularse el porcentual original al
    redactar el reglamento, asi que como punto de partida es mejor que partes
    iguales cuando las superficies ya estan cargadas. Sigue siendo un punto de
    partida: el numero que manda es el del reglamento.

    Las superficies se reciben como `Decimal`, entero o texto, nunca como
    `float`: 0,1 no es representable en binario y un edificio no necesita que
    su reparto arranque con un error de redondeo heredado.
    """
    if not metros_cuadrados:
        raise ValueError("Hace falta al menos una unidad para repartir el 100%.")

    pesos = []
    for crudo in metros_cuadrados:
        metros = _a_fraccion(crudo)
        if metros <= 0:
            raise ValueError(
                "Los metros cuadrados de cada unidad tienen que ser mayores "
                "que cero para repartir por superficie."
            )
        pesos.append(metros)

    return _pasos_a_coeficientes(_repartir_pasos(pesos))


def validar_coeficientes(coeficientes: Sequence[Decimal | int | str]) -> bool:
    """¿Esta lista de coeficientes suma 100% exacto?

    Sin tolerancia, y es a proposito. La tolerancia tendria sentido si el error
    fuera inevitable por redondeo, pero no lo es: la columna guarda tres
    decimales y los dos atajos reparten en pasos de 0,001, asi que 100,000%
    exacto es alcanzable siempre, tambien cargando a mano. Una suma que no da
    100% no es ruido de calculo: es un edificio al que le falta cargar una
    unidad o le sobra un porcentual mal tipeado, y en los dos casos el
    prorrateo repartiria de mas o de menos entre propietarios reales.

    Cada valor se lleva primero a tres decimales, que es lo que la base va a
    guardar: lo que se valida es la suma **que va a quedar persistida**, no la
    que tiene mas precision en memoria. Esa diferencia es exactamente el error
    de 99,989% de la iteracion anterior.
    """
    if not coeficientes:
        return False

    suma = sum(
        (_a_decimal(valor).quantize(PASO_COEFICIENTE) for valor in coeficientes),
        Decimal(0),
    )
    return suma == TOTAL_COEFICIENTES


# ==========================================================================
# EL REPARTO, EN ENTEROS
# ==========================================================================


def _repartir_pasos(pesos: Sequence[Fraction]) -> tuple[int, ...]:
    """Reparte `PASOS_EN_EL_TOTAL` entre varios pesos, sin perder ni un paso.

    Es el metodo del **resto mayor**, el mismo con el que se reparten escaños
    por cantidad de votos: a cada uno le toca la parte entera de lo que le
    corresponde, y los pasos que sobran van de a uno a quienes quedaron con el
    resto fraccionario mas grande.

    Se trabaja con `Fraction`, que es exacto, en vez de `Decimal`: la cuenta
    intermedia `100000 * peso / total` casi nunca termina en decimal finito
    —100/28 no termina nunca— y cualquier redondeo intermedio es justo el error
    que este modulo existe para no cometer. Con fracciones no hay cuenta
    intermedia que redondear, y la suma de los enteros devueltos da
    `PASOS_EN_EL_TOTAL` por construccion.

    El desempate es por posicion, asi que el resultado es el mismo en cada
    corrida: dos unidades con el mismo peso no se alternan segun como quedaron
    ordenadas en memoria.
    """
    total = sum(pesos)
    exactos = [Fraction(PASOS_EN_EL_TOTAL) * peso / total for peso in pesos]

    pasos = [int(exacto) for exacto in exactos]
    sobrantes = PASOS_EN_EL_TOTAL - sum(pasos)

    orden = sorted(
        range(len(exactos)),
        key=lambda i: (-(exactos[i] - pasos[i]), i),
    )
    for i in orden[:sobrantes]:
        pasos[i] += 1

    return tuple(pasos)


def _pasos_a_coeficientes(pasos: Sequence[int]) -> tuple[Decimal, ...]:
    """Pasa pasos enteros de 0,001 a porcentajes con tres decimales."""
    return tuple(
        Decimal(paso).scaleb(-DECIMALES_COEFICIENTE).quantize(PASO_COEFICIENTE)
        for paso in pasos
    )


def _a_decimal(valor: Decimal | int | str) -> Decimal:
    """Lo que entra se vuelve `Decimal` sin pasar por `float`."""
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor))


def _a_fraccion(valor: Decimal | int | str) -> Fraction:
    """Lo mismo, pero exacto para las cuentas intermedias."""
    return Fraction(_a_decimal(valor))

"""Pruebas del prorrateo de un monto entre unidades (`F2-T03`).

Esta es la cuenta de la que depende la plata de todos los propietarios a la
vez, asi que lo que se prueba no es que devuelva numeros plausibles: es el
contrato de una balanza. **Lo que entra sale, al centavo, siempre.**

Las cuatro propiedades que se verifican:

  1. **La suma de las partes iguala el total, exacto.** En todos los casos:
     montos que no dividen bien, coeficientes desiguales, edificios de 3 y de
     160 unidades.
  2. **Ninguna unidad se desvia mas de un centavo** de su parte exacta. Es la
     diferencia con "la ultima unidad recibe el resto", que concentraba hasta
     N-1 centavos en el mismo vecino todos los meses.
  3. **El resultado es estable.** Dos corridas con los mismos datos dan lo
     mismo: una liquidacion que cambia al regenerarse sin que cambie ningun
     dato es una liquidacion en la que nadie puede confiar.
  4. **Se niega a repartir lo que no puede repartir bien**, en vez de devolver
     un numero que parece correcto.
"""

from decimal import Decimal
from fractions import Fraction

import pytest

from app.services import finanzas


def _suma(partes) -> Decimal:
    return sum(partes, Decimal("0.00"))


# ===========================================================================
# LA PROPIEDAD PRINCIPAL: LA SUMA CIERRA
# ===========================================================================


def test_el_caso_del_roadmap():
    """El caso exacto que pide la tarea: $4.849.900 entre 32 unidades con
    coeficientes **desiguales**.

    Los coeficientes se arman asi: 16 unidades de 2,500% y 16 de 3,750%, que
    suman 100,000% exacto y no son parejos. Un edificio real tiene unidades de
    distinto tamano, y el reparto parejo esconde el problema del redondeo.
    """
    coeficientes = [Decimal("2.500")] * 16 + [Decimal("3.750")] * 16
    assert finanzas.validar_coeficientes(coeficientes)
    total = Decimal("4849900.00")

    partes = finanzas.prorratear(total, coeficientes)

    assert _suma(partes) == total


def test_un_monto_que_no_divide_entre_tres():
    """El caso mas chico donde el problema se ve a mano: 100 entre tres partes
    iguales son 33,33 y sobra un centavo."""
    partes = finanzas.prorratear(
        Decimal("100.00"),
        [Decimal("33.334"), Decimal("33.333"), Decimal("33.333")],
    )

    assert _suma(partes) == Decimal("100.00")
    # El centavo sobrante va a la unidad con el coeficiente mas grande, que es
    # la que mas cerca estaba de merecerlo.
    assert partes == (Decimal("33.34"), Decimal("33.33"), Decimal("33.33"))


def test_coeficientes_desiguales_de_un_reglamento_real():
    """Un reglamento real casi nunca es parejo: hay unidades al frente, al
    contrafrente y un semipiso."""
    coeficientes = [
        Decimal("12.500"),
        Decimal("12.500"),
        Decimal("8.750"),
        Decimal("8.750"),
        Decimal("8.750"),
        Decimal("8.750"),
        Decimal("6.250"),
        Decimal("6.250"),
        Decimal("6.250"),
        Decimal("6.250"),
        Decimal("7.500"),
        Decimal("7.500"),
    ]
    total = Decimal("3287654.33")

    partes = finanzas.prorratear(total, coeficientes)

    assert _suma(partes) == total
    assert len(partes) == len(coeficientes)


def test_el_edificio_de_28_unidades():
    """El edificio con el que se descubrio el error historico del 99,989%: 28
    no divide 100 de forma exacta."""
    coeficientes = finanzas.calcular_partes_iguales(28)
    total = Decimal("1234567.89")

    partes = finanzas.prorratear(total, coeficientes)

    assert _suma(partes) == total


def test_un_edificio_grande():
    """160 unidades: que el metodo no se degrade con la cantidad."""
    coeficientes = finanzas.calcular_partes_iguales(160)
    total = Decimal("9876543.21")

    partes = finanzas.prorratear(total, coeficientes)

    assert _suma(partes) == total


@pytest.mark.parametrize(
    "total",
    ["0.01", "0.03", "1.00", "999.99", "100000.07", "9999999.99"],
)
def test_la_suma_cierra_para_cualquier_total(total):
    """Incluido un centavo entre siete unidades, que es el caso extremo: seis
    unidades reciben cero y una recibe el centavo."""
    coeficientes = finanzas.calcular_partes_iguales(7)

    partes = finanzas.prorratear(Decimal(total), coeficientes)

    assert _suma(partes) == Decimal(total)


@pytest.mark.parametrize("cantidad", [1, 2, 3, 7, 13, 28, 31, 32, 99])
def test_la_suma_cierra_para_cualquier_cantidad_de_unidades(cantidad):
    coeficientes = finanzas.calcular_partes_iguales(cantidad)

    partes = finanzas.prorratear(Decimal("4849900.00"), coeficientes)

    assert _suma(partes) == Decimal("4849900.00")
    assert len(partes) == cantidad


# ===========================================================================
# LA SEGUNDA PROPIEDAD: NADIE SE LLEVA LOS CENTAVOS DE TODOS
# ===========================================================================


def test_ninguna_unidad_se_desvia_mas_de_un_centavo_de_su_parte_exacta():
    """**La prueba que justifica el cambio de regla.** Con "la ultima unidad
    recibe el resto", una unidad podia quedar hasta 31 centavos por encima de
    su parte exacta. Con resto mayor, ninguna se pasa de un centavo.
    """
    coeficientes = finanzas.calcular_partes_iguales(32)
    total = Decimal("4849900.00")

    partes = finanzas.prorratear(total, coeficientes)

    for parte, coeficiente in zip(partes, coeficientes, strict=True):
        exacta = Fraction(total) * Fraction(coeficiente) / Fraction(100)
        assert abs(Fraction(parte) - exacta) < Fraction(1, 100)


def test_los_centavos_sobrantes_se_reparten_y_no_se_acumulan():
    """Con tres unidades iguales y un total que deja dos centavos sueltos, los
    dos centavos van a dos unidades distintas, no los dos a la misma."""
    coeficientes = finanzas.calcular_partes_iguales(3)

    partes = finanzas.prorratear(Decimal("10.00"), coeficientes)

    assert _suma(partes) == Decimal("10.00")
    # 3,34 / 3,33 / 3,33: el sobrante se distribuye de a un centavo.
    assert max(partes) - min(partes) == Decimal("0.01")


def test_la_ultima_unidad_no_es_la_que_absorbe_el_resto():
    """Lo que la regla vieja hacia y esta no: con partes iguales, el centavo
    sobrante va a la primera unidad por desempate de posicion, no a la
    ultima."""
    coeficientes = finanzas.calcular_partes_iguales(3)

    partes = finanzas.prorratear(Decimal("10.00"), coeficientes)

    assert partes[-1] == min(partes)


# ===========================================================================
# LA TERCERA PROPIEDAD: EL RESULTADO ES ESTABLE
# ===========================================================================


def test_dos_corridas_con_los_mismos_datos_dan_lo_mismo():
    """Una liquidacion que cambia al regenerarse sin que cambie ningun dato es
    una liquidacion en la que nadie puede confiar."""
    coeficientes = finanzas.calcular_partes_iguales(28)
    total = Decimal("987654.32")

    primera = finanzas.prorratear(total, coeficientes)
    segunda = finanzas.prorratear(total, coeficientes)

    assert primera == segunda


def test_el_orden_de_salida_es_el_de_entrada():
    """La unidad 1A tiene que recibir la parte de 1A. El endpoint va a
    emparejar las dos listas por posicion, asi que esto es parte del
    contrato."""
    partes = finanzas.prorratear(
        Decimal("1000.00"),
        [Decimal("50.000"), Decimal("30.000"), Decimal("20.000")],
    )

    assert partes == (Decimal("500.00"), Decimal("300.00"), Decimal("200.00"))


# ===========================================================================
# LA CUARTA PROPIEDAD: SE NIEGA ANTES DE REPARTIR MAL
# ===========================================================================


def test_no_reparte_si_los_coeficientes_no_suman_cien():
    """Con 99,9% el consorcio reparte menos de lo que gasto y la diferencia no
    la paga nadie. El mensaje dice cuanto suman, que es el dato con el que se
    arregla."""
    with pytest.raises(ValueError) as error:
        finanzas.prorratear(
            Decimal("1000.00"), [Decimal("50.000"), Decimal("49.900")]
        )

    assert "99.900" in str(error.value)


def test_no_reparte_si_los_coeficientes_pasan_de_cien():
    with pytest.raises(ValueError):
        finanzas.prorratear(
            Decimal("1000.00"), [Decimal("50.000"), Decimal("50.001")]
        )


def test_no_reparte_sin_unidades():
    with pytest.raises(ValueError):
        finanzas.prorratear(Decimal("1000.00"), [])


@pytest.mark.parametrize("total", ["0.00", "-1500.00"])
def test_no_reparte_un_total_que_no_es_positivo(total):
    """Un periodo sin gastos no se liquida; no se liquida en cero."""
    with pytest.raises(ValueError):
        finanzas.prorratear(Decimal(total), [Decimal("100.000")])


def test_no_reparte_un_total_con_tres_decimales():
    """Seria un total que la base no puede guardar tal como se repartio."""
    with pytest.raises(ValueError) as error:
        finanzas.prorratear(Decimal("1000.005"), [Decimal("100.000")])

    assert "decimales" in str(error.value)


def test_no_reparte_con_un_coeficiente_negativo():
    with pytest.raises(ValueError):
        finanzas.prorratear(
            Decimal("1000.00"), [Decimal("110.000"), Decimal("-10.000")]
        )


def test_un_total_que_no_es_numero_se_rechaza():
    """`Decimal('NaN')` atraviesa cualquier comparacion `>` sin levantar nada y
    llegaria hasta el reparto."""
    with pytest.raises(ValueError):
        finanzas.prorratear(Decimal("NaN"), [Decimal("100.000")])


# ===========================================================================
# UNIDADES EXENTAS
# ===========================================================================


def test_una_unidad_con_coeficiente_cero_no_paga_nada():
    """Existen: una unidad exenta por reglamento, o un espacio que figura como
    unidad y no participa de los gastos."""
    partes = finanzas.prorratear(
        Decimal("1000.00"),
        [Decimal("0.000"), Decimal("50.000"), Decimal("50.000")],
    )

    assert partes[0] == Decimal("0.00")
    assert _suma(partes) == Decimal("1000.00")


def test_una_unidad_exenta_no_recibe_centavos_sobrantes():
    """El sobrante va a quien le corresponde por resto, y el resto de una
    unidad exenta es cero: nunca puede quedar primera en la cola."""
    coeficientes = [Decimal("0.000")] + list(finanzas.calcular_partes_iguales(3))

    partes = finanzas.prorratear(Decimal("10.00"), coeficientes)

    assert partes[0] == Decimal("0.00")
    assert _suma(partes) == Decimal("10.00")

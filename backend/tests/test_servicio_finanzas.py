# -*- coding: utf-8 -*-
"""Tests de `services/finanzas.py` — estructura vacia y atajos de coeficiente.

Son tests de logica pura: no hay cliente HTTP, no hay base y no hay fixtures.
Corren en milisegundos, que es el motivo por el que la regla se escribe en un
servicio antes de modelar la tabla que la usa.

El test que no se puede sacar de aca es `test_veintiocho_unidades_...`: es la
reproduccion del error real de la iteracion anterior, donde la suma guardada
daba 99,989% en un edificio de 28 unidades.
"""

from decimal import Decimal

import pytest

from app.services import finanzas


def suma_persistida(coeficientes):
    """La suma tal como va a quedar en la base, con tres decimales.

    Los tests tienen que mirar esto y no la suma en memoria: el error historico
    era exactamente la diferencia entre las dos.
    """
    return sum(
        (c.quantize(finanzas.PASO_COEFICIENTE) for c in coeficientes),
        Decimal(0),
    )


def decimales_de(valor: Decimal) -> int:
    expuesto = -valor.as_tuple().exponent
    return max(expuesto, 0)


# ==========================================================================
# LA ESTRUCTURA VACIA
# ==========================================================================


def test_genera_un_piso_por_cada_piso_pedido():
    estructura = finanzas.generar_estructura(cantidad_pisos=5, unidades_por_piso=2)

    assert len(estructura) == 5
    assert [piso.numero for piso in estructura] == [1, 2, 3, 4, 5]


def test_cada_piso_recibe_la_cantidad_de_unidades_pedida():
    estructura = finanzas.generar_estructura(cantidad_pisos=3, unidades_por_piso=4)

    assert all(len(piso.unidades) == 4 for piso in estructura)
    assert finanzas.contar_unidades(estructura) == 12


def test_el_identificador_es_el_piso_mas_una_letra():
    estructura = finanzas.generar_estructura(cantidad_pisos=2, unidades_por_piso=3)

    identificadores = [
        unidad.identificador for piso in estructura for unidad in piso.unidades
    ]
    assert identificadores == ["1A", "1B", "1C", "2A", "2B", "2C"]


def test_pasada_la_zeta_las_letras_siguen_con_dos_caracteres():
    """Se prueba el nombrador directo, y no generando un piso de 28 unidades.

    Con `MAX_UNIDADES_POR_PISO` en 15 (bajado el 2026-11-09), un piso de 28
    unidades se rechaza antes de nombrar nada, asi que este caso ya no se puede
    ejercitar por `generar_estructura()`. La continuacion despues de la Z se
    deja escrita y probada igual: es la convencion de cualquier planilla de
    calculo y la unica que no se queda sin nombres, y tiene que seguir siendo
    correcta el dia que el tope se suba.
    """
    letras = [finanzas._letra(indice) for indice in range(28)]

    assert letras[0] == "A"
    assert letras[25] == "Z"
    assert letras[26] == "AA"
    assert letras[27] == "AB"
    assert len(set(letras)) == 28


def test_el_tope_de_unidades_no_llega_a_necesitar_dos_letras():
    """El tope vigente y el nombrador son coherentes entre si.

    Si alguien sube `MAX_UNIDADES_POR_PISO` por encima de 26, este test falla y
    avisa que la numeracion de dos letras pasa a ser alcanzable de verdad — o
    sea que hay que revisar las pantallas que muestran identificadores, no solo
    la constante.
    """
    estructura = finanzas.generar_estructura(
        cantidad_pisos=1, unidades_por_piso=finanzas.MAX_UNIDADES_POR_PISO
    )

    identificadores = [unidad.identificador for unidad in estructura[0].unidades]
    assert all(len(ident) == len("1") + 1 for ident in identificadores)


def test_el_orden_de_apilado_arranca_igual_al_numero_de_piso():
    estructura = finanzas.generar_estructura(cantidad_pisos=4, unidades_por_piso=1)

    assert [piso.orden for piso in estructura] == [1, 2, 3, 4]


def test_las_unidades_de_un_piso_vienen_ordenadas():
    estructura = finanzas.generar_estructura(cantidad_pisos=1, unidades_por_piso=3)

    assert [unidad.orden for unidad in estructura[0].unidades] == [1, 2, 3]


def test_la_estructura_no_trae_coeficientes_ni_metros():
    """La forma del edificio y sus porcentuales son dos cargas distintas."""
    estructura = finanzas.generar_estructura(cantidad_pisos=1, unidades_por_piso=1)
    unidad = estructura[0].unidades[0]

    assert not hasattr(unidad, "coeficiente")
    assert not hasattr(unidad, "metros_cuadrados")


@pytest.mark.parametrize("pisos,unidades", [(0, 2), (-1, 2), (2, 0), (2, -3)])
def test_un_edificio_sin_pisos_o_sin_unidades_no_se_genera(pisos, unidades):
    with pytest.raises(ValueError):
        finanzas.generar_estructura(cantidad_pisos=pisos, unidades_por_piso=unidades)


def test_los_numeros_absurdos_se_rechazan_antes_de_generar_nada():
    """`F1-T20` crea todo en una transaccion: un cero de mas es una barbaridad."""
    with pytest.raises(ValueError):
        finanzas.generar_estructura(
            cantidad_pisos=finanzas.MAX_PISOS + 1, unidades_por_piso=1
        )
    with pytest.raises(ValueError):
        finanzas.generar_estructura(
            cantidad_pisos=1,
            unidades_por_piso=finanzas.MAX_UNIDADES_POR_PISO + 1,
        )


def test_el_tope_exacto_si_se_genera():
    estructura = finanzas.generar_estructura(
        cantidad_pisos=finanzas.MAX_PISOS,
        unidades_por_piso=finanzas.MAX_UNIDADES_POR_PISO,
    )

    assert len(estructura) == finanzas.MAX_PISOS


# ==========================================================================
# ATAJO 1 — PARTES IGUALES
# ==========================================================================


def test_partes_iguales_cuando_divide_exacto():
    assert finanzas.calcular_partes_iguales(4) == (
        Decimal("25.000"),
        Decimal("25.000"),
        Decimal("25.000"),
        Decimal("25.000"),
    )


def test_partes_iguales_devuelve_una_por_unidad():
    assert len(finanzas.calcular_partes_iguales(13)) == 13


@pytest.mark.parametrize("cantidad", [1, 2, 3, 6, 7, 9, 11, 12, 28, 31, 97, 100, 365])
def test_partes_iguales_siempre_suma_cien_exacto(cantidad):
    coeficientes = finanzas.calcular_partes_iguales(cantidad)

    assert suma_persistida(coeficientes) == Decimal("100.000")


def test_partes_iguales_con_una_sola_unidad_le_da_todo():
    assert finanzas.calcular_partes_iguales(1) == (Decimal("100.000"),)


def test_partes_iguales_reparte_el_sobrante_y_no_lo_apila_en_la_ultima():
    """El coeficiente es permanente: nadie queda a mas de un paso de su vecino.

    Con 28 unidades sobran 12 pasos de 0,001. Si se los cargara todos a una
    sola unidad quedaria en 3,583 contra 3,571 de las otras veintisiete, y esa
    diferencia la paga ese propietario todos los meses.
    """
    coeficientes = finanzas.calcular_partes_iguales(28)

    assert max(coeficientes) - min(coeficientes) == Decimal("0.001")
    assert sorted(set(coeficientes)) == [Decimal("3.571"), Decimal("3.572")]
    assert coeficientes.count(Decimal("3.572")) == 12


def test_partes_iguales_con_cero_unidades_no_tiene_sentido():
    with pytest.raises(ValueError):
        finanzas.calcular_partes_iguales(0)


# ==========================================================================
# ATAJO 2 — POR METROS CUADRADOS
# ==========================================================================


def test_por_metros_reparte_proporcional():
    coeficientes = finanzas.calcular_por_metros_cuadrados(["50", "50", "100"])

    assert coeficientes == (
        Decimal("25.000"),
        Decimal("25.000"),
        Decimal("50.000"),
    )


def test_por_metros_con_superficies_iguales_da_lo_mismo_que_partes_iguales():
    assert finanzas.calcular_por_metros_cuadrados(
        ["62.5"] * 8
    ) == finanzas.calcular_partes_iguales(8)


def test_por_metros_acepta_decimales_de_superficie():
    coeficientes = finanzas.calcular_por_metros_cuadrados(
        [Decimal("48.75"), Decimal("63.20"), Decimal("88.05")]
    )

    assert suma_persistida(coeficientes) == Decimal("100.000")
    assert coeficientes[2] > coeficientes[1] > coeficientes[0]


@pytest.mark.parametrize(
    "metros",
    [
        ["33.33", "33.33", "33.34"],
        ["10", "20", "30", "40", "55", "61", "77"],
        ["45.5"] * 28,
        [str(40 + i) for i in range(28)],
        ["120", "35.75", "35.75", "99.9", "12.5"],
    ],
)
def test_por_metros_siempre_suma_cien_exacto(metros):
    coeficientes = finanzas.calcular_por_metros_cuadrados(metros)

    assert len(coeficientes) == len(metros)
    assert suma_persistida(coeficientes) == Decimal("100.000")


def test_por_metros_con_una_sola_unidad_le_da_todo():
    assert finanzas.calcular_por_metros_cuadrados(["70"]) == (Decimal("100.000"),)


def test_por_metros_sin_unidades_no_tiene_sentido():
    with pytest.raises(ValueError):
        finanzas.calcular_por_metros_cuadrados([])


@pytest.mark.parametrize("metros", [["50", "0"], ["50", "-10"]])
def test_una_unidad_sin_superficie_no_puede_repartirse_por_superficie(metros):
    with pytest.raises(ValueError):
        finanzas.calcular_por_metros_cuadrados(metros)


# ==========================================================================
# LA PRECISION — TRES DECIMALES, NO CUATRO
# ==========================================================================


def test_la_precision_declarada_es_la_de_la_columna():
    """`Departamento.coeficiente` es `Numeric(6,3)`."""
    assert finanzas.DECIMALES_COEFICIENTE == 3
    assert finanzas.PASO_COEFICIENTE == Decimal("0.001")


@pytest.mark.parametrize("cantidad", [3, 7, 13, 28, 31])
def test_ningun_coeficiente_trae_mas_de_tres_decimales(cantidad):
    """Mas decimales que los que la columna guarda = suma rota al persistir."""
    for coeficiente in finanzas.calcular_partes_iguales(cantidad):
        assert decimales_de(coeficiente) <= finanzas.DECIMALES_COEFICIENTE

    metros = [str(30 + i) for i in range(cantidad)]
    for coeficiente in finanzas.calcular_por_metros_cuadrados(metros):
        assert decimales_de(coeficiente) <= finanzas.DECIMALES_COEFICIENTE


def test_veintiocho_unidades_el_error_historico_de_99_989():
    """Regresion del bug real de la iteracion anterior.

    Las funciones redondeaban a cuatro decimales y la columna guarda tres: cada
    valor perdia un decimal al guardarse y la suma en la base daba 99,989% en
    un edificio de 28 unidades. Lo que se verifica aca es la suma **ya
    redondeada a tres decimales**, que es la que iba a quedar persistida.
    """
    coeficientes = finanzas.calcular_partes_iguales(28)

    assert len(coeficientes) == 28
    assert suma_persistida(coeficientes) == Decimal("100.000")
    assert suma_persistida(coeficientes) != Decimal("99.989")

    por_superficie = finanzas.calcular_por_metros_cuadrados(["45.5"] * 28)
    assert suma_persistida(por_superficie) == Decimal("100.000")


def test_un_edificio_entero_generado_y_con_coeficientes_cierra_en_cien():
    """Las dos mitades de la tarea, juntas: 7 pisos por 4 = 28 unidades."""
    estructura = finanzas.generar_estructura(cantidad_pisos=7, unidades_por_piso=4)
    coeficientes = finanzas.calcular_partes_iguales(
        finanzas.contar_unidades(estructura)
    )

    assert len(coeficientes) == 28
    assert finanzas.validar_coeficientes(coeficientes)


# ==========================================================================
# LA VALIDACION
# ==========================================================================


def test_cien_exacto_es_valido():
    assert finanzas.validar_coeficientes(["25.000", "25.000", "50.000"])


def test_una_suma_que_no_da_cien_no_es_valida():
    assert not finanzas.validar_coeficientes(["25.000", "25.000", "25.000"])
    assert not finanzas.validar_coeficientes(["50.000", "50.001"])


def test_una_lista_vacia_no_es_un_edificio_valido():
    assert not finanzas.validar_coeficientes([])


def test_la_validacion_mira_la_suma_ya_redondeada_a_tres_decimales():
    """Cuatro decimales que suman 100 en memoria, pero no al guardarse.

    Veintiocho valores de 3,5714 suman 99,9992 en memoria; redondeados a los
    tres decimales que guarda la columna quedan en 3,571 y suman 99,988. La
    validacion tiene que ver lo segundo.
    """
    assert not finanzas.validar_coeficientes(["3.5714"] * 28)


def test_los_dos_atajos_pasan_su_propia_validacion():
    assert finanzas.validar_coeficientes(finanzas.calcular_partes_iguales(28))
    assert finanzas.validar_coeficientes(
        finanzas.calcular_por_metros_cuadrados([str(40 + i) for i in range(28)])
    )


# ==========================================================================
# COMPLETAR EL RESTO ENTRE LAS UNIDADES EN BLANCO
#
# El caso que lo motiva, dicho por el usuario: cuatro unidades, dos cargadas
# al 30% cada una, falta repartir 40% entre las otras dos, o sea 20% a cada
# una. La diferencia con los dos atajos es que esto **no toca** las cargadas.
# ==========================================================================


def test_el_resto_es_lo_que_falta_para_cien():
    resto = finanzas.resto_por_repartir([Decimal("30.000"), Decimal("30.000")])

    assert resto == Decimal("40.000")


def test_sin_nada_cargado_el_resto_es_todo():
    assert finanzas.resto_por_repartir([]) == Decimal("100.000")


def test_el_resto_puede_dar_negativo_y_no_es_un_error_de_la_funcion():
    """Devuelve el numero en vez de levantar: quien llama tiene que poder
    mirarlo para explicar que las cargadas ya pasan el 100%."""
    resto = finanzas.resto_por_repartir([Decimal("60.000"), Decimal("60.000")])

    assert resto == Decimal("-20.000")


def test_el_caso_del_usuario_cuatro_unidades_dos_al_treinta():
    resto = finanzas.resto_por_repartir([Decimal("30.000"), Decimal("30.000")])

    partes = finanzas.completar_el_resto(resto, 2)

    assert partes == (Decimal("20.000"), Decimal("20.000"))


def test_el_resto_que_no_divide_exacto_igual_cierra():
    """40% entre tres unidades es 13,333... y una tiene que quedar en 13,334,
    o se pierde un paso y el edificio nunca suma 100."""
    partes = finanzas.completar_el_resto(Decimal("40.000"), 3)

    assert sum(partes) == Decimal("40.000")
    assert sorted(set(partes)) == [Decimal("13.333"), Decimal("13.334")]


def test_completar_el_resto_mas_lo_cargado_da_cien_exacto():
    cargados = [Decimal("12.500"), Decimal("7.250"), Decimal("0.000")]
    resto = finanzas.resto_por_repartir(cargados)

    partes = finanzas.completar_el_resto(resto, 7)

    assert sum(cargados) + sum(partes) == finanzas.TOTAL_COEFICIENTES
    assert finanzas.validar_coeficientes(list(cargados) + list(partes))


def test_el_sobrante_se_reparte_de_a_un_paso_tambien_en_el_resto():
    """Mismo criterio que los atajos: nadie queda a mas de 0,001 de su vecino.
    Un coeficiente es permanente, asi que una unidad con el sobrante entero
    pagaria esa diferencia todos los meses."""
    partes = finanzas.completar_el_resto(Decimal("10.000"), 3)

    assert max(partes) - min(partes) == finanzas.PASO_COEFICIENTE


def test_sin_unidades_en_blanco_no_hay_nada_que_completar():
    with pytest.raises(ValueError):
        finanzas.completar_el_resto(Decimal("40.000"), 0)


def test_no_se_completa_un_resto_de_cero():
    """A las unidades en blanco les tocaria 0%, que es un dato inventado y no
    un dato que falte: lo rechaza y quien llama lo explica."""
    with pytest.raises(ValueError):
        finanzas.completar_el_resto(Decimal("0.000"), 3)


def test_no_se_completa_un_resto_negativo():
    with pytest.raises(ValueError):
        finanzas.completar_el_resto(Decimal("-5.000"), 3)

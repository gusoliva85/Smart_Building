"""Pruebas del calculo de la liquidacion — logica pura (`F2-T05`).

`expensas.liquidar()` es la funcion que decide cuanto paga cada propietario.
Lo que se prueba es su contrato completo, incluido lo que **todavia no se
usa**: el recargo por mora y el saldo a favor se calculan aca pero recien van a
tener datos reales cuando exista `Pago` (`F2-T08`). Se prueban igual, y con
datos a mano, porque la alternativa es escribir la logica dos veces: una ahora
sin probar y otra despues.

Las reglas que se fijan:

  1. **El orden de las tres operaciones no es intercambiable**: prorratear,
     sumar el recargo, y recien al final aplicar el saldo a favor.
  2. **El saldo a favor no se sobregira**: el total a pagar nunca da negativo.
  3. **No hay recargo sobre el recargo.**
  4. **Con el recargo en cero, todo se comporta como si no existiera** — que
     es el estado de cualquier edificio que no configuro nada.
"""

from decimal import Decimal

import pytest

from app.services import expensas


def _unidades(cantidad: int) -> list[tuple[int, Decimal]]:
    """`cantidad` unidades con coeficientes que suman 100% exacto."""
    from app.services import finanzas

    coeficientes = finanzas.calcular_partes_iguales(cantidad)
    return [(i + 1, coeficiente) for i, coeficiente in enumerate(coeficientes)]


# ===========================================================================
# EL RECARGO
# ===========================================================================


def test_el_recargo_es_un_porcentaje_del_saldo_vencido():
    assert expensas.calcular_recargo(Decimal("100000.00"), Decimal("5.00")) == Decimal(
        "5000.00"
    )


def test_sin_recargo_configurado_el_recargo_es_cero():
    """El valor por defecto de todo edificio que no configuro nada."""
    assert expensas.calcular_recargo(Decimal("100000.00"), Decimal("0")) == Decimal(
        "0.00"
    )


def test_sin_deuda_vencida_no_hay_recargo():
    assert expensas.calcular_recargo(Decimal("0.00"), Decimal("5.00")) == Decimal(
        "0.00"
    )


def test_el_recargo_se_redondea_al_centavo_mas_cercano():
    """Redondeo comercial, el que espera cualquiera que haga la cuenta a mano.
    Truncar favoreceria siempre al mismo lado, y a lo largo de un ano eso es
    plata."""
    # 1,55% de 1000,33 = 15,505115 -> 15,51
    assert expensas.calcular_recargo(Decimal("1000.33"), Decimal("1.55")) == Decimal(
        "15.51"
    )


def test_el_recargo_siempre_tiene_dos_decimales():
    recargo = expensas.calcular_recargo(Decimal("1.00"), Decimal("1.00"))

    assert recargo.as_tuple().exponent == -2


# ===========================================================================
# LA LIQUIDACION COMPLETA
# ===========================================================================


def test_lo_prorrateado_cierra_exacto_contra_el_total():
    """La propiedad que importa: es la misma garantia de `F2-T03`, y tiene que
    seguir valiendo despues de pasar por el recargo y el saldo a favor."""
    partes = expensas.liquidar(Decimal("4849900.00"), _unidades(28))

    prorrateado = sum((p.monto_expensa for p in partes), Decimal("0.00"))
    assert prorrateado == Decimal("4849900.00")


def test_sin_mora_ni_saldo_a_favor_cada_unidad_paga_solo_su_parte():
    """El caso de hoy, y el de cualquier edificio al dia."""
    partes = expensas.liquidar(Decimal("1000.00"), _unidades(4))

    for parte in partes:
        assert parte.recargo_mora == Decimal("0.00")
        assert parte.saldo_a_favor_aplicado == Decimal("0.00")
        assert parte.total_a_pagar == parte.monto_expensa


def test_el_recargo_se_le_carga_solo_a_la_unidad_que_se_atraso():
    """**La regla de fondo.** Si el recargo entrara en el total a repartir, lo
    pagarian todos los vecinos, incluidos los que pagaron en fecha."""
    partes = expensas.liquidar(
        Decimal("1000.00"),
        _unidades(4),
        porcentaje_mora=Decimal("10.00"),
        vencido_por_unidad={2: Decimal("250.00")},
    )

    por_id = {p.departamento_id: p for p in partes}
    assert por_id[2].recargo_mora == Decimal("25.00")
    assert por_id[1].recargo_mora == Decimal("0.00")
    assert por_id[3].recargo_mora == Decimal("0.00")


def test_el_recargo_no_cambia_lo_prorrateado():
    """El total de la expensa son los gastos del periodo y nada mas: el
    recargo se suma despues, por unidad."""
    sin_mora = expensas.liquidar(Decimal("1000.00"), _unidades(4))
    con_mora = expensas.liquidar(
        Decimal("1000.00"),
        _unidades(4),
        porcentaje_mora=Decimal("10.00"),
        vencido_por_unidad={2: Decimal("250.00")},
    )

    assert [p.monto_expensa for p in sin_mora] == [p.monto_expensa for p in con_mora]


def test_el_saldo_a_favor_se_descuenta_de_lo_que_hay_que_pagar():
    partes = expensas.liquidar(
        Decimal("400.00"),
        _unidades(4),
        saldo_a_favor_por_unidad={1: Decimal("40.00")},
    )

    por_id = {p.departamento_id: p for p in partes}
    assert por_id[1].monto_expensa == Decimal("100.00")
    assert por_id[1].saldo_a_favor_aplicado == Decimal("40.00")
    assert por_id[1].total_a_pagar == Decimal("60.00")


def test_el_saldo_a_favor_no_se_sobregira():
    """**El caso que el usuario planteo:** alguien adelanto plata y la expensa
    subio. Se aplica lo que hay, el total da cero, y el excedente que no
    alcanzo NO se convierte en un saldo negativo."""
    partes = expensas.liquidar(
        Decimal("400.00"),
        _unidades(4),
        saldo_a_favor_por_unidad={1: Decimal("500.00")},
    )

    por_id = {p.departamento_id: p for p in partes}
    assert por_id[1].saldo_a_favor_aplicado == Decimal("100.00")
    assert por_id[1].total_a_pagar == Decimal("0.00")


def test_el_total_a_pagar_nunca_da_negativo():
    partes = expensas.liquidar(
        Decimal("400.00"),
        _unidades(4),
        saldo_a_favor_por_unidad={i: Decimal("99999.00") for i in range(1, 5)},
    )

    assert all(p.total_a_pagar >= 0 for p in partes)


def test_el_saldo_a_favor_se_aplica_despues_del_recargo():
    """**El orden importa y es una decision.** Si el saldo a favor se aplicara
    antes, estaria pagando el recargo con plata que el vecino adelanto para sus
    expensas, y el recargo quedaria cancelado sin que nadie decidiera
    perdonarlo. Aplicado despues, cubre el total —expensa mas recargo— y lo
    que sobra queda para el mes siguiente.
    """
    partes = expensas.liquidar(
        Decimal("400.00"),
        _unidades(4),
        porcentaje_mora=Decimal("10.00"),
        vencido_por_unidad={1: Decimal("200.00")},
        saldo_a_favor_por_unidad={1: Decimal("1000.00")},
    )

    por_id = {p.departamento_id: p for p in partes}
    # Expensa 100,00 + recargo 20,00 = 120,00: se aplican 120,00, no 100,00.
    assert por_id[1].recargo_mora == Decimal("20.00")
    assert por_id[1].saldo_a_favor_aplicado == Decimal("120.00")
    assert por_id[1].total_a_pagar == Decimal("0.00")


def test_no_hay_recargo_sobre_el_recargo():
    """El recargo se calcula sobre el capital atrasado que se le pasa, y nada
    mas. Con interes compuesto una deuda chica se multiplica sola y el numero
    deja de tener relacion con lo que se debe.
    """
    primero = expensas.liquidar(
        Decimal("400.00"),
        _unidades(4),
        porcentaje_mora=Decimal("10.00"),
        vencido_por_unidad={1: Decimal("100.00")},
    )
    por_id = {p.departamento_id: p for p in primero}

    # El mes siguiente, el vencido sigue siendo el capital: 100. El recargo del
    # mes anterior no se suma a la base del nuevo recargo.
    assert por_id[1].recargo_mora == Decimal("10.00")

    segundo = expensas.liquidar(
        Decimal("400.00"),
        _unidades(4),
        porcentaje_mora=Decimal("10.00"),
        vencido_por_unidad={1: Decimal("100.00")},
    )
    assert segundo[0].recargo_mora == Decimal("10.00")


def test_el_orden_de_salida_es_el_de_entrada():
    """El endpoint empareja las partes con las unidades por posicion."""
    unidades = [
        (7, Decimal("50.000")),
        (3, Decimal("30.000")),
        (9, Decimal("20.000")),
    ]

    partes = expensas.liquidar(Decimal("1000.00"), unidades)

    assert [p.departamento_id for p in partes] == [7, 3, 9]
    assert [p.monto_expensa for p in partes] == [
        Decimal("500.00"),
        Decimal("300.00"),
        Decimal("200.00"),
    ]


def test_el_coeficiente_viaja_en_la_parte_para_quedar_copiado():
    """Es lo que despues se guarda congelado en la liquidacion."""
    partes = expensas.liquidar(Decimal("1000.00"), [(1, Decimal("100.000"))])

    assert partes[0].coeficiente == Decimal("100.000")


def test_dos_corridas_dan_lo_mismo():
    unidades = _unidades(28)
    datos = dict(
        porcentaje_mora=Decimal("5.00"),
        vencido_por_unidad={3: Decimal("1000.00"), 7: Decimal("500.00")},
        saldo_a_favor_por_unidad={1: Decimal("200.00")},
    )

    primera = expensas.liquidar(Decimal("987654.32"), unidades, **datos)
    segunda = expensas.liquidar(Decimal("987654.32"), unidades, **datos)

    assert primera == segunda


def test_una_unidad_exenta_no_paga_expensa_pero_si_puede_tener_recargo():
    """Coeficiente 0%: no participa de los gastos. Pero si quedo debiendo de
    antes, ese atraso sigue siendo suyo."""
    partes = expensas.liquidar(
        Decimal("1000.00"),
        [(1, Decimal("0.000")), (2, Decimal("100.000"))],
        porcentaje_mora=Decimal("10.00"),
        vencido_por_unidad={1: Decimal("500.00")},
    )

    assert partes[0].monto_expensa == Decimal("0.00")
    assert partes[0].recargo_mora == Decimal("50.00")
    assert partes[0].total_a_pagar == Decimal("50.00")


def test_un_saldo_a_favor_negativo_se_rechaza():
    """Un saldo a favor negativo no es un saldo a favor: es deuda, y pasarlo
    por este camino la convertiria en un descuento."""
    with pytest.raises(ValueError):
        expensas.liquidar(
            Decimal("400.00"),
            _unidades(4),
            saldo_a_favor_por_unidad={1: Decimal("-100.00")},
        )


def test_no_liquida_si_los_coeficientes_no_suman_cien():
    """Hereda la garantia del prorrateo: con 99,9% el consorcio reparte menos
    de lo que gasto y la diferencia no la paga nadie."""
    with pytest.raises(ValueError):
        expensas.liquidar(
            Decimal("1000.00"), [(1, Decimal("50.000")), (2, Decimal("49.000"))]
        )

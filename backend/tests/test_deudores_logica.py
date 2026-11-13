"""Pruebas del calculo de deuda y atraso — logica pura (`F2-T11`).

Cuatro reglas, y cada una decide plata o color:

  1. **La deuda del mes corriente no es atraso** hasta pasado el vencimiento,
     y el dia del vencimiento todavia no cuenta.
  2. **Los meses de atraso se cuentan por periodos impagos**, no por
     calendario.
  3. **La base de un recargo nuevo es el capital, no el saldo** — si fuera el
     saldo habria recargo sobre el recargo.
  4. **Un mes amarillo, mas de uno rojo**, y lo decide el backend.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.services import deudores
from app.services.pagos import PeriodoDeCuenta


def _periodo(
    anio=2026,
    mes=11,
    total="50000.00",
    pagado="0.00",
    capital=None,
    recargo="0.00",
    vence_el=None,
) -> PeriodoDeCuenta:
    return PeriodoDeCuenta(
        expensa_id=anio * 100 + mes,
        anio=anio,
        mes=mes,
        total_a_pagar=Decimal(total),
        pagado_confirmado=Decimal(pagado),
        pendiente_de_confirmar=Decimal("0.00"),
        monto_expensa=Decimal(capital if capital is not None else total),
        recargo_mora=Decimal(recargo),
        vence_el=vence_el,
    )


# ===========================================================================
# EL VENCIMIENTO
# ===========================================================================


def test_el_vencimiento_se_cuenta_desde_la_publicacion():
    """Y no desde el fin del periodo liquidado: es desde la publicacion que el
    residente puede pagar. Si se liquida noviembre el 20 de diciembre, los diez
    dias corren desde el 20."""
    vence = deudores.fecha_de_vencimiento(datetime(2026, 12, 20, 9, 0), 10)

    assert vence == date(2026, 12, 30)


def test_una_expensa_en_borrador_no_vence():
    """El vecino no tuvo forma de pagarla."""
    assert deudores.fecha_de_vencimiento(None, 10) is None
    assert not deudores.esta_vencida(None)


def test_el_dia_del_vencimiento_todavia_no_es_atraso():
    """Pagar el ultimo dia del plazo es pagar en termino. La comparacion
    estricta es lo que evita marcar en rojo a quien pago el mismo dia."""
    vence = date(2026, 12, 10)

    assert not deudores.esta_vencida(vence, hoy=date(2026, 12, 10))
    assert deudores.esta_vencida(vence, hoy=date(2026, 12, 11))


def test_antes_del_vencimiento_no_hay_atraso():
    assert not deudores.esta_vencida(date(2026, 12, 10), hoy=date(2026, 12, 1))


# ===========================================================================
# EL SEMAFORO
# ===========================================================================


def test_sin_atraso_esta_al_dia():
    assert deudores.severidad(0) == deudores.AL_DIA


def test_un_mes_de_atraso_pinta_amarillo():
    assert deudores.severidad(1) == deudores.UN_MES


@pytest.mark.parametrize("meses", [2, 5, 12])
def test_mas_de_un_mes_pinta_rojo(meses):
    assert deudores.severidad(meses) == deudores.VARIOS_MESES


def test_los_nombres_son_los_del_sistema_de_diseno():
    """Es el mismo semaforo que pinta el edificio en la Fase 5, no una escala
    paralela. El naranja no participa: esta reservado para mantenimiento en
    curso."""
    assert (deudores.AL_DIA, deudores.UN_MES, deudores.VARIOS_MESES) == (
        "ok",
        "warn",
        "crit",
    )


# ===========================================================================
# ARMAR EL DEUDOR
# ===========================================================================


def test_una_unidad_al_dia_no_debe_nada():
    deudor = deudores.armar_deudor(
        1, "1A", [_periodo(pagado="50000.00", vence_el=date(2026, 12, 1))]
    )

    assert deudor.saldo == Decimal("0.00")
    assert not deudor.debe
    assert deudor.meses_de_atraso == 0
    assert deudor.severidad == deudores.AL_DIA


def test_una_deuda_en_termino_se_cobra_pero_no_es_atraso(cliente=None):
    """**La regla que importa.** La unidad debe y hay que cobrarle, pero no
    esta atrasada: el vencimiento no llego. No pinta nada en el Dashboard."""
    deudor = deudores.armar_deudor(
        1, "1A", [_periodo(vence_el=date(2026, 12, 20))], hoy=date(2026, 12, 5)
    )

    assert deudor.saldo == Decimal("50000.00")
    assert deudor.debe
    assert deudor.vencido == Decimal("0.00")
    assert deudor.meses_de_atraso == 0
    assert deudor.severidad == deudores.AL_DIA


def test_pasado_el_vencimiento_la_misma_deuda_pasa_a_ser_atraso():
    """**La misma deuda cambia de categoria sola, con el paso de los dias, sin
    que nadie toque nada.** Es exactamente la razon por la que deudores no
    puede ser una tabla."""
    periodos = [_periodo(vence_el=date(2026, 12, 20))]

    antes = deudores.armar_deudor(1, "1A", periodos, hoy=date(2026, 12, 5))
    despues = deudores.armar_deudor(1, "1A", periodos, hoy=date(2026, 12, 21))

    assert antes.meses_de_atraso == 0
    assert despues.meses_de_atraso == 1
    assert despues.severidad == deudores.UN_MES


def test_los_meses_de_atraso_se_cuentan_por_periodos_impagos():
    """**No por calendario.** Una unidad que debe marzo y mayo y pago abril
    tiene dos meses de atraso; el calendario diria tres."""
    deudor = deudores.armar_deudor(
        1,
        "1A",
        [
            _periodo(mes=3, vence_el=date(2026, 4, 10)),
            _periodo(mes=4, pagado="50000.00", vence_el=date(2026, 5, 10)),
            _periodo(mes=5, vence_el=date(2026, 6, 10)),
        ],
        hoy=date(2026, 12, 1),
    )

    assert deudor.meses_de_atraso == 2
    assert deudor.periodos_impagos == ("03/2026", "05/2026")
    assert deudor.severidad == deudores.VARIOS_MESES


def test_el_periodo_mas_viejo_es_el_mas_viejo_sin_importar_el_orden_de_entrada():
    """La pantalla de cobranza lo muestra como "debe desde"."""
    deudor = deudores.armar_deudor(
        1,
        "1A",
        [
            _periodo(mes=11, vence_el=date(2026, 12, 10)),
            _periodo(mes=3, vence_el=date(2026, 4, 10)),
            _periodo(mes=7, vence_el=date(2026, 8, 10)),
        ],
        hoy=date(2027, 1, 1),
    )

    assert deudor.periodo_mas_viejo == "03/2026"


def test_un_pago_parcial_deja_el_resto_como_deuda():
    deudor = deudores.armar_deudor(
        1,
        "1A",
        [_periodo(total="50000.00", pagado="20000.00", vence_el=date(2026, 12, 10))],
        hoy=date(2026, 12, 20),
    )

    assert deudor.saldo == Decimal("30000.00")
    assert deudor.meses_de_atraso == 1


def test_un_periodo_pagado_de_mas_no_cuenta_como_deuda():
    """Su saldo es negativo: es saldo a favor, y eso lo informa el estado de
    cuenta, no esta vista."""
    deudor = deudores.armar_deudor(
        1,
        "1A",
        [_periodo(total="50000.00", pagado="80000.00", vence_el=date(2026, 12, 10))],
        hoy=date(2026, 12, 20),
    )

    assert deudor.saldo == Decimal("0.00")
    assert not deudor.debe


# ===========================================================================
# LA BASE DEL RECARGO: CAPITAL Y NO SALDO
# ===========================================================================


def test_la_base_del_recargo_excluye_el_recargo_ya_cargado():
    """**La regla que evita que una deuda chica se multiplique sola.** El saldo
    de un periodo impago incluye el recargo que ya se le cargó; calcular el
    recargo nuevo sobre ese saldo seria cobrar recargo sobre el recargo.
    """
    # Capital 50.000 + recargo 5.000 = 55.000 a pagar, nada pagado.
    deudor = deudores.armar_deudor(
        1,
        "1A",
        [
            _periodo(
                total="55000.00",
                capital="50000.00",
                recargo="5000.00",
                vence_el=date(2026, 12, 10),
            )
        ],
        hoy=date(2026, 12, 20),
    )

    assert deudor.saldo == Decimal("55000.00")
    assert deudor.vencido == Decimal("55000.00")
    assert deudor.capital_vencido == Decimal("50000.00")


def test_los_pagos_se_imputan_primero_al_recargo():
    """Es la regla habitual del rubro (intereses primero) y la que hace que la
    cuenta cierre: mientras el capital no se pague, sigue generando recargo.
    """
    periodo = _periodo(
        total="55000.00",
        capital="50000.00",
        recargo="5000.00",
        pagado="5000.00",
        vence_el=date(2026, 12, 10),
    )

    # Los 5.000 pagados cubren el recargo, asi que el capital sigue entero.
    assert periodo.capital_impago == Decimal("50000.00")


def test_pagar_mas_que_el_recargo_empieza_a_bajar_el_capital():
    periodo = _periodo(
        total="55000.00",
        capital="50000.00",
        recargo="5000.00",
        pagado="25000.00",
        vence_el=date(2026, 12, 10),
    )

    assert periodo.capital_impago == Decimal("30000.00")


def test_el_capital_impago_nunca_es_negativo():
    periodo = _periodo(
        total="55000.00",
        capital="50000.00",
        recargo="5000.00",
        pagado="99999.00",
        vence_el=date(2026, 12, 10),
    )

    assert periodo.capital_impago == Decimal("0.00")


# ===========================================================================
# EL ORDEN
# ===========================================================================


def test_el_orden_es_de_mas_a_menos_atrasada():
    """Es el orden de una pantalla de cobranza: lo primero que hay que atender
    es la unidad que debe desde hace mas tiempo."""
    uno_solo = deudores.armar_deudor(
        1, "1A", [_periodo(mes=11, vence_el=date(2026, 12, 1))], hoy=date(2027, 1, 1)
    )
    tres = deudores.armar_deudor(
        2,
        "1B",
        [
            _periodo(mes=8, vence_el=date(2026, 9, 1)),
            _periodo(mes=9, vence_el=date(2026, 10, 1)),
            _periodo(mes=10, vence_el=date(2026, 11, 1)),
        ],
        hoy=date(2027, 1, 1),
    )

    assert [d.identificador for d in deudores.ordenar([uno_solo, tres])] == ["1B", "1A"]


def test_a_igual_atraso_primero_la_que_debe_mas():
    chica = deudores.armar_deudor(
        1,
        "1A",
        [_periodo(mes=11, total="1000.00", vence_el=date(2026, 12, 1))],
        hoy=date(2027, 1, 1),
    )
    grande = deudores.armar_deudor(
        2,
        "1B",
        [_periodo(mes=11, total="90000.00", vence_el=date(2026, 12, 1))],
        hoy=date(2027, 1, 1),
    )

    assert [d.identificador for d in deudores.ordenar([chica, grande])] == ["1B", "1A"]


def test_el_orden_es_estable_entre_dos_consultas_identicas():
    """Sin el desempate por identificador, dos unidades con el mismo atraso y el
    mismo saldo podrian alternarse entre dos consultas."""
    iguales = [
        deudores.armar_deudor(
            i,
            f"1{letra}",
            [_periodo(mes=11, vence_el=date(2026, 12, 1))],
            hoy=date(2027, 1, 1),
        )
        for i, letra in enumerate("CAB", start=1)
    ]

    primera = [d.identificador for d in deudores.ordenar(iguales)]
    segunda = [d.identificador for d in deudores.ordenar(list(reversed(iguales)))]

    assert primera == segunda == ["1A", "1B", "1C"]

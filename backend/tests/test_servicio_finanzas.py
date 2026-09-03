"""Tests de services/finanzas.py — criterio de prorrateo.

Lógica pura (sin base de datos, sin HTTP), igual que ya se hizo con
services/edificios.py — se prueba antes de que exista ningún modelo
financiero real (próximas tareas de la Fase 2).
"""

import pytest

from app.services.finanzas import (
    calcular_partes_iguales,
    calcular_por_metros_cuadrados,
    prorratear_gasto,
    validar_coeficientes,
)


# ------------------------- validar_coeficientes -------------------------

def test_coeficientes_que_suman_100_son_validos():
    validar_coeficientes([50, 30, 20])  # no debe lanzar nada


def test_coeficientes_con_error_de_redondeo_minimo_son_validos():
    validar_coeficientes([33.34, 33.33, 33.33])  # suma 100.00 exacto


def test_coeficientes_que_no_suman_100_lanza_error():
    with pytest.raises(ValueError):
        validar_coeficientes([50, 30, 15])  # suma 95


def test_lista_vacia_de_coeficientes_lanza_error():
    with pytest.raises(ValueError):
        validar_coeficientes([])


# ------------------------- calcular_partes_iguales -------------------------

def test_partes_iguales_4_unidades():
    coeficientes = calcular_partes_iguales(4)
    assert coeficientes == [25.0, 25.0, 25.0, 25.0]
    assert sum(coeficientes) == 100.0


def test_partes_iguales_3_unidades_no_divide_exacto():
    # 100/3 = 33.333... — el resultado tiene que sumar EXACTO 100, no 99.99
    coeficientes = calcular_partes_iguales(3)
    assert sum(coeficientes) == 100.0
    assert coeficientes[0] == coeficientes[1] == 33.3333
    assert coeficientes[2] == 33.3334  # la última se lleva el resto exacto


def test_partes_iguales_una_sola_unidad():
    assert calcular_partes_iguales(1) == [100.0]


@pytest.mark.parametrize("cantidad", [0, -1])
def test_partes_iguales_cantidad_invalida_lanza_error(cantidad):
    with pytest.raises(ValueError):
        calcular_partes_iguales(cantidad)


# ------------------------- calcular_por_metros_cuadrados -------------------------

def test_por_metros_cuadrados_proporcional():
    # 3 unidades de 50/30/20 m² (100 m² en total) -> mismos porcentajes
    coeficientes = calcular_por_metros_cuadrados([50, 30, 20])
    assert coeficientes == [50.0, 30.0, 20.0]
    assert sum(coeficientes) == 100.0


def test_por_metros_cuadrados_no_divide_exacto_suma_100():
    coeficientes = calcular_por_metros_cuadrados([33, 33, 34])
    assert sum(coeficientes) == 100.0


def test_por_metros_cuadrados_lista_vacia_lanza_error():
    with pytest.raises(ValueError):
        calcular_por_metros_cuadrados([])


@pytest.mark.parametrize("metros", [[50, 0, 20], [50, -10, 20]])
def test_por_metros_cuadrados_con_alguna_unidad_sin_dato_lanza_error(metros):
    # una sola unidad sin m² invalida el cálculo para TODO el edificio,
    # no solo para esa unidad — el prorrateo tiene que ser todo o nada
    with pytest.raises(ValueError):
        calcular_por_metros_cuadrados(metros)


# ------------------------- prorratear_gasto -------------------------

def test_prorratear_caso_tipico():
    montos = prorratear_gasto(100_000, [50, 30, 20])
    assert montos == [50_000, 30_000, 20_000]
    assert sum(montos) == 100_000


def test_prorratear_no_pierde_centavos_por_redondeo():
    # 3 unidades con coeficientes que no dividen exacto ($100 entre tres
    # partes de 33.33...%) -- el error clásico de repartir dinero: si cada
    # parte se redondea por separado puede faltar o sobrar 1 centavo.
    coeficientes = calcular_partes_iguales(3)  # [33.33, 33.33, 33.34]
    montos = prorratear_gasto(100.00, coeficientes)
    assert sum(montos) == 100.00
    assert len(montos) == 3


def test_prorratear_con_coeficientes_invalidos_lanza_error():
    with pytest.raises(ValueError):
        prorratear_gasto(100_000, [50, 30, 15])  # suma 95, no 100


def test_prorratear_monto_con_muchos_decimales_reconciliados():
    # caso realista: expensa de $157.432,87 repartida entre 7 unidades
    # con coeficientes irregulares (7 unidades a mano, no partes iguales)
    coeficientes = [18.5, 16.2, 14.8, 13.1, 12.9, 12.7, 11.8]
    montos = prorratear_gasto(157_432.87, coeficientes)
    assert round(sum(montos), 2) == 157_432.87

"""Tests de services/edificios.py — generación de estructura vacía.

Lógica pura (sin base de datos, sin HTTP), igual que ya se hizo con
services/autorizacion.py — se prueba antes de que exista el modelo
`Edificio` real (próxima tarea).
"""

import pytest

from app.services.edificios import MAXIMO_UNIDADES_POR_PISO, generar_estructura_vacia


def test_caso_tipico_3_pisos_4_unidades():
    estructura = generar_estructura_vacia(cantidad_pisos=3, unidades_por_piso=4)

    assert len(estructura) == 3
    assert [p["numero"] for p in estructura] == [1, 2, 3]
    assert estructura[0]["departamentos"] == ["1A", "1B", "1C", "1D"]
    assert estructura[2]["departamentos"] == ["3A", "3B", "3C", "3D"]


def test_coincide_con_la_convencion_del_mockup_aprobado():
    # El mockup (Mockup_3D_Vidrio_Grafito.html) usa 7 pisos de 4 unidades,
    # con departamentos "7A".."7D" en el piso más alto.
    estructura = generar_estructura_vacia(cantidad_pisos=7, unidades_por_piso=4)
    assert estructura[-1]["numero"] == 7
    assert estructura[-1]["departamentos"] == ["7A", "7B", "7C", "7D"]


def test_un_piso_una_unidad():
    estructura = generar_estructura_vacia(cantidad_pisos=1, unidades_por_piso=1)
    assert estructura == [{"numero": 1, "departamentos": ["1A"]}]


def test_maximo_de_26_unidades_por_piso_usa_hasta_la_z():
    estructura = generar_estructura_vacia(cantidad_pisos=1, unidades_por_piso=MAXIMO_UNIDADES_POR_PISO)
    assert estructura[0]["departamentos"][-1] == "1Z"
    assert len(estructura[0]["departamentos"]) == 26


@pytest.mark.parametrize("cantidad_pisos", [0, -1])
def test_cantidad_de_pisos_invalida_lanza_error(cantidad_pisos):
    with pytest.raises(ValueError):
        generar_estructura_vacia(cantidad_pisos=cantidad_pisos, unidades_por_piso=4)


@pytest.mark.parametrize("unidades_por_piso", [0, -1])
def test_unidades_por_piso_invalidas_lanza_error(unidades_por_piso):
    with pytest.raises(ValueError):
        generar_estructura_vacia(cantidad_pisos=3, unidades_por_piso=unidades_por_piso)


def test_mas_de_26_unidades_por_piso_lanza_error():
    with pytest.raises(ValueError):
        generar_estructura_vacia(cantidad_pisos=1, unidades_por_piso=MAXIMO_UNIDADES_POR_PISO + 1)

"""Tests de services/reclamos.py — flujo de estados y prioridad.

Lógica pura (sin base de datos, sin HTTP), igual que ya se hizo con
services/edificios.py y services/finanzas.py — se prueba antes de que
exista ningún modelo de Reclamo real (próxima tarea de esta fase).
"""

import pytest

from app.services.reclamos import (
    ESTADOS,
    PRIORIDADES,
    color_por_prioridad,
    transicion_valida,
)


# ------------------------------- transicion_valida -------------------------------

def test_flujo_lineal_normal_es_valido():
    assert transicion_valida("recibido", "asignado")
    assert transicion_valida("asignado", "en_curso")
    assert transicion_valida("en_curso", "resuelto")
    assert transicion_valida("resuelto", "cerrado")


def test_no_se_puede_saltear_estados():
    assert not transicion_valida("recibido", "en_curso")
    assert not transicion_valida("recibido", "resuelto")
    assert not transicion_valida("asignado", "cerrado")


def test_no_se_puede_retroceder_el_flujo_normal():
    assert not transicion_valida("en_curso", "asignado")
    assert not transicion_valida("asignado", "recibido")


def test_resuelto_puede_volver_a_en_curso():
    # Excepción real al flujo lineal: quien reclamó confirma que el
    # problema sigue — se reabre el mismo reclamo en vez de perder su
    # historial de comentarios/fotos cargando uno nuevo.
    assert transicion_valida("resuelto", "en_curso")


def test_cerrado_es_terminal():
    # La recurrencia se resuelve con un reclamo NUEVO (Documento General
    # 11.5), nunca reabriendo uno ya cerrado.
    for estado in ESTADOS:
        assert not transicion_valida("cerrado", estado)


def test_estado_desconocido_no_lanza_solo_es_invalido():
    assert not transicion_valida("inventado", "recibido")
    assert not transicion_valida("recibido", "inventado")


# ------------------------------- color_por_prioridad -------------------------------

def test_leve_y_medio_pintan_amarillo():
    assert color_por_prioridad("leve") == "warn"
    assert color_por_prioridad("medio") == "warn"


def test_critico_pinta_rojo():
    assert color_por_prioridad("critico") == "crit"


def test_prioridad_invalida_lanza_error():
    with pytest.raises(ValueError):
        color_por_prioridad("urgente")


def test_todas_las_prioridades_tienen_color_valido():
    for prioridad in PRIORIDADES:
        assert color_por_prioridad(prioridad) in ("warn", "crit")

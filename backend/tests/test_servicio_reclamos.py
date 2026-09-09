"""Tests de services/reclamos.py — flujo de estados y prioridad.

Lógica pura (sin base de datos, sin HTTP), igual que ya se hizo con
services/edificios.py y services/finanzas.py — se prueba antes de que
exista ningún modelo de Reclamo real (próxima tarea de esta fase).
"""

import pytest

from app.services.reclamos import (
    ESTADOS,
    ESTADOS_OT,
    PRIORIDADES,
    TIPOS_OT,
    color_por_prioridad,
    transicion_valida,
    transicion_valida_ot,
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


# --------------------------- transicion_valida_ot (Orden de Trabajo) ---------------------------

def test_flujo_de_ot_es_lineal_y_valido():
    assert transicion_valida_ot("pendiente", "en_curso")
    assert transicion_valida_ot("en_curso", "resuelta")


def test_ot_no_puede_saltear_pendiente_a_resuelta():
    assert not transicion_valida_ot("pendiente", "resuelta")


def test_ot_no_retrocede_nunca():
    # A diferencia de Reclamo, la OT no tiene ninguna excepción de
    # reapertura — es un registro de ejecución, no un hilo de seguimiento.
    assert not transicion_valida_ot("en_curso", "pendiente")
    assert not transicion_valida_ot("resuelta", "en_curso")


def test_ot_resuelta_es_terminal():
    for estado in ESTADOS_OT:
        assert not transicion_valida_ot("resuelta", estado)


def test_flujo_de_ot_es_distinto_del_de_reclamo():
    # No comparten tabla de transiciones — "asignado" existe para
    # Reclamo pero no tiene sentido en el flujo de OT.
    assert "asignado" not in ESTADOS_OT
    assert "cerrado" not in ESTADOS_OT
    assert set(ESTADOS_OT) == {"pendiente", "en_curso", "resuelta"}


def test_tipos_de_ot_son_los_del_documento_general():
    assert set(TIPOS_OT) == {"preventivo", "correctivo", "programado", "emergencia"}

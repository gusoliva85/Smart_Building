"""Tests de services/reclamos.py — flujo de estados y prioridad.

Lógica pura (sin base de datos, sin HTTP), igual que ya se hizo con
services/edificios.py y services/finanzas.py — se prueba antes de que
exista ningún modelo de Reclamo real (próxima tarea de esta fase).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from app.services.reclamos import (
    ESTADOS,
    ESTADOS_OT,
    PRIORIDADES,
    TIPOS_OT,
    color_por_prioridad,
    tiempo_resolucion_ot,
    tiempo_resolucion_reclamo,
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


# --------------------------- tiempo_resolucion_* ---------------------------

@dataclass
class _ObjetoConFechas:
    """Duck typing puro — ni `tiempo_resolucion_reclamo()` ni
    `tiempo_resolucion_ot()` importan modelos reales, así que alcanza con
    cualquier objeto con los atributos que leen."""

    creado_en: datetime
    cerrado_en: datetime | None = None
    fecha_cierre: datetime | None = None


def test_tiempo_resolucion_reclamo_none_mientras_sigue_abierto():
    reclamo = _ObjetoConFechas(creado_en=datetime.now(timezone.utc))
    assert tiempo_resolucion_reclamo(reclamo) is None


def test_tiempo_resolucion_reclamo_calcula_desde_cerrado_en():
    inicio = datetime(2026, 1, 1, tzinfo=timezone.utc)
    reclamo = _ObjetoConFechas(creado_en=inicio, cerrado_en=inicio + timedelta(hours=5))
    assert tiempo_resolucion_reclamo(reclamo) == timedelta(hours=5)


def test_tiempo_resolucion_reclamo_ignora_resuelto_solo_mira_cerrado():
    # Un reclamo "resuelto" pero todavía no "cerrado" sigue sin tiempo de
    # resolución — 11.7 mide hasta el CIERRE, no hasta "resuelto" (que
    # todavía puede reabrirse).
    reclamo = _ObjetoConFechas(creado_en=datetime.now(timezone.utc), cerrado_en=None)
    assert tiempo_resolucion_reclamo(reclamo) is None


def test_tiempo_resolucion_ot_none_mientras_sigue_abierta():
    orden = _ObjetoConFechas(creado_en=datetime.now(timezone.utc))
    assert tiempo_resolucion_ot(orden) is None


def test_tiempo_resolucion_ot_calcula_desde_fecha_cierre():
    inicio = datetime(2026, 1, 1, tzinfo=timezone.utc)
    orden = _ObjetoConFechas(creado_en=inicio, fecha_cierre=inicio + timedelta(days=2))
    assert tiempo_resolucion_ot(orden) == timedelta(days=2)

"""Tests de services/severidad.py — "peor estado" por departamento.

Lógica pura (sin base de datos, sin HTTP), igual que el resto de los
servicios del proyecto — se prueba con objetos de juguete (duck typing:
solo hace falta `.prioridad`/.estado`, no un `Reclamo`/`OrdenTrabajo`
real)."""

from dataclasses import dataclass

from app.services.severidad import ESTADOS_SEVERIDAD, ot_severity, reclamo_severity


@dataclass
class _ReclamoDeJuguete:
    prioridad: str


@dataclass
class _OtDeJuguete:
    estado: str


# ------------------------------- reclamo_severity -------------------------------

def test_sin_reclamos_abiertos_es_ok():
    assert reclamo_severity([]) == "ok"


def test_un_reclamo_leve_es_warn():
    assert reclamo_severity([_ReclamoDeJuguete(prioridad="leve")]) == "warn"


def test_un_reclamo_medio_es_warn():
    assert reclamo_severity([_ReclamoDeJuguete(prioridad="medio")]) == "warn"


def test_un_reclamo_critico_es_crit():
    assert reclamo_severity([_ReclamoDeJuguete(prioridad="critico")]) == "crit"


def test_critico_gana_aunque_haya_otros_leves():
    reclamos = [_ReclamoDeJuguete(prioridad="leve"), _ReclamoDeJuguete(prioridad="critico"), _ReclamoDeJuguete(prioridad="medio")]
    assert reclamo_severity(reclamos) == "crit"


def test_reclamo_severity_acepta_un_generador_no_solo_una_lista():
    generador = (r for r in [_ReclamoDeJuguete(prioridad="medio")])
    assert reclamo_severity(generador) == "warn"


# ------------------------------- ot_severity -------------------------------

def test_sin_ordenes_de_trabajo_es_ok():
    assert ot_severity([]) == "ok"


def test_ot_pendiente_sola_no_alcanza_todavia_es_ok():
    # Documento Técnico sección 12: "pendiente" no dispara el naranja,
    # solo "en_curso" lo hace.
    assert ot_severity([_OtDeJuguete(estado="pendiente")]) == "ok"


def test_ot_en_curso_es_pend():
    assert ot_severity([_OtDeJuguete(estado="en_curso")]) == "pend"


def test_ot_resuelta_sola_no_cuenta():
    assert ot_severity([_OtDeJuguete(estado="resuelta")]) == "ok"


def test_una_en_curso_entre_varias_alcanza():
    ordenes = [_OtDeJuguete(estado="pendiente"), _OtDeJuguete(estado="en_curso"), _OtDeJuguete(estado="resuelta")]
    assert ot_severity(ordenes) == "pend"


def test_ot_severity_nunca_devuelve_warn_ni_crit():
    for estado in ("pendiente", "en_curso", "resuelta"):
        assert ot_severity([_OtDeJuguete(estado=estado)]) in ("ok", "pend")


def test_ot_severity_acepta_un_generador_no_solo_una_lista():
    generador = (o for o in [_OtDeJuguete(estado="en_curso")])
    assert ot_severity(generador) == "pend"


# ------------------------------- valores válidos -------------------------------

def test_estados_de_severidad_son_los_cuatro_del_semaforo():
    assert ESTADOS_SEVERIDAD == ("ok", "warn", "pend", "crit")

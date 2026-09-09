"""Lógica del flujo de reclamos — Documento General, sección 11.4 (flujo de
estados) y 11.3 (prioridad); Documento Técnico, sección 13. También el
flujo (bien más simple, y DISTINTO) de las órdenes de trabajo — Documento
General 10.2, Documento Técnico sección 12 — porque los dos dominios se
implementan juntos en esta misma fase (un reclamo puede generar una OT) y
comparten archivo de lógica, no porque sean el mismo flujo.

Se fija ANTES de modelar `Reclamo`/`ReclamoComentario`/`OrdenTrabajo` —
mismo criterio que el resto del proyecto (roles en Fase 1, prorrateo en
Fase 2): la regla de negocio se define y prueba en Python puro antes de
tocar la base, para no terminar con la validación de transiciones
repartida a mano en cada endpoint que cambie un estado.
"""

PRIORIDADES = ("leve", "medio", "critico")

ESTADOS = ("recibido", "asignado", "en_curso", "resuelto", "cerrado")

# Flujo lineal normal (Documento General 11.4: "recibido → asignado → en
# curso → resuelto → cerrado") + UNA excepción real que ese flujo lineal
# no contempla: un reclamo dado por "resuelto" puede volver a "en_curso"
# si quien lo reportó confirma que el problema sigue. Sin esto, la única
# forma de corregir un cierre prematuro sería cargar un reclamo nuevo,
# perdiendo el historial de comentarios/fotos del original — decisión de
# diseño de esta tarea, documentada acá porque el enunciado no la fija
# explícitamente.
#
# "cerrado" es SIEMPRE terminal a propósito: la sección 11.5 del
# Documento General ya resuelve la recurrencia de otra forma ("la misma
# pérdida de agua reportada tres veces... es una señal de que la
# reparación anterior no fue efectiva") — el antecedente tiene que quedar
# archivado tal cual se cerró, un problema que vuelve es un reclamo
# NUEVO, no la reapertura del viejo.
TRANSICIONES_VALIDAS = {
    "recibido": ("asignado",),
    "asignado": ("en_curso",),
    "en_curso": ("resuelto",),
    "resuelto": ("cerrado", "en_curso"),
    "cerrado": (),
}


def transicion_valida(estado_actual: str, estado_nuevo: str) -> bool:
    """`False` también si alguno de los dos estados no existe — nunca
    lanza para un estado desconocido, lo trata simplemente como una
    transición inválida (el endpoint que la use decide qué error dar)."""
    return estado_nuevo in TRANSICIONES_VALIDAS.get(estado_actual, ())


def color_por_prioridad(prioridad: str) -> str:
    """Documento Técnico, sección 13: leve/medio pintan amarillo, crítico
    pinta rojo — mismos códigos que el resto del semáforo del proyecto
    (`--warn`/`--crit`, `premium-uiux`). Leve y medio nunca se distinguen
    en color, solo en la urgencia percibida dentro del propio reclamo."""
    if prioridad not in PRIORIDADES:
        raise ValueError(f"Prioridad inválida: {prioridad!r}. Válidas: {PRIORIDADES}")
    return "crit" if prioridad == "critico" else "warn"


# ------------------------------------------------------------------
# Órdenes de trabajo — Documento General 10.1 (tipos) y 10.2 (estado).
# Flujo PROPIO, deliberadamente más simple que el de Reclamo y sin
# ninguna excepción de reapertura: acá no hay "quien reportó" pidiendo
# reabrir, es un registro de ejecución — si el trabajo resulta
# incompleto, se genera una OT nueva, la vieja queda tal cual se cerró
# (mismo criterio de "el antecedente no se reescribe" que ya rige a
# Reclamo con su estado "cerrado").
# ------------------------------------------------------------------

TIPOS_OT = ("preventivo", "correctivo", "programado", "emergencia")

ESTADOS_OT = ("pendiente", "en_curso", "resuelta")

TRANSICIONES_VALIDAS_OT = {
    "pendiente": ("en_curso",),
    "en_curso": ("resuelta",),
    "resuelta": (),
}


def transicion_valida_ot(estado_actual: str, estado_nuevo: str) -> bool:
    """Misma forma que `transicion_valida()`, pero contra el flujo de OT
    — nunca se reutiliza `TRANSICIONES_VALIDAS` (la de `Reclamo`) para
    esto, son dos flujos distintos aunque compartan este archivo."""
    return estado_nuevo in TRANSICIONES_VALIDAS_OT.get(estado_actual, ())

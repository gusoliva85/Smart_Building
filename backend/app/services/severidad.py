"""Servicio de "peor estado" (severidad) por departamento — Documento
Técnico, sección 1.2.1, y su referencia visual en la skill `premium-uiux`
(`references/componentes.md`, "Motor de datos (JS), independiente de la
piel visual"): `reclamoSeverity()`/`otSeverity()` ahí son la REGLA de
negocio, escritas en JS solo como referencia rápida para el mockup — el
propio archivo lo aclara ("el motor de arriba es solo la referencia de
la REGLA, no el lugar donde vive en producción"). Acá es donde vive de
verdad: un servicio Python puro (sin tocar la base), que el Dashboard
Visual (Fase 5) va a consumir por HTTP — nunca se recalcula esto en el
frontend con datos reales.

Los nombres acá son `snake_case` (`reclamo_severity`/`ot_severity`), no
los `camelCase` del JS de referencia — mismo criterio que el resto del
proyecto (Python siempre `snake_case`), la skill solo fija la REGLA, no
el símbolo exacto.

Alcance de esta tarea (Fase 3, "reclamos y mantenimiento"): solo
`reclamo_severity()`/`ot_severity()` — las dos reglas que dependen de
este dominio. `deuda_severity()` (financiero, ya tiene su propio cálculo
de morosidad en `services/finanzas.py`) y `severidad_maxima()` +
"severidad según la vista" (que combinan las tres con la regla de
precedencia ok < warn < pend < crit) son tarea de la Fase 5, cuando el
Dashboard Visual arma la respuesta completa por departamento.

Primer módulo con lógica de cálculo no trivial fuera de flujos de
estado — Documento Técnico, sección 20 pide test con pytest en la misma
tarea que lo introduce, ver `test_servicio_severidad.py`.
"""

ESTADOS_SEVERIDAD = ("ok", "warn", "pend", "crit")


def reclamo_severity(reclamos) -> str:
    """`reclamos`: los reclamos ABIERTOS (no `resuelto`/`cerrado`) de una
    unidad — filtrar por estado es responsabilidad de quien arma esta
    lista (Fase 5, consultando la base); acá solo se mira la prioridad,
    mismo criterio que `reclamoSeverity()` del mockup. Al menos un
    reclamo crítico → `'crit'`; ninguno crítico pero hay al menos uno →
    `'warn'`; sin reclamos abiertos → `'ok'`."""
    reclamos = list(reclamos)
    if any(r.prioridad == "critico" for r in reclamos):
        return "crit"
    if reclamos:
        return "warn"
    return "ok"


def ot_severity(ordenes_trabajo) -> str:
    """`ordenes_trabajo`: las órdenes de trabajo de una unidad, en
    cualquier estado — a diferencia de `reclamo_severity()`, acá el
    filtro por estado SÍ es parte de la regla (Documento Técnico,
    sección 12: "pendiente → en curso (dispara naranja) → resuelta" —
    una OT todavía `pendiente`, sin arrancar, no cuenta). Nunca devuelve
    `'warn'`/`'crit'` — el naranja (`'pend'`) es exclusivo de
    mantenimiento en curso."""
    return "pend" if any(o.estado == "en_curso" for o in ordenes_trabajo) else "ok"

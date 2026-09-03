"""Lógica de prorrateo de gastos entre departamentos.

Documento General, sección 6.1. Validado contra la normativa real de
propiedad horizontal en Argentina (Ley 13.512 y su continuación en el
Código Civil y Comercial, arts. 2037 y siguientes) antes de escribir esta
lógica: cada unidad funcional tiene un **coeficiente** (%) fijo, registrado
en el reglamento de propiedad horizontal del edificio — NO un criterio
global recalculado en cada liquidación como "partes iguales" o "por m²".
Esos dos son solo atajos para completar el coeficiente la primera vez (al
dar de alta la estructura); el coeficiente en sí queda como el dato real,
editable a mano después desde la pantalla de Configuración (Administrador
General o el Administrador de Consorcio del edificio).

Fuera de alcance por ahora (decisión consultada con el usuario): un
criterio de distribución distinto por rubro dentro del mismo edificio (ej.
"el ascensor no lo paga planta baja") — real y contemplado por la ley vía
el reglamento, pero se deja para una tarea aparte que no rompa esta base.

Esta es la pieza más delicada del módulo financiero: un error acá afecta
a todos los propietarios a la vez. Por eso el prorrateo de un monto nunca
redondea cada parte por separado (eso puede dejar centavos de más o de
menos sin asignar) — la última unidad recibe el resto exacto, así la suma
de lo repartido da siempre igual al total original.
"""

TOLERANCIA_SUMA_COEFICIENTES = 0.01  # margen para redondeos de punta a punta, no para errores reales


def validar_coeficientes(coeficientes: list[float]) -> None:
    """Los coeficientes de todas las unidades de un edificio tienen que
    sumar 100% — si no suman eso, algo quedó mal cargado (una unidad sin
    coeficiente, uno duplicado, etc.) y prorratear igual sería repartir
    de más o de menos entre los propietarios reales."""
    if not coeficientes:
        raise ValueError("El edificio no tiene coeficientes cargados")
    suma = sum(coeficientes)
    if abs(suma - 100) > TOLERANCIA_SUMA_COEFICIENTES:
        raise ValueError(f"Los coeficientes suman {suma}%, tienen que sumar 100%")


def calcular_partes_iguales(cantidad_unidades: int) -> list[float]:
    """Atajo para completar el coeficiente la primera vez — reparte 100%
    en partes iguales. La última unidad recibe el resto exacto (no su
    parte redondeada) para que la suma dé justo 100, nunca una
    aproximación con error de redondeo."""
    if cantidad_unidades < 1:
        raise ValueError("cantidad_unidades tiene que ser al menos 1")
    parte = round(100 / cantidad_unidades, 4)
    coeficientes = [parte] * (cantidad_unidades - 1)
    coeficientes.append(round(100 - sum(coeficientes), 4))
    return coeficientes


def calcular_por_metros_cuadrados(metros_cuadrados: list[float]) -> list[float]:
    """Atajo: coeficiente proporcional a la superficie de cada unidad —
    requiere que TODAS las unidades tengan m² cargados, porque un
    coeficiente calculado con datos parciales sería incorrecto para
    todo el edificio, no solo para la unidad sin dato."""
    if not metros_cuadrados:
        raise ValueError("No hay unidades para calcular")
    if any(m2 <= 0 for m2 in metros_cuadrados):
        raise ValueError("Todas las unidades necesitan m² cargados y mayores a 0 para este atajo")
    total_m2 = sum(metros_cuadrados)
    coeficientes = [round(m2 / total_m2 * 100, 4) for m2 in metros_cuadrados[:-1]]
    coeficientes.append(round(100 - sum(coeficientes), 4))
    return coeficientes


def prorratear_gasto(monto_total: float, coeficientes: list[float]) -> list[float]:
    """Reparte monto_total entre las unidades según su coeficiente (%),
    en el mismo orden. Devuelve una lista de montos que SIEMPRE suma
    exactamente monto_total — la última unidad recibe el resto exacto en
    vez de su parte redondeada a centavos."""
    validar_coeficientes(coeficientes)
    montos = [round(monto_total * coeficiente / 100, 2) for coeficiente in coeficientes[:-1]]
    montos.append(round(monto_total - sum(montos), 2))
    return montos

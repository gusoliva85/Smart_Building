"""El catalogo de rubros de un gasto del consorcio (`F2-T01`).

============================================================================
POR QUE ESTO ES UN CATALOGO Y NO UN CAMPO DE TEXTO LIBRE
============================================================================

El Roadmap y el Documento Tecnico describian `gastos.rubro` como una columna
de texto, sin decir que valores admite. **Con texto libre, "Limpieza",
"limpieza" y "Limpieza " son tres rubros distintos**, y eso no es un problema
estetico: la apertura por rubro de la expensa (`F2-T04`) y los reportes de
evolucion por rubro (`F2-T16`, y la Analitica de la Fase 6) **agrupan por ese
valor**. Tres variantes del mismo rubro son tres lineas en la liquidacion que
ve el consorcista y tres series en el reporte.

Asi que el rubro es una regla del sistema, y en este proyecto una regla del
sistema es una estructura de datos y no texto suelto — el mismo razonamiento
que puso los permisos en una matriz y los tipos de cochera en una tupla. El
CHECK de la tabla se arma desde esta misma tupla, asi que la base y la
aplicacion no pueden quedar en desacuerdo.

============================================================================
NO CONFUNDIR CON LOS RUBROS DE UN PROVEEDOR
============================================================================

La Fase 7 crea una tabla `rubros` para el directorio de proveedores. **Es otro
concepto y por eso no se comparte:**

- El rubro de un **gasto** es una categoria contable: en que se fue la plata
  del consorcio este mes (sueldos, seguros, ascensores).
- El rubro de un **proveedor** es su oficio: plomeria, electricidad,
  cerrajeria.

Se parecen en algunos valores y no en otros —"seguros" o "impuestos" no son
oficios, y "cerrajeria" no es una linea de la liquidacion—, asi que unirlos
obligaria a que cada lista tuviera entradas que a la otra no le sirven. Cuando
la Fase 7 construya su tabla, la decision a tomar es si un proveedor sugiere un
rubro de gasto al cargar una factura; eso es un mapeo, no una tabla compartida.

============================================================================
QUE PASA CUANDO FALTA UN RUBRO
============================================================================

Existe `otros`, y existe para que nadie quede bloqueado sin poder cargar un
gasto real a las diez de la noche. Pero es una valvula de escape, no un cajon:
si en los reportes `otros` empieza a pesar, lo que falta es un rubro nuevo en
esta lista, no mas gastos ahi adentro.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rubro:
    """Un rubro de gasto: su nombre interno y como se lee en pantalla.

    `nombre` es lo que se guarda en la base y lo que agrupa los reportes; no
    cambia nunca. `etiqueta` es lo que lee una persona y se puede reescribir
    sin tocar un solo dato — la misma separacion que tienen los roles.
    """

    nombre: str
    etiqueta: str
    descripcion: str


# El orden es el de una liquidacion real, de lo que mas pesa a lo que menos, y
# es el orden en que se muestran: un desplegable alfabetico pondria
# "Administracion" primero y dejaria "Sueldos" —que es casi siempre el rubro
# mas grande de un consorcio— perdido en el medio.
CATALOGO: tuple[Rubro, ...] = (
    Rubro(
        "sueldos",
        "Sueldos y cargas sociales",
        "El encargado y el personal del edificio, con sus cargas.",
    ),
    Rubro(
        "servicios",
        "Servicios",
        "Luz, agua y gas de los espacios comunes.",
    ),
    Rubro(
        "limpieza",
        "Limpieza",
        "Servicio de limpieza y artículos.",
    ),
    Rubro(
        "mantenimiento",
        "Mantenimiento y reparaciones",
        "Arreglos generales del edificio que no son de un equipo con "
        "mantenimiento propio.",
    ),
    Rubro(
        "ascensores",
        "Ascensores",
        "Abono de mantenimiento y habilitación.",
    ),
    Rubro(
        "seguros",
        "Seguros",
        "Pólizas del consorcio.",
    ),
    Rubro(
        "administracion",
        "Administración",
        "Honorarios de la administración y gastos administrativos.",
    ),
    Rubro(
        "impuestos",
        "Impuestos y tasas",
        "Lo que paga el consorcio como tal.",
    ),
    Rubro(
        "bancarios",
        "Gastos bancarios",
        "Comisiones y mantenimiento de la cuenta del consorcio.",
    ),
    Rubro(
        "otros",
        "Otros",
        "Lo que no entra en ninguno de los anteriores. Si pesa en los "
        "reportes, falta un rubro en el catálogo.",
    ),
)

# Los nombres sueltos, que es lo que se compara y lo que se guarda.
RUBROS: tuple[str, ...] = tuple(rubro.nombre for rubro in CATALOGO)

OTROS = "otros"

_POR_NOMBRE: dict[str, Rubro] = {rubro.nombre: rubro for rubro in CATALOGO}


def es_rubro_valido(nombre: str) -> bool:
    """Si ese valor se puede guardar en la columna."""
    return nombre in _POR_NOMBRE


def obtener(nombre: str) -> Rubro:
    """El rubro completo, o un error que dice cuales son los validos.

    Revienta en vez de devolver `None` a proposito: un rubro invalido no tiene
    etiqueta ni descripcion, asi que seguir con el seria arrastrar un agujero
    hasta la pantalla.
    """
    rubro = _POR_NOMBRE.get(nombre)
    if rubro is None:
        raise ValueError(
            f"Rubro inválido: {nombre!r}. Los válidos son: {', '.join(RUBROS)}."
        )
    return rubro


def etiqueta(nombre: str) -> str:
    """Como se lee el rubro en pantalla."""
    return obtener(nombre).etiqueta

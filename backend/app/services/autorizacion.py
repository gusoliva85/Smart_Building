"""Matriz de roles y permisos — la fuente unica de verdad de la autorizacion.

Traduce la matriz del Documento Tecnico (seccion 4.2) a una **estructura de
datos**, no a condicionales repartidos por los routers. Toda pregunta sobre
permisos se responde consultando este modulo, y ningun endpoint decide por su
cuenta quien puede hacer que.

Por que importa que sea una estructura y no una serie de `if`:

  - La matriz se lee de un vistazo y se compara con la documentacion.
  - Agregar un rol o cambiar un permiso se hace en un solo lugar.
  - Los modelos declaran sus CheckConstraint contra `ROLES`, la misma lista que
    usa la autorizacion: la base y la aplicacion no pueden discrepar.

Este modulo es logica pura: no importa modelos, no toca la base y no sabe que
existe HTTP. Se prueba con pytest en milisegundos.
"""

from dataclasses import dataclass

# ---------------------------------------------------------------- alcances --

# Hasta donde llega un rol. Es la primera pregunta de toda autorizacion:
# antes de "¿puede ver montos?" viene "¿sobre que edificio o unidad?".
ALCANCE_CARTERA = "cartera"
"""Todos los edificios de la plataforma."""

ALCANCE_EDIFICIO = "edificio"
"""El edificio del que es responsable, resuelto por un vinculo real."""

ALCANCE_UNIDAD = "unidad"
"""Las unidades propias, y nada mas."""

ALCANCE_OTS_ASIGNADAS = "ots_asignadas"
"""Solo las ordenes de trabajo que le asignaron."""

ALCANCE_ASIGNADO = "asignado"
"""Los edificios que se le hayan asignado explicitamente.

Es el alcance del Auditor. El Documento General lo describe como "definido por
edificio o cartera": no es una constante del rol, se configura por usuario.

Se modela como un alcance propio, y no como cartera, a proposito: asi el valor
por defecto de un Auditor recien creado es **ningun edificio** hasta que se le
asigne uno. Darle la cartera entera por defecto seria el tipo de sobre-permiso
silencioso que conviene no tener. El mecanismo concreto del vinculo se decide
en `F1-T02`.
"""

ALCANCES = (
    ALCANCE_CARTERA,
    ALCANCE_EDIFICIO,
    ALCANCE_UNIDAD,
    ALCANCE_OTS_ASIGNADAS,
    ALCANCE_ASIGNADO,
)


# ------------------------------------------------------------------- roles --

ADMIN_GENERAL = "admin_general"
ADMIN_CONSORCIO = "admin_consorcio"
ENCARGADO = "encargado"
PROPIETARIO = "propietario"
INQUILINO = "inquilino"
PROVEEDOR = "proveedor"
AUDITOR = "auditor"
SEGURIDAD = "seguridad"


@dataclass(frozen=True)
class Rol:
    """Los permisos de un rol. Inmutable: nadie los modifica en caliente."""

    nombre: str
    etiqueta: str
    alcance: str
    ve_financiero_unidad: bool
    ve_financiero_edificio: bool
    solo_lectura: bool


# La matriz. Cualquier cambio de permisos se hace aca y en ningun otro lugar.
#
# Nota de interpretacion: la tabla del Documento Tecnico marca con "—" el
# financiero de la unidad para los roles administrativos. Ese guion significa
# "no es un permiso separado", porque quien ve el financiero del edificio ve
# tambien el de cada una de sus unidades. Al pasarlo a un modelo booleano se
# resuelve como True para esos roles: es la lectura correcta, no una ampliacion.
_MATRIZ: dict[str, Rol] = {
    ADMIN_GENERAL: Rol(
        nombre=ADMIN_GENERAL,
        etiqueta="Administrador General",
        alcance=ALCANCE_CARTERA,
        ve_financiero_unidad=True,
        ve_financiero_edificio=True,
        solo_lectura=False,
    ),
    ADMIN_CONSORCIO: Rol(
        nombre=ADMIN_CONSORCIO,
        etiqueta="Administrador de Consorcio",
        alcance=ALCANCE_EDIFICIO,
        ve_financiero_unidad=True,
        ve_financiero_edificio=True,
        solo_lectura=False,
    ),
    # El Encargado gestiona reclamos, ordenes de trabajo y activos de su
    # edificio, pero NUNCA ve un monto: el semaforo si, los importes no.
    ENCARGADO: Rol(
        nombre=ENCARGADO,
        etiqueta="Encargado",
        alcance=ALCANCE_EDIFICIO,
        ve_financiero_unidad=False,
        ve_financiero_edificio=False,
        solo_lectura=False,
    ),
    PROPIETARIO: Rol(
        nombre=PROPIETARIO,
        etiqueta="Propietario",
        alcance=ALCANCE_UNIDAD,
        ve_financiero_unidad=True,
        ve_financiero_edificio=False,
        solo_lectura=False,
    ),
    # Decision adoptada (Documento General 3.1): el Inquilino tiene EXACTAMENTE
    # el mismo acceso financiero que el Propietario a nivel de su propia unidad.
    # El diseno original decia lo contrario, y al implementar pagos aparecio la
    # contradiccion: en la enorme mayoria de los alquileres de Argentina la
    # expensa ordinaria la paga de hecho el inquilino, y uno que no puede ver su
    # propia expensa no puede usar el modulo que mas va a usar.
    INQUILINO: Rol(
        nombre=INQUILINO,
        etiqueta="Inquilino",
        alcance=ALCANCE_UNIDAD,
        ve_financiero_unidad=True,
        ve_financiero_edificio=False,
        solo_lectura=False,
    ),
    PROVEEDOR: Rol(
        nombre=PROVEEDOR,
        etiqueta="Proveedor / Tecnico",
        alcance=ALCANCE_OTS_ASIGNADAS,
        ve_financiero_unidad=False,
        ve_financiero_edificio=False,
        solo_lectura=False,
    ),
    # El unico rol de solo lectura del sistema.
    AUDITOR: Rol(
        nombre=AUDITOR,
        etiqueta="Auditor",
        alcance=ALCANCE_ASIGNADO,
        ve_financiero_unidad=True,
        ve_financiero_edificio=True,
        solo_lectura=True,
    ),
    SEGURIDAD: Rol(
        nombre=SEGURIDAD,
        etiqueta="Personal de seguridad",
        alcance=ALCANCE_EDIFICIO,
        ve_financiero_unidad=False,
        ve_financiero_edificio=False,
        solo_lectura=False,
    ),
}

ROLES: tuple[str, ...] = tuple(_MATRIZ)
"""Los 8 roles validos, en el orden de la documentacion.

Es la lista que consumen los CheckConstraint de los modelos y los validadores
de Pydantic. **Nunca se repite esta lista escrita a mano en otro archivo**: si
se repitiera, en algun momento una de las dos copias quedaria atras y la base
aceptaria un rol que la aplicacion no conoce, o al reves.
"""


# ---------------------------------------------------------------- consultas --


class RolDesconocido(ValueError):
    """El rol no existe en la matriz."""


def obtener(rol: str) -> Rol:
    """Devuelve la definicion de un rol, o falla ruidosamente.

    Falla en vez de devolver un rol "por defecto" o None: un rol mal escrito es
    un error de programacion, y un permiso que se resuelve silenciosamente por
    defecto es la forma mas facil de abrir un agujero sin darse cuenta.
    """
    try:
        return _MATRIZ[rol]
    except KeyError:
        raise RolDesconocido(
            f"Rol desconocido: {rol!r}. Los validos son: {', '.join(ROLES)}."
        ) from None


def es_rol_valido(rol: str) -> bool:
    return rol in _MATRIZ


def etiqueta(rol: str) -> str:
    """El nombre del rol tal como se le muestra a una persona."""
    return obtener(rol).etiqueta


def alcance(rol: str) -> str:
    return obtener(rol).alcance


def ve_financiero_unidad(rol: str) -> bool:
    """Si puede ver la expensa, el saldo y los pagos de una unidad."""
    return obtener(rol).ve_financiero_unidad


def ve_financiero_edificio(rol: str) -> bool:
    """Si puede ver los importes del edificio: gastos, liquidaciones, deudores.

    El Encargado da False a proposito: ve el semaforo del edificio, nunca los
    montos.
    """
    return obtener(rol).ve_financiero_edificio


def es_solo_lectura(rol: str) -> bool:
    """Si el rol no puede modificar nada, en ninguna pantalla."""
    return obtener(rol).solo_lectura


def puede_escribir(rol: str) -> bool:
    return not es_solo_lectura(rol)


def roles_con(alcance_buscado: str) -> tuple[str, ...]:
    """Los roles que tienen un alcance determinado.

    Util para armar mensajes de error y para las pruebas, no para autorizar:
    autorizar es siempre preguntar por un rol concreto.
    """
    return tuple(r.nombre for r in _MATRIZ.values() if r.alcance == alcance_buscado)

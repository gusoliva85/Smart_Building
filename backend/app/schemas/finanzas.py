"""Esquemas del dinero del consorcio (Fase 2).

Por ahora viven aca los del gasto (`F2-T02`). Las expensas, los pagos y los
fondos se suman en las tareas siguientes, en este mismo archivo, igual que sus
modelos conviven en `models/finanzas.py`.

============================================================================
EL MONTO ENTRA COMO `Decimal` Y SE RECHAZA SI TIENE MAS DE DOS DECIMALES
============================================================================

No se redondea en silencio. Un monto de 1234,567 guardado como 1234,57 es
plata que nadie decidio: la diferencia aparece meses despues, al cerrar un
periodo, y para entonces no hay forma de saber de que fila salio. Es la misma
regla que ya rige para el coeficiente, que rechaza mas de tres decimales en
vez de recortarlos.

Pydantic recibe el numero como `Decimal` y no como `float` **por la misma
razon por la que la columna es `Numeric`**: un `float` ya llega mal desde el
JSON, asi que validar sobre el no sirve de nada.

============================================================================
EL RUBRO SE VALIDA CONTRA EL CATALOGO, NO CONTRA UNA LISTA ESCRITA ACA
============================================================================

La lista sale de `services/rubros.py`, que es la misma de la que se arma el
CHECK de la tabla. Asi hay una sola definicion de que es un rubro valido: el
esquema la usa para dar un mensaje claro, y la base la usa como ultima barrera
para lo que entre por fuera de la API.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services import rubros

# Dos decimales: la columna es `Numeric(12,2)`. Se escribe una sola vez aca y
# el modelo la declara igual; si alguna vez cambiara, cambia en los dos lados
# a la vez o los tests del modelo lo cantan.
DECIMALES_MONTO = 2

# Tope del monto de un gasto, alineado con `Numeric(12,2)`.
MONTO_MAXIMO = Decimal("9999999999.99")

# Largo maximo de la descripcion. La columna es `Text` y no tiene limite
# propio, asi que el limite lo pone el esquema: sin tope, un pegado accidental
# de diez mil caracteres entra sin que nada lo frene y despues rompe cualquier
# listado.
LARGO_DESCRIPCION = 500


def _monto_valido(valor: Decimal) -> Decimal:
    """Un monto con dos decimales como maximo, y finito.

    El chequeo de `is_finite` no es paranoia: el JSON admite `NaN` e
    `Infinity` en varios parsers, y un `Decimal('NaN')` atraviesa cualquier
    comparacion `>` sin levantar nada y llega hasta la base.
    """
    if not valor.is_finite():
        raise ValueError("El monto tiene que ser un número.")
    if -valor.as_tuple().exponent > DECIMALES_MONTO:
        raise ValueError(f"El monto admite hasta {DECIMALES_MONTO} decimales.")
    return valor


def _rubro_valido(valor: str) -> str:
    """Un rubro del catalogo. El mensaje dice cuales son, no solo que ese no.

    Quien manda un rubro invalido casi siempre lo escribio a mano o lo trajo de
    otro sistema: decirle "no es valido" lo obliga a ir a buscar la lista a
    otro lado, y la lista es corta.
    """
    if not rubros.es_rubro_valido(valor):
        raise ValueError(
            "El rubro tiene que ser uno de estos: " + ", ".join(rubros.RUBROS) + "."
        )
    return valor


class GastoCrear(BaseModel):
    """Un gasto nuevo del consorcio.

    `proveedor_id` y `activo_id` **no se piden todavia**: las pantallas que
    eligen un proveedor (Fase 7) y un activo (Fase 4) no existen, y un campo
    que acepta cualquier entero sin nada que lo valide es una invitacion a
    guardar basura. Las columnas estan en la tabla, que es lo que hace que
    agregarlos despues no necesite migracion.
    """

    model_config = ConfigDict(extra="forbid")

    rubro: str
    monto: Decimal = Field(gt=0, le=MONTO_MAXIMO)
    fecha: date
    descripcion: str | None = Field(default=None, max_length=LARGO_DESCRIPCION)

    @field_validator("rubro")
    @classmethod
    def del_catalogo(cls, valor: str) -> str:
        return _rubro_valido(valor)

    @field_validator("monto")
    @classmethod
    def con_dos_decimales(cls, valor: Decimal) -> Decimal:
        return _monto_valido(valor)

    @field_validator("descripcion")
    @classmethod
    def sin_espacios_al_borde(cls, valor: str | None) -> str | None:
        """Una descripcion de solo espacios es una descripcion vacia.

        Sin esto, " " se guarda como texto y el listado muestra una celda en
        blanco que parece un error de la pantalla.
        """
        if valor is None:
            return None
        limpio = valor.strip()
        return limpio or None


class GastoEditar(BaseModel):
    """La edicion de un gasto, campo por campo.

    **Todos los campos son opcionales y por eso hace falta distinguir "no lo
    mandaste" de "lo mandaste vacio"**: `descripcion=None` tiene que poder
    borrar la descripcion, y no mandar `descripcion` tiene que dejarla como
    esta. Eso se resuelve en el endpoint con `exclude_unset`, no aca.

    La edicion es parte de esta tarea y no un agregado posterior: sin ella, un
    monto mal cargado obliga a borrar el gasto y cargarlo de nuevo, y con eso
    se pierde la fecha de carga original.
    """

    model_config = ConfigDict(extra="forbid")

    rubro: str | None = None
    monto: Decimal | None = Field(default=None, gt=0, le=MONTO_MAXIMO)
    fecha: date | None = None
    descripcion: str | None = Field(default=None, max_length=LARGO_DESCRIPCION)

    @field_validator("rubro")
    @classmethod
    def del_catalogo(cls, valor: str | None) -> str | None:
        return None if valor is None else _rubro_valido(valor)

    @field_validator("monto")
    @classmethod
    def con_dos_decimales(cls, valor: Decimal | None) -> Decimal | None:
        return None if valor is None else _monto_valido(valor)

    @field_validator("descripcion")
    @classmethod
    def sin_espacios_al_borde(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        limpio = valor.strip()
        return limpio or None


class GastoLeer(BaseModel):
    """Un gasto como lo lee la pantalla.

    Lleva `rubro` y `rubro_etiqueta` juntos: el primero es el valor estable con
    el que la pantalla filtra y agrupa, el segundo es el texto que se muestra.
    Mandar solo el nombre interno obligaria al frontend a tener su propia copia
    del catalogo, y esa copia es la que un dia queda vieja.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    rubro: str
    rubro_etiqueta: str
    monto: Decimal
    fecha: date
    descripcion: str | None


class RubroLeer(BaseModel):
    """Una entrada del catalogo, para armar el desplegable de la pantalla."""

    nombre: str
    etiqueta: str
    descripcion: str


class ListadoDeGastos(BaseModel):
    """Los gastos que pasaron el filtro, con lo que suman.

    **El total viaja calculado por el servidor y no lo suma la pantalla.** Es el
    numero que despues se reparte entre las unidades, asi que tiene que salir
    del mismo lugar del que va a salir la expensa; dos sumas hechas en dos
    lados distintos son dos numeros que algun dia no coinciden.
    """

    total: Decimal
    cantidad: int
    gastos: list[GastoLeer]

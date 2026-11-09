"""Esquemas de entrada de la estructura del edificio (`F1-T23`).

Pisos, departamentos, cocheras y espacios comunes. Las respuestas no se
redefinen aca: son las de `schemas/edificio.py` —`PisoDetalle`,
`DepartamentoDetalle`, `CocheraDetalle`, `EspacioComunDetalle`—, que ya las usa
el detalle del edificio. Dos esquemas de salida para la misma fila es la clase
de duplicacion que termina con una pantalla mostrando un campo que la otra no.

============================================================================
CADA ENTIDAD TIENE UN ESQUEMA DE ALTA Y OTRO DE EDICION, Y NINGUNO HEREDA
============================================================================

Son parecidos y aun asi van separados, igual que en el resto del proyecto. El
alta exige lo que la fila necesita para existir; la edicion no exige nada y
distingue "no mandes el campo" de "mandalo en null". Si la edicion heredara del
alta, heredaria tambien sus campos obligatorios, y el dia que el alta gane uno
nuevo la edicion empezaria a pedirlo sin que nadie lo decida.

============================================================================
LOS DECIMALES SE RECHAZAN, NO SE REDONDEAN
============================================================================

`m2` es `Numeric(8,2)`: un 45,678 se guardaria como 45,68 y quien lo escribio
no se enteraria. Y la superficie no es un dato decorativo — de ella sale el
atajo de coeficientes por metro cuadrado, o sea el reparto de la expensa. El
mismo criterio que el recargo por mora de `F1-T22`.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import edificio as modelo_edificio

DECIMALES_M2 = 2

# Un piso puede llamarse 0 (planta baja) o -1 (subsuelo), asi que el rango no
# empieza en 1. Los topes son generosos a proposito: no estan para describir
# edificios reales sino para que un 99999 escrito de mas no entre a la base.
PISO_MINIMO = -10
PISO_MAXIMO = 200


def _texto_obligatorio(valor: str) -> str:
    limpio = valor.strip()
    if not limpio:
        raise ValueError("No puede quedar vacío.")
    return limpio


def _texto_opcional(valor: str | None) -> str | None:
    if valor is None:
        return None
    return valor.strip() or None


def _m2_valido(valor: Decimal | None) -> Decimal | None:
    """Superficie mayor que cero y con dos decimales como maximo.

    El cero se rechaza y no es un detalle: `calcular_por_metros_cuadrados()`
    reparte 100% proporcionalmente a la superficie, y una unidad con 0 m2
    quedaria con coeficiente 0 — o sea, sin pagar expensas, sin que nadie lo
    haya decidido.
    """
    if valor is None:
        return None
    if valor <= 0:
        raise ValueError("La superficie tiene que ser mayor que cero.")
    if -valor.as_tuple().exponent > DECIMALES_M2:
        raise ValueError(f"La superficie admite hasta {DECIMALES_M2} decimales.")
    return valor


def _exigir_algun_campo(modelo: BaseModel) -> BaseModel:
    """Un PATCH sin campos no es un cambio, es un pedido mal armado."""
    if not modelo.model_fields_set:
        raise ValueError("No enviaste ningún cambio.")
    return modelo


# ===========================================================================
# PISOS
# ===========================================================================


class PisoCrear(BaseModel):
    """Alta de un piso.

    `orden` es opcional: si no viene, el piso se agrega **arriba del ultimo**,
    que es el caso normal —se construyo una planta mas— y evita que quien carga
    tenga que saber como se numera internamente. Si viene, manda lo que se
    pidio: es el caso del entrepiso, que va en el medio.
    """

    model_config = ConfigDict(extra="forbid")

    numero: int = Field(ge=PISO_MINIMO, le=PISO_MAXIMO)
    orden: int | None = Field(default=None, ge=PISO_MINIMO, le=PISO_MAXIMO)


class PisoEditar(BaseModel):
    """Edicion de un piso: su nombre y su lugar en la pila."""

    model_config = ConfigDict(extra="forbid")

    numero: int | None = Field(default=None, ge=PISO_MINIMO, le=PISO_MAXIMO)
    orden: int | None = Field(default=None, ge=PISO_MINIMO, le=PISO_MAXIMO)

    @model_validator(mode="after")
    def algun_campo(self) -> "PisoEditar":
        _exigir_algun_campo(self)
        # Ninguno de los dos es anulable en la tabla, asi que mandarlos en
        # `null` es un pedido imposible y conviene que el rechazo lo explique.
        for campo in ("numero", "orden"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"«{campo}» no puede quedar vacío.")
        return self


# ===========================================================================
# DEPARTAMENTOS
# ===========================================================================


class DepartamentoCrear(BaseModel):
    """Alta de una unidad en un piso que ya existe.

    No pide `coeficiente`: la carga de coeficientes es `F1-T24` y tiene su
    propio endpoint. Y no pide propietario ni inquilino porque una unidad
    recien creada todavia no sabe quien la habita: se asignan con el PATCH,
    que es tambien el que desvincula.
    """

    model_config = ConfigDict(extra="forbid")

    identificador: str = Field(min_length=1, max_length=20)
    m2: Decimal | None = None

    @field_validator("identificador")
    @classmethod
    def identificador_limpio(cls, valor: str) -> str:
        return _texto_obligatorio(valor)

    @field_validator("m2")
    @classmethod
    def superficie_valida(cls, valor: Decimal | None) -> Decimal | None:
        return _m2_valido(valor)


class DepartamentoEditar(BaseModel):
    """Edicion de una unidad, incluida la asignacion de quien la habita.

    `propietario_id` e `inquilino_id` en `null` **desvinculan**, que es lo que
    pide el Roadmap: "la asignacion y desvinculacion de propietario o inquilino
    a un departamento existente". Van en este PATCH y no en cuatro endpoints
    propios porque la operacion es la misma —cambiar una columna de la
    unidad— y partirla obligaria a la pantalla a decidir a cual de cuatro URLs
    pegarle segun que cambio el usuario.

    Que esas personas existan, esten activas, tengan el rol que corresponde y
    tengan ese rol habilitado en el edificio lo valida el endpoint: hace falta
    la base para saberlo.
    """

    model_config = ConfigDict(extra="forbid")

    identificador: str | None = Field(default=None, min_length=1, max_length=20)
    m2: Decimal | None = None
    propietario_id: int | None = None
    inquilino_id: int | None = None

    @field_validator("identificador")
    @classmethod
    def identificador_limpio(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return _texto_obligatorio(valor)

    @field_validator("m2")
    @classmethod
    def superficie_valida(cls, valor: Decimal | None) -> Decimal | None:
        return _m2_valido(valor)

    @model_validator(mode="after")
    def algun_campo(self) -> "DepartamentoEditar":
        _exigir_algun_campo(self)
        if "identificador" in self.model_fields_set and self.identificador is None:
            raise ValueError("«identificador» no puede quedar vacío.")
        return self


# ===========================================================================
# COCHERAS
# ===========================================================================


class CocheraCrear(BaseModel):
    """Alta de una cochera.

    `numero` es texto porque en la practica las cocheras estan rotuladas, y el
    rotulo dice "S2-14" o "12 bis" tan seguido como dice "12".

    `departamento_id` es opcional y solo vale para las **fijas**: una cochera
    rotativa, por definicion, no es de nadie en particular. La tabla tambien lo
    prohibe con un CHECK; el endpoint lo valida antes para que el mensaje
    explique el motivo en vez de devolver un 500.
    """

    model_config = ConfigDict(extra="forbid")

    numero: str = Field(min_length=1, max_length=20)
    tipo: str
    departamento_id: int | None = None

    @field_validator("numero")
    @classmethod
    def numero_limpio(cls, valor: str) -> str:
        return _texto_obligatorio(valor)

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, valor: str) -> str:
        limpio = valor.strip().lower()
        if limpio not in modelo_edificio.TIPOS_COCHERA:
            validos = ", ".join(modelo_edificio.TIPOS_COCHERA)
            raise ValueError(f"El tipo de cochera tiene que ser uno de: {validos}.")
        return limpio


class CocheraEditar(BaseModel):
    """Edicion de una cochera."""

    model_config = ConfigDict(extra="forbid")

    numero: str | None = Field(default=None, min_length=1, max_length=20)
    tipo: str | None = None
    departamento_id: int | None = None

    @field_validator("numero")
    @classmethod
    def numero_limpio(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return _texto_obligatorio(valor)

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        limpio = valor.strip().lower()
        if limpio not in modelo_edificio.TIPOS_COCHERA:
            validos = ", ".join(modelo_edificio.TIPOS_COCHERA)
            raise ValueError(f"El tipo de cochera tiene que ser uno de: {validos}.")
        return limpio

    @model_validator(mode="after")
    def algun_campo(self) -> "CocheraEditar":
        _exigir_algun_campo(self)
        for campo in ("numero", "tipo"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"«{campo}» no puede quedar vacío.")
        return self


# ===========================================================================
# ESPACIOS COMUNES
# ===========================================================================


class EspacioComunCrear(BaseModel):
    """Alta de un espacio comun.

    `capacidad` es opcional porque hay espacios que no tienen aforo: un laundry
    con dos lavarropas no se mide en personas. Y es mayor que cero cuando
    viene: un 0 usado como "sin dato" seria un espacio que no admite a nadie,
    y la pantalla de reservas lo mostraria como lleno para siempre.
    """

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=120)
    capacidad: int | None = Field(default=None, gt=0)
    reglas_uso: str | None = None

    @field_validator("nombre")
    @classmethod
    def nombre_limpio(cls, valor: str) -> str:
        return _texto_obligatorio(valor)

    @field_validator("reglas_uso")
    @classmethod
    def reglas_limpias(cls, valor: str | None) -> str | None:
        return _texto_opcional(valor)


class EspacioComunEditar(BaseModel):
    """Edicion de un espacio comun. `capacidad` y `reglas_uso` se pueden vaciar."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    capacidad: int | None = Field(default=None, gt=0)
    reglas_uso: str | None = None

    @field_validator("nombre")
    @classmethod
    def nombre_limpio(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return _texto_obligatorio(valor)

    @field_validator("reglas_uso")
    @classmethod
    def reglas_limpias(cls, valor: str | None) -> str | None:
        return _texto_opcional(valor)

    @model_validator(mode="after")
    def algun_campo(self) -> "EspacioComunEditar":
        _exigir_algun_campo(self)
        if "nombre" in self.model_fields_set and self.nombre is None:
            raise ValueError("«nombre» no puede quedar vacío.")
        return self

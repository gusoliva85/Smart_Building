"""Esquemas de fondos, caja chica, presupuestos y facturas (`F2-T15`).

Archivo propio y no dentro de `schemas/finanzas.py` porque ese ya tiene los de
gastos, expensas y pagos y pasaba las mil lineas. Son cuatro dominios que se
leen juntos — todo lo que no es el circuito de la expensa.

============================================================================
LO QUE SE REPITE EN LOS CUATRO
============================================================================

**El monto entra como `Decimal` y se rechaza con mas de dos decimales**, nunca
se redondea en silencio. Y **ningun esquema de entrada acepta el estado ni los
campos de auditoria** (`registrado_por_id`, `decidido_por_id`): salen del
token, no del cuerpo del pedido. Si el cliente pudiera mandarlos, podria
aprobar un presupuesto en nombre de otra persona.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.finanzas import (
    LARGO_DESCRIPCION,
    LARGO_URL,
    MONTO_MAXIMO,
    _monto_valido,
)
from app.services import fondos, presupuestos

LARGO_NOMBRE_FONDO = 80
LARGO_NUMERO_FACTURA = 50


def _texto_limpio(valor: str | None) -> str | None:
    """Sin espacios al borde, y vacio es nulo.

    Un nombre de " " se guarda como texto y despues la pantalla muestra una
    celda en blanco que parece un error.
    """
    if valor is None:
        return None
    limpio = valor.strip()
    return limpio or None


# ===========================================================================
# FONDOS
# ===========================================================================


class FondoCrear(BaseModel):
    """Un fondo nuevo del consorcio."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=3, max_length=LARGO_NOMBRE_FONDO)
    descripcion: str | None = Field(default=None, max_length=LARGO_DESCRIPCION)

    @field_validator("nombre", "descripcion")
    @classmethod
    def sin_espacios_al_borde(cls, valor: str | None) -> str | None:
        return _texto_limpio(valor)


class FondoEditar(BaseModel):
    """Cambios sobre un fondo. Todo opcional; el endpoint usa `exclude_unset`."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=3, max_length=LARGO_NOMBRE_FONDO)
    descripcion: str | None = Field(default=None, max_length=LARGO_DESCRIPCION)
    activo: bool | None = None

    @field_validator("nombre", "descripcion")
    @classmethod
    def sin_espacios_al_borde(cls, valor: str | None) -> str | None:
        return _texto_limpio(valor)


class MovimientoCrear(BaseModel):
    """Un movimiento de un fondo o de la caja. **El mismo esquema para los dos.**

    Los dos modelos tienen las mismas columnas y el mismo catalogo de tipos, asi
    que un esquema por cada uno serian dos copias que algun dia se separan.
    """

    model_config = ConfigDict(extra="forbid")

    tipo: str
    monto: Decimal = Field(gt=0, le=MONTO_MAXIMO)
    fecha: date
    descripcion: str | None = Field(default=None, max_length=LARGO_DESCRIPCION)

    @field_validator("tipo")
    @classmethod
    def del_catalogo(cls, valor: str) -> str:
        if not fondos.es_tipo_valido(valor):
            raise ValueError(
                "El tipo tiene que ser uno de estos: "
                + ", ".join(fondos.TIPOS_DE_MOVIMIENTO)
                + "."
            )
        return valor

    @field_validator("monto")
    @classmethod
    def con_dos_decimales(cls, valor: Decimal) -> Decimal:
        return _monto_valido(valor)

    @field_validator("descripcion")
    @classmethod
    def sin_espacios_al_borde(cls, valor: str | None) -> str | None:
        return _texto_limpio(valor)


class MovimientoLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    tipo_etiqueta: str
    monto: Decimal
    fecha: date
    descripcion: str | None
    registrado_por: str
    creado_en: datetime


class FondoLeer(BaseModel):
    """Un fondo con su saldo calculado.

    Trae los tres totales —ingresos, egresos y saldo— porque responden
    preguntas distintas: cuanto junto el consorcio no es lo mismo que cuanto
    queda disponible.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    activo: bool
    ingresos: Decimal
    egresos: Decimal
    saldo: Decimal
    cantidad_movimientos: int
    esta_en_rojo: bool


class ListadoDeFondos(BaseModel):
    """Los fondos del edificio con el total de lo que tiene guardado.

    El total viaja calculado: es el numero del resumen del edificio y del
    Dashboard General, y se calcula una sola vez para que las dos pantallas
    muestren lo mismo.
    """

    total: Decimal
    cantidad: int
    fondos: list[FondoLeer]


# ===========================================================================
# CAJA CHICA
# ===========================================================================


class CajaGuardar(BaseModel):
    """El monto fijo y el responsable de la caja chica.

    Mismo esquema para crearla y para editarla: son los dos unicos datos que
    la definen, y editarla es cambiar uno de los dos.
    """

    model_config = ConfigDict(extra="forbid")

    monto_fijo: Decimal = Field(gt=0, le=MONTO_MAXIMO)
    responsable_id: int

    @field_validator("monto_fijo")
    @classmethod
    def con_dos_decimales(cls, valor: Decimal) -> Decimal:
        return _monto_valido(valor)


class CajaLeer(BaseModel):
    """El estado de la caja: todo derivado del monto fijo y los movimientos.

    `pendiente_de_reposicion` es **lo que el responsable gasto y todavia no le
    devolvieron**, que es la cifra de la rendicion, y `reposicion_sugerida` es
    el valor que la pantalla pone por defecto en el formulario de reposicion.
    Son el mismo numero, con dos nombres, porque se leen en dos lugares
    distintos de la pantalla.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    monto_fijo: Decimal
    responsable_id: int
    responsable: str
    activo: bool

    ingresos: Decimal
    egresos: Decimal
    disponible: Decimal
    pendiente_de_reposicion: Decimal
    reposicion_sugerida: Decimal
    cantidad_movimientos: int

    necesita_reposicion: bool
    esta_en_rojo: bool
    excede_el_fondo_fijo: bool


# ===========================================================================
# PRESUPUESTOS
# ===========================================================================


class PresupuestoCrear(BaseModel):
    """Una cotizacion recibida.

    **No acepta `estado`**: un presupuesto siempre nace pendiente. Si el
    cliente pudiera mandarlo, podria cargarlo ya aprobado y la decision dejaria
    de registrarse como tal.
    """

    model_config = ConfigDict(extra="forbid")

    descripcion: str = Field(min_length=3, max_length=LARGO_DESCRIPCION)
    monto: Decimal = Field(gt=0, le=MONTO_MAXIMO)
    fecha: date
    proveedor_id: int | None = None

    @field_validator("monto")
    @classmethod
    def con_dos_decimales(cls, valor: Decimal) -> Decimal:
        return _monto_valido(valor)

    @field_validator("descripcion")
    @classmethod
    def sin_espacios_al_borde(cls, valor: str) -> str:
        limpio = (valor or "").strip()
        if len(limpio) < 3:
            raise ValueError("Escribí qué se cotizó.")
        return limpio


class PresupuestoDecidir(BaseModel):
    """La decision sobre un presupuesto: aprobarlo o rechazarlo.

    `gasto_id` es opcional y solo tiene sentido al aprobar: es el gasto real que
    ese presupuesto genero. Se puede aprobar ahora y vincular despues — el
    gasto normalmente se carga cuando llega la factura.
    """

    model_config = ConfigDict(extra="forbid")

    estado: str
    gasto_id: int | None = None

    @field_validator("estado")
    @classmethod
    def uno_de_los_dos_finales(cls, valor: str) -> str:
        if valor not in (presupuestos.APROBADO, presupuestos.RECHAZADO):
            raise ValueError(
                f"El estado tiene que ser {presupuestos.APROBADO} o "
                f"{presupuestos.RECHAZADO}."
            )
        return valor


class PresupuestoLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    descripcion: str
    monto: Decimal
    fecha: date
    estado: str
    estados_siguientes: list[str]
    proveedor_id: int | None
    gasto_id: int | None

    # Lo que permite comparar lo cotizado con lo que finalmente se pago. Nulo
    # mientras no haya gasto vinculado.
    monto_del_gasto: Decimal | None

    decidido_por: str | None
    decidido_en: datetime | None
    creado_en: datetime


class ListadoDePresupuestos(BaseModel):
    cantidad: int
    pendientes: int
    presupuestos: list[PresupuestoLeer]


# ===========================================================================
# FACTURAS
# ===========================================================================


class FacturaCrear(BaseModel):
    """Un comprobante de un gasto.

    **Casi todo es opcional a proposito.** Cargar un comprobante no es
    obligatorio — muchos gastos reales de un consorcio no tienen uno formal— y
    lo que se carga no tiene que ser una factura fiscal: un recibo, un remito,
    un ticket. Hasta el numero es opcional, porque un recibo escrito a mano no
    tiene numero y exigirlo haria que alguien escriba "sin numero" para poder
    guardar el monto, que es el dato que si tiene.
    """

    model_config = ConfigDict(extra="forbid")

    monto: Decimal = Field(gt=0, le=MONTO_MAXIMO)
    fecha: date
    numero: str | None = Field(default=None, max_length=LARGO_NUMERO_FACTURA)
    proveedor_id: int | None = None
    archivo_url: str | None = Field(default=None, max_length=LARGO_URL)

    @field_validator("monto")
    @classmethod
    def con_dos_decimales(cls, valor: Decimal) -> Decimal:
        return _monto_valido(valor)

    @field_validator("numero")
    @classmethod
    def sin_espacios_al_borde(cls, valor: str | None) -> str | None:
        return _texto_limpio(valor)

    @field_validator("archivo_url")
    @classmethod
    def una_direccion_de_verdad(cls, valor: str | None) -> str | None:
        """Si se manda un enlace, que sea un enlace.

        Mismo criterio que el comprobante de un pago: no se verifica que exista
        —eso seria salir a internet por cada carga— pero la forma ataja el caso
        real, que es pegar el nombre del archivo en vez del enlace.
        """
        limpio = _texto_limpio(valor)
        if limpio is None:
            return None
        if not limpio.startswith(("http://", "https://")):
            raise ValueError(
                "El archivo tiene que ser un enlace que empiece con http:// o "
                "https://."
            )
        return limpio


class FacturaLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    gasto_id: int
    numero: str | None
    monto: Decimal
    fecha: date
    proveedor_id: int | None
    archivo_url: str | None
    creado_en: datetime


class ListadoDeFacturas(BaseModel):
    """Las facturas de un gasto, con lo que suman contra el monto del gasto.

    **La diferencia entre los dos numeros es informacion, no un error**: una
    factura puede traer un ajuste y un gasto puede cubrirse con dos facturas.
    Viaja calculada para que la pantalla pueda mostrarla sin hacer la cuenta.
    """

    cantidad: int
    total_facturado: Decimal
    monto_del_gasto: Decimal
    facturas: list[FacturaLeer]

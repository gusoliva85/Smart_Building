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

from datetime import date, datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.services import pagos, rubros

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

# Largo maximo del enlace al comprobante. Las URL de los servicios de archivos
# son largas de verdad (tokens firmados incluidos), asi que el tope es alto; lo
# que corta es que no sea ilimitado.
LARGO_URL = 2000

# Largo minimo del motivo de un rechazo. No es un numero arbitrario: con menos
# de esto no se escribio un motivo, se escribio cualquier cosa para pasar la
# validacion ("no", "mal"). Cinco caracteres dejan pasar "error" y frenan "x".
LARGO_MINIMO_MOTIVO = 5


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

    # Un aviso para la pantalla cuando el gasto se guardo bien **pero hay algo
    # que quien lo cargo tiene que saber**: hoy, que su fecha cae en un periodo
    # cuya expensa ya se publico, asi que no va a aparecer en esa liquidacion.
    # No es un error y por eso no entra en el catalogo: el gasto es real, se
    # guardo, y lo que corresponde es informar y no bloquear.
    aviso: str | None = None


class RubroLeer(BaseModel):
    """Una entrada del catalogo, para armar el desplegable de la pantalla."""

    nombre: str
    etiqueta: str
    descripcion: str


class ExpensaGenerar(BaseModel):
    """El pedido de generar la liquidacion de un periodo.

    `confirmar` es el segundo paso del patron de confirmacion del proyecto: si
    ya hay una expensa en borrador de ese periodo, el servidor responde `409`
    diciendo exactamente que se va a reemplazar, y el cliente reenvia el mismo
    pedido con esto en `true`. **Es lo que permite no usar nunca un `confirm()`
    del navegador.**
    """

    model_config = ConfigDict(extra="forbid")

    anio: int = Field(ge=2000, le=2100)
    mes: int = Field(ge=1, le=12)
    confirmar: bool = False


class DetalleLeer(BaseModel):
    """Una linea de la apertura por rubro."""

    model_config = ConfigDict(from_attributes=True)

    rubro: str
    rubro_etiqueta: str
    monto: Decimal


class UnidadLiquidadaLeer(BaseModel):
    """Lo que paga una unidad, con los tres montos abiertos.

    **Los tres por separado y no un total**, porque un solo numero no le
    permite al propietario entender por que este mes le vino distinto, y es
    exactamente ahi donde llama por telefono.
    """

    departamento_id: int
    identificador: str
    coeficiente: Decimal
    monto_expensa: Decimal
    recargo_mora: Decimal
    saldo_a_favor_aplicado: Decimal
    total_a_pagar: Decimal


class ExpensaLeer(BaseModel):
    """Una liquidacion con su apertura por rubro y su reparto por unidad."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    anio: int
    mes: int
    periodo: str
    total: Decimal
    estado: str
    publicada_en: datetime | None
    cantidad_unidades: int
    detalle: list[DetalleLeer]
    unidades: list[UnidadLiquidadaLeer]


class ExpensaResumen(BaseModel):
    """Una liquidacion como fila de un listado.

    Trae `se_puede_regenerar` calculado por el servidor y no el estado para que
    la pantalla lo deduzca: la regla de cuando se puede regenerar es del
    backend, y una pantalla que la reimplemente es una pantalla que algun dia
    ofrece un boton que el servidor va a rechazar.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    anio: int
    mes: int
    periodo: str
    total: Decimal
    estado: str
    publicada_en: datetime | None
    cantidad_unidades: int
    cantidad_rubros: int
    se_puede_regenerar: bool


class ExpensaDeUnidad(BaseModel):
    """La liquidacion de un periodo vista desde una unidad.

    Es lo que consume "Mi cuenta" del residente, y por eso lleva **la apertura
    por rubro del edificio** y no solo lo que le toca pagar: la transparencia
    que pide el Documento General (seccion 6.1) es que el consorcista vea en
    que se gasto, no solo cuanto le corresponde. Una expensa que dice un numero
    y nada mas es la razon por la que las administraciones reciben llamados.
    """

    expensa_id: int
    anio: int
    mes: int
    periodo: str
    estado: str
    publicada_en: datetime | None

    # El total del edificio, para poder leer la propia parte en contexto.
    total_edificio: Decimal

    coeficiente: Decimal
    monto_expensa: Decimal
    recargo_mora: Decimal
    saldo_a_favor_aplicado: Decimal
    total_a_pagar: Decimal

    detalle: list[DetalleLeer]


class PagoCargar(BaseModel):
    """El pago que carga el residente.

    **No se piden ni el edificio ni el piso**: el backend resuelve las unidades
    de quien esta logueado. `departamento_id` solo hace falta cuando esa
    persona tiene mas de una unidad en el edificio de esa liquidacion, y en ese
    caso el servidor lo pide con un mensaje que dice cuales son.

    Tampoco se pide el estado: un pago **siempre** nace pendiente. Si el
    cliente pudiera mandarlo, podria mandarlo confirmado.
    """

    model_config = ConfigDict(extra="forbid")

    expensa_id: int
    monto: Decimal = Field(gt=0, le=MONTO_MAXIMO)
    fecha: date
    medio_pago: str
    comprobante_url: str | None = Field(default=None, max_length=LARGO_URL)
    departamento_id: int | None = None

    @field_validator("medio_pago")
    @classmethod
    def del_catalogo(cls, valor: str) -> str:
        if not pagos.es_medio_valido(valor):
            raise ValueError(
                "El medio de pago tiene que ser uno de estos: "
                + ", ".join(pagos.MEDIOS_DE_PAGO)
                + "."
            )
        return valor

    @field_validator("monto")
    @classmethod
    def con_dos_decimales(cls, valor: Decimal) -> Decimal:
        return _monto_valido(valor)

    @field_validator("comprobante_url")
    @classmethod
    def una_direccion_de_verdad(cls, valor: str | None) -> str | None:
        """Si se manda una URL, que sea una URL.

        No se valida que exista ni que la pagina responda — eso seria pedirle
        al backend que salga a internet por cada pago. Se valida la forma, que
        ataja el caso real: pegar el nombre del archivo en vez del enlace.
        """
        if valor is None:
            return None
        limpio = valor.strip()
        if not limpio:
            return None
        if not limpio.startswith(("http://", "https://")):
            raise ValueError(
                "El comprobante tiene que ser un enlace que empiece con "
                "http:// o https://."
            )
        return limpio


class PagoLeer(BaseModel):
    """Un pago como lo lee la pantalla."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    expensa_id: int
    periodo: str
    departamento_id: int
    identificador: str
    monto: Decimal
    fecha: date
    medio_pago: str
    medio_pago_etiqueta: str
    comprobante_url: str | None
    estado: str

    # Lo que el residente tiene que leer, en palabras, sin que la pantalla
    # arme el texto por su cuenta a partir del estado. Si el pago se rechazo,
    # el mensaje **incluye el motivo**: es el dato con el que puede corregir.
    mensaje: str
    motivo_rechazo: str | None

    # Para que la cola de conciliacion sepa que botones mostrar sin tener su
    # propia copia de la tabla de transiciones.
    estados_siguientes: list[str]


class MedioDePagoLeer(BaseModel):
    nombre: str
    etiqueta: str


class PagoConciliar(BaseModel):
    """La decision de la administracion sobre un pago.

    Un solo campo: a que estado pasa. **No se mandan dos endpoints distintos**
    (uno para confirmar y otro para rechazar) porque la validacion es la misma
    — la tabla de transiciones de `services/pagos.py`— y dos endpoints
    significarian escribirla dos veces.
    """

    model_config = ConfigDict(extra="forbid")

    estado: str
    motivo: str | None = Field(default=None, max_length=LARGO_DESCRIPCION)

    @field_validator("estado")
    @classmethod
    def uno_de_los_dos_finales(cls, valor: str) -> str:
        """Solo `confirmado` o `rechazado`.

        `pendiente` se rechaza aca y no en la tabla de transiciones porque es un
        pedido mal formado y no una transicion imposible: nadie "concilia a
        pendiente".
        """
        if valor not in (pagos.CONFIRMADO, pagos.RECHAZADO):
            raise ValueError(
                f"El estado tiene que ser {pagos.CONFIRMADO} o {pagos.RECHAZADO}."
            )
        return valor

    @model_validator(mode="after")
    def el_rechazo_lleva_motivo(self) -> "PagoConciliar":
        """**Rechazar exige motivo; confirmar no lo admite.**

        Las dos mitades importan. Sin motivo, un pago rechazado le dice al
        residente que hable con la administracion y nada mas, y eso es
        exactamente el llamado telefonico que el sistema existe para evitar:
        los motivos reales son pocos y concretos —el comprobante no se ve, el
        monto no coincide, la transferencia no aparecio en el extracto— y con
        cualquiera de ellos escrito el residente resuelve solo.

        Y un motivo en un pago **confirmado** no significa nada: quedaria
        guardado un texto que ninguna pantalla muestra, que es como empiezan los
        datos que nadie sabe de donde salieron.
        """
        limpio = (self.motivo or "").strip()

        if self.estado == pagos.RECHAZADO:
            if len(limpio) < LARGO_MINIMO_MOTIVO:
                raise ValueError(
                    "Para rechazar un pago hay que escribir el motivo, asi el "
                    "residente sabe que corregir."
                )
            object.__setattr__(self, "motivo", limpio)
        else:
            if limpio:
                raise ValueError(
                    "Un pago confirmado no lleva motivo: el motivo es del "
                    "rechazo."
                )
            object.__setattr__(self, "motivo", None)

        return self


class PagoDeGestionLeer(BaseModel):
    """Un pago como lo ve la administracion, en la cola de conciliacion.

    Lleva mas datos que `PagoLeer`: de que unidad es, quien lo cargo y —si ya
    se concilio— quien y cuando. **El residente no necesita saber quien
    concilio su pago; la administracion si**, porque es su propia traza de
    auditoria.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    expensa_id: int
    periodo: str
    departamento_id: int
    identificador: str
    monto: Decimal
    fecha: date
    medio_pago: str
    medio_pago_etiqueta: str
    comprobante_url: str | None
    estado: str
    estados_siguientes: list[str]

    cargado_por: str
    cargado_en: datetime
    conciliado_por: str | None
    conciliado_en: datetime | None
    motivo_rechazo: str | None

    # Si quien esta mirando puede conciliar **este** pago. Lo calcula el
    # servidor: la pantalla no tiene por que saber la regla de que quien carga
    # no concilia, y si la supiera tendria una copia que algun dia no coincide.
    puedo_conciliarlo: bool


class ColaDeConciliacion(BaseModel):
    """El listado de pagos con los totales que la administracion necesita.

    Los totales viajan calculados porque son la razon de ser de la pantalla:
    "hay 12 pagos esperando por $840.000" es la frase que hace que alguien se
    siente a conciliar. Sumarlos en el navegador daria el total de **la
    pagina**, no el del filtro.
    """

    cantidad: int
    total: Decimal
    pagos: list[PagoDeGestionLeer]


class PeriodoDeCuentaLeer(BaseModel):
    """Un periodo en el estado de cuenta de una unidad."""

    expensa_id: int
    periodo: str
    total_a_pagar: Decimal
    pagado_confirmado: Decimal
    pendiente_de_confirmar: Decimal
    saldo: Decimal
    esta_pago: bool


class CuentaDeUnidadLeer(BaseModel):
    """Una unidad con su estado de cuenta: lo que consume "Mi cuenta".

    **Los tres totales van por separado y no netos entre si.** Un unico
    "saldo final" mezclaria plata verificada con plata declarada, que es
    exactamente la distincion que todo este modulo existe para mantener.
    """

    departamento_id: int
    identificador: str
    edificio_id: int
    edificio_nombre: str
    vinculo: str

    deuda: Decimal
    saldo_a_favor: Decimal
    pendiente_de_confirmar: Decimal
    esta_al_dia: bool

    # Los datos para pagar, que es lo que la persona vino a buscar.
    cbu: str | None
    alias_cbu: str | None

    periodos: list[PeriodoDeCuentaLeer]


class DeudorLeer(BaseModel):
    """Una unidad con su deuda, como la muestra la pantalla de Deudores.

    **El saldo y lo vencido van por separado**, porque responden preguntas
    distintas: cuanto hay que cobrarle, y que tan mal esta. Y la severidad la
    calcula el servidor: si la pantalla la dedujera de los meses, el Dashboard
    Visual y esta pantalla podrian pintar la misma unidad de colores distintos.
    """

    departamento_id: int
    identificador: str

    # Entero, igual que la columna: `Piso.numero` es un numero y no un texto.
    piso_numero: int

    # A quien hay que llamar. Sin esto, la pantalla de cobranza obliga a
    # abrir la ficha de la unidad para cada deudor.
    propietario: str | None
    inquilino: str | None

    saldo: Decimal
    vencido: Decimal
    meses_de_atraso: int
    periodo_mas_viejo: str | None
    periodos_impagos: list[str]
    severidad: str


class ListadoDeDeudores(BaseModel):
    """Los deudores del edificio con los totales de la cartera.

    Los totales viajan calculados: "17 unidades deben $2.400.000, de las cuales
    $1.900.000 estan vencidos" es la foto que la administracion necesita, y
    sumarla en el navegador daria el total de lo que se mostro.
    """

    cantidad_deudores: int
    cantidad_unidades: int
    total: Decimal
    total_vencido: Decimal
    deudores: list[DeudorLeer]


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

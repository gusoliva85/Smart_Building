# -*- coding: utf-8 -*-
"""El ciclo de vida de un pago — logica pura, sin ORM y sin HTTP (`F2-T07`).

============================================================================
LA REGLA FUNDAMENTAL: SOLO UN PAGO CONFIRMADO REDUCE LA DEUDA
============================================================================

El residente **carga** su pago; la administracion lo **concilia** contra el
extracto bancario. Son dos actos de dos personas distintas, y entre uno y otro
el saldo no se mueve.

Si el sistema diera por saldado un pago apenas el residente lo carga,
cualquiera podria subir un comprobante falso —o una captura de pantalla de
otra transferencia— y aparecer sin deuda sin que la plata haya entrado en la
cuenta del consorcio. **La conciliacion es un paso humano, no automatico**, y
no es burocracia: es la unica verificacion que existe de que el dinero llego.

Por eso la pregunta "¿este pago reduce la deuda?" no se contesta mirando si
hay un pago cargado, sino preguntandole a `reduce_la_deuda()`. Esta escrita
como funcion y no como `estado == "confirmado"` repetido en cada consulta
porque es **la** regla del modulo: el dia que haya que revisarla, se revisa en
un solo lugar.

============================================================================
QUIEN CARGA NO PUEDE CONFIRMAR
============================================================================

El propio residente **nunca** puede confirmar su pago, aunque tenga todos los
permisos sobre su unidad. Es la separacion de funciones mas basica que existe
en cualquier circuito de dinero: si quien declara el pago es tambien quien lo
valida, la validacion no valida nada.

Y vale tambien al reves, para el caso que de verdad pasa: **un administrador
que vive en el edificio** —es propietario de una unidad y a la vez administra
el consorcio— puede conciliar los pagos de sus vecinos, pero no el suyo. Esa
persona existe en la realidad del rubro, asi que la regla se escribe por
**quien cargo el pago**, no por el rol de quien lo mira.

============================================================================
UN PAGO PENDIENTE NO BAJA EL SALDO, PERO SE MUESTRA
============================================================================

La tercera regla es de interfaz y es la que evita un problema concreto: si el
residente carga su pago y sigue viendo el saldo intacto, **vuelve a pagar**.
Despues hay que devolverle la plata o dejarla como saldo a favor, y mientras
tanto llamo por telefono.

Asi que un pago pendiente se le muestra —"ya lo cargaste, esta esperando que
la administracion lo confirme"— sin tocar el saldo. `se_le_muestra_al_residente()`
es la funcion que contesta eso, y es distinta de `reduce_la_deuda()`: la
diferencia entre las dos es, exactamente, el problema que este modulo resuelve.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Sequence

PENDIENTE = "pendiente"
CONFIRMADO = "confirmado"
RECHAZADO = "rechazado"

ESTADOS: tuple[str, ...] = (PENDIENTE, CONFIRMADO, RECHAZADO)
"""Los tres estados posibles de un pago.

El CHECK de la tabla se arma desde esta tupla, asi que la base y la aplicacion
no pueden quedar en desacuerdo sobre que es un estado valido.
"""

# Las dos transiciones que existen, y nada mas. Un pago ya conciliado —en
# cualquiera de los dos sentidos— es un hecho registrado: la administracion
# dijo "esta plata entro" o "esta plata no entro", y eso no se edita.
_TRANSICIONES: dict[str, tuple[str, ...]] = {
    PENDIENTE: (CONFIRMADO, RECHAZADO),
    CONFIRMADO: (),
    RECHAZADO: (),
}


def es_estado_valido(estado: str) -> bool:
    """Si ese valor se puede guardar en la columna."""
    return estado in ESTADOS


def transicion_valida(desde: str, hacia: str) -> bool:
    """Si un pago puede pasar de un estado al otro.

    **Las dos transiciones salen de `pendiente` y ninguna vuelve.** No se
    "des-confirma" un pago: si la administracion confirmo por equivocacion, lo
    que corresponde es registrar el movimiento que lo corrige, no reescribir el
    historial. Y un pago rechazado no se reactiva — el residente carga uno
    nuevo, con su comprobante, y queda la traza de los dos intentos.

    Pasar al mismo estado tampoco es valido: confirmar dos veces el mismo pago
    no es inofensivo si en el medio quedo registrado quien lo confirmo y
    cuando.

    Devuelve `False` para un `desde` desconocido: una fila con un estado que el
    sistema no entiende no habilita nada.
    """
    return hacia in _TRANSICIONES.get(desde, ())


def estados_siguientes(estado: str) -> tuple[str, ...]:
    """A que estados puede pasar un pago que esta asi.

    Lo usa la pantalla para decidir que botones mostrar, en vez de que el
    JavaScript tenga su propia copia de la tabla de transiciones — que es la
    copia que un dia ofrece un boton que el servidor rechaza.
    """
    return _TRANSICIONES.get(estado, ())


def esta_conciliado(estado: str) -> bool:
    """Si la administracion ya se pronuncio sobre este pago.

    Sirve para contestar "¿esto sigue en la cola de conciliacion?" sin
    preguntar por los dos estados finales por separado, que es como se termina
    olvidando uno de los dos.
    """
    return estado in (CONFIRMADO, RECHAZADO)


def reduce_la_deuda(estado: str) -> bool:
    """**La regla fundamental.** Solo un pago confirmado reduce la deuda.

    Un pago pendiente es una declaracion del residente; un pago rechazado es
    plata que no entro. Ninguno de los dos mueve el saldo.

    Escrita como funcion y no como `estado == CONFIRMADO` repetido en cada
    consulta: el calculo de deudores, el estado de cuenta de una unidad y los
    reportes van a hacer esta misma pregunta, y tienen que hacerla en un solo
    lugar.
    """
    return estado == CONFIRMADO


def se_le_muestra_al_residente(estado: str) -> bool:
    """Si el residente ve este pago en su cuenta.

    **Los tres se le muestran**, y eso es a proposito. El pendiente, para que
    no vuelva a pagar. El confirmado, porque es su recibo. Y el rechazado,
    porque es la unica forma de que se entere — un pago que desaparece sin
    explicacion es un llamado telefonico garantizado.

    Existe como funcion igual, aunque hoy devuelva siempre `True`, porque la
    pregunta es **distinta** de `reduce_la_deuda()` y la diferencia entre las
    dos es exactamente el problema que este modulo resuelve: se muestra sin
    bajar el saldo. Si algun dia hubiera un estado que no se muestra, el lugar
    donde decirlo es este y no veinte pantallas.
    """
    return es_estado_valido(estado)


def puede_confirmar(quien_confirma_id: int, quien_cargo_id: int) -> bool:
    """Si esa persona puede conciliar ese pago.

    **No recibe roles ni permisos a proposito**: el permiso de rol lo resuelve
    el endpoint, que exige administrador. Lo que esta funcion contesta es la
    otra mitad, la que no depende del rol: **quien cargo el pago no lo
    concilia**, aunque sea el administrador del consorcio y viva en el
    edificio. Ese caso pasa de verdad, y escribir la regla por rol lo dejaria
    pasar.

    Si quien declara el pago es tambien quien lo valida, la validacion no
    valida nada.
    """
    return quien_confirma_id != quien_cargo_id


# ===========================================================================
# LOS MEDIOS DE PAGO (`F2-T08`)
# ===========================================================================
#
# Cerrado, por el mismo motivo que los rubros de un gasto: el medio de pago se
# agrupa en los reportes y se filtra en la cola de conciliacion. Con texto
# libre, "Transferencia", "transferencia" y "transf" serian tres medios
# distintos, y la administracion que quiere ver "cuanto entro por
# transferencia este mes" veria un tercio.
#
# Importante: **el medio de pago no cambia ninguna regla.** Un pago en efectivo
# y uno por transferencia siguen el mismo ciclo y los dos necesitan
# conciliacion humana. Es un dato para conciliar y para reportar, no una
# bifurcacion del flujo.


@dataclass(frozen=True)
class MedioDePago:
    """Un medio de pago: su nombre interno y como se lee en pantalla."""

    nombre: str
    etiqueta: str


MEDIOS: tuple[MedioDePago, ...] = (
    # Primero el que se usa en el 90% de los casos.
    MedioDePago("transferencia", "Transferencia bancaria"),
    MedioDePago("efectivo", "Efectivo"),
    MedioDePago("debito_automatico", "Débito automático"),
    MedioDePago("cheque", "Cheque"),
    MedioDePago("otro", "Otro"),
)

MEDIOS_DE_PAGO: tuple[str, ...] = tuple(medio.nombre for medio in MEDIOS)

_MEDIOS_POR_NOMBRE: dict[str, MedioDePago] = {m.nombre: m for m in MEDIOS}


def es_medio_valido(nombre: str) -> bool:
    return nombre in _MEDIOS_POR_NOMBRE


def etiqueta_del_medio(nombre: str) -> str:
    """Como se lee el medio de pago en pantalla.

    Revienta si no existe, en vez de devolver el nombre interno: un
    `debito_automatico` escrito asi en la pantalla es un error que nadie
    reporta pero todos ven.
    """
    medio = _MEDIOS_POR_NOMBRE.get(nombre)
    if medio is None:
        raise ValueError(
            f"Medio de pago invalido: {nombre!r}. Los validos son: "
            f"{', '.join(MEDIOS_DE_PAGO)}."
        )
    return medio.etiqueta


# ===========================================================================
# EL ESTADO DE CUENTA DE UNA UNIDAD (`F2-T08`)
# ===========================================================================
#
# Logica pura, y vive aca porque la van a usar tres pantallas distintas: "Mi
# cuenta" del residente (`F2-T22`), el calculo de deudores (`F2-T11`) y el
# resumen del edificio. Si cada una armara su propia cuenta, tarde o temprano
# dos pantallas le dirian al mismo propietario dos saldos distintos — y la que
# estaria mal seria siempre la que nadie reviso.
#
# ============================================================================
# EL SALDO A FAVOR ES UN SALDO NEGATIVO, NO UNA TABLA
# ============================================================================
#
# No hay columna ni tabla de "saldo a favor". Es lo que sobra cuando una unidad
# pago mas de lo que debia: el saldo de ese periodo da negativo, y la suma de
# los negativos es lo que tiene a favor. Guardarlo seria guardar un numero que
# se deduce de los pagos, y el dia que un pago se rechace habria que acordarse
# de recalcularlo.


@dataclass(frozen=True)
class PeriodoDeCuenta:
    """Lo que una unidad debe y pago en un periodo.

    Entra con los datos ya leidos de la base — asi esta funcion no sabe que
    existe un ORM y se puede probar con numeros escritos a mano.
    """

    expensa_id: int
    anio: int
    mes: int
    total_a_pagar: Decimal
    pagado_confirmado: Decimal
    pendiente_de_confirmar: Decimal

    # Los tres que siguen tienen valor por defecto porque no todos los
    # consumidores de esta estructura los necesitan: el estado de cuenta del
    # residente se arma sin ellos. Los usa el calculo de deudores (`F2-T11`),
    # que necesita separar el capital del recargo — para no cobrar recargo
    # sobre el recargo— y saber si el periodo ya vencio.
    monto_expensa: Decimal = Decimal("0.00")
    recargo_mora: Decimal = Decimal("0.00")
    vence_el: date | None = None

    @property
    def periodo(self) -> str:
        return f"{self.mes:02d}/{self.anio}"

    @property
    def capital_impago(self) -> Decimal:
        """Lo que falta pagar **del capital**, sin contar el recargo.

        Es la base sobre la que se calcula un recargo nuevo, y por eso se
        calcula aparte del saldo: si la base fuera el saldo, incluiria el
        recargo del mes anterior y habria **recargo sobre el recargo** — una
        deuda chica se multiplicaria sola.

        **Los pagos se imputan primero al recargo y despues al capital.** Es la
        regla habitual del rubro (intereses primero) y la que hace que esta
        cuenta cierre: mientras el capital no se pague, sigue generando
        recargo.
        """
        pagado_al_capital = max(
            Decimal("0.00"), self.pagado_confirmado - self.recargo_mora
        )
        return max(Decimal("0.00"), self.monto_expensa - pagado_al_capital)

    @property
    def saldo(self) -> Decimal:
        """Lo que falta pagar de este periodo.

        **Negativo significa que pago de mas**, y eso es informacion, no un
        error: es el saldo a favor que se va a aplicar en la liquidacion
        siguiente.
        """
        return self.total_a_pagar - self.pagado_confirmado

    @property
    def esta_pago(self) -> bool:
        return self.saldo <= 0


@dataclass(frozen=True)
class CuentaDeUnidad:
    """El resumen de una unidad: lo que debe, lo que tiene a favor, y por que.

    `deuda` y `saldo_a_favor` **nunca son los dos mayores que cero a la vez**
    en el mismo periodo, pero si pueden convivir en la cuenta: se puede deber
    marzo y haber adelantado mayo. Mostrar un solo numero neto esconderia
    justamente eso, y es lo que hace que un propietario crea que esta al dia.
    """

    periodos: tuple[PeriodoDeCuenta, ...]
    deuda: Decimal
    saldo_a_favor: Decimal
    pendiente_de_confirmar: Decimal

    @property
    def esta_al_dia(self) -> bool:
        return self.deuda <= 0


def armar_cuenta(periodos: Sequence[PeriodoDeCuenta]) -> CuentaDeUnidad:
    """El estado de cuenta de una unidad a partir de sus periodos liquidados.

    Tres totales, y los tres son distintos a proposito:

      - `deuda`: la suma de los saldos **positivos**. Lo que falta pagar.
      - `saldo_a_favor`: la suma de los saldos negativos, en positivo. Lo que
        pago de mas y se le va a descontar.
      - `pendiente_de_confirmar`: lo que cargo y la administracion todavia no
        concilio. **No reduce la deuda** (es la regla fundamental de este
        modulo) pero se muestra igual, porque si no el residente ve su saldo
        intacto y vuelve a pagar.

    Los tres se devuelven por separado y no netos entre si. Un unico numero
    "saldo final" mezclaria plata verificada con plata declarada, que es
    exactamente la distincion que todo este modulo existe para mantener.
    """
    deuda = Decimal("0.00")
    a_favor = Decimal("0.00")
    pendiente = Decimal("0.00")

    for periodo in periodos:
        saldo = periodo.saldo
        if saldo > 0:
            deuda += saldo
        else:
            a_favor += -saldo
        pendiente += periodo.pendiente_de_confirmar

    return CuentaDeUnidad(
        periodos=tuple(periodos),
        deuda=deuda,
        saldo_a_favor=a_favor,
        pendiente_de_confirmar=pendiente,
    )

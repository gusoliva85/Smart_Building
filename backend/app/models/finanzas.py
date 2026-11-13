"""Los modelos del dinero del consorcio (Fase 2).

Viven aca `Gasto` (`F2-T01`) y la liquidacion: `Expensa`, `ExpensaDetalle` y
`ExpensaDepartamento` (`F2-T04`). Los pagos, los fondos y la caja chica se
suman en las tareas siguientes de la fase, en este mismo archivo: son el mismo
dominio y se leen juntos.

============================================================================
EL CIRCUITO, EN UNA FRASE
============================================================================

Los **gastos** de un periodo se agrupan por rubro y se copian en el **detalle**
de la expensa; su total se reparte entre las unidades segun su coeficiente y
queda una fila **por departamento**. De ahi en adelante la expensa es un
documento: dice lo que decia el dia que se emitio, y lo unico que la mueve son
los pagos.

============================================================================
LA REGLA QUE ATRAVIESA TODO ESTE ARCHIVO: NUNCA `float`
============================================================================

Ninguna columna de plata es `Float`. Son `Numeric` con sus decimales
declarados, porque 0,1 no existe en binario: un monto guardado como float es
un monto que se guarda "casi", y cien montos casi exactos sumados dan un total
que no cierra con ninguno de los dos lados. Es la misma regla que ya rige para
los coeficientes (`Numeric(6,3)`) y los metros cuadrados (`Numeric(8,2)`).

============================================================================
LAS DOS COLUMNAS SIN CLAVE FORANEA, Y POR QUE ESTAN ASI
============================================================================

`proveedor_id` y `activo_id` son enteros sueltos, **sin** `ForeignKey`. No es
un descuido: las tablas destino no existen todavia. Una columna sin FK no
depende de que la tabla destino exista, asi que el dato se puede empezar a
guardar hoy; lo que necesita la tabla es la restriccion.

**Cada una dice aca en que fase se formaliza**, que es la regla del Roadmap
para las columnas diferidas: `activo_id` en la Fase 4 (Activos) y
`proveedor_id` en la Fase 7 (Proveedores). Y ojo con como se formalizan: el
mecanismo de arranque del proyecto es **aditivo** —agrega columnas que faltan,
nunca agrega restricciones a columnas que ya existen—, asi que convertirlas en
clave foranea real necesita una migracion escrita a mano. Esta anotado en
`02_Documento_Tecnico.md`, seccion 3.5.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.services import expensas, rubros

# La lista de rubros validos NO se escribe de nuevo aca: se arma desde la misma
# tupla que usan los reportes y la pantalla. Si se escribiera dos veces, en
# algun momento una copia quedaria atras y la base aceptaria un rubro que la
# aplicacion no sabe mostrar — o al reves, y eso no da error: da una fila que
# no aparece en ningun agrupamiento.
_RUBROS_PARA_CHECK = ", ".join(f"'{rubro}'" for rubro in rubros.RUBROS)


class Gasto(Base):
    """Una erogacion real del consorcio, en un periodo.

    Es el insumo de la expensa: `F2-T05` toma los gastos del periodo, los
    agrupa por rubro y reparte el total entre las unidades segun su
    coeficiente. Nada mas que eso, y por eso el modelo es chico.

    ========================================================================
    UN GASTO ES EDITABLE Y UNA EXPENSA LIQUIDADA NO SE REESCRIBE
    ========================================================================

    Las dos cosas a la vez, y no se contradicen. Un monto se carga mal y hay
    que poder corregirlo, asi que el gasto se edita y se borra. Lo que **no**
    pasa es que esa correccion altere una liquidacion ya emitida: la expensa
    guarda su propia apertura por rubro (`expensa_detalle`) con los montos
    copiados en el momento de liquidar, no una referencia a estas filas. Una
    expensa es un documento contable y dice lo que decia el dia que se emitio.

    La unica forma de que una correccion llegue a una liquidacion es
    **regenerar la ultima** expensa, que es una operacion explicita, pedida a
    mano y con confirmacion (`F2-T05`).
    """

    __tablename__ = "gastos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    edificio_id: Mapped[int] = mapped_column(
        ForeignKey("edificios.id"),
        nullable=False,
        index=True,
    )

    # El rubro es una categoria contable cerrada, no texto libre. El porque
    # esta en `services/rubros.py`: la expensa y los reportes **agrupan** por
    # este valor, y con texto libre "Limpieza" y "limpieza" serian dos lineas
    # distintas en la liquidacion que ve el consorcista.
    rubro: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # Numeric(12,2): hasta 9.999.999.999,99. Un consorcio grande liquida
    # decenas de millones de pesos al mes, asi que doce digitos dejan lugar de
    # sobra sin volver la columna absurda.
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # La fecha del gasto, que es la que decide a que periodo pertenece. Es
    # `Date` y no `DateTime` a proposito: a una factura de luz no le importa la
    # hora, y guardar una hora inventada invita a compararla con otra.
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --------------------------------------------- columnas diferidas ------
    # Enteros sueltos, sin ForeignKey. Ver la cabecera del modulo.
    #
    # `proveedor_id` se formaliza en la **Fase 7** (directorio de proveedores).
    proveedor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #
    # `activo_id` se formaliza en la **Fase 4** (activos y seguridad
    # normativa). Sirve para responder "cuanto gaste en este ascensor", que es
    # la pregunta que hace que el historial de un activo valga algo.
    activo_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    edificio = relationship("Edificio")

    __table_args__ = (
        # Un gasto de cero no es un gasto, y uno negativo es un ingreso — que
        # en este sistema se registra como movimiento de un fondo (`F2-T12`),
        # no como un gasto con el signo cambiado. Permitirlo aca haria que la
        # suma de los gastos de un periodo dejara de ser el total a repartir.
        CheckConstraint("monto > 0", name="ck_gastos_monto_positivo"),
        CheckConstraint(
            f"rubro IN ({_RUBROS_PARA_CHECK})",
            name="ck_gastos_rubro_valido",
        ),
        # El listado y la generacion de la expensa preguntan siempre lo mismo:
        # los gastos de ESTE edificio en ESTE periodo. Un indice por los dos
        # juntos es el que sirve para esa consulta; dos indices sueltos obligan
        # a la base a elegir uno y filtrar el resto a mano.
        Index("ix_gastos_edificio_fecha", "edificio_id", "fecha"),
    )

    def __repr__(self) -> str:
        return (
            f"<Gasto id={self.id} edificio={self.edificio_id} "
            f"rubro={self.rubro!r} monto={self.monto}>"
        )


# ===========================================================================
# LA EXPENSA (`F2-T04`)
# ===========================================================================

_ESTADOS_PARA_CHECK = ", ".join(f"'{estado}'" for estado in expensas.ESTADOS)


class Expensa(Base):
    """La liquidacion de un periodo: un documento contable, no un calculo.

    ========================================================================
    QUE ES EL `total`, EXACTAMENTE
    ========================================================================

    Son **los gastos del consorcio de ese periodo, y nada mas**. No incluye
    recargos por mora ni descuenta saldos a favor: eso son cuentas entre el
    consorcio y una unidad puntual, y viven en `ExpensaDepartamento`. Si
    entraran aca, los pagaria todo el edificio — incluidos los vecinos que
    pagaron en fecha.

    La consecuencia hay que tenerla escrita antes de que alguien la "corrija":
    **la suma de los `total_a_pagar` de las unidades no tiene por que dar este
    numero.** Lo que si tiene que cerrar exacto es la suma de los
    `monto_expensa`, que es lo que se repartio.

    ========================================================================
    POR QUE GUARDA SU PROPIA APERTURA EN VEZ DE APUNTAR A LOS GASTOS
    ========================================================================

    `ExpensaDetalle` copia los montos por rubro en el momento de liquidar. Eso
    es lo que permite las dos cosas a la vez: que un gasto sea editable y que
    una liquidacion emitida diga lo que decia el dia que se emitio. Si la
    apertura se calculara en vivo sobre la tabla de gastos, corregir un gasto
    de marzo cambiaria la expensa de marzo que cuarenta propietarios ya
    pagaron.
    """

    __tablename__ = "expensas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    edificio_id: Mapped[int] = mapped_column(
        ForeignKey("edificios.id"),
        nullable=False,
        index=True,
    )

    # El periodo, en dos columnas enteras y no en una fecha. Una expensa es de
    # un MES, no de un dia: con una fecha habria que elegir un dia arbitrario
    # —el 1, el ultimo— y despues acordarse de esa convencion en cada consulta.
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    mes: Mapped[int] = mapped_column(Integer, nullable=False)

    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Nace en borrador. El valor por defecto va del lado de Python Y de la base
    # (`server_default`): el de Python sirve al crear el objeto, el de la base
    # es el que hace que el mecanismo aditivo de arranque pueda agregar esta
    # columna a una tabla que ya tuviera filas.
    estado: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=expensas.BORRADOR,
        server_default=expensas.BORRADOR,
        index=True,
    )

    # Cuando se publico, que es **el momento desde el que corre el
    # vencimiento**. Nulo mientras este en borrador, y por eso la columna es
    # anulable: no es un dato que falte, es un dato que todavia no ocurrio.
    publicada_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    edificio = relationship("Edificio")

    # `delete-orphan` en las dos: el detalle y el reparto no existen sin su
    # expensa. Es ademas lo que hace que regenerar sea limpio — se vacian las
    # colecciones y se vuelven a llenar, en la misma transaccion, sin borrar la
    # expensa (que conserva su identidad, asi que los pagos que apunten a ella
    # siguen siendo validos).
    detalle = relationship(
        "ExpensaDetalle",
        back_populates="expensa",
        cascade="all, delete-orphan",
    )
    por_departamento = relationship(
        "ExpensaDepartamento",
        back_populates="expensa",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # UN PERIODO, UNA EXPENSA. Sin esto se pueden generar dos
        # liquidaciones del mismo mes para el mismo edificio, y toda la regla
        # de regeneracion se vuelve ambigua: cual de las dos es la que vale.
        UniqueConstraint("edificio_id", "anio", "mes", name="uq_expensas_periodo"),
        CheckConstraint("mes BETWEEN 1 AND 12", name="ck_expensas_mes_valido"),
        CheckConstraint("total > 0", name="ck_expensas_total_positivo"),
        CheckConstraint(
            f"estado IN ({_ESTADOS_PARA_CHECK})",
            name="ck_expensas_estado_valido",
        ),
        # La consulta de todo el modulo: las expensas de ESTE edificio, de la
        # mas nueva a la mas vieja.
        Index("ix_expensas_edificio_periodo", "edificio_id", "anio", "mes"),
    )

    @property
    def esta_publicada(self) -> bool:
        """Si los residentes ya la vieron.

        Se pregunta por el estado y no por `publicada_en is not None`: el
        estado es el dato que manda, y la fecha es informacion de cuando paso.
        """
        return expensas.es_visible_para_el_residente(self.estado)

    @property
    def se_puede_regenerar(self) -> bool:
        return expensas.se_puede_regenerar(self.estado)

    @property
    def periodo(self) -> str:
        """El periodo como lo escribe una persona: "11/2026"."""
        return f"{self.mes:02d}/{self.anio}"

    def __repr__(self) -> str:
        return (
            f"<Expensa id={self.id} edificio={self.edificio_id} "
            f"periodo={self.periodo} estado={self.estado!r} total={self.total}>"
        )


class ExpensaDetalle(Base):
    """Cuanto se gasto en cada rubro, copiado al liquidar.

    Es la transparencia que pide el Documento General (seccion 6.1): el
    consorcista tiene derecho a ver **en que** se gasto, no solo cuanto le
    toca. Una expensa que dice "$4.849.900" y nada mas es la razon por la que
    las administraciones reciben llamados.

    Los montos estan **copiados**, no referenciados. Ver la cabecera de
    `Expensa`.
    """

    __tablename__ = "expensa_detalle"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    expensa_id: Mapped[int] = mapped_column(
        ForeignKey("expensas.id"),
        nullable=False,
        index=True,
    )

    rubro: Mapped[str] = mapped_column(String(32), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    expensa = relationship("Expensa", back_populates="detalle")

    __table_args__ = (
        # Un rubro, una linea. Dos lineas del mismo rubro en la misma
        # liquidacion serian dos renglones "Limpieza" en el comprobante, y el
        # propietario que suma a mano no llegaria al total.
        UniqueConstraint("expensa_id", "rubro", name="uq_detalle_rubro"),
        CheckConstraint("monto > 0", name="ck_detalle_monto_positivo"),
        CheckConstraint(
            f"rubro IN ({_RUBROS_PARA_CHECK})",
            name="ck_detalle_rubro_valido",
        ),
    )

    def __repr__(self) -> str:
        return f"<ExpensaDetalle rubro={self.rubro!r} monto={self.monto}>"


class ExpensaDepartamento(Base):
    """Lo que paga una unidad en una liquidacion. **Tres montos, no uno.**

    ========================================================================
    POR QUE TRES COLUMNAS Y NO UN TOTAL
    ========================================================================

    Decidido el 2026-11-13. Un solo numero no le permite al propietario
    entender por que este mes le vino distinto, y es exactamente ahi donde
    llama por telefono:

      - `monto_expensa`: lo que le toco del prorrateo de los gastos.
      - `recargo_mora`: el recargo por lo que venia atrasado. **Es una cuenta
        suya**, no un gasto del consorcio, y por eso no esta en el total de la
        expensa ni en la apertura por rubro.
      - `saldo_a_favor_aplicado`: lo que se le descuento de lo que habia pagado
        de mas en periodos anteriores. Se guarda en **positivo** y se resta;
        guardarlo con signo negativo obligaria a acordarse del signo en cada
        suma.

    `total_a_pagar` no es una columna: se calcula. Guardarlo seria guardar una
    suma que puede quedar desincronizada de sus tres sumandos, y la unica forma
    de detectarlo seria sumar a mano justo la fila que quedo mal.

    ========================================================================
    EL COEFICIENTE TAMBIEN SE COPIA, Y NO ES REDUNDANTE
    ========================================================================

    `coeficiente` guarda el porcentual que tenia la unidad **el dia que se
    liquido**. La unidad ya lo tiene en su propia tabla, pero ese valor puede
    cambiar: un reglamento de propiedad horizontal se modifica, y el sistema
    permite corregir un coeficiente mal cargado. Sin la copia, una expensa de
    hace ocho meses quedaria sin forma de explicarse — el monto no se
    deduciria del coeficiente actual, y nadie podria decir si el error esta en
    el monto o en el coeficiente. Es el mismo criterio que copia los montos por
    rubro: una liquidacion emitida se explica con los datos con los que se
    emitio.
    """

    __tablename__ = "expensa_departamento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    expensa_id: Mapped[int] = mapped_column(
        ForeignKey("expensas.id"),
        nullable=False,
        index=True,
    )

    departamento_id: Mapped[int] = mapped_column(
        ForeignKey("departamentos.id"),
        nullable=False,
        index=True,
    )

    # El porcentual con el que se calculo, copiado. Ver la cabecera.
    coeficiente: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)

    monto_expensa: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Los dos nacen en cero y en cero se quedan mientras nadie se atrase ni
    # pague de mas, que es el caso normal. El `server_default` es lo que
    # permite que el arranque aditivo agregue estas columnas si alguna vez
    # hiciera falta.
    recargo_mora: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )
    saldo_a_favor_aplicado: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )

    expensa = relationship("Expensa", back_populates="por_departamento")
    departamento = relationship("Departamento")

    __table_args__ = (
        # Una unidad aparece una sola vez en una liquidacion.
        UniqueConstraint(
            "expensa_id",
            "departamento_id",
            name="uq_expensa_departamento",
        ),
        # El monto prorrateado puede ser cero: una unidad exenta tiene
        # coeficiente 0% y no paga. Negativo, no.
        CheckConstraint("monto_expensa >= 0", name="ck_ed_monto_no_negativo"),
        CheckConstraint("recargo_mora >= 0", name="ck_ed_recargo_no_negativo"),
        CheckConstraint("saldo_a_favor_aplicado >= 0", name="ck_ed_saldo_no_negativo"),
        CheckConstraint(
            "coeficiente >= 0 AND coeficiente <= 100",
            name="ck_ed_coeficiente_valido",
        ),
        # La consulta de "mi cuenta" y la de deudores: todo lo de ESTA unidad.
        Index("ix_ed_departamento", "departamento_id"),
    )

    @property
    def total_a_pagar(self) -> Decimal:
        """Lo que la unidad tiene que pagar en esta liquidacion.

        El saldo a favor se **resta**: esta guardado en positivo.

        Puede dar cero cuando el saldo a favor cubre todo, y **nunca da
        negativo** porque al liquidar se aplica como maximo lo que se debe; el
        excedente que queda sin usar sigue siendo saldo a favor para el periodo
        siguiente (`F2-T08`). Esa regla la hace cumplir la generacion, no esta
        columna.
        """
        return self.monto_expensa + self.recargo_mora - self.saldo_a_favor_aplicado

    def __repr__(self) -> str:
        return (
            f"<ExpensaDepartamento expensa={self.expensa_id} "
            f"departamento={self.departamento_id} total={self.total_a_pagar}>"
        )

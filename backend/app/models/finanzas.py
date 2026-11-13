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
    Boolean,
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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import expression

from app.database import Base
from app.services import expensas, fondos, pagos, presupuestos, rubros

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
        server_default=text("0"),
    )
    saldo_a_favor_aplicado: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
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


# ===========================================================================
# EL PAGO (`F2-T08`)
# ===========================================================================

_ESTADOS_PAGO_CHECK = ", ".join(f"'{estado}'" for estado in pagos.ESTADOS)
_MEDIOS_CHECK = ", ".join(f"'{medio}'" for medio in pagos.MEDIOS_DE_PAGO)


class Pago(Base):
    """Un pago declarado por el residente, a conciliar por la administracion.

    ========================================================================
    ES UNA DECLARACION HASTA QUE ALGUIEN LA CONFIRMA
    ========================================================================

    Una fila de esta tabla no dice "entro esta plata": dice "alguien dice que
    pago esto". **Solo el estado `confirmado` reduce la deuda** (la regla vive
    en `services/pagos.py`), y para llegar ahi hace falta que una persona de la
    administracion lo coteje contra el extracto bancario. Sin ese paso,
    cualquier captura de pantalla borraria una deuda.

    ========================================================================
    DOS COLUMNAS QUE EL ROADMAP NO PEDIA Y SIN LAS CUALES LA REGLA NO SE
    PUEDE CUMPLIR
    ========================================================================

    `cargado_por_id` y `conciliado_por_id`. La regla de `F2-T07` dice que
    **quien carga un pago no lo concilia**, ni siquiera siendo administrador —
    y el caso que de verdad pasa es el administrador que vive en el edificio.
    Esa regla se escribe por **persona**, no por rol, asi que sin guardar quien
    cargo el pago no hay forma de aplicarla.

    Y `conciliado_por_id` es la contraparte: quien se hizo responsable de decir
    "esta plata entro". Un circuito de dinero sin ese nombre es un circuito que
    no se puede auditar, y la Fase 6 lo va a necesitar.

    ========================================================================
    EL PAGO APUNTA A UNA EXPENSA, Y ESO ES UNA DECISION
    ========================================================================

    `expensa_id` es **obligatorio**: cada pago se imputa a una liquidacion
    concreta. En la realidad alguien transfiere una vez y cubre tres meses, y
    con este modelo eso son tres pagos — uno por expensa.

    Se eligio asi porque es lo trazable: con un "pago a cuenta" que se imputa
    despues, el saldo de una unidad depende de como se repartio ese monto, y
    ese reparto es una decision que quedaria sin registrar. Tres filas con su
    comprobante repetido se entienden solas ocho meses mas tarde. **Lo que
    tiene que hacer la pantalla es que esto sea obvio** y no una sorpresa
    (`F2-T22`).
    """

    __tablename__ = "pagos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    departamento_id: Mapped[int] = mapped_column(
        ForeignKey("departamentos.id"),
        nullable=False,
        index=True,
    )

    expensa_id: Mapped[int] = mapped_column(
        ForeignKey("expensas.id"),
        nullable=False,
        index=True,
    )

    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # La fecha en que se pago, que la pone el residente y **no es la fecha de
    # carga**: se paga el 10 y se sube el comprobante el 12. Las dos cosas se
    # guardan por separado (`creado_en` es la segunda), porque la primera es la
    # que decide si el pago entro en termino.
    fecha: Mapped[date] = mapped_column(Date, nullable=False)

    medio_pago: Mapped[str] = mapped_column(String(24), nullable=False)

    # Mientras no haya almacenamiento propio de archivos, el comprobante es una
    # URL que el residente pega (ya decidido para las fotos de reclamos). Es
    # opcional: un pago en efectivo en la administracion no tiene comprobante
    # digital, y exigirlo haria que se cargue cualquier cosa en el campo.
    comprobante_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    estado: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=pagos.PENDIENTE,
        server_default=pagos.PENDIENTE,
        index=True,
    )

    cargado_por_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"),
        nullable=False,
    )

    conciliado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"),
        nullable=True,
    )
    conciliado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Por que se rechazo, **obligatorio al rechazar** y nulo en cualquier otro
    # caso. Un pago que desaparece sin explicacion es un llamado telefonico
    # garantizado, y los motivos reales son pocos y concretos: el comprobante
    # no se ve, el monto no coincide, la transferencia no aparecio en el
    # extracto. Que el motivo sea obligatorio es lo que convierte el rechazo en
    # algo que el residente puede resolver solo.
    #
    # La columna es anulable porque la mayoria de los pagos no se rechazan; que
    # sea obligatoria **cuando se rechaza** lo garantiza el esquema de entrada,
    # no la base: un CHECK condicional sobre dos columnas seria mas fragil de
    # leer que la regla escrita donde se aplica.
    motivo_rechazo: Mapped[str | None] = mapped_column(Text, nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    departamento = relationship("Departamento")
    expensa = relationship("Expensa")
    cargado_por = relationship("Usuario", foreign_keys=[cargado_por_id])
    conciliado_por = relationship("Usuario", foreign_keys=[conciliado_por_id])

    __table_args__ = (
        # Un pago de cero no es un pago, y uno negativo seria una devolucion —
        # que es otra operacion, con otra autorizacion.
        CheckConstraint("monto > 0", name="ck_pagos_monto_positivo"),
        CheckConstraint(
            f"estado IN ({_ESTADOS_PAGO_CHECK})",
            name="ck_pagos_estado_valido",
        ),
        CheckConstraint(
            f"medio_pago IN ({_MEDIOS_CHECK})",
            name="ck_pagos_medio_valido",
        ),
        # **No hay UNIQUE de (expensa, departamento).** Es deliberado: los
        # pagos parciales estan permitidos, asi que una unidad puede pagar la
        # misma expensa en dos o tres veces. Y un pago rechazado deja su fila,
        # asi que el residente carga otro para la misma expensa.
        #
        # La consulta que mas se hace: los pagos de ESTA unidad por ESTA
        # expensa, para calcular el saldo.
        Index("ix_pagos_departamento_expensa", "departamento_id", "expensa_id"),
        # Y la cola de conciliacion: los pendientes, de la mas vieja a la mas
        # nueva.
        Index("ix_pagos_estado_fecha", "estado", "fecha"),
    )

    @property
    def reduce_la_deuda(self) -> bool:
        """Si este pago efectivamente baja el saldo de la unidad."""
        return pagos.reduce_la_deuda(self.estado)

    @property
    def esta_conciliado(self) -> bool:
        return pagos.esta_conciliado(self.estado)

    def __repr__(self) -> str:
        return (
            f"<Pago id={self.id} departamento={self.departamento_id} "
            f"expensa={self.expensa_id} monto={self.monto} "
            f"estado={self.estado!r}>"
        )


# ===========================================================================
# LOS FONDOS (`F2-T12`)
# ===========================================================================

_TIPOS_MOVIMIENTO_CHECK = ", ".join(
    f"'{tipo}'" for tipo in fondos.TIPOS_DE_MOVIMIENTO
)


class Fondo(Base):
    """Una bolsa de plata separada del flujo corriente de gastos.

    El **fondo de reserva** es el caso obligado — la ley de propiedad
    horizontal lo exige— pero no es el unico: un consorcio junta plata para una
    obra, para renovar el ascensor, para una contingencia. Cada uno es un fondo
    con su propio historial.

    ========================================================================
    POR QUE ESTA SEPARADO DEL GASTO CORRIENTE
    ========================================================================

    Un gasto del mes se reparte entre las unidades y se cobra en la expensa de
    ese mes. La plata de un fondo **ya se cobro**: esta guardada, y gastarla no
    genera una expensa nueva. Mezclar las dos cosas en la misma tabla haria que
    la suma de los gastos de un periodo incluyera plata que no hay que repartir,
    y la expensa saldria mal.

    ========================================================================
    EL SALDO SE CALCULA, NO SE GUARDA
    ========================================================================

    No hay columna `saldo`, y es la decision central del modelo. Un saldo
    guardado hay que actualizarlo en cada movimiento, y el dia que alguien
    inserte un movimiento sin pasar por el endpoint —un script, una
    correccion a mano— el numero queda mal **sin que nada falle**. Un saldo
    calculado no puede desincronizarse: es la suma de los movimientos, y si los
    movimientos estan bien el saldo esta bien.
    """

    __tablename__ = "fondos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    edificio_id: Mapped[int] = mapped_column(
        ForeignKey("edificios.id"),
        nullable=False,
        index=True,
    )

    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Un fondo que ya no se usa no se borra: tiene historial, y el historial de
    # la plata de un consorcio no se tira. Se desactiva, y deja de ofrecerse
    # para movimientos nuevos.
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        # `expression.true()` y NO text("1"): SQLite acepta DEFAULT 1 en una
        # columna booleana y PostgreSQL lo rechaza ("column is of type boolean
        # but default expression is of type integer"). Como el esquema se
        # sincroniza al arrancar, eso tira la aplicacion entera en produccion y
        # anda perfecto en desarrollo. Es el mismo helper que usan `usuarios` y
        # `edificios`, que llevan meses funcionando.
        default=True,
        server_default=expression.true(),
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    edificio = relationship("Edificio")
    movimientos = relationship(
        "MovimientoFondo",
        back_populates="fondo",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Dos fondos con el mismo nombre en el mismo edificio son dos bolsas
        # indistinguibles en cualquier reporte, y nadie se acordaria cual es
        # cual tres meses despues.
        UniqueConstraint("edificio_id", "nombre", name="uq_fondos_nombre"),
    )

    def __repr__(self) -> str:
        return f"<Fondo id={self.id} edificio={self.edificio_id} {self.nombre!r}>"


class MovimientoFondo(Base):
    """Un ingreso o un egreso de un fondo.

    `tipo` es un catalogo cerrado de dos valores (`services/fondos.py`), y el
    **monto siempre es positivo**: el signo lo da el tipo, no el numero.

    Guardar egresos como montos negativos parece mas simple y es la fuente del
    error clasico: un egreso cargado por error en positivo suma en vez de
    restar, y la unica forma de notarlo es que el saldo no cierre. Con un tipo
    explicito, cargar mal el signo es imposible — no hay signo que cargar.
    """

    __tablename__ = "movimientos_fondo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    fondo_id: Mapped[int] = mapped_column(
        ForeignKey("fondos.id"),
        nullable=False,
        index=True,
    )

    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Quien lo registro. En un circuito de dinero, cada movimiento tiene un
    # responsable — es la misma razon por la que un pago guarda quien lo
    # concilio.
    registrado_por_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"),
        nullable=False,
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    fondo = relationship("Fondo", back_populates="movimientos")
    registrado_por = relationship("Usuario")

    __table_args__ = (
        # Un movimiento de cero no es un movimiento. Y negativo no puede ser:
        # el signo lo da el tipo.
        CheckConstraint("monto > 0", name="ck_mov_fondo_monto_positivo"),
        CheckConstraint(
            f"tipo IN ({_TIPOS_MOVIMIENTO_CHECK})",
            name="ck_mov_fondo_tipo_valido",
        ),
        # La consulta del detalle de un fondo: sus movimientos por fecha.
        Index("ix_mov_fondo_fecha", "fondo_id", "fecha"),
    )

    @property
    def con_signo(self) -> Decimal:
        """El monto con el signo que le corresponde, para sumar saldos.

        Es la unica traduccion de tipo a signo que existe en el sistema, y
        existe una sola vez a proposito: repetir `if tipo == "ingreso"` en cada
        consulta es como se termina con un reporte que resta lo que otro suma.
        """
        return fondos.con_signo(self.tipo, self.monto)

    def __repr__(self) -> str:
        return (
            f"<MovimientoFondo fondo={self.fondo_id} "
            f"{self.tipo}={self.monto} {self.fecha}>"
        )


# ===========================================================================
# LA CAJA CHICA (`F2-T13`)
# ===========================================================================


class Caja(Base):
    """La caja chica del edificio, como **sistema de fondo fijo**.

    ========================================================================
    `monto_fijo` ES LA COLUMNA QUE LA DEFINE
    ========================================================================

    No es "cuanta plata tiene": es **el monto al que se repone**. Una caja
    chica tiene un importe asignado, se gasta contra ella durante el mes, y
    cuando baja el responsable rinde los comprobantes y se la devuelve a ese
    importe. Sin esta columna, "reponer la caja" no tiene un objetivo numerico
    contra el cual reponerse.

    El primer diseno de este modelo **no tenia movimientos**: guardaba solo
    "este edificio tiene esta persona responsable". No podia calcular saldo, ni
    rendir cuentas, ni reponerse. El fundamento de la correccion, con las
    fuentes consultadas, esta en `investigaciones/Caja_chica.md`.

    ========================================================================
    UNA CAJA POR EDIFICIO
    ========================================================================

    Y lo garantiza la base. Una caja chica es el efectivo que maneja **una**
    persona para los gastos menores del dia; dos cajas en el mismo edificio no
    son dos cajas chicas, son un fondo mal modelado. Si de verdad hiciera falta
    separar plata para un destino propio, eso es un `Fondo`.
    """

    __tablename__ = "cajas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    edificio_id: Mapped[int] = mapped_column(
        ForeignKey("edificios.id"),
        nullable=False,
    )

    monto_fijo: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Quien tiene el efectivo y rinde los comprobantes. Es **obligatorio**: una
    # caja chica sin responsable es plata de nadie, y la rendicion no tiene a
    # quien pedirsele.
    responsable_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"),
        nullable=False,
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        # `expression.true()` y NO text("1"): SQLite acepta DEFAULT 1 en una
        # columna booleana y PostgreSQL lo rechaza ("column is of type boolean
        # but default expression is of type integer"). Como el esquema se
        # sincroniza al arrancar, eso tira la aplicacion entera en produccion y
        # anda perfecto en desarrollo. Es el mismo helper que usan `usuarios` y
        # `edificios`, que llevan meses funcionando.
        default=True,
        server_default=expression.true(),
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    edificio = relationship("Edificio")
    responsable = relationship("Usuario")
    movimientos = relationship(
        "MovimientoCaja",
        back_populates="caja",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("edificio_id", name="uq_cajas_edificio"),
        # Una caja con monto fijo cero no es una caja: no hay nada que reponer
        # ni contra que medir el disponible.
        CheckConstraint("monto_fijo > 0", name="ck_cajas_monto_fijo_positivo"),
    )

    def __repr__(self) -> str:
        return (
            f"<Caja edificio={self.edificio_id} monto_fijo={self.monto_fijo}>"
        )


class MovimientoCaja(Base):
    """Un movimiento de la caja chica: el libro de registro.

    Mismo patron que `MovimientoFondo` y **los mismos dos tipos**, importados
    del mismo catalogo: es el mismo concepto — entra plata o sale plata— y dos
    tuplas paralelas con los mismos valores son el camino corto a que un
    reporte sume lo que otro resta.

    **Una reposicion es un movimiento de tipo `ingreso`**, no una operacion
    especial ni un campo aparte. Es exactamente como funciona en la practica: la
    reposicion es el movimiento que trae el disponible de vuelta al monto fijo.

    El comprobante todavia no se adjunta — depende de la gestion documental de
    la Fase 7— asi que `descripcion` es por ahora donde queda la constancia en
    texto de contra que se gasto.
    """

    __tablename__ = "movimientos_caja"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    caja_id: Mapped[int] = mapped_column(
        ForeignKey("cajas.id"),
        nullable=False,
        index=True,
    )

    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    registrado_por_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"),
        nullable=False,
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    caja = relationship("Caja", back_populates="movimientos")
    registrado_por = relationship("Usuario")

    __table_args__ = (
        CheckConstraint("monto > 0", name="ck_mov_caja_monto_positivo"),
        CheckConstraint(
            f"tipo IN ({_TIPOS_MOVIMIENTO_CHECK})",
            name="ck_mov_caja_tipo_valido",
        ),
        Index("ix_mov_caja_fecha", "caja_id", "fecha"),
    )

    @property
    def con_signo(self) -> Decimal:
        return fondos.con_signo(self.tipo, self.monto)

    def __repr__(self) -> str:
        return (
            f"<MovimientoCaja caja={self.caja_id} "
            f"{self.tipo}={self.monto} {self.fecha}>"
        )


# ===========================================================================
# PRESUPUESTOS Y FACTURAS (`F2-T14`)
# ===========================================================================
#
# Las dos puntas de la cadena de trazabilidad que el Documento General pide:
#
#     Presupuesto  →  Gasto  →  Factura  →  Pago
#
# El presupuesto es el "antes" (que nos cotizaron y que elegimos) y la factura
# el "despues" (el comprobante de lo que efectivamente se contrato). En el
# medio esta el `Gasto`, que ya existe desde `F2-T01`.
#
# **No hay orden de compra**, y es una decision tomada: la practica formal de
# compras la tiene, pero un consorcio no — el gasto ya cumple ese rol.
# Fundamento en `investigaciones/Presupuestos_y_Facturas.md`.

_ESTADOS_PRESUPUESTO_CHECK = ", ".join(
    f"'{estado}'" for estado in presupuestos.ESTADOS
)


class Presupuesto(Base):
    """Una cotizacion recibida, con la decision que se tomo sobre ella.

    ========================================================================
    EL ESTADO ES LO QUE REGISTRA LA DECISION
    ========================================================================

    Sin estado, tres presupuestos cargados para el mismo arreglo son tres filas
    indistinguibles y **cual se eligio no queda escrito en ningun lado** — que
    es justamente la informacion que un consorcista puede pedir ver.

    ========================================================================
    NO SE EXIGE NINGUNA CANTIDAD
    ========================================================================

    Puede haber cero, uno o diez para el mismo arreglo, y el modelo no objeta
    nada. Ninguna norma argentina exige un minimo de presupuestos antes de
    aprobar un gasto: es buena practica, y lo fija el reglamento de cada
    consorcio. Si alguna vez se pide "a partir de tal monto, exigir tres", eso
    es configuracion del edificio y no una regla del modelo.

    ========================================================================
    `gasto_id` SI ES CLAVE FORANEA REAL, A DIFERENCIA DE `proveedor_id`
    ========================================================================

    La tabla `gastos` **ya existe**, asi que no hay motivo para diferir el
    vinculo: cuando un presupuesto se aprueba y genera un gasto, se liga de una
    vez. Es lo que cierra la comparacion entre **lo que se presupuesto** y **lo
    que finalmente se pago**.

    Es anulable porque un presupuesto puede quedar rechazado y nunca
    convertirse en gasto — y porque ligarlo es un paso posterior a aprobarlo.

    `proveedor_id`, en cambio, sigue siendo un entero suelto: la tabla
    `proveedores` no existe hasta la Fase 7. Mismo criterio que en `Gasto`.
    """

    __tablename__ = "presupuestos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    edificio_id: Mapped[int] = mapped_column(
        ForeignKey("edificios.id"),
        nullable=False,
        index=True,
    )

    # Sin ForeignKey: la tabla destino llega en la Fase 7. Ver `Gasto`.
    proveedor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Que se cotizo. **Obligatoria**, al contrario que en un gasto: un gasto se
    # entiende por su rubro y su monto, pero un presupuesto sin descripcion es
    # un numero sin objeto — y comparar tres numeros sin saber de que son no
    # es comparar nada.
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)

    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    estado: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=presupuestos.PENDIENTE,
        server_default=presupuestos.PENDIENTE,
        index=True,
    )

    gasto_id: Mapped[int | None] = mapped_column(
        ForeignKey("gastos.id"),
        nullable=True,
    )

    # Quien tomo la decision y cuando. Un presupuesto aprobado sin nombre es
    # una decision de nadie, y es la clase de dato que se pide meses despues.
    decidido_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"),
        nullable=True,
    )
    decidido_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    edificio = relationship("Edificio")
    gasto = relationship("Gasto")
    decidido_por = relationship("Usuario")

    __table_args__ = (
        CheckConstraint("monto > 0", name="ck_presupuestos_monto_positivo"),
        CheckConstraint(
            f"estado IN ({_ESTADOS_PRESUPUESTO_CHECK})",
            name="ck_presupuestos_estado_valido",
        ),
        # Un presupuesto rechazado no puede estar ligado a un gasto: diria "no
        # elegimos esto" y "esto es lo que gastamos" a la vez. Lo ataja la base
        # porque es una contradiccion de datos, no una regla de flujo.
        CheckConstraint(
            "gasto_id IS NULL OR estado <> 'rechazado'",
            name="ck_presupuestos_rechazado_sin_gasto",
        ),
        Index("ix_presupuestos_edificio_estado", "edificio_id", "estado"),
    )

    @property
    def esta_decidido(self) -> bool:
        return presupuestos.esta_decidido(self.estado)

    def __repr__(self) -> str:
        return (
            f"<Presupuesto id={self.id} edificio={self.edificio_id} "
            f"monto={self.monto} estado={self.estado!r}>"
        )


class Factura(Base):
    """El comprobante de un gasto real.

    ========================================================================
    SIEMPRE COLGADA DE UN GASTO, Y ESO NO ES OPCIONAL
    ========================================================================

    `gasto_id` es **obligatorio**. Una factura suelta no sirve para nada: lo
    que se audita es el gasto, y la factura es lo que lo respalda. El Documento
    General (6.8) lo dice sin margen: "vinculadas a su gasto correspondiente".

    Por eso tampoco tiene `edificio_id`: el edificio sale del gasto. Repetirlo
    seria poder guardar una factura de un edificio contra un gasto de otro.

    ========================================================================
    CARGAR UNA FACTURA ES OPCIONAL, Y NO TIENE QUE SER UNA FACTURA
    ========================================================================

    **Un gasto sin ninguna fila en esta tabla es un gasto perfectamente
    valido.** Muchos gastos reales de un consorcio no tienen comprobante
    formal: el arreglo que hizo un vecino, el flete que se pago en efectivo.
    Nada en el sistema exige una factura para registrar un gasto, y esta tabla
    existe para **guardar el respaldo cuando lo hay**, no para pedirlo.

    Y lo que se guarda tampoco tiene que ser una factura en el sentido fiscal:
    un recibo, un remito, un ticket. Por eso `numero` **tambien es opcional** —
    un recibo escrito a mano no tiene numero, y exigirlo haria que alguien
    escriba "sin numero" o "1" para poder guardar el dato que si tiene.

    ========================================================================
    `numero` ES TEXTO LIBRE, Y ES UNA DECISION
    ========================================================================

    Una factura argentina real lleva tipo (A/B/C), CUIT del emisor, punto de
    venta, numero correlativo y CAE. **Nada de eso se modela por separado**,
    porque este sistema no tiene —ni tiene planeada en ninguna fase del
    Roadmap— integracion con AFIP: la factura se registra para la trazabilidad
    interna del gasto, no para emitirse ni validarse.

    Separar esos campos seria construir para una integracion que no existe. Se
    guarda el comprobante completo como un texto ("B 0001-00000123"), que es lo
    que alguien busca cuando quiere encontrar una factura.
    """

    __tablename__ = "facturas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    gasto_id: Mapped[int] = mapped_column(
        ForeignKey("gastos.id"),
        nullable=False,
        index=True,
    )

    proveedor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Anulable: un recibo escrito a mano no tiene numero. Ver la cabecera.
    numero: Mapped[str | None] = mapped_column(String(50), nullable=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Mientras no haya almacenamiento propio (Fase 7), un enlace. Mismo
    # criterio que el comprobante de un pago.
    archivo_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    gasto = relationship("Gasto")

    __table_args__ = (
        CheckConstraint("monto > 0", name="ck_facturas_monto_positivo"),
        # La misma factura cargada dos veces contra el mismo gasto es el error
        # de doble carga mas facil de cometer — dos personas archivando el
        # mismo papel— y duplicaria el respaldo de un gasto que es uno solo.
        #
        # **Con `numero` nulo la restriccion no aplica**, y eso es lo correcto:
        # la unicidad sobre una columna anulable admite muchos NULL, tanto en
        # SQLite como en PostgreSQL. Dos recibos sin numero contra el mismo
        # gasto son dos comprobantes distintos y tienen que poder cargarse; lo
        # que se ataja es repetir **un numero**, que es lo que identifica un
        # papel concreto.
        UniqueConstraint("gasto_id", "numero", name="uq_facturas_gasto_numero"),
    )

    def __repr__(self) -> str:
        return (
            f"<Factura {self.numero!r} gasto={self.gasto_id} monto={self.monto}>"
        )

"""Modelos `Fondo`, `MovimientoFondo` y `Caja` — Documento General, secciones
6.5 y 6.6. Un solo archivo para los tres, mismo criterio que
`models/edificio.py` (un archivo por dominio, no uno por tabla): "Fondos"
y "Caja" son el mismo bloque financiero, separado del flujo corriente de
`Gasto`/`Expensa`/`Pago`.

`Caja` sigue el sistema de "fondo fijo" real (investigado en
`documentacion/Caja_chica.md` tras la duda del usuario sobre el primer
diseño): un `monto_fijo` al que se repone, y sus propios movimientos
(`MovimientoCaja`) — sin esto, la caja no podía calcular saldo ni
sostener una rendición de cuentas, que es justamente para lo que sirve
una caja chica.
"""

from datetime import date, datetime, timezone

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import backref, relationship

from app.database import Base


class Fondo(Base):
    """Fondo de reserva u otro fondo especial (ej. "Fondo de Obras") de un
    edificio. El saldo disponible se calcula sumando sus `MovimientoFondo`
    — no se guarda acá, para no tener un número que se pueda desincronizar
    del historial real de movimientos."""

    __tablename__ = "fondos"

    id = Column(Integer, primary_key=True, index=True)
    edificio_id = Column(Integer, ForeignKey("edificios.id"), nullable=False)
    nombre = Column(String, nullable=False)  # ej. "Fondo de Reserva", "Fondo de Obras"
    creado_en = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    edificio = relationship("Edificio", backref="fondos")
    movimientos = relationship("MovimientoFondo", back_populates="fondo", order_by="MovimientoFondo.fecha")


class MovimientoFondo(Base):
    """`tipo` sí es un `CHECK` cerrado (a diferencia de `Gasto.rubro` o
    `Pago.medio_pago`) porque acá solo hay dos valores reales posibles —
    mismo criterio que `Cochera.tipo`."""

    __tablename__ = "movimientos_fondo"
    __table_args__ = (
        CheckConstraint("tipo IN ('ingreso', 'egreso')", name="ck_movimientos_fondo_tipo_valido"),
        CheckConstraint("monto > 0", name="ck_movimientos_fondo_monto_positivo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    fondo_id = Column(Integer, ForeignKey("fondos.id"), nullable=False)
    tipo = Column(String, nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)
    fecha = Column(Date, nullable=False, default=date.today)
    descripcion = Column(Text, nullable=True)
    creado_en = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    fondo = relationship("Fondo", back_populates="movimientos")


class Caja(Base):
    """Caja chica del edificio, con su responsable y el monto fijo al que
    se repone (sistema de fondo fijo — ver `Caja_chica.md`). Un registro
    por edificio; sus movimientos viven en `MovimientoCaja`."""

    __tablename__ = "cajas"
    __table_args__ = (CheckConstraint("monto_fijo > 0", name="ck_cajas_monto_fijo_positivo"),)

    id = Column(Integer, primary_key=True, index=True)
    edificio_id = Column(Integer, ForeignKey("edificios.id"), nullable=False, unique=True)
    responsable_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    monto_fijo = Column(Numeric(12, 2), nullable=False)
    creado_en = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    edificio = relationship("Edificio", backref=backref("caja", uselist=False))
    responsable = relationship("Usuario")
    movimientos = relationship("MovimientoCaja", back_populates="caja", order_by="MovimientoCaja.fecha")


class MovimientoCaja(Base):
    """Ingreso (incluida una reposición) o egreso de la caja chica — mismo
    esqueleto que `MovimientoFondo`. Una reposición no es un campo ni una
    acción especial: es, en los datos, un movimiento de tipo `"ingreso"`
    más, igual que ocurre en la práctica real (ver `Caja_chica.md`)."""

    __tablename__ = "movimientos_caja"
    __table_args__ = (
        CheckConstraint("tipo IN ('ingreso', 'egreso')", name="ck_movimientos_caja_tipo_valido"),
        CheckConstraint("monto > 0", name="ck_movimientos_caja_monto_positivo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    caja_id = Column(Integer, ForeignKey("cajas.id"), nullable=False)
    tipo = Column(String, nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)
    fecha = Column(Date, nullable=False, default=date.today)
    descripcion = Column(Text, nullable=True)
    creado_en = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    caja = relationship("Caja", back_populates="movimientos")

"""Modelos `Expensa` y `ExpensaDetalle` — Documento General, sección 6.1.

`Expensa`: la liquidación de un edificio para un período (mes/año), con el
total. `ExpensaDetalle`: la apertura por rubro dentro de esa expensa — es
lo que el Documento General pide explícitamente como "transparencia de
gasto" (no mostrar solo un monto total, sino cuánto correspondió a cada
rubro: limpieza, seguridad, mantenimiento, etc.).

`ExpensaDepartamento`: cuánto le toca pagar a CADA unidad en esa expensa
puntual — investigado en `Prorrateo.md` (sección 6) antes de agregarlo:
es una foto fija calculada una sola vez al generar la expensa (con
`calcular_prorrateo_periodo()`), nunca recalculada después aunque el
`coeficiente` del departamento cambie — misma práctica que cualquier
sistema de facturación real (una liquidación ya emitida es inmutable).
"""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Expensa(Base):
    """Una por edificio y período — `UniqueConstraint` evita liquidar el
    mismo mes dos veces por error."""

    __tablename__ = "expensas"
    __table_args__ = (
        UniqueConstraint("edificio_id", "anio", "mes", name="uq_expensas_edificio_periodo"),
        CheckConstraint("mes BETWEEN 1 AND 12", name="ck_expensas_mes_valido"),
        CheckConstraint("total > 0", name="ck_expensas_total_positivo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    edificio_id = Column(Integer, ForeignKey("edificios.id"), nullable=False)
    anio = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    total = Column(Numeric(12, 2), nullable=False)
    creado_en = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    edificio = relationship("Edificio", backref="expensas")
    detalles = relationship("ExpensaDetalle", back_populates="expensa", order_by="ExpensaDetalle.rubro")
    por_departamento = relationship("ExpensaDepartamento", back_populates="expensa")


class ExpensaDetalle(Base):
    """Apertura por rubro de una `Expensa` — la suma de sus `monto` tiene
    que dar el `total` de la expensa (se valida cuando exista el servicio
    que genera ambos juntos, no acá a nivel de modelo)."""

    __tablename__ = "expensa_detalle"
    __table_args__ = (CheckConstraint("monto > 0", name="ck_expensa_detalle_monto_positivo"),)

    id = Column(Integer, primary_key=True, index=True)
    expensa_id = Column(Integer, ForeignKey("expensas.id"), nullable=False)
    rubro = Column(String, nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)

    expensa = relationship("Expensa", back_populates="detalles")


class ExpensaDepartamento(Base):
    """Foto fija de lo que le tocó pagar a un departamento en una
    expensa puntual — ver la nota de diseño en `Prorrateo.md`, sección 6.
    `UniqueConstraint`: un departamento tiene como máximo una fila por
    expensa (no tendría sentido dos montos distintos para la misma
    unidad en el mismo período)."""

    __tablename__ = "expensa_departamento"
    __table_args__ = (
        UniqueConstraint("expensa_id", "departamento_id", name="uq_expensa_departamento_unico"),
        CheckConstraint("monto > 0", name="ck_expensa_departamento_monto_positivo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    expensa_id = Column(Integer, ForeignKey("expensas.id"), nullable=False)
    departamento_id = Column(Integer, ForeignKey("departamentos.id"), nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)

    expensa = relationship("Expensa", back_populates="por_departamento")
    departamento = relationship("Departamento", backref="expensas_departamento")

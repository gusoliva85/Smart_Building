"""Modelos `Expensa` y `ExpensaDetalle` — Documento General, sección 6.1.

`Expensa`: la liquidación de un edificio para un período (mes/año), con el
total. `ExpensaDetalle`: la apertura por rubro dentro de esa expensa — es
lo que el Documento General pide explícitamente como "transparencia de
gasto" (no mostrar solo un monto total, sino cuánto correspondió a cada
rubro: limpieza, seguridad, mantenimiento, etc.).

Todavía sin la distribución por departamento (cuánto le toca pagar a cada
unidad según su coeficiente) — el propio Roadmap la deja para la tarea de
"servicio de prorrateo automático" / "generación de expensa mensual", más
adelante en esta misma fase. Agregar ese campo ahora sería resolver un
problema que todavía no le toca el turno.
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

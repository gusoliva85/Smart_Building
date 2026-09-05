"""Modelo `Pago` — Documento General, sección 6.2.

Registra un pago real de un departamento contra una expensa puntual.
Soporta pago parcial o total simplemente por no forzar `monto == total de
la expensa` a nivel de modelo — la conciliación real (si con este pago la
expensa queda saldada o sigue parcial) es lógica de la tarea de
"registro de pagos y conciliación", más adelante en esta misma fase, no
algo que el modelo decida por sí solo.
"""

from datetime import date, datetime, timezone

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.database import Base


class Pago(Base):
    """`medio_pago` queda como texto libre (igual que `Gasto.rubro`) — el
    Documento General da ejemplos ("transferencia, efectivo, débito") sin
    fijar una lista cerrada, a diferencia de `Cochera.tipo` que sí tiene
    solo dos valores reales posibles. `comprobante_url` es opcional y
    todavía no tiene un endpoint de carga de archivos detrás (llega con
    Gestión documental, Fase 7) — por ahora es solo un texto/URL suelto."""

    __tablename__ = "pagos"
    __table_args__ = (CheckConstraint("monto > 0", name="ck_pagos_monto_positivo"),)

    id = Column(Integer, primary_key=True, index=True)
    departamento_id = Column(Integer, ForeignKey("departamentos.id"), nullable=False)
    expensa_id = Column(Integer, ForeignKey("expensas.id"), nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)
    fecha = Column(Date, nullable=False, default=date.today)
    medio_pago = Column(String, nullable=False)
    comprobante_url = Column(String, nullable=True)
    creado_en = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    departamento = relationship("Departamento", backref="pagos")
    expensa = relationship("Expensa", backref="pagos")

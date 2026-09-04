"""Modelo del dominio "Gastos" — Documento General, sección 6; Documento
Técnico, sección 8. Primer modelo de la Fase 2: registra un gasto real del
edificio, la materia prima que después reparte `services/finanzas.py`
(Fase 2, Tarea 1) entre los departamentos.
"""

from datetime import date, datetime, timezone

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Gasto(Base):
    """Pertenece siempre a un edificio. `proveedor_id`/`activo_id` quedan
    como columnas sueltas (sin `ForeignKey` real todavía, porque esas
    tablas no existen hasta las Fases 7 y 4 respectivamente) — el vínculo
    real se cablea cuando cada una llegue, tal como lo anticipa el
    Roadmap. Hasta entonces son solo un número opcional sin validar."""

    __tablename__ = "gastos"
    __table_args__ = (CheckConstraint("monto > 0", name="ck_gastos_monto_positivo"),)

    id = Column(Integer, primary_key=True, index=True)
    edificio_id = Column(Integer, ForeignKey("edificios.id"), nullable=False)

    rubro = Column(String, nullable=False)  # ej. "Limpieza", "Ascensor" — texto libre por ahora
    monto = Column(Numeric(12, 2), nullable=False)
    fecha = Column(Date, nullable=False, default=date.today)
    descripcion = Column(Text, nullable=True)

    proveedor_id = Column(Integer, nullable=True)  # se vuelve FK real recién en la Fase 7
    activo_id = Column(Integer, nullable=True)  # se vuelve FK real recién en la Fase 4

    creado_en = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    edificio = relationship("Edificio", backref="gastos")

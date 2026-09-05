"""Modelos `Presupuesto` y `Factura` — Documento General, secciones 6.7 y
6.8. Sostienen el tramo "presupuesto → gasto → factura" de la
trazabilidad completa que pide el Documento General — investigado y
documentado en `documentacion/Presupuestos_y_Facturas.md` antes de
escribir este archivo (flujo simplificado respecto al procure-to-pay de
manual, sin `OrdenCompra` propia; campos de AFIP deliberadamente NO
modelados porque este proyecto no integra con AFIP en ninguna fase).
"""

from datetime import date, datetime, timezone

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Presupuesto(Base):
    """Cotización de un proveedor para un trabajo/compra, cargada para
    comparar antes de aprobar un gasto (Documento General 6.7) — no hay
    cantidad mínima ni máxima exigida por ley, así que el modelo no la
    fuerza. `estado` es lo que registra cuál de varios presupuestos se
    eligió; `gasto_id` queda `NULL` hasta que uno se apruebe y se
    convierta en el `Gasto` real (un presupuesto rechazado nunca lo
    tiene)."""

    __tablename__ = "presupuestos"
    __table_args__ = (
        CheckConstraint("estado IN ('pendiente', 'aprobado', 'rechazado')", name="ck_presupuestos_estado_valido"),
        CheckConstraint("monto > 0", name="ck_presupuestos_monto_positivo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    edificio_id = Column(Integer, ForeignKey("edificios.id"), nullable=False)
    proveedor_id = Column(Integer, nullable=True)  # FK real recién en la Fase 7, igual que Gasto.proveedor_id
    descripcion = Column(Text, nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)
    fecha = Column(Date, nullable=False, default=date.today)
    estado = Column(String, nullable=False, default="pendiente")
    gasto_id = Column(Integer, ForeignKey("gastos.id"), nullable=True)
    creado_en = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    edificio = relationship("Edificio", backref="presupuestos")
    gasto = relationship("Gasto", backref="presupuestos")


class Factura(Base):
    """Factura de un gasto, para archivo y trazabilidad interna — NO un
    comprobante fiscal (sin CAE/tipo/punto de venta: este proyecto no
    integra con AFIP). `gasto_id` es obligatorio: el Documento General
    6.8 pide la factura "vinculada a su gasto correspondiente", nunca
    suelta."""

    __tablename__ = "facturas"
    __table_args__ = (CheckConstraint("monto > 0", name="ck_facturas_monto_positivo"),)

    id = Column(Integer, primary_key=True, index=True)
    gasto_id = Column(Integer, ForeignKey("gastos.id"), nullable=False)
    proveedor_id = Column(Integer, nullable=True)  # FK real recién en la Fase 7
    numero = Column(String, nullable=False)  # texto libre, ej. "B 0001-00000123"
    monto = Column(Numeric(12, 2), nullable=False)
    fecha = Column(Date, nullable=False, default=date.today)
    archivo_url = Column(String, nullable=True)  # sin carga de archivos real hasta Gestión documental (Fase 7)
    creado_en = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    gasto = relationship("Gasto", backref="facturas")

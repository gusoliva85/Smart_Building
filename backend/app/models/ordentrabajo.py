"""Modelos del dominio "Órdenes de trabajo" — Documento General, sección
10; Documento Técnico, sección 12. Unidad central del módulo de
mantenimiento: se origina de tres formas (manual, automática por
vencimiento de un `Activo`, o desde un `Reclamo`) — Documento General
10.2. Un archivo propio, no `models/reclamo.py`, aunque ambos dominios se
implementen juntos en esta fase: son dos entidades separadas con su
propio ciclo de vida.

Estados PROPIOS, distintos de los de `Reclamo` (Fase 3, Tarea 1): acá el
flujo es `pendiente → en_curso → resuelta` (Documento Técnico, sección
12), sin "asignado" ni "cerrado" — se valida contra
`services/reclamos.py::ESTADOS_OT`/`TIPOS_OT`, nunca una segunda lista de
valores a mano.
"""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.services.reclamos import ESTADOS_OT, PRIORIDADES, TIPOS_OT

_TIPOS_OT_SQL = ", ".join(f"'{tipo}'" for tipo in TIPOS_OT)
_ESTADOS_OT_SQL = ", ".join(f"'{estado}'" for estado in ESTADOS_OT)
_PRIORIDADES_SQL = ", ".join(f"'{prioridad}'" for prioridad in PRIORIDADES)


class OrdenTrabajo(Base):
    """`activo_id` queda como entero suelto sin `ForeignKey` real —
    mismo criterio que `Gasto.activo_id`/`Gasto.proveedor_id` (Fase 2):
    una columna sin FK no depende de que la tabla destino ya exista, y
    `Activo` recién llega en la Fase 4. Se conecta de verdad ahí, en el
    modelo (agregarle `ForeignKey`/`relationship`), sin tocar la base ya
    creada.

    Asignación — decisión consultada con el usuario, 2026-09-09:
    `encargado_id` (FK real a `Usuario` con rol `encargado`, que ya tiene
    login desde la Fase 1) y/o `proveedor_id` (entero suelto, mismo
    criterio que `activo_id` — se conecta de verdad recién con el
    `Proveedor` real de la Fase 7). Ninguno de los dos es obligatorio al
    crear la orden (puede nacer `pendiente` sin asignar todavía), pero
    hace falta al menos uno para pasar a `en_curso` (regla de aplicación,
    se valida en el endpoint que cambia el estado, no acá a nivel de
    modelo — igual que el resto de las reglas de transición del proyecto)."""

    __tablename__ = "ordenes_trabajo"
    __table_args__ = (
        CheckConstraint(f"tipo IN ({_TIPOS_OT_SQL})", name="ck_ot_tipo_valido"),
        CheckConstraint(f"estado IN ({_ESTADOS_OT_SQL})", name="ck_ot_estado_valido"),
        CheckConstraint(f"prioridad IN ({_PRIORIDADES_SQL})", name="ck_ot_prioridad_valida"),
        CheckConstraint("costo IS NULL OR costo >= 0", name="ck_ot_costo_no_negativo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    edificio_id = Column(Integer, ForeignKey("edificios.id"), nullable=False)
    espacio_comun_id = Column(Integer, ForeignKey("espacios_comunes.id"), nullable=True)
    activo_id = Column(Integer, nullable=True)  # se vuelve FK real recién en la Fase 4
    reclamo_id = Column(Integer, ForeignKey("reclamos.id"), nullable=True)

    tipo = Column(String, nullable=False)
    prioridad = Column(String, nullable=False)  # mismas PRIORIDADES que Reclamo (leve/medio/critico)
    estado = Column(String, nullable=False, server_default="pendiente")
    descripcion = Column(Text, nullable=True)
    costo = Column(Numeric(12, 2), nullable=True)

    encargado_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    proveedor_id = Column(Integer, nullable=True)  # se vuelve FK real recién en la Fase 7

    creado_en = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_cierre = Column(DateTime, nullable=True)

    edificio = relationship("Edificio", backref="ordenes_trabajo")
    espacio_comun = relationship("EspacioComun", backref="ordenes_trabajo")
    reclamo = relationship("Reclamo", backref="ordenes_trabajo")
    encargado = relationship("Usuario")
    evidencias = relationship("OtEvidencia", back_populates="orden_trabajo", order_by="OtEvidencia.id")


class OtEvidencia(Base):
    """Foto de antes/después de la intervención — mismo criterio que
    `ReclamoFoto`: solo la URL, sin upload real de archivos todavía (no
    hay ninguno en el proyecto)."""

    __tablename__ = "ot_evidencias"
    __table_args__ = (CheckConstraint("momento IN ('antes', 'despues')", name="ck_ot_evidencias_momento_valido"),)

    id = Column(Integer, primary_key=True, index=True)
    orden_trabajo_id = Column(Integer, ForeignKey("ordenes_trabajo.id"), nullable=False)
    url = Column(String, nullable=False)
    momento = Column(String, nullable=False)

    subido_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    creado_en = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    orden_trabajo = relationship("OrdenTrabajo", back_populates="evidencias")
    subido_por = relationship("Usuario")

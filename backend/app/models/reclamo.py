"""Modelos del dominio "Reclamos" — Documento General, sección 11;
Documento Técnico, sección 13. `Reclamo`: lo que carga un propietario o
inquilino al reportar un problema. `ReclamoFoto`: sus fotos de respaldo,
en tabla propia — mismo criterio que `OtEvidencia`/`ActivoFoto` (Fases 3 y
4), nunca una lista de URLs aplastada en un solo campo de texto.
`ReclamoComentario`: el hilo de conversación entre quien reclama y quien
lo gestiona.

El flujo de estados y los niveles de prioridad ya se definieron y
probaron en Python puro antes de este modelo (Fase 3, Tarea 1,
`services/reclamos.py`) — acá solo se valida contra esas mismas
constantes, nunca se repite la lista de valores válidos a mano en un
segundo lugar.
"""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.services.reclamos import ESTADOS, PRIORIDADES

_ESTADOS_SQL = ", ".join(f"'{estado}'" for estado in ESTADOS)
_PRIORIDADES_SQL = ", ".join(f"'{prioridad}'" for prioridad in PRIORIDADES)


class Reclamo(Base):
    """Siempre pertenece a un edificio. El objetivo puntual es UNA de tres
    opciones reales (Documento General 11.1): su propia unidad
    (`departamento_id`), un espacio común (`espacio_comun_id`), o ninguna
    de las dos — "el edificio en general". Nunca las dos a la vez (ver
    `CheckConstraint` de abajo): un reclamo no es sobre una unidad Y un
    espacio común al mismo tiempo."""

    __tablename__ = "reclamos"
    __table_args__ = (
        CheckConstraint(f"prioridad IN ({_PRIORIDADES_SQL})", name="ck_reclamos_prioridad_valida"),
        CheckConstraint(f"estado IN ({_ESTADOS_SQL})", name="ck_reclamos_estado_valido"),
        CheckConstraint(
            "departamento_id IS NULL OR espacio_comun_id IS NULL",
            name="ck_reclamos_un_solo_objetivo",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    edificio_id = Column(Integer, ForeignKey("edificios.id"), nullable=False)
    departamento_id = Column(Integer, ForeignKey("departamentos.id"), nullable=True)
    espacio_comun_id = Column(Integer, ForeignKey("espacios_comunes.id"), nullable=True)

    descripcion = Column(Text, nullable=False)
    prioridad = Column(String, nullable=False)
    estado = Column(String, nullable=False, server_default="recibido")

    creado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    creado_en = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    # Documento General 11.7: tiempo de resolución = creado_en → cerrado_en
    # (el CIERRE, no "resuelto" — ese todavía puede reabrirse). Se fija una
    # sola vez, al llegar al estado terminal "cerrado" (`routers/reclamos.py`).
    cerrado_en = Column(DateTime, nullable=True)

    edificio = relationship("Edificio", backref="reclamos")
    departamento = relationship("Departamento", backref="reclamos")
    espacio_comun = relationship("EspacioComun", backref="reclamos")
    creado_por = relationship("Usuario")
    fotos = relationship("ReclamoFoto", back_populates="reclamo", order_by="ReclamoFoto.id")
    comentarios = relationship("ReclamoComentario", back_populates="reclamo", order_by="ReclamoComentario.creado_en")


class ReclamoFoto(Base):
    """Una foto de respaldo de un reclamo — solo la URL (mismo criterio
    que `Pago.comprobante_url`): no hay ningún endpoint de carga de
    archivos real en el proyecto todavía, ni siquiera `Documento` (Fase 7)
    cubre esto — esa tabla es para documentos del edificio, no para
    evidencia de reclamos. Se resuelve de verdad cuando la Gestión
    documental construya un upload real y este campo se cablee a eso."""

    __tablename__ = "reclamo_fotos"

    id = Column(Integer, primary_key=True, index=True)
    reclamo_id = Column(Integer, ForeignKey("reclamos.id"), nullable=False)
    url = Column(String, nullable=False)
    creado_en = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    reclamo = relationship("Reclamo", back_populates="fotos")


class ReclamoComentario(Base):
    """Hilo de comentarios de un reclamo. Cualquiera con acceso al reclamo
    (quien lo creó, Administrador o Encargado del edificio) puede comentar
    en cualquier estado — Fase 3, Tarea "ciclo de vida del reclamo"."""

    __tablename__ = "reclamo_comentarios"

    id = Column(Integer, primary_key=True, index=True)
    reclamo_id = Column(Integer, ForeignKey("reclamos.id"), nullable=False)
    autor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    texto = Column(Text, nullable=False)
    creado_en = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    reclamo = relationship("Reclamo", back_populates="comentarios")
    autor = relationship("Usuario")

"""Esquemas Pydantic del router de órdenes de trabajo (`routers/ordentrabajo.py`)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from app.services.reclamos import PRIORIDADES, TIPOS_OT


class OrdenTrabajoDesdeReclamoEntrada(BaseModel):
    """Generar una OT a partir de un reclamo existente (Documento General
    10.2). `prioridad`/`descripcion` heredan del reclamo si no se
    especifican — normalmente alcanza con elegir el `tipo` de trabajo y,
    opcionalmente, a quién asignarlo ya de una."""

    tipo: str
    prioridad: str | None = None
    descripcion: str | None = None
    encargado_id: int | None = None
    proveedor_id: int | None = None

    @field_validator("tipo")
    @classmethod
    def _validar_tipo(cls, valor):
        if valor not in TIPOS_OT:
            raise ValueError(f"Tipo inválido: {valor!r}. Válidos: {TIPOS_OT}")
        return valor

    @field_validator("prioridad")
    @classmethod
    def _validar_prioridad(cls, valor):
        if valor is not None and valor not in PRIORIDADES:
            raise ValueError(f"Prioridad inválida: {valor!r}. Válidas: {PRIORIDADES}")
        return valor


class OtEvidenciaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    momento: str
    subido_por_id: int
    creado_en: datetime


class OrdenTrabajoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    edificio_id: int
    espacio_comun_id: int | None
    activo_id: int | None
    reclamo_id: int | None
    tipo: str
    prioridad: str
    estado: str
    descripcion: str | None
    costo: Decimal | None
    encargado_id: int | None
    proveedor_id: int | None
    creado_en: datetime
    fecha_inicio: datetime | None
    fecha_cierre: datetime | None
    evidencias: list[OtEvidenciaSalida]

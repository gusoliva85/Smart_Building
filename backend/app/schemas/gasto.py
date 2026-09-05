"""Esquemas Pydantic del CRUD de `Gasto` (`routers/financiero.py`)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class GastoEntrada(BaseModel):
    rubro: str
    monto: float = Field(gt=0)
    fecha: date
    descripcion: str | None = None
    proveedor_id: int | None = None  # sin FK real hasta la Fase 7
    activo_id: int | None = None  # sin FK real hasta la Fase 4


class GastoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    edificio_id: int
    rubro: str
    monto: float
    fecha: date
    descripcion: str | None
    proveedor_id: int | None
    activo_id: int | None
    creado_en: datetime

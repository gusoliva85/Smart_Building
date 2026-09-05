"""Esquemas Pydantic del router financiero (`routers/financiero.py`)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExpensaGeneracionEntrada(BaseModel):
    anio: int = Field(ge=2000, le=2100)
    mes: int = Field(ge=1, le=12)


class ExpensaDetalleSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rubro: str
    monto: float


class ExpensaDepartamentoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    departamento_id: int
    monto: float


class ExpensaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    edificio_id: int
    anio: int
    mes: int
    total: float
    creado_en: datetime
    detalles: list[ExpensaDetalleSalida]
    por_departamento: list[ExpensaDepartamentoSalida]

"""Esquemas Pydantic del CRUD de `Presupuesto`/`Factura` (`routers/financiero.py`)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PresupuestoEntrada(BaseModel):
    descripcion: str
    monto: float = Field(gt=0)
    fecha: date | None = None
    proveedor_id: int | None = None  # sin FK real hasta la Fase 7


class PresupuestoEstadoEntrada(BaseModel):
    """Aprobar vincula el presupuesto a un `Gasto` real (`gasto_id`);
    rechazar no necesita ninguno."""

    estado: str
    gasto_id: int | None = None

    @field_validator("estado")
    @classmethod
    def _validar_estado(cls, valor):
        if valor not in ("aprobado", "rechazado"):
            raise ValueError("estado debe ser 'aprobado' o 'rechazado'")
        return valor


class PresupuestoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    edificio_id: int
    proveedor_id: int | None
    descripcion: str
    monto: float
    fecha: date
    estado: str
    gasto_id: int | None
    creado_en: datetime


class FacturaEntrada(BaseModel):
    gasto_id: int
    proveedor_id: int | None = None
    numero: str
    monto: float = Field(gt=0)
    fecha: date | None = None
    archivo_url: str | None = None


class FacturaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    gasto_id: int
    proveedor_id: int | None
    numero: str
    monto: float
    fecha: date
    archivo_url: str | None
    creado_en: datetime

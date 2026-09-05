"""Esquemas Pydantic del CRUD de `Fondo`/`MovimientoFondo`/`Caja`/
`MovimientoCaja` (`routers/financiero.py`)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validar_tipo_movimiento(valor):
    if valor not in ("ingreso", "egreso"):
        raise ValueError("tipo debe ser 'ingreso' o 'egreso'")
    return valor


class FondoEntrada(BaseModel):
    nombre: str


class MovimientoFondoEntrada(BaseModel):
    tipo: str
    monto: float = Field(gt=0)
    fecha: date | None = None
    descripcion: str | None = None

    _validar_tipo = field_validator("tipo")(_validar_tipo_movimiento)


class MovimientoFondoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fondo_id: int
    tipo: str
    monto: float
    fecha: date
    descripcion: str | None
    creado_en: datetime


class FondoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    edificio_id: int
    nombre: str
    saldo: float
    creado_en: datetime


class CajaEntrada(BaseModel):
    responsable_id: int
    monto_fijo: float = Field(gt=0)


class CajaConfiguracion(BaseModel):
    responsable_id: int | None = None
    monto_fijo: float | None = Field(default=None, gt=0)


class CajaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    edificio_id: int
    responsable_id: int
    monto_fijo: float
    saldo: float
    creado_en: datetime


class MovimientoCajaEntrada(BaseModel):
    tipo: str
    monto: float = Field(gt=0)
    fecha: date | None = None
    descripcion: str | None = None

    _validar_tipo = field_validator("tipo")(_validar_tipo_movimiento)


class MovimientoCajaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    caja_id: int
    tipo: str
    monto: float
    fecha: date
    descripcion: str | None
    creado_en: datetime

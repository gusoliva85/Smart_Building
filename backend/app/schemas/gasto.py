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


class GastoEdicion(BaseModel):
    """`PATCH /api/edificios/{id}/gastos/{id}` — corregir un gasto ya
    cargado (error de tipeo en el rubro, monto mal cargado, fecha
    equivocada). Todos los campos opcionales (`exclude_unset` en el
    router: solo se toca lo que venga en el body, mismo criterio que
    `EdificioConfiguracion`/`UsuarioEdicion`).

    Nunca reabre una expensa ya generada: `ExpensaDetalle`/
    `ExpensaDepartamento` son una foto fija tomada al momento de generar
    (Prorrateo.md, sección 6) — corregir el `Gasto` de origen después
    solo afecta a la PRÓXIMA expensa que se genere para ese período, no
    reescribe una ya emitida."""

    rubro: str | None = None
    monto: float | None = Field(default=None, gt=0)
    fecha: date | None = None
    descripcion: str | None = None


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

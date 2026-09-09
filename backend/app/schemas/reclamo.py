"""Esquemas Pydantic del router de reclamos (`routers/reclamos.py`)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.services.reclamos import ESTADOS, PRIORIDADES, tiempo_resolucion_reclamo


class ReclamoEntrada(BaseModel):
    """El objetivo puntual es UNA de tres opciones reales (Documento
    General 11.1): `departamento_id`, `espacio_comun_id`, o ninguno de
    los dos ("el edificio en general") — nunca los dos a la vez, mismo
    `CheckConstraint` del modelo, validado acá también para devolver un
    422 claro en vez de esperar al error de la base."""

    departamento_id: int | None = None
    espacio_comun_id: int | None = None
    descripcion: str
    prioridad: str
    fotos: list[str] = Field(default_factory=list)

    @field_validator("prioridad")
    @classmethod
    def _validar_prioridad(cls, valor):
        if valor not in PRIORIDADES:
            raise ValueError(f"Prioridad inválida: {valor!r}. Válidas: {PRIORIDADES}")
        return valor

    @field_validator("espacio_comun_id")
    @classmethod
    def _validar_un_solo_objetivo(cls, valor, info):
        if valor is not None and info.data.get("departamento_id") is not None:
            raise ValueError("Un reclamo es sobre la unidad O el espacio común, nunca los dos a la vez")
        return valor


class ReclamoEstadoEntrada(BaseModel):
    estado: str

    @field_validator("estado")
    @classmethod
    def _validar_estado(cls, valor):
        if valor not in ESTADOS:
            raise ValueError(f"Estado inválido: {valor!r}. Válidos: {ESTADOS}")
        return valor


class ReclamoComentarioEntrada(BaseModel):
    texto: str


class ReclamoComentarioSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    autor_id: int
    texto: str
    creado_en: datetime


class ReclamoFotoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str


class ReclamoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    edificio_id: int
    departamento_id: int | None
    espacio_comun_id: int | None
    descripcion: str
    prioridad: str
    estado: str
    creado_por_id: int
    creado_en: datetime
    cerrado_en: datetime | None
    fotos: list[ReclamoFotoSalida]
    comentarios: list[ReclamoComentarioSalida]

    @computed_field
    @property
    def tiempo_resolucion_segundos(self) -> int | None:
        """Documento General 11.7 — `None` mientras el reclamo siga
        abierto (todavía no llegó a `cerrado`)."""
        delta = tiempo_resolucion_reclamo(self)
        return int(delta.total_seconds()) if delta is not None else None

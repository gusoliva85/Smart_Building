"""Esquemas Pydantic del router financiero (`routers/financiero.py`)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class MedioPagoSalida(BaseModel):
    """CBU/alias del edificio para transferir por fuera de la plataforma
    — sin QR (decisión final del usuario, ver Pagos_y_Conciliacion.md):
    cada dato se copia por separado y el pago se hace desde la app del
    banco/billetera del propio usuario."""

    cbu: str | None
    alias_cbu: str | None


class MiExpensaSalida(BaseModel):
    """Una expensa puntual vista desde la unidad — Documento General 6.2,
    "estado de cuenta por unidad". `saldo` descuenta solo los `Pago` ya
    `confirmado`s, nunca los `pendiente` (todavía no verificados)."""

    expensa_id: int
    anio: int
    mes: int
    monto: float
    pagado_confirmado: float
    saldo: float


class MiDepartamentoSalida(BaseModel):
    departamento_id: int
    identificador: str
    edificio_id: int
    edificio_nombre: str
    expensas: list[MiExpensaSalida]


class PagoEntrada(BaseModel):
    """Alta de un pago por el propio propietario/inquilino — nunca elige
    "de qué piso" navegando el edificio: `departamento_id` tiene que ser
    una de SUS propias unidades (`GET /api/mis-departamentos`), validado
    en el router, no acá."""

    departamento_id: int
    expensa_id: int
    monto: float = Field(gt=0)
    fecha: date
    medio_pago: str
    comprobante_url: str | None = None


class PagoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    departamento_id: int
    expensa_id: int
    monto: float
    fecha: date
    medio_pago: str
    comprobante_url: str | None
    estado: str
    creado_en: datetime


class ExpensaImpagaSalida(BaseModel):
    expensa_id: int
    anio: int
    mes: int
    saldo: float


class DeudorSalida(BaseModel):
    """Documento Técnico, sección 5.2: vista calculada, nunca una tabla
    propia. `meses_atraso` es lo que alimenta `deudaSeverity()` en la
    Fase 5: 1 mes → amarillo, más de 1 mes → rojo (Documento General 6.3)."""

    departamento_id: int
    identificador: str
    propietario_id: int | None
    inquilino_id: int | None
    deuda_total: float
    meses_atraso: int
    expensas_impagas: list[ExpensaImpagaSalida]


class RecaudadoPeriodoSalida(BaseModel):
    """Un período (expensa) del edificio: cuánto se esperaba cobrar
    (`Expensa.total`) contra cuánto se cobró de verdad (`Pago`
    `confirmado`, nunca `pendiente`)."""

    anio: int
    mes: int
    esperado: float
    recaudado: float


class GastoPorRubroPeriodoSalida(BaseModel):
    rubro: str
    anio: int
    mes: int
    monto: float


class ReporteFinancieroSalida(BaseModel):
    """`GET /api/edificios/{id}/reportes/financiero` — Documento Técnico,
    sección 8: la data cruda para Analítica (Fase 6), consolidando en un
    solo lugar lo que ya calculan otros endpoints de esta fase (nunca
    recalculado desde cero)."""

    recaudado_vs_esperado: list[RecaudadoPeriodoSalida]
    gastos_por_rubro: list[GastoPorRubroPeriodoSalida]
    deuda_total_actual: float
    cantidad_deudores: int


class PagoEstadoEntrada(BaseModel):
    """Un Administrador solo puede llevar un pago a `confirmado` o
    `rechazado` — nunca de vuelta a `pendiente` a mano (ese es el estado
    inicial, no un destino)."""

    estado: str

    @field_validator("estado")
    @classmethod
    def _validar_estado(cls, valor):
        if valor not in ("confirmado", "rechazado"):
            raise ValueError("estado debe ser 'confirmado' o 'rechazado'")
        return valor

"""Esquemas Pydantic del router de edificios."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.autorizacion import ROLES
from app.services.edificios import MAXIMO_UNIDADES_POR_PISO


def _validar_lista_roles(valor):
    if valor is None:
        return valor
    invalidos = [r for r in valor if r not in ROLES]
    if invalidos:
        raise ValueError(f"Roles inválidos: {invalidos}. Roles válidos: {ROLES}")
    return valor


class EdificioEntrada(BaseModel):
    nombre: str
    direccion: str
    cp: str | None = None
    cuit: str | None = None
    admin_consorcio_id: int | None = None

    # Geocodificados en el frontend (Leaflet + Nominatim) al completar
    # Dirección + CP — opcionales acá porque el alta no debe bloquearse si
    # el geocoder no encontró nada (dirección nueva, o simplemente falló).
    latitud: float | None = None
    longitud: float | None = None

    # Validados en el borde de la API (Documento Técnico, sección 19): un
    # valor fuera de rango nunca llega a services/edificios.py.
    cantidad_pisos: int = Field(ge=1)
    unidades_por_piso: int = Field(ge=1, le=MAXIMO_UNIDADES_POR_PISO)

    dias_vencimiento_expensas: int = 10
    recargo_mora_porcentual: int = 0


class EdificioConfiguracion(BaseModel):
    """Cuerpo de `PATCH /api/edificios/{id}` — Documento General, sección 5.2.
    Todos los campos son opcionales: solo se cambia lo que venga en el body
    (`exclude_unset`), nunca se pisa un valor existente con `None` por error."""

    contacto_emergencia_nombre: str | None = None
    contacto_emergencia_telefono: str | None = None
    dias_vencimiento_expensas: int | None = Field(default=None, ge=1)
    recargo_mora_porcentual: int | None = Field(default=None, ge=0)
    roles_habilitados: list[str] | None = None

    _validar_roles = field_validator("roles_habilitados")(_validar_lista_roles)


class DepartamentoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    identificador: str
    m2: float | None
    ocupado: bool
    propietario_id: int | None
    inquilino_id: int | None


class PisoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    orden: int
    departamentos: list[DepartamentoSalida]


class EdificioResumenSalida(BaseModel):
    """Usado SOLO por el listado (`GET /api/edificios`) — a diferencia de
    `EdificioSalida`, no trae `pisos`/`departamentos` completos (eso
    obligaría a cargar la estructura entera de TODOS los edificios del
    portfolio para mostrar apenas "N pisos · M unidades" de cada uno).
    `cantidad_pisos`/`cantidad_unidades` llegan ya calculados por el
    propio router con un `COUNT` en la base, sin traer una sola fila de
    piso o departamento."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    direccion: str
    cp: str | None
    cuit: str | None
    admin_consorcio_id: int | None
    activo: bool
    cantidad_pisos: int
    cantidad_unidades: int


class EdificioSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    direccion: str
    cp: str | None
    cuit: str | None
    latitud: float | None
    longitud: float | None
    admin_consorcio_id: int | None
    dias_vencimiento_expensas: int
    recargo_mora_porcentual: int
    contacto_emergencia_nombre: str | None
    contacto_emergencia_telefono: str | None
    activo: bool
    pisos: list[PisoSalida]

    roles_habilitados: list[str]

    @field_validator("roles_habilitados", mode="before")
    @classmethod
    def _parsear_roles(cls, valor):
        if valor is None:
            return list(ROLES)
        if isinstance(valor, str):
            return valor.split(",") if valor else list(ROLES)
        return valor


class PisoEntrada(BaseModel):
    numero: str
    orden: int


class DepartamentoEntrada(BaseModel):
    piso_id: int
    identificador: str
    m2: float | None = None


class DepartamentoAsignacion(BaseModel):
    """`exclude_unset` distingue "no tocar este campo" de "desvincular"
    (mandar el campo explícitamente en `null`) — mismo patrón ya usado en
    `UsuarioEdicion`."""

    propietario_id: int | None = None
    inquilino_id: int | None = None


class CocheraEntrada(BaseModel):
    numero: str
    tipo: str
    departamento_id: int | None = None

    @field_validator("tipo")
    @classmethod
    def _validar_tipo(cls, valor):
        if valor not in ("fija", "rotativa"):
            raise ValueError("tipo debe ser 'fija' o 'rotativa'")
        return valor


class CocheraSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    tipo: str
    departamento_id: int | None


class EspacioComunEntrada(BaseModel):
    nombre: str
    capacidad: int | None = None
    reglas_uso: str | None = None


class EspacioComunSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    capacidad: int | None
    reglas_uso: str | None

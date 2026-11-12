"""Esquemas de la carga de coeficientes (`F1-T24`).

El coeficiente es el porcentaje de la expensa que paga cada unidad. No es un
dato mas de la unidad: es **el** dato del que depende todo el modulo
financiero, y por eso tiene sus propios endpoints y sus propios esquemas en vez
de ser un campo del PATCH de la estructura.

============================================================================
TRES DECIMALES, NI UNO MAS, Y POR QUE ESO ES UNA REGLA Y NO UN FORMATO
============================================================================

La columna es `Numeric(6,3)`. Un coeficiente con cuatro decimales se guardaria
redondeado, y la suma de los redondeos es la que en la iteracion anterior daba
99,989% en vez de 100%: faltaba cobrar una milesima de la expensa de todo el
edificio, cada mes, sin que nadie lo viera.

Asi que un valor con mas decimales **se rechaza**, no se redondea. El limite no
se escribe aca: sale de `services/finanzas.DECIMALES_COEFICIENTE`, que es la
misma constante con la que el servicio hace las cuentas. Si se repitiera, el
dia que cambie la precision habria dos respuestas distintas a cuantos decimales
tiene un coeficiente.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services import finanzas

CRITERIO_PARTES_IGUALES = "partes_iguales"
CRITERIO_METROS_CUADRADOS = "metros_cuadrados"

# El tercer criterio no es un atajo como los otros dos: no calcula todas las
# unidades, completa **solo las que estan en blanco** con lo que falta para
# llegar a 100 y no toca ninguna de las cargadas. Por eso tampoco pide
# confirmacion: no puede pisar nada.
CRITERIO_COMPLETAR_EL_RESTO = "completar_el_resto"

CRITERIOS = (
    CRITERIO_PARTES_IGUALES,
    CRITERIO_METROS_CUADRADOS,
    CRITERIO_COMPLETAR_EL_RESTO,
)


def _coeficiente_valido(valor: Decimal) -> Decimal:
    """Entre 0 y 100, con tres decimales como maximo."""
    if -valor.as_tuple().exponent > finanzas.DECIMALES_COEFICIENTE:
        raise ValueError(
            f"El coeficiente admite hasta {finanzas.DECIMALES_COEFICIENTE} "
            "decimales."
        )
    return valor


class CoeficienteCargar(BaseModel):
    """El coeficiente de una unidad, cargado a mano.

    Esta es la carga que refleja el reglamento real de propiedad horizontal:
    los coeficientes estan escritos en el reglamento y no se calculan, se
    copian. Los atajos son para los edificios que todavia no lo tienen cargado.
    """

    model_config = ConfigDict(extra="forbid")

    coeficiente: Decimal = Field(ge=0, le=finanzas.TOTAL_COEFICIENTES)

    @field_validator("coeficiente")
    @classmethod
    def con_tres_decimales(cls, valor: Decimal) -> Decimal:
        return _coeficiente_valido(valor)


class AtajoDeCoeficientes(BaseModel):
    """Aplicar un atajo a todas las unidades del edificio.

    `sobrescribir` existe porque los coeficientes cargados a mano salen del
    reglamento, y pisarlos con un calculo automatico es destruir el dato
    verdadero. Sin confirmacion explicita, el atajo se niega a tocar un edificio
    que ya tiene coeficientes.

    **`sobrescribir` no aplica a `completar_el_resto`**, y es por construccion:
    ese criterio solo escribe en las unidades que estan en blanco, asi que no
    hay nada que pisar ni nada que confirmar. Mandarlo en `true` no cambia su
    comportamiento.
    """

    model_config = ConfigDict(extra="forbid")

    criterio: str
    sobrescribir: bool = False

    @field_validator("criterio")
    @classmethod
    def criterio_valido(cls, valor: str) -> str:
        limpio = valor.strip().lower()
        if limpio not in CRITERIOS:
            raise ValueError(f"El criterio tiene que ser uno de: {', '.join(CRITERIOS)}.")
        return limpio


class UnidadConCoeficiente(BaseModel):
    """Una unidad en la pantalla de coeficientes.

    Lleva el piso y la superficie porque es lo que se mira al cargar: el
    coeficiente de la unidad 3B se compara con el de la 2B, y la superficie es
    el unico control de razonabilidad que tiene a mano quien carga.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    identificador: str
    piso_numero: int
    m2: Decimal | None
    coeficiente: Decimal | None


class EstadoDeCoeficientes(BaseModel):
    """Como esta el edificio, y es la respuesta de los tres endpoints.

    ========================================================================
    POR QUE LOS TRES DEVUELVEN LO MISMO Y POR QUE LLEVA LA SUMA
    ========================================================================

    En la iteracion anterior la carga de coeficientes **nunca existio** y el
    problema aparecio recien al intentar generar una expensa, con un "Hay
    departamentos sin coeficiente cargado" que no decia cuales ni cuantos.

    Por eso cada respuesta de este modulo trae el estado completo: cuanto suma
    hoy, si eso es 100%, cuantas unidades siguen sin coeficiente y cuales son
    las primeras. Asi la pantalla puede mostrar "suman 99,988% y faltan 3
    unidades" en el mismo momento en que se carga una, sin pedir nada mas, y el
    problema se ve mientras se esta trabajando — no tres fases despues.
    """

    suma: Decimal
    suma_cien: bool
    cantidad_unidades: int
    unidades_sin_coeficiente: int
    unidades: list[UnidadConCoeficiente]
    mensaje: str

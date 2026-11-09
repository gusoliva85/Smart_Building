"""Esquemas de Pydantic del dominio del edificio.

Por ahora solo el alta (`F1-T20`). El listado y el detalle son `F1-T21`, y la
configuracion —responsables, vencimientos, mora, CBU, roles habilitados— es
`F1-T22`: nada de eso entra en el alta, a proposito. Un formulario de alta que
pide dieciocho campos para crear un edificio es un formulario que nadie
completa, y la mayoria de esos datos no se tienen el dia que se carga el
edificio.

Lo que el alta si pide y no es un dato del edificio son **cuantos pisos y
cuantas unidades por piso**: son los dos numeros con los que se genera la
estructura vacia, y solo sirven en ese momento. No se guardan en ninguna
columna; lo que queda guardado son los pisos y los departamentos que crearon.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import edificio as modelo_edificio
from app.services import autorizacion, finanzas


def _texto_obligatorio(valor: str) -> str:
    """Recorta los espacios y rechaza lo que queda vacio.

    Sin esto, un campo con solo espacios pasa el `min_length` y queda guardado
    como un nombre en blanco: la fila existe, el listado muestra un renglon
    vacio y nadie sabe que edificio es.
    """
    limpio = valor.strip()
    if not limpio:
        raise ValueError("No puede quedar vacío.")
    return limpio


def _texto_opcional(valor: str | None) -> str | None:
    """Lo mismo, pero un campo vacio es un campo sin cargar, no un error.

    Un formulario manda `""` cuando la persona no completo el campo, y guardar
    cadena vacia en vez de NULL deja dos formas distintas de decir "no hay
    dato": despues hay que preguntar por las dos en cada consulta, y el dia que
    alguien pregunte por una sola, la mitad de las filas no aparece.
    """
    if valor is None:
        return None
    limpio = valor.strip()
    return limpio or None


class EdificioCrear(BaseModel):
    """Alta de un edificio, con el tamanio de la estructura a generar."""

    # Un campo que el esquema no conoce se RECHAZA, no se ignora: el default de
    # Pydantic es descartarlo en silencio, y en un formulario eso significa que
    # un campo mal escrito devuelve 201 sin haber guardado ese dato.
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=2, max_length=160)
    direccion: str = Field(min_length=3, max_length=255)
    cp: str = Field(min_length=3, max_length=16)

    cuit: str | None = Field(default=None, max_length=13)

    # ------------------------------------------------------ geocodificacion --

    # Las manda el frontend despues de geocodificar con Nominatim (`F1-T25`).
    # Son opcionales porque una direccion que no se encuentra **avisa pero no
    # bloquea el alta**: una calle nueva puede no estar indexada todavia, y eso
    # no es motivo para no poder cargar un edificio que existe.
    #
    # Los limites son los mismos que los CHECK de la tabla. Estan en los dos
    # lados a proposito: aca para que el error sea un 422 que dice que esta
    # mal, y en la tabla para que un INSERT que no pase por la API tampoco
    # pueda poner un edificio fuera del planeta.
    latitud: Decimal | None = Field(default=None, ge=-90, le=90)
    longitud: Decimal | None = Field(default=None, ge=-180, le=180)

    # -------------------------------------------------- la estructura ------

    # Los topes salen de `services/finanzas.py` y no se escriben de nuevo aca.
    # Si se repitieran, el dia que se suba el tope del servicio este esquema
    # seguiria rechazando el valor y el error diria un numero que ya no es el
    # que rige.
    cantidad_pisos: int = Field(ge=1, le=finanzas.MAX_PISOS)
    unidades_por_piso: int = Field(ge=1, le=finanzas.MAX_UNIDADES_POR_PISO)

    @field_validator("nombre", "direccion", "cp")
    @classmethod
    def sin_espacios_de_sobra(cls, valor: str) -> str:
        return _texto_obligatorio(valor)

    @field_validator("cuit")
    @classmethod
    def cuit_limpio(cls, valor: str | None) -> str | None:
        """Recorta y trata el vacio como "sin cargar".

        **No se valida el formato ni el digito verificador**, y lo dejo escrito
        para que no parezca un olvido: el CUIT no es la clave de nada en este
        sistema (no es unico, porque un consorcio puede administrar dos torres)
        y rechazar un CUIT por formato impediria cargar un edificio real por un
        dato accesorio mal tipeado. Si alguna vez se emite documentacion
        fiscal, ahi si hace falta validarlo.
        """
        return _texto_opcional(valor)


class PisoCreado(BaseModel):
    """Un piso recien generado, con los identificadores de sus unidades."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: int
    orden: int
    unidades: list[str]


class EdificioRespuesta(BaseModel):
    """El edificio tal como lo devuelve la API.

    Lleva las columnas de configuracion aunque el alta no las pida: nacen con
    su valor por defecto y quien acaba de crear el edificio tiene que poder
    ver con que quedo, sin hacer un segundo pedido.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    direccion: str
    cp: str
    cuit: str | None
    latitud: Decimal | None
    longitud: Decimal | None

    admin_consorcio_id: int | None
    encargado_id: int | None

    dias_vencimiento_expensas: int
    recargo_mora_porcentual: Decimal
    contacto_emergencia_nombre: str | None
    contacto_emergencia_telefono: str | None
    roles_habilitados: list[str]
    cbu: str | None
    alias_cbu: str | None

    activo: bool
    creado_en: datetime


class EdificioCreado(BaseModel):
    """La respuesta del alta: el edificio y que estructura se le genero.

    Va envuelto y no plano porque lo segundo no es parte del edificio: son
    dos pisos y veintiocho unidades que se crearon en la misma transaccion, y
    la pantalla de `F1-T25` tiene que poder decir exactamente eso. Devolver
    solo el edificio obligaria a un segundo pedido para saber si la estructura
    se genero.
    """

    edificio: EdificioRespuesta
    pisos: list[PisoCreado]
    cantidad_pisos: int
    cantidad_departamentos: int
    mensaje: str


# ===========================================================================
# LECTURA (`F1-T21`)
#
# Son DOS formas distintas del mismo edificio, y la separacion es el punto de
# la tarea: el listado devuelve un **resumen** con dos numeros agregados, y el
# detalle devuelve la estructura completa. Si el listado reusara el esquema del
# detalle, cada renglon de la pantalla arrastraria los pisos y los
# departamentos del edificio entero — y eso, para una cartera de treinta
# edificios, son miles de filas que nadie va a mirar.
# ===========================================================================


class EdificioResumen(BaseModel):
    """Un edificio en el listado: identidad, ubicacion y tamanio.

    No lleva la estructura ni la configuracion. `cantidad_pisos` y
    `cantidad_departamentos` **no son columnas**: los cuenta la base en la
    misma consulta del listado, que es lo que evita el N+1 — ver el endpoint.

    No lleva `from_attributes` a proposito: no se construye desde un objeto de
    SQLAlchemy sino desde una fila con el edificio mas sus dos conteos, y
    declararlo invitaria a armarlo con `model_validate(edificio)`, que es
    justamente la version que dispara una consulta por edificio.
    """

    id: int
    nombre: str
    direccion: str
    cp: str
    cuit: str | None
    latitud: Decimal | None
    longitud: Decimal | None
    admin_consorcio_id: int | None
    encargado_id: int | None
    activo: bool
    creado_en: datetime

    cantidad_pisos: int
    cantidad_departamentos: int


class DepartamentoDetalle(BaseModel):
    """Una unidad, con su ocupacion ya resuelta.

    `ocupado` sale de la `hybrid_property` del modelo, no de una columna: es
    "hay propietario o hay inquilino". Viaja calculado para que el frontend no
    reimplemente la regla —y la reimplemente distinto— en JavaScript.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    identificador: str
    m2: Decimal | None
    propietario_id: int | None
    inquilino_id: int | None
    coeficiente: Decimal | None
    ocupado: bool


class PisoDetalle(BaseModel):
    """Un piso con sus unidades."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: int
    orden: int
    departamentos: list[DepartamentoDetalle]


class CocheraDetalle(BaseModel):
    """Una cochera del edificio."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    tipo: str
    departamento_id: int | None


class EspacioComunDetalle(BaseModel):
    """Un espacio comun del edificio."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    capacidad: int | None
    reglas_uso: str | None


class EdificioDetalle(BaseModel):
    """El edificio completo: sus datos mas toda su estructura.

    Va envuelto —el edificio en su propio campo y las listas al lado— por el
    mismo motivo que `EdificioCreado`: los pisos, las cocheras y los espacios
    comunes no son campos del edificio, son colecciones que cuelgan de el. Asi
    un cliente que solo necesita la cabecera sabe exactamente que leer, y el
    dia que aparezca una coleccion mas no cambia la forma de lo que ya hay.

    Los dos conteos van calculados aunque las listas esten presentes: la
    pantalla muestra "7 pisos, 28 unidades" en la cabecera, y contar en el
    cliente obliga a recorrer dos niveles para mostrar un numero.
    """

    edificio: EdificioRespuesta
    pisos: list[PisoDetalle]
    cocheras: list[CocheraDetalle]
    espacios_comunes: list[EspacioComunDetalle]
    cantidad_pisos: int
    cantidad_departamentos: int


# ===========================================================================
# CONFIGURACION (`F1-T22`)
# ===========================================================================


# Los campos que la columna declara NOT NULL. Mandarlos explicitamente en
# `null` es un pedido imposible —"dejame el edificio sin dias de vencimiento"—
# y conviene que el rechazo sea un 422 con un texto que lo explique, en vez de
# un 500 cuando la base rechace el UPDATE.
_NO_SE_PUEDEN_VACIAR = (
    "dias_vencimiento_expensas",
    "recargo_mora_porcentual",
    "roles_habilitados",
)

_CARACTERES_DEL_ALIAS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
)
LARGO_MINIMO_ALIAS = 6
LARGO_MAXIMO_ALIAS = 20
DECIMALES_DEL_RECARGO = 2


class EdificioConfigurar(BaseModel):
    """Configuracion del edificio. Todo opcional, y eso es el punto.

    ========================================================================
    POR QUE ES UN PATCH Y NO UN PUT
    ========================================================================

    La pantalla de configuracion tiene varios bloques —responsables, cobranza,
    contacto de emergencia, roles habilitados— y se guardan por separado. Con un
    PUT, guardar el bloque de cobranza obligaria a mandar tambien los
    responsables y el contacto; el dia que un campo nuevo no viaje en ese
    formulario, guardar la cobranza lo borraria sin que nadie lo pida.

    La diferencia entre "no mande este campo" y "mande este campo en null" la
    resuelve `model_fields_set` de Pydantic, no un valor centinela: el endpoint
    arma el UPDATE con `model_dump(exclude_unset=True)`, asi que un campo
    ausente no se toca y un campo en `null` se vacia de verdad. Es lo que
    permite **borrar** el telefono de emergencia, que con un centinela tipo
    cadena vacia seria imposible de distinguir de "no lo toques".
    """

    model_config = ConfigDict(extra="forbid")

    # ---------------------------------------------------------- responsables --
    #
    # Solo ids. Que el usuario exista, este activo y tenga el rol que
    # corresponde lo valida el endpoint, porque hace falta la base para saberlo
    # y un esquema no la tiene.
    admin_consorcio_id: int | None = None
    encargado_id: int | None = None

    # ------------------------------------------------------------- cobranza --
    dias_vencimiento_expensas: int | None = Field(default=None, ge=1, le=31)
    recargo_mora_porcentual: Decimal | None = Field(default=None, ge=0, le=100)
    cbu: str | None = None
    alias_cbu: str | None = None

    # -------------------------------------------- contacto de emergencia -----
    contacto_emergencia_nombre: str | None = Field(default=None, max_length=120)
    contacto_emergencia_telefono: str | None = Field(default=None, max_length=40)

    # -------------------------------------------------- roles habilitados ----
    roles_habilitados: list[str] | None = None

    @field_validator("contacto_emergencia_nombre", "contacto_emergencia_telefono")
    @classmethod
    def texto_de_contacto(cls, valor: str | None) -> str | None:
        return _texto_opcional(valor)

    @field_validator("cbu")
    @classmethod
    def cbu_de_22_digitos(cls, valor: str | None) -> str | None:
        """Limpia el CBU y exige los 22 digitos exactos.

        Se le sacan espacios y guiones antes de validar porque un CBU se copia
        y se pega de un resumen bancario o de un mail, y casi siempre viene
        separado en bloques. Rechazar "0170 0999 2000 0000 1234 56" seria
        rechazar la forma en la que el dato realmente llega.

        **No se valida el digito verificador**, y lo dejo escrito para que no
        parezca un olvido: alcanza para evitar el error de tipeo que corta un
        digito, que es el frecuente. Si hace falta la validacion completa, es
        una funcion en `services/finanzas.py` y un test.
        """
        if valor is None:
            return None

        limpio = valor.strip().replace(" ", "").replace("-", "")
        if not limpio:
            return None

        if len(limpio) != modelo_edificio.LARGO_CBU or not limpio.isdigit():
            raise ValueError(
                f"El CBU tiene que tener {modelo_edificio.LARGO_CBU} dígitos, "
                "sin letras."
            )
        return limpio

    @field_validator("alias_cbu")
    @classmethod
    def alias_valido(cls, valor: str | None) -> str | None:
        """Largo y caracteres del alias, con el vacio como "sin cargar".

        Los limites son los del alias bancario argentino: entre 6 y 20
        caracteres, letras, numeros, puntos y guiones. Si no se validaran, un
        alias de 30 caracteres entraria al esquema y lo rechazaria la columna
        `String(20)` — en PostgreSQL con un error de la base, que no se le
        muestra a nadie, asi que la persona veria un 500 sin explicacion.
        """
        if valor is None:
            return None

        limpio = valor.strip()
        if not limpio:
            return None

        if not LARGO_MINIMO_ALIAS <= len(limpio) <= LARGO_MAXIMO_ALIAS:
            raise ValueError(
                f"El alias tiene que tener entre {LARGO_MINIMO_ALIAS} y "
                f"{LARGO_MAXIMO_ALIAS} caracteres."
            )
        if not set(limpio) <= _CARACTERES_DEL_ALIAS:
            raise ValueError(
                "El alias solo admite letras, números, puntos y guiones."
            )
        return limpio

    @field_validator("recargo_mora_porcentual")
    @classmethod
    def recargo_con_dos_decimales(cls, valor: Decimal | None) -> Decimal | None:
        """Rechaza mas de dos decimales en vez de redondearlos en silencio.

        La columna es `Numeric(5,2)`: un 1,555 se guardaria como 1,56 o 1,55
        segun el motor, y la persona que escribio 1,555 nunca se enteraria de
        que el recargo que se aplica no es el que puso. Es plata ajena, asi que
        el rechazo explicito es la unica respuesta honesta.
        """
        if valor is None:
            return None

        if -valor.as_tuple().exponent > DECIMALES_DEL_RECARGO:
            raise ValueError(
                f"El recargo admite hasta {DECIMALES_DEL_RECARGO} decimales."
            )
        return valor

    @field_validator("roles_habilitados")
    @classmethod
    def roles_de_la_matriz(cls, valor: list[str] | None) -> list[str] | None:
        """Solo roles que existen y que tienen sentido dentro de un edificio.

        La lista valida es `ROLES_HABILITABLES`, que es la misma constante de la
        que sale el valor por defecto de la columna. Si este validador tuviera
        su propia lista, el dia que la Fase 11 agregue un rol habria dos
        respuestas distintas a "que roles puede tener un edificio".

        Se permite la lista **vacia**: significa "no habilitar a nadie todavia"
        y es una decision legitima de quien configura. El valor por defecto es
        "todos" justamente para que nadie se quede sin roles sin haberlo
        pedido, pero pedirlo explicitamente es otra cosa.
        """
        if valor is None:
            return None

        limpios: list[str] = []
        for rol in valor:
            rol = rol.strip()
            if rol not in autorizacion.ROLES_HABILITABLES:
                validos = ", ".join(autorizacion.ROLES_HABILITABLES)
                raise ValueError(
                    f"«{rol}» no es un rol que se pueda habilitar en un "
                    f"edificio. Los válidos son: {validos}."
                )
            # Repetir un rol no significa nada distinto de nombrarlo una vez,
            # y dejarlo entrar obligaria a desduplicar en cada lectura.
            if rol not in limpios:
                limpios.append(rol)
        return limpios

    @model_validator(mode="after")
    def no_vaciar_lo_obligatorio(self) -> "EdificioConfigurar":
        for campo in _NO_SE_PUEDEN_VACIAR:
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(
                    f"«{campo}» no puede quedar vacío: si no lo querés cambiar, "
                    "no lo mandes."
                )
        return self

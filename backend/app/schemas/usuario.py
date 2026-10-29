"""Esquemas de Pydantic del dominio de usuarios.

Alta, edicion parcial y respuesta. Cada uno es una clase aparte y **ninguno
hereda de los otros**, aunque compartan campos: las reglas de los tres son
distintas —en el alta la contrasenia es obligatoria, en la edicion no se toca
por esa via, y en la respuesta no existe— y una base comun termina siendo el
lugar por donde se cuela un campo que uno de los tres no deberia aceptar.

Lo que si se comparte son las funciones de normalizacion de abajo, que los tres
invocan. Eso evita lo unico que de verdad importa evitar: que el alta y la
edicion normalicen un email de dos maneras distintas.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator

from app.core import security
from app.services import autorizacion


def normalizar_email(valor: str) -> str:
    """Deja un email en la forma unica con la que se guarda y se busca.

    Vive como funcion suelta y no dentro del validador porque el login
    (`F1-T07`) tiene su propio esquema y necesita aplicar EXACTAMENTE la misma
    normalizacion. Si cada esquema escribiera su `.lower()`, alcanzaria con que
    uno quedara sin el para que el alta guardara en minusculas y el login
    buscara con mayusculas: el usuario existe, la consulta no lo encuentra, y
    el mensaje que ve la persona es "credenciales invalidas".
    """
    return valor.strip().lower()


def validar_rol(valor: str) -> str:
    """Rechaza un rol que no este en la matriz.

    Es la primera de las DOS validaciones del rol, y la que da el mensaje util:
    dice cuales son los validos. La segunda es el CheckConstraint de la tabla,
    que ya no explica nada pero ataja lo que no pasa por la API.

    Vive suelta, igual que `normalizar_email`, porque el alta y la edicion
    tienen que aplicar exactamente la misma regla. Si cada esquema escribiera
    su propia comprobacion, alcanzaria con agregar un rol a la matriz y
    olvidarse de uno de los dos.
    """
    if not autorizacion.es_rol_valido(valor):
        raise ValueError(
            f"Rol invalido: {valor!r}. Los validos son: "
            f"{', '.join(autorizacion.ROLES)}."
        )
    return valor


def limpiar_nombre(valor: str) -> str:
    """Recorta los espacios de los extremos y rechaza lo que quede vacio.

    Un nombre de solo espacios pasa el `min_length` de Pydantic, porque tiene
    largo. Despues aparece como una fila en blanco en el listado de usuarios y
    nadie sabe quien es.
    """
    limpio = valor.strip()
    if len(limpio) < 2:
        raise ValueError("El nombre no puede estar vacio.")
    return limpio


class UsuarioCrear(BaseModel):
    """Datos para dar de alta un usuario.

    No hereda de un esquema base compartido con el de edicion, y es deliberado:
    las reglas de los dos son distintas (en el alta la contrasenia es
    obligatoria, en la edicion no se toca por esa via) y una base comun termina
    siendo el lugar donde se cuelan campos que uno de los dos no deberia
    aceptar.
    """

    # Un campo que el esquema no conoce se RECHAZA, no se ignora.
    #
    # El comportamiento por defecto de Pydantic es descartarlo en silencio, y
    # en un formulario eso significa que un `nombres` por `nombre` —o un campo
    # que el frontend renombro y el backend no— devuelve 200 sin haber guardado
    # nada. La persona ve que se guardo bien y no se guardo. Un 422 que nombra
    # el campo desconocido convierte una hora de buscar el bug en un mensaje.
    #
    # De paso cierra la puerta a mandar campos que este esquema no deberia
    # aceptar, como `password` en la edicion o `activo` en el alta.
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str
    rol: str
    telefono: str | None = Field(default=None, max_length=40)

    @field_validator("password")
    @classmethod
    def password_robusta(cls, valor: str) -> str:
        """Aplica la politica de `core/security.py`.

        La politica NO se reescribe aca. Este validador solo la invoca, para
        que el minimo de caracteres y el maximo de bytes que acepta bcrypt
        sigan viviendo en un solo archivo.

        `PasswordInsegura` hereda de `ValueError`, que es lo que Pydantic
        espera: lo convierte en un 422 con el mensaje completo de todo lo que
        falta, no del primer requisito incumplido.
        """
        security.validar_password(valor)
        return valor

    @field_validator("email")
    @classmethod
    def email_en_minusculas(cls, valor: str) -> str:
        """Normaliza el email entero a minusculas.

        Pydantic ya pasa el DOMINIO a minusculas, pero deja la parte local tal
        como vino: `ANA@ejemplo.com` y `ana@ejemplo.com` llegan como dos valores
        distintos. Y el indice unico de la tabla distingue mayusculas, asi que
        serian DOS usuarios — con dos contrasenias y dos historiales — para una
        sola persona. Peor todavia en el login: quien se dio de alta como
        `Ana@...` no entra escribiendo `ana@...`, y el mensaje que ve es
        "credenciales invalidas", que no da ninguna pista de lo que paso.

        Es una decision y no una correccion de bug, asi que vale aclararla: el
        estandar de correo dice que la parte local SI es sensible a mayusculas,
        y en teoria `Ana@` y `ana@` podrian ser dos casillas. En la practica no
        existe ningun proveedor que las distinga, y el costo de equivocarse
        para cada lado no es el mismo: tratarlas como distintas genera cuentas
        duplicadas y gente que no puede entrar, tratarlas como iguales no rompe
        nada en ningun caso real.

        Se normaliza en la ENTRADA y no al consultar, para que lo que quede
        guardado ya este normalizado: si se normalizara solo al buscar, las
        filas viejas quedarian con mayusculas y el indice unico no serviria
        para impedir el duplicado, que es justamente lo que tiene que impedir.
        """
        return normalizar_email(valor)

    @field_validator("rol")
    @classmethod
    def rol_conocido(cls, valor: str) -> str:
        """Rechaza un rol que no este en la matriz.

        Es la primera de las DOS validaciones del rol, y la que da el mensaje
        util: dice cuales son los validos. La segunda es el CheckConstraint de
        la tabla, que ya no explica nada pero ataja lo que no pasa por la API.
        """
        return validar_rol(valor)

    @field_validator("nombre")
    @classmethod
    def nombre_sin_espacios_de_sobra(cls, valor: str) -> str:
        """Recorta los espacios de los extremos y rechaza lo que quede vacio.

        Un nombre de solo espacios pasa el `min_length` de Pydantic, porque
        tiene largo. Despues aparece como una fila en blanco en el listado de
        usuarios y nadie sabe quien es.
        """
        return limpiar_nombre(valor)


class UsuarioEditar(BaseModel):
    """Modificacion parcial de un usuario.

    ========================================================================
    SEMANTICA DE PATCH, QUE VALE PARA TODO EL SISTEMA
    ========================================================================

    - Un campo que **no viene** queda como estaba.
    - Un campo que viene en **`null`** se borra de verdad.

    Las dos cosas son distintas y hay que poder distinguirlas, porque si no
    fuera posible habria que elegir entre no poder borrar un telefono o
    borrarlo sin querer en cada edicion que no lo mande. Se resuelve con
    `exclude_unset=True` al volcar el esquema: Pydantic recuerda que campos
    llegaron, no solo su valor. **Ningun endpoint de edicion del proyecto lee
    estos campos directamente**; todos pasan por ese volcado.

    Solo `telefono` es opcional en la tabla, asi que es el unico que se puede
    mandar en `null`. Los demas tienen tipo no-nulo y Pydantic rechaza el
    `null` con un 422, que es exactamente lo que corresponde: un usuario sin
    nombre o sin rol no es un usuario con un campo vacio, es una fila que el
    resto del sistema no sabe mostrar.

    ========================================================================
    LA CONTRASENIA NO SE EDITA POR ACA
    ========================================================================

    No esta en este esquema a proposito, y no es un olvido. Cambiar la
    contrasenia de alguien es una operacion distinta de corregirle el telefono:
    tiene que pedir la contrasenia actual si la cambia el propio usuario, o
    forzar un cambio en el proximo ingreso si la resetea un administrador.
    Meterla como un campo mas de este PATCH significaria que un administrador
    le pisa la contrasenia a cualquiera sin que la persona se entere.
    """

    # Un campo que el esquema no conoce se RECHAZA, no se ignora.
    #
    # El comportamiento por defecto de Pydantic es descartarlo en silencio, y
    # en un formulario eso significa que un `nombres` por `nombre` —o un campo
    # que el frontend renombro y el backend no— devuelve 200 sin haber guardado
    # nada. La persona ve que se guardo bien y no se guardo. Un 422 que nombra
    # el campo desconocido convierte una hora de buscar el bug en un mensaje.
    #
    # De paso convierte en un error explicito mandar `password` por acá, que
    # es una operacion distinta y no un campo mas de la edicion.
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    rol: str | None = None
    telefono: str | None = Field(default=None, max_length=40)
    activo: bool | None = None

    @field_validator("nombre", "email", "rol", "activo", mode="before")
    @classmethod
    def no_se_borra_lo_que_no_es_opcional(cls, valor, info):
        """Rechaza un `null` explicito en los campos que la tabla no admite
        vacios, y lo explica.

        Hace falta por como se escriben estos campos: son `tipo | None` para
        poder omitirlos, asi que el tipo **acepta** `null` y sin esta guarda un
        `{"nombre": null}` llegaria como `None` al validador de abajo y
        reventaria con un 500 en `None.strip()`. El error correcto es un 422
        que diga que ese campo no se puede vaciar y como se hace para no
        cambiarlo.
        """
        if valor is None:
            raise ValueError(
                f"'{info.field_name}' no se puede dejar vacio. "
                "Si no queres cambiarlo, no lo mandes."
            )
        return valor

    @field_validator("email")
    @classmethod
    def email_en_minusculas(cls, valor: str) -> str:
        """La MISMA normalizacion que el alta.

        Si la edicion no normalizara, alcanzaria con corregirle el email a
        alguien escribiendolo con una mayuscula para que esa persona deje de
        poder entrar: el login normaliza antes de buscar, y la fila quedaria
        guardada sin normalizar.
        """
        return normalizar_email(valor)

    @field_validator("rol")
    @classmethod
    def rol_conocido(cls, valor: str) -> str:
        return validar_rol(valor)

    @field_validator("nombre")
    @classmethod
    def nombre_sin_espacios_de_sobra(cls, valor: str) -> str:
        return limpiar_nombre(valor)


class CambioDeEstado(BaseModel):
    """El estado que se quiere dejar, para el endpoint de alta y baja logica.

    Es un cuerpo de un solo campo y no un parametro de consulta a proposito:
    `?activo=false` en una URL se copia, se comparte y se llama por accidente
    desde la barra de direcciones, y esto cambia quien puede entrar al sistema.

    Y dice el estado DESEADO, no la transicion: asi el pedido es idempotente y
    no depende de que el frontend tenga el estado actual al dia, que es una
    suposicion que se rompe con dos pestanias abiertas.
    """

    activo: bool


class PermisosRol(BaseModel):
    """La fila de la matriz de roles que le corresponde a un usuario.

    Viaja dentro de `/auth/me` para que el frontend **no vuelva a declarar la
    matriz**. Si el frontend tuviera su propia copia de quien ve montos y quien
    es de solo lectura, serian dos verdades sobre lo mismo: el dia que una
    cambie, la interfaz va a mostrar botones que el backend rechaza, o a
    esconder cosas que el usuario si puede hacer.

    No reemplaza al control del backend. El backend decide; esto es para que la
    interfaz no ofrezca lo que va a ser rechazado.
    """

    alcance: str
    ve_financiero_unidad: bool
    ve_financiero_edificio: bool
    solo_lectura: bool


class UsuarioRespuesta(BaseModel):
    """Un usuario tal como se lo devuelve la API.

    Nunca incluye `password_hash`. Que el esquema de salida sea una clase
    aparte, y no el modelo de SQLAlchemy serializado, es precisamente lo que
    hace imposible filtrarlo: no alcanza con olvidarse de excluirlo, habria que
    agregarlo a mano.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    # `str` y no `EmailStr`, a proposito, aunque la entrada si use `EmailStr`.
    #
    # Un esquema de SALIDA con `EmailStr` vuelve a validar el dato al
    # responder, y si lo que esta guardado no pasa esa validacion la respuesta
    # no es "el usuario con un email raro": es un **500**. O sea, el endpoint
    # deja de funcionar por completo para esa persona, y el error habla de
    # validacion de respuesta, que no le dice a nadie que el problema es el
    # email de una fila.
    #
    # Apareció de verdad: `email-validator` rechaza los dominios de uso
    # reservado (`.local`, `.test`, `.example`), asi que un email interno
    # perfectamente razonable rompe la lectura. La validacion va donde entra el
    # dato —el esquema de alta y el seed—, no donde sale.
    email: str
    rol: str
    telefono: str | None
    activo: bool
    creado_en: datetime

    @computed_field
    @property
    def rol_etiqueta(self) -> str:
        """El nombre del rol como se le muestra a una persona.

        Lo resuelve la matriz y no el frontend: "Administrador de Consorcio" es
        un dato del rol, y escribirlo en el HTML seria una traduccion paralela
        que en algun momento queda desactualizada.
        """
        return autorizacion.etiqueta(self.rol)

    @computed_field
    @property
    def permisos(self) -> PermisosRol:
        return PermisosRol.model_validate(autorizacion.obtener(self.rol), from_attributes=True)


class Token(BaseModel):
    """La respuesta del login.

    Los nombres de los campos (`access_token`, `token_type`) son los que fija
    el estandar de OAuth2 y los que espera el boton "Authorize" de /docs. No se
    traducen al castellano como el resto del proyecto: cambiarlos rompe la
    interoperabilidad con cualquier cliente que siga el estandar, y /docs es el
    primero.
    """

    access_token: str
    token_type: str = "bearer"

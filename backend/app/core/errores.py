"""Catalogo unico de los errores que el sistema le muestra a una persona.

============================================================================
LA REGLA, Y ES LA UNICA QUE IMPORTA DE ESTE ARCHIVO
============================================================================

**Todo mensaje de error que vea un usuario vive aca y en ningun otro lado.**
Ningun endpoint vuelve a escribir un `detail=` literal, ninguna pantalla
escribe su propia version de un texto del backend, y cada error nuevo que
aparezca —en esta fase o en la Fase 9— se agrega a este catalogo antes de
usarlo.

No es prolijidad. Antes de existir este archivo habia 27 mensajes escritos a
mano repartidos en seis archivos, y el mismo error —fallo el guardado en la
base— estaba redactado de **cuatro formas distintas**. Con dos endpoints eso
no molesta; con cuarenta se convierte en tres problemas concretos:

1. El mismo error se le explica distinto a la misma persona segun la pantalla
   desde la que llegue.
2. El frontend no tiene nada estable contra lo que decidir. Si tiene que
   reaccionar distinto a dos errores 400 distintos, su unica opcion es
   comparar el texto en castellano — que cambia en cuanto alguien corrige una
   tilde.
3. Cambiar un mensaje obliga a buscarlo por todo el proyecto.

Es el mismo razonamiento que puso los permisos en una matriz en vez de
repartirlos en condicionales: **si es una regla del sistema, es una estructura
de datos, no texto suelto.**

============================================================================
LA FORMA DE LA RESPUESTA, QUE ES SIEMPRE LA MISMA
============================================================================

Los cuatro manejadores de abajo devuelven exactamente esta forma, sin
importar si el error lo levanto un endpoint, una dependencia, la validacion de
Pydantic o el ruteo de FastAPI:

    {
      "codigo":  "PISO_CON_UNIDADES",     // estable, para que decida el cliente
      "mensaje": "El piso 9 todavia ...", // castellano, para que lea la persona
      "campos":  {"cantidad_pisos": "..."} // por campo, cuando es un formulario
    }

`codigo` es el contrato con el frontend y **no se cambia nunca**; `mensaje` se
puede reescribir cuantas veces haga falta sin romper nada. `campos` viaja
siempre, vacio cuando no corresponde: una forma que cambia segun el caso
obliga a quien la consume a preguntar antes de leer.

============================================================================
LO QUE NINGUN MENSAJE PUEDE DECIR (REGLA `FX-T11`)
============================================================================

El texto de un error de negocio se le muestra a cualquiera, asi que **ninguna
entrada nombra tablas, columnas, consultas, ids internos ni nombres de
archivo**. Eso ya era regla del proyecto y este catalogo la vuelve
verificable: auditarla pasa de recorrer cuarenta endpoints a leer un archivo
—y hay un test que recorre el catalogo entero buscando esas palabras.

Por eso, de paso, el 404 de usuario dejo de decir "No existe un usuario con id
37": el id es interno y no le sirve a nadie del otro lado de la pantalla.
"""

from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as ExcepcionHTTP

# ===========================================================================
# EL CATALOGO
# ===========================================================================


@dataclass(frozen=True)
class DefinicionDeError:
    """Un error del sistema: su codigo, su codigo HTTP y su texto.

    `plantilla` puede llevar parametros con nombre (`{puesto}`), que se
    completan al levantar el error. Son parte del mensaje, no datos sueltos:
    "La persona que elegiste como Encargado no existe" explica el problema y
    "Falta un responsable" no.
    """

    codigo: str
    http: int
    plantilla: str


CATALOGO: dict[str, DefinicionDeError] = {}


def _definir(codigo: str, http: int, plantilla: str) -> str:
    """Registra un error y devuelve su codigo, para usarlo como constante.

    Devolver el codigo es lo que permite escribir
    `raise ErrorDeNegocio(SIN_CAMBIOS)` con el nombre y no con la cadena: un
    codigo mal tipeado es un `NameError` al importar el modulo, no un error en
    tiempo de ejecucion dentro de un endpoint que quiza nadie llame hoy.
    """
    if codigo in CATALOGO:
        raise ValueError(f"El codigo de error {codigo} ya esta definido.")
    CATALOGO[codigo] = DefinicionDeError(codigo=codigo, http=http, plantilla=plantilla)
    return codigo


# ------------------------------------------------------- sesion y permisos --

SESION_INVALIDA = _definir(
    "SESION_INVALIDA",
    status.HTTP_401_UNAUTHORIZED,
    "No se pudo validar la sesión. Volvé a iniciar sesión.",
)

CREDENCIALES_INVALIDAS = _definir(
    "CREDENCIALES_INVALIDAS",
    status.HTTP_401_UNAUTHORIZED,
    "Email o contraseña incorrectos.",
)

# `F1-T30`. Este mensaje solo se puede dar DESPUES de verificar la contrasenia,
# y el porque esta en el endpoint de login: decirlo antes convertiria al login
# en un verificador de direcciones de correo.
CUENTA_INHABILITADA = _definir(
    "CUENTA_INHABILITADA",
    status.HTTP_403_FORBIDDEN,
    "Tu cuenta está inhabilitada. Contactá al administrador del consorcio.",
)

SIN_PERMISO = _definir(
    "SIN_PERMISO",
    status.HTTP_403_FORBIDDEN,
    "Esta acción es solo para: {quienes}.",
)

ROL_DE_SOLO_LECTURA = _definir(
    "ROL_DE_SOLO_LECTURA",
    status.HTTP_403_FORBIDDEN,
    "{rol} es un rol de consulta: puede ver la información pero no modificarla.",
)

RESPONSABLES_SOLO_ADMIN_GENERAL = _definir(
    "RESPONSABLES_SOLO_ADMIN_GENERAL",
    status.HTTP_403_FORBIDDEN,
    "Quién administra el edificio lo decide el Administrador General. "
    "Podés configurar el resto.",
)

# ---------------------------------------------------------------- usuarios --

USUARIO_NO_ENCONTRADO = _definir(
    "USUARIO_NO_ENCONTRADO",
    status.HTTP_404_NOT_FOUND,
    "No encontramos a esa persona.",
)

EMAIL_REPETIDO = _definir(
    "EMAIL_REPETIDO",
    status.HTTP_400_BAD_REQUEST,
    "Ya existe un usuario con ese email.",
)

NO_PODES_DESACTIVARTE = _definir(
    "NO_PODES_DESACTIVARTE",
    status.HTTP_400_BAD_REQUEST,
    "No podés desactivar tu propia cuenta. Si lo hicieras no podrías volver a "
    "iniciar sesión, y hace falta otro administrador para reactivarla.",
)

NO_PODES_CAMBIARTE_EL_ROL = _definir(
    "NO_PODES_CAMBIARTE_EL_ROL",
    status.HTTP_400_BAD_REQUEST,
    "No podés cambiarte el rol a vos mismo. Al dejar de ser Administrador "
    "General perderías el permiso para volver a cambiarlo.",
)

# ---------------------------------------------------------------- edificios --

EDIFICIO_NO_ENCONTRADO = _definir(
    "EDIFICIO_NO_ENCONTRADO",
    status.HTTP_404_NOT_FOUND,
    "No se encontró el edificio.",
)

SIN_CAMBIOS = _definir(
    "SIN_CAMBIOS",
    status.HTTP_400_BAD_REQUEST,
    "No enviaste ningún cambio.",
)

RESPONSABLE_NO_EXISTE = _definir(
    "RESPONSABLE_NO_EXISTE",
    status.HTTP_400_BAD_REQUEST,
    "La persona que elegiste como {puesto} no existe.",
)

RESPONSABLE_DESACTIVADO = _definir(
    "RESPONSABLE_DESACTIVADO",
    status.HTTP_400_BAD_REQUEST,
    "{nombre} está desactivado, así que no puede quedar como {puesto}.",
)

RESPONSABLE_CON_OTRO_ROL = _definir(
    "RESPONSABLE_CON_OTRO_ROL",
    status.HTTP_400_BAD_REQUEST,
    "{nombre} es {rol_actual}, no {puesto}. Cambiale el rol primero o elegí a "
    "otra persona.",
)

RESPONSABLES_IGUALES = _definir(
    "RESPONSABLES_IGUALES",
    status.HTTP_400_BAD_REQUEST,
    "La misma persona no puede ser Administrador de Consorcio y Encargado del "
    "mismo edificio.",
)

# -------------------------------------------------------------- estructura --

NO_ENCONTRADO_EN_EL_EDIFICIO = _definir(
    "NO_ENCONTRADO_EN_EL_EDIFICIO",
    status.HTTP_404_NOT_FOUND,
    "No se encontró {que}.",
)

PISO_REPETIDO = _definir(
    "PISO_REPETIDO",
    status.HTTP_400_BAD_REQUEST,
    "Este edificio ya tiene un piso {numero}.",
)

POSICION_DE_PISO_OCUPADA = _definir(
    "POSICION_DE_PISO_OCUPADA",
    status.HTTP_400_BAD_REQUEST,
    "Ya hay un piso en la posición {orden}. Elegí otra posición o dejá el "
    "campo vacío para agregarlo arriba del último.",
)

PISO_CON_UNIDADES = _definir(
    "PISO_CON_UNIDADES",
    status.HTTP_400_BAD_REQUEST,
    "El piso {numero} todavía tiene {cuantas}. Borralas primero.",
)

# Habia dos textos para esto —"El piso 9 ya tiene una unidad 9A" en el alta y
# "Ese piso ya tiene una unidad 9A" en la edicion— y ahora hay uno. El numero
# del piso se saco del mensaje a proposito: las dos operaciones pasan dentro de
# un piso que quien las hizo acaba de elegir.
UNIDAD_REPETIDA = _definir(
    "UNIDAD_REPETIDA",
    status.HTTP_400_BAD_REQUEST,
    "Ese piso ya tiene una unidad {identificador}.",
)

UNIDAD_CON_RESIDENTE = _definir(
    "UNIDAD_CON_RESIDENTE",
    status.HTTP_400_BAD_REQUEST,
    "La unidad {identificador} tiene a alguien asignado. Desvinculá al "
    "propietario o al inquilino antes de borrarla.",
)

UNIDAD_CON_COCHERAS = _definir(
    "UNIDAD_CON_COCHERAS",
    status.HTTP_400_BAD_REQUEST,
    "La unidad {identificador} tiene {cuantas}. Desasignalas primero.",
)

# El cruce que la tabla ya prohibe con un CHECK. Hoy es inalcanzable por la
# API —cada puesto exige su rol y un usuario tiene uno solo— y existe para que,
# si alguna vez se alcanzara, la respuesta explique el motivo en vez de ser un
# 500 sin texto.
PROPIETARIO_ES_INQUILINO = _definir(
    "PROPIETARIO_ES_INQUILINO",
    status.HTTP_400_BAD_REQUEST,
    "La misma persona no puede ser propietaria e inquilina de la misma unidad.",
)

RESIDENTE_NO_EXISTE = _definir(
    "RESIDENTE_NO_EXISTE",
    status.HTTP_400_BAD_REQUEST,
    "La persona que elegiste como {puesto} no existe.",
)

RESIDENTE_DESACTIVADO = _definir(
    "RESIDENTE_DESACTIVADO",
    status.HTTP_400_BAD_REQUEST,
    "{nombre} está desactivado, así que no puede quedar como {puesto} de la "
    "unidad.",
)

RESIDENTE_CON_OTRO_ROL = _definir(
    "RESIDENTE_CON_OTRO_ROL",
    status.HTTP_400_BAD_REQUEST,
    "{nombre} es {rol_actual}, no {puesto}. Cambiale el rol primero o elegí a "
    "otra persona.",
)

ROL_NO_HABILITADO_EN_EL_EDIFICIO = _definir(
    "ROL_NO_HABILITADO_EN_EL_EDIFICIO",
    status.HTTP_400_BAD_REQUEST,
    "Este edificio no tiene habilitado el rol {puesto}. Habilitalo en la "
    "configuración del edificio y volvé a intentarlo.",
)

INQUILINO_EN_OTRA_UNIDAD = _definir(
    "INQUILINO_EN_OTRA_UNIDAD",
    status.HTTP_400_BAD_REQUEST,
    "{nombre} ya figura como inquilino de la unidad {unidad}. Un inquilino "
    "tiene una sola unidad: desvinculalo de esa primero.",
)

COCHERA_REPETIDA = _definir(
    "COCHERA_REPETIDA",
    status.HTTP_400_BAD_REQUEST,
    "Este edificio ya tiene una cochera {numero}.",
)

COCHERA_ROTATIVA_ASIGNADA = _definir(
    "COCHERA_ROTATIVA_ASIGNADA",
    status.HTTP_400_BAD_REQUEST,
    "Una cochera rotativa no se asigna a una unidad: rotativa significa "
    "justamente que no es de nadie en particular.",
)

ESPACIO_REPETIDO = _definir(
    "ESPACIO_REPETIDO",
    status.HTTP_400_BAD_REQUEST,
    "Este edificio ya tiene un espacio «{nombre}».",
)

# ------------------------------------------------------------ coeficientes --

EDIFICIO_SIN_UNIDADES = _definir(
    "EDIFICIO_SIN_UNIDADES",
    status.HTTP_400_BAD_REQUEST,
    "Este edificio todavía no tiene unidades, así que no hay nada que repartir.",
)

COEFICIENTES_YA_CARGADOS = _definir(
    "COEFICIENTES_YA_CARGADOS",
    status.HTTP_409_CONFLICT,
    "{cuantas} ya {tienen} coeficiente cargado. Los coeficientes del "
    "reglamento no se pueden recalcular: ¿querés reemplazarlos igual?",
)

# El 409 de arriba es el unico de la Fase 1 y es el mecanismo de confirmacion
# del proyecto: `api.js` lo convierte en `error.necesitaConfirmacion` y abre el
# dialogo con este mismo texto. Por eso el texto es una pregunta.

FALTAN_SUPERFICIES = _definir(
    "FALTAN_SUPERFICIES",
    status.HTTP_400_BAD_REQUEST,
    "No se puede repartir por metro cuadrado: {cuantas} no {tienen} superficie "
    "cargada ({cuales}). Cargá las superficies o usá el reparto en partes "
    "iguales.",
)

SIN_RESTO_QUE_COMPLETAR = _definir(
    "SIN_RESTO_QUE_COMPLETAR",
    status.HTTP_400_BAD_REQUEST,
    "Todas las unidades ya tienen coeficiente, así que no queda resto que "
    "completar. Si querés recalcularlos todos, usá el reparto en partes "
    "iguales o por metro cuadrado.",
)

RESTO_EN_CERO = _definir(
    "RESTO_EN_CERO",
    status.HTTP_400_BAD_REQUEST,
    "Las unidades que ya tienen coeficiente suman 100%, así que a {cuantas} "
    "{les} tocaría 0%. Si {son} —el departamento del encargado suele serlo— "
    "cargale 0 a mano; si no, hay algún coeficiente de más en las otras.",
)

COEFICIENTES_PASAN_CIEN = _definir(
    "COEFICIENTES_PASAN_CIEN",
    status.HTTP_400_BAD_REQUEST,
    "Las unidades que ya tienen coeficiente suman {suma}%, o sea más de 100%. "
    "Corregí alguna antes de completar el resto.",
)

# ----------------------------------------------------------------- gastos --
#
# Los dos son del filtro del listado, no del gasto en si: el rubro y el monto
# del alta los valida el esquema y los ataja el CHECK de la tabla.

MES_SIN_ANIO = _definir(
    "MES_SIN_ANIO",
    status.HTTP_400_BAD_REQUEST,
    "Para filtrar por mes hace falta elegir también el año.",
)

RUBRO_INVALIDO = _definir(
    "RUBRO_INVALIDO",
    status.HTTP_400_BAD_REQUEST,
    "Ese rubro no existe. Los rubros válidos son: {cuales}.",
)

# --------------------------------------------------------------- expensas --

PERIODO_SIN_GASTOS = _definir(
    "PERIODO_SIN_GASTOS",
    status.HTTP_400_BAD_REQUEST,
    "No hay gastos cargados en {periodo}, así que no hay nada que liquidar.",
)

COEFICIENTES_INCOMPLETOS = _definir(
    "COEFICIENTES_INCOMPLETOS",
    status.HTTP_400_BAD_REQUEST,
    "Hay {cuantas} sin coeficiente cargado ({cuales}). Cargá los coeficientes "
    "antes de generar la expensa.",
)

COEFICIENTES_NO_SUMAN_CIEN = _definir(
    "COEFICIENTES_NO_SUMAN_CIEN",
    status.HTTP_400_BAD_REQUEST,
    "Los coeficientes de este edificio suman {suma}% y tienen que sumar 100% "
    "exacto para poder liquidar.",
)

EXPENSA_YA_PUBLICADA = _definir(
    "EXPENSA_YA_PUBLICADA",
    status.HTTP_400_BAD_REQUEST,
    "La expensa de {periodo} ya está publicada y no se puede volver a "
    "generar. Lo que haya que corregir de ese período se corrige en la "
    "liquidación siguiente.",
)

EXPENSA_SE_REGENERA = _definir(
    "EXPENSA_SE_REGENERA",
    status.HTTP_409_CONFLICT,
    "Ya hay una expensa de {periodo} en borrador, por {total}. Si seguís, se "
    "reemplaza por una nueva calculada con los gastos de ahora.",
)

EXPENSA_NO_ENCONTRADA = _definir(
    "EXPENSA_NO_ENCONTRADA",
    status.HTTP_404_NOT_FOUND,
    "No se encontró esa liquidación.",
)

EXPENSA_NO_SE_PUEDE_PUBLICAR = _definir(
    "EXPENSA_NO_SE_PUEDE_PUBLICAR",
    status.HTTP_400_BAD_REQUEST,
    "La expensa de {periodo} ya está publicada.",
)

GASTO_DE_PERIODO_PUBLICADO = _definir(
    "GASTO_DE_PERIODO_PUBLICADO",
    status.HTTP_400_BAD_REQUEST,
    "Este gasto ya entró en la expensa de {periodo}, que está publicada, "
    "así que no se puede cambiar ni borrar. Lo que corresponde es cargar la "
    "corrección en la liquidación siguiente.",
)

# ------------------------------------------------------- genericos y sistema --

PEDIDO_INVALIDO = _definir(
    "PEDIDO_INVALIDO",
    status.HTTP_400_BAD_REQUEST,
    "El pedido no se pudo procesar.",
)

DATOS_INVALIDOS = _definir(
    "DATOS_INVALIDOS",
    status.HTTP_422_UNPROCESSABLE_ENTITY,
    "Revisá los datos del formulario.",
)

NO_ENCONTRADO = _definir(
    "NO_ENCONTRADO",
    status.HTTP_404_NOT_FOUND,
    "No se encontró lo que buscabas.",
)

METODO_NO_PERMITIDO = _definir(
    "METODO_NO_PERMITIDO",
    status.HTTP_405_METHOD_NOT_ALLOWED,
    "Esa operación no está disponible en esta dirección.",
)

NECESITA_CONFIRMACION = _definir(
    "NECESITA_CONFIRMACION",
    status.HTTP_409_CONFLICT,
    "Hace falta que confirmes esta acción.",
)

# Los cuatro 500 de guardado que existian estaban redactados distinto cada uno.
# Es UN error con un parametro, y el parametro es lo unico que cambiaba.
ERROR_AL_GUARDAR = _definir(
    "ERROR_AL_GUARDAR",
    status.HTTP_500_INTERNAL_SERVER_ERROR,
    "No se pudo guardar {que}. No quedó nada a medio cambiar: podés volver a "
    "intentarlo.",
)

ERROR_INTERNO = _definir(
    "ERROR_INTERNO",
    status.HTTP_500_INTERNAL_SERVER_ERROR,
    "Hubo un problema en el servidor. Volvé a intentarlo en un rato.",
)


# ===========================================================================
# LA EXCEPCION
# ===========================================================================


@dataclass
class ErrorDeNegocio(Exception):
    """Un error del catalogo, listo para levantar desde un endpoint.

        raise ErrorDeNegocio(PISO_CON_UNIDADES, numero=9, cuantas="1 unidad")

    Se levanta **por codigo y nunca por texto**. Eso es lo que hace que el
    mensaje se pueda reescribir sin tocar un solo endpoint, y que el frontend
    pueda decidir sin leer castellano.
    """

    codigo: str
    campos: dict[str, str] = field(default_factory=dict)
    parametros: dict[str, Any] = field(default_factory=dict)
    cabeceras: dict[str, str] | None = None

    def __init__(
        self,
        codigo: str,
        *,
        campos: dict[str, str] | None = None,
        cabeceras: dict[str, str] | None = None,
        **parametros: Any,
    ) -> None:
        if codigo not in CATALOGO:
            # Pasa solo si alguien construye el error con una cadena en vez de
            # con la constante. Revienta fuerte y temprano: un codigo que no
            # esta en el catalogo no tiene mensaje, asi que lo que llegaria al
            # usuario seria una pantalla vacia.
            raise ValueError(f"El codigo de error {codigo!r} no esta en el catalogo.")

        self.codigo = codigo
        self.campos = campos or {}
        self.parametros = parametros
        # Las cabeceras existen por un solo caso y es importante: los dos 401
        # de sesion tienen que llevar `WWW-Authenticate`. Sin ese header la
        # respuesta no cumple el estandar de HTTP para un 401 y el boton
        # "Authorize" de /docs no se da cuenta de que tiene que volver a pedir
        # credenciales.
        self.cabeceras = cabeceras
        super().__init__(self.mensaje)

    @property
    def definicion(self) -> DefinicionDeError:
        return CATALOGO[self.codigo]

    @property
    def http(self) -> int:
        return self.definicion.http

    @property
    def mensaje(self) -> str:
        """El texto del catalogo con sus parametros completados.

        Si falta un parametro, el mensaje sale con la llave sin reemplazar en
        vez de romper la respuesta: un error mostrado a medias es molesto, uno
        que levanta otra excepcion mientras se esta reportando un error deja al
        usuario frente a un 500 sin explicacion.
        """
        try:
            return self.definicion.plantilla.format(**self.parametros)
        except (KeyError, IndexError):
            return self.definicion.plantilla


# ===========================================================================
# EL 422 DE PYDANTIC, EN CASTELLANO
# ===========================================================================
#
# Pydantic rechaza el cuerpo de un pedido con una lista de problemas por campo,
# y el texto de cada problema lo escribe la libreria **en ingles**: "Input
# should be less than or equal to 40". Eso es lo que estaba llegando a la
# pantalla.
#
# Se traduce **por tipo de problema** y no mensaje por mensaje: son unas pocas
# entradas y cubren todos los formularios del sistema, presentes y futuros. La
# alternativa —un mensaje escrito a mano por campo en cada esquema— seria el
# mismo texto repetido en cuarenta lugares, que es justamente lo que este
# archivo existe para eliminar.

# El nombre del campo como lo lee una persona. Sin esto, "El valor no puede ser
# mayor que 40" no dice nada: el campo se llama `cantidad_pisos`.
CAMPOS_LEGIBLES: dict[str, str] = {
    # sesion y usuarios
    "username": "el email",
    "email": "el email",
    "password": "la contraseña",
    "nombre": "el nombre",
    "rol": "el rol",
    "telefono": "el teléfono",
    "activo": "el estado",
    # edificio
    "direccion": "la dirección",
    "cp": "el código postal",
    "cuit": "el CUIT",
    "latitud": "la latitud",
    "longitud": "la longitud",
    "cantidad_pisos": "la cantidad de pisos",
    "unidades_por_piso": "las unidades por piso",
    # configuracion
    "admin_consorcio_id": "el Administrador de Consorcio",
    "encargado_id": "el Encargado",
    "dias_vencimiento_expensas": "el día de vencimiento",
    "recargo_mora_porcentual": "el recargo por mora",
    "cbu": "el CBU",
    "alias_cbu": "el alias",
    "contacto_emergencia_nombre": "el nombre del contacto de emergencia",
    "contacto_emergencia_telefono": "el teléfono del contacto de emergencia",
    "roles_habilitados": "los roles habilitados",
    # estructura
    "numero": "el número",
    "orden": "la posición",
    "identificador": "el identificador",
    "m2": "la superficie",
    "propietario_id": "el propietario",
    "inquilino_id": "el inquilino",
    "tipo": "el tipo",
    "departamento_id": "la unidad",
    "capacidad": "la capacidad",
    "reglas_uso": "las reglas de uso",
    # coeficientes
    "coeficiente": "el coeficiente",
    "criterio": "el criterio",
    "sobrescribir": "la confirmación",
}

# Las plantillas por tipo de problema de Pydantic. `{campo}` es el nombre
# legible y el resto sale del contexto que informa la propia validacion.
_PLANTILLAS_DE_VALIDACION: dict[str, str] = {
    "missing": "Completá {campo}.",
    "string_too_short": "{campo} necesita al menos {min_length} caracteres.",
    "string_too_long": "{campo} admite hasta {max_length} caracteres.",
    "greater_than": "{campo} tiene que ser mayor que {gt}.",
    "greater_than_equal": "{campo} no puede ser menor que {ge}.",
    "less_than": "{campo} tiene que ser menor que {lt}.",
    "less_than_equal": "{campo} no puede ser mayor que {le}.",
    "int_parsing": "{campo} tiene que ser un número entero.",
    "int_type": "{campo} tiene que ser un número entero.",
    "decimal_parsing": "{campo} tiene que ser un número.",
    "decimal_type": "{campo} tiene que ser un número.",
    "float_parsing": "{campo} tiene que ser un número.",
    "decimal_max_places": "{campo} admite hasta {decimal_places} decimales.",
    "bool_parsing": "{campo} tiene que ser sí o no.",
    "bool_type": "{campo} tiene que ser sí o no.",
    "string_type": "{campo} tiene que ser texto.",
    "list_type": "{campo} tiene que ser una lista.",
    "too_short": "{campo} necesita al menos {min_length} elementos.",
    "too_long": "{campo} admite hasta {max_length} elementos.",
    "extra_forbidden": "{campo} no es un campo de este formulario.",
    "json_invalid": "El pedido no llegó en un formato que el servidor entienda.",
    "literal_error": "{campo} no tiene un valor válido.",
    "enum": "{campo} no tiene un valor válido.",
}

# Lo que informa `email-validator` cuando el email esta mal. Viene como
# `value_error` igual que los validadores propios, pero su texto es en ingles
# ("An email address must have an @-sign"), asi que se reconoce por el `reason`
# del contexto y se contesta con texto propio.
_PREFIJO_EMAIL_INVALIDO = "value is not a valid email address"


def nombre_legible(campo: str) -> str:
    """El campo como lo lee una persona, o el nombre crudo si no esta mapeado.

    Devolver el nombre crudo y no "un campo" es deliberado: si alguna vez
    aparece un `detalle_de_pago` sin traducir, el mensaje va a quedar raro y
    **se va a notar**, que es lo que hace que se agregue al diccionario. Un
    "revisá un campo del formulario" generico no se nota nunca.
    """
    return CAMPOS_LEGIBLES.get(campo, campo)


def _con_mayuscula(frase: str) -> str:
    """La primera letra en mayuscula.

    Hace falta porque varias plantillas empiezan con el nombre del campo —"{campo}
    no puede ser mayor que {le}"— y el nombre va en minuscula para poder usarse
    en el medio de una oracion ("Completá la cantidad de pisos"). Sin esto, la
    pantalla muestra "la cantidad de pisos no puede ser mayor que 40", con
    minuscula inicial, que se lee como una frase cortada.
    """
    return frase[:1].upper() + frase[1:] if frase else frase


def frase_de_validacion(problema: dict[str, Any]) -> str:
    """Un problema de Pydantic, en castellano.

    `problema` es un elemento de `exc.errors()`.
    """
    tipo = problema.get("type", "")
    partes = [str(p) for p in problema.get("loc", ()) if p != "body"]
    campo = nombre_legible(partes[-1]) if partes else "el formulario"
    contexto = problema.get("ctx") or {}

    # Los validadores propios del proyecto ya escriben su mensaje en
    # castellano, y es mejor que cualquier plantilla generica: "El coeficiente
    # admite hasta 3 decimales" sabe cosas que el tipo de error no. Llegan como
    # `value_error` con la excepcion en el contexto.
    if tipo == "value_error":
        propio = contexto.get("error")
        if propio is not None and not str(propio).startswith(_PREFIJO_EMAIL_INVALIDO):
            return _con_mayuscula(str(propio))
        return _con_mayuscula(f"escribí {campo} con un formato válido.")

    plantilla = _PLANTILLAS_DE_VALIDACION.get(tipo)
    if plantilla is None:
        # Un tipo que todavia no esta traducido no deja al usuario sin
        # explicacion: nombra el campo, que es la mitad de la informacion, y se
        # agrega la plantilla cuando aparezca.
        return _con_mayuscula(f"revisá {campo}.")

    try:
        return _con_mayuscula(plantilla.format(campo=campo, **contexto))
    except (KeyError, IndexError):
        return _con_mayuscula(f"revisá {campo}.")


# ===========================================================================
# LOS MANEJADORES
# ===========================================================================


def _respuesta(
    codigo: str,
    mensaje: str,
    http: int,
    campos: dict[str, str] | None = None,
    cabeceras: dict[str, str] | None = None,
) -> JSONResponse:
    """La unica forma en la que este sistema devuelve un error.

    `detail` viaja ademas de `mensaje`, con el mismo texto, y no es una
    duplicacion por descuido: es el campo que usa FastAPI por convencion y el
    que lee cualquier cliente generico —incluido el "Try it out" de `/docs`—.
    El frontend del proyecto usa `codigo` y `mensaje`; `detail` existe para
    todo lo demas.
    """
    cuerpo: dict[str, Any] = {
        "codigo": codigo,
        "mensaje": mensaje,
        "campos": campos or {},
        "detail": mensaje,
    }
    return JSONResponse(status_code=http, content=cuerpo, headers=cabeceras)


# Para los `HTTPException` que no levanta este catalogo: los de FastAPI (una
# ruta que no existe, un metodo que no corresponde) y el 401 del esquema de
# OAuth2. No se traducen a un codigo inventado: se los mapea al codigo
# generico que corresponde a su situacion.
_CODIGO_POR_ESTADO: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: PEDIDO_INVALIDO,
    status.HTTP_401_UNAUTHORIZED: SESION_INVALIDA,
    status.HTTP_403_FORBIDDEN: SIN_PERMISO,
    status.HTTP_404_NOT_FOUND: NO_ENCONTRADO,
    status.HTTP_405_METHOD_NOT_ALLOWED: METODO_NO_PERMITIDO,
    status.HTTP_409_CONFLICT: NECESITA_CONFIRMACION,
    status.HTTP_422_UNPROCESSABLE_ENTITY: DATOS_INVALIDOS,
    status.HTTP_500_INTERNAL_SERVER_ERROR: ERROR_INTERNO,
}


def registrar_manejadores(app: FastAPI) -> None:
    """Engancha los tres manejadores en la aplicacion.

    Se llama una vez desde `main.py`. Vive aca y no alla para que el catalogo y
    la forma de la respuesta esten en el mismo archivo: son la misma decision.
    """

    @app.exception_handler(ErrorDeNegocio)
    async def _error_de_negocio(_: Request, exc: ErrorDeNegocio) -> JSONResponse:
        return _respuesta(
            exc.codigo, exc.mensaje, exc.http, exc.campos, exc.cabeceras
        )

    @app.exception_handler(RequestValidationError)
    async def _datos_invalidos(_: Request, exc: RequestValidationError) -> JSONResponse:
        problemas = exc.errors()

        campos: dict[str, str] = {}
        for problema in problemas:
            partes = [str(p) for p in problema.get("loc", ()) if p != "body"]
            clave = ".".join(partes) if partes else "formulario"
            # El primero gana: si un campo tiene dos problemas, el segundo
            # normalmente es consecuencia del primero.
            campos.setdefault(clave, frase_de_validacion(problema))

        # El mensaje general es la frase del primer campo con problema, no un
        # "revisá el formulario": el aviso de la pantalla muestra un solo
        # renglon, y ese renglon tiene que decir que arreglar.
        mensaje = (
            frase_de_validacion(problemas[0])
            if problemas
            else CATALOGO[DATOS_INVALIDOS].plantilla
        )

        return _respuesta(
            DATOS_INVALIDOS,
            mensaje,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            campos,
        )

    @app.exception_handler(ExcepcionHTTP)
    async def _excepcion_http(_: Request, exc: ExcepcionHTTP) -> JSONResponse:
        codigo = _CODIGO_POR_ESTADO.get(exc.status_code, ERROR_INTERNO)

        # Si el texto es el que puso FastAPI ("Not Found", "Method Not
        # Allowed"), se usa el del catalogo: esos dos estan en ingles y los ve
        # cualquiera que escriba una URL a mano.
        detalle = exc.detail if isinstance(exc.detail, str) else ""
        mensaje = (
            detalle
            if detalle and not _parece_de_la_libreria(detalle)
            else CATALOGO[codigo].plantilla
        )

        # Las cabeceras se conservan: el 401 del esquema de OAuth2 trae
        # `WWW-Authenticate`, y perderlo cambia como se comporta un cliente
        # estandar frente a una sesion vencida.
        cabeceras = dict(exc.headers) if exc.headers else None

        return _respuesta(codigo, mensaje, exc.status_code, None, cabeceras)


# Los textos que pone Starlette cuando nadie puso uno. Son en ingles y no son
# mensajes de negocio.
_DE_LA_LIBRERIA = frozenset(
    {
        "Not Found",
        "Method Not Allowed",
        "Internal Server Error",
        "Unprocessable Entity",
        "Forbidden",
        "Unauthorized",
        "Bad Request",
        "Conflict",
    }
)


def _parece_de_la_libreria(detalle: str) -> bool:
    return detalle.strip() in _DE_LA_LIBRERIA

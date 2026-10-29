"""Hasheo de contrasenias y emision de tokens de acceso.

Dos responsabilidades, las dos puramente criptograficas:

- ``hashear_password`` / ``verificar_password`` — bcrypt, usado directo.
- ``crear_token_de_acceso`` / ``decodificar_token`` — JWT HS256, 60 minutos.

Este modulo NO sabe que existe la base de datos ni que existe HTTP: recibe
strings y devuelve strings. Quien busca al usuario, quien valida que este
activo y quien decide que puede hacer son otros (`core/dependencies.py`, en
F1-T08, y `services/autorizacion.py`).

============================================================================
LA CONTRASENIA EN TEXTO PLANO NO SE GUARDA, NO SE LOGUEA Y NO SE DEVUELVE
============================================================================

En ningun entorno, ni siquiera en modo test. Por eso ninguna excepcion de este
modulo incluye la contrasenia en su mensaje, ni siquiera parcialmente: los
mensajes de error terminan en logs, y un log con contrasenias es una filtracion
con fecha diferida.

============================================================================
POR QUE PyJWT Y bcrypt DIRECTO, Y NO python-jose Y passlib
============================================================================

El Roadmap decia `passlib`/bcrypt y `python-jose`. Lo cambie el 2026-10-28, al
escribir este modulo:

- **python-jose** 3.3.0 arrastra CVE-2024-33663 (confusion de algoritmo) y
  CVE-2024-33664 (denegacion de servicio por JWE comprimido). El primero sigue
  reportado como arreglo incompleto hasta 3.5.0, y la libreria esta casi sin
  mantenimiento. Firmar los JWT del sistema con eso no se sostiene cuando el
  proyecto tiene una seccion de lineamientos de seguridad que lo va a mirar.
- **passlib** tiene su ultima release en enero de 2020, y era la unica razon
  por la que bcrypt estaba clavado en 4.0.1. Sacandola, bcrypt queda al dia.

El formato del hash es identico ($2b$), asi que no hubo nada que migrar.
"""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core import config

# --------------------------------------------------------- contrasenias -----

# bcrypt no acepta mas de 72 BYTES. El limite es en bytes y no en caracteres, y
# esa diferencia importa de verdad en castellano: con UTF-8 cada caracter
# acentuado ocupa 2 bytes, asi que "contrasenia" con enie y acentos llega al
# tope con bastante menos de 72 letras. Quien escribe la contrasenia cuenta
# caracteres; bcrypt cuenta bytes.
#
# Hasta bcrypt 4.0 el exceso se truncaba EN SILENCIO, lo cual es peor que
# fallar: dos contrasenias distintas que comparten los primeros 72 bytes
# resultaban equivalentes para entrar. Desde 4.1 bcrypt levanta ValueError, y
# este modulo lo convierte en un error propio con el dato que hace falta para
# explicarlo.
MAX_BYTES_PASSWORD = 72


class PasswordDemasiadoLarga(ValueError):
    """La contrasenia supera el limite de bytes que acepta bcrypt.

    Lleva el conteo de bytes y de caracteres por separado para que el mensaje
    que ve la persona pueda explicar la diferencia, que de otro modo parece
    arbitraria ("pero tiene 50 letras").
    """

    def __init__(self, bytes_recibidos: int, caracteres: int) -> None:
        self.bytes_recibidos = bytes_recibidos
        self.caracteres = caracteres
        super().__init__(
            f"La contrasenia ocupa {bytes_recibidos} bytes y el maximo es "
            f"{MAX_BYTES_PASSWORD}. Tiene {caracteres} caracteres, pero las "
            "letras acentuadas y la enie ocupan 2 bytes cada una."
        )


# ------------------------------------------- politica de contrasenia --------

MIN_CARACTERES_PASSWORD = 8

# Los requisitos como ESTRUCTURA DE DATOS y no como una cadena de `if`, por la
# misma razon por la que la matriz de roles es una estructura: se leen de un
# vistazo, se agrega o se saca uno en un solo lugar, y la lista que ve la
# persona en el frontend (F1-T13) se arma recorriendo esto mismo en vez de ser
# un texto escrito a mano que en algun momento deja de coincidir con la regla.
#
# El texto esta redactado para mostrarse tal cual, en segunda persona y
# diciendo que FALTA, no que esta mal.
_REQUISITOS: tuple[tuple[str, Callable[[str], bool]], ...] = (
    (
        f"al menos {MIN_CARACTERES_PASSWORD} caracteres",
        lambda p: len(p) >= MIN_CARACTERES_PASSWORD,
    ),
    ("una letra mayuscula", lambda p: any(c.isupper() for c in p)),
    ("una letra minuscula", lambda p: any(c.islower() for c in p)),
    ("un numero", lambda p: any(c.isdigit() for c in p)),
    # "Especial" se define por exclusion —cualquier cosa que no sea letra ni
    # numero— y no con una lista fija de simbolos permitidos. Una lista fija
    # tiene el problema de rechazar caracteres perfectamente validos que no
    # figuran en ella (el guion bajo, los signos de apertura del castellano, el
    # simbolo del euro), y lo hace con un mensaje que no se entiende: la persona
    # puso un caracter especial y el sistema le dice que falta uno.
    (
        "un caracter especial (cualquiera que no sea letra ni numero)",
        lambda p: any(not c.isalnum() for c in p),
    ),
)

# Las mayusculas y minusculas se detectan con `isupper()`/`islower()` y no
# comparando contra el alfabeto ASCII: asi "Ñandú" cuenta sus acentos y su enie
# como las letras que son. Un control hecho con a-z y A-Z le diria a quien usa
# una contrasenia en castellano que le falta una minuscula cuando no le falta.


class PasswordInsegura(ValueError):
    """La contrasenia no cumple uno o mas requisitos.

    Guarda la lista completa de lo que falta, no el primero que encontro. Un
    validador que corta en el primer problema obliga a reintentar de a una vez
    por requisito, y son cinco: en el peor caso, cinco rechazos seguidos para
    enterarse de todo lo que hacia falta de entrada.
    """

    def __init__(self, faltantes: tuple[str, ...]) -> None:
        self.faltantes = faltantes
        super().__init__("La contrasenia necesita " + ", ".join(faltantes) + ".")


def requisitos_faltantes(password: str) -> tuple[str, ...]:
    """Los requisitos que la contrasenia NO cumple, en orden de la lista.

    Devuelve una tupla vacia cuando esta bien. Es la funcion que consume tanto
    el esquema de alta como —mas adelante— el texto de ayuda del frontend.
    """
    faltantes = [texto for texto, cumple in _REQUISITOS if not cumple(password)]

    # El maximo se evalua aparte porque no es un requisito que se "cumpla": es
    # un tope, y aparece en la lista solo cuando se pasa. Va al final para que
    # lo primero que se lea sea lo que falta y no lo que sobra.
    if len(password.encode("utf-8")) > MAX_BYTES_PASSWORD:
        faltantes.append(
            f"no mas de {MAX_BYTES_PASSWORD} bytes (tiene "
            f"{len(password.encode('utf-8'))}; las letras acentuadas y la enie "
            "ocupan 2 bytes cada una)"
        )

    return tuple(faltantes)


def validar_password(password: str) -> None:
    """Falla si la contrasenia no cumple la politica. No devuelve nada.

    Esta aca, al lado del hasheo y del limite de bytes, y no en el esquema de
    Pydantic, por una razon concreta: el minimo y el maximo tienen que vivir
    juntos. Si la politica estuviera en `schemas/` y el tope de 72 bytes en
    este modulo, serian dos archivos que hay que acordarse de mirar a la vez, y
    el dia que alguien suba el minimo a 80 caracteres la contradiccion recien
    aparece en ejecucion, cuando bcrypt rechaza lo que el esquema acepto.
    """
    faltantes = requisitos_faltantes(password)
    if faltantes:
        raise PasswordInsegura(faltantes)


def hashear_password(password: str) -> str:
    """Devuelve el hash bcrypt de una contrasenia en texto plano.

    Falla ruidosamente si la contrasenia excede el limite. Es deliberado que
    ACA falle y que `verificar_password` no: hashear pasa al crear o cambiar
    una contrasenia, y ahi la persona tiene que enterarse de que la suya no
    entra. Truncar en silencio seria aceptar una contrasenia distinta de la que
    la persona cree que puso.
    """
    en_bytes = password.encode("utf-8")
    if len(en_bytes) > MAX_BYTES_PASSWORD:
        raise PasswordDemasiadoLarga(len(en_bytes), len(password))

    return bcrypt.hashpw(en_bytes, bcrypt.gensalt()).decode("utf-8")


def verificar_password(password: str, password_hash: str) -> bool:
    """Compara una contrasenia en texto plano contra su hash.

    Devuelve False en vez de levantar excepcion ante CUALQUIER entrada mala:
    una contrasenia larguisima, un hash vacio, un hash con formato invalido.
    Esto es a proposito y es lo contrario de `hashear_password`.

    Dos razones. Una, operativa: esta funcion corre en el login, y una
    excepcion ahi es un 500 en vez de un "credenciales invalidas" — alguien
    pegando basura en el formulario tiraria errores del servidor. Dos, de
    seguridad: si una entrada malformada diera 500 y una contrasenia incorrecta
    diera 401, la diferencia entre las dos respuestas seria informacion gratis
    sobre que hay guardado del otro lado.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ----------------------------------------------------------------- JWT ------


class TokenInvalido(Exception):
    """El token no se pudo decodificar: firma mala, vencido o mal formado.

    Es un solo error para los tres casos, a proposito. Distinguir "vencido" de
    "firma invalida" hacia afuera le diria a quien prueba tokens al azar cual
    de sus intentos estuvo mas cerca. Adentro, el detalle igual queda en
    `causa` para poder diagnosticar.
    """

    def __init__(self, mensaje: str = "Token invalido o vencido", causa: str = "") -> None:
        self.causa = causa
        super().__init__(mensaje)


def crear_token_de_acceso(usuario_id: int, minutos: int | None = None) -> str:
    """Emite el JWT de sesion de un usuario.

    El token lleva lo MINIMO indispensable: a quien identifica y hasta cuando
    vale. Ni el rol, ni el email, ni los edificios que alcanza.

    Que no lleve el rol es una decision, no un olvido. Un token vive 60 minutos,
    y en esos 60 minutos a un usuario le pueden cambiar el rol o desactivarlo.
    Si el rol viajara en el token, cada endpoint tendria la tentacion de
    confiar en el, y estaria autorizando con un dato viejo: un usuario
    degradado seguiria operando como administrador hasta que su token venza.
    Por eso `core/dependencies.py` (F1-T08) va a la base en cada request.

    El Documento Tecnico ya advierte exactamente esto a proposito de la lista
    de edificios que la version anterior del proyecto queria meter en el token
    y nunca poblo: no escribir codigo que ASUMA que el token trae el alcance.
    """
    ahora = datetime.now(timezone.utc)
    vence_en = minutos if minutos is not None else config.JWT_MINUTOS_EXPIRACION

    cuerpo = {
        # `sub` va como string porque asi lo exige el estandar de JWT, y PyJWT
        # lo valida: un `sub` numerico hace fallar la decodificacion. Se
        # convierte de vuelta a int al leerlo.
        "sub": str(usuario_id),
        "iat": ahora,
        "exp": ahora + timedelta(minutes=vence_en),
    }

    return jwt.encode(cuerpo, config.JWT_SECRETO, algorithm=config.JWT_ALGORITMO)


def decodificar_token(token: str) -> dict[str, Any]:
    """Valida la firma y el vencimiento de un token, y devuelve su contenido.

    El `algorithms` explicito y acotado a UNO es la linea mas importante del
    modulo. Es la defensa contra la familia de ataques de confusion de
    algoritmo: sin esa lista, quien recibe el token acepta el algoritmo que el
    PROPIO token declara en su encabezado, y entonces alcanza con mandar uno
    firmado con `alg: none` —o con HMAC usando la clave publica como secreto—
    para fabricarse una sesion. Es la clase de vulnerabilidad por la que este
    proyecto dejo de usar python-jose; seria absurdo reintroducirla a mano.

    `require` pide que los dos campos esten presentes: un token sin `exp` no
    vence nunca, y si la ausencia de `exp` se aceptara, bastaria con emitir uno
    sin ese campo para tener una sesion eterna.
    """
    try:
        return jwt.decode(
            token,
            config.JWT_SECRETO,
            algorithms=[config.JWT_ALGORITMO],
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError as error:
        # Se captura InvalidTokenError y no Exception: es la base de toda la
        # jerarquia de errores de PyJWT (firma, vencimiento, formato, claims
        # faltantes), asi que cubre los casos previstos sin tragarse un error
        # de programacion que conviene que explote.
        raise TokenInvalido(causa=f"{type(error).__name__}: {error}") from error


def usuario_id_del_token(token: str) -> int:
    """El id del usuario que identifica un token ya validado.

    Existe para que ningun llamador tenga que acordarse de que `sub` viaja como
    string y hay que convertirlo. Esa conversion repartida por varios archivos
    es exactamente el tipo de detalle que en algun lugar se olvida, y comparar
    un string con un int no da error: da False, y el usuario "no existe".
    """
    cuerpo = decodificar_token(token)
    try:
        return int(cuerpo["sub"])
    except (KeyError, TypeError, ValueError) as error:
        raise TokenInvalido(causa=f"sub no es un id valido: {error}") from error

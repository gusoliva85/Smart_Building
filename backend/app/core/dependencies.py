"""Dependencias compartidas de los endpoints.

Vive aca `obtener_usuario_actual`, que es la puerta de entrada de **todo**
endpoint protegido del sistema: decodifica el token, busca al usuario y valida
que siga teniendo permitido entrar.

============================================================================
NINGUNA REGLA DE PERMISO SE ESCRIBE DENTRO DEL CUERPO DE UN ENDPOINT
============================================================================

Esta dependencia responde "quien es". Lo que ese quien puede hacer lo responde
`services/autorizacion.py`, consultado desde dependencias de autorizacion que
se van sumando a medida que haya pantallas que las necesiten. Un endpoint que
decide permisos por su cuenta es un permiso que no esta en la matriz, y por lo
tanto uno que nadie puede auditar leyendo un solo archivo.

============================================================================
POR QUE ESTE ARCHIVO NACE EN F1-T07 Y NO EN F1-T08, QUE ES SU TAREA
============================================================================

Porque `GET /api/auth/me` no puede existir sin el: la tarea F1-T07 pide
explicitamente que el estado del usuario se verifique en cada request y no solo
la firma del token, y eso es esta dependencia. La alternativa era escribir una
version descartable dentro del router y rehacerla una tarea despues, que es
exactamente la clase de duplicacion que el Roadmap evita.

Lo que queda para F1-T08 es lo que todavia no se puede construir: exponer el
ALCANCE del usuario — sobre que edificios o unidades opera — que necesita los
modelos `Edificio` y `Departamento`, y esos nacen en F1-T18 y F1-T19.

============================================================================
LAS DOS PREGUNTAS, Y POR QUE SON DOS DEPENDENCIAS Y NO UNA
============================================================================

  - `obtener_usuario_actual` responde **quien es**. Si falla, es 401.
  - `exigir_roles(...)` y `exigir_que_pueda_escribir` responden **si puede**.
    Si fallan, es 403.

La distincion de codigos no es cosmetica: el envoltorio de `fetch` del frontend
trata el 401 limpiando la sesion y mandando al login. Devolver 401 donde
corresponde un 403 desloguearia a alguien que esta perfectamente logueado y
solo intento algo que no le toca, y el error que veria —"tu sesion vencio"— no
tiene nada que ver con lo que paso.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config, security
from app.database import obtener_db
from app.models.usuario import Usuario
from app.services import autorizacion

# `tokenUrl` es lo que hace funcionar el boton "Authorize" de /docs: le dice a
# la interfaz a donde mandar el usuario y la contrasenia para obtener el token.
# Va sin barra inicial, relativo, porque asi lo resuelve bien tanto en local
# como detras del reescribido de rutas de Vercel.
#
# `auto_error=False` es necesario para que el mensaje de error sea nuestro.
# Con el valor por defecto, cuando falta el header `Authorization` el propio
# esquema corta antes de que esta dependencia corra y responde
# `{"detail": "Not authenticated"}`: en ingles, y distinto del mensaje que da
# el mismo endpoint cuando el token esta vencido o es invalido. O sea, dos
# textos para la misma situacion —"no estas autenticado"— y uno de los dos en
# otro idioma que el resto de la aplicacion, apareciendo en la pantalla del
# usuario. Con `False`, el token llega como `None` y el rechazo lo da esta
# funcion, siempre con el mismo mensaje.
esquema_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{config.PREFIJO_API[1:]}/auth/login",
    auto_error=False,
)


# Un solo mensaje para todos los motivos de rechazo. Distinguir "token vencido"
# de "firma invalida" de "usuario inactivo" hacia afuera le iria contando a
# quien prueba credenciales cual de sus intentos estuvo mas cerca.
_NO_AUTORIZADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudo validar la sesion. Volve a iniciar sesion.",
    # Sin este header la respuesta no cumple el estandar de HTTP para un 401, y
    # el boton "Authorize" de /docs no se da cuenta de que tiene que volver a
    # pedir credenciales.
    headers={"WWW-Authenticate": "Bearer"},
)


def obtener_usuario_actual(
    token: Annotated[str | None, Depends(esquema_oauth2)],
    db: Annotated[Session, Depends(obtener_db)],
) -> Usuario:
    """El usuario de la sesion, o 401.

    Hace tres cosas, y las tres son necesarias en cada request:

    1. Valida la firma y el vencimiento del token.
    2. Busca al usuario en la base.
    3. Verifica que siga **activo**.

    El punto 3 es el que suele faltar, y es el que hace que la baja de un
    usuario sea efectiva de verdad. Un token vive 60 minutos: si solo se
    validara la firma, alguien desactivado seguiria operando normalmente hasta
    que su token venza, con todos sus permisos intactos. Y el punto 2 tampoco es
    de adorno: un usuario borrado de la base tendria un token con firma
    perfectamente valida.

    Devuelve el modelo de SQLAlchemy y no un esquema, a proposito: quien la usa
    casi siempre necesita consultar o modificar algo relacionado con ese
    usuario, y volver a buscarlo seria una consulta extra por request.
    """
    # `None` es el caso "no vino el header Authorization", que con
    # `auto_error=False` llega hasta acá en vez de cortar antes.
    if token is None:
        raise _NO_AUTORIZADO

    try:
        usuario_id = security.usuario_id_del_token(token)
    except security.TokenInvalido:
        raise _NO_AUTORIZADO from None

    usuario = db.scalar(select(Usuario).where(Usuario.id == usuario_id))

    if usuario is None or not usuario.activo:
        raise _NO_AUTORIZADO

    return usuario


# Alias para las firmas de los endpoints. Escribir
# `usuario: UsuarioActual` es mas legible que repetir el `Annotated[...]`
# completo en cada endpoint, y evita que alguno lo declare distinto.
UsuarioActual = Annotated[Usuario, Depends(obtener_usuario_actual)]

SesionDB = Annotated[Session, Depends(obtener_db)]
"""La sesion de base de datos, para las firmas de los endpoints.

Mismo motivo que el alias de arriba: repetir `Annotated[Session,
Depends(obtener_db)]` en cada endpoint es la clase de linea que alguien copia
mal una vez —con otra dependencia, o sin `Depends`— y el error aparece en
ejecucion y no al importar.
"""


# ---------------------------------------------------------------------------
# AUTORIZACION
#
# Estas dependencias no deciden nada por su cuenta: preguntan a
# `services/autorizacion.py`. Son el puente entre la matriz —que es logica pura
# y no sabe que existe HTTP— y los endpoints.
# ---------------------------------------------------------------------------


def _prohibido(mensaje: str) -> HTTPException:
    """Un 403 con un mensaje de negocio.

    Sin `WWW-Authenticate`, a proposito: ese header significa "volve a
    autenticarte", y acá la autenticacion ya salio bien. Lo que falta son
    permisos, y volver a loguearse no los da.
    """
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=mensaje)


def exigir_roles(*roles: str) -> Callable[[Usuario], Usuario]:
    """Dependencia que solo deja pasar a los roles indicados.

    Se usa asi, en la firma del endpoint:

        @router.post("/usuarios")
        def crear(usuario: Annotated[Usuario, Depends(exigir_roles(ADMIN_GENERAL))]):

    **Valida los nombres de rol al construirse, no al recibir el request.** Es
    la parte importante de esta funcion. Como las dependencias se declaran al
    importar el modulo del router, un rol mal escrito —`"encargdo"`— revienta
    al arrancar la aplicacion, con el mensaje de `autorizacion.obtener`. Si se
    validara al atender el request, ese endpoint quedaria rechazando a
    **todos** para siempre, sin error visible en ningun log: un rol que no
    existe no coincide con nadie. Es un agujero que se nota el dia que alguien
    reporta que no puede entrar a una pantalla, meses despues.
    """
    if not roles:
        raise ValueError(
            "exigir_roles() sin roles no deja pasar a nadie. Si el endpoint es "
            "para cualquier usuario autenticado, usar UsuarioActual."
        )

    for rol in roles:
        autorizacion.obtener(rol)  # revienta aca si esta mal escrito

    permitidos = frozenset(roles)
    etiquetas = ", ".join(autorizacion.etiqueta(r) for r in roles)

    def verificar(usuario: UsuarioActual) -> Usuario:
        if usuario.rol not in permitidos:
            raise _prohibido(f"Esta accion es solo para: {etiquetas}.")
        return usuario

    return verificar


def exigir_que_pueda_escribir(usuario: UsuarioActual) -> Usuario:
    """Rechaza a los roles de solo lectura.

    Hoy el unico es el Auditor, y por eso mismo hace falta que esta dependencia
    sea independiente del rol. El Auditor **ve todo**: cualquier endpoint de
    escritura que se proteja solo con una lista de roles de lectura amplia lo
    va a dejar pasar. La condicion de solo lectura es una propiedad del rol en
    la matriz, no una ausencia de la lista.

    Va **ademas** de la verificacion de rol, no en su lugar. Y se combina por
    el decorador, no por la firma:

        @router.patch("/algo", dependencies=[Depends(exigir_que_pueda_escribir)])
        def editar(usuario: SoloAdministradores): ...

    Dos `Depends` en el mismo `Annotated` no se pueden: FastAPI corta al
    construir la ruta con "Cannot specify multiple Annotated FastAPI
    arguments". El parametro `dependencies=` del decorador existe justamente
    para las guardas que no necesitan devolver nada.
    """
    if autorizacion.es_solo_lectura(usuario.rol):
        raise _prohibido(
            f"{autorizacion.etiqueta(usuario.rol)} es un rol de consulta: "
            "puede ver la informacion pero no modificarla."
        )
    return usuario


# Atajos para los casos que se repiten en todo el proyecto. Que esten nombrados
# evita que cada router escriba su propia version de lo mismo y que una de esas
# versiones quede distinta.
SoloAdminGeneral = Annotated[Usuario, Depends(exigir_roles(autorizacion.ADMIN_GENERAL))]
"""Administracion de la plataforma: usuarios, parametros globales."""

SoloAdministradores = Annotated[
    Usuario,
    Depends(exigir_roles(autorizacion.ADMIN_GENERAL, autorizacion.ADMIN_CONSORCIO)),
]
"""Gestion de un consorcio. El Administrador General entra a todo."""

UsuarioQuePuedeEscribir = Annotated[Usuario, Depends(exigir_que_pueda_escribir)]
"""Cualquier usuario autenticado que no sea de solo lectura."""

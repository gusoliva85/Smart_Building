"""CRUD de usuarios.

Seis endpoints:

- ``POST   /api/usuarios``             — alta (la de un administrador; el
  registro propio de una persona es ``POST /api/auth/registro``)
- ``GET    /api/usuarios``             — listado
- ``GET    /api/usuarios/opciones``    — roles y politica de contrasenia
- ``GET    /api/usuarios/{id}``        — detalle
- ``PATCH  /api/usuarios/{id}``        — edicion parcial
- ``POST   /api/usuarios/{id}/estado`` — alta o baja logica

============================================================================
POR QUE TODO ESTE MODULO ES SOLO DEL ADMINISTRADOR GENERAL EN ESTA FASE
============================================================================

El Roadmap pide un "listado filtrado segun el rol de quien consulta". Filtrar
por rol significa, en concreto, filtrar por **alcance**: un Administrador de
Consorcio tendria que ver los usuarios de SUS edificios, y el alcance es
exactamente lo que no existe todavia — necesita los modelos `Edificio` y
`Departamento`, que nacen en `F1-T18` y `F1-T19`.

Asi que la eleccion real era entre dejar el modulo solo-admin-general o darle
el acceso al Administrador de Consorcio **sin poder limitarlo**, que no es un
filtro parcial: es que vea y edite los usuarios de todos los consorcios de la
plataforma, incluidos los administradores de los otros. Entre un permiso que
falta y un permiso de mas, falta.

Y hay un segundo motivo, independiente del alcance: **sin una regla que impida
crear un rol de mas permisos que el propio, el alta es una escalada de
privilegios.** Un Administrador de Consorcio que pudiera dar de alta usuarios
se daria de alta a si mismo un Administrador General. Esa regla es parte de
ampliar este modulo, no de esta tarea.

Donde se amplia esta anotado en `F1-T08`.

============================================================================
LA BAJA ES SIEMPRE LOGICA
============================================================================

No hay DELETE y no lo va a haber. Un usuario borrado fisicamente se lleva
puesta la trazabilidad de todo lo que cargo —gastos, reclamos, pagos— y esos
registros tienen que seguir diciendo quien los creo anios despues de que la
persona dejo el consorcio.
"""

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import errores, security
from app.core.dependencies import SesionDB, SoloAdminGeneral
from app.models.usuario import Usuario
from app.schemas.usuario import (
    CambioDeEstado,
    OpcionesDeAlta,
    PoliticaDePassword,
    RolDisponible,
    UsuarioCrear,
    UsuarioEditar,
    UsuarioRespuesta,
)
from app.services import autorizacion

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

# `409` NO se usa para el email repetido, y vale aclarar por que: en este
# proyecto ese codigo ya tiene significado reservado. El envoltorio de `fetch`
# del frontend marca `error.necesitaConfirmacion = estado === 409`, asi que un
# 409 hace que la pantalla ofrezca confirmar y repetir la operacion — que es lo
# ultimo que corresponde ante un email duplicado, porque repetirla va a fallar
# igual. Es un 400: el pedido esta mal y no hay nada que confirmar.
#
# Que el significado de un error dependa del codigo HTTP es justamente la
# limitacion que resuelve el catalogo de `F1-T29`, con codigos propios.
_CODIGO_EMAIL_REPETIDO = status.HTTP_400_BAD_REQUEST
_MENSAJE_EMAIL_REPETIDO = "Ya existe un usuario con ese email."


def _buscar(db: Session, usuario_id: int) -> Usuario:
    """El usuario, o un 404 con mensaje.

    Devuelve tambien los inactivos: un administrador tiene que poder ver y
    reactivar a alguien que esta de baja, y si este buscador los escondiera no
    habria forma de llegar a ellos desde la API.
    """
    usuario = db.scalar(select(Usuario).where(Usuario.id == usuario_id))
    if usuario is None:
        # El mensaje del catalogo ya no nombra el id, y es a proposito: un id
        # interno no le dice nada a quien esta del otro lado de la pantalla, y
        # la regla `FX-T11` pide que ningun error muestre estructura interna.
        raise errores.ErrorDeNegocio(errores.USUARIO_NO_ENCONTRADO)
    return usuario


def _verificar_que_no_se_desactiva_a_si_mismo(
    quien_edita: Usuario, objetivo: Usuario
) -> None:
    """La regla que no se negocia de esta tarea.

    **Esto no es teorico.** Un Administrador General se desactivo a si mismo
    probando el boton: el login rechaza usuarios inactivos, hace falta ser
    administrador para reactivar a alguien, y la cuenta quedo irrecuperable.
    Hubo que reparar la base a mano.

    Vive en una funcion y no escrita dos veces porque la tiene que aplicar
    tanto el PATCH con `activo: false` como el endpoint de estado. Dos copias
    de la misma regla es una copia que en algun momento queda sin corregir.
    """
    if quien_edita.id == objetivo.id:
        raise errores.ErrorDeNegocio(errores.NO_PODES_DESACTIVARTE)


def _verificar_que_no_se_cambia_el_rol_a_si_mismo(
    quien_edita: Usuario, objetivo: Usuario, rol_nuevo: str
) -> None:
    """Misma familia que la anterior, y por eso esta al lado.

    El Roadmap nombra la auto-desactivacion, pero cambiarse el rol a uno mismo
    deja exactamente el mismo estado irrecuperable y por el mismo camino: un
    Administrador General que se pone rol `propietario` pierde en ese instante
    el permiso para volver a cambiarselo, y necesita a otro administrador —o
    una reparacion a mano— para salir. No hace falta ni que sea un error de
    dedo: "me bajo el rol para ver como queda la pantalla" alcanza.

    Y cierra el ultimo camino al sistema sin ningun administrador activo. Con
    las dos reglas juntas, toda baja y toda degradacion se la aplica
    **otro** usuario, que por definicion sigue activo y sigue siendo
    administrador.
    """
    if quien_edita.id == objetivo.id and rol_nuevo != objetivo.rol:
        raise errores.ErrorDeNegocio(errores.NO_PODES_CAMBIARTE_EL_ROL)


def _guardar(db: Session, usuario: Usuario) -> Usuario:
    """Confirma la transaccion traduciendo el choque de email a un 400.

    La unicidad del email la garantiza el indice de la tabla y no una consulta
    previa, a proposito: entre el "¿ya existe?" y el INSERT hay una ventana en
    la que otro request puede insertar el mismo email. La consulta previa
    existe igual, pero solo para dar el mensaje; **la garantia es esta.**
    """
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise errores.ErrorDeNegocio(errores.EMAIL_REPETIDO) from None
    db.refresh(usuario)
    return usuario


def _verificar_que_el_email_esta_libre(
    db: Session, email: str, excepto_id: int | None = None
) -> None:
    """Chequeo previo, solo para el mensaje de error.

    `excepto_id` es necesario en la edicion: guardar a alguien con el email que
    ya tenia no es un duplicado, y sin esta excepcion cualquier PATCH que
    reenvie el email sin cambiarlo seria rechazado.
    """
    consulta = select(Usuario.id).where(Usuario.email == email)
    if excepto_id is not None:
        consulta = consulta.where(Usuario.id != excepto_id)
    if db.scalar(consulta) is not None:
        raise errores.ErrorDeNegocio(errores.EMAIL_REPETIDO)


# ------------------------------------------------------------------- alta ----


@router.post(
    "",
    response_model=UsuarioRespuesta,
    status_code=status.HTTP_201_CREATED,
    summary="Dar de alta un usuario",
)
def crear(
    datos: UsuarioCrear,
    quien_edita: SoloAdminGeneral,
    db: SesionDB,
) -> Usuario:
    """Crea un usuario con una contrasenia inicial.

    La contrasenia llega en el cuerpo y la pone quien da el alta, porque
    todavia no hay circuito de invitacion por email. Se hashea antes de tocar
    la base y no se devuelve en la respuesta: el esquema de salida no tiene ese
    campo, asi que filtrarla requeriria agregarlo a mano.
    """
    _verificar_que_el_email_esta_libre(db, datos.email)

    usuario = Usuario(
        nombre=datos.nombre,
        email=datos.email,
        password_hash=security.hashear_password(datos.password),
        rol=datos.rol,
        telefono=datos.telefono,
    )
    db.add(usuario)
    return _guardar(db, usuario)


# --------------------------------------------------------------- lectura -----


@router.get("", response_model=list[UsuarioRespuesta], summary="Listar usuarios")
def listar(
    quien_consulta: SoloAdminGeneral,
    db: SesionDB,
) -> list[Usuario]:
    """Todos los usuarios, activos e inactivos, ordenados por nombre.

    Los inactivos **se incluyen**. Esconderlos dejaria al administrador sin
    forma de reactivar a nadie desde la pantalla, y la baja de este sistema es
    logica justamente para que la persona siga estando. El estado viaja en el
    campo `activo` y es el frontend el que lo muestra como corresponda.
    """
    return list(db.scalars(select(Usuario).order_by(Usuario.nombre)).all())


@router.get(
    "/opciones",
    response_model=OpcionesDeAlta,
    summary="Opciones que necesita el formulario de alta",
)
def opciones(
    quien_consulta: SoloAdminGeneral,
) -> OpcionesDeAlta:
    """El catalogo de roles y la politica de contrasenia, para armar el formulario.

    ========================================================================
    POR QUE ESTE ENDPOINT EXISTE
    ========================================================================

    El `<select>` de rol del alta necesita los 8 roles con su etiqueta legible
    ("Administrador de Consorcio", no `admin_consorcio`). Esas etiquetas viven
    en la matriz de `services/autorizacion.py` y hasta ahora no salian del
    backend.

    Escribirlas a mano en el JavaScript habria sido tener la matriz de roles en
    dos lugares, que es exactamente lo que la matriz existe para evitar: el dia
    que la Fase 11 agregue un rol, la pantalla seguiria ofreciendo ocho. Lo
    mismo con la politica de contrasenia: el texto de ayuda bajo el campo tiene
    que decir lo mismo que el 422 que la rechaza, con las mismas palabras.

    No lleva `db`: no toca la base. Lee dos modulos de constantes. Igual pide
    sesion de Administrador General, porque el catalogo de roles es informacion
    de la estructura interna del sistema y no hay motivo para regalarla sin
    autenticar.

    ========================================================================
    LA RUTA VA DECLARADA ANTES QUE `/{usuario_id}` Y NO ES CASUAL
    ========================================================================

    FastAPI resuelve las rutas en orden de declaracion. Si esta quedara
    despues, `/api/usuarios/opciones` entraria por el endpoint de detalle con
    `usuario_id="opciones"` y devolveria un 422 de tipo invalido — un error que
    no menciona en ningun momento el problema real, que es el orden de dos
    decoradores. Cualquier ruta literal nueva de este router va arriba de las
    que tienen parametro.
    """
    return OpcionesDeAlta(
        roles=[
            RolDisponible(
                nombre=rol.nombre,
                etiqueta=rol.etiqueta,
                alcance=rol.alcance,
                solo_lectura=rol.solo_lectura,
            )
            # Se recorre `ROLES_ASIGNABLES` y no `ROLES`, que son dos listas
            # distintas: la segunda incluye `pendiente`, que es un valor
            # legitimo de la columna pero NO un rol que alguien pueda elegir.
            # Con `ROLES` aca, el `<select>` del formulario ofreceria
            # "Pendiente de aprobación" como si fuera un rol del consorcio.
            #
            # Y se recorre la lista, no el diccionario interno, para conservar
            # el orden de la matriz, que va de mas permisos a menos. Un
            # `<select>` alfabetico pondria "Auditor" primero, y el rol que
            # mas se elige en la practica —Propietario— quedaria perdido en el
            # medio.
            for rol in (
                autorizacion.obtener(nombre)
                for nombre in autorizacion.ROLES_ASIGNABLES
            )
        ],
        # La politica la arma el esquema y no este endpoint: la misma
        # estructura la devuelve tambien `/auth/politica-password`, que es la
        # que usa el formulario de registro propio. Dos lecturas a mano de las
        # mismas constantes se desacoplan en cuanto una gane un campo.
        password=PoliticaDePassword.vigente(),
    )


@router.get("/{usuario_id}", response_model=UsuarioRespuesta, summary="Ver un usuario")
def detalle(
    usuario_id: int,
    quien_consulta: SoloAdminGeneral,
    db: SesionDB,
) -> Usuario:
    return _buscar(db, usuario_id)


# -------------------------------------------------------------- edicion ------


@router.patch(
    "/{usuario_id}", response_model=UsuarioRespuesta, summary="Editar un usuario"
)
def editar(
    usuario_id: int,
    datos: UsuarioEditar,
    quien_edita: SoloAdminGeneral,
    db: SesionDB,
) -> Usuario:
    """Modifica solo los campos que vengan en el cuerpo.

    El volcado con `exclude_unset=True` es lo que hace que esto sea un PATCH y
    no un PUT disfrazado: sin el, todo campo ausente llegaria como `None` y
    cada edicion de un telefono borraria el nombre y el rol. Es el unico lugar
    donde se lee el esquema de edicion, para que la semantica no pueda quedar
    implementada de dos maneras distintas en dos endpoints.
    """
    usuario = _buscar(db, usuario_id)
    cambios = datos.model_dump(exclude_unset=True)

    # Las dos guardas van ANTES de aplicar cualquier cambio. Si fueran despues,
    # un pedido que cambie el telefono y encima intente la auto-desactivacion
    # terminaria rechazado con el telefono ya modificado en la sesion.
    if cambios.get("activo") is False:
        _verificar_que_no_se_desactiva_a_si_mismo(quien_edita, usuario)

    if "rol" in cambios:
        _verificar_que_no_se_cambia_el_rol_a_si_mismo(
            quien_edita, usuario, cambios["rol"]
        )

    if "email" in cambios:
        _verificar_que_el_email_esta_libre(db, cambios["email"], excepto_id=usuario.id)

    for campo, valor in cambios.items():
        setattr(usuario, campo, valor)

    return _guardar(db, usuario)


# ---------------------------------------------------------------- estado -----


@router.post(
    "/{usuario_id}/estado",
    response_model=UsuarioRespuesta,
    summary="Activar o desactivar un usuario",
)
def cambiar_estado(
    usuario_id: int,
    datos: CambioDeEstado,
    quien_edita: SoloAdminGeneral,
    db: SesionDB,
) -> Usuario:
    """Da de baja o reactiva una cuenta.

    Un solo endpoint para las dos direcciones y no `/desactivar` + `/activar`,
    porque el boton del frontend (`F1-T14`) es uno que alterna: dos endpoints
    lo obligarian a elegir a cual pegarle segun el estado actual, y ese estado
    puede haber cambiado en otra pestania. Asi el pedido dice el estado que
    quiere dejar, no la transicion que cree que corresponde.

    Es idempotente: desactivar a alguien que ya esta inactivo no es un error.
    """
    usuario = _buscar(db, usuario_id)

    if not datos.activo:
        _verificar_que_no_se_desactiva_a_si_mismo(quien_edita, usuario)

    usuario.activo = datos.activo
    return _guardar(db, usuario)

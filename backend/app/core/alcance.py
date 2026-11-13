"""Que edificios alcanza cada usuario.

============================================================================
QUE PREGUNTA RESPONDE ESTE ARCHIVO, Y POR QUE NO ES LA DE `autorizacion.py`
============================================================================

`services/autorizacion.py` responde **que puede hacer un rol**: crear usuarios,
ver el financiero del edificio, escribir o solo leer. Es logica pura y no sabe
que existe una base de datos.

Lo que falta es la otra mitad: **sobre que edificios**. Un Administrador de
Consorcio puede configurar un edificio, pero no cualquiera: el suyo. Un
Propietario puede ver los espacios comunes, pero los de su edificio. Esa
pregunta no se puede responder sin consultar la base, asi que no vive en la
matriz — vive aca.

Es la deuda que `core/dependencies.py` dejo anotada en `F1-T07`: "lo que queda
para F1-T08 es exponer el ALCANCE del usuario, que necesita los modelos
`Edificio` y `Departamento`". Esos modelos nacieron en `F1-T18` y `F1-T19`, y
`F1-T23` es la primera tarea que necesita el alcance de verdad, porque es la
primera que tiene un endpoint que **no es admin-only** (el listado de espacios
comunes).

============================================================================
DOS FUNCIONES, Y LA DIFERENCIA IMPORTA
============================================================================

  - `limitar_a_los_que_administra(consulta, usuario)` filtra una consulta: es
    para los endpoints de ESCRITURA y para el listado de la cartera. Devuelve
    los edificios que esa persona administra.
  - `puede_ver(db, usuario, edificio)` responde si esa persona tiene algo que
    hacer en ese edificio: lo administra, trabaja ahi, vive ahi o lo tiene
    asignado. Es para los endpoints de LECTURA que no son admin-only.

La primera es un `WHERE` y la segunda un booleano porque se usan distinto: la
escritura siempre opera sobre un edificio puntual, mientras el filtro de la
consulta evita traer de la base lo que despues habria que descartar.

**El filtro va en la consulta y no en la pantalla.** Un filtro que vive en el
frontend no es un permiso: la respuesta ya trajo los datos de los otros
edificios y cualquiera los lee en la pestania de red del navegador.
"""

from sqlalchemy import exists, false, or_, select
from sqlalchemy.orm import Session

from app.models.edificio import Departamento, Edificio, Piso
from app.models.usuario import AsignacionEdificio, Usuario
from app.services import autorizacion


def administra_todo(usuario: Usuario) -> bool:
    """El Administrador General alcanza la cartera entera.

    Esta en una funcion y no escrito como comparacion en cada endpoint para que
    el dia que la Fase 11 agregue otro rol de alcance de cartera haya un solo
    lugar que lo diga.
    """
    return usuario.rol == autorizacion.ADMIN_GENERAL


def limitar_a_los_que_administra(consulta, usuario: Usuario):
    """Restringe una consulta de `Edificio` a los que ese usuario administra.

    El Administrador General ve todo: es quien da de alta los edificios. El
    Administrador de Consorcio, solo donde figura como tal.

    Los demas roles no llegan a usar esta funcion: los endpoints que la
    consumen piden `SoloAdministradores`. Igual devuelve "ninguno" para
    cualquier otro rol en vez de "todos", porque el default de una funcion de
    permisos tiene que ser el que no regala nada.
    """
    if administra_todo(usuario):
        return consulta
    if usuario.rol == autorizacion.ADMIN_CONSORCIO:
        return consulta.where(Edificio.admin_consorcio_id == usuario.id)
    return consulta.where(false())


def puede_ver(db: Session, usuario: Usuario, edificio: Edificio) -> bool:
    """Si esa persona tiene algo que hacer en ese edificio.

    Las cinco formas de estar vinculado a un edificio, que son las que el
    sistema sabe representar hoy:

      1. Administrador General: la cartera entera.
      2. Administrador de Consorcio: el edificio que administra.
      3. Encargado: el edificio donde trabaja.
      4. Propietario o Inquilino: el edificio donde tiene una unidad.
      5. Seguridad o Auditor: los edificios de `asignacion_edificio`.

    El Proveedor queda afuera a proposito: su alcance en la matriz es
    `ots_asignadas`, o sea que llega a un edificio por una orden de trabajo y
    no por el edificio en si. Cuando existan las ordenes (Fase 5), el permiso
    sale de la orden, no de aca.

    Devuelve `False` para cualquier rol que no este en esa lista —incluido
    `pendiente`— porque un alcance que no se sabe responder no es un alcance
    que convenga conceder.
    """
    if administra_todo(usuario):
        return True

    if usuario.rol == autorizacion.ADMIN_CONSORCIO:
        return edificio.admin_consorcio_id == usuario.id

    if usuario.rol == autorizacion.ENCARGADO:
        return edificio.encargado_id == usuario.id

    if usuario.rol in (autorizacion.PROPIETARIO, autorizacion.INQUILINO):
        # Una sola consulta con `EXISTS`: alcanza con saber si hay al menos una
        # unidad suya en el edificio, asi que no hace falta traerlas.
        tiene_unidad = (
            select(Departamento.id)
            .join(Piso, Piso.id == Departamento.piso_id)
            .where(Piso.edificio_id == edificio.id)
            .where(
                or_(
                    Departamento.propietario_id == usuario.id,
                    Departamento.inquilino_id == usuario.id,
                )
            )
        )
        return bool(db.scalar(select(exists(tiene_unidad))))

    if usuario.rol in (autorizacion.SEGURIDAD, autorizacion.AUDITOR):
        asignado = (
            select(AsignacionEdificio.id)
            .where(AsignacionEdificio.usuario_id == usuario.id)
            .where(AsignacionEdificio.edificio_id == edificio.id)
        )
        return bool(db.scalar(select(exists(asignado))))

    return False


def administra_el_edificio_de(db: Session, usuario: Usuario, unidad) -> bool:
    """Si esa persona **administra** el edificio al que pertenece esa unidad.

    Es una pregunta distinta de `puede_ver`: un propietario puede ver su
    edificio y no por eso administra nada. Esto responde "¿puede ver lo que
    todavia no se publico?", que es lo que separa a la administracion del
    residente en todo el modulo financiero.
    """
    if administra_todo(usuario):
        return True
    if usuario.rol != autorizacion.ADMIN_CONSORCIO:
        return False

    consulta = (
        select(Edificio.id)
        .join(Piso, Piso.edificio_id == Edificio.id)
        .where(Piso.id == unidad.piso_id)
        .where(Edificio.admin_consorcio_id == usuario.id)
    )
    return bool(db.scalar(select(exists(consulta))))


def puede_ver_unidad(db: Session, usuario: Usuario, unidad) -> bool:
    """Si esa persona tiene algo que hacer con **esa unidad puntual**.

    Tres formas de estar vinculado a una unidad:

      1. Quien administra el edificio donde esta (General o de Consorcio).
      2. Su propietario.
      3. Su inquilino.

    **El Encargado queda afuera a proposito.** Puede ver el edificio porque
    trabaja ahi, pero la cuenta de una unidad es informacion economica de una
    familia: cuanto debe el 3B no es asunto del encargado. Es la clase de
    permiso que se concede "porque ya veia el edificio" y despues nadie revisa.

    El Auditor tambien queda afuera hasta `F11-T05`, que es la tarea que crea
    la pantalla para vincularlo con los edificios que audita; darle hoy acceso
    a toda la cartera sin un vinculo real seria un sobre-permiso.
    """
    if administra_el_edificio_de(db, usuario, unidad):
        return True

    if usuario.rol in (autorizacion.PROPIETARIO, autorizacion.INQUILINO):
        return usuario.id in (unidad.propietario_id, unidad.inquilino_id)

    return False

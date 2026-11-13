"""CRUD anidado de la estructura del edificio (`F1-T23`).

Pisos, departamentos, cocheras y espacios comunes, todos bajo
``/api/edificios/{edificio_id}/...``, mas la asignacion y desvinculacion de
propietario o inquilino a una unidad existente.

============================================================================
POR QUE TODO ESTA ANIDADO BAJO EL EDIFICIO
============================================================================

Un piso no existe por si solo: existe en un edificio. Que eso se vea en la URL
tiene una consecuencia practica y no es estetica — **el permiso se verifica una
sola vez, sobre el edificio, y al principio**. Si las rutas fueran
``/api/pisos/{id}``, cada endpoint tendria que subir del piso al edificio para
saber si quien pide tiene algo que ver con el, y el dia que uno se olvide de
hacerlo el agujero no se ve leyendo ese endpoint: se ve comparandolo con los
otros nueve.

Aca el orden es siempre el mismo:

  1. Buscar el edificio **dentro del alcance** de quien pide (404 si no).
  2. Buscar la fila hija **dentro de ese edificio** (404 si no).
  3. Validar la regla de negocio (400 si no).
  4. Guardar.

El paso 2 tambien es un permiso, no una comodidad: pedir el piso 7 del edificio
ajeno pasando el id del edificio propio tiene que dar 404, y por eso la
busqueda del hijo lleva SIEMPRE la condicion del padre.

============================================================================
UNA EXCEPCION DELIBERADA: VER LOS ESPACIOS COMUNES NO ES ADMIN-ONLY
============================================================================

Es lo que el Roadmap marca como el error de la iteracion anterior: el listado
de espacios comunes quedo restringido a administradores y dejo sin poder
reportar un reclamo sobre el SUM a Propietario, Inquilino y Encargado, que son
justamente los que estan ahi. Se descubrio recien en la Fase 3.

Asi que `GET /espacios-comunes` pide `UsuarioActual` y resuelve el alcance con
`core/alcance.puede_ver()`: lo ve cualquiera que tenga algo que hacer en ese
edificio. **Crear**, editar y borrar siguen siendo exclusivos del
administrador.

============================================================================
LOS DUPLICADOS DEVUELVEN 400, NO 409
============================================================================

El 409 esta reservado en este proyecto: el envoltorio de `fetch` del frontend
lo mapea a `error.necesitaConfirmacion` y abre un dialogo de "¿seguro?". Un
numero de piso repetido no es algo que se pueda confirmar, asi que va 400.
"""

import logging

from fastapi import APIRouter, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core import alcance
from app.core import errores
from app.core.dependencies import SesionDB, SoloAdministradores, UsuarioActual
from app.models.edificio import (
    COCHERA_FIJA,
    Cochera,
    Departamento,
    Edificio,
    EspacioComun,
    Piso,
)
from app.models.usuario import Usuario
from app.routers.edificios import buscar_edificio_que_administra, no_encontrado
from app.schemas.edificio import (
    CocheraDetalle,
    DepartamentoDetalle,
    EspacioComunDetalle,
    PisoDetalle,
)
from app.schemas.estructura import (
    CocheraCrear,
    CocheraEditar,
    DepartamentoCrear,
    DepartamentoEditar,
    EspacioComunCrear,
    EspacioComunEditar,
    PisoCrear,
    PisoEditar,
)
from app.services import autorizacion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edificios", tags=["Estructura del edificio"])


# El rol que tiene que tener realmente la persona que se asigna a una unidad.
_ROL_DEL_RESIDENTE = {
    "propietario_id": autorizacion.PROPIETARIO,
    "inquilino_id": autorizacion.INQUILINO,
}


# ---------------------------------------------------------------------------
# HELPERS
#
# Los cuatro `_buscar_*` existen para que ningun endpoint escriba su propia
# version de "buscar el hijo dentro del padre". Un endpoint que se olvide de la
# condicion del padre deja ver —y modificar— la estructura de un edificio ajeno
# con solo acertar un id.
# ---------------------------------------------------------------------------


def _no_esta(que: str) -> errores.ErrorDeNegocio:
    """El 404 de una fila hija que no esta en este edificio.

    El texto vive en el catalogo (`core/errores.py`) como el resto de los
    mensajes del sistema; lo unico que aporta cada llamada es de QUE fila
    habla. Un 404 que no dice si no encontro el piso o la unidad obliga a
    adivinar cual de los dos ids del pedido estaba mal.
    """
    return errores.ErrorDeNegocio(
        errores.NO_ENCONTRADO_EN_EL_EDIFICIO, que=que
    )


def _buscar_piso(db: Session, edificio: Edificio, piso_id: int) -> Piso:
    piso = db.scalars(
        select(Piso).where(Piso.id == piso_id, Piso.edificio_id == edificio.id)
    ).first()
    if piso is None:
        raise _no_esta("el piso")
    return piso


def buscar_departamento(
    db: Session, edificio: Edificio, departamento_id: int
) -> Departamento:
    """La unidad, si pertenece a ese edificio. Si no, 404.

    Es publica porque la usa tambien `routers/coeficientes.py`: la carga de
    coeficientes opera sobre una unidad y tiene que verificar exactamente lo
    mismo. Dos versiones de "buscar la unidad dentro del edificio" es una de mas,
    y la que se olvide de la condicion del padre deja editar la estructura de un
    edificio ajeno con solo acertar un id.
    """
    departamento = db.scalars(
        select(Departamento)
        .join(Piso, Piso.id == Departamento.piso_id)
        .where(Departamento.id == departamento_id, Piso.edificio_id == edificio.id)
    ).first()
    if departamento is None:
        raise _no_esta("la unidad")
    return departamento


def _buscar_cochera(db: Session, edificio: Edificio, cochera_id: int) -> Cochera:
    cochera = db.scalars(
        select(Cochera).where(
            Cochera.id == cochera_id, Cochera.edificio_id == edificio.id
        )
    ).first()
    if cochera is None:
        raise _no_esta("la cochera")
    return cochera


def _buscar_espacio(db: Session, edificio: Edificio, espacio_id: int) -> EspacioComun:
    espacio = db.scalars(
        select(EspacioComun).where(
            EspacioComun.id == espacio_id, EspacioComun.edificio_id == edificio.id
        )
    ).first()
    if espacio is None:
        raise _no_esta("el espacio común")
    return espacio


def _guardar(db: Session, descripcion: str) -> None:
    """El `commit` con su red.

    Las reglas de negocio ya se validaron una por una, asi que si la base
    rechaza algo igual, es un error de programacion o una carrera entre dos
    pedidos simultaneos. En los dos casos el detalle va al log y NO a la
    respuesta: un error de base nombra tablas, columnas y restricciones, y eso
    no se le muestra a nadie (regla `FX-T11`).
    """
    try:
        db.commit()
    except (IntegrityError, SQLAlchemyError):
        db.rollback()
        logger.exception("Fallo al guardar: %s", descripcion)
        raise errores.ErrorDeNegocio(
            errores.ERROR_AL_GUARDAR, que="el cambio"
        ) from None


def _verificar_residente(
    db: Session, edificio: Edificio, usuario_id: int, campo: str, propio_id: int
) -> None:
    """Valida a quien se asigna a una unidad: existe, activo, rol y edificio.

    Son cuatro verificaciones y cada una ataja un problema distinto:

    1. **Existe y esta activo.** Asignar una cuenta desactivada dejaria la
       unidad con un responsable que no puede entrar al sistema.
    2. **Tiene ESE rol en la matriz.** Un "propietario" que en realidad es
       Proveedor no ve ninguna de las pantallas del propietario, y la falla
       aparece recien cuando esa persona intenta entrar.
    3. **Ese rol esta habilitado en ESTE edificio** (`roles_habilitados`, que se
       configura en `F1-T22`). Es lo que le da sentido a esa columna: si un
       consorcio decidio no habilitar inquilinos, asignar uno igual seria
       guardar un dato que la configuracion del edificio dice que no existe.
    4. **Un inquilino no puede estar en dos unidades.** La base tambien lo
       prohibe con una restriccion de unicidad, pero una restriccion que salta
       devuelve un 500 sin explicacion: aca el mensaje dice en que unidad ya
       figura, que es lo unico que permite resolverlo.
    """
    rol_esperado = _ROL_DEL_RESIDENTE[campo]
    etiqueta = autorizacion.etiqueta(rol_esperado)

    usuario = db.scalar(select(Usuario).where(Usuario.id == usuario_id))

    if usuario is None:
        raise errores.ErrorDeNegocio(
            errores.RESIDENTE_NO_EXISTE, puesto=etiqueta
        )

    if not usuario.activo:
        raise errores.ErrorDeNegocio(
            errores.RESIDENTE_DESACTIVADO,
            nombre=usuario.nombre,
            puesto=etiqueta,
        )

    if usuario.rol != rol_esperado:
        raise errores.ErrorDeNegocio(
            errores.RESIDENTE_CON_OTRO_ROL,
            nombre=usuario.nombre,
            rol_actual=autorizacion.etiqueta(usuario.rol),
            puesto=etiqueta,
        )

    if rol_esperado not in (edificio.roles_habilitados or []):
        raise errores.ErrorDeNegocio(
            errores.ROL_NO_HABILITADO_EN_EL_EDIFICIO, puesto=etiqueta
        )

    if rol_esperado == autorizacion.INQUILINO:
        ocupada = db.scalars(
            select(Departamento).where(
                Departamento.inquilino_id == usuario_id,
                Departamento.id != propio_id,
            )
        ).first()
        if ocupada is not None:
            raise errores.ErrorDeNegocio(
                errores.INQUILINO_EN_OTRA_UNIDAD,
                nombre=usuario.nombre,
                unidad=ocupada.identificador,
            )


# ===========================================================================
# PISOS
# ===========================================================================


@router.post(
    "/{edificio_id}/pisos",
    response_model=PisoDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar un piso",
)
def crear_piso(
    edificio_id: int,
    datos: PisoCrear,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> Piso:
    """Agrega un piso. Sin `orden`, va arriba del ultimo.

    El piso nace **sin unidades**: las unidades se agregan una por una con su
    propio endpoint. Generar unidades automaticamente aca obligaria a inventar
    cuantas, y la planta que se agrega a un edificio existente casi nunca tiene
    la misma cantidad que las demas.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)

    if datos.orden is None:
        ultimo = db.scalar(
            select(func.max(Piso.orden)).where(Piso.edificio_id == edificio.id)
        )
        orden = (ultimo or 0) + 1
    else:
        orden = datos.orden

    # Las dos unicidades se verifican antes del INSERT para que el mensaje diga
    # cual de las dos se repitio. La tabla las garantiza igual.
    if db.scalars(
        select(Piso).where(Piso.edificio_id == edificio.id, Piso.numero == datos.numero)
    ).first():
        raise errores.ErrorDeNegocio(errores.PISO_REPETIDO, numero=datos.numero)

    if db.scalars(
        select(Piso).where(Piso.edificio_id == edificio.id, Piso.orden == orden)
    ).first():
        raise errores.ErrorDeNegocio(
            errores.POSICION_DE_PISO_OCUPADA, orden=orden
        )

    piso = Piso(edificio_id=edificio.id, numero=datos.numero, orden=orden)
    db.add(piso)
    _guardar(db, f"alta de piso en el edificio {edificio.id}")
    db.refresh(piso)

    return piso


@router.patch(
    "/{edificio_id}/pisos/{piso_id}",
    response_model=PisoDetalle,
    summary="Editar un piso",
)
def editar_piso(
    edificio_id: int,
    piso_id: int,
    datos: PisoEditar,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> Piso:
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)
    piso = _buscar_piso(db, edificio, piso_id)

    cambios = datos.model_dump(exclude_unset=True)

    if "numero" in cambios and cambios["numero"] != piso.numero:
        if db.scalars(
            select(Piso).where(
                Piso.edificio_id == edificio.id,
                Piso.numero == cambios["numero"],
                Piso.id != piso.id,
            )
        ).first():
            raise errores.ErrorDeNegocio(
                errores.PISO_REPETIDO, numero=cambios["numero"]
            )

    if "orden" in cambios and cambios["orden"] != piso.orden:
        if db.scalars(
            select(Piso).where(
                Piso.edificio_id == edificio.id,
                Piso.orden == cambios["orden"],
                Piso.id != piso.id,
            )
        ).first():
            raise errores.ErrorDeNegocio(
                errores.POSICION_DE_PISO_OCUPADA, orden=cambios["orden"]
            )

    for campo, valor in cambios.items():
        setattr(piso, campo, valor)

    _guardar(db, f"edicion del piso {piso_id}")
    db.refresh(piso)

    return piso


@router.delete(
    "/{edificio_id}/pisos/{piso_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Borrar un piso vacío",
)
def borrar_piso(
    edificio_id: int,
    piso_id: int,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> None:
    """Borra el piso solo si no tiene unidades.

    No hay borrado en cascada, y es una decision de `F1-T19`: un departamento
    puede tener expensas y pagos apuntandole, asi que darlo de baja es una
    decision con consecuencias y se toma unidad por unidad. Borrar el piso y
    llevarse las unidades por delante seria tomarla sin preguntar.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)
    piso = _buscar_piso(db, edificio, piso_id)

    cuantas = db.scalar(
        select(func.count(Departamento.id)).where(Departamento.piso_id == piso.id)
    )
    if cuantas:
        raise errores.ErrorDeNegocio(
            errores.PISO_CON_UNIDADES,
            numero=piso.numero,
            cuantas=f"{cuantas} {'unidad' if cuantas == 1 else 'unidades'}",
        )

    db.delete(piso)
    _guardar(db, f"baja del piso {piso_id}")


# ===========================================================================
# DEPARTAMENTOS
# ===========================================================================


@router.post(
    "/{edificio_id}/pisos/{piso_id}/departamentos",
    response_model=DepartamentoDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar una unidad a un piso",
)
def crear_departamento(
    edificio_id: int,
    piso_id: int,
    datos: DepartamentoCrear,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> Departamento:
    """La unidad nace vacia: sin propietario, sin inquilino y sin coeficiente.

    Un coeficiente inventado reparte plata mal sin que nadie lo note, mientras
    uno ausente lo encuentra la validacion antes de generar la primera expensa.
    Se carga en `F1-T24`.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)
    piso = _buscar_piso(db, edificio, piso_id)

    if db.scalars(
        select(Departamento).where(
            Departamento.piso_id == piso.id,
            Departamento.identificador == datos.identificador,
        )
    ).first():
        raise errores.ErrorDeNegocio(
            errores.UNIDAD_REPETIDA, identificador=datos.identificador
        )

    departamento = Departamento(
        piso_id=piso.id,
        identificador=datos.identificador,
        m2=datos.m2,
    )
    db.add(departamento)
    _guardar(db, f"alta de unidad en el piso {piso_id}")
    db.refresh(departamento)

    return departamento


@router.patch(
    "/{edificio_id}/departamentos/{departamento_id}",
    response_model=DepartamentoDetalle,
    summary="Editar una unidad, asignar o desvincular a quien la habita",
)
def editar_departamento(
    edificio_id: int,
    departamento_id: int,
    datos: DepartamentoEditar,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> Departamento:
    """Cambia la unidad y, si vienen, a su propietario o inquilino.

    Mandar `propietario_id` o `inquilino_id` en `null` **desvincula**. Un campo
    que no viaja no se toca, asi que corregir los metros cuadrados no borra al
    propietario — que es el error que un PUT comete solo.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)
    departamento = buscar_departamento(db, edificio, departamento_id)

    cambios = datos.model_dump(exclude_unset=True)

    if "identificador" in cambios and cambios["identificador"] != departamento.identificador:
        if db.scalars(
            select(Departamento).where(
                Departamento.piso_id == departamento.piso_id,
                Departamento.identificador == cambios["identificador"],
                Departamento.id != departamento.id,
            )
        ).first():
            raise errores.ErrorDeNegocio(
                errores.UNIDAD_REPETIDA, identificador=cambios["identificador"]
            )

    for campo in _ROL_DEL_RESIDENTE:
        if cambios.get(campo) is not None:
            _verificar_residente(
                db, edificio, cambios[campo], campo, departamento.id
            )

    for campo, valor in cambios.items():
        setattr(departamento, campo, valor)

    # La misma persona no puede ser propietaria e inquilina de la misma unidad.
    # Hoy es inalcanzable —cada puesto exige su rol y un usuario tiene uno
    # solo—, igual que el cruce de responsables del edificio en `F1-T22`. Queda
    # como respaldo del CHECK `ck_departamentos_propietario_distinto_inquilino`,
    # que si saltara devolveria un 500 sin explicacion.
    if (
        departamento.propietario_id is not None
        and departamento.propietario_id == departamento.inquilino_id
    ):
        db.rollback()
        raise errores.ErrorDeNegocio(errores.PROPIETARIO_ES_INQUILINO)

    _guardar(db, f"edicion de la unidad {departamento_id}")
    db.refresh(departamento)

    return departamento


@router.delete(
    "/{edificio_id}/departamentos/{departamento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Borrar una unidad desocupada",
)
def borrar_departamento(
    edificio_id: int,
    departamento_id: int,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> None:
    """Borra la unidad solo si no tiene a nadie y no tiene cocheras asignadas.

    Las dos condiciones son el mismo criterio: antes de borrar una fila de la
    que cuelga algo, se desarma lo que cuelga. Una unidad con propietario se
    borra "sin querer" y con ella desaparece el vinculo de esa persona con el
    edificio; una cochera fija apuntando a una unidad que ya no esta queda
    apuntando a la nada.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)
    departamento = buscar_departamento(db, edificio, departamento_id)

    if departamento.ocupado:
        raise errores.ErrorDeNegocio(
            errores.UNIDAD_CON_RESIDENTE,
            identificador=departamento.identificador,
        )

    cocheras = db.scalar(
        select(func.count(Cochera.id)).where(
            Cochera.departamento_id == departamento.id
        )
    )
    if cocheras:
        raise errores.ErrorDeNegocio(
            errores.UNIDAD_CON_COCHERAS,
            identificador=departamento.identificador,
            cuantas=(
                f"{cocheras} {'cochera' if cocheras == 1 else 'cocheras'} "
                f"asignada{'' if cocheras == 1 else 's'}"
            ),
        )

    db.delete(departamento)
    _guardar(db, f"baja de la unidad {departamento_id}")


# ===========================================================================
# COCHERAS
# ===========================================================================


def _verificar_cochera(
    db: Session, edificio: Edificio, tipo: str, departamento_id: int | None
) -> None:
    """Las dos reglas de una cochera, con el mensaje que explica cada una."""
    if departamento_id is None:
        return

    if tipo != COCHERA_FIJA:
        raise errores.ErrorDeNegocio(errores.COCHERA_ROTATIVA_ASIGNADA)

    # La unidad tiene que ser de ESTE edificio. Sin esta verificacion se podria
    # asignar una cochera a una unidad de otro consorcio pasando su id.
    buscar_departamento(db, edificio, departamento_id)


@router.post(
    "/{edificio_id}/cocheras",
    response_model=CocheraDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar una cochera",
)
def crear_cochera(
    edificio_id: int,
    datos: CocheraCrear,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> Cochera:
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)

    if db.scalars(
        select(Cochera).where(
            Cochera.edificio_id == edificio.id, Cochera.numero == datos.numero
        )
    ).first():
        raise errores.ErrorDeNegocio(
            errores.COCHERA_REPETIDA, numero=datos.numero
        )

    _verificar_cochera(db, edificio, datos.tipo, datos.departamento_id)

    cochera = Cochera(
        edificio_id=edificio.id,
        numero=datos.numero,
        tipo=datos.tipo,
        departamento_id=datos.departamento_id,
    )
    db.add(cochera)
    _guardar(db, f"alta de cochera en el edificio {edificio.id}")
    db.refresh(cochera)

    return cochera


@router.patch(
    "/{edificio_id}/cocheras/{cochera_id}",
    response_model=CocheraDetalle,
    summary="Editar una cochera",
)
def editar_cochera(
    edificio_id: int,
    cochera_id: int,
    datos: CocheraEditar,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> Cochera:
    """Edita la cochera. `departamento_id` en `null` la desasigna."""
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)
    cochera = _buscar_cochera(db, edificio, cochera_id)

    cambios = datos.model_dump(exclude_unset=True)

    if "numero" in cambios and cambios["numero"] != cochera.numero:
        if db.scalars(
            select(Cochera).where(
                Cochera.edificio_id == edificio.id,
                Cochera.numero == cambios["numero"],
                Cochera.id != cochera.id,
            )
        ).first():
            raise errores.ErrorDeNegocio(
                errores.COCHERA_REPETIDA, numero=cambios["numero"]
            )

    # Se valida el resultado FINAL y no lo que vino en el pedido: cambiar una
    # cochera fija a rotativa sin desasignar la unidad en el mismo pedido es
    # exactamente el caso que hay que detectar, y ahi `departamento_id` no
    # viaja.
    tipo_final = cambios.get("tipo", cochera.tipo)
    departamento_final = cambios.get("departamento_id", cochera.departamento_id)
    _verificar_cochera(db, edificio, tipo_final, departamento_final)

    for campo, valor in cambios.items():
        setattr(cochera, campo, valor)

    _guardar(db, f"edicion de la cochera {cochera_id}")
    db.refresh(cochera)

    return cochera


@router.delete(
    "/{edificio_id}/cocheras/{cochera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Borrar una cochera",
)
def borrar_cochera(
    edificio_id: int,
    cochera_id: int,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> None:
    """Se borra sin condiciones: de una cochera no cuelga nada todavia.

    El dia que haya reservas de cochera (Fase 7) esto gana la misma
    verificacion que tienen el piso y la unidad.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)
    cochera = _buscar_cochera(db, edificio, cochera_id)

    db.delete(cochera)
    _guardar(db, f"baja de la cochera {cochera_id}")


# ===========================================================================
# ESPACIOS COMUNES
# ===========================================================================


@router.get(
    "/{edificio_id}/espacios-comunes",
    response_model=list[EspacioComunDetalle],
    summary="Listar los espacios comunes del edificio",
)
def listar_espacios(
    edificio_id: int,
    quien_consulta: UsuarioActual,
    db: SesionDB,
) -> list[EspacioComun]:
    """**No es admin-only, y es el punto de este endpoint.**

    En la iteracion anterior este listado quedo restringido a administradores y
    dejo sin poder reportar un reclamo sobre el SUM a Propietario, Inquilino y
    Encargado, que son justamente los que estan ahi. Se descubrio recien en la
    Fase 3.

    Lo ve cualquiera que tenga algo que hacer en el edificio: quien lo
    administra, quien trabaja ahi, quien vive ahi y quien lo tiene asignado.
    Eso lo resuelve `core/alcance.puede_ver()`, que es el unico lugar del
    proyecto donde esa pregunta se contesta.
    """
    edificio = db.scalars(select(Edificio).where(Edificio.id == edificio_id)).first()

    # Quien no tiene nada que hacer en el edificio recibe el mismo 404 que si
    # no existiera: un 403 distinguible le iria contando que edificios hay.
    if edificio is None or not alcance.puede_ver(db, quien_consulta, edificio):
        raise no_encontrado()

    return list(
        db.scalars(
            select(EspacioComun)
            .where(EspacioComun.edificio_id == edificio.id)
            .order_by(EspacioComun.nombre)
        ).all()
    )


@router.post(
    "/{edificio_id}/espacios-comunes",
    response_model=EspacioComunDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar un espacio común",
)
def crear_espacio(
    edificio_id: int,
    datos: EspacioComunCrear,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> EspacioComun:
    """Crear si es exclusivo del administrador. Ver, no."""
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)

    if db.scalars(
        select(EspacioComun).where(
            EspacioComun.edificio_id == edificio.id,
            EspacioComun.nombre == datos.nombre,
        )
    ).first():
        raise errores.ErrorDeNegocio(
            errores.ESPACIO_REPETIDO, nombre=datos.nombre
        )

    espacio = EspacioComun(
        edificio_id=edificio.id,
        nombre=datos.nombre,
        capacidad=datos.capacidad,
        reglas_uso=datos.reglas_uso,
    )
    db.add(espacio)
    _guardar(db, f"alta de espacio comun en el edificio {edificio.id}")
    db.refresh(espacio)

    return espacio


@router.patch(
    "/{edificio_id}/espacios-comunes/{espacio_id}",
    response_model=EspacioComunDetalle,
    summary="Editar un espacio común",
)
def editar_espacio(
    edificio_id: int,
    espacio_id: int,
    datos: EspacioComunEditar,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> EspacioComun:
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)
    espacio = _buscar_espacio(db, edificio, espacio_id)

    cambios = datos.model_dump(exclude_unset=True)

    if "nombre" in cambios and cambios["nombre"] != espacio.nombre:
        if db.scalars(
            select(EspacioComun).where(
                EspacioComun.edificio_id == edificio.id,
                EspacioComun.nombre == cambios["nombre"],
                EspacioComun.id != espacio.id,
            )
        ).first():
            raise errores.ErrorDeNegocio(
                errores.ESPACIO_REPETIDO, nombre=cambios["nombre"]
            )

    for campo, valor in cambios.items():
        setattr(espacio, campo, valor)

    _guardar(db, f"edicion del espacio comun {espacio_id}")
    db.refresh(espacio)

    return espacio


@router.delete(
    "/{edificio_id}/espacios-comunes/{espacio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Borrar un espacio común",
)
def borrar_espacio(
    edificio_id: int,
    espacio_id: int,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> None:
    """Se borra sin condiciones por ahora.

    El dia que haya reservas (Fase 7) esto tiene que negarse a borrar un
    espacio con reservas futuras: borrarlo dejaria a varias personas con una
    reserva de un lugar que ya no existe, y sin aviso.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)
    espacio = _buscar_espacio(db, edificio, espacio_id)

    db.delete(espacio)
    _guardar(db, f"baja del espacio comun {espacio_id}")

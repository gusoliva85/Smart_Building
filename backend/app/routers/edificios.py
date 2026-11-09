"""Alta de edificios, con su estructura generada en la misma transaccion.

Tres endpoints:

- ``POST /api/edificios`` — crea el edificio y sus pisos y departamentos vacios
- ``GET  /api/edificios`` — listado con la cantidad de pisos y de unidades
- ``GET  /api/edificios/{id}`` — detalle con toda la estructura
- ``PATCH /api/edificios/{id}`` — configuracion: responsables, cobranza,
  contacto de emergencia y roles habilitados

El CRUD anidado de la estructura es `F1-T23`.

============================================================================
POR QUE EL ALTA ES SOLO DEL ADMINISTRADOR GENERAL
============================================================================

Crear un edificio es incorporar un consorcio a la plataforma. El Administrador
de Consorcio administra **el suyo**; no decide que edificios existen. Es la
matriz de `services/autorizacion.py` la que lo dice, y este modulo no la
reescribe: usa la dependencia `SoloAdminGeneral`, igual que `routers/usuarios`.

============================================================================
UNA SOLA TRANSACCION, Y POR QUE IMPORTA
============================================================================

Un edificio de 7 pisos por 4 unidades son 36 filas: el edificio, 7 pisos y 28
departamentos. Si eso se guardara de a tandas y algo fallara en la mitad,
quedaria un edificio con tres pisos y nadie sabria que le faltan cuatro — ni la
persona que lo cargo, que vio un error y va a volver a intentarlo, generando un
segundo edificio incompleto al lado del primero.

Aca se arma el grafo completo en memoria —el edificio con sus pisos, y cada
piso con sus departamentos— y se hace **un solo** `commit`. SQLAlchemy resuelve
el orden de los INSERT por las relaciones. Si algo falla, no se confirmo nada:
no hay un "a medio crear" posible.
"""

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.core import alcance
from app.core.dependencies import SesionDB, SoloAdminGeneral, SoloAdministradores
from app.models.edificio import Departamento, Edificio, Piso
from app.models.usuario import Usuario
from app.schemas.edificio import (
    CocheraDetalle,
    EdificioConfigurar,
    EdificioCreado,
    EdificioCrear,
    EdificioDetalle,
    EdificioRespuesta,
    EdificioResumen,
    EspacioComunDetalle,
    PisoCreado,
    PisoDetalle,
)
from app.services import autorizacion, finanzas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edificios", tags=["Edificios"])


@router.post(
    "",
    response_model=EdificioCreado,
    status_code=status.HTTP_201_CREATED,
    summary="Dar de alta un edificio con su estructura vacia",
)
def crear(
    datos: EdificioCrear,
    quien_crea: SoloAdminGeneral,
    db: SesionDB,
) -> EdificioCreado:
    """Crea el edificio y, en la misma transaccion, sus pisos y departamentos.

    Los dos numeros de tamanio —`cantidad_pisos` y `unidades_por_piso`— no se
    guardan en ninguna columna: son los argumentos con los que
    `services/finanzas.generar_estructura()` arma la estructura, y lo que queda
    guardado son los pisos y las unidades que esa estructura describe. Preguntar
    despues "¿cuantos pisos tiene?" se responde contando pisos, que es el dato
    verdadero: un numero guardado aparte dejaria de coincidir en cuanto alguien
    agregue un piso en `F1-T23`.

    Las unidades nacen **vacias**: sin metros cuadrados, sin propietario y sin
    coeficiente. Eso no es una tarea a medias, es lo correcto — un coeficiente
    inventado reparte plata mal sin que nadie lo note, mientras uno ausente lo
    encuentra la validacion antes de generar la primera expensa. Se completan en
    `F1-T23` (propietario, superficie) y `F1-T24` (coeficientes).
    """
    # Los topes los valida el esquema de entrada contra las constantes de este
    # mismo servicio, asi que aca no puede llegar un numero que la generacion
    # rechace. Igual se llama primero, antes de tocar la base: si alguna vez se
    # desalinearan, conviene que falle sin haber creado nada.
    estructura = finanzas.generar_estructura(
        cantidad_pisos=datos.cantidad_pisos,
        unidades_por_piso=datos.unidades_por_piso,
    )

    edificio = Edificio(
        nombre=datos.nombre,
        direccion=datos.direccion,
        cp=datos.cp,
        cuit=datos.cuit,
        latitud=datos.latitud,
        longitud=datos.longitud,
    )

    # El grafo entero, de una vez. Asignar por relacion y no por `edificio_id`
    # es lo que permite no hacer un `flush` por piso para conseguir su id:
    # SQLAlchemy inserta el edificio, lee su id y lo propaga a los pisos, y lo
    # mismo de cada piso a sus departamentos. Son menos consultas y, sobre
    # todo, una sola transaccion sin pasos intermedios confirmados.
    edificio.pisos = [
        Piso(
            numero=proyectado.numero,
            orden=proyectado.orden,
            departamentos=[
                Departamento(identificador=unidad.identificador)
                for unidad in proyectado.unidades
            ],
        )
        for proyectado in estructura
    ]

    db.add(edificio)

    try:
        db.commit()
    except (IntegrityError, SQLAlchemyError):
        db.rollback()
        # El detalle va al log y NO a la respuesta. Un mensaje de error de base
        # de datos nombra tablas, columnas y restricciones, y eso no se le
        # muestra a nadie (regla `FX-T11`). Ademas, si esto pasa es un error de
        # programacion y no algo que la persona pueda corregir reescribiendo el
        # formulario, asi que el mensaje no tiene nada util que ofrecerle.
        logger.exception("Fallo el alta del edificio %r", datos.nombre)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "No se pudo crear el edificio. No quedó nada a medio crear: "
                "podés volver a intentarlo."
            ),
        ) from None

    db.refresh(edificio)

    pisos = [
        PisoCreado(
            id=piso.id,
            numero=piso.numero,
            orden=piso.orden,
            unidades=[depto.identificador for depto in piso.departamentos],
        )
        for piso in edificio.pisos
    ]
    cantidad_departamentos = sum(len(piso.unidades) for piso in pisos)

    logger.info(
        "Edificio %s creado por %s: %d pisos, %d unidades",
        edificio.id,
        quien_crea.email,
        len(pisos),
        cantidad_departamentos,
    )

    return EdificioCreado(
        edificio=EdificioRespuesta.model_validate(edificio),
        pisos=pisos,
        cantidad_pisos=len(pisos),
        cantidad_departamentos=cantidad_departamentos,
        mensaje=(
            f"Se creó el edificio con {len(pisos)} "
            f"{'piso' if len(pisos) == 1 else 'pisos'} y "
            f"{cantidad_departamentos} "
            f"{'unidad' if cantidad_departamentos == 1 else 'unidades'}. "
            "Las unidades quedaron sin superficie, sin propietario y sin "
            "coeficiente: eso se completa después."
        ),
    )


# ------------------------------------------------------------- lectura -------
#
# ===========================================================================
# EL N+1, QUE ES LO QUE ESTA TAREA EXISTE PARA EVITAR
# ===========================================================================
#
# "N+1" es una consulta para traer la lista y una consulta mas por cada
# elemento de esa lista. Pasa sin que nadie lo escriba: si el esquema de
# respuesta del listado incluyera los pisos, Pydantic leeria `edificio.pisos`
# de cada fila y SQLAlchemy —que no los trajo— saldria a buscarlos uno por uno.
#
# En la iteracion anterior el listado disparaba 29 consultas para 7 edificios
# y el detalle 6 para un edificio de 3 pisos. En SQLite local eso son 2 a 12
# milisegundos y no se nota; contra Supabase cada consulta paga ida y vuelta
# de red, y el mismo listado tardaba alrededor de un segundo y medio.
#
# Las dos defensas son distintas porque los dos endpoints necesitan cosas
# distintas:
#
#   - El LISTADO no trae la estructura. Los dos numeros que la pantalla
#     muestra los cuenta la base con subconsultas correlacionadas, dentro de
#     la misma consulta: **una sola**, haya 1 edificio o 300.
#   - El DETALLE si trae la estructura, con `selectinload`: una consulta extra
#     por coleccion, con todos los ids juntos en un `IN`. Son 4 extra fijas
#     —pisos, departamentos, cocheras, espacios comunes— sin importar cuantos
#     pisos tenga el edificio. (El Roadmap anoto "2 extra" contando solo pisos
#     y departamentos; las otras dos colecciones tambien van en el detalle, y
#     lo que importa es que el numero sea FIJO.)
#
# Y hay tests que CUENTAN las consultas disparadas, no que miden tiempos: un
# tiempo en CI depende de la maquina y de la carga, asi que un N+1 que vuelva
# a aparecer pasaria un test de tiempo en silencio.
# ===========================================================================


def _conteos_del_edificio() -> tuple:
    """Las dos subconsultas de conteo, correlacionadas con `edificios`.

    `correlate(Edificio)` es lo que hace que la subconsulta use el `edificios`
    de la consulta de afuera en vez de volver a nombrarlo. Sin eso, SQLAlchemy
    agrega `edificios` otra vez al FROM de la subconsulta y el conteo sale
    sobre TODOS los edificios: el mismo numero repetido en cada renglon, que es
    un error que pasa los tests de permisos y de forma sin chistar.
    """
    pisos = (
        select(func.count(Piso.id))
        .where(Piso.edificio_id == Edificio.id)
        .correlate(Edificio)
        .scalar_subquery()
    )
    departamentos = (
        select(func.count(Departamento.id))
        .join(Piso, Piso.id == Departamento.piso_id)
        .where(Piso.edificio_id == Edificio.id)
        .correlate(Edificio)
        .scalar_subquery()
    )
    return pisos, departamentos


def no_encontrado() -> HTTPException:
    """El mismo 404 para "no existe" y para "no es tuyo".

    Un 403 distinguible le iria contando a un Administrador de Consorcio que
    edificios hay en la cartera probando ids.

    Es publica porque la usa tambien `routers/estructura.py`: el mensaje de
    "ese edificio no esta" tiene que ser uno solo en todo el proyecto. Dos
    textos distintos para la misma situacion es la clase de diferencia que
    despues alguien usa para deducir cual de los dos casos le toco.
    """
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No se encontró el edificio.",
    )


def buscar_edificio_que_administra(
    db: Session, edificio_id: int, quien_consulta: Usuario
) -> Edificio:
    """El edificio, si esa persona lo administra. Si no, 404.

    El filtro de alcance vive en `core/alcance.py`, que es el archivo que
    responde "sobre que edificios" — la otra mitad de la pregunta que
    `services/autorizacion.py` contesta para los permisos. Aca solo se traduce
    "no hay fila" a un 404.
    """
    consulta = alcance.limitar_a_los_que_administra(
        select(Edificio).where(Edificio.id == edificio_id),
        quien_consulta,
    )
    edificio = db.scalars(consulta).first()

    if edificio is None:
        raise no_encontrado()

    return edificio


@router.get(
    "",
    response_model=list[EdificioResumen],
    summary="Listar edificios, con su cantidad de pisos y unidades",
)
def listar(
    quien_consulta: SoloAdministradores,
    db: SesionDB,
) -> list[EdificioResumen]:
    """Los edificios del alcance de quien consulta, ordenados por nombre.

    **Una sola consulta**, sin importar cuantos edificios haya: los dos
    conteos los calcula la base con subconsultas correlacionadas, y el esquema
    de respuesta no incluye ninguna coleccion, asi que no hay nada que Pydantic
    pueda leer y disparar una consulta por edificio.

    Los inactivos **se incluyen**, igual que en el listado de usuarios: la baja
    de este sistema es logica para que el edificio siga estando, y esconderlo
    dejaria al administrador sin forma de reactivarlo desde la pantalla. El
    estado viaja en `activo`.
    """
    subconsulta_pisos, subconsulta_departamentos = _conteos_del_edificio()

    consulta = alcance.limitar_a_los_que_administra(
        select(Edificio, subconsulta_pisos, subconsulta_departamentos),
        quien_consulta,
    ).order_by(Edificio.nombre)

    return [
        EdificioResumen(
            id=edificio.id,
            nombre=edificio.nombre,
            direccion=edificio.direccion,
            cp=edificio.cp,
            cuit=edificio.cuit,
            latitud=edificio.latitud,
            longitud=edificio.longitud,
            admin_consorcio_id=edificio.admin_consorcio_id,
            encargado_id=edificio.encargado_id,
            activo=edificio.activo,
            creado_en=edificio.creado_en,
            cantidad_pisos=cantidad_pisos,
            cantidad_departamentos=cantidad_departamentos,
        )
        for edificio, cantidad_pisos, cantidad_departamentos in db.execute(consulta)
    ]


@router.get(
    "/{edificio_id}",
    response_model=EdificioDetalle,
    summary="Ver un edificio con toda su estructura",
)
def detalle(
    edificio_id: int,
    quien_consulta: SoloAdministradores,
    db: SesionDB,
) -> EdificioDetalle:
    """El edificio completo: pisos con sus unidades, cocheras y espacios comunes.

    **Cinco consultas fijas**: una por el edificio y una por cada coleccion,
    gracias a `selectinload`. No crecen con el tamanio del edificio — uno de 20
    pisos dispara las mismas cinco que uno de 3.

    Se usa `selectinload` y no `joinedload` a proposito. Un `joinedload` de dos
    colecciones hermanas —pisos y cocheras— hace el producto cartesiano de las
    dos en una sola consulta: 7 pisos y 10 cocheras devuelven 70 filas que
    SQLAlchemy despues deduplica en memoria. `selectinload` las trae en
    consultas separadas con los ids en un `IN`, y cada fila viaja una sola vez.

    Un edificio que existe pero esta fuera del alcance de quien consulta
    responde **lo mismo** que uno que no existe. Un 403 distinguible le iria
    contando a un Administrador de Consorcio que edificios hay en la cartera
    probando ids, que es informacion que no le corresponde.
    """
    consulta = alcance.limitar_a_los_que_administra(
        select(Edificio).where(Edificio.id == edificio_id),
        quien_consulta,
    ).options(
        selectinload(Edificio.pisos).selectinload(Piso.departamentos),
        selectinload(Edificio.cocheras),
        selectinload(Edificio.espacios_comunes),
    )

    edificio = db.scalars(consulta).first()

    if edificio is None:
        raise no_encontrado()

    cantidad_departamentos = sum(len(piso.departamentos) for piso in edificio.pisos)

    return EdificioDetalle(
        edificio=EdificioRespuesta.model_validate(edificio),
        pisos=[PisoDetalle.model_validate(piso) for piso in edificio.pisos],
        cocheras=[
            CocheraDetalle.model_validate(cochera) for cochera in edificio.cocheras
        ],
        espacios_comunes=[
            EspacioComunDetalle.model_validate(espacio)
            for espacio in edificio.espacios_comunes
        ],
        cantidad_pisos=len(edificio.pisos),
        cantidad_departamentos=cantidad_departamentos,
    )


# ----------------------------------------------------------- configuracion ---
#
# ===========================================================================
# QUIEN CONFIGURA QUE, Y POR QUE NO ES UN SOLO PERMISO
# ===========================================================================
#
# La configuracion del edificio tiene dos clases de campo y no se pueden
# proteger igual:
#
#   - **Quien administra el edificio** (`admin_consorcio_id`, `encargado_id`)
#     es una decision de la plataforma, no del consorcio. Solo el
#     Administrador General. Si un Administrador de Consorcio pudiera
#     cambiarlos, podria sacarse a si mismo —perdiendo el acceso al edificio
#     sin forma de recuperarlo— o, al reves, asignarse un edificio ajeno.
#   - **Como cobra y a quien llamar** (dias de vencimiento, recargo por mora,
#     CBU, alias, contacto de emergencia, roles habilitados) es el trabajo
#     diario del Administrador de Consorcio sobre SU edificio. Pedirle al
#     Administrador General que cargue el CBU de cada consorcio seria convertir
#     un dato operativo en un tramite.
#
# El alcance es el mismo que el de la lectura: el Administrador de Consorcio
# solo llega a los edificios donde figura como tal, y uno ajeno responde 404
# igual que uno inexistente.
# ===========================================================================


# Que rol tiene que tener realmente el usuario que se elige para cada puesto.
# El Roadmap lo pide explicitamente, y es la unica forma de que el puesto
# signifique algo: un "encargado" que en la matriz de roles es Proveedor no
# tiene ninguno de los permisos que la pantalla del encargado necesita, y la
# falla aparece recien cuando esa persona intenta entrar.
_ROL_DEL_PUESTO = {
    "admin_consorcio_id": autorizacion.ADMIN_CONSORCIO,
    "encargado_id": autorizacion.ENCARGADO,
}

_PUESTO_LEGIBLE = {
    "admin_consorcio_id": "Administrador de Consorcio",
    "encargado_id": "Encargado",
}


def _verificar_responsable(db: Session, usuario_id: int, campo: str) -> None:
    """Valida que el usuario elegido exista, este activo y tenga ESE rol.

    Los tres motivos de rechazo dan mensajes distintos a proposito: quien
    configura es un administrador eligiendo entre usuarios que el mismo dio de
    alta, asi que "esa persona está desactivada" es informacion que le
    corresponde y que le ahorra adivinar. Lo que ningun mensaje nombra es una
    tabla, una columna ni una consulta (regla `FX-T11`).
    """
    rol_esperado = _ROL_DEL_PUESTO[campo]
    puesto = _PUESTO_LEGIBLE[campo]

    usuario = db.scalar(select(Usuario).where(Usuario.id == usuario_id))

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La persona que elegiste como {puesto} no existe.",
        )
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{usuario.nombre} está desactivado, así que no puede quedar "
                f"como {puesto}."
            ),
        )
    if usuario.rol != rol_esperado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{usuario.nombre} es {autorizacion.etiqueta(usuario.rol)}, "
                f"no {puesto}. Cambiale el rol primero o elegí a otra persona."
            ),
        )


@router.patch(
    "/{edificio_id}",
    response_model=EdificioRespuesta,
    summary="Configurar un edificio",
)
def configurar(
    edificio_id: int,
    datos: EdificioConfigurar,
    quien_configura: SoloAdministradores,
    db: SesionDB,
) -> Edificio:
    """Cambia solo los campos que viajaron en el pedido.

    Un campo ausente no se toca; un campo en `null` se vacia. Los que la
    columna declara NOT NULL no se pueden vaciar, y eso lo rechaza el esquema
    con un 422 antes de llegar a la base.

    Los responsables se validan contra la matriz de roles —`admin_consorcio_id`
    tiene que ser un Administrador de Consorcio de verdad, `encargado_id` un
    Encargado— y los cambia **solo el Administrador General**.
    """
    cambios = datos.model_dump(exclude_unset=True)

    if not cambios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No enviaste ningún cambio.",
        )

    puestos = [campo for campo in _ROL_DEL_PUESTO if campo in cambios]

    # El permiso se verifica ANTES de buscar el edificio: asi un Administrador
    # de Consorcio que intenta cambiar los responsables recibe el 403 que
    # explica el motivo, y no un 404 que lo mandaria a buscar un problema de id
    # que no existe.
    if puestos and quien_configura.rol != autorizacion.ADMIN_GENERAL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Quién administra el edificio lo decide el Administrador "
                "General. Podés configurar el resto."
            ),
        )

    edificio = buscar_edificio_que_administra(db, edificio_id, quien_configura)

    for campo in puestos:
        if cambios[campo] is not None:
            _verificar_responsable(db, cambios[campo], campo)

    for campo, valor in cambios.items():
        # `roles_habilitados` se ASIGNA, nunca se modifica en el lugar: una
        # columna JSON no se da cuenta de un `.append()` sobre la lista que ya
        # tiene cargada, asi que ese cambio no se guardaria y tampoco daria
        # error. Acá siempre viene una lista nueva del esquema.
        setattr(edificio, campo, valor)

    # Los dos puestos no pueden ser la misma persona, y la base tambien lo
    # prohibe (`ck_edificios_responsables_distintos`). Hoy este chequeo es
    # INALCANZABLE y conviene decirlo en vez de dejarlo pareciendo la defensa
    # principal: un usuario tiene un solo rol, y cada puesto exige el suyo, asi
    # que el cruce lo rechaza antes `_verificar_responsable` con un mensaje mas
    # util. Queda igual como respaldo del CHECK, porque el dia que un puesto
    # admita mas de un rol esta seria la unica red: un CHECK que salta devuelve
    # un 500 sin explicacion. Se mira el resultado FINAL —lo que ya estaba mas
    # lo que cambia— y no solo lo que vino en el pedido.
    if (
        edificio.admin_consorcio_id is not None
        and edificio.admin_consorcio_id == edificio.encargado_id
    ):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "La misma persona no puede ser Administrador de Consorcio y "
                "Encargado del mismo edificio."
            ),
        )

    try:
        db.commit()
    except (IntegrityError, SQLAlchemyError):
        db.rollback()
        logger.exception("Fallo la configuracion del edificio %s", edificio_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "No se pudo guardar la configuración. No se cambió nada: "
                "podés volver a intentarlo."
            ),
        ) from None

    db.refresh(edificio)

    logger.info(
        "Edificio %s configurado por %s: %s",
        edificio.id,
        quien_configura.email,
        ", ".join(sorted(cambios)),
    )

    return edificio

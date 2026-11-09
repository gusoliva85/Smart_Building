"""Carga de coeficientes (`F1-T24`).

Tres endpoints, todos bajo ``/api/edificios/{edificio_id}``:

- ``GET  /coeficientes`` — como esta el edificio: cuanto suman y que falta
- ``PATCH /departamentos/{id}/coeficiente`` — carga manual, unidad por unidad
- ``POST /coeficientes/aplicar-atajo`` — los atajos de `F1-T17` a todo el edificio

============================================================================
POR QUE ESTA TAREA ES PRERREQUISITO DE TODA LA FASE 2
============================================================================

El coeficiente es el porcentaje de la expensa que paga cada unidad. Sin
coeficientes cargados no hay expensa posible: no es que salga mal, es que no se
puede emitir.

En la iteracion anterior esto quedo pendiente **en silencio**. Nunca existio un
endpoint para cargar el coeficiente —solo se podia a mano, escribiendo en la
base— y el problema aparecio recien al intentar generar la primera expensa, con
un "Hay departamentos sin coeficiente cargado" que no decia cuales ni cuantos.

Lo que este modulo hace distinto, y es su decision central: **cada respuesta
trae el estado completo del edificio**. Cuanto suma hoy, si eso es 100%,
cuantas unidades siguen sin coeficiente y cuales son las primeras. La pantalla
puede mostrar "suman 99,988% y faltan 3 unidades" en el mismo momento en que se
carga una. El problema se ve mientras se trabaja, no tres fases despues.

============================================================================
LA CARGA MANUAL ES LA PRINCIPAL. LOS ATAJOS SON PARA EMPEZAR
============================================================================

Los coeficientes de un consorcio real estan escritos en el reglamento de
propiedad horizontal: no se calculan, se copian. El atajo —partes iguales o por
metro cuadrado— sirve para el edificio que todavia no tiene el reglamento
cargado, o para el que de hecho reparte en partes iguales.

Por eso el atajo se niega a pisar coeficientes ya cargados sin confirmacion
explicita: pisar un coeficiente que salio del reglamento con un calculo
automatico es destruir el dato verdadero y reemplazarlo por uno plausible.

============================================================================
LA SUMA NO SE BLOQUEA MIENTRAS SE CARGA
============================================================================

Cargar treinta coeficientes a mano pasa por estados intermedios donde la suma
no es 100: cuando se cargo el primero suma 3,5. Rechazar esos estados obligaria
a cargar todo en un solo pedido o a bajar un coeficiente antes de poder subir
otro, que es la clase de validacion que hace que la gente cargue los datos en
otro lado.

Asi que **cada endpoint informa la suma y no la impone**. Lo que si impone la
suma exacta es la generacion de la expensa (Fase 2), que es donde importa — y
para entonces la pantalla ya venia avisando.
"""

import logging
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.dependencies import SesionDB, SoloAdministradores
from app.models.edificio import Departamento, Edificio, Piso
from app.routers.edificios import buscar_edificio_que_administra
from app.routers.estructura import buscar_departamento
from app.schemas.coeficientes import (
    CRITERIO_METROS_CUADRADOS,
    AtajoDeCoeficientes,
    CoeficienteCargar,
    EstadoDeCoeficientes,
    UnidadConCoeficiente,
)
from app.services import finanzas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edificios", tags=["Coeficientes"])

# Cuantos identificadores se nombran en el mensaje cuando faltan coeficientes.
# Todos no: un edificio de 160 unidades recien cargado daria un mensaje
# ilegible. Y ninguno tampoco, que es lo que hacia la version anterior.
IDENTIFICADORES_EN_EL_MENSAJE = 5


def _unidades_ordenadas(db: Session, edificio: Edificio) -> list[tuple[Departamento, int]]:
    """Las unidades del edificio con el numero de su piso, en orden estable.

    El orden importa y no es cosmetico: el reparto de los atajos distribuye el
    sobrante del redondeo entre las primeras unidades, asi que un orden que
    cambie entre dos llamadas daria coeficientes distintos para el mismo
    edificio. Se ordena por la posicion del piso y, dentro del piso, por el
    identificador: lo mismo que devuelve el detalle del edificio, asi que la
    pantalla y el calculo ven la misma lista.
    """
    return list(
        db.execute(
            select(Departamento, Piso.numero)
            .join(Piso, Piso.id == Departamento.piso_id)
            .where(Piso.edificio_id == edificio.id)
            .order_by(Piso.orden, Departamento.identificador)
        ).all()
    )


def _armar_estado(filas: list[tuple[Departamento, int]]) -> EstadoDeCoeficientes:
    """El estado del edificio a partir de sus unidades.

    La suma se calcula sobre los valores **tal como estan guardados**, que es
    el unico numero que importa: el error historico del 99,989% era exactamente
    la diferencia entre sumar los valores exactos y sumar los redondeados.
    """
    cargados = [
        departamento.coeficiente
        for departamento, _ in filas
        if departamento.coeficiente is not None
    ]
    sin_cargar = [
        departamento.identificador
        for departamento, _ in filas
        if departamento.coeficiente is None
    ]

    suma = sum(cargados, Decimal(0)).quantize(finanzas.PASO_COEFICIENTE)
    completo = not sin_cargar and bool(cargados)
    suma_cien = completo and finanzas.validar_coeficientes(cargados)

    if not filas:
        mensaje = "Este edificio todavía no tiene unidades."
    elif sin_cargar:
        primeros = ", ".join(sin_cargar[:IDENTIFICADORES_EN_EL_MENSAJE])
        resto = len(sin_cargar) - IDENTIFICADORES_EN_EL_MENSAJE
        if resto > 0:
            primeros += f" y {resto} más"
        mensaje = (
            f"Faltan {len(sin_cargar)} "
            f"{'unidad' if len(sin_cargar) == 1 else 'unidades'} sin "
            f"coeficiente: {primeros}."
        )
    elif suma_cien:
        mensaje = (
            "Los coeficientes suman 100%: el edificio está listo para generar "
            "expensas."
        )
    else:
        mensaje = (
            f"Los coeficientes suman {suma}%. Tienen que sumar exactamente "
            "100% para poder generar una expensa."
        )

    return EstadoDeCoeficientes(
        suma=suma,
        suma_cien=suma_cien,
        cantidad_unidades=len(filas),
        unidades_sin_coeficiente=len(sin_cargar),
        unidades=[
            UnidadConCoeficiente(
                id=departamento.id,
                identificador=departamento.identificador,
                piso_numero=piso_numero,
                m2=departamento.m2,
                coeficiente=departamento.coeficiente,
            )
            for departamento, piso_numero in filas
        ],
        mensaje=mensaje,
    )


def _guardar(db: Session, descripcion: str) -> None:
    try:
        db.commit()
    except (IntegrityError, SQLAlchemyError):
        db.rollback()
        logger.exception("Fallo al guardar: %s", descripcion)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "No se pudieron guardar los coeficientes. No quedó nada a "
                "medio cambiar: podés volver a intentarlo."
            ),
        ) from None


@router.get(
    "/{edificio_id}/coeficientes",
    response_model=EstadoDeCoeficientes,
    summary="Ver los coeficientes del edificio y cuánto suman",
)
def ver(
    edificio_id: int,
    quien_consulta: SoloAdministradores,
    db: SesionDB,
) -> EstadoDeCoeficientes:
    """Todas las unidades con su coeficiente, mas el estado del edificio.

    Es la pantalla de carga: una lista de unidades para completar y, arriba, el
    unico numero que decide si se puede emitir una expensa.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_consulta)
    return _armar_estado(_unidades_ordenadas(db, edificio))


@router.patch(
    "/{edificio_id}/departamentos/{departamento_id}/coeficiente",
    response_model=EstadoDeCoeficientes,
    summary="Cargar el coeficiente de una unidad",
)
def cargar(
    edificio_id: int,
    departamento_id: int,
    datos: CoeficienteCargar,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> EstadoDeCoeficientes:
    """Carga el coeficiente de una unidad y devuelve como quedo el edificio.

    Devuelve el estado completo y no solo la unidad a proposito: quien carga
    treinta coeficientes necesita ver la suma despues de cada uno, y pedirla
    aparte seria el doble de pedidos para el dato que mas importa.

    Tiene su propio endpoint y no es un campo del PATCH de la estructura porque
    es el dato del que depende todo el modulo financiero: separado, el permiso
    y la validacion se leen de un vistazo, y cambiar los metros cuadrados nunca
    puede tocar un coeficiente por accidente.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)
    departamento = buscar_departamento(db, edificio, departamento_id)

    departamento.coeficiente = datos.coeficiente
    _guardar(db, f"coeficiente de la unidad {departamento_id}")

    logger.info(
        "Coeficiente de la unidad %s = %s, cargado por %s",
        departamento_id,
        datos.coeficiente,
        quien_edita.email,
    )

    return _armar_estado(_unidades_ordenadas(db, edificio))


@router.post(
    "/{edificio_id}/coeficientes/aplicar-atajo",
    response_model=EstadoDeCoeficientes,
    summary="Aplicar un atajo de coeficientes a todo el edificio",
)
def aplicar_atajo(
    edificio_id: int,
    datos: AtajoDeCoeficientes,
    quien_edita: SoloAdministradores,
    db: SesionDB,
) -> EstadoDeCoeficientes:
    """Calcula los coeficientes de todas las unidades con un criterio.

    Las cuentas las hace `services/finanzas.py` y no este endpoint: el reparto
    cuenta 100.000 pasos de 0,001 y los distribuye por resto mayor, asi que la
    suma da 100,000% **por construccion** y no por redondeo afortunado. Aca solo
    se arma la lista de unidades, se la pasa al servicio y se guardan los
    valores que devuelve, **en una sola transaccion**: la mitad de un edificio
    con coeficientes nuevos y la otra con los viejos no suma 100% y nadie se
    daria cuenta hasta la expensa.
    """
    edificio = buscar_edificio_que_administra(db, edificio_id, quien_edita)
    filas = _unidades_ordenadas(db, edificio)

    if not filas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Este edificio todavía no tiene unidades, así que no hay nada "
                "que repartir."
            ),
        )

    unidades = [departamento for departamento, _ in filas]

    # El 409 es el codigo de "necesito que confirmes" en este proyecto: el
    # envoltorio de `fetch` del frontend lo convierte en
    # `error.necesitaConfirmacion` y abre el dialogo. Es exactamente este caso,
    # y es el unico lugar de la Fase 1 donde corresponde.
    ya_cargados = [u for u in unidades if u.coeficiente is not None]
    if ya_cargados and not datos.sobrescribir:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{len(ya_cargados)} "
                f"{'unidad' if len(ya_cargados) == 1 else 'unidades'} ya "
                f"{'tiene' if len(ya_cargados) == 1 else 'tienen'} coeficiente "
                "cargado. Los coeficientes del reglamento no se pueden "
                "recalcular: ¿querés reemplazarlos igual?"
            ),
        )

    if datos.criterio == CRITERIO_METROS_CUADRADOS:
        sin_m2 = [u.identificador for u in unidades if u.m2 is None]
        if sin_m2:
            primeros = ", ".join(sin_m2[:IDENTIFICADORES_EN_EL_MENSAJE])
            resto = len(sin_m2) - IDENTIFICADORES_EN_EL_MENSAJE
            if resto > 0:
                primeros += f" y {resto} más"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"No se puede repartir por metro cuadrado: {len(sin_m2)} "
                    f"{'unidad' if len(sin_m2) == 1 else 'unidades'} no "
                    f"{'tiene' if len(sin_m2) == 1 else 'tienen'} superficie "
                    f"cargada ({primeros}). Cargá las superficies o usá el "
                    "reparto en partes iguales."
                ),
            )
        calculados = finanzas.calcular_por_metros_cuadrados([u.m2 for u in unidades])
    else:
        calculados = finanzas.calcular_partes_iguales(len(unidades))

    for unidad, coeficiente in zip(unidades, calculados, strict=True):
        unidad.coeficiente = coeficiente

    _guardar(db, f"atajo de coeficientes del edificio {edificio_id}")

    logger.info(
        "Coeficientes del edificio %s recalculados por %s con el criterio %s "
        "(%d unidades)",
        edificio_id,
        quien_edita.email,
        datos.criterio,
        len(unidades),
    )

    return _armar_estado(_unidades_ordenadas(db, edificio))

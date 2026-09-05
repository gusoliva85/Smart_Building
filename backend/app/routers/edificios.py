"""Router de edificios — Documento General, secciones 5.1 y 5.2.

`POST /api/edificios`: alta de un edificio nuevo, solo Administrador
General. En la misma operación se genera su estructura vacía (pisos +
departamentos) reutilizando `services/edificios.py` (lógica ya probada
en una tarea anterior) — nunca se carga piso por piso a mano.

`PATCH /api/edificios/{id}`: configuración (contacto de emergencia, días
de vencimiento, roles habilitados). CRUD anidado de pisos/departamentos/
cocheras/espacios comunes bajo `/api/edificios/{id}/...`, y el endpoint
de asignación/desvinculación de propietario o inquilino a un departamento.

Regla de acceso para todo lo de esta fase: Administrador General (siempre)
o el Administrador de Consorcio de ESE edificio puntual — se resuelve
comparando contra `Edificio.admin_consorcio_id` directamente, no todavía
contra `UsuarioEdificio`/el JWT (ese vínculo genérico multi-edificio se
retoma cuando el login empiece a poblarlo con datos reales).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.database import obtener_db
from app.models.edificio import Cochera, Departamento, Edificio, EspacioComun, Piso
from app.models.usuario import Usuario
from app.schemas.edificio import (
    CocheraEntrada,
    CocheraSalida,
    DepartamentoAsignacion,
    DepartamentoEntrada,
    DepartamentoSalida,
    EdificioConfiguracion,
    EdificioEntrada,
    EdificioResumenSalida,
    EdificioSalida,
    EspacioComunEntrada,
    EspacioComunSalida,
    PisoEntrada,
    PisoSalida,
)
from app.services.edificios import generar_estructura_vacia

router = APIRouter(prefix="/api/edificios", tags=["edificios"])


def _requerir_admin_general(
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
) -> UsuarioAutenticado:
    if actual.usuario.rol != "admin_general":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el Administrador General puede dar de alta un edificio",
        )
    return actual


def _obtener_edificio_o_404(edificio_id: int, db: Session) -> Edificio:
    edificio = db.get(Edificio, edificio_id)
    if not edificio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edificio no encontrado")
    return edificio


def _verificar_admin_del_edificio(edificio: Edificio, actual: UsuarioAutenticado) -> None:
    """Admin General (siempre) o el Admin de Consorcio asignado a ESTE
    edificio puntual — nadie más gestiona su configuración o estructura.
    Separado de `_requerir_admin_del_edificio` para poder reutilizar la
    misma regla de acceso sobre un edificio que ya se cargó con eager
    loading (ver `obtener_edificio`), en vez de volver a consultarlo."""
    es_admin_general = actual.usuario.rol == "admin_general"
    es_admin_de_este_edificio = actual.usuario.rol == "admin_consorcio" and edificio.admin_consorcio_id == actual.usuario.id
    if not (es_admin_general or es_admin_de_este_edificio):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No administrás este edificio")


def _requerir_admin_del_edificio(
    edificio_id: int,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
) -> Edificio:
    edificio = _obtener_edificio_o_404(edificio_id, db)
    _verificar_admin_del_edificio(edificio, actual)
    return edificio


@router.get("", response_model=list[EdificioResumenSalida])
def listar_edificios(
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    """Administrador General ve todos los edificios; Administrador de
    Consorcio ve solo los suyos (mismo criterio que _requerir_admin_del_edificio,
    acá aplicado a un listado en vez de a un edificio puntual).

    Antes traía cada edificio con TODOS sus pisos y departamentos anidados
    (uno o varios `SELECT` extra por cada piso de cada edificio — un N+1
    real, medido en 29 consultas SQL para listar 7 edificios de prueba).
    Acá se pide directo el conteo (`COUNT`) resuelto por la base en una
    sola consulta con `JOIN` — nunca se trae una fila de piso o
    departamento solo para poder mostrar "N pisos · M unidades"."""
    consulta = (
        db.query(
            Edificio.id,
            Edificio.nombre,
            Edificio.direccion,
            Edificio.cp,
            Edificio.cuit,
            Edificio.admin_consorcio_id,
            Edificio.activo,
            func.count(func.distinct(Piso.id)).label("cantidad_pisos"),
            func.count(Departamento.id).label("cantidad_unidades"),
        )
        .outerjoin(Piso, Piso.edificio_id == Edificio.id)
        .outerjoin(Departamento, Departamento.piso_id == Piso.id)
        .group_by(Edificio.id)
    )
    if actual.usuario.rol == "admin_general":
        pass
    elif actual.usuario.rol == "admin_consorcio":
        consulta = consulta.filter(Edificio.admin_consorcio_id == actual.usuario.id)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenés acceso al listado de edificios")
    return consulta.order_by(Edificio.nombre).all()


@router.get("/{edificio_id}", response_model=EdificioSalida)
def obtener_edificio(
    edificio_id: int,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    """A diferencia del listado, acá sí hace falta la estructura completa
    (es la pestaña "Estructura" del detalle) — pero traída con
    `selectinload` en 2 consultas fijas (una para todos los pisos del
    edificio, una para todos los departamentos de esos pisos), en vez de
    una consulta de departamentos por cada piso (el N+1 medido: 6
    consultas para un edificio de solo 3 pisos, uno más por cada piso
    extra que tuviera)."""
    edificio = (
        db.query(Edificio)
        .options(selectinload(Edificio.pisos).selectinload(Piso.departamentos))
        .filter(Edificio.id == edificio_id)
        .first()
    )
    if not edificio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edificio no encontrado")
    _verificar_admin_del_edificio(edificio, actual)
    return edificio


@router.post("", response_model=EdificioSalida, status_code=status.HTTP_201_CREATED)
def crear_edificio(
    datos: EdificioEntrada,
    db: Session = Depends(obtener_db),
    _: UsuarioAutenticado = Depends(_requerir_admin_general),
):
    if datos.admin_consorcio_id is not None:
        admin = db.get(Usuario, datos.admin_consorcio_id)
        if not admin or admin.rol != "admin_consorcio":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="admin_consorcio_id debe corresponder a un usuario con rol admin_consorcio",
            )

    edificio = Edificio(
        nombre=datos.nombre,
        direccion=datos.direccion,
        cp=datos.cp,
        cuit=datos.cuit,
        latitud=datos.latitud,
        longitud=datos.longitud,
        admin_consorcio_id=datos.admin_consorcio_id,
        dias_vencimiento_expensas=datos.dias_vencimiento_expensas,
        recargo_mora_porcentual=datos.recargo_mora_porcentual,
    )
    db.add(edificio)
    db.flush()  # asigna edificio.id sin cerrar la transacción todavía

    estructura = generar_estructura_vacia(datos.cantidad_pisos, datos.unidades_por_piso)
    for piso_data in estructura:
        piso = Piso(edificio_id=edificio.id, numero=str(piso_data["numero"]), orden=piso_data["numero"])
        db.add(piso)
        db.flush()
        for identificador in piso_data["departamentos"]:
            db.add(Departamento(piso_id=piso.id, identificador=identificador))

    db.commit()
    db.refresh(edificio)
    return edificio


@router.patch("/{edificio_id}", response_model=EdificioSalida)
def configurar_edificio(
    datos: EdificioConfiguracion,
    edificio: Edificio = Depends(_requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    cambios = datos.model_dump(exclude_unset=True)
    if "roles_habilitados" in cambios:
        lista = cambios.pop("roles_habilitados")
        edificio.roles_habilitados = ",".join(lista) if lista is not None else None
    for campo, valor in cambios.items():
        setattr(edificio, campo, valor)

    db.commit()
    db.refresh(edificio)
    return edificio


# ------------------------------ Pisos ------------------------------

@router.get("/{edificio_id}/pisos", response_model=list[PisoSalida])
def listar_pisos(edificio: Edificio = Depends(_requerir_admin_del_edificio)):
    return edificio.pisos


@router.post("/{edificio_id}/pisos", response_model=PisoSalida, status_code=status.HTTP_201_CREATED)
def crear_piso(
    datos: PisoEntrada,
    edificio: Edificio = Depends(_requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    piso = Piso(edificio_id=edificio.id, numero=datos.numero, orden=datos.orden)
    db.add(piso)
    db.commit()
    db.refresh(piso)
    return piso


# --------------------------- Departamentos ---------------------------

@router.post("/{edificio_id}/departamentos", response_model=DepartamentoSalida, status_code=status.HTTP_201_CREATED)
def crear_departamento(
    datos: DepartamentoEntrada,
    edificio: Edificio = Depends(_requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    piso = db.get(Piso, datos.piso_id)
    if not piso or piso.edificio_id != edificio.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="piso_id debe pertenecer a este edificio")

    depto = Departamento(piso_id=piso.id, identificador=datos.identificador, m2=datos.m2)
    db.add(depto)
    db.commit()
    db.refresh(depto)
    return depto


@router.patch("/departamentos/{departamento_id}/asignacion", response_model=DepartamentoSalida)
def asignar_departamento(
    departamento_id: int,
    datos: DepartamentoAsignacion,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    depto = db.get(Departamento, departamento_id)
    if not depto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Departamento no encontrado")

    edificio_id = depto.piso.edificio_id
    _requerir_admin_del_edificio(edificio_id=edificio_id, db=db, actual=actual)

    cambios = datos.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        if valor is not None:
            usuario = db.get(Usuario, valor)
            rol_esperado = "propietario" if campo == "propietario_id" else "inquilino"
            if not usuario or usuario.rol != rol_esperado:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{campo} debe corresponder a un usuario con rol {rol_esperado}",
                )
            # Un inquilino vive en UN solo lugar a la vez — a diferencia del
            # propietario (que sí puede tener varias unidades a su nombre),
            # no puede quedar asignado a dos departamentos al mismo tiempo.
            if campo == "inquilino_id":
                ya_asignado = (
                    db.query(Departamento)
                    .filter(Departamento.inquilino_id == valor, Departamento.id != departamento_id)
                    .first()
                )
                if ya_asignado:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Ese inquilino ya está asignado a otro departamento",
                    )
        setattr(depto, campo, valor)

    depto.ocupado = bool(depto.propietario_id or depto.inquilino_id)
    db.commit()
    db.refresh(depto)
    return depto


# ------------------------------ Cocheras ------------------------------

@router.get("/{edificio_id}/cocheras", response_model=list[CocheraSalida])
def listar_cocheras(edificio: Edificio = Depends(_requerir_admin_del_edificio), db: Session = Depends(obtener_db)):
    return db.query(Cochera).filter(Cochera.edificio_id == edificio.id).order_by(Cochera.numero).all()


@router.post("/{edificio_id}/cocheras", response_model=CocheraSalida, status_code=status.HTTP_201_CREATED)
def crear_cochera(
    datos: CocheraEntrada,
    edificio: Edificio = Depends(_requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    if datos.departamento_id is not None:
        depto = db.get(Departamento, datos.departamento_id)
        if not depto or depto.piso.edificio_id != edificio.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="departamento_id debe pertenecer a este edificio")

    cochera = Cochera(edificio_id=edificio.id, numero=datos.numero, tipo=datos.tipo, departamento_id=datos.departamento_id)
    db.add(cochera)
    db.commit()
    db.refresh(cochera)
    return cochera


# --------------------------- Espacios comunes ---------------------------

@router.get("/{edificio_id}/espacios-comunes", response_model=list[EspacioComunSalida])
def listar_espacios_comunes(edificio: Edificio = Depends(_requerir_admin_del_edificio), db: Session = Depends(obtener_db)):
    return db.query(EspacioComun).filter(EspacioComun.edificio_id == edificio.id).order_by(EspacioComun.nombre).all()


@router.post("/{edificio_id}/espacios-comunes", response_model=EspacioComunSalida, status_code=status.HTTP_201_CREATED)
def crear_espacio_comun(
    datos: EspacioComunEntrada,
    edificio: Edificio = Depends(_requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    espacio = EspacioComun(edificio_id=edificio.id, nombre=datos.nombre, capacidad=datos.capacidad, reglas_uso=datos.reglas_uso)
    db.add(espacio)
    db.commit()
    db.refresh(espacio)
    return espacio

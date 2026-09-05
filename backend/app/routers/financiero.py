"""Router del dominio financiero — Documento General, sección 6.

`generar_expensa_mensual`: junta lo que ya está construido en esta fase
(`Gasto`, `services/finanzas.py`, `Departamento.coeficiente`) en una sola
operación transaccional.

Medio de pago y registro de pagos (investigado en
`documentacion/Pagos_y_Conciliacion.md`): el CBU/alias de un edificio es
informativo — la plata nunca pasa por la plataforma, se muestra el dato
para transferir por fuera. Sin QR (decisión final del usuario, corrección
sobre el QR de conveniencia inicial): CBU y alias se copian por separado,
el pago se hace en la app del banco/billetera del usuario. El pago que
carga un propietario/inquilino nace `pendiente`: recién cuenta como
cobrado cuando un Administrador lo concilia contra el movimiento bancario
real y lo confirma.
"""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import extract
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import UsuarioAutenticado, obtener_usuario_actual, requerir_acceso_financiero_edificio
from app.database import obtener_db
from app.models.edificio import Departamento, Edificio, Piso
from app.models.expensa import Expensa, ExpensaDepartamento, ExpensaDetalle
from app.models.gasto import Gasto
from app.models.pago import Pago
from app.routers.edificios import requerir_admin_del_edificio
from app.schemas.financiero import (
    ExpensaGeneracionEntrada,
    ExpensaSalida,
    MedioPagoSalida,
    MiDepartamentoSalida,
    MiExpensaSalida,
    PagoEntrada,
    PagoEstadoEntrada,
    PagoSalida,
)
from app.services.finanzas import calcular_prorrateo_periodo

router = APIRouter(prefix="/api/edificios", tags=["financiero"])
router_pagos = APIRouter(prefix="/api", tags=["financiero"])


@router.post("/{edificio_id}/expensas", response_model=ExpensaSalida, status_code=status.HTTP_201_CREATED)
def generar_expensa_mensual(
    datos: ExpensaGeneracionEntrada,
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    """Toma los `Gasto` del período, arma la apertura por rubro
    (`ExpensaDetalle`) y el monto por departamento (`ExpensaDepartamento`,
    una foto fija — ver `Prorrateo.md` sección 6) usando
    `calcular_prorrateo_periodo()`, ya probado en la tarea anterior. Todo
    en una sola transacción: si el prorrateo falla (coeficientes
    incompletos, sin gastos cargados), no queda nada a medio crear."""
    try:
        montos_por_departamento = calcular_prorrateo_periodo(db, edificio.id, datos.anio, datos.mes)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    gastos_del_periodo = (
        db.query(Gasto)
        .filter(
            Gasto.edificio_id == edificio.id,
            extract("year", Gasto.fecha) == datos.anio,
            extract("month", Gasto.fecha) == datos.mes,
        )
        .all()
    )
    totales_por_rubro = defaultdict(float)
    for gasto in gastos_del_periodo:
        totales_por_rubro[gasto.rubro] += float(gasto.monto)

    expensa = Expensa(
        edificio_id=edificio.id,
        anio=datos.anio,
        mes=datos.mes,
        total=round(sum(totales_por_rubro.values()), 2),
    )
    db.add(expensa)
    try:
        db.flush()  # asigna expensa.id sin cerrar la transacción, y dispara el UniqueConstraint de período si ya existe
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una expensa generada para {datos.mes}/{datos.anio} en este edificio",
        )

    for rubro, monto in totales_por_rubro.items():
        db.add(ExpensaDetalle(expensa_id=expensa.id, rubro=rubro, monto=round(monto, 2)))

    for departamento_id, monto in montos_por_departamento.items():
        db.add(ExpensaDepartamento(expensa_id=expensa.id, departamento_id=departamento_id, monto=monto))

    db.commit()
    db.refresh(expensa)
    return expensa


@router.get("/{edificio_id}/medio-pago", response_model=MedioPagoSalida)
def obtener_medio_pago(
    edificio_id: int,
    db: Session = Depends(obtener_db),
    _: UsuarioAutenticado = Depends(requerir_acceso_financiero_edificio),
):
    """Accesible para Administrador General/de Consorcio del edificio Y
    para cualquier propietario/inquilino con una unidad ahí — a
    diferencia del resto de este router (solo administración), acá el
    residente necesita ver el dato para poder pagar. Sin QR (decisión
    final del usuario, ver `Pagos_y_Conciliacion.md`): CBU y alias se
    copian por separado, el pago se hace desde la app del banco/billetera
    del propio usuario — esta plataforma nunca lo procesa."""
    edificio = db.get(Edificio, edificio_id)
    if not edificio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edificio no encontrado")

    return MedioPagoSalida(cbu=edificio.cbu, alias_cbu=edificio.alias_cbu)


@router_pagos.get("/mis-departamentos", response_model=list[MiDepartamentoSalida])
def listar_mis_departamentos(
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    """Documento General 6.2, "estado de cuenta por unidad": todas las
    unidades del usuario logueado (puede tener más de una, o ninguna —
    nunca se navega el edificio completo), con sus expensas y saldo
    pendiente. `saldo` descuenta solo los `Pago` ya `confirmado`s."""
    departamentos = (
        db.query(Departamento)
        .join(Piso, Piso.id == Departamento.piso_id)
        .filter((Departamento.propietario_id == actual.usuario.id) | (Departamento.inquilino_id == actual.usuario.id))
        .all()
    )

    resultado = []
    for depto in departamentos:
        expensas_salida = []
        for ed in depto.expensas_departamento:
            pagado_confirmado = sum(
                float(p.monto) for p in ed.expensa.pagos
                if p.departamento_id == depto.id and p.estado == "confirmado"
            )
            expensas_salida.append(MiExpensaSalida(
                expensa_id=ed.expensa_id,
                anio=ed.expensa.anio,
                mes=ed.expensa.mes,
                monto=float(ed.monto),
                pagado_confirmado=pagado_confirmado,
                saldo=round(float(ed.monto) - pagado_confirmado, 2),
            ))
        resultado.append(MiDepartamentoSalida(
            departamento_id=depto.id,
            identificador=depto.identificador,
            edificio_id=depto.piso.edificio_id,
            edificio_nombre=depto.piso.edificio.nombre,
            expensas=sorted(expensas_salida, key=lambda e: (e.anio, e.mes)),
        ))
    return resultado


@router_pagos.post("/pagos", response_model=PagoSalida, status_code=status.HTTP_201_CREATED)
def registrar_pago(
    datos: PagoEntrada,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    """El propietario/inquilino carga su propio pago — nace `pendiente`
    (ver `Pagos_y_Conciliacion.md`, sección 3: la conciliación es un paso
    humano, no se confirma solo). `departamento_id` tiene que ser una
    unidad propia: no hay forma de cargar un pago "para otro"."""
    depto = db.get(Departamento, datos.departamento_id)
    if not depto or (depto.propietario_id != actual.usuario.id and depto.inquilino_id != actual.usuario.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ese departamento no es tuyo")

    expensa_depto = (
        db.query(ExpensaDepartamento)
        .filter(ExpensaDepartamento.departamento_id == datos.departamento_id, ExpensaDepartamento.expensa_id == datos.expensa_id)
        .first()
    )
    if not expensa_depto:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esa expensa no corresponde a este departamento")

    pago = Pago(
        departamento_id=datos.departamento_id,
        expensa_id=datos.expensa_id,
        monto=datos.monto,
        fecha=datos.fecha,
        medio_pago=datos.medio_pago,
        comprobante_url=datos.comprobante_url,
    )
    db.add(pago)
    db.commit()
    db.refresh(pago)
    return pago


@router_pagos.patch("/pagos/{pago_id}/estado", response_model=PagoSalida)
def actualizar_estado_pago(
    pago_id: int,
    datos: PagoEstadoEntrada,
    db: Session = Depends(obtener_db),
    actual: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    """Confirma o rechaza un pago — la conciliación real, que solo puede
    hacer un Administrador (General o de Consorcio del edificio del
    departamento pagado), nunca el propio residente que lo cargó."""
    pago = db.get(Pago, pago_id)
    if not pago:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")

    edificio_id = pago.departamento.piso.edificio_id
    es_admin_general = actual.usuario.rol == "admin_general"
    es_admin_de_este_edificio = (
        actual.usuario.rol == "admin_consorcio"
        and db.get(Edificio, edificio_id).admin_consorcio_id == actual.usuario.id
    )
    if not (es_admin_general or es_admin_de_este_edificio):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No administrás este edificio")

    pago.estado = datos.estado
    db.commit()
    db.refresh(pago)
    return pago

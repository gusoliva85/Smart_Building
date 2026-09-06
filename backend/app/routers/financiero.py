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
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import extract
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import UsuarioAutenticado, obtener_usuario_actual, requerir_acceso_financiero_edificio
from app.database import obtener_db
from app.models.edificio import Departamento, Edificio, Piso
from app.models.expensa import Expensa, ExpensaDepartamento, ExpensaDetalle
from app.models.fondo import Caja, Fondo, MovimientoCaja, MovimientoFondo
from app.models.gasto import Gasto
from app.models.pago import Pago
from app.models.presupuesto import Factura, Presupuesto
from app.routers.edificios import requerir_admin_del_edificio
from app.schemas.financiero import (
    DeudorSalida,
    ExpensaGeneracionEntrada,
    ExpensaImpagaSalida,
    ExpensaSalida,
    GastoPorRubroPeriodoSalida,
    MedioPagoSalida,
    MiDepartamentoSalida,
    MiExpensaSalida,
    PagoEntrada,
    PagoEstadoEntrada,
    PagoSalida,
    RecaudadoPeriodoSalida,
    ReporteFinancieroSalida,
)
from app.schemas.fondo import (
    CajaConfiguracion,
    CajaEntrada,
    CajaSalida,
    FondoEntrada,
    FondoSalida,
    MovimientoCajaEntrada,
    MovimientoCajaSalida,
    MovimientoFondoEntrada,
    MovimientoFondoSalida,
)
from app.schemas.gasto import GastoEntrada, GastoSalida
from app.schemas.presupuesto import (
    FacturaEntrada,
    FacturaSalida,
    PresupuestoEntrada,
    PresupuestoEstadoEntrada,
    PresupuestoSalida,
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


TOLERANCIA_SALDO = 0.01  # mismo margen de redondeo que services/finanzas.py, no para deuda real


def _pagado_confirmado(expensa_departamento: ExpensaDepartamento) -> float:
    return sum(
        float(p.monto) for p in expensa_departamento.expensa.pagos
        if p.departamento_id == expensa_departamento.departamento_id and p.estado == "confirmado"
    )


def _saldo(expensa_departamento: ExpensaDepartamento) -> float:
    return round(float(expensa_departamento.monto) - _pagado_confirmado(expensa_departamento), 2)


def _calcular_deudores(db: Session, edificio_id: int, hoy: date | None = None) -> list[DeudorSalida]:
    """Documento Técnico 5.2: vista CALCULADA, no una tabla propia — se
    recorren los `ExpensaDepartamento` de todo el edificio y se descarta
    todo lo que ya está saldado. `meses_atraso` cuenta desde el período
    más viejo con saldo pendiente hasta hoy, sin contar el mes de la
    propia expensa (la del mes corriente todavía no está "atrasada",
    aunque tenga saldo) — así 1 mes vencido da amarillo, más de 1 da
    rojo (Documento General 6.3). Factorizada de `listar_deudores` para
    que `reportes/financiero` reutilice el mismo cálculo, no lo repita."""
    hoy = hoy or date.today()
    mes_actual_absoluto = hoy.year * 12 + hoy.month

    departamentos = (
        db.query(Departamento)
        .join(Piso, Piso.id == Departamento.piso_id)
        .filter(Piso.edificio_id == edificio_id)
        .all()
    )

    deudores = []
    for depto in departamentos:
        impagas = []
        for ed in depto.expensas_departamento:
            saldo = _saldo(ed)
            if saldo > TOLERANCIA_SALDO:
                impagas.append((ed, saldo))
        if not impagas:
            continue

        mas_vieja = min(ed.expensa.anio * 12 + ed.expensa.mes for ed, _ in impagas)
        meses_atraso = max(0, mes_actual_absoluto - mas_vieja)

        deudores.append(DeudorSalida(
            departamento_id=depto.id,
            identificador=depto.identificador,
            propietario_id=depto.propietario_id,
            inquilino_id=depto.inquilino_id,
            deuda_total=round(sum(saldo for _, saldo in impagas), 2),
            meses_atraso=meses_atraso,
            expensas_impagas=sorted(
                (ExpensaImpagaSalida(expensa_id=ed.expensa_id, anio=ed.expensa.anio, mes=ed.expensa.mes, saldo=saldo)
                 for ed, saldo in impagas),
                key=lambda e: (e.anio, e.mes),
            ),
        ))

    return sorted(deudores, key=lambda d: d.meses_atraso, reverse=True)


@router.get("/{edificio_id}/deudores", response_model=list[DeudorSalida])
def listar_deudores(
    hoy: date | None = None,
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    """`hoy` es un parámetro de test/depuración (por defecto la fecha
    real) para no depender de la fecha del sistema en los tests."""
    return _calcular_deudores(db, edificio.id, hoy)


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
        expensas_salida = [
            MiExpensaSalida(
                expensa_id=ed.expensa_id,
                anio=ed.expensa.anio,
                mes=ed.expensa.mes,
                monto=float(ed.monto),
                pagado_confirmado=_pagado_confirmado(ed),
                saldo=_saldo(ed),
            )
            for ed in depto.expensas_departamento
        ]
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


# ------------------------------------------------------------------
# Gastos, Fondos, Caja, Presupuestos y Facturas — CRUD anidado bajo
# edificio (Documento General 6.4-6.8). Todo admin-only (mismo criterio
# que el resto de este router salvo medio-pago/mis-departamentos/pagos):
# es información de gestión interna, no algo que un residente cargue o
# necesite ver directo.
# ------------------------------------------------------------------

@router.post("/{edificio_id}/gastos", response_model=GastoSalida, status_code=status.HTTP_201_CREATED)
def crear_gasto(
    datos: GastoEntrada,
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    gasto = Gasto(edificio_id=edificio.id, **datos.model_dump())
    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    return gasto


@router.get("/{edificio_id}/gastos", response_model=list[GastoSalida])
def listar_gastos(
    anio: int | None = None,
    mes: int | None = None,
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    consulta = db.query(Gasto).filter(Gasto.edificio_id == edificio.id)
    if anio is not None:
        consulta = consulta.filter(extract("year", Gasto.fecha) == anio)
    if mes is not None:
        consulta = consulta.filter(extract("month", Gasto.fecha) == mes)
    return consulta.order_by(Gasto.fecha.desc()).all()


def _saldo_fondo(fondo: Fondo) -> float:
    return round(sum(
        float(m.monto) if m.tipo == "ingreso" else -float(m.monto)
        for m in fondo.movimientos
    ), 2)


def _salida_fondo(fondo: Fondo) -> FondoSalida:
    return FondoSalida(
        id=fondo.id, edificio_id=fondo.edificio_id, nombre=fondo.nombre,
        saldo=_saldo_fondo(fondo), creado_en=fondo.creado_en,
    )


@router.post("/{edificio_id}/fondos", response_model=FondoSalida, status_code=status.HTTP_201_CREATED)
def crear_fondo(
    datos: FondoEntrada,
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    fondo = Fondo(edificio_id=edificio.id, nombre=datos.nombre)
    db.add(fondo)
    db.commit()
    db.refresh(fondo)
    return _salida_fondo(fondo)


@router.get("/{edificio_id}/fondos", response_model=list[FondoSalida])
def listar_fondos(
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    fondos = db.query(Fondo).filter(Fondo.edificio_id == edificio.id).order_by(Fondo.nombre).all()
    return [_salida_fondo(f) for f in fondos]


def _obtener_fondo_del_edificio_o_404(fondo_id: int, edificio_id: int, db: Session) -> Fondo:
    fondo = db.get(Fondo, fondo_id)
    if not fondo or fondo.edificio_id != edificio_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fondo no encontrado en este edificio")
    return fondo


@router.post(
    "/{edificio_id}/fondos/{fondo_id}/movimientos",
    response_model=MovimientoFondoSalida,
    status_code=status.HTTP_201_CREATED,
)
def crear_movimiento_fondo(
    fondo_id: int,
    datos: MovimientoFondoEntrada,
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    _obtener_fondo_del_edificio_o_404(fondo_id, edificio.id, db)
    movimiento = MovimientoFondo(fondo_id=fondo_id, **datos.model_dump(exclude_none=True))
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    return movimiento


@router.get("/{edificio_id}/fondos/{fondo_id}/movimientos", response_model=list[MovimientoFondoSalida])
def listar_movimientos_fondo(
    fondo_id: int,
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    fondo = _obtener_fondo_del_edificio_o_404(fondo_id, edificio.id, db)
    return fondo.movimientos


def _saldo_caja(caja: Caja) -> float:
    return round(sum(
        float(m.monto) if m.tipo == "ingreso" else -float(m.monto)
        for m in caja.movimientos
    ), 2)


def _salida_caja(caja: Caja) -> CajaSalida:
    return CajaSalida(
        id=caja.id, edificio_id=caja.edificio_id, responsable_id=caja.responsable_id,
        monto_fijo=float(caja.monto_fijo), saldo=_saldo_caja(caja), creado_en=caja.creado_en,
    )


@router.post("/{edificio_id}/caja", response_model=CajaSalida, status_code=status.HTTP_201_CREATED)
def crear_caja(
    datos: CajaEntrada,
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    caja = Caja(edificio_id=edificio.id, responsable_id=datos.responsable_id, monto_fijo=datos.monto_fijo)
    db.add(caja)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este edificio ya tiene una caja chica creada")
    db.refresh(caja)
    return _salida_caja(caja)


def _obtener_caja_del_edificio_o_404(edificio_id: int, db: Session) -> Caja:
    caja = db.query(Caja).filter(Caja.edificio_id == edificio_id).first()
    if not caja:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Este edificio todavía no tiene caja chica")
    return caja


@router.get("/{edificio_id}/caja", response_model=CajaSalida)
def obtener_caja(
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    return _salida_caja(_obtener_caja_del_edificio_o_404(edificio.id, db))


@router.patch("/{edificio_id}/caja", response_model=CajaSalida)
def configurar_caja(
    datos: CajaConfiguracion,
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    caja = _obtener_caja_del_edificio_o_404(edificio.id, db)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(caja, campo, valor)
    db.commit()
    db.refresh(caja)
    return _salida_caja(caja)


@router.post(
    "/{edificio_id}/caja/movimientos",
    response_model=MovimientoCajaSalida,
    status_code=status.HTTP_201_CREATED,
)
def crear_movimiento_caja(
    datos: MovimientoCajaEntrada,
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    caja = _obtener_caja_del_edificio_o_404(edificio.id, db)
    movimiento = MovimientoCaja(caja_id=caja.id, **datos.model_dump(exclude_none=True))
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    return movimiento


@router.get("/{edificio_id}/caja/movimientos", response_model=list[MovimientoCajaSalida])
def listar_movimientos_caja(
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    caja = _obtener_caja_del_edificio_o_404(edificio.id, db)
    return caja.movimientos


@router.post("/{edificio_id}/presupuestos", response_model=PresupuestoSalida, status_code=status.HTTP_201_CREATED)
def crear_presupuesto(
    datos: PresupuestoEntrada,
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    presupuesto = Presupuesto(edificio_id=edificio.id, **datos.model_dump(exclude_none=True))
    db.add(presupuesto)
    db.commit()
    db.refresh(presupuesto)
    return presupuesto


@router.get("/{edificio_id}/presupuestos", response_model=list[PresupuestoSalida])
def listar_presupuestos(
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    return (
        db.query(Presupuesto)
        .filter(Presupuesto.edificio_id == edificio.id)
        .order_by(Presupuesto.creado_en.desc())
        .all()
    )


@router.patch("/{edificio_id}/presupuestos/{presupuesto_id}/estado", response_model=PresupuestoSalida)
def actualizar_estado_presupuesto(
    presupuesto_id: int,
    datos: PresupuestoEstadoEntrada,
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    """Aprobar puede (opcionalmente) vincular el presupuesto al `Gasto`
    real que generó — el mismo criterio de comparar antes de aprobar de
    `Pagos_y_Conciliacion.md`, aplicado acá: nada obliga a que el gasto ya
    exista en el momento de aprobar el presupuesto."""
    presupuesto = db.get(Presupuesto, presupuesto_id)
    if not presupuesto or presupuesto.edificio_id != edificio.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presupuesto no encontrado en este edificio")

    if datos.gasto_id is not None:
        gasto = db.get(Gasto, datos.gasto_id)
        if not gasto or gasto.edificio_id != edificio.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="gasto_id debe pertenecer a este edificio")
        presupuesto.gasto_id = datos.gasto_id

    presupuesto.estado = datos.estado
    db.commit()
    db.refresh(presupuesto)
    return presupuesto


@router.post("/{edificio_id}/facturas", response_model=FacturaSalida, status_code=status.HTTP_201_CREATED)
def crear_factura(
    datos: FacturaEntrada,
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    gasto = db.get(Gasto, datos.gasto_id)
    if not gasto or gasto.edificio_id != edificio.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="gasto_id debe pertenecer a este edificio")

    factura = Factura(**datos.model_dump(exclude_none=True))
    db.add(factura)
    db.commit()
    db.refresh(factura)
    return factura


@router.get("/{edificio_id}/facturas", response_model=list[FacturaSalida])
def listar_facturas(
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    return (
        db.query(Factura)
        .join(Gasto, Gasto.id == Factura.gasto_id)
        .filter(Gasto.edificio_id == edificio.id)
        .order_by(Factura.creado_en.desc())
        .all()
    )


@router.get("/{edificio_id}/reportes/financiero", response_model=ReporteFinancieroSalida)
def obtener_reporte_financiero(
    edificio: Edificio = Depends(requerir_admin_del_edificio),
    db: Session = Depends(obtener_db),
):
    """Documento Técnico, sección 8: consolida en un solo endpoint la data
    cruda para Analítica (Fase 6) — recaudado vs. esperado, morosidad,
    evolución de gastos por rubro. Ninguna de las tres se recalcula desde
    cero: reutiliza `Expensa`/`Pago` (Tareas 3-4, 8-9), `Gasto` (Tarea 2,
    11) y `_calcular_deudores()` (Tarea 10) tal cual ya están probados."""
    expensas = db.query(Expensa).filter(Expensa.edificio_id == edificio.id).order_by(Expensa.anio, Expensa.mes).all()
    recaudado_vs_esperado = [
        RecaudadoPeriodoSalida(
            anio=expensa.anio,
            mes=expensa.mes,
            esperado=float(expensa.total),
            recaudado=round(sum(float(p.monto) for p in expensa.pagos if p.estado == "confirmado"), 2),
        )
        for expensa in expensas
    ]

    gastos = db.query(Gasto).filter(Gasto.edificio_id == edificio.id).all()
    totales_por_rubro_periodo = defaultdict(float)
    for gasto in gastos:
        totales_por_rubro_periodo[(gasto.rubro, gasto.fecha.year, gasto.fecha.month)] += float(gasto.monto)
    gastos_por_rubro = [
        GastoPorRubroPeriodoSalida(rubro=rubro, anio=anio, mes=mes, monto=round(monto, 2))
        for (rubro, anio, mes), monto in sorted(totales_por_rubro_periodo.items(), key=lambda item: (item[0][1], item[0][2], item[0][0]))
    ]

    deudores = _calcular_deudores(db, edificio.id)

    return ReporteFinancieroSalida(
        recaudado_vs_esperado=recaudado_vs_esperado,
        gastos_por_rubro=gastos_por_rubro,
        deuda_total_actual=round(sum(d.deuda_total for d in deudores), 2),
        cantidad_deudores=len(deudores),
    )

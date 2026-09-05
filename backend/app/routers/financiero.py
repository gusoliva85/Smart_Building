"""Router del dominio financiero — Documento General, sección 6. Primer
endpoint: generación de la expensa mensual, que junta lo que ya está
construido en esta fase (`Gasto`, `services/finanzas.py`, `Departamento.
coeficiente`) en una sola operación transaccional.
"""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import extract
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import obtener_db
from app.models.edificio import Edificio
from app.models.expensa import Expensa, ExpensaDepartamento, ExpensaDetalle
from app.models.gasto import Gasto
from app.routers.edificios import requerir_admin_del_edificio
from app.schemas.financiero import ExpensaGeneracionEntrada, ExpensaSalida
from app.services.finanzas import calcular_prorrateo_periodo

router = APIRouter(prefix="/api/edificios", tags=["financiero"])


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

"""Pruebas del reporte financiero consolidado (`F2-T16`).

Lo que se prueba:

  1. **Que consolide y no recalcule**: los numeros del reporte tienen que
     coincidir **exactamente** con los de las pantallas de las que salen. Hay
     un test que compara el reporte contra la vista de deudores y otro contra
     el listado de gastos.
  2. **Los tres numeros que parecen el mismo**: gastos, esperado y recaudado,
     y que el pendiente de confirmar no cuente como recaudado.
  3. **Que un porcentaje nulo signifique algo distinto de cero.**
  4. **Que los pagos se imputen al periodo de su expensa**, no a su fecha.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core import security
from app.models.edificio import Departamento, Edificio, Piso
from app.models.finanzas import Expensa, Gasto, Pago
from app.models.usuario import Usuario
from app.services import autorizacion, finanzas, reportes


# ===========================================================================
# LA LOGICA PURA
# ===========================================================================


def test_un_porcentaje_sobre_cero_es_nulo_y_no_cero():
    """**La diferencia importa:** "se recaudo el 0%" dice que nadie pago, y "no
    hay nada que recaudar" dice que no hubo liquidacion. Un cero en lugar de un
    hueco es la forma mas facil de que un grafico muestre una caida que nunca
    existio."""
    assert reportes.porcentaje(Decimal("0.00"), Decimal("0.00")) is None
    assert reportes.porcentaje(Decimal("0.00"), Decimal("100.00")) == Decimal("0.00")


def test_el_porcentaje_tiene_dos_decimales():
    assert reportes.porcentaje(Decimal("1.00"), Decimal("3.00")) == Decimal("33.33")


def test_el_porcentaje_del_resumen_no_es_el_promedio_de_los_mensuales():
    """**Son dos numeros distintos.** Un mes al 100% sobre una expensa chica no
    compensa uno al 50% sobre una grande, y promediarlos diria 75% cuando no es
    cierto."""
    chico = reportes.PeriodoDelReporte(
        anio=2026,
        mes=10,
        gastos=Decimal("1000.00"),
        esperado=Decimal("1000.00"),
        recaudado=Decimal("1000.00"),
        pendiente_de_confirmar=Decimal("0.00"),
    )
    grande = reportes.PeriodoDelReporte(
        anio=2026,
        mes=11,
        gastos=Decimal("100000.00"),
        esperado=Decimal("100000.00"),
        recaudado=Decimal("50000.00"),
        pendiente_de_confirmar=Decimal("0.00"),
    )

    resumen = reportes.resumir([chico, grande])

    assert chico.porcentaje_recaudado == Decimal("100.00")
    assert grande.porcentaje_recaudado == Decimal("50.00")
    # El promedio seria 75%. El real es 50,50%.
    assert resumen.porcentaje_recaudado == Decimal("50.50")


def test_lo_por_cobrar_nunca_es_negativo():
    """Si se cobro de mas, no falta cobrar menos que nada."""
    periodo = reportes.PeriodoDelReporte(
        anio=2026,
        mes=11,
        gastos=Decimal("100.00"),
        esperado=Decimal("100.00"),
        recaudado=Decimal("150.00"),
        pendiente_de_confirmar=Decimal("0.00"),
    )

    assert periodo.por_cobrar == Decimal("0.00")


def test_la_evolucion_devuelve_un_valor_por_periodo_con_cero_donde_falta():
    """La pantalla lo grafica sin rellenar huecos: el relleno en el cliente es
    como se terminan desalineando dos series."""
    periodos = [(2026, 9), (2026, 10), (2026, 11)]
    gastos = {
        (2026, 9): {"limpieza": Decimal("100.00")},
        (2026, 11): {"limpieza": Decimal("300.00"), "sueldos": Decimal("900.00")},
    }

    series = reportes.armar_evolucion(
        periodos, gastos, {"limpieza": "Limpieza", "sueldos": "Sueldos"},
        ("sueldos", "limpieza"),
    )

    por_rubro = {s.rubro: s for s in series}
    assert por_rubro["limpieza"].por_periodo == (
        Decimal("100.00"),
        Decimal("0.00"),
        Decimal("300.00"),
    )
    assert por_rubro["sueldos"].por_periodo == (
        Decimal("0.00"),
        Decimal("0.00"),
        Decimal("900.00"),
    )


def test_la_evolucion_deja_afuera_los_rubros_sin_gastos():
    """Diez filas en cero no son informacion."""
    series = reportes.armar_evolucion(
        [(2026, 11)],
        {(2026, 11): {"limpieza": Decimal("100.00")}},
        {"limpieza": "Limpieza", "seguros": "Seguros"},
        ("limpieza", "seguros"),
    )

    assert [s.rubro for s in series] == ["limpieza"]


def test_el_orden_de_los_rubros_es_el_del_catalogo_y_no_el_del_monto():
    """La liquidacion y el reporte se leen con los rubros en el mismo orden mes
    a mes, asi que comparar dos meses es mirar la misma fila."""
    series = reportes.armar_evolucion(
        [(2026, 11)],
        {(2026, 11): {"limpieza": Decimal("900.00"), "sueldos": Decimal("100.00")}},
        {"limpieza": "Limpieza", "sueldos": "Sueldos"},
        ("sueldos", "limpieza"),  # el orden del catalogo
    )

    assert [s.rubro for s in series] == ["sueldos", "limpieza"]


# ===========================================================================
# ESCENARIO PARA EL ENDPOINT
# ===========================================================================


def _usuario(db, rol, nombre) -> Usuario:
    usuario = Usuario(
        nombre=nombre,
        email=f"{nombre.lower().replace(' ', '')}@prueba.com.ar",
        password_hash=security.hashear_password("Prueba123!"),
        rol=rol,
        activo=True,
    )
    db.add(usuario)
    db.commit()
    return usuario


def _login(cliente, usuario) -> dict:
    respuesta = cliente.post(
        "/api/auth/login",
        data={"username": usuario.email, "password": "Prueba123!"},
    )
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def _edificio(db, unidades=2, recargo="0.00") -> Edificio:
    edificio = Edificio(
        nombre="Consorcio Mitre 500",
        direccion="Mitre 500",
        cp="C1000",
        dias_vencimiento_expensas=10,
        recargo_mora_porcentual=Decimal(recargo),
    )
    db.add(edificio)
    db.commit()
    piso = Piso(edificio_id=edificio.id, numero=1, orden=1)
    db.add(piso)
    db.commit()
    for numero, coeficiente in enumerate(
        finanzas.calcular_partes_iguales(unidades), start=1
    ):
        db.add(
            Departamento(
                piso_id=piso.id,
                identificador=f"1{chr(64 + numero)}",
                coeficiente=coeficiente,
            )
        )
    db.commit()
    return edificio


def _gasto(db, edificio, rubro="limpieza", monto="100000.00", mes=11):
    db.add(
        Gasto(
            edificio_id=edificio.id,
            rubro=rubro,
            monto=Decimal(monto),
            fecha=date(2026, mes, 5),
        )
    )
    db.commit()


def _liquidar(cliente, edificio, admin, mes=11, publicar=True):
    expensa = cliente.post(
        f"/api/edificios/{edificio.id}/expensas",
        json={"anio": 2026, "mes": mes},
        headers=admin,
    ).json()
    if publicar:
        cliente.post(
            f"/api/edificios/{edificio.id}/expensas/{expensa['id']}/publicar",
            headers=admin,
        )
    return expensa


def _reporte(cliente, edificio, headers, **filtros):
    base = {"hasta_anio": 2026, "hasta_mes": 11, "meses": 3}
    base.update(filtros)
    consulta = "&".join(f"{k}={v}" for k, v in base.items())
    return cliente.get(
        f"/api/edificios/{edificio.id}/reportes/financiero?{consulta}",
        headers=headers,
    )


# ===========================================================================
# EL ENDPOINT
# ===========================================================================


def test_un_edificio_sin_nada_devuelve_el_reporte_vacio_y_no_un_error(
    cliente, como, db
):
    """El estado inicial de todo edificio. Un 404 obligaria a la pantalla a
    tratar lo normal como una excepcion."""
    edificio = _edificio(db)

    respuesta = _reporte(cliente, edificio, como("admin_general"))

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["resumen"]["gastos"] == "0.00"
    assert cuerpo["gastos_por_rubro"] == []
    assert len(cuerpo["periodos"]) == 3


def test_los_periodos_van_del_mas_viejo_al_mas_nuevo(cliente, como, db):
    """Al contrario de los listados, que muestran lo ultimo primero: es el
    orden de un grafico de evolucion, el tiempo va hacia la derecha."""
    edificio = _edificio(db)

    cuerpo = _reporte(cliente, edificio, como("admin_general")).json()

    assert [p["periodo"] for p in cuerpo["periodos"]] == [
        "09/2026",
        "10/2026",
        "11/2026",
    ]
    assert cuerpo["desde"] == "09/2026"
    assert cuerpo["hasta"] == "11/2026"


def test_el_rango_cruza_el_cambio_de_anio(cliente, como, db):
    """Restar un mes a enero es diciembre del ano anterior, y es la unica regla
    de la cuenta."""
    edificio = _edificio(db)

    cuerpo = _reporte(
        cliente, edificio, como("admin_general"), hasta_anio=2027, hasta_mes=1, meses=3
    ).json()

    assert [p["periodo"] for p in cuerpo["periodos"]] == [
        "11/2026",
        "12/2026",
        "01/2027",
    ]


def test_los_gastos_del_reporte_coinciden_con_el_listado_de_gastos(cliente, como, db):
    """**Que consolide y no recalcule, verificado.** Si el reporte tuviera su
    propia consulta, el dia que cambie que gasto es de noviembre habria dos
    respuestas distintas."""
    edificio = _edificio(db)
    headers = como("admin_general")
    _gasto(db, edificio, "limpieza", "100000.00", mes=11)
    _gasto(db, edificio, "sueldos", "300000.50", mes=11)

    listado = cliente.get(
        f"/api/edificios/{edificio.id}/gastos?anio=2026&mes=11", headers=headers
    ).json()
    reporte = _reporte(cliente, edificio, headers).json()
    noviembre = [p for p in reporte["periodos"] if p["periodo"] == "11/2026"][0]

    assert noviembre["gastos"] == listado["total"] == "400000.50"


def test_la_morosidad_del_reporte_coincide_con_la_vista_de_deudores(
    cliente, como, db
):
    """Las dos salen de las mismas funciones. Un reporte que no coincide con la
    pantalla de la que sale es peor que no tener reporte."""
    edificio = _edificio(db)
    headers = como("admin_general")
    _gasto(db, edificio)
    expensa = _liquidar(cliente, edificio, headers)
    fila = db.get(Expensa, expensa["id"])
    fila.publicada_en = datetime.now() - timedelta(days=40)
    db.commit()

    deudores_api = cliente.get(
        f"/api/edificios/{edificio.id}/deudores", headers=headers
    ).json()
    reporte = _reporte(cliente, edificio, headers).json()

    assert reporte["morosidad_de_hoy"]["total"] == deudores_api["total"]
    assert reporte["morosidad_de_hoy"]["total_vencido"] == deudores_api["total_vencido"]
    assert (
        reporte["morosidad_de_hoy"]["unidades_con_deuda"]
        == deudores_api["cantidad_deudores"]
    )


def test_una_expensa_en_borrador_no_entra_en_lo_esperado(cliente, como, db):
    """Un borrador no se le cobro a nadie: incluirlo inflaria el numero con
    plata que todavia nadie debe."""
    edificio = _edificio(db)
    headers = como("admin_general")
    _gasto(db, edificio)
    _liquidar(cliente, edificio, headers, publicar=False)

    cuerpo = _reporte(cliente, edificio, headers).json()
    noviembre = [p for p in cuerpo["periodos"] if p["periodo"] == "11/2026"][0]

    assert noviembre["gastos"] == "100000.00"
    assert noviembre["esperado"] == "0.00"
    assert noviembre["liquidada"] is False


def test_un_mes_sin_liquidar_se_distingue_de_un_mes_sin_cobrar(cliente, como, db):
    """**Para esto existe `liquidada`.** Sin el campo, un mes con gastos y sin
    expensa pareceria un mes en el que nadie pago, cuando lo que falta es
    generar la liquidacion. Y el porcentaje es **nulo**, no cero."""
    edificio = _edificio(db)
    headers = como("admin_general")
    _gasto(db, edificio)
    _liquidar(cliente, edificio, headers, publicar=False)

    noviembre = [
        p
        for p in _reporte(cliente, edificio, headers).json()["periodos"]
        if p["periodo"] == "11/2026"
    ][0]

    assert noviembre["porcentaje_recaudado"] is None


def test_el_recaudado_cuenta_solo_los_pagos_confirmados(cliente, como, db):
    """La regla fundamental del modulo, verificada tambien en el reporte."""
    edificio = _edificio(db)
    headers = como("admin_general")
    unidad = db.scalars(select(Departamento)).first()
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Dueno Uno")
    unidad.propietario_id = propietario.id
    db.commit()
    _gasto(db, edificio)
    expensa = _liquidar(cliente, edificio, headers)

    pago = cliente.post(
        "/api/mis-pagos",
        json={
            "expensa_id": expensa["id"],
            "monto": "50000.00",
            "fecha": "2026-11-20",
            "medio_pago": "transferencia",
        },
        headers=_login(cliente, propietario),
    ).json()

    con_pendiente = [
        p
        for p in _reporte(cliente, edificio, headers).json()["periodos"]
        if p["periodo"] == "11/2026"
    ][0]

    cliente.patch(
        f"/api/edificios/{edificio.id}/pagos/{pago['id']}",
        json={"estado": "confirmado"},
        headers=headers,
    )
    confirmado = [
        p
        for p in _reporte(cliente, edificio, headers).json()["periodos"]
        if p["periodo"] == "11/2026"
    ][0]

    assert con_pendiente["recaudado"] == "0.00"
    assert con_pendiente["pendiente_de_confirmar"] == "50000.00"
    assert confirmado["recaudado"] == "50000.00"
    assert confirmado["pendiente_de_confirmar"] == "0.00"
    assert confirmado["porcentaje_recaudado"] == "50.00"


def test_el_pago_se_imputa_al_periodo_de_su_expensa_y_no_a_su_fecha(
    cliente, como, db
):
    """**La pregunta que el reporte contesta** es "cuanto de la expensa de
    noviembre se cobro". Alguien que paga noviembre en enero suma a noviembre,
    no a enero."""
    edificio = _edificio(db)
    headers = como("admin_general")
    unidad = db.scalars(select(Departamento)).first()
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Dueno Dos")
    unidad.propietario_id = propietario.id
    db.commit()
    _gasto(db, edificio, mes=9)
    septiembre = _liquidar(cliente, edificio, headers, mes=9)

    # Paga en noviembre la expensa de septiembre.
    pago = cliente.post(
        "/api/mis-pagos",
        json={
            "expensa_id": septiembre["id"],
            "monto": "50000.00",
            "fecha": "2026-11-28",
            "medio_pago": "transferencia",
        },
        headers=_login(cliente, propietario),
    ).json()
    cliente.patch(
        f"/api/edificios/{edificio.id}/pagos/{pago['id']}",
        json={"estado": "confirmado"},
        headers=headers,
    )

    periodos = {
        p["periodo"]: p for p in _reporte(cliente, edificio, headers).json()["periodos"]
    }

    assert periodos["09/2026"]["recaudado"] == "50000.00"
    assert periodos["11/2026"]["recaudado"] == "0.00"


def test_la_participacion_de_cada_rubro_sale_calculada(cliente, como, db):
    edificio = _edificio(db)
    headers = como("admin_general")
    _gasto(db, edificio, "sueldos", "750000.00", mes=11)
    _gasto(db, edificio, "limpieza", "250000.00", mes=11)

    series = {
        s["rubro"]: s
        for s in _reporte(cliente, edificio, headers).json()["gastos_por_rubro"]
    }

    assert series["sueldos"]["participacion"] == "75.00"
    assert series["limpieza"]["participacion"] == "25.00"


def test_la_evolucion_trae_un_valor_por_periodo(cliente, como, db):
    edificio = _edificio(db)
    headers = como("admin_general")
    _gasto(db, edificio, "limpieza", "100.00", mes=9)
    _gasto(db, edificio, "limpieza", "300.00", mes=11)

    serie = _reporte(cliente, edificio, headers).json()["gastos_por_rubro"][0]

    assert serie["por_periodo"] == ["100.00", "0.00", "300.00"]
    assert serie["total"] == "400.00"


def test_el_resumen_trae_lo_guardado_en_los_fondos(cliente, como, db):
    """No es del periodo: es de hoy, igual que la morosidad."""
    edificio = _edificio(db)
    headers = como("admin_general")
    fondo = cliente.post(
        f"/api/edificios/{edificio.id}/fondos",
        json={"nombre": "Fondo de reserva"},
        headers=headers,
    ).json()
    cliente.post(
        f"/api/edificios/{edificio.id}/fondos/{fondo['id']}/movimientos",
        json={"tipo": "ingreso", "monto": "750000.00", "fecha": "2026-11-05"},
        headers=headers,
    )

    cuerpo = _reporte(cliente, edificio, headers).json()

    assert cuerpo["resumen"]["total_en_fondos"] == "750000.00"


def test_el_reporte_distingue_unidades_con_deuda_de_unidades_atrasadas(
    cliente, como, db
):
    """La primera incluye a quien debe la expensa publicada hace tres dias, que
    hay que cobrarle pero no esta atrasado. El color del Dashboard lo decide la
    segunda."""
    edificio = _edificio(db)
    headers = como("admin_general")
    _gasto(db, edificio)
    _liquidar(cliente, edificio, headers)

    morosidad = _reporte(cliente, edificio, headers).json()["morosidad_de_hoy"]

    assert morosidad["unidades_con_deuda"] == 2
    assert morosidad["unidades_con_atraso"] == 0
    assert morosidad["porcentaje_unidades_con_atraso"] == "0.00"


# ===========================================================================
# PERMISOS Y VALIDACION
# ===========================================================================


def test_un_residente_no_ve_el_reporte(cliente, como, db):
    edificio = _edificio(db)

    respuesta = _reporte(cliente, edificio, como("propietario"))

    assert respuesta.status_code == 403


def test_un_encargado_no_ve_el_reporte(cliente, como, db):
    edificio = _edificio(db)

    respuesta = _reporte(cliente, edificio, como("encargado"))

    assert respuesta.status_code == 403


def test_un_admin_de_consorcio_no_ve_el_reporte_de_un_edificio_ajeno(
    cliente, como, db
):
    edificio = _edificio(db)

    respuesta = _reporte(cliente, edificio, como(autorizacion.ADMIN_CONSORCIO))

    assert respuesta.status_code == 404


def test_sin_sesion_no_se_ve_el_reporte(cliente, db):
    edificio = _edificio(db)

    assert (
        cliente.get(f"/api/edificios/{edificio.id}/reportes/financiero").status_code
        == 401
    )


@pytest.mark.parametrize("meses", [0, 37])
def test_un_rango_absurdo_se_rechaza(cliente, como, db, meses):
    """Cero meses no es un reporte, y mas de tres anios en una pantalla no se
    lee."""
    edificio = _edificio(db)

    respuesta = _reporte(cliente, edificio, como("admin_general"), meses=meses)

    assert respuesta.status_code == 422

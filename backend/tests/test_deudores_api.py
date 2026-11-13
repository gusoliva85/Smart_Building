"""Pruebas del endpoint de deudores y del recargo real (`F2-T11`).

Dos cosas que esta tarea cierra:

  1. **La vista de deudores**, de punta a punta: liquidar, publicar, dejar
     impago, y ver aparecer la unidad con su atraso y su color.
  2. **La costura que `F2-T05` dejo abierta.** Ahora que los pagos existen, el
     recargo por mora y el saldo a favor se calculan de verdad al generar la
     liquidacion siguiente. Los dos tests que lo verifican son los mas
     importantes del archivo.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core import security
from app.models.edificio import Departamento, Edificio, Piso
from app.models.finanzas import Expensa, Gasto, Pago
from app.models.usuario import Usuario
from app.services import autorizacion, finanzas


# ===========================================================================
# ESCENARIO
# ===========================================================================


def _usuario(db, rol: str, nombre: str) -> Usuario:
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


def _edificio_listo(db, unidades=2, dias_vencimiento=10, recargo="0.00") -> Edificio:
    edificio = Edificio(
        nombre="Consorcio Mitre 500",
        direccion="Mitre 500",
        cp="C1000",
        dias_vencimiento_expensas=dias_vencimiento,
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


def _unidades(db, edificio) -> list[Departamento]:
    return list(
        db.scalars(
            select(Departamento)
            .join(Piso, Piso.id == Departamento.piso_id)
            .where(Piso.edificio_id == edificio.id)
            .order_by(Departamento.identificador)
        ).all()
    )


def _liquidar(cliente, db, edificio, admin, monto="100000.00", mes=11, publicar=True):
    db.add(
        Gasto(
            edificio_id=edificio.id,
            rubro="limpieza",
            monto=Decimal(monto),
            fecha=date(2026, mes, 5),
        )
    )
    db.commit()

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


def _vencer(db, expensa_id, dias_atras=40):
    """Mueve la fecha de publicacion al pasado para que la expensa este vencida.

    Es la unica forma de probar el atraso sin esperar cuarenta dias. **Es dato
    de prueba inventado**: en produccion esa fecha la escribe el endpoint de
    publicar y nadie la toca.
    """
    expensa = db.get(Expensa, expensa_id)
    expensa.publicada_en = datetime.now() - timedelta(days=dias_atras)
    db.commit()


def _deudores(cliente, edificio, headers, **filtros):
    consulta = "&".join(f"{k}={v}" for k, v in filtros.items())
    ruta = f"/api/edificios/{edificio.id}/deudores"
    if consulta:
        ruta += f"?{consulta}"
    return cliente.get(ruta, headers=headers)


# ===========================================================================
# LA VISTA
# ===========================================================================


def test_un_edificio_sin_liquidaciones_no_tiene_deudores(cliente, como, db):
    edificio = _edificio_listo(db)

    respuesta = _deudores(cliente, edificio, como("admin_general"))

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["cantidad_deudores"] == 0
    assert cuerpo["cantidad_unidades"] == 2
    assert cuerpo["total"] == "0.00"


def test_una_expensa_en_borrador_no_genera_deudores(cliente, como, db):
    """Deuda es lo publicado: hasta que la administracion no publico la
    liquidacion, el vecino no tuvo forma de pagarla."""
    admin = como("admin_general")
    edificio = _edificio_listo(db)
    _liquidar(cliente, db, edificio, admin, publicar=False)

    cuerpo = _deudores(cliente, edificio, admin).json()

    assert cuerpo["cantidad_deudores"] == 0


def test_una_deuda_en_termino_aparece_con_saldo_pero_sin_atraso(cliente, como, db):
    """**La regla de la tarea.** Hay que cobrarle, pero no esta atrasada: no
    pinta nada en el Dashboard Visual."""
    admin = como("admin_general")
    edificio = _edificio_listo(db, dias_vencimiento=10)
    _liquidar(cliente, db, edificio, admin)

    cuerpo = _deudores(cliente, edificio, admin).json()

    assert cuerpo["cantidad_deudores"] == 2
    deudor = cuerpo["deudores"][0]
    assert deudor["saldo"] == "50000.00"
    assert deudor["vencido"] == "0.00"
    assert deudor["meses_de_atraso"] == 0
    assert deudor["severidad"] == "ok"


def test_pasado_el_vencimiento_la_unidad_pinta_amarillo(cliente, como, db):
    admin = como("admin_general")
    edificio = _edificio_listo(db, dias_vencimiento=10)
    expensa = _liquidar(cliente, db, edificio, admin)
    _vencer(db, expensa["id"])

    deudor = _deudores(cliente, edificio, admin).json()["deudores"][0]

    assert deudor["meses_de_atraso"] == 1
    assert deudor["severidad"] == "warn"
    assert deudor["vencido"] == "50000.00"
    assert deudor["periodo_mas_viejo"] == "11/2026"


def test_con_dos_periodos_vencidos_pinta_rojo(cliente, como, db):
    """Un mes amarillo, mas de uno rojo. Es el dato que alimenta el Dashboard
    Visual de la Fase 5."""
    admin = como("admin_general")
    edificio = _edificio_listo(db, dias_vencimiento=10)
    primera = _liquidar(cliente, db, edificio, admin, mes=10)
    segunda = _liquidar(cliente, db, edificio, admin, mes=11)
    _vencer(db, primera["id"], dias_atras=70)
    _vencer(db, segunda["id"], dias_atras=40)

    deudor = _deudores(cliente, edificio, admin).json()["deudores"][0]

    assert deudor["meses_de_atraso"] == 2
    assert deudor["severidad"] == "crit"
    assert deudor["periodos_impagos"] == ["10/2026", "11/2026"]
    assert deudor["periodo_mas_viejo"] == "10/2026"


def test_un_pago_confirmado_saca_a_la_unidad_del_listado(cliente, como, db):
    """**La unica forma de saldar una deuda es conciliar el pago.** No hay
    endpoint para "marcar como pago" y no va a haberlo."""
    admin = como("admin_general")
    edificio = _edificio_listo(db)
    unidad = _unidades(db, edificio)[0]
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Dueno Uno")
    unidad.propietario_id = propietario.id
    db.commit()
    expensa = _liquidar(cliente, db, edificio, admin)
    _vencer(db, expensa["id"])

    pago = cliente.post(
        "/api/mis-pagos",
        json={
            "expensa_id": expensa["id"],
            "monto": "50000.00",
            "fecha": "2026-12-05",
            "medio_pago": "transferencia",
        },
        headers=_login(cliente, propietario),
    ).json()

    con_pendiente = _deudores(cliente, edificio, admin).json()
    cliente.patch(
        f"/api/edificios/{edificio.id}/pagos/{pago['id']}",
        json={"estado": "confirmado"},
        headers=admin,
    )
    despues = _deudores(cliente, edificio, admin).json()

    # El pago pendiente no la saca del listado: solo el confirmado.
    assert con_pendiente["cantidad_deudores"] == 2
    assert despues["cantidad_deudores"] == 1
    assert despues["deudores"][0]["identificador"] == "1B"


def test_el_filtro_de_solo_vencidos_deja_afuera_las_que_estan_en_termino(
    cliente, como, db
):
    """La pantalla de cobranza quiere las atrasadas; el resumen del edificio,
    todas."""
    admin = como("admin_general")
    edificio = _edificio_listo(db, dias_vencimiento=10)
    _liquidar(cliente, db, edificio, admin)

    todas = _deudores(cliente, edificio, admin).json()
    atrasadas = _deudores(cliente, edificio, admin, solo_vencidos="true").json()

    assert todas["cantidad_deudores"] == 2
    assert atrasadas["cantidad_deudores"] == 0


def test_el_listado_trae_los_totales_de_la_cartera(cliente, como, db):
    """"17 unidades deben $2.400.000, de las cuales $1.900.000 estan vencidos"
    es la foto que la administracion necesita."""
    admin = como("admin_general")
    edificio = _edificio_listo(db, dias_vencimiento=10)
    expensa = _liquidar(cliente, db, edificio, admin)
    _vencer(db, expensa["id"])

    cuerpo = _deudores(cliente, edificio, admin).json()

    assert cuerpo["total"] == "100000.00"
    assert cuerpo["total_vencido"] == "100000.00"


def test_el_listado_dice_a_quien_hay_que_llamar(cliente, como, db):
    """Sin esto, la pantalla de cobranza obliga a abrir la ficha de la unidad
    para cada deudor."""
    admin = como("admin_general")
    edificio = _edificio_listo(db)
    unidad = _unidades(db, edificio)[0]
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Dueno Dos")
    inquilino = _usuario(db, autorizacion.INQUILINO, "Inquilino Dos")
    unidad.propietario_id = propietario.id
    unidad.inquilino_id = inquilino.id
    db.commit()
    _liquidar(cliente, db, edificio, admin)

    fila = [
        d
        for d in _deudores(cliente, edificio, admin).json()["deudores"]
        if d["identificador"] == "1A"
    ][0]

    assert fila["propietario"] == "Dueno Dos"
    assert fila["inquilino"] == "Inquilino Dos"
    assert fila["piso_numero"] == 1


def test_el_orden_pone_primero_a_la_mas_atrasada(cliente, como, db):
    admin = como("admin_general")
    edificio = _edificio_listo(db, dias_vencimiento=10)
    unidades = _unidades(db, edificio)
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Dueno Tres")
    unidades[0].propietario_id = propietario.id
    db.commit()

    octubre = _liquidar(cliente, db, edificio, admin, mes=10)
    noviembre = _liquidar(cliente, db, edificio, admin, mes=11)
    _vencer(db, octubre["id"], dias_atras=70)
    _vencer(db, noviembre["id"], dias_atras=40)

    # La unidad 1A paga octubre, asi que le queda un solo mes de atraso.
    pago = cliente.post(
        "/api/mis-pagos",
        json={
            "expensa_id": octubre["id"],
            "monto": "50000.00",
            "fecha": "2026-11-05",
            "medio_pago": "transferencia",
        },
        headers=_login(cliente, propietario),
    ).json()
    cliente.patch(
        f"/api/edificios/{edificio.id}/pagos/{pago['id']}",
        json={"estado": "confirmado"},
        headers=admin,
    )

    orden = [d["identificador"] for d in _deudores(cliente, edificio, admin).json()["deudores"]]

    assert orden == ["1B", "1A"]


# ===========================================================================
# PERMISOS
# ===========================================================================


def test_un_residente_no_ve_la_lista_de_deudores(cliente, como, db):
    """Quien debe en el edificio es informacion economica de los vecinos."""
    edificio = _edificio_listo(db)

    respuesta = _deudores(cliente, edificio, como("propietario"))

    assert respuesta.status_code == 403


def test_un_encargado_no_ve_la_lista_de_deudores(cliente, como, db):
    edificio = _edificio_listo(db)

    respuesta = _deudores(cliente, edificio, como("encargado"))

    assert respuesta.status_code == 403


def test_un_admin_de_consorcio_no_ve_los_deudores_de_un_edificio_ajeno(
    cliente, como, db
):
    edificio = _edificio_listo(db)

    respuesta = _deudores(cliente, edificio, como(autorizacion.ADMIN_CONSORCIO))

    assert respuesta.status_code == 404


def test_sin_sesion_no_se_ven_los_deudores(cliente, db):
    edificio = _edificio_listo(db)

    assert cliente.get(f"/api/edificios/{edificio.id}/deudores").status_code == 401


# ===========================================================================
# LA COSTURA DE `F2-T05`: EL RECARGO Y EL SALDO A FAVOR, DE VERDAD
# ===========================================================================


def test_el_recargo_se_le_cobra_a_la_unidad_atrasada_en_la_liquidacion_siguiente(
    cliente, como, db
):
    """**El test mas importante de la tarea.** Es la costura que `F2-T05` dejo
    marcada: con el modelo `Pago` existiendo, el recargo se calcula de verdad.

    El edificio cobra 10% de recargo. La unidad 1B deja vencer noviembre; 1A
    paga. Al generar diciembre, **1B recibe recargo y 1A no**.
    """
    admin = como("admin_general")
    edificio = _edificio_listo(db, dias_vencimiento=10, recargo="10.00")
    unidades = _unidades(db, edificio)
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Dueno Cuatro")
    unidades[0].propietario_id = propietario.id
    db.commit()

    noviembre = _liquidar(cliente, db, edificio, admin, mes=11)
    pago = cliente.post(
        "/api/mis-pagos",
        json={
            "expensa_id": noviembre["id"],
            "monto": "50000.00",
            "fecha": "2026-11-20",
            "medio_pago": "transferencia",
        },
        headers=_login(cliente, propietario),
    ).json()
    cliente.patch(
        f"/api/edificios/{edificio.id}/pagos/{pago['id']}",
        json={"estado": "confirmado"},
        headers=admin,
    )
    _vencer(db, noviembre["id"])

    diciembre = _liquidar(cliente, db, edificio, admin, mes=12, publicar=False)

    por_unidad = {u["identificador"]: u for u in diciembre["unidades"]}
    assert por_unidad["1A"]["recargo_mora"] == "0.00"
    assert por_unidad["1B"]["recargo_mora"] == "5000.00"  # 10% de 50.000


def test_el_recargo_no_entra_en_el_total_de_la_expensa(cliente, como, db):
    """El total son los gastos del periodo y nada mas. Si el recargo entrara,
    lo pagarian todos los vecinos — incluidos los que pagaron en fecha."""
    admin = como("admin_general")
    edificio = _edificio_listo(db, dias_vencimiento=10, recargo="10.00")
    noviembre = _liquidar(cliente, db, edificio, admin, mes=11)
    _vencer(db, noviembre["id"])

    diciembre = _liquidar(cliente, db, edificio, admin, mes=12, publicar=False)

    prorrateado = sum(
        (Decimal(u["monto_expensa"]) for u in diciembre["unidades"]), Decimal("0.00")
    )
    assert prorrateado == Decimal(diciembre["total"]) == Decimal("100000.00")


def test_sin_recargo_configurado_nadie_recibe_recargo(cliente, como, db):
    """El valor por defecto de todo edificio que no configuro nada: el sistema
    se comporta como si la mora no existiera."""
    admin = como("admin_general")
    edificio = _edificio_listo(db, recargo="0.00")
    noviembre = _liquidar(cliente, db, edificio, admin, mes=11)
    _vencer(db, noviembre["id"])

    diciembre = _liquidar(cliente, db, edificio, admin, mes=12, publicar=False)

    assert all(u["recargo_mora"] == "0.00" for u in diciembre["unidades"])


def test_no_hay_recargo_sobre_el_recargo(cliente, como, db):
    """**La regla que evita que una deuda chica se multiplique sola.** La
    unidad deja vencer noviembre y diciembre; al generar enero, el recargo se
    calcula sobre el **capital** de los dos meses (100.000) y no sobre el saldo,
    que ya incluye el recargo que diciembre le cargo.
    """
    admin = como("admin_general")
    edificio = _edificio_listo(db, unidades=1, dias_vencimiento=10, recargo="10.00")

    noviembre = _liquidar(cliente, db, edificio, admin, mes=11)
    _vencer(db, noviembre["id"], dias_atras=70)

    diciembre = _liquidar(cliente, db, edificio, admin, mes=12, publicar=False)
    cliente.post(
        f"/api/edificios/{edificio.id}/expensas/{diciembre['id']}/publicar",
        headers=admin,
    )
    _vencer(db, diciembre["id"], dias_atras=40)

    # Diciembre le cargo 10% de los 100.000 de noviembre = 10.000.
    assert diciembre["unidades"][0]["recargo_mora"] == "10000.00"

    enero = _liquidar(cliente, db, edificio, admin, mes=1, publicar=False)

    # Capital vencido: 100.000 de noviembre + 100.000 de diciembre = 200.000.
    # El recargo de 10.000 que arrastra diciembre NO entra en la base.
    assert enero["unidades"][0]["recargo_mora"] == "20000.00"


def test_el_saldo_a_favor_se_descuenta_en_la_liquidacion_siguiente(cliente, como, db):
    """La otra mitad de la costura. El excedente no se devuelve ni se pierde:
    se aplica solo."""
    admin = como("admin_general")
    edificio = _edificio_listo(db, unidades=1)
    unidad = _unidades(db, edificio)[0]
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Dueno Cinco")
    unidad.propietario_id = propietario.id
    db.commit()

    noviembre = _liquidar(cliente, db, edificio, admin, mes=11)
    pago = cliente.post(
        "/api/mis-pagos",
        json={
            "expensa_id": noviembre["id"],
            "monto": "130000.00",  # 30.000 de mas
            "fecha": "2026-11-20",
            "medio_pago": "transferencia",
        },
        headers=_login(cliente, propietario),
    ).json()
    cliente.patch(
        f"/api/edificios/{edificio.id}/pagos/{pago['id']}",
        json={"estado": "confirmado"},
        headers=admin,
    )

    diciembre = _liquidar(cliente, db, edificio, admin, mes=12, publicar=False)

    fila = diciembre["unidades"][0]
    assert fila["monto_expensa"] == "100000.00"
    assert fila["saldo_a_favor_aplicado"] == "30000.00"
    assert fila["total_a_pagar"] == "70000.00"


def test_un_pago_pendiente_no_evita_el_recargo(cliente, como, db):
    """Coherente con la regla fundamental: un pago sin conciliar no reduce la
    deuda, asi que tampoco la saca del atraso."""
    admin = como("admin_general")
    edificio = _edificio_listo(db, unidades=1, dias_vencimiento=10, recargo="10.00")
    unidad = _unidades(db, edificio)[0]
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Dueno Seis")
    unidad.propietario_id = propietario.id
    db.commit()

    noviembre = _liquidar(cliente, db, edificio, admin, mes=11)
    cliente.post(
        "/api/mis-pagos",
        json={
            "expensa_id": noviembre["id"],
            "monto": "100000.00",
            "fecha": "2026-11-20",
            "medio_pago": "transferencia",
        },
        headers=_login(cliente, propietario),
    )
    _vencer(db, noviembre["id"])

    diciembre = _liquidar(cliente, db, edificio, admin, mes=12, publicar=False)

    assert diciembre["unidades"][0]["recargo_mora"] == "10000.00"

"""Pruebas del modelo `Pago` y de la carga por el residente (`F2-T08`).

Lo que se prueba:

  1. **Que el pago nazca pendiente y no mueva el saldo.** Es la regla
     fundamental, verificada de punta a punta y no solo en la logica.
  2. **Que el residente no tenga que elegir edificio ni piso**, y que cuando
     tiene dos unidades el servidor le diga cuales son.
  3. **Que no se pueda pagar lo que no es propio ni lo que no esta
     publicado.**
  4. **El estado de cuenta**: pago parcial, pago de mas, y los tres totales
     por separado.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

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


def _edificio_listo(db, cantidad_unidades: int = 2, nombre="Mitre 500") -> Edificio:
    edificio = Edificio(
        nombre=nombre,
        direccion=f"{nombre} 1",
        cp="C1000",
        cbu="0170099220000067797888",
        alias_cbu="consorcio.mitre.500",
    )
    db.add(edificio)
    db.commit()

    piso = Piso(edificio_id=edificio.id, numero="1", orden=1)
    db.add(piso)
    db.commit()

    for numero, coeficiente in enumerate(
        finanzas.calcular_partes_iguales(cantidad_unidades), start=1
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


def _unidades_de(db, edificio) -> list[Departamento]:
    return list(
        db.scalars(
            select(Departamento)
            .join(Piso, Piso.id == Departamento.piso_id)
            .where(Piso.edificio_id == edificio.id)
            .order_by(Departamento.identificador)
        ).all()
    )


def _liquidar(cliente, db, edificio, admin, monto="100000.00", mes=11, publicar=True):
    """Deja una expensa publicada del periodo, con un gasto que la justifica."""
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


def _escenario(cliente, como, db, cantidad_unidades=2):
    """Un edificio liquidado y publicado, con un propietario en la unidad 1A."""
    admin = como("admin_general")
    edificio = _edificio_listo(db, cantidad_unidades)
    unidades = _unidades_de(db, edificio)
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Dueno Uno")
    unidades[0].propietario_id = propietario.id
    db.commit()
    expensa = _liquidar(cliente, db, edificio, admin)
    return edificio, unidades, propietario, expensa, admin


def _cuerpo(expensa, **campos) -> dict:
    datos = {
        "expensa_id": expensa["id"],
        "monto": "50000.00",
        "fecha": "2026-12-05",
        "medio_pago": "transferencia",
    }
    datos.update(campos)
    return datos


# ===========================================================================
# EL MODELO
# ===========================================================================


def test_un_pago_nace_pendiente(cliente, como, db):
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    pago = Pago(
        departamento_id=unidades[0].id,
        expensa_id=expensa["id"],
        monto=Decimal("1000.00"),
        fecha=date(2026, 12, 5),
        medio_pago="transferencia",
        cargado_por_id=propietario.id,
    )
    db.add(pago)
    db.commit()

    assert pago.estado == "pendiente"
    assert not pago.reduce_la_deuda
    assert not pago.esta_conciliado


@pytest.mark.parametrize("monto", ["0.00", "-500.00"])
def test_un_pago_que_no_es_positivo_lo_rechaza_la_base(cliente, como, db, monto):
    """Un pago negativo seria una devolucion, que es otra operacion con otra
    autorizacion."""
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    db.add(
        Pago(
            departamento_id=unidades[0].id,
            expensa_id=expensa["id"],
            monto=Decimal(monto),
            fecha=date(2026, 12, 5),
            medio_pago="transferencia",
            cargado_por_id=propietario.id,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_un_medio_de_pago_fuera_del_catalogo_lo_rechaza_la_base(cliente, como, db):
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    db.add(
        Pago(
            departamento_id=unidades[0].id,
            expensa_id=expensa["id"],
            monto=Decimal("100.00"),
            fecha=date(2026, 12, 5),
            medio_pago="mercadopago",
            cargado_por_id=propietario.id,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_se_guarda_quien_cargo_el_pago(cliente, como, db):
    """Sin esta columna la regla de `F2-T07` no se puede aplicar: quien carga un
    pago no lo concilia, y eso se decide por persona y no por rol."""
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    respuesta = cliente.post(
        "/api/mis-pagos", json=_cuerpo(expensa), headers=_login(cliente, propietario)
    )

    pago = db.scalars(select(Pago)).first()
    assert respuesta.status_code == 201, respuesta.text
    assert pago.cargado_por_id == propietario.id
    assert pago.conciliado_por_id is None
    assert pago.conciliado_en is None


def test_la_fecha_del_pago_y_la_de_carga_son_distintas(cliente, como, db):
    """Se paga el 10 y se sube el comprobante el 12: la primera es la que
    decide si el pago entro en termino."""
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    cliente.post(
        "/api/mis-pagos",
        json=_cuerpo(expensa, fecha="2026-12-10"),
        headers=_login(cliente, propietario),
    )

    pago = db.scalars(select(Pago)).first()
    assert pago.fecha == date(2026, 12, 10)
    assert pago.creado_en is not None


# ===========================================================================
# CARGAR UN PAGO
# ===========================================================================


def test_el_residente_carga_su_pago_sin_elegir_edificio_ni_piso(cliente, como, db):
    """Lo que pide la tarea: el backend resuelve sus unidades solo."""
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    respuesta = cliente.post(
        "/api/mis-pagos", json=_cuerpo(expensa), headers=_login(cliente, propietario)
    )

    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["identificador"] == "1A"
    assert cuerpo["periodo"] == "11/2026"


def test_el_pago_cargado_queda_pendiente_y_lo_dice_en_palabras(cliente, como, db):
    """Sin ese aviso, el residente ve su saldo intacto y vuelve a pagar. El
    texto lo arma el servidor: tres pantallas armandolo son tres textos que
    algun dia dicen cosas distintas."""
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    cuerpo = cliente.post(
        "/api/mis-pagos", json=_cuerpo(expensa), headers=_login(cliente, propietario)
    ).json()

    assert cuerpo["estado"] == "pendiente"
    assert "confirme" in cuerpo["mensaje"]


def test_el_cliente_no_puede_mandar_el_estado(cliente, como, db):
    """Si pudiera, un pago llegaria confirmado desde el navegador y la
    conciliacion dejaria de existir como control."""
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    respuesta = cliente.post(
        "/api/mis-pagos",
        json=_cuerpo(expensa, estado="confirmado"),
        headers=_login(cliente, propietario),
    )

    assert respuesta.status_code == 422


def test_el_cliente_no_puede_decir_quien_cargo_el_pago(cliente, como, db):
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    respuesta = cliente.post(
        "/api/mis-pagos",
        json=_cuerpo(expensa, cargado_por_id=1),
        headers=_login(cliente, propietario),
    )

    assert respuesta.status_code == 422


def test_con_dos_unidades_el_servidor_pide_cual_y_dice_cuales_son(cliente, como, db):
    """"Elegi una unidad" sin la lista obliga a adivinar."""
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)
    unidades[1].propietario_id = propietario.id
    db.commit()

    respuesta = cliente.post(
        "/api/mis-pagos", json=_cuerpo(expensa), headers=_login(cliente, propietario)
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "ELEGI_UNA_UNIDAD"
    assert "1A" in respuesta.json()["mensaje"]
    assert "1B" in respuesta.json()["mensaje"]


def test_con_dos_unidades_se_puede_elegir(cliente, como, db):
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)
    unidades[1].propietario_id = propietario.id
    db.commit()

    respuesta = cliente.post(
        "/api/mis-pagos",
        json=_cuerpo(expensa, departamento_id=unidades[1].id),
        headers=_login(cliente, propietario),
    )

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["identificador"] == "1B"


def test_no_se_puede_pagar_por_una_unidad_ajena(cliente, como, db):
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    respuesta = cliente.post(
        "/api/mis-pagos",
        json=_cuerpo(expensa, departamento_id=unidades[1].id),
        headers=_login(cliente, propietario),
    )

    assert respuesta.status_code == 404


def test_no_se_puede_pagar_una_expensa_en_borrador(cliente, como, db):
    """Un borrador no se le cobro a nadie todavia."""
    admin = como("admin_general")
    edificio = _edificio_listo(db)
    unidades = _unidades_de(db, edificio)
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Dueno Dos")
    unidades[0].propietario_id = propietario.id
    db.commit()
    expensa = _liquidar(cliente, db, edificio, admin, publicar=False)

    respuesta = cliente.post(
        "/api/mis-pagos", json=_cuerpo(expensa), headers=_login(cliente, propietario)
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "EXPENSA_EN_BORRADOR"


def test_no_se_puede_pagar_la_expensa_de_un_edificio_ajeno(cliente, como, db):
    """Contesta lo mismo que una liquidacion inexistente: un 404 que no
    confirma que esa liquidacion existe."""
    admin = como("admin_general")
    mio = _edificio_listo(db, nombre="Mitre 500")
    ajeno = _edificio_listo(db, nombre="Otro 900")
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Dueno Tres")
    _unidades_de(db, mio)[0].propietario_id = propietario.id
    db.commit()
    ajena = _liquidar(cliente, db, ajeno, admin)

    respuesta = cliente.post(
        "/api/mis-pagos", json=_cuerpo(ajena), headers=_login(cliente, propietario)
    )

    assert respuesta.status_code == 404


def test_quien_no_tiene_unidades_no_carga_pagos(cliente, como, db):
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)
    otro = _usuario(db, autorizacion.PROPIETARIO, "Sin Unidad")

    respuesta = cliente.post(
        "/api/mis-pagos", json=_cuerpo(expensa), headers=_login(cliente, otro)
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "SIN_UNIDADES"


def test_sin_sesion_no_se_carga_un_pago(cliente, como, db):
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    respuesta = cliente.post("/api/mis-pagos", json=_cuerpo(expensa))

    assert respuesta.status_code == 401


def test_un_pago_parcial_se_acepta(cliente, como, db):
    """Son habituales en la realidad del rubro."""
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    respuesta = cliente.post(
        "/api/mis-pagos",
        json=_cuerpo(expensa, monto="1000.00"),
        headers=_login(cliente, propietario),
    )

    assert respuesta.status_code == 201, respuesta.text


def test_pagar_de_mas_se_acepta(cliente, como, db):
    """El excedente queda como saldo a favor y se descuenta de la liquidacion
    siguiente. Rechazarlo obligaria a devolver plata."""
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    respuesta = cliente.post(
        "/api/mis-pagos",
        json=_cuerpo(expensa, monto="999999.00"),
        headers=_login(cliente, propietario),
    )

    assert respuesta.status_code == 201, respuesta.text


def test_se_pueden_cargar_dos_pagos_de_la_misma_expensa(cliente, como, db):
    """No hay UNIQUE de (expensa, unidad): los pagos parciales lo necesitan, y
    un pago rechazado deja su fila."""
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)
    headers = _login(cliente, propietario)

    primero = cliente.post("/api/mis-pagos", json=_cuerpo(expensa, monto="1.00"), headers=headers)
    segundo = cliente.post("/api/mis-pagos", json=_cuerpo(expensa, monto="2.00"), headers=headers)

    assert primero.status_code == 201
    assert segundo.status_code == 201


def test_un_comprobante_que_no_es_un_enlace_se_rechaza(cliente, como, db):
    """Ataja el caso real: pegar el nombre del archivo en vez del enlace."""
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    respuesta = cliente.post(
        "/api/mis-pagos",
        json=_cuerpo(expensa, comprobante_url="comprobante.pdf"),
        headers=_login(cliente, propietario),
    )

    assert respuesta.status_code == 422


def test_el_comprobante_es_opcional(cliente, como, db):
    """Un pago en efectivo en la administracion no tiene comprobante digital, y
    exigirlo haria que se cargue cualquier cosa en el campo."""
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    respuesta = cliente.post(
        "/api/mis-pagos",
        json=_cuerpo(expensa, medio_pago="efectivo"),
        headers=_login(cliente, propietario),
    )

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["comprobante_url"] is None


def test_un_monto_con_tres_decimales_se_rechaza(cliente, como, db):
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    respuesta = cliente.post(
        "/api/mis-pagos",
        json=_cuerpo(expensa, monto="1000.555"),
        headers=_login(cliente, propietario),
    )

    assert respuesta.status_code == 422


# ===========================================================================
# EL ESTADO DE CUENTA
# ===========================================================================


def test_mis_unidades_devuelve_la_deuda_del_periodo(cliente, como, db):
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    cuerpo = cliente.get("/api/mis-unidades", headers=_login(cliente, propietario)).json()

    assert len(cuerpo) == 1
    assert cuerpo[0]["identificador"] == "1A"
    assert cuerpo[0]["deuda"] == "50000.00"
    assert cuerpo[0]["esta_al_dia"] is False


def test_un_pago_pendiente_no_baja_la_deuda_pero_se_informa(cliente, como, db):
    """**La regla fundamental, verificada de punta a punta.** Si el pendiente
    bajara el saldo, cualquiera podria subir un comprobante falso y aparecer
    sin deuda."""
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)
    headers = _login(cliente, propietario)
    cliente.post("/api/mis-pagos", json=_cuerpo(expensa), headers=headers)

    cuenta = cliente.get("/api/mis-unidades", headers=headers).json()[0]

    assert cuenta["deuda"] == "50000.00"
    assert cuenta["pendiente_de_confirmar"] == "50000.00"


def test_un_pago_confirmado_si_baja_la_deuda(cliente, como, db):
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)
    headers = _login(cliente, propietario)
    cliente.post("/api/mis-pagos", json=_cuerpo(expensa), headers=headers)

    pago = db.scalars(select(Pago)).first()
    pago.estado = "confirmado"
    db.commit()

    cuenta = cliente.get("/api/mis-unidades", headers=headers).json()[0]

    assert cuenta["deuda"] == "0.00"
    assert cuenta["pendiente_de_confirmar"] == "0.00"
    assert cuenta["esta_al_dia"] is True


def test_un_pago_parcial_confirmado_deja_el_saldo_restante(cliente, como, db):
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)
    headers = _login(cliente, propietario)
    cliente.post("/api/mis-pagos", json=_cuerpo(expensa, monto="20000.00"), headers=headers)
    db.scalars(select(Pago)).first().estado = "confirmado"
    db.commit()

    cuenta = cliente.get("/api/mis-unidades", headers=headers).json()[0]

    assert cuenta["deuda"] == "30000.00"
    assert cuenta["periodos"][0]["esta_pago"] is False


def test_pagar_de_mas_deja_saldo_a_favor_y_no_deuda_negativa(cliente, como, db):
    """**El saldo a favor no es una tabla: es un saldo negativo.** Y la deuda
    no se netea con el, porque se puede deber marzo y haber adelantado mayo."""
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)
    headers = _login(cliente, propietario)
    cliente.post("/api/mis-pagos", json=_cuerpo(expensa, monto="80000.00"), headers=headers)
    db.scalars(select(Pago)).first().estado = "confirmado"
    db.commit()

    cuenta = cliente.get("/api/mis-unidades", headers=headers).json()[0]

    assert cuenta["deuda"] == "0.00"
    assert cuenta["saldo_a_favor"] == "30000.00"
    assert cuenta["esta_al_dia"] is True


def test_los_borradores_no_entran_en_la_cuenta(cliente, como, db):
    """Un borrador no se le puede cobrar a nadie."""
    admin = como("admin_general")
    edificio = _edificio_listo(db)
    unidades = _unidades_de(db, edificio)
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Dueno Cuatro")
    unidades[0].propietario_id = propietario.id
    db.commit()
    _liquidar(cliente, db, edificio, admin, publicar=False)

    cuenta = cliente.get(
        "/api/mis-unidades", headers=_login(cliente, propietario)
    ).json()[0]

    assert cuenta["periodos"] == []
    assert cuenta["deuda"] == "0.00"


def test_la_cuenta_trae_el_cbu_y_el_alias(cliente, como, db):
    """Son lo que la persona vino a buscar."""
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    cuenta = cliente.get(
        "/api/mis-unidades", headers=_login(cliente, propietario)
    ).json()[0]

    assert cuenta["cbu"] == "0170099220000067797888"
    assert cuenta["alias_cbu"] == "consorcio.mitre.500"


def test_la_cuenta_dice_si_soy_propietario_o_inquilino(cliente, como, db):
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)
    inquilino = _usuario(db, autorizacion.INQUILINO, "Inquilino Uno")
    unidades[1].inquilino_id = inquilino.id
    db.commit()

    delpropietario = cliente.get(
        "/api/mis-unidades", headers=_login(cliente, propietario)
    ).json()[0]
    delinquilino = cliente.get(
        "/api/mis-unidades", headers=_login(cliente, inquilino)
    ).json()[0]

    assert delpropietario["vinculo"] == "propietario"
    assert delinquilino["vinculo"] == "inquilino"


def test_quien_no_tiene_unidades_recibe_lista_vacia_y_no_un_error(cliente, como, db):
    """Un administrador que no vive en ningun edificio del sistema es
    completamente normal."""
    respuesta = cliente.get("/api/mis-unidades", headers=como("admin_general"))

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_un_propietario_con_dos_unidades_ve_las_dos(cliente, como, db):
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)
    unidades[1].propietario_id = propietario.id
    db.commit()

    cuerpo = cliente.get("/api/mis-unidades", headers=_login(cliente, propietario)).json()

    assert {c["identificador"] for c in cuerpo} == {"1A", "1B"}


def test_los_periodos_salen_del_mas_nuevo_al_mas_viejo(cliente, como, db):
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)
    _liquidar(cliente, db, edificio, admin, mes=12)

    cuenta = cliente.get(
        "/api/mis-unidades", headers=_login(cliente, propietario)
    ).json()[0]

    assert [p["periodo"] for p in cuenta["periodos"]] == ["12/2026", "11/2026"]


def test_sin_sesion_no_se_ven_mis_unidades(cliente):
    assert cliente.get("/api/mis-unidades").status_code == 401


# ===========================================================================
# EL CATALOGO DE MEDIOS
# ===========================================================================


def test_el_catalogo_de_medios_pone_primero_la_transferencia(cliente, como):
    """Es la que se usa en el 90% de los casos."""
    cuerpo = cliente.get("/api/pagos/medios", headers=como("propietario")).json()

    assert cuerpo[0]["nombre"] == "transferencia"
    assert cuerpo[0]["etiqueta"] == "Transferencia bancaria"
    assert all(m["etiqueta"] for m in cuerpo)


def test_el_catalogo_de_medios_pide_sesion(cliente):
    assert cliente.get("/api/pagos/medios").status_code == 401


# ===========================================================================
# LA DECISION DE COMO SE COBRA (`F2-T10`)
# ===========================================================================
#
# `F2-T10` no es codigo nuevo: es una decision que se cumple implementando, y
# estos dos tests la vuelven **verificable** en vez de dejarla solo escrita.
#
# Lo decidido: se muestran el CBU y el alias como texto, cada uno con su boton
# de copiar, y **no hay QR de ningun tipo**. El QR interoperable de Argentina
# ("Transferencias 3.0", regulado por el BCRA) solo lo pueden emitir entidades
# financieras y proveedores de pago registrados: una aplicacion de terceros no
# puede generar un QR de pago real y valido. Y un "QR de conveniencia" que al
# escanearlo solo muestra el CBU es un paso de mas — copiar un texto es un
# toque.
#
# Consecuencia legal que conviene tener escrita: mostrar el CBU del consorcio
# no convierte a SMART Building en un procesador de pagos. La plata nunca pasa
# por la plataforma.


def test_los_datos_para_pagar_llegan_como_texto_copiable(cliente, como, db):
    """El CBU y el alias, tal cual se guardaron, para pegarlos en la app del
    banco. Sin transformarlos ni enmascararlos: son datos de cobro de un
    consorcio, no de una persona."""
    edificio, unidades, propietario, expensa, admin = _escenario(cliente, como, db)

    cuenta = cliente.get(
        "/api/mis-unidades", headers=_login(cliente, propietario)
    ).json()[0]

    assert cuenta["cbu"] == "0170099220000067797888"
    assert cuenta["alias_cbu"] == "consorcio.mitre.500"


def test_ningun_endpoint_expone_un_qr_de_pago():
    """**La decision, hecha verificable.** Si alguna vez alguien agrega un
    campo o un endpoint de QR, este test lo encuentra — y entonces lo que hay
    que revisar primero es `investigaciones/Pagos_y_Conciliacion.md`, no el
    codigo.
    """
    from app.main import app

    esquema = str(app.openapi()).lower()

    assert "qr" not in esquema.replace("qrstuvwxyz", "")

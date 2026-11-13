"""Pruebas del CRUD de fondos, caja, presupuestos y facturas (`F2-T15`).

Son cuatro conjuntos de endpoints y lo que se prueba de cada uno es la regla
que lo distingue, no que el CRUD funcione:

  - **Fondos:** que el saldo salga calculado en cada respuesta, que un fondo
    desactivado no admita movimientos nuevos, y que no haya forma de borrar un
    fondo con historial.
  - **Caja:** que todo se mida contra el monto fijo, que una reposicion sea un
    movimiento de ingreso, y que el responsable tenga que ser alguien del
    edificio.
  - **Presupuestos:** que una decision no se cambie despues, y que solo un
    aprobado se pueda vincular a un gasto.
  - **Facturas:** que sean **opcionales** en todo sentido, y que cuelguen del
    gasto.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core import security
from app.models.edificio import Edificio
from app.models.finanzas import Caja, Fondo, Gasto, Presupuesto
from app.models.usuario import Usuario
from app.services import autorizacion


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


def _edificio(db, nombre="Mitre 500") -> Edificio:
    edificio = Edificio(nombre=nombre, direccion=f"{nombre} 1", cp="C1000")
    db.add(edificio)
    db.commit()
    return edificio


def _gasto(db, edificio, monto="180000.00") -> Gasto:
    gasto = Gasto(
        edificio_id=edificio.id,
        rubro="mantenimiento",
        monto=Decimal(monto),
        fecha=date(2026, 11, 20),
    )
    db.add(gasto)
    db.commit()
    return gasto


def _crear_fondo(cliente, edificio, headers, nombre="Fondo de reserva"):
    return cliente.post(
        f"/api/edificios/{edificio.id}/fondos",
        json={"nombre": nombre},
        headers=headers,
    )


def _movimiento(cliente, edificio, fondo_id, headers, tipo="ingreso", monto="100000.00"):
    return cliente.post(
        f"/api/edificios/{edificio.id}/fondos/{fondo_id}/movimientos",
        json={"tipo": tipo, "monto": monto, "fecha": "2026-11-05"},
        headers=headers,
    )


# ===========================================================================
# FONDOS
# ===========================================================================


def test_un_fondo_nace_vacio_con_saldo_cero(cliente, como, db):
    """La plata entra cuando se registra el ingreso, no al crear la bolsa. Un
    fondo que naciera con saldo inicial seria plata sin movimiento que la
    respalde."""
    edificio = _edificio(db)

    respuesta = _crear_fondo(cliente, edificio, como("admin_general"))

    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["saldo"] == "0.00"
    assert cuerpo["cantidad_movimientos"] == 0
    assert cuerpo["activo"] is True


def test_no_puede_haber_dos_fondos_con_el_mismo_nombre(cliente, como, db):
    edificio = _edificio(db)
    headers = como("admin_general")
    _crear_fondo(cliente, edificio, headers, "Fondo de obras")

    respuesta = _crear_fondo(cliente, edificio, headers, "Fondo de obras")

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "FONDO_REPETIDO"


def test_el_movimiento_devuelve_el_fondo_con_el_saldo_nuevo(cliente, como, db):
    """Quien carga un movimiento quiere ver el saldo nuevo, y pedirlo aparte
    seria el doble de pedidos para el dato que importa."""
    edificio = _edificio(db)
    headers = como("admin_general")
    fondo = _crear_fondo(cliente, edificio, headers).json()

    _movimiento(cliente, edificio, fondo["id"], headers, "ingreso", "500000.00")
    cuerpo = _movimiento(
        cliente, edificio, fondo["id"], headers, "egreso", "120000.50"
    ).json()

    assert cuerpo["ingresos"] == "500000.00"
    assert cuerpo["egresos"] == "120000.50"
    assert cuerpo["saldo"] == "379999.50"
    assert cuerpo["cantidad_movimientos"] == 2


def test_un_egreso_que_deja_el_fondo_en_rojo_se_acepta_y_se_informa(
    cliente, como, db
):
    """Casi siempre significa que falta cargar el ingreso que lo financio, y
    bloquearlo obligaria a inventarlo para registrar un gasto que ya ocurrio."""
    edificio = _edificio(db)
    headers = como("admin_general")
    fondo = _crear_fondo(cliente, edificio, headers).json()

    cuerpo = _movimiento(
        cliente, edificio, fondo["id"], headers, "egreso", "50000.00"
    ).json()

    assert cuerpo["saldo"] == "-50000.00"
    assert cuerpo["esta_en_rojo"] is True


def test_un_tipo_de_movimiento_invalido_se_rechaza(cliente, como, db):
    edificio = _edificio(db)
    headers = como("admin_general")
    fondo = _crear_fondo(cliente, edificio, headers).json()

    respuesta = _movimiento(cliente, edificio, fondo["id"], headers, "deposito")

    assert respuesta.status_code == 422


def test_un_fondo_desactivado_no_admite_movimientos(cliente, como, db):
    edificio = _edificio(db)
    headers = como("admin_general")
    fondo = _crear_fondo(cliente, edificio, headers).json()
    cliente.patch(
        f"/api/edificios/{edificio.id}/fondos/{fondo['id']}",
        json={"activo": False},
        headers=headers,
    )

    respuesta = _movimiento(cliente, edificio, fondo["id"], headers)

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "FONDO_INACTIVO"


def test_el_listado_oculta_los_inactivos_pero_su_plata_sigue_contando(
    cliente, como, db
):
    """No se puede dar por perdido el saldo de un fondo solo porque se dejo de
    usar."""
    edificio = _edificio(db)
    headers = como("admin_general")
    activo = _crear_fondo(cliente, edificio, headers, "Reserva").json()
    viejo = _crear_fondo(cliente, edificio, headers, "Obras 2024").json()
    _movimiento(cliente, edificio, activo["id"], headers, "ingreso", "100.00")
    _movimiento(cliente, edificio, viejo["id"], headers, "ingreso", "900.00")
    cliente.patch(
        f"/api/edificios/{edificio.id}/fondos/{viejo['id']}",
        json={"activo": False},
        headers=headers,
    )

    solo_activos = cliente.get(
        f"/api/edificios/{edificio.id}/fondos", headers=headers
    ).json()
    todos = cliente.get(
        f"/api/edificios/{edificio.id}/fondos?incluir_inactivos=true", headers=headers
    ).json()

    assert solo_activos["cantidad"] == 1
    assert solo_activos["total"] == "100.00"
    assert todos["cantidad"] == 2
    assert todos["total"] == "1000.00"


def test_no_existe_endpoint_para_borrar_un_fondo(cliente, como, db):
    """Tiene historial, y el historial de la plata de un consorcio no se tira.
    Se desactiva."""
    edificio = _edificio(db)
    headers = como("admin_general")
    fondo = _crear_fondo(cliente, edificio, headers).json()

    respuesta = cliente.delete(
        f"/api/edificios/{edificio.id}/fondos/{fondo['id']}", headers=headers
    )

    assert respuesta.status_code == 405


def test_un_movimiento_se_borra_y_el_saldo_vuelve(cliente, como, db):
    """No hay edicion: un movimiento mal cargado se saca y se vuelve a cargar
    bien. Editarlo seria reescribir el historial de la plata."""
    edificio = _edificio(db)
    headers = como("admin_general")
    fondo = _crear_fondo(cliente, edificio, headers).json()
    _movimiento(cliente, edificio, fondo["id"], headers, "ingreso", "100000.00")
    mal = _movimiento(cliente, edificio, fondo["id"], headers, "egreso", "99999.00")
    movimientos = cliente.get(
        f"/api/edificios/{edificio.id}/fondos/{fondo['id']}/movimientos",
        headers=headers,
    ).json()
    id_del_egreso = [m["id"] for m in movimientos if m["tipo"] == "egreso"][0]

    cuerpo = cliente.delete(
        f"/api/edificios/{edificio.id}/fondos/{fondo['id']}/movimientos/{id_del_egreso}",
        headers=headers,
    ).json()

    assert mal.json()["saldo"] == "1.00"
    assert cuerpo["saldo"] == "100000.00"


def test_el_historial_dice_quien_registro_cada_movimiento(cliente, como, db):
    edificio = _edificio(db)
    headers = como("admin_general")
    fondo = _crear_fondo(cliente, edificio, headers).json()
    _movimiento(cliente, edificio, fondo["id"], headers)

    filas = cliente.get(
        f"/api/edificios/{edificio.id}/fondos/{fondo['id']}/movimientos",
        headers=headers,
    ).json()

    assert filas[0]["registrado_por"]
    assert filas[0]["tipo_etiqueta"] == "Ingreso"


def test_un_fondo_de_otro_edificio_no_se_toca(cliente, como, db):
    mio = _edificio(db, "Mitre 500")
    otro = _edificio(db, "Otro 900")
    headers = como("admin_general")
    ajeno = _crear_fondo(cliente, otro, headers).json()

    respuesta = cliente.patch(
        f"/api/edificios/{mio.id}/fondos/{ajeno['id']}",
        json={"nombre": "Robado"},
        headers=headers,
    )

    assert respuesta.status_code == 404


def test_un_residente_no_ve_los_fondos(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/fondos", headers=como("propietario")
    )

    assert respuesta.status_code == 403


def test_sin_sesion_no_se_ven_los_fondos(cliente, db):
    edificio = _edificio(db)

    assert cliente.get(f"/api/edificios/{edificio.id}/fondos").status_code == 401


# ===========================================================================
# CAJA CHICA
# ===========================================================================


def _crear_caja(cliente, edificio, headers, responsable, monto_fijo="50000.00"):
    return cliente.post(
        f"/api/edificios/{edificio.id}/caja",
        json={"monto_fijo": monto_fijo, "responsable_id": responsable.id},
        headers=headers,
    )


def _mov_caja(cliente, edificio, headers, tipo="egreso", monto="5000.00"):
    return cliente.post(
        f"/api/edificios/{edificio.id}/caja/movimientos",
        json={"tipo": tipo, "monto": monto, "fecha": "2026-11-05"},
        headers=headers,
    )


def _edificio_con_encargado(db, nombre="Mitre 500"):
    edificio = _edificio(db, nombre)
    encargado = _usuario(db, autorizacion.ENCARGADO, f"Encargado {nombre}")
    edificio.encargado_id = encargado.id
    db.commit()
    return edificio, encargado


def test_una_caja_nueva_arranca_con_todo_pendiente_de_reposicion(cliente, como, db):
    """**El caso que muestra de que se trata el fondo fijo.** La caja no tiene
    "saldo cero y listo": tiene 50.000 pendientes, porque todavia no se le
    entrego el efectivo al responsable."""
    edificio, encargado = _edificio_con_encargado(db)

    respuesta = _crear_caja(cliente, edificio, como("admin_general"), encargado)

    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["disponible"] == "0.00"
    assert cuerpo["pendiente_de_reposicion"] == "50000.00"
    assert cuerpo["necesita_reposicion"] is True


def test_un_edificio_sin_caja_devuelve_404_con_su_codigo(cliente, como, db):
    """Es un estado normal y no un problema: no todo consorcio maneja
    efectivo."""
    edificio = _edificio(db)

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/caja", headers=como("admin_general")
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "SIN_CAJA"


def test_una_caja_por_edificio(cliente, como, db):
    edificio, encargado = _edificio_con_encargado(db)
    headers = como("admin_general")
    _crear_caja(cliente, edificio, headers, encargado)

    respuesta = _crear_caja(cliente, edificio, headers, encargado)

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "CAJA_YA_EXISTE"


def test_el_responsable_tiene_que_trabajar_en_el_edificio(cliente, como, db):
    """El efectivo del edificio no lo maneja un vecino, y tampoco alguien de
    otro edificio."""
    edificio, _ = _edificio_con_encargado(db)
    ajeno = _usuario(db, autorizacion.ENCARGADO, "Encargado De Otro")

    respuesta = _crear_caja(cliente, edificio, como("admin_general"), ajeno)

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "RESPONSABLE_DE_CAJA_INVALIDO"


def test_un_propietario_no_puede_ser_responsable_de_la_caja(cliente, como, db):
    edificio, _ = _edificio_con_encargado(db)
    vecino = _usuario(db, autorizacion.PROPIETARIO, "Vecino Pepe")

    respuesta = _crear_caja(cliente, edificio, como("admin_general"), vecino)

    assert respuesta.json()["codigo"] == "RESPONSABLE_DE_CAJA_INVALIDO"


def test_el_gasto_de_caja_baja_el_disponible_y_sube_lo_pendiente(cliente, como, db):
    """**Lo pendiente es lo que el responsable gasto y todavia no le
    devolvieron**, que es la cifra de la rendicion."""
    edificio, encargado = _edificio_con_encargado(db)
    headers = como("admin_general")
    _crear_caja(cliente, edificio, headers, encargado)
    _mov_caja(cliente, edificio, headers, "ingreso", "50000.00")

    cuerpo = _mov_caja(cliente, edificio, headers, "egreso", "12000.00").json()

    assert cuerpo["disponible"] == "38000.00"
    assert cuerpo["pendiente_de_reposicion"] == "12000.00"
    assert cuerpo["reposicion_sugerida"] == "12000.00"


def test_la_reposicion_es_un_movimiento_de_ingreso(cliente, como, db):
    """No hay endpoint de "reponer": la reposicion **es** el movimiento que
    trae el disponible de vuelta al monto fijo."""
    edificio, encargado = _edificio_con_encargado(db)
    headers = como("admin_general")
    _crear_caja(cliente, edificio, headers, encargado)
    _mov_caja(cliente, edificio, headers, "ingreso", "50000.00")
    antes = _mov_caja(cliente, edificio, headers, "egreso", "40000.00").json()

    cuerpo = _mov_caja(
        cliente, edificio, headers, "ingreso", antes["reposicion_sugerida"]
    ).json()

    assert cuerpo["disponible"] == "50000.00"
    assert cuerpo["pendiente_de_reposicion"] == "0.00"
    assert cuerpo["necesita_reposicion"] is False


def test_cambiar_el_monto_fijo_no_mueve_plata_pero_cambia_lo_pendiente(
    cliente, como, db
):
    """Cambia el objetivo contra el que se mide el disponible: la diferencia
    aparece como pendiente hasta que se entregue el efectivo."""
    edificio, encargado = _edificio_con_encargado(db)
    headers = como("admin_general")
    _crear_caja(cliente, edificio, headers, encargado)
    _mov_caja(cliente, edificio, headers, "ingreso", "50000.00")

    cuerpo = cliente.patch(
        f"/api/edificios/{edificio.id}/caja",
        json={"monto_fijo": "80000.00", "responsable_id": encargado.id},
        headers=headers,
    ).json()

    assert cuerpo["disponible"] == "50000.00"
    assert cuerpo["pendiente_de_reposicion"] == "30000.00"


def test_la_caja_que_excede_su_monto_fijo_se_informa(cliente, como, db):
    """**Una caja chica que crece sola deja de ser una caja chica.**"""
    edificio, encargado = _edificio_con_encargado(db)
    headers = como("admin_general")
    _crear_caja(cliente, edificio, headers, encargado)

    cuerpo = _mov_caja(cliente, edificio, headers, "ingreso", "80000.00").json()

    assert cuerpo["excede_el_fondo_fijo"] is True


def test_editar_la_caja_sin_cambiar_nada_avisa(cliente, como, db):
    edificio, encargado = _edificio_con_encargado(db)
    headers = como("admin_general")
    _crear_caja(cliente, edificio, headers, encargado)

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/caja",
        json={"monto_fijo": "50000.00", "responsable_id": encargado.id},
        headers=headers,
    )

    assert respuesta.json()["codigo"] == "SIN_CAMBIOS"


def test_un_residente_no_ve_la_caja(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/caja", headers=como("inquilino")
    )

    assert respuesta.status_code == 403


# ===========================================================================
# PRESUPUESTOS
# ===========================================================================


def _crear_presupuesto(cliente, edificio, headers, monto="180000.00"):
    return cliente.post(
        f"/api/edificios/{edificio.id}/presupuestos",
        json={
            "descripcion": "Arreglo de la bomba de agua",
            "monto": monto,
            "fecha": "2026-11-10",
        },
        headers=headers,
    )


def test_un_presupuesto_nace_pendiente(cliente, como, db):
    edificio = _edificio(db)

    respuesta = _crear_presupuesto(cliente, edificio, como("admin_general"))

    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "pendiente"
    assert cuerpo["gasto_id"] is None
    assert set(cuerpo["estados_siguientes"]) == {"aprobado", "rechazado"}


def test_se_pueden_cargar_varios_presupuestos_y_el_listado_cuenta_los_pendientes(
    cliente, como, db
):
    """Es el numero que importa: los que estan esperando una decision."""
    edificio = _edificio(db)
    headers = como("admin_general")
    for monto in ("180000.00", "210000.00", "165000.00"):
        _crear_presupuesto(cliente, edificio, headers, monto)

    cuerpo = cliente.get(
        f"/api/edificios/{edificio.id}/presupuestos", headers=headers
    ).json()

    assert cuerpo["cantidad"] == 3
    assert cuerpo["pendientes"] == 3


def test_aprobar_un_presupuesto_registra_quien_decidio(cliente, como, db):
    edificio = _edificio(db)
    headers = como("admin_general")
    presupuesto = _crear_presupuesto(cliente, edificio, headers).json()

    cuerpo = cliente.patch(
        f"/api/edificios/{edificio.id}/presupuestos/{presupuesto['id']}",
        json={"estado": "aprobado"},
        headers=headers,
    ).json()

    assert cuerpo["estado"] == "aprobado"
    assert cuerpo["decidido_por"]
    assert cuerpo["decidido_en"] is not None
    assert cuerpo["estados_siguientes"] == []


def test_una_decision_no_se_cambia_despues(cliente, como, db):
    """Cual se habia elegido es informacion que un consorcista puede pedir ver,
    y reescribirla la borra."""
    edificio = _edificio(db)
    headers = como("admin_general")
    presupuesto = _crear_presupuesto(cliente, edificio, headers).json()
    cliente.patch(
        f"/api/edificios/{edificio.id}/presupuestos/{presupuesto['id']}",
        json={"estado": "aprobado"},
        headers=headers,
    )

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/presupuestos/{presupuesto['id']}",
        json={"estado": "rechazado"},
        headers=headers,
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "PRESUPUESTO_YA_DECIDIDO"


def test_aprobar_y_vincular_el_gasto_permite_comparar_lo_cotizado_con_lo_pagado(
    cliente, como, db
):
    """**Para esto existe el vinculo.** El monto del gasto viaja al lado del
    presupuestado: pedirlo en otra consulta volveria opcional la
    comparacion."""
    edificio = _edificio(db)
    headers = como("admin_general")
    gasto = _gasto(db, edificio, monto="172000.00")
    presupuesto = _crear_presupuesto(cliente, edificio, headers, "165000.00").json()

    cuerpo = cliente.patch(
        f"/api/edificios/{edificio.id}/presupuestos/{presupuesto['id']}",
        json={"estado": "aprobado", "gasto_id": gasto.id},
        headers=headers,
    ).json()

    assert cuerpo["monto"] == "165000.00"
    assert cuerpo["monto_del_gasto"] == "172000.00"


def test_un_rechazado_no_se_puede_vincular_a_un_gasto(cliente, como, db):
    """Diria "no elegimos esto" y "esto es lo que gastamos" a la vez."""
    edificio = _edificio(db)
    headers = como("admin_general")
    gasto = _gasto(db, edificio)
    presupuesto = _crear_presupuesto(cliente, edificio, headers).json()

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/presupuestos/{presupuesto['id']}",
        json={"estado": "rechazado", "gasto_id": gasto.id},
        headers=headers,
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "PRESUPUESTO_SIN_APROBAR"


def test_no_se_puede_vincular_el_gasto_de_otro_edificio(cliente, como, db):
    edificio = _edificio(db, "Mitre 500")
    otro = _edificio(db, "Otro 900")
    headers = como("admin_general")
    ajeno = _gasto(db, otro)
    presupuesto = _crear_presupuesto(cliente, edificio, headers).json()

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/presupuestos/{presupuesto['id']}",
        json={"estado": "aprobado", "gasto_id": ajeno.id},
        headers=headers,
    )

    assert respuesta.status_code == 404


def test_el_cliente_no_puede_cargar_un_presupuesto_ya_aprobado(cliente, como, db):
    """Si pudiera, la decision dejaria de registrarse como tal."""
    edificio = _edificio(db)

    respuesta = cliente.post(
        f"/api/edificios/{edificio.id}/presupuestos",
        json={
            "descripcion": "Arreglo",
            "monto": "1000.00",
            "fecha": "2026-11-10",
            "estado": "aprobado",
        },
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 422


def test_un_presupuesto_pendiente_se_puede_borrar(cliente, como, db):
    edificio = _edificio(db)
    headers = como("admin_general")
    presupuesto = _crear_presupuesto(cliente, edificio, headers).json()

    respuesta = cliente.delete(
        f"/api/edificios/{edificio.id}/presupuestos/{presupuesto['id']}",
        headers=headers,
    )

    assert respuesta.status_code == 204
    assert db.scalars(select(Presupuesto)).all() == []


def test_un_presupuesto_ya_decidido_no_se_borra(cliente, como, db):
    """Borrar el rechazado dejaria la aprobacion sin contexto: "aprobamos este"
    sin los otros dos no dice nada."""
    edificio = _edificio(db)
    headers = como("admin_general")
    presupuesto = _crear_presupuesto(cliente, edificio, headers).json()
    cliente.patch(
        f"/api/edificios/{edificio.id}/presupuestos/{presupuesto['id']}",
        json={"estado": "rechazado"},
        headers=headers,
    )

    respuesta = cliente.delete(
        f"/api/edificios/{edificio.id}/presupuestos/{presupuesto['id']}",
        headers=headers,
    )

    assert respuesta.status_code == 400


def test_el_listado_se_filtra_por_estado(cliente, como, db):
    edificio = _edificio(db)
    headers = como("admin_general")
    uno = _crear_presupuesto(cliente, edificio, headers).json()
    _crear_presupuesto(cliente, edificio, headers, "210000.00")
    cliente.patch(
        f"/api/edificios/{edificio.id}/presupuestos/{uno['id']}",
        json={"estado": "aprobado"},
        headers=headers,
    )

    aprobados = cliente.get(
        f"/api/edificios/{edificio.id}/presupuestos?estado=aprobado", headers=headers
    ).json()

    assert aprobados["cantidad"] == 1
    assert aprobados["pendientes"] == 0


def test_un_estado_inventado_en_el_filtro_se_rechaza(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/presupuestos?estado=en_revision",
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "ESTADO_DE_PRESUPUESTO_INVALIDO"


def test_un_residente_no_ve_los_presupuestos(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/presupuestos", headers=como("propietario")
    )

    assert respuesta.status_code == 403


# ===========================================================================
# FACTURAS — OPCIONALES EN TODO SENTIDO
# ===========================================================================


def _crear_factura(cliente, edificio, gasto, headers, **campos):
    cuerpo = {"monto": "180000.00", "fecha": "2026-11-25"}
    cuerpo.update(campos)
    return cliente.post(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}/facturas",
        json=cuerpo,
        headers=headers,
    )


def test_un_gasto_sin_comprobantes_devuelve_lista_vacia_y_no_un_error(
    cliente, como, db
):
    """**Cargar un comprobante es opcional.** Una lista vacia es una respuesta
    normal."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}/facturas",
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["cantidad"] == 0
    assert cuerpo["total_facturado"] == "0.00"
    assert cuerpo["monto_del_gasto"] == "180000.00"


def test_se_puede_cargar_un_comprobante_con_solo_monto_y_fecha(cliente, como, db):
    """Ni numero, ni proveedor, ni archivo. Un recibo escrito a mano no tiene
    numero, y exigirlo haria que alguien escriba "sin numero"."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)

    respuesta = _crear_factura(cliente, edificio, gasto, como("admin_general"))

    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["numero"] is None
    assert cuerpo["archivo_url"] is None


def test_el_comprobante_no_tiene_que_ser_una_factura_fiscal(cliente, como, db):
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)

    respuesta = _crear_factura(
        cliente, edificio, gasto, como("admin_general"), numero="Recibo del plomero"
    )

    assert respuesta.json()["numero"] == "Recibo del plomero"


def test_el_mismo_numero_dos_veces_en_el_mismo_gasto_se_rechaza(cliente, como, db):
    """Dos personas archivando el mismo papel."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)
    headers = como("admin_general")
    _crear_factura(cliente, edificio, gasto, headers, numero="B 0001-00000123")

    respuesta = _crear_factura(
        cliente, edificio, gasto, headers, numero="B 0001-00000123"
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "FACTURA_REPETIDA"


def test_dos_comprobantes_sin_numero_conviven(cliente, como, db):
    """Son dos comprobantes distintos."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)
    headers = como("admin_general")

    _crear_factura(cliente, edificio, gasto, headers, monto="100000.00")
    segundo = _crear_factura(cliente, edificio, gasto, headers, monto="80000.00")

    assert segundo.status_code == 201, segundo.text


def test_el_total_facturado_puede_no_coincidir_con_el_gasto(cliente, como, db):
    """**La diferencia es informacion, no un error:** una factura puede traer un
    ajuste y un gasto puede cubrirse con dos facturas."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio, monto="180000.00")
    headers = como("admin_general")
    _crear_factura(cliente, edificio, gasto, headers, monto="181500.00")

    cuerpo = cliente.get(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}/facturas", headers=headers
    ).json()

    assert cuerpo["total_facturado"] == "181500.00"
    assert cuerpo["monto_del_gasto"] == "180000.00"


def test_un_archivo_que_no_es_un_enlace_se_rechaza(cliente, como, db):
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)

    respuesta = _crear_factura(
        cliente, edificio, gasto, como("admin_general"), archivo_url="factura.pdf"
    )

    assert respuesta.status_code == 422


def test_borrar_un_comprobante_no_toca_el_gasto(cliente, como, db):
    """Son dos cosas distintas, y el gasto puede existir sin comprobante."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)
    headers = como("admin_general")
    factura = _crear_factura(cliente, edificio, gasto, headers).json()

    respuesta = cliente.delete(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}/facturas/{factura['id']}",
        headers=headers,
    )

    assert respuesta.status_code == 204
    assert db.get(Gasto, gasto.id) is not None


def test_no_se_carga_un_comprobante_en_el_gasto_de_otro_edificio(cliente, como, db):
    edificio = _edificio(db, "Mitre 500")
    otro = _edificio(db, "Otro 900")
    ajeno = _gasto(db, otro)

    respuesta = _crear_factura(cliente, edificio, ajeno, como("admin_general"))

    assert respuesta.status_code == 404


def test_un_residente_no_ve_los_comprobantes(cliente, como, db):
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}/facturas",
        headers=como("propietario"),
    )

    assert respuesta.status_code == 403


def test_un_admin_de_consorcio_no_toca_la_tesoreria_de_un_edificio_ajeno(
    cliente, como, db
):
    """404 y no 403, como en todo el proyecto."""
    ajeno = _edificio(db)
    headers = como(autorizacion.ADMIN_CONSORCIO)

    assert cliente.get(f"/api/edificios/{ajeno.id}/fondos", headers=headers).status_code == 404
    assert cliente.get(f"/api/edificios/{ajeno.id}/caja", headers=headers).status_code == 404
    assert (
        cliente.get(f"/api/edificios/{ajeno.id}/presupuestos", headers=headers).status_code
        == 404
    )

"""Pruebas de la carga de coeficientes (`F1-T24`).

Esta es la tarea que en la iteracion anterior quedo pendiente **en silencio**:
nunca existio endpoint para cargar el coeficiente y el problema aparecio recien
al intentar generar una expensa. Asi que lo que se prueba, mas que el CRUD, es
que el estado del edificio sea visible en cada respuesta:

  1. **La suma y lo que falta viajan siempre**, con los identificadores de las
     unidades sin coeficiente. Un "faltan coeficientes" que no dice cuales es lo
     que hizo que esto se descubriera tres fases despues.
  2. **La suma no se bloquea mientras se carga**, porque cargar treinta
     coeficientes pasa por estados intermedios donde no suma 100.
  3. **El atajo no pisa lo cargado a mano sin confirmar** (409, que es el codigo
     de "necesito que confirmes" en este proyecto).
  4. **El atajo da 100% exacto**, con los casos que historicamente no cerraban.
  5. El caso permitido y el prohibido, y el anidado como permiso.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.edificio import Departamento, Edificio, Piso
from app.models.usuario import Usuario
from app.services import autorizacion, finanzas


def _edificio(db, nombre: str = "Consorcio Mitre 500", **columnas) -> Edificio:
    edificio = Edificio(nombre=nombre, direccion="Mitre 500", cp="C1000", **columnas)
    db.add(edificio)
    db.commit()
    return edificio


def _estructura(db, edificio: Edificio, pisos: int, por_piso: int, m2=None) -> list[Departamento]:
    """Pisos y unidades, con la misma forma que genera el alta del edificio."""
    unidades: list[Departamento] = []
    for numero in range(1, pisos + 1):
        piso = Piso(edificio_id=edificio.id, numero=numero, orden=numero)
        db.add(piso)
        db.commit()
        for indice in range(por_piso):
            unidad = Departamento(
                piso_id=piso.id,
                identificador=f"{numero}{chr(ord('A') + indice)}",
                m2=Decimal(m2) if m2 is not None else None,
            )
            db.add(unidad)
            unidades.append(unidad)
    db.commit()
    return unidades


def _admin(como) -> dict:
    return como(autorizacion.ADMIN_GENERAL)


def ruta_estado(edificio_id: int) -> str:
    return f"/api/edificios/{edificio_id}/coeficientes"


def ruta_atajo(edificio_id: int) -> str:
    return f"/api/edificios/{edificio_id}/coeficientes/aplicar-atajo"


def ruta_carga(edificio_id: int, departamento_id: int) -> str:
    return f"/api/edificios/{edificio_id}/departamentos/{departamento_id}/coeficiente"


# ==========================================================================
# EL ESTADO SE VE SIEMPRE
# ==========================================================================


def test_un_edificio_recien_cargado_dice_cuantas_unidades_faltan(cliente, como, db):
    edificio = _edificio(db)
    _estructura(db, edificio, pisos=2, por_piso=2)

    respuesta = cliente.get(ruta_estado(edificio.id), headers=_admin(como))

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["cantidad_unidades"] == 4
    assert cuerpo["unidades_sin_coeficiente"] == 4
    assert cuerpo["suma"] == "0.000"
    assert cuerpo["suma_cien"] is False


def test_el_mensaje_nombra_las_unidades_que_faltan(cliente, como, db):
    """Un "faltan coeficientes" que no dice cuales es lo que hizo que esto se
    descubriera tres fases despues."""
    edificio = _edificio(db)
    _estructura(db, edificio, pisos=1, por_piso=3)

    mensaje = cliente.get(ruta_estado(edificio.id), headers=_admin(como)).json()["mensaje"]

    assert "3 unidades" in mensaje
    assert "1A" in mensaje and "1B" in mensaje and "1C" in mensaje


def test_con_muchas_unidades_el_mensaje_no_las_nombra_todas(cliente, como, db):
    """Un edificio de 160 unidades recien cargado daria un mensaje ilegible."""
    edificio = _edificio(db)
    _estructura(db, edificio, pisos=5, por_piso=8)

    mensaje = cliente.get(ruta_estado(edificio.id), headers=_admin(como)).json()["mensaje"]

    assert "40 unidades" in mensaje
    assert "más" in mensaje


def test_un_edificio_sin_unidades_lo_dice(cliente, como, db):
    edificio = _edificio(db)

    cuerpo = cliente.get(ruta_estado(edificio.id), headers=_admin(como)).json()

    assert cuerpo["cantidad_unidades"] == 0
    assert "no tiene unidades" in cuerpo["mensaje"]


def test_las_unidades_vienen_con_su_piso_y_su_superficie(cliente, como, db):
    """Es lo que se mira al cargar: el coeficiente de la 2B se compara con el de
    la 1B, y la superficie es el unico control de razonabilidad a mano."""
    edificio = _edificio(db)
    _estructura(db, edificio, pisos=2, por_piso=1, m2="50.00")

    unidades = cliente.get(ruta_estado(edificio.id), headers=_admin(como)).json()["unidades"]

    assert [u["identificador"] for u in unidades] == ["1A", "2A"]
    assert [u["piso_numero"] for u in unidades] == [1, 2]
    assert unidades[0]["m2"] == "50.00"


def test_el_orden_de_las_unidades_es_por_piso_y_despues_por_identificador(cliente, como, db):
    """El orden importa: el reparto de los atajos distribuye el sobrante entre
    las primeras unidades, asi que un orden inestable daria coeficientes
    distintos para el mismo edificio."""
    edificio = _edificio(db)
    _estructura(db, edificio, pisos=3, por_piso=2)

    unidades = cliente.get(ruta_estado(edificio.id), headers=_admin(como)).json()["unidades"]

    assert [u["identificador"] for u in unidades] == ["1A", "1B", "2A", "2B", "3A", "3B"]


# ==========================================================================
# CARGA MANUAL
# ==========================================================================


def test_carga_el_coeficiente_de_una_unidad(cliente, como, db):
    edificio = _edificio(db)
    unidades = _estructura(db, edificio, pisos=1, por_piso=2)

    respuesta = cliente.patch(
        ruta_carga(edificio.id, unidades[0].id),
        json={"coeficiente": "3.571"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 200
    db.refresh(unidades[0])
    assert unidades[0].coeficiente == Decimal("3.571")


def test_la_respuesta_de_la_carga_trae_la_suma_del_edificio(cliente, como, db):
    """Quien carga treinta coeficientes necesita ver la suma despues de cada
    uno; pedirla aparte seria el doble de pedidos para el dato que mas importa."""
    edificio = _edificio(db)
    unidades = _estructura(db, edificio, pisos=1, por_piso=2)
    headers = _admin(como)

    cliente.patch(ruta_carga(edificio.id, unidades[0].id), json={"coeficiente": "60.000"}, headers=headers)
    cuerpo = cliente.patch(
        ruta_carga(edificio.id, unidades[1].id), json={"coeficiente": "40.000"}, headers=headers
    ).json()

    assert cuerpo["suma"] == "100.000"
    assert cuerpo["suma_cien"] is True
    assert cuerpo["unidades_sin_coeficiente"] == 0
    assert "listo para generar expensas" in cuerpo["mensaje"]


def test_mientras_falta_cargar_la_suma_no_se_bloquea(cliente, como, db):
    """Cargar treinta coeficientes pasa por estados intermedios donde la suma no
    es 100: rechazarlos obligaria a cargar todo en un solo pedido."""
    edificio = _edificio(db)
    unidades = _estructura(db, edificio, pisos=1, por_piso=3)

    respuesta = cliente.patch(
        ruta_carga(edificio.id, unidades[0].id),
        json={"coeficiente": "3.500"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["suma"] == "3.500"
    assert respuesta.json()["suma_cien"] is False


def test_una_suma_que_no_llega_a_cien_lo_dice_con_el_numero(cliente, como, db):
    edificio = _edificio(db)
    unidades = _estructura(db, edificio, pisos=1, por_piso=2)
    headers = _admin(como)

    cliente.patch(ruta_carga(edificio.id, unidades[0].id), json={"coeficiente": "50.000"}, headers=headers)
    cuerpo = cliente.patch(
        ruta_carga(edificio.id, unidades[1].id), json={"coeficiente": "49.989"}, headers=headers
    ).json()

    assert cuerpo["suma"] == "99.989"
    assert cuerpo["suma_cien"] is False
    assert "99.989" in cuerpo["mensaje"]


def test_un_coeficiente_con_cuatro_decimales_se_rechaza(cliente, como, db):
    """La columna es `Numeric(6,3)`: un cuarto decimal se guardaria redondeado,
    y la suma de los redondeos es la que daba 99,989% en la iteracion anterior."""
    edificio = _edificio(db)
    unidades = _estructura(db, edificio, pisos=1, por_piso=1)

    respuesta = cliente.patch(
        ruta_carga(edificio.id, unidades[0].id),
        json={"coeficiente": "3.5712"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 422


@pytest.mark.parametrize("valor", ["-1", "100.001", "150"])
def test_un_coeficiente_fuera_de_rango_se_rechaza(cliente, como, db, valor):
    edificio = _edificio(db)
    unidades = _estructura(db, edificio, pisos=1, por_piso=1)

    respuesta = cliente.patch(
        ruta_carga(edificio.id, unidades[0].id),
        json={"coeficiente": valor},
        headers=_admin(como),
    )

    assert respuesta.status_code == 422


def test_cero_es_un_coeficiente_valido(cliente, como, db):
    """Una unidad puede estar exenta —el departamento del encargado suele
    estarlo— y eso es un 0 cargado a proposito, no un dato faltante."""
    edificio = _edificio(db)
    unidades = _estructura(db, edificio, pisos=1, por_piso=1)

    respuesta = cliente.patch(
        ruta_carga(edificio.id, unidades[0].id),
        json={"coeficiente": "0"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["unidades_sin_coeficiente"] == 0


def test_un_campo_que_el_esquema_no_conoce_se_rechaza(cliente, como, db):
    edificio = _edificio(db)
    unidades = _estructura(db, edificio, pisos=1, por_piso=1)

    respuesta = cliente.patch(
        ruta_carga(edificio.id, unidades[0].id),
        json={"coeficiente": "1.000", "m2": "50"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 422


# ==========================================================================
# LOS ATAJOS
# ==========================================================================


def test_el_atajo_de_partes_iguales_suma_cien_exacto(cliente, como, db):
    edificio = _edificio(db)
    _estructura(db, edificio, pisos=7, por_piso=4)

    respuesta = cliente.post(
        ruta_atajo(edificio.id),
        json={"criterio": "partes_iguales"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["suma"] == "100.000"
    assert cuerpo["suma_cien"] is True
    assert cuerpo["unidades_sin_coeficiente"] == 0


def test_el_caso_historico_de_veintiocho_unidades_cierra_en_cien(cliente, como, db):
    """28 unidades es el caso que daba 99,989% en la iteracion anterior: 100/28
    no es exacto con tres decimales. Ahora el sobrante se reparte, asi que la
    suma da 100 por construccion y no por redondeo afortunado."""
    edificio = _edificio(db)
    _estructura(db, edificio, pisos=7, por_piso=4)

    cliente.post(ruta_atajo(edificio.id), json={"criterio": "partes_iguales"}, headers=_admin(como))

    guardados = [
        d.coeficiente for d in db.scalars(select(Departamento)).all()
    ]
    assert sum(guardados) == Decimal("100.000")
    # El sobrante se reparte entre las primeras, no se apila en la ultima.
    assert sorted(set(guardados)) == [Decimal("3.571"), Decimal("3.572")]


def test_el_atajo_por_metros_cuadrados_reparte_proporcionalmente(cliente, como, db):
    edificio = _edificio(db)
    piso = Piso(edificio_id=edificio.id, numero=1, orden=1)
    db.add(piso)
    db.commit()
    for identificador, metros in (("1A", "30.00"), ("1B", "70.00")):
        db.add(Departamento(piso_id=piso.id, identificador=identificador, m2=Decimal(metros)))
    db.commit()

    respuesta = cliente.post(
        ruta_atajo(edificio.id),
        json={"criterio": "metros_cuadrados"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 200
    unidades = {u["identificador"]: u["coeficiente"] for u in respuesta.json()["unidades"]}
    assert unidades["1A"] == "30.000"
    assert unidades["1B"] == "70.000"
    assert respuesta.json()["suma"] == "100.000"


def test_el_atajo_por_metros_cuadrados_necesita_todas_las_superficies(cliente, como, db):
    """Y el mensaje dice cuantas faltan y cuales: sin eso, quien carga tiene que
    revisar una por una."""
    edificio = _edificio(db)
    piso = Piso(edificio_id=edificio.id, numero=1, orden=1)
    db.add(piso)
    db.commit()
    db.add(Departamento(piso_id=piso.id, identificador="1A", m2=Decimal("50.00")))
    db.add(Departamento(piso_id=piso.id, identificador="1B"))
    db.commit()

    respuesta = cliente.post(
        ruta_atajo(edificio.id),
        json={"criterio": "metros_cuadrados"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 400
    detalle = respuesta.json()["detail"]
    assert "1 unidad" in detalle
    assert "1B" in detalle


def test_el_atajo_no_pisa_lo_cargado_a_mano_sin_confirmar(cliente, como, db):
    """Pisar un coeficiente que salio del reglamento con un calculo automatico
    es destruir el dato verdadero y reemplazarlo por uno plausible."""
    edificio = _edificio(db)
    unidades = _estructura(db, edificio, pisos=1, por_piso=2)
    unidades[0].coeficiente = Decimal("60.000")
    db.commit()

    respuesta = cliente.post(
        ruta_atajo(edificio.id),
        json={"criterio": "partes_iguales"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 409
    db.refresh(unidades[0])
    assert unidades[0].coeficiente == Decimal("60.000")


def test_el_rechazo_del_atajo_es_409_porque_es_el_codigo_de_confirmacion(cliente, como, db):
    """El envoltorio de `fetch` del frontend convierte el 409 en
    `error.necesitaConfirmacion` y abre el dialogo de "¿seguro?". Este es el
    unico lugar de la Fase 1 donde eso corresponde."""
    edificio = _edificio(db)
    unidades = _estructura(db, edificio, pisos=1, por_piso=2)
    unidades[0].coeficiente = Decimal("60.000")
    db.commit()

    respuesta = cliente.post(
        ruta_atajo(edificio.id),
        json={"criterio": "partes_iguales"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 409
    assert "¿querés reemplazarlos igual?" in respuesta.json()["detail"]


def test_con_sobrescribir_el_atajo_reemplaza_todo(cliente, como, db):
    edificio = _edificio(db)
    unidades = _estructura(db, edificio, pisos=1, por_piso=2)
    unidades[0].coeficiente = Decimal("60.000")
    db.commit()

    respuesta = cliente.post(
        ruta_atajo(edificio.id),
        json={"criterio": "partes_iguales", "sobrescribir": True},
        headers=_admin(como),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["suma"] == "100.000"
    db.refresh(unidades[0])
    assert unidades[0].coeficiente == Decimal("50.000")


def test_un_criterio_inventado_se_rechaza(cliente, como, db):
    edificio = _edificio(db)
    _estructura(db, edificio, pisos=1, por_piso=2)

    respuesta = cliente.post(
        ruta_atajo(edificio.id),
        json={"criterio": "por_ventanas"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 422


def test_el_atajo_en_un_edificio_sin_unidades_se_rechaza(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.post(
        ruta_atajo(edificio.id),
        json={"criterio": "partes_iguales"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 400


def test_el_atajo_de_una_sola_unidad_le_da_el_cien_por_ciento(cliente, como, db):
    edificio = _edificio(db)
    _estructura(db, edificio, pisos=1, por_piso=1)

    respuesta = cliente.post(
        ruta_atajo(edificio.id),
        json={"criterio": "partes_iguales"},
        headers=_admin(como),
    )

    assert respuesta.json()["unidades"][0]["coeficiente"] == "100.000"


def test_el_atajo_es_una_sola_transaccion(cliente, como, db):
    """La mitad de un edificio con coeficientes nuevos y la otra con los viejos
    no suma 100% y nadie se daria cuenta hasta la expensa.

    Se verifica por el resultado: despues de aplicarlo, TODAS las unidades
    tienen coeficiente y la suma es exacta — no hay ninguna que haya quedado
    como estaba.
    """
    edificio = _edificio(db)
    _estructura(db, edificio, pisos=6, por_piso=7)

    cliente.post(ruta_atajo(edificio.id), json={"criterio": "partes_iguales"}, headers=_admin(como))

    guardados = [d.coeficiente for d in db.scalars(select(Departamento)).all()]
    assert len(guardados) == 42
    assert all(c is not None for c in guardados)
    assert sum(guardados) == finanzas.TOTAL_COEFICIENTES


def test_aplicar_el_atajo_dos_veces_da_el_mismo_resultado(cliente, como, db):
    """El orden de las unidades es estable, asi que el reparto del sobrante
    tambien: si no lo fuera, dos llamadas darian coeficientes distintos para el
    mismo edificio y nadie entenderia por que cambio su expensa."""
    edificio = _edificio(db)
    _estructura(db, edificio, pisos=7, por_piso=4)
    headers = _admin(como)

    primera = cliente.post(ruta_atajo(edificio.id), json={"criterio": "partes_iguales"}, headers=headers).json()
    segunda = cliente.post(
        ruta_atajo(edificio.id),
        json={"criterio": "partes_iguales", "sobrescribir": True},
        headers=headers,
    ).json()

    assert primera["unidades"] == segunda["unidades"]


# ==========================================================================
# PERMISOS Y ALCANCE
# ==========================================================================


@pytest.mark.parametrize(
    "rol",
    [
        autorizacion.ENCARGADO,
        autorizacion.PROPIETARIO,
        autorizacion.INQUILINO,
        autorizacion.AUDITOR,
        autorizacion.PROVEEDOR,
    ],
)
def test_los_demas_roles_no_tocan_los_coeficientes(cliente, como, db, rol):
    edificio = _edificio(db)
    unidades = _estructura(db, edificio, pisos=1, por_piso=1)
    headers = como(rol)

    assert cliente.get(ruta_estado(edificio.id), headers=headers).status_code == 403
    assert cliente.patch(
        ruta_carga(edificio.id, unidades[0].id), json={"coeficiente": "1"}, headers=headers
    ).status_code == 403
    assert cliente.post(
        ruta_atajo(edificio.id), json={"criterio": "partes_iguales"}, headers=headers
    ).status_code == 403


def test_sin_autenticacion_es_401(cliente, db):
    edificio = _edificio(db)

    assert cliente.get(ruta_estado(edificio.id)).status_code == 401


def test_el_administrador_de_consorcio_carga_los_de_su_edificio(cliente, como, db):
    headers = como(autorizacion.ADMIN_CONSORCIO)
    admin = db.scalars(
        select(Usuario)
        .where(Usuario.rol == autorizacion.ADMIN_CONSORCIO)
        .order_by(Usuario.id.desc())
    ).first()
    edificio = _edificio(db, admin_consorcio_id=admin.id)
    unidades = _estructura(db, edificio, pisos=1, por_piso=1)

    respuesta = cliente.patch(
        ruta_carga(edificio.id, unidades[0].id),
        json={"coeficiente": "100.000"},
        headers=headers,
    )

    assert respuesta.status_code == 200


def test_un_edificio_ajeno_responde_404(cliente, como, db):
    headers = como(autorizacion.ADMIN_CONSORCIO)
    ajeno = _edificio(db, "De otro")
    _estructura(db, ajeno, pisos=1, por_piso=1)

    assert cliente.get(ruta_estado(ajeno.id), headers=headers).status_code == 404


def test_una_unidad_de_otro_edificio_es_404(cliente, como, db):
    """El anidado es un permiso: el helper que busca la unidad lleva siempre la
    condicion del edificio, y es el mismo que usa el CRUD de la estructura."""
    mio = _edificio(db, "El mio")
    ajeno = _edificio(db, "De otro")
    unidades = _estructura(db, ajeno, pisos=1, por_piso=1)

    respuesta = cliente.patch(
        ruta_carga(mio.id, unidades[0].id),
        json={"coeficiente": "50.000"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 404
    db.refresh(unidades[0])
    assert unidades[0].coeficiente is None


def test_el_coeficiente_no_entra_por_el_patch_de_la_estructura(cliente, como, db):
    """Tiene su propio endpoint a proposito: separado, el permiso y la
    validacion se leen de un vistazo, y cambiar los metros cuadrados nunca
    puede tocar un coeficiente por accidente."""
    edificio = _edificio(db)
    unidades = _estructura(db, edificio, pisos=1, por_piso=1)

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/departamentos/{unidades[0].id}",
        json={"coeficiente": "50.000"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 422


# ==========================================================================
# COMPLETAR EL RESTO (observacion del 2026-11-11)
#
# El tercer criterio del endpoint de atajos. No es un atajo mas: completa solo
# las unidades en blanco y no toca ninguna de las cargadas, asi que tampoco
# pide confirmacion — no puede pisar nada.
# ==========================================================================


def _edificio_con_unidades(db, cantidad):
    """Un edificio con N unidades, repartidas como las reparte el alta.

    Hasta cuatro unidades van en un piso; de ahi en adelante, de a cuatro por
    piso, que es la forma del edificio tipico de la cartera y la que usan el
    resto de los tests de este archivo.
    """
    if cantidad > 4 and cantidad % 4 == 0:
        pisos, por_piso = cantidad // 4, 4
    else:
        pisos, por_piso = 1, cantidad

    edificio = _edificio(db, nombre=f"Consorcio de {cantidad} unidades")
    unidades = _estructura(db, edificio, pisos=pisos, por_piso=por_piso)
    return edificio, unidades


def _completar(cliente, headers, edificio_id):
    return cliente.post(
        f"/api/edificios/{edificio_id}/coeficientes/aplicar-atajo",
        json={"criterio": "completar_el_resto"},
        headers=headers,
    )


def test_completar_el_resto_reparte_entre_las_que_estan_en_blanco(
    cliente, db, como
):
    """El caso del usuario: cuatro unidades, dos al 30%, las otras dos al 20%."""
    headers = como(autorizacion.ADMIN_GENERAL)
    edificio, unidades = _edificio_con_unidades(db, cantidad=4)

    for unidad in unidades[:2]:
        unidad.coeficiente = Decimal("30.000")
    db.commit()

    respuesta = _completar(cliente, headers, edificio.id)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["suma"] == "100.000"
    assert cuerpo["suma_cien"] is True
    valores = [u["coeficiente"] for u in cuerpo["unidades"]]
    assert valores == ["30.000", "30.000", "20.000", "20.000"]


def test_completar_el_resto_no_toca_las_cargadas(cliente, db, como):
    """Es la razon de ser del criterio: un coeficiente que salio del
    reglamento no lo puede pisar un calculo automatico."""
    headers = como(autorizacion.ADMIN_GENERAL)
    edificio, unidades = _edificio_con_unidades(db, cantidad=3)

    unidades[0].coeficiente = Decimal("51.234")
    db.commit()

    cuerpo = _completar(cliente, headers, edificio.id).json()

    assert cuerpo["unidades"][0]["coeficiente"] == "51.234"
    assert cuerpo["suma"] == "100.000"


def test_completar_el_resto_no_pide_confirmacion(cliente, db, como):
    """Los dos atajos devuelven 409 si hay algo cargado. Este no, porque no
    puede pisar nada: pedir confirmacion seria preguntar por algo que no va a
    pasar, y una pregunta que siempre se contesta igual se deja de leer."""
    headers = como(autorizacion.ADMIN_GENERAL)
    edificio, unidades = _edificio_con_unidades(db, cantidad=4)

    unidades[0].coeficiente = Decimal("25.000")
    db.commit()

    assert _completar(cliente, headers, edificio.id).status_code == 200


def test_sin_nada_cargado_completar_el_resto_es_partes_iguales(cliente, db, como):
    """Con todas en blanco, el resto es 100% y se reparte entre todas: el
    mismo resultado que el atajo de partes iguales, por el mismo metodo."""
    headers = como(autorizacion.ADMIN_GENERAL)
    edificio, _ = _edificio_con_unidades(db, cantidad=28)

    cuerpo = _completar(cliente, headers, edificio.id).json()

    assert cuerpo["suma"] == "100.000"
    assert sorted({u["coeficiente"] for u in cuerpo["unidades"]}) == [
        "3.571",
        "3.572",
    ]


def test_sin_unidades_en_blanco_explica_que_no_queda_resto(cliente, db, como):
    headers = como(autorizacion.ADMIN_GENERAL)
    edificio, unidades = _edificio_con_unidades(db, cantidad=2)

    for unidad in unidades:
        unidad.coeficiente = Decimal("50.000")
    db.commit()

    respuesta = _completar(cliente, headers, edificio.id)

    assert respuesta.status_code == 400
    assert "no queda" in respuesta.json()["detail"].lower()


def test_si_lo_cargado_ya_suma_cien_no_se_completa_con_ceros(cliente, db, como):
    """A las que faltan les tocaria 0%, que es un dato inventado. El mensaje
    nombra la salida real: si son exentas, se les carga 0 a mano."""
    headers = como(autorizacion.ADMIN_GENERAL)
    edificio, unidades = _edificio_con_unidades(db, cantidad=3)

    unidades[0].coeficiente = Decimal("40.000")
    unidades[1].coeficiente = Decimal("60.000")
    db.commit()

    respuesta = _completar(cliente, headers, edificio.id)

    assert respuesta.status_code == 400
    assert "0%" in respuesta.json()["detail"]
    # No escribio nada: la unidad en blanco sigue en blanco.
    db.refresh(unidades[2])
    assert unidades[2].coeficiente is None


def test_si_lo_cargado_pasa_de_cien_lo_dice_con_el_numero(cliente, db, como):
    headers = como(autorizacion.ADMIN_GENERAL)
    edificio, unidades = _edificio_con_unidades(db, cantidad=3)

    unidades[0].coeficiente = Decimal("60.000")
    unidades[1].coeficiente = Decimal("60.000")
    db.commit()

    respuesta = _completar(cliente, headers, edificio.id)

    assert respuesta.status_code == 400
    assert "120.000" in respuesta.json()["detail"]


def test_completar_el_resto_es_idempotente_en_la_suma(cliente, db, como):
    """Aplicarlo y volver a aplicarlo no cambia nada: la segunda vez ya no
    quedan unidades en blanco, asi que contesta 400 y la suma sigue en 100."""
    headers = como(autorizacion.ADMIN_GENERAL)
    edificio, unidades = _edificio_con_unidades(db, cantidad=4)

    unidades[0].coeficiente = Decimal("10.000")
    db.commit()

    primera = _completar(cliente, headers, edificio.id)
    assert primera.json()["suma"] == "100.000"

    segunda = _completar(cliente, headers, edificio.id)
    assert segunda.status_code == 400

    estado = cliente.get(
        f"/api/edificios/{edificio.id}/coeficientes", headers=headers
    ).json()
    assert estado["suma"] == "100.000"


def test_un_criterio_que_no_existe_sigue_dando_422(cliente, db, como):
    """La lista de criterios creció a tres: el validador tiene que seguir
    rechazando lo que no esté en ella."""
    headers = como(autorizacion.ADMIN_GENERAL)
    edificio, _ = _edificio_con_unidades(db, cantidad=2)

    respuesta = cliente.post(
        f"/api/edificios/{edificio.id}/coeficientes/aplicar-atajo",
        json={"criterio": "lo_que_se_me_ocurra"},
        headers=headers,
    )

    assert respuesta.status_code == 422

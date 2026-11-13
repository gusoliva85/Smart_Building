"""Pruebas de la generacion y publicacion de la expensa (`F2-T05`).

Lo que se prueba:

  1. **Que se niegue antes de liquidar mal.** Sin gastos, sin coeficientes, con
     coeficientes que no suman 100: tres mensajes distintos porque se arreglan
     distinto.
  2. **El patron de confirmacion de 409**, que es el que permite no usar nunca
     un `confirm()` del navegador.
  3. **Que regenerar conserve la identidad** de la expensa y reemplace su
     contenido, en vez de dejar dos liquidaciones del mismo mes.
  4. **Que publicar cierre la puerta para siempre**, y que a partir de ahi
     tampoco se puedan tocar los gastos de ese periodo.
  5. **Que todo pase en una transaccion**: que un fallo no deje una expensa a
     medio crear.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.edificio import Departamento, Edificio, Piso
from app.models.finanzas import Expensa, ExpensaDepartamento, ExpensaDetalle, Gasto
from app.models.usuario import Usuario
from app.services import autorizacion, finanzas

RUTA = "/api/edificios/{}/expensas"


# ===========================================================================
# ESCENARIO
# ===========================================================================


def _edificio_listo(db, cantidad_unidades: int = 4) -> Edificio:
    """Un edificio con unidades y coeficientes que suman 100%.

    Es el estado minimo desde el que se puede liquidar, y armarlo a mano en
    cada test es lo que hace que los tests digan que les falta cuando falla.
    """
    edificio = Edificio(nombre="Consorcio Mitre 500", direccion="Mitre 500", cp="C1000")
    db.add(edificio)
    db.commit()

    piso = Piso(edificio_id=edificio.id, numero="1", orden=1)
    db.add(piso)
    db.commit()

    coeficientes = finanzas.calcular_partes_iguales(cantidad_unidades)
    for numero, coeficiente in enumerate(coeficientes, start=1):
        db.add(
            Departamento(
                piso_id=piso.id,
                identificador=f"1{chr(64 + numero)}",
                coeficiente=coeficiente,
            )
        )
    db.commit()
    return edificio


def _gasto(db, edificio, **columnas) -> Gasto:
    datos = {
        "edificio_id": edificio.id,
        "rubro": "limpieza",
        "monto": Decimal("100000.00"),
        "fecha": date(2026, 11, 5),
    }
    datos.update(columnas)
    gasto = Gasto(**datos)
    db.add(gasto)
    db.commit()
    return gasto


def _generar(cliente, edificio, headers, **cuerpo):
    datos = {"anio": 2026, "mes": 11}
    datos.update(cuerpo)
    return cliente.post(RUTA.format(edificio.id), json=datos, headers=headers)


# ===========================================================================
# SE NIEGA ANTES DE LIQUIDAR MAL
# ===========================================================================


def test_sin_gastos_no_hay_nada_que_liquidar(cliente, como, db):
    edificio = _edificio_listo(db)

    respuesta = _generar(cliente, edificio, como("admin_general"))

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "PERIODO_SIN_GASTOS"


def test_los_gastos_de_otro_mes_no_cuentan(cliente, como, db):
    """El filtro de periodo es el mismo de `F2-T02`, reutilizado: las dos
    pantallas no pueden discrepar sobre que gastos son de noviembre."""
    edificio = _edificio_listo(db)
    _gasto(db, edificio, fecha=date(2026, 10, 31))
    _gasto(db, edificio, fecha=date(2026, 12, 1))

    respuesta = _generar(cliente, edificio, como("admin_general"))

    assert respuesta.json()["codigo"] == "PERIODO_SIN_GASTOS"


def test_sin_coeficientes_cargados_no_liquida_y_dice_cuales_faltan(
    cliente, como, db
):
    """Decir "faltan coeficientes" sin decir cuales obliga a ir a buscarlos a
    mano, unidad por unidad."""
    edificio = _edificio_listo(db)
    unidad = db.scalars(select(Departamento)).first()
    unidad.coeficiente = None
    db.commit()
    _gasto(db, edificio)

    respuesta = _generar(cliente, edificio, como("admin_general"))

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "COEFICIENTES_INCOMPLETOS"
    assert unidad.identificador in respuesta.json()["mensaje"]


def test_con_coeficientes_que_no_suman_cien_no_liquida_y_dice_cuanto_suman(
    cliente, como, db
):
    """Con 99,9% el consorcio reparte menos de lo que gasto y la diferencia no
    la paga nadie. El mensaje trae la suma, que es el dato con el que se
    arregla."""
    edificio = _edificio_listo(db)
    unidad = db.scalars(select(Departamento)).first()
    unidad.coeficiente = Decimal("1.000")
    db.commit()
    _gasto(db, edificio)

    respuesta = _generar(cliente, edificio, como("admin_general"))

    assert respuesta.json()["codigo"] == "COEFICIENTES_NO_SUMAN_CIEN"
    assert "%" in respuesta.json()["mensaje"]


def test_un_edificio_sin_unidades_no_liquida(cliente, como, db):
    edificio = Edificio(nombre="Vacio", direccion="Nada 1", cp="C1000")
    db.add(edificio)
    db.commit()
    _gasto(db, edificio)

    respuesta = _generar(cliente, edificio, como("admin_general"))

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "EDIFICIO_SIN_UNIDADES"


def test_el_orden_de_las_verificaciones_no_hace_confirmar_de_mas(cliente, como, db):
    """Si faltaran coeficientes Y hubiera un borrador, el error que llega es el
    de los coeficientes: pedir una confirmacion para despues fallar seria
    hacerle confirmar algo que no iba a pasar."""
    edificio = _edificio_listo(db)
    _gasto(db, edificio)
    headers = como("admin_general")
    assert _generar(cliente, edificio, headers).status_code == 201

    unidad = db.scalars(select(Departamento)).first()
    unidad.coeficiente = None
    db.commit()

    respuesta = _generar(cliente, edificio, headers)

    assert respuesta.json()["codigo"] == "COEFICIENTES_INCOMPLETOS"


# ===========================================================================
# GENERAR
# ===========================================================================


def test_se_genera_en_borrador(cliente, como, db):
    edificio = _edificio_listo(db)
    _gasto(db, edificio)

    respuesta = _generar(cliente, edificio, como("admin_general"))

    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "borrador"
    assert cuerpo["publicada_en"] is None
    assert cuerpo["periodo"] == "11/2026"


def test_el_total_es_la_suma_de_los_gastos_del_periodo(cliente, como, db):
    edificio = _edificio_listo(db)
    _gasto(db, edificio, rubro="limpieza", monto=Decimal("100000.00"))
    _gasto(db, edificio, rubro="sueldos", monto=Decimal("300000.50"))

    cuerpo = _generar(cliente, edificio, como("admin_general")).json()

    assert cuerpo["total"] == "400000.50"


def test_lo_repartido_cierra_exacto_contra_el_total(cliente, como, db):
    """La garantia de toda la fase, verificada de punta a punta: un monto que
    no divide bien entre 28 unidades."""
    edificio = _edificio_listo(db, cantidad_unidades=28)
    _gasto(db, edificio, monto=Decimal("4849900.00"))

    cuerpo = _generar(cliente, edificio, como("admin_general")).json()

    repartido = sum(
        (Decimal(u["monto_expensa"]) for u in cuerpo["unidades"]), Decimal("0.00")
    )
    assert repartido == Decimal(cuerpo["total"])
    assert cuerpo["cantidad_unidades"] == 28


def test_la_apertura_por_rubro_sale_agrupada_y_en_el_orden_del_catalogo(
    cliente, como, db
):
    """El orden lo pone el catalogo, no el monto ni el alfabeto: comparar dos
    meses es mirar la misma fila."""
    edificio = _edificio_listo(db)
    _gasto(db, edificio, rubro="limpieza", monto=Decimal("100.00"))
    _gasto(db, edificio, rubro="limpieza", monto=Decimal("50.00"))
    _gasto(db, edificio, rubro="sueldos", monto=Decimal("900.00"))

    cuerpo = _generar(cliente, edificio, como("admin_general")).json()

    assert [linea["rubro"] for linea in cuerpo["detalle"]] == ["sueldos", "limpieza"]
    assert cuerpo["detalle"][1]["monto"] == "150.00"
    assert cuerpo["detalle"][0]["rubro_etiqueta"] == "Sueldos y cargas sociales"


def test_cada_unidad_viene_con_su_identificador_y_no_solo_con_el_id(
    cliente, como, db
):
    """El id es interno y no le sirve a nadie del otro lado de la pantalla."""
    edificio = _edificio_listo(db)
    _gasto(db, edificio)

    cuerpo = _generar(cliente, edificio, como("admin_general")).json()

    assert {u["identificador"] for u in cuerpo["unidades"]} == {"1A", "1B", "1C", "1D"}


def test_el_coeficiente_queda_copiado_en_la_liquidacion(cliente, como, db):
    edificio = _edificio_listo(db)
    _gasto(db, edificio)

    cuerpo = _generar(cliente, edificio, como("admin_general")).json()

    assert all(Decimal(u["coeficiente"]) == Decimal("25.000") for u in cuerpo["unidades"])


def test_el_recargo_y_el_saldo_a_favor_nacen_en_cero(cliente, como, db):
    """Hoy no se pueden calcular: necesitan `Pago`, que llega en `F2-T08`. Con
    el recargo configurado en cero, este es ademas el resultado correcto."""
    edificio = _edificio_listo(db)
    _gasto(db, edificio)

    cuerpo = _generar(cliente, edificio, como("admin_general")).json()

    for unidad in cuerpo["unidades"]:
        assert unidad["recargo_mora"] == "0.00"
        assert unidad["saldo_a_favor_aplicado"] == "0.00"
        assert unidad["total_a_pagar"] == unidad["monto_expensa"]


def test_se_escriben_las_tres_tablas(cliente, como, db):
    edificio = _edificio_listo(db)
    _gasto(db, edificio, rubro="limpieza")
    _gasto(db, edificio, rubro="seguros")

    _generar(cliente, edificio, como("admin_general"))

    assert len(db.scalars(select(Expensa)).all()) == 1
    assert len(db.scalars(select(ExpensaDetalle)).all()) == 2
    assert len(db.scalars(select(ExpensaDepartamento)).all()) == 4


# ===========================================================================
# REGENERAR: EL PATRON DE CONFIRMACION
# ===========================================================================


def test_regenerar_sin_confirmar_devuelve_409_con_lo_que_se_reemplaza(
    cliente, como, db
):
    """El 409 es el "necesito que confirmes" de este proyecto, y el mensaje
    trae por cuanto era la que se pisa: es el dato con el que alguien decide si
    seguir."""
    edificio = _edificio_listo(db)
    _gasto(db, edificio, monto=Decimal("100000.00"))
    headers = como("admin_general")
    _generar(cliente, edificio, headers)

    respuesta = _generar(cliente, edificio, headers)

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "EXPENSA_SE_REGENERA"
    assert "100000.00" in respuesta.json()["mensaje"]


def test_regenerar_confirmando_reemplaza_el_contenido(cliente, como, db):
    edificio = _edificio_listo(db)
    _gasto(db, edificio, monto=Decimal("100000.00"))
    headers = como("admin_general")
    primera = _generar(cliente, edificio, headers).json()

    _gasto(db, edificio, rubro="sueldos", monto=Decimal("900000.00"))
    segunda = _generar(cliente, edificio, headers, confirmar=True).json()

    assert segunda["total"] == "1000000.00"
    assert len(segunda["detalle"]) == 2
    assert primera["total"] == "100000.00"


def test_regenerar_conserva_la_identidad_de_la_expensa(cliente, como, db):
    """Se reemplazan su detalle y su reparto, no se la borra y recrea: mantiene
    estables las referencias y evita un agujero si alguna vez se carga un pago
    adelantado."""
    edificio = _edificio_listo(db)
    _gasto(db, edificio)
    headers = como("admin_general")
    primera = _generar(cliente, edificio, headers).json()

    segunda = _generar(cliente, edificio, headers, confirmar=True).json()

    assert segunda["id"] == primera["id"]


def test_regenerar_no_deja_filas_viejas_sueltas(cliente, como, db):
    """`delete-orphan`: el detalle y el reparto son parte del documento, no
    datos sueltos. Si quedaran, la liquidacion tendria el doble de lineas."""
    edificio = _edificio_listo(db)
    _gasto(db, edificio, rubro="limpieza")
    headers = como("admin_general")
    _generar(cliente, edificio, headers)

    _generar(cliente, edificio, headers, confirmar=True)

    assert len(db.scalars(select(ExpensaDetalle)).all()) == 1
    assert len(db.scalars(select(ExpensaDepartamento)).all()) == 4


def test_nunca_quedan_dos_expensas_del_mismo_periodo(cliente, como, db):
    edificio = _edificio_listo(db)
    _gasto(db, edificio)
    headers = como("admin_general")

    _generar(cliente, edificio, headers)
    _generar(cliente, edificio, headers, confirmar=True)
    _generar(cliente, edificio, headers, confirmar=True)

    assert len(db.scalars(select(Expensa)).all()) == 1


def test_dos_periodos_distintos_conviven(cliente, como, db):
    edificio = _edificio_listo(db)
    _gasto(db, edificio, fecha=date(2026, 11, 5))
    _gasto(db, edificio, fecha=date(2026, 12, 5))
    headers = como("admin_general")

    assert _generar(cliente, edificio, headers, mes=11).status_code == 201
    assert _generar(cliente, edificio, headers, mes=12).status_code == 201


# ===========================================================================
# PUBLICAR
# ===========================================================================


def _publicar(cliente, edificio, expensa_id, headers):
    return cliente.post(
        f"/api/edificios/{edificio.id}/expensas/{expensa_id}/publicar",
        headers=headers,
    )


def test_publicar_deja_la_fecha_y_el_estado(cliente, como, db):
    edificio = _edificio_listo(db)
    _gasto(db, edificio)
    headers = como("admin_general")
    expensa = _generar(cliente, edificio, headers).json()

    respuesta = _publicar(cliente, edificio, expensa["id"], headers)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "publicada"
    assert cuerpo["publicada_en"] is not None


def test_una_expensa_publicada_no_se_regenera_nunca_mas(cliente, como, db):
    """**La regla de fondo de la fase.** Los residentes ya tienen su
    comprobante y ya empezaron a pagar: cambiarles el monto abajo de los pies
    es inaceptable, sea la ultima liquidacion o no."""
    edificio = _edificio_listo(db)
    _gasto(db, edificio)
    headers = como("admin_general")
    expensa = _generar(cliente, edificio, headers).json()
    _publicar(cliente, edificio, expensa["id"], headers)

    respuesta = _generar(cliente, edificio, headers, confirmar=True)

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "EXPENSA_YA_PUBLICADA"


def test_publicar_dos_veces_no_vuelve_a_mover_el_vencimiento(cliente, como, db):
    """No es inofensivo: volveria a escribir la fecha de publicacion y con eso
    correria el vencimiento de todo el edificio."""
    edificio = _edificio_listo(db)
    _gasto(db, edificio)
    headers = como("admin_general")
    expensa = _generar(cliente, edificio, headers).json()
    _publicar(cliente, edificio, expensa["id"], headers)

    segunda = _publicar(cliente, edificio, expensa["id"], headers)

    assert segunda.status_code == 400
    assert segunda.json()["codigo"] == "EXPENSA_NO_SE_PUEDE_PUBLICAR"


def test_publicar_una_expensa_que_no_existe(cliente, como, db):
    edificio = _edificio_listo(db)

    respuesta = _publicar(cliente, edificio, 9999, como("admin_general"))

    assert respuesta.status_code == 404


def test_no_se_publica_la_expensa_de_otro_edificio(cliente, como, db):
    """Se la busca siempre dentro del edificio ya verificado."""
    mio = _edificio_listo(db)
    otro = _edificio_listo(db)
    _gasto(db, otro)
    headers = como("admin_general")
    ajena = _generar(cliente, otro, headers).json()

    respuesta = _publicar(cliente, mio, ajena["id"], headers)

    assert respuesta.status_code == 404


# ===========================================================================
# EL CANDADO SOBRE LOS GASTOS YA LIQUIDADOS
# ===========================================================================


def test_un_gasto_de_un_periodo_publicado_no_se_borra(cliente, como, db):
    edificio = _edificio_listo(db)
    gasto = _gasto(db, edificio)
    headers = como("admin_general")
    expensa = _generar(cliente, edificio, headers).json()
    _publicar(cliente, edificio, expensa["id"], headers)

    respuesta = cliente.delete(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}", headers=headers
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "GASTO_DE_PERIODO_PUBLICADO"


def test_un_gasto_de_un_periodo_publicado_no_cambia_de_monto(cliente, como, db):
    edificio = _edificio_listo(db)
    gasto = _gasto(db, edificio)
    headers = como("admin_general")
    expensa = _generar(cliente, edificio, headers).json()
    _publicar(cliente, edificio, expensa["id"], headers)

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}",
        json={"monto": "1.00"},
        headers=headers,
    )

    assert respuesta.json()["codigo"] == "GASTO_DE_PERIODO_PUBLICADO"


def test_la_descripcion_de_un_gasto_ya_liquidado_si_se_puede_corregir(
    cliente, como, db
):
    """No altera ningun numero de la liquidacion, y es justo el campo donde se
    arregla un numero de factura mal tipeado."""
    edificio = _edificio_listo(db)
    gasto = _gasto(db, edificio)
    headers = como("admin_general")
    expensa = _generar(cliente, edificio, headers).json()
    _publicar(cliente, edificio, expensa["id"], headers)

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}",
        json={"descripcion": "Factura 0001-00004521"},
        headers=headers,
    )

    assert respuesta.status_code == 200, respuesta.text


def test_un_gasto_no_se_puede_mover_a_un_periodo_ya_publicado(cliente, como, db):
    """Sacarlo de un periodo abierto para meterlo en uno publicado tambien
    desalinearia una liquidacion emitida."""
    edificio = _edificio_listo(db)
    _gasto(db, edificio, fecha=date(2026, 11, 5))
    de_diciembre = _gasto(db, edificio, fecha=date(2026, 12, 5))
    headers = como("admin_general")
    expensa = _generar(cliente, edificio, headers, mes=11).json()
    _publicar(cliente, edificio, expensa["id"], headers)

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/gastos/{de_diciembre.id}",
        json={"fecha": "2026-11-20"},
        headers=headers,
    )

    assert respuesta.json()["codigo"] == "GASTO_DE_PERIODO_PUBLICADO"


def test_un_gasto_de_un_periodo_en_borrador_se_edita_y_se_borra(cliente, como, db):
    """El flujo normal: corregir un gasto y regenerar. El candado es solo
    despues de publicar."""
    edificio = _edificio_listo(db)
    gasto = _gasto(db, edificio)
    headers = como("admin_general")
    _generar(cliente, edificio, headers)

    editar = cliente.patch(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}",
        json={"monto": "123456.00"},
        headers=headers,
    )
    borrar = cliente.delete(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}", headers=headers
    )

    assert editar.status_code == 200, editar.text
    assert borrar.status_code == 204


def test_cargar_un_gasto_de_un_periodo_publicado_avisa_pero_no_bloquea(
    cliente, como, db
):
    """El gasto es real y tiene que quedar registrado. Lo que corresponde es
    informar, no rechazar."""
    edificio = _edificio_listo(db)
    _gasto(db, edificio)
    headers = como("admin_general")
    expensa = _generar(cliente, edificio, headers).json()
    _publicar(cliente, edificio, expensa["id"], headers)

    respuesta = cliente.post(
        f"/api/edificios/{edificio.id}/gastos",
        json={"rubro": "seguros", "monto": "5000.00", "fecha": "2026-11-28"},
        headers=headers,
    )

    assert respuesta.status_code == 201, respuesta.text
    assert "11/2026" in respuesta.json()["aviso"]


def test_un_gasto_de_un_periodo_sin_liquidar_no_trae_aviso(cliente, como, db):
    edificio = _edificio_listo(db)
    headers = como("admin_general")

    respuesta = cliente.post(
        f"/api/edificios/{edificio.id}/gastos",
        json={"rubro": "seguros", "monto": "5000.00", "fecha": "2026-11-28"},
        headers=headers,
    )

    assert respuesta.json()["aviso"] is None


# ===========================================================================
# PERMISOS Y ALCANCE
# ===========================================================================


def test_un_residente_no_genera_expensas(cliente, como, db):
    edificio = _edificio_listo(db)
    _gasto(db, edificio)

    respuesta = _generar(cliente, edificio, como("propietario"))

    assert respuesta.status_code == 403


def test_un_encargado_no_genera_expensas(cliente, como, db):
    edificio = _edificio_listo(db)
    _gasto(db, edificio)

    respuesta = _generar(cliente, edificio, como("encargado"))

    assert respuesta.status_code == 403


def test_sin_sesion_no_se_genera(cliente, db):
    edificio = _edificio_listo(db)

    respuesta = cliente.post(RUTA.format(edificio.id), json={"anio": 2026, "mes": 11})

    assert respuesta.status_code == 401


def test_un_admin_de_consorcio_no_liquida_un_edificio_ajeno(cliente, como, db):
    """404 y no 403: un 403 confirmaria que ese edificio existe."""
    ajeno = _edificio_listo(db)
    _gasto(db, ajeno)
    headers = como(autorizacion.ADMIN_CONSORCIO)

    respuesta = _generar(cliente, ajeno, headers)

    assert respuesta.status_code == 404


def test_un_admin_de_consorcio_liquida_su_edificio(cliente, como, db):
    headers = como(autorizacion.ADMIN_CONSORCIO)
    usuario = db.scalars(
        select(Usuario)
        .where(Usuario.rol == autorizacion.ADMIN_CONSORCIO)
        .order_by(Usuario.id.desc())
    ).first()
    edificio = _edificio_listo(db)
    edificio.admin_consorcio_id = usuario.id
    db.commit()
    _gasto(db, edificio)

    respuesta = _generar(cliente, edificio, headers)

    assert respuesta.status_code == 201, respuesta.text


def test_un_residente_no_publica(cliente, como, db):
    edificio = _edificio_listo(db)
    _gasto(db, edificio)
    expensa = _generar(cliente, edificio, como("admin_general")).json()

    respuesta = _publicar(cliente, edificio, expensa["id"], como("inquilino"))

    assert respuesta.status_code == 403


# ===========================================================================
# VALIDACION DEL PEDIDO
# ===========================================================================


@pytest.mark.parametrize("mes", [0, 13])
def test_un_mes_que_no_existe_se_rechaza(cliente, como, db, mes):
    edificio = _edificio_listo(db)

    respuesta = _generar(cliente, edificio, como("admin_general"), mes=mes)

    assert respuesta.status_code == 422


def test_un_campo_de_mas_se_rechaza(cliente, como, db):
    """`extra="forbid"`: un `total` mandado por el cliente seria un total que
    el cliente decide, y el total lo calcula el servidor."""
    edificio = _edificio_listo(db)

    respuesta = _generar(cliente, edificio, como("admin_general"), total="1.00")

    assert respuesta.status_code == 422

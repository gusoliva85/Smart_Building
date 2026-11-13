"""Pruebas del CRUD de gastos (`F2-T02`).

Lo que se prueba aca son las cuatro cosas que pueden salir mal de verdad, y no
que un POST devuelva 201:

  1. **El alcance.** Que un administrador no pueda cargar, ver, editar ni
     borrar gastos de un edificio que no administra, y que el que no es
     administrador no entre.
  2. **El filtro de periodo.** Es la razon de ser del endpoint: la expensa se
     genera con los gastos de UN mes, y un filtro que se come el ultimo dia del
     mes se descubre al cerrar el periodo.
  3. **La exactitud del monto.** Que lo que entra vuelva identico, y que un
     monto con mas decimales se rechace en vez de redondearse.
  4. **Que la edicion sea un PATCH de verdad.** Que mandar un campo no borre
     los otros.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.edificio import Edificio
from app.models.finanzas import Gasto
from app.models.usuario import Usuario
from app.services import autorizacion, rubros


def _admin_consorcio_logueado(db, como) -> tuple[dict, Usuario]:
    """El header de un Administrador de Consorcio y su fila de usuario.

    Hacen falta las dos cosas juntas: el header para llamar al endpoint y el
    usuario para poder ponerlo como responsable de un edificio y probar el
    alcance.
    """
    headers = como(autorizacion.ADMIN_CONSORCIO)
    usuario = db.scalars(
        select(Usuario)
        .where(Usuario.rol == autorizacion.ADMIN_CONSORCIO)
        .order_by(Usuario.id.desc())
    ).first()
    return headers, usuario


def _edificio(db, **columnas) -> Edificio:
    datos = {"nombre": "Consorcio Mitre 500", "direccion": "Mitre 500", "cp": "C1000"}
    datos.update(columnas)
    edificio = Edificio(**datos)
    db.add(edificio)
    db.commit()
    return edificio


def _cargar(db, edificio, **columnas) -> Gasto:
    """Un gasto escrito directo en la base, para armar escenarios de lectura."""
    datos = {
        "edificio_id": edificio.id,
        "rubro": "limpieza",
        "monto": Decimal("150000.00"),
        "fecha": date(2026, 11, 5),
    }
    datos.update(columnas)
    gasto = Gasto(**datos)
    db.add(gasto)
    db.commit()
    return gasto


def _nuevo(**campos) -> dict:
    cuerpo = {"rubro": "servicios", "monto": "84500.50", "fecha": "2026-11-10"}
    cuerpo.update(campos)
    return cuerpo


# ===========================================================================
# ALTA
# ===========================================================================


def test_un_admin_general_carga_un_gasto(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.post(
        f"/api/edificios/{edificio.id}/gastos",
        json=_nuevo(descripcion="Factura de luz de noviembre"),
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["rubro"] == "servicios"
    assert cuerpo["monto"] == "84500.50"
    assert cuerpo["descripcion"] == "Factura de luz de noviembre"


def test_la_respuesta_trae_la_etiqueta_del_rubro(cliente, como, db):
    """Para que la pantalla no tenga que mantener su propia copia del catalogo,
    que es la copia que un dia queda vieja."""
    edificio = _edificio(db)

    respuesta = cliente.post(
        f"/api/edificios/{edificio.id}/gastos",
        json=_nuevo(rubro="sueldos"),
        headers=como("admin_general"),
    )

    assert respuesta.json()["rubro_etiqueta"] == "Sueldos y cargas sociales"


def test_el_monto_vuelve_exacto(cliente, como, db):
    """La regla que atraviesa toda la fase: la plata no pasa por `float`."""
    edificio = _edificio(db)

    respuesta = cliente.post(
        f"/api/edificios/{edificio.id}/gastos",
        json=_nuevo(monto="1234.56"),
        headers=como("admin_general"),
    )

    assert respuesta.json()["monto"] == "1234.56"


def test_un_monto_con_tres_decimales_se_rechaza_en_vez_de_redondearse(
    cliente, como, db
):
    """1234,567 guardado como 1234,57 es plata que nadie decidio, y la
    diferencia aparece meses despues sin forma de rastrearla."""
    edificio = _edificio(db)

    respuesta = cliente.post(
        f"/api/edificios/{edificio.id}/gastos",
        json=_nuevo(monto="1234.567"),
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 422
    assert "decimales" in respuesta.text


@pytest.mark.parametrize("monto", ["0", "-500.00"])
def test_un_monto_que_no_es_positivo_se_rechaza(cliente, como, db, monto):
    edificio = _edificio(db)

    respuesta = cliente.post(
        f"/api/edificios/{edificio.id}/gastos",
        json=_nuevo(monto=monto),
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 422


def test_un_rubro_fuera_del_catalogo_se_rechaza_y_el_mensaje_dice_cuales_valen(
    cliente, como, db
):
    edificio = _edificio(db)

    respuesta = cliente.post(
        f"/api/edificios/{edificio.id}/gastos",
        json=_nuevo(rubro="Limpieza"),  # con mayuscula: no es el valor
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 422
    assert "limpieza" in respuesta.text


@pytest.mark.parametrize("rubro", rubros.RUBROS)
def test_los_diez_rubros_del_catalogo_se_pueden_cargar(cliente, como, db, rubro):
    edificio = _edificio(db)

    respuesta = cliente.post(
        f"/api/edificios/{edificio.id}/gastos",
        json=_nuevo(rubro=rubro),
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 201, respuesta.text


def test_una_descripcion_de_solo_espacios_se_guarda_como_vacia(cliente, como, db):
    """Si se guardara el espacio, el listado mostraria una celda en blanco que
    parece un error de la pantalla."""
    edificio = _edificio(db)

    respuesta = cliente.post(
        f"/api/edificios/{edificio.id}/gastos",
        json=_nuevo(descripcion="   "),
        headers=como("admin_general"),
    )

    assert respuesta.json()["descripcion"] is None


def test_un_campo_que_no_existe_se_rechaza(cliente, como, db):
    """`extra="forbid"`: un `proveedor_id` mandado hoy se guardaria sin que
    nada lo valide, porque la tabla de proveedores todavia no existe."""
    edificio = _edificio(db)

    respuesta = cliente.post(
        f"/api/edificios/{edificio.id}/gastos",
        json=_nuevo(proveedor_id=7),
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 422


def test_una_fecha_futura_se_acepta(cliente, como, db):
    """Un seguro o un abono se cargan con su fecha de vencimiento, que todavia
    no llego. Rechazarlos obligaria a esperar al dia exacto."""
    edificio = _edificio(db)

    respuesta = cliente.post(
        f"/api/edificios/{edificio.id}/gastos",
        json=_nuevo(fecha="2027-06-30"),
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 201, respuesta.text


# ===========================================================================
# ALCANCE Y PERMISOS
# ===========================================================================


def test_un_residente_no_entra(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.post(
        f"/api/edificios/{edificio.id}/gastos",
        json=_nuevo(),
        headers=como("propietario"),
    )

    assert respuesta.status_code == 403


def test_un_encargado_no_carga_gastos(cliente, como, db):
    """El encargado gestiona reclamos, no la plata del consorcio."""
    edificio = _edificio(db)

    respuesta = cliente.post(
        f"/api/edificios/{edificio.id}/gastos",
        json=_nuevo(),
        headers=como("encargado"),
    )

    assert respuesta.status_code == 403


def test_sin_sesion_no_se_entra(cliente, db):
    edificio = _edificio(db)

    respuesta = cliente.post(f"/api/edificios/{edificio.id}/gastos", json=_nuevo())

    assert respuesta.status_code == 401


def test_un_admin_de_consorcio_no_toca_un_edificio_ajeno(cliente, como, db):
    """**404 y no 403**: un 403 confirmaria que ese edificio existe, y un
    administrador no tiene por que enterarse de la cartera de otro."""
    ajeno = _edificio(db, nombre="Consorcio de otro")
    headers = como("admin_consorcio")

    respuesta = cliente.post(
        f"/api/edificios/{ajeno.id}/gastos", json=_nuevo(), headers=headers
    )

    assert respuesta.status_code == 404


def test_un_admin_de_consorcio_carga_en_su_edificio(cliente, como, db):
    headers, usuario = _admin_consorcio_logueado(db, como)
    suyo = _edificio(db, admin_consorcio_id=usuario.id)

    respuesta = cliente.post(
        f"/api/edificios/{suyo.id}/gastos", json=_nuevo(), headers=headers
    )

    assert respuesta.status_code == 201, respuesta.text


def test_un_gasto_de_otro_edificio_no_se_puede_editar(cliente, como, db):
    """Se lo busca SIEMPRE dentro del edificio ya verificado. Buscarlo por id
    suelto y comparar despues es el error que deja pasar el id ajeno."""
    mio = _edificio(db)
    otro = _edificio(db, nombre="Consorcio de al lado")
    gasto_ajeno = _cargar(db, otro)

    respuesta = cliente.patch(
        f"/api/edificios/{mio.id}/gastos/{gasto_ajeno.id}",
        json={"monto": "1.00"},
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 404


# ===========================================================================
# LISTADO Y FILTRO DE PERIODO
# ===========================================================================


def test_el_listado_trae_solo_los_gastos_de_ese_edificio(cliente, como, db):
    mio = _edificio(db)
    otro = _edificio(db, nombre="Consorcio de al lado")
    _cargar(db, mio, monto=Decimal("100.00"))
    _cargar(db, otro, monto=Decimal("999.00"))

    respuesta = cliente.get(
        f"/api/edificios/{mio.id}/gastos", headers=como("admin_general")
    )

    cuerpo = respuesta.json()
    assert cuerpo["cantidad"] == 1
    assert cuerpo["total"] == "100.00"


def test_el_total_lo_calcula_el_servidor(cliente, como, db):
    """Es el numero que despues se reparte entre las unidades: tiene que salir
    del mismo lugar del que va a salir la expensa."""
    edificio = _edificio(db)
    _cargar(db, edificio, monto=Decimal("1000.01"))
    _cargar(db, edificio, monto=Decimal("2000.02"))

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/gastos", headers=como("admin_general")
    )

    assert respuesta.json()["total"] == "3000.03"


def test_el_filtro_por_mes_toma_el_primero_y_el_ultimo_dia(cliente, como, db):
    """El caso que importa del filtro: el rango es `[desde, hasta)`, asi que el
    31 tiene que entrar y el 1 del mes siguiente no. Un filtro que se come el
    ultimo dia del mes se descubre al cerrar el periodo."""
    edificio = _edificio(db)
    _cargar(db, edificio, fecha=date(2026, 3, 1), monto=Decimal("1.00"))
    _cargar(db, edificio, fecha=date(2026, 3, 31), monto=Decimal("2.00"))
    _cargar(db, edificio, fecha=date(2026, 4, 1), monto=Decimal("4.00"))
    _cargar(db, edificio, fecha=date(2026, 2, 28), monto=Decimal("8.00"))

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/gastos?anio=2026&mes=3",
        headers=como("admin_general"),
    )

    assert respuesta.json()["total"] == "3.00"


def test_el_filtro_de_diciembre_no_se_pasa_de_anio(cliente, como, db):
    """Diciembre es el unico mes cuyo limite de arriba cambia de anio."""
    edificio = _edificio(db)
    _cargar(db, edificio, fecha=date(2026, 12, 31), monto=Decimal("5.00"))
    _cargar(db, edificio, fecha=date(2027, 1, 1), monto=Decimal("7.00"))

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/gastos?anio=2026&mes=12",
        headers=como("admin_general"),
    )

    assert respuesta.json()["total"] == "5.00"


def test_el_filtro_de_febrero_no_necesita_saber_cuantos_dias_tiene(
    cliente, como, db
):
    """2028 es bisiesto: el 29 de febrero existe y tiene que entrar."""
    edificio = _edificio(db)
    _cargar(db, edificio, fecha=date(2028, 2, 29), monto=Decimal("3.00"))

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/gastos?anio=2028&mes=2",
        headers=como("admin_general"),
    )

    assert respuesta.json()["cantidad"] == 1


def test_el_filtro_por_anio_sin_mes_trae_el_anio_entero(cliente, como, db):
    edificio = _edificio(db)
    _cargar(db, edificio, fecha=date(2026, 1, 15), monto=Decimal("1.00"))
    _cargar(db, edificio, fecha=date(2026, 12, 15), monto=Decimal("2.00"))
    _cargar(db, edificio, fecha=date(2025, 12, 31), monto=Decimal("4.00"))

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/gastos?anio=2026",
        headers=como("admin_general"),
    )

    assert respuesta.json()["total"] == "3.00"


def test_el_mes_sin_anio_se_rechaza_con_su_codigo(cliente, como, db):
    """"Los gastos de marzo" de un edificio con tres anios de historia son tres
    marzos distintos."""
    edificio = _edificio(db)

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/gastos?mes=3", headers=como("admin_general")
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "MES_SIN_ANIO"


def test_un_mes_que_no_existe_se_rechaza(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/gastos?anio=2026&mes=13",
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 422


def test_el_filtro_por_rubro(cliente, como, db):
    edificio = _edificio(db)
    _cargar(db, edificio, rubro="limpieza", monto=Decimal("1.00"))
    _cargar(db, edificio, rubro="sueldos", monto=Decimal("2.00"))

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/gastos?rubro=sueldos",
        headers=como("admin_general"),
    )

    cuerpo = respuesta.json()
    assert cuerpo["cantidad"] == 1
    assert cuerpo["total"] == "2.00"


def test_un_rubro_invalido_en_el_filtro_se_rechaza_con_su_codigo(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/gastos?rubro=inventado",
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "RUBRO_INVALIDO"
    assert "limpieza" in respuesta.json()["mensaje"]


def test_el_listado_sale_del_mas_reciente_al_mas_viejo(cliente, como, db):
    edificio = _edificio(db)
    _cargar(db, edificio, fecha=date(2026, 1, 10), monto=Decimal("1.00"))
    _cargar(db, edificio, fecha=date(2026, 6, 10), monto=Decimal("2.00"))

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/gastos", headers=como("admin_general")
    )

    fechas = [gasto["fecha"] for gasto in respuesta.json()["gastos"]]
    assert fechas == ["2026-06-10", "2026-01-10"]


def test_un_edificio_sin_gastos_devuelve_cero_y_no_un_error(cliente, como, db):
    """El estado inicial de todo edificio nuevo. Un 404 aca obligaria a la
    pantalla a tratar lo normal como una excepcion."""
    edificio = _edificio(db)

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/gastos", headers=como("admin_general")
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"total": "0.00", "cantidad": 0, "gastos": []}


# ===========================================================================
# EDICION
# ===========================================================================


def test_editar_solo_el_monto_no_borra_los_demas_campos(cliente, como, db):
    """Es lo que separa un PATCH de un PUT disfrazado: sin `exclude_unset`, los
    campos que no se mandan llegan en `None` y borran lo que habia."""
    edificio = _edificio(db)
    gasto = _cargar(db, edificio, descripcion="Factura 0001-00004521")

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}",
        json={"monto": "175000.00"},
        headers=como("admin_general"),
    )

    cuerpo = respuesta.json()
    assert cuerpo["monto"] == "175000.00"
    assert cuerpo["descripcion"] == "Factura 0001-00004521"
    assert cuerpo["rubro"] == "limpieza"
    assert cuerpo["fecha"] == "2026-11-05"


def test_se_puede_borrar_la_descripcion_mandandola_vacia(cliente, como, db):
    """"No mandaste descripcion" y "mandaste descripcion vacia" son dos cosas
    distintas, y las dos son validas."""
    edificio = _edificio(db)
    gasto = _cargar(db, edificio, descripcion="Algo que no corresponde")

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}",
        json={"descripcion": None},
        headers=como("admin_general"),
    )

    assert respuesta.json()["descripcion"] is None


def test_editar_con_los_mismos_valores_avisa_en_vez_de_guardar(cliente, como, db):
    """Un "guardado" que no guardo nada es la forma mas facil de creer que se
    corrigio algo que sigue mal."""
    edificio = _edificio(db)
    gasto = _cargar(db, edificio)

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}",
        json={"monto": "150000.00"},
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SIN_CAMBIOS"


def test_editar_sin_mandar_nada_avisa(cliente, como, db):
    edificio = _edificio(db)
    gasto = _cargar(db, edificio)

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}",
        json={},
        headers=como("admin_general"),
    )

    assert respuesta.json()["codigo"] == "SIN_CAMBIOS"


def test_editar_el_rubro_a_uno_invalido_se_rechaza(cliente, como, db):
    edificio = _edificio(db)
    gasto = _cargar(db, edificio)

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}",
        json={"rubro": "nada"},
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 422


def test_editar_un_gasto_que_no_existe(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/gastos/9999",
        json={"monto": "1.00"},
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 404


def test_un_residente_no_edita_un_gasto(cliente, como, db):
    edificio = _edificio(db)
    gasto = _cargar(db, edificio)

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}",
        json={"monto": "1.00"},
        headers=como("inquilino"),
    )

    assert respuesta.status_code == 403


# ===========================================================================
# BAJA
# ===========================================================================


def test_borrar_un_gasto(cliente, como, db):
    edificio = _edificio(db)
    gasto = _cargar(db, edificio)
    headers = como("admin_general")

    respuesta = cliente.delete(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}", headers=headers
    )

    assert respuesta.status_code == 204
    listado = cliente.get(f"/api/edificios/{edificio.id}/gastos", headers=headers)
    assert listado.json()["cantidad"] == 0


def test_borrar_dos_veces_el_mismo_gasto_da_404(cliente, como, db):
    """Un doble clic no puede dar 500."""
    edificio = _edificio(db)
    gasto = _cargar(db, edificio)
    headers = como("admin_general")

    cliente.delete(f"/api/edificios/{edificio.id}/gastos/{gasto.id}", headers=headers)
    segunda = cliente.delete(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}", headers=headers
    )

    assert segunda.status_code == 404


def test_un_residente_no_borra_un_gasto(cliente, como, db):
    edificio = _edificio(db)
    gasto = _cargar(db, edificio)

    respuesta = cliente.delete(
        f"/api/edificios/{edificio.id}/gastos/{gasto.id}",
        headers=como("propietario"),
    )

    assert respuesta.status_code == 403


# ===========================================================================
# EL CATALOGO DE RUBROS
# ===========================================================================


def test_el_catalogo_se_sirve_completo_y_en_orden(cliente, como):
    """El orden no es alfabetico: es el de una liquidacion real, de lo que mas
    pesa a lo que menos. Si se sirviera ordenado alfabeticamente, "Sueldos"
    —casi siempre el rubro mas grande— quedaria perdido en el medio."""
    respuesta = cliente.get("/api/gastos/rubros", headers=como("admin_general"))

    cuerpo = respuesta.json()
    assert [r["nombre"] for r in cuerpo] == list(rubros.RUBROS)
    assert cuerpo[0]["etiqueta"] == "Sueldos y cargas sociales"
    assert all(r["descripcion"] for r in cuerpo)


def test_el_catalogo_pide_sesion(cliente):
    respuesta = cliente.get("/api/gastos/rubros")

    assert respuesta.status_code == 401

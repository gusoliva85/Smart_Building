"""Pruebas de `POST /api/edificios` — alta con estructura automatica.

Tres cosas se prueban aca, y la tercera es la que da sentido a la tarea:

  1. El caso permitido: se crea el edificio y su estructura queda generada.
  2. El prohibido: ningun otro rol puede crear un edificio. **Un endpoint sin
     test de 403 es un endpoint sin control de acceso probado.**
  3. La atomicidad: si algo falla a mitad de camino **no queda nada**. Es la
     unica forma de verificar la promesa de "una sola transaccion", y se prueba
     provocando la falla a proposito.
"""

import pytest
from sqlalchemy import select

from app.models.edificio import Departamento, Edificio, Piso
from app.services import autorizacion, finanzas

RUTA = "/api/edificios"

ALTA_MINIMA = {
    "nombre": "Consorcio Rivadavia 1234",
    "direccion": "Av. Rivadavia 1234",
    "cp": "C1033",
    "cantidad_pisos": 7,
    "unidades_por_piso": 4,
}


def _alta(**cambios) -> dict:
    datos = dict(ALTA_MINIMA)
    datos.update(cambios)
    return datos


# ==========================================================================
# EL CASO PERMITIDO
# ==========================================================================


def test_el_administrador_general_crea_un_edificio(cliente, como):
    respuesta = cliente.post(RUTA, json=_alta(), headers=como(autorizacion.ADMIN_GENERAL))

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["edificio"]["nombre"] == "Consorcio Rivadavia 1234"
    assert cuerpo["cantidad_pisos"] == 7
    assert cuerpo["cantidad_departamentos"] == 28


def test_la_estructura_queda_guardada_en_la_base(cliente, como, db):
    cliente.post(RUTA, json=_alta(), headers=como(autorizacion.ADMIN_GENERAL))

    assert len(db.scalars(select(Piso)).all()) == 7
    assert len(db.scalars(select(Departamento)).all()) == 28


def test_los_identificadores_son_los_que_genera_el_servicio(cliente, como):
    respuesta = cliente.post(
        RUTA,
        json=_alta(cantidad_pisos=2, unidades_por_piso=3),
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    pisos = respuesta.json()["pisos"]
    assert [p["numero"] for p in pisos] == [1, 2]
    assert pisos[0]["unidades"] == ["1A", "1B", "1C"]
    assert pisos[1]["unidades"] == ["2A", "2B", "2C"]


def test_las_unidades_nacen_sin_superficie_propietario_ni_coeficiente(cliente, como, db):
    """No es una tarea a medias: un coeficiente inventado reparte plata mal
    sin que nadie lo note, uno ausente lo encuentra la validacion."""
    cliente.post(
        RUTA,
        json=_alta(cantidad_pisos=1, unidades_por_piso=2),
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    for depto in db.scalars(select(Departamento)).all():
        assert depto.m2 is None
        assert depto.coeficiente is None
        assert depto.propietario_id is None
        assert depto.inquilino_id is None
        assert depto.ocupado is False


def test_el_edificio_nace_activo_y_con_su_configuracion_por_defecto(cliente, como):
    cuerpo = cliente.post(
        RUTA, json=_alta(), headers=como(autorizacion.ADMIN_GENERAL)
    ).json()["edificio"]

    assert cuerpo["activo"] is True
    assert 1 <= cuerpo["dias_vencimiento_expensas"] <= 31
    assert sorted(cuerpo["roles_habilitados"]) == sorted(
        autorizacion.ROLES_HABILITABLES
    )
    assert cuerpo["admin_consorcio_id"] is None
    assert cuerpo["encargado_id"] is None
    assert cuerpo["cbu"] is None


def test_un_edificio_de_una_sola_unidad_tambien_se_crea(cliente, como):
    cuerpo = cliente.post(
        RUTA,
        json=_alta(cantidad_pisos=1, unidades_por_piso=1),
        headers=como(autorizacion.ADMIN_GENERAL),
    ).json()

    assert cuerpo["cantidad_departamentos"] == 1
    assert "1 unidad." in cuerpo["mensaje"] or "1 unidad" in cuerpo["mensaje"]


def test_las_coordenadas_se_guardan_cuando_vienen(cliente, como):
    cuerpo = cliente.post(
        RUTA,
        json=_alta(latitud="-34.609722", longitud="-58.392222"),
        headers=como(autorizacion.ADMIN_GENERAL),
    ).json()["edificio"]

    assert cuerpo["latitud"] == "-34.609722"
    assert cuerpo["longitud"] == "-58.392222"


def test_un_edificio_sin_coordenadas_se_crea_igual(cliente, como):
    """`F1-T25`: una direccion que Nominatim no encuentra avisa, no bloquea."""
    cuerpo = cliente.post(
        RUTA, json=_alta(), headers=como(autorizacion.ADMIN_GENERAL)
    ).json()["edificio"]

    assert cuerpo["latitud"] is None
    assert cuerpo["longitud"] is None


def test_dos_edificios_en_la_misma_direccion_se_permiten(cliente, como):
    """Un complejo de dos torres se carga como dos edificios."""
    cabecera = como(autorizacion.ADMIN_GENERAL)
    primero = cliente.post(RUTA, json=_alta(nombre="Torre A"), headers=cabecera)
    segundo = cliente.post(RUTA, json=_alta(nombre="Torre B"), headers=cabecera)

    assert primero.status_code == 201
    assert segundo.status_code == 201


def test_dos_edificios_pueden_compartir_cuit(cliente, como):
    """Un mismo consorcio puede administrar dos torres."""
    cabecera = como(autorizacion.ADMIN_GENERAL)
    primero = cliente.post(
        RUTA, json=_alta(nombre="Torre A", cuit="30-12345678-9"), headers=cabecera
    )
    segundo = cliente.post(
        RUTA, json=_alta(nombre="Torre B", cuit="30-12345678-9"), headers=cabecera
    )

    assert primero.status_code == 201
    assert segundo.status_code == 201


# ==========================================================================
# EL CASO PROHIBIDO
# ==========================================================================


@pytest.mark.parametrize(
    "rol", [r for r in autorizacion.ROLES_ASIGNABLES if r != autorizacion.ADMIN_GENERAL]
)
def test_ningun_otro_rol_puede_crear_un_edificio(cliente, como, rol):
    """Crear un edificio es incorporar un consorcio a la plataforma.

    El Administrador de Consorcio administra el suyo; no decide que edificios
    existen.
    """
    respuesta = cliente.post(RUTA, json=_alta(), headers=como(rol))

    assert respuesta.status_code == 403


def test_sin_autenticacion_no_se_crea_nada(cliente, db):
    respuesta = cliente.post(RUTA, json=_alta())

    assert respuesta.status_code == 401
    assert db.scalars(select(Edificio)).all() == []


def test_un_rol_prohibido_no_deja_ni_el_edificio_ni_la_estructura(cliente, como, db):
    cliente.post(RUTA, json=_alta(), headers=como(autorizacion.PROPIETARIO))

    assert db.scalars(select(Edificio)).all() == []
    assert db.scalars(select(Piso)).all() == []


# ==========================================================================
# VALIDACION DE ENTRADA
# ==========================================================================


@pytest.mark.parametrize(
    "cambios",
    [
        {"cantidad_pisos": 0},
        {"cantidad_pisos": -1},
        {"unidades_por_piso": 0},
        {"unidades_por_piso": -3},
        {"cantidad_pisos": finanzas.MAX_PISOS + 1},
        {"unidades_por_piso": finanzas.MAX_UNIDADES_POR_PISO + 1},
    ],
)
def test_un_tamanio_imposible_devuelve_422(cliente, como, cambios):
    """El tope lo valida el esquema contra las constantes del servicio.

    Asi el error es un 422 que explica el limite, y no un 500 por un
    `ValueError` que se escapo del servicio.
    """
    respuesta = cliente.post(
        RUTA, json=_alta(**cambios), headers=como(autorizacion.ADMIN_GENERAL)
    )

    assert respuesta.status_code == 422


def test_el_tope_exacto_si_se_acepta(cliente, como):
    respuesta = cliente.post(
        RUTA,
        json=_alta(
            cantidad_pisos=finanzas.MAX_PISOS,
            unidades_por_piso=1,
        ),
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["cantidad_pisos"] == finanzas.MAX_PISOS


@pytest.mark.parametrize("campo", ["nombre", "direccion", "cp"])
def test_un_campo_obligatorio_con_solo_espacios_devuelve_422(cliente, como, campo):
    """Sin esto quedaria guardado un nombre en blanco: la fila existe, el
    listado muestra un renglon vacio y nadie sabe que edificio es."""
    respuesta = cliente.post(
        RUTA, json=_alta(**{campo: "   "}), headers=como(autorizacion.ADMIN_GENERAL)
    )

    assert respuesta.status_code == 422


@pytest.mark.parametrize("campo", ["nombre", "direccion", "cp", "cantidad_pisos"])
def test_un_campo_obligatorio_que_falta_devuelve_422(cliente, como, campo):
    datos = _alta()
    del datos[campo]

    respuesta = cliente.post(
        RUTA, json=datos, headers=como(autorizacion.ADMIN_GENERAL)
    )

    assert respuesta.status_code == 422


def test_un_campo_desconocido_devuelve_422_y_no_se_descarta_en_silencio(cliente, como):
    """Un `direcion` por `direccion` tiene que ser un error, no un 201 sin
    haber guardado la direccion."""
    respuesta = cliente.post(
        RUTA,
        json=_alta(cantidad_de_pisos=7),
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 422


@pytest.mark.parametrize(
    "cambios",
    [
        {"latitud": "91"},
        {"latitud": "-91"},
        {"longitud": "181"},
        {"longitud": "-181"},
    ],
)
def test_una_coordenada_fuera_del_planeta_devuelve_422(cliente, como, cambios):
    respuesta = cliente.post(
        RUTA, json=_alta(**cambios), headers=como(autorizacion.ADMIN_GENERAL)
    )

    assert respuesta.status_code == 422


def test_los_espacios_de_sobra_se_recortan(cliente, como):
    cuerpo = cliente.post(
        RUTA,
        json=_alta(nombre="  Torre Norte  ", cp=" C1033 "),
        headers=como(autorizacion.ADMIN_GENERAL),
    ).json()["edificio"]

    assert cuerpo["nombre"] == "Torre Norte"
    assert cuerpo["cp"] == "C1033"


def test_un_cuit_vacio_se_guarda_como_sin_cargar(cliente, como):
    """Cadena vacia y NULL serian dos formas de decir "no hay dato", y el dia
    que una consulta pregunte por una sola, la mitad de las filas no aparece."""
    cuerpo = cliente.post(
        RUTA, json=_alta(cuit="   "), headers=como(autorizacion.ADMIN_GENERAL)
    ).json()["edificio"]

    assert cuerpo["cuit"] is None


# ==========================================================================
# LA ATOMICIDAD — LO QUE DA SENTIDO A LA TAREA
# ==========================================================================


def test_si_la_estructura_falla_no_queda_ni_el_edificio(
    cliente, como, db, monkeypatch
):
    """La promesa de "una sola transaccion", verificada provocando la falla.

    Se fuerza una estructura con dos unidades del MISMO identificador en el
    mismo piso, que la restriccion de unicidad de `departamentos` rechaza. El
    edificio ya estaba agregado a la sesion cuando eso pasa, asi que si el
    alta no fuera una sola transaccion quedaria un edificio sin estructura — y
    la persona, que vio un error, lo cargaria de nuevo y tendria dos.
    """
    from app.routers import edificios as router_edificios

    def estructura_rota(cantidad_pisos, unidades_por_piso):
        unidad = finanzas.UnidadProyectada(identificador="1A", orden=1)
        return (
            finanzas.PisoProyectado(
                numero=1, orden=1, unidades=(unidad, unidad)
            ),
        )

    monkeypatch.setattr(
        router_edificios.finanzas, "generar_estructura", estructura_rota
    )

    respuesta = cliente.post(
        RUTA, json=_alta(), headers=como(autorizacion.ADMIN_GENERAL)
    )

    assert respuesta.status_code == 500
    assert db.scalars(select(Edificio)).all() == []
    assert db.scalars(select(Piso)).all() == []
    assert db.scalars(select(Departamento)).all() == []


def test_el_error_de_la_atomicidad_no_filtra_nombres_de_tablas(
    cliente, como, monkeypatch
):
    """Regla `FX-T11`: ningun mensaje de error nombra tablas ni columnas."""
    from app.routers import edificios as router_edificios

    def estructura_rota(cantidad_pisos, unidades_por_piso):
        unidad = finanzas.UnidadProyectada(identificador="1A", orden=1)
        return (
            finanzas.PisoProyectado(
                numero=1, orden=1, unidades=(unidad, unidad)
            ),
        )

    monkeypatch.setattr(
        router_edificios.finanzas, "generar_estructura", estructura_rota
    )

    detalle = cliente.post(
        RUTA, json=_alta(), headers=como(autorizacion.ADMIN_GENERAL)
    ).json()["detail"]

    for palabra in ("departamentos", "pisos", "edificios", "UNIQUE", "SELECT"):
        assert palabra not in detalle

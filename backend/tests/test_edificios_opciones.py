"""Pruebas de los dos accesos que necesita la pantalla de detalle (`F1-T26`).

- ``GET /api/edificios/opciones`` — los catalogos y los topes con los que la
  pantalla arma sus formularios.
- ``GET /api/edificios/{id}/asignables`` — los candidatos de cada puesto y de
  cada unidad, para elegir de una lista en vez de escribir un id.

Los dos existen por el mismo motivo y es el motivo que hay que probar: **los
valores que son reglas del sistema no se escriben en el JavaScript.** Los tipos
de cochera, los roles habilitables y los topes de la generacion automatica
viven en el backend, y si la pantalla los repitiera, el dia que cambie uno
habria dos respuestas distintas a la misma pregunta.

El segundo tiene ademas una regla propia que es la mitad de su valor: **no
puede ofrecer una opcion que el backend vaya a rechazar.** Un usuario
desactivado, uno con otro rol, o un residente de un rol que este edificio no
habilita son todos pedidos que fallan, asi que no entran en la lista.
"""

import pytest
from sqlalchemy import select

from app.models.edificio import Edificio
from app.models.usuario import Usuario
from app.models import edificio as modelo_edificio
from app.services import autorizacion, finanzas

RUTA_OPCIONES = "/api/edificios/opciones"

# Los roles que no son ninguno de los dos administradores: ninguno de estos
# puede ver estos dos endpoints.
ROLES_SIN_ACCESO = [
    rol
    for rol in autorizacion.ROLES_ASIGNABLES
    if rol not in (autorizacion.ADMIN_GENERAL, autorizacion.ADMIN_CONSORCIO)
]


def _edificio(db, nombre: str = "Consorcio Mitre 500", **columnas) -> Edificio:
    edificio = Edificio(
        nombre=nombre,
        direccion="Mitre 500",
        cp="C1000",
        **columnas,
    )
    db.add(edificio)
    db.commit()
    return edificio


def _usuario(db, rol: str, nombre: str, activo: bool = True) -> Usuario:
    usuario = Usuario(
        nombre=nombre,
        email=f"{nombre.lower().replace(' ', '')}-{rol}@prueba.com.ar",
        password_hash="x",
        rol=rol,
        activo=activo,
    )
    db.add(usuario)
    db.commit()
    return usuario


def _admin_consorcio_logueado(db, como) -> tuple[dict, Usuario]:
    headers = como(autorizacion.ADMIN_CONSORCIO)
    usuario = db.scalars(
        select(Usuario)
        .where(Usuario.rol == autorizacion.ADMIN_CONSORCIO)
        .order_by(Usuario.id.desc())
    ).first()
    return headers, usuario


# ===========================================================================
# GET /api/edificios/opciones
# ===========================================================================


def test_las_opciones_piden_sesion(cliente):
    assert cliente.get(RUTA_OPCIONES).status_code == 401


def test_el_administrador_general_ve_las_opciones(cliente, como):
    respuesta = cliente.get(RUTA_OPCIONES, headers=como(autorizacion.ADMIN_GENERAL))

    assert respuesta.status_code == 200


def test_el_administrador_de_consorcio_tambien_ve_las_opciones(cliente, como):
    """Es el punto del endpoint, no un permiso de mas.

    El de Consorcio configura los roles habilitados de su edificio (`F1-T22`) y
    carga sus cocheras (`F1-T23`). Si los catalogos fueran exclusivos del
    Administrador General, su pantalla quedaria sin las dos cosas.
    """
    respuesta = cliente.get(RUTA_OPCIONES, headers=como(autorizacion.ADMIN_CONSORCIO))

    assert respuesta.status_code == 200


@pytest.mark.parametrize("rol", ROLES_SIN_ACCESO)
def test_los_demas_roles_no_ven_las_opciones(cliente, como, rol):
    assert cliente.get(RUTA_OPCIONES, headers=como(rol)).status_code == 403


def test_los_tipos_de_cochera_son_los_del_modelo(cliente, como):
    cuerpo = cliente.get(
        RUTA_OPCIONES, headers=como(autorizacion.ADMIN_GENERAL)
    ).json()

    assert cuerpo["tipos_cochera"] == list(modelo_edificio.TIPOS_COCHERA)


def test_los_topes_son_los_del_servicio(cliente, como):
    """Si la pantalla dijera un tope y el servidor aplicara otro, el formulario
    prometeria algo que el alta rechaza."""
    cuerpo = cliente.get(
        RUTA_OPCIONES, headers=como(autorizacion.ADMIN_GENERAL)
    ).json()

    assert cuerpo["max_pisos"] == finanzas.MAX_PISOS
    assert cuerpo["max_unidades_por_piso"] == finanzas.MAX_UNIDADES_POR_PISO


def test_los_roles_habilitables_son_los_siete_y_no_incluyen_al_general(cliente, como):
    """`admin_general` queda afuera: su alcance es la cartera entera y no se
    habilita edificio por edificio."""
    cuerpo = cliente.get(
        RUTA_OPCIONES, headers=como(autorizacion.ADMIN_GENERAL)
    ).json()

    nombres = [rol["nombre"] for rol in cuerpo["roles_habilitables"]]

    assert nombres == list(autorizacion.ROLES_HABILITABLES)
    assert autorizacion.ADMIN_GENERAL not in nombres


def test_cada_rol_habilitable_viaja_con_su_etiqueta_legible(cliente, como):
    """La pantalla muestra "Administrador de Consorcio", no `admin_consorcio`."""
    cuerpo = cliente.get(
        RUTA_OPCIONES, headers=como(autorizacion.ADMIN_GENERAL)
    ).json()

    for rol in cuerpo["roles_habilitables"]:
        assert rol["etiqueta"]
        assert rol["etiqueta"] == autorizacion.etiqueta(rol["nombre"])
        assert rol["etiqueta"] != rol["nombre"]


def test_la_ruta_literal_no_la_captura_el_detalle(cliente, como):
    """`/opciones` esta declarada antes que `/{edificio_id}`.

    Si quedara despues, este pedido entraria por el detalle con
    `edificio_id="opciones"` y devolveria un 422 de tipo invalido, que no
    menciona en ningun momento el problema real.
    """
    respuesta = cliente.get(RUTA_OPCIONES, headers=como(autorizacion.ADMIN_GENERAL))

    assert respuesta.status_code == 200
    assert "tipos_cochera" in respuesta.json()


# ===========================================================================
# GET /api/edificios/{id}/asignables
# ===========================================================================


def _ruta_asignables(edificio_id: int) -> str:
    return f"/api/edificios/{edificio_id}/asignables"


def test_los_asignables_piden_sesion(cliente, db):
    edificio = _edificio(db)

    assert cliente.get(_ruta_asignables(edificio.id)).status_code == 401


@pytest.mark.parametrize("rol", ROLES_SIN_ACCESO)
def test_los_demas_roles_no_ven_los_asignables(cliente, db, como, rol):
    edificio = _edificio(db)

    respuesta = cliente.get(_ruta_asignables(edificio.id), headers=como(rol))

    assert respuesta.status_code == 403


def test_un_edificio_que_no_existe_da_404(cliente, como):
    respuesta = cliente.get(
        _ruta_asignables(9999), headers=como(autorizacion.ADMIN_GENERAL)
    )

    assert respuesta.status_code == 404


def test_un_edificio_ajeno_da_404_igual_que_uno_inexistente(cliente, db, como):
    """El alcance no se filtra con un 403: un edificio fuera del alcance
    contesta exactamente como uno que no existe, asi que los ids no se pueden
    tantear."""
    headers, _ = _admin_consorcio_logueado(db, como)
    ajeno = _edificio(db, nombre="Consorcio de otro")

    respuesta = cliente.get(_ruta_asignables(ajeno.id), headers=headers)

    assert respuesta.status_code == 404


def test_trae_los_responsables_posibles_de_los_dos_puestos(cliente, db, como):
    _usuario(db, autorizacion.ADMIN_CONSORCIO, "Candidata Admin")
    _usuario(db, autorizacion.ENCARGADO, "Candidato Encargado")
    edificio = _edificio(db)

    cuerpo = cliente.get(
        _ruta_asignables(edificio.id), headers=como(autorizacion.ADMIN_GENERAL)
    ).json()

    assert "Candidata Admin" in [u["nombre"] for u in cuerpo["admin_consorcio"]]
    assert "Candidato Encargado" in [u["nombre"] for u in cuerpo["encargado"]]


def test_no_trae_usuarios_desactivados(cliente, db, como):
    """Asignar a alguien desactivado lo rechaza el backend, asi que ofrecerlo
    seria ofrecer algo que va a fallar."""
    _usuario(db, autorizacion.ENCARGADO, "Encargado Dado De Baja", activo=False)
    edificio = _edificio(db)

    cuerpo = cliente.get(
        _ruta_asignables(edificio.id), headers=como(autorizacion.ADMIN_GENERAL)
    ).json()

    nombres = [u["nombre"] for u in cuerpo["encargado"]]
    assert "Encargado Dado De Baja" not in nombres


def test_no_mezcla_los_roles(cliente, db, como):
    _usuario(db, autorizacion.PROPIETARIO, "Solo Propietario")
    edificio = _edificio(db)

    cuerpo = cliente.get(
        _ruta_asignables(edificio.id), headers=como(autorizacion.ADMIN_GENERAL)
    ).json()

    assert "Solo Propietario" not in [u["nombre"] for u in cuerpo["encargado"]]
    assert "Solo Propietario" in [u["nombre"] for u in cuerpo["propietario"]]


def test_los_residentes_vienen_vacios_si_ese_rol_no_esta_habilitado(cliente, db, como):
    """Asignar un residente exige que su rol este habilitado en ESE edificio
    (`F1-T23`). Si no lo esta, el desplegable tiene que venir vacio."""
    _usuario(db, autorizacion.PROPIETARIO, "Propietaria Posible")
    _usuario(db, autorizacion.INQUILINO, "Inquilino Posible")
    edificio = _edificio(db, roles_habilitados=[autorizacion.ENCARGADO])

    cuerpo = cliente.get(
        _ruta_asignables(edificio.id), headers=como(autorizacion.ADMIN_GENERAL)
    ).json()

    assert cuerpo["propietario"] == []
    assert cuerpo["inquilino"] == []


def test_los_puestos_no_dependen_de_los_roles_habilitados(cliente, db, como):
    """Administrar un edificio o estar a cargo de el no es un rol que el
    edificio habilite, asi que los dos puestos vienen igual."""
    _usuario(db, autorizacion.ADMIN_CONSORCIO, "Admin Igual")
    _usuario(db, autorizacion.ENCARGADO, "Encargado Igual")
    edificio = _edificio(db, roles_habilitados=[autorizacion.PROPIETARIO])

    cuerpo = cliente.get(
        _ruta_asignables(edificio.id), headers=como(autorizacion.ADMIN_GENERAL)
    ).json()

    assert "Admin Igual" in [u["nombre"] for u in cuerpo["admin_consorcio"]]
    assert "Encargado Igual" in [u["nombre"] for u in cuerpo["encargado"]]


def test_con_el_rol_habilitado_los_residentes_aparecen(cliente, db, como):
    _usuario(db, autorizacion.PROPIETARIO, "Propietaria Habilitada")
    edificio = _edificio(
        db, roles_habilitados=[autorizacion.PROPIETARIO, autorizacion.INQUILINO]
    )

    cuerpo = cliente.get(
        _ruta_asignables(edificio.id), headers=como(autorizacion.ADMIN_GENERAL)
    ).json()

    assert "Propietaria Habilitada" in [u["nombre"] for u in cuerpo["propietario"]]


def test_cada_candidato_viaja_con_su_email(cliente, db, como):
    """Dos personas pueden llamarse igual: el email es con lo que quien asigna
    las distingue."""
    usuario = _usuario(db, autorizacion.ENCARGADO, "Con Email")
    edificio = _edificio(db)

    cuerpo = cliente.get(
        _ruta_asignables(edificio.id), headers=como(autorizacion.ADMIN_GENERAL)
    ).json()

    candidato = next(u for u in cuerpo["encargado"] if u["id"] == usuario.id)
    assert candidato["email"] == usuario.email


def test_no_viaja_el_hash_de_la_contrasenia(cliente, db, como):
    """El esquema declara tres campos y nada mas: un listado de usuarios que
    arrastre columnas de mas es como se filtra lo que no se queria exponer."""
    _usuario(db, autorizacion.ENCARGADO, "Sin Hash")
    edificio = _edificio(db)

    cuerpo = cliente.get(
        _ruta_asignables(edificio.id), headers=como(autorizacion.ADMIN_GENERAL)
    ).json()

    for lista in cuerpo.values():
        for candidato in lista:
            assert set(candidato) == {"id", "nombre", "email"}


def test_los_candidatos_vienen_ordenados_por_nombre(cliente, db, como):
    _usuario(db, autorizacion.ENCARGADO, "Zulema Zeta")
    _usuario(db, autorizacion.ENCARGADO, "Ana Alfa")
    edificio = _edificio(db)

    cuerpo = cliente.get(
        _ruta_asignables(edificio.id), headers=como(autorizacion.ADMIN_GENERAL)
    ).json()

    nombres = [u["nombre"] for u in cuerpo["encargado"]]
    assert nombres == sorted(nombres)


def test_el_administrador_de_consorcio_ve_los_de_su_edificio(cliente, db, como):
    """Es el caso que motiva el endpoint: sin esto no tiene de donde sacar la
    lista, porque `GET /api/usuarios` es exclusivo del Administrador General."""
    headers, usuario = _admin_consorcio_logueado(db, como)
    _usuario(db, autorizacion.PROPIETARIO, "Propietaria Del Suyo")
    edificio = _edificio(db, admin_consorcio_id=usuario.id)

    respuesta = cliente.get(_ruta_asignables(edificio.id), headers=headers)

    assert respuesta.status_code == 200
    nombres = [u["nombre"] for u in respuesta.json()["propietario"]]
    assert "Propietaria Del Suyo" in nombres

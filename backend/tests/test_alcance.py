"""Pruebas del alcance: sobre que edificios opera cada usuario (`F1-T23`).

`services/autorizacion.py` responde **que puede hacer un rol**;
`core/alcance.py` responde **sobre que edificios**. Esta segunda mitad nace con
`F1-T23`, que es la primera tarea con un endpoint que no es admin-only: el
listado de espacios comunes.

Se prueba a traves de ese endpoint y no llamando a la funcion suelta, a
proposito. Lo que importa no es que `puede_ver()` devuelva el booleano
correcto, sino que la persona que entra a reportar un reclamo sobre el SUM vea
la lista — y que la de otro edificio no. Eso solo lo prueba el endpoint.

**El error que estas pruebas existen para que no se repita:** en la iteracion
anterior este listado quedo restringido a administradores y dejo sin poder
reportar un reclamo sobre un espacio comun a Propietario, Inquilino y Encargado,
que son justamente los que estan ahi. Se descubrio recien en la Fase 3.
"""

import pytest

from app.models.edificio import Departamento, Edificio, EspacioComun, Piso
from app.models.usuario import AsignacionEdificio, Usuario
from app.services import autorizacion


def _edificio(db, nombre: str = "Consorcio Mitre 500", **columnas) -> Edificio:
    edificio = Edificio(nombre=nombre, direccion="Mitre 500", cp="C1000", **columnas)
    db.add(edificio)
    db.commit()
    db.add(EspacioComun(edificio_id=edificio.id, nombre="SUM", capacidad=40))
    db.commit()
    return edificio


def _ruta(edificio_id: int) -> str:
    return f"/api/edificios/{edificio_id}/espacios-comunes"


def _ultimo(db, rol: str) -> Usuario:
    """El usuario que `como(rol)` acaba de crear y autenticar."""
    from sqlalchemy import select

    return db.scalars(
        select(Usuario).where(Usuario.rol == rol).order_by(Usuario.id.desc())
    ).first()


def _con_unidad(db, edificio: Edificio, usuario: Usuario, campo: str) -> None:
    piso = Piso(edificio_id=edificio.id, numero=1, orden=1)
    db.add(piso)
    db.commit()
    db.add(Departamento(piso_id=piso.id, identificador="1A", **{campo: usuario.id}))
    db.commit()


# ==========================================================================
# QUIEN SI VE LOS ESPACIOS COMUNES
# ==========================================================================


def test_el_administrador_general_ve_los_de_cualquier_edificio(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.get(_ruta(edificio.id), headers=como(autorizacion.ADMIN_GENERAL))

    assert respuesta.status_code == 200
    assert [e["nombre"] for e in respuesta.json()] == ["SUM"]


def test_el_administrador_de_consorcio_ve_los_de_su_edificio(cliente, como, db):
    headers = como(autorizacion.ADMIN_CONSORCIO)
    admin = _ultimo(db, autorizacion.ADMIN_CONSORCIO)
    edificio = _edificio(db, admin_consorcio_id=admin.id)

    assert cliente.get(_ruta(edificio.id), headers=headers).status_code == 200


def test_el_encargado_ve_los_del_edificio_donde_trabaja(cliente, como, db):
    """Uno de los tres roles que la iteracion anterior bloqueo sin querer."""
    headers = como(autorizacion.ENCARGADO)
    encargado = _ultimo(db, autorizacion.ENCARGADO)
    edificio = _edificio(db, encargado_id=encargado.id)

    assert cliente.get(_ruta(edificio.id), headers=headers).status_code == 200


def test_el_propietario_ve_los_del_edificio_donde_tiene_una_unidad(cliente, como, db):
    headers = como(autorizacion.PROPIETARIO)
    propietario = _ultimo(db, autorizacion.PROPIETARIO)
    edificio = _edificio(db)
    _con_unidad(db, edificio, propietario, "propietario_id")

    assert cliente.get(_ruta(edificio.id), headers=headers).status_code == 200


def test_el_inquilino_ve_los_del_edificio_donde_vive(cliente, como, db):
    headers = como(autorizacion.INQUILINO)
    inquilino = _ultimo(db, autorizacion.INQUILINO)
    edificio = _edificio(db)
    _con_unidad(db, edificio, inquilino, "inquilino_id")

    assert cliente.get(_ruta(edificio.id), headers=headers).status_code == 200


@pytest.mark.parametrize("rol", [autorizacion.SEGURIDAD, autorizacion.AUDITOR])
def test_seguridad_y_auditor_ven_los_de_los_edificios_que_tienen_asignados(
    cliente, como, db, rol
):
    """Su alcance no sale de una columna del edificio sino de
    `asignacion_edificio`: un edificio tiene un solo administrador y un solo
    encargado, pero varios agentes de seguridad (son turnos)."""
    headers = como(rol)
    usuario = _ultimo(db, rol)
    edificio = _edificio(db)
    db.add(AsignacionEdificio(usuario_id=usuario.id, edificio_id=edificio.id))
    db.commit()

    assert cliente.get(_ruta(edificio.id), headers=headers).status_code == 200


# ==========================================================================
# QUIEN NO
# ==========================================================================


def test_el_administrador_de_consorcio_no_ve_los_de_un_edificio_ajeno(cliente, como, db):
    headers = como(autorizacion.ADMIN_CONSORCIO)
    ajeno = _edificio(db, "De otro")

    assert cliente.get(_ruta(ajeno.id), headers=headers).status_code == 404


def test_el_encargado_no_ve_los_de_un_edificio_donde_no_trabaja(cliente, como, db):
    headers = como(autorizacion.ENCARGADO)
    ajeno = _edificio(db, "De otro")

    assert cliente.get(_ruta(ajeno.id), headers=headers).status_code == 404


def test_el_propietario_no_ve_los_de_un_edificio_donde_no_tiene_nada(cliente, como, db):
    headers = como(autorizacion.PROPIETARIO)
    propietario = _ultimo(db, autorizacion.PROPIETARIO)
    suyo = _edificio(db, "El suyo")
    ajeno = _edificio(db, "De otro")
    _con_unidad(db, suyo, propietario, "propietario_id")

    assert cliente.get(_ruta(suyo.id), headers=headers).status_code == 200
    assert cliente.get(_ruta(ajeno.id), headers=headers).status_code == 404


def test_un_propietario_sin_ninguna_unidad_no_ve_nada(cliente, como, db):
    """El caso de la cuenta recien creada a la que todavia no le asignaron la
    unidad: tiene el rol, pero no tiene edificio."""
    headers = como(autorizacion.PROPIETARIO)
    edificio = _edificio(db)

    assert cliente.get(_ruta(edificio.id), headers=headers).status_code == 404


def test_seguridad_sin_asignacion_no_ve_nada(cliente, como, db):
    headers = como(autorizacion.SEGURIDAD)
    edificio = _edificio(db)

    assert cliente.get(_ruta(edificio.id), headers=headers).status_code == 404


def test_el_proveedor_no_ve_los_espacios_comunes(cliente, como, db):
    """Queda afuera a proposito: su alcance en la matriz es `ots_asignadas`, o
    sea que llega a un edificio por una orden de trabajo y no por el edificio
    en si. Cuando existan las ordenes (Fase 5), el permiso sale de la orden."""
    headers = como(autorizacion.PROVEEDOR)
    edificio = _edificio(db)

    assert cliente.get(_ruta(edificio.id), headers=headers).status_code == 404


def test_una_cuenta_pendiente_no_ve_nada(cliente, como, db):
    """`pendiente` es una cuenta que existe y todavia no tiene rol real."""
    headers = como(autorizacion.PENDIENTE)
    edificio = _edificio(db)

    assert cliente.get(_ruta(edificio.id), headers=headers).status_code == 404


def test_sin_autenticacion_es_401_y_no_404(cliente, db):
    """La distincion importa: el envoltorio de `fetch` del frontend trata el
    401 limpiando la sesion y mandando al login."""
    edificio = _edificio(db)

    assert cliente.get(_ruta(edificio.id)).status_code == 401


def test_un_edificio_sin_acceso_responde_igual_que_uno_inexistente(cliente, como, db):
    """Un 403 distinguible le iria contando que edificios hay probando ids."""
    headers = como(autorizacion.PROPIETARIO)
    ajeno = _edificio(db, "De otro")

    sin_acceso = cliente.get(_ruta(ajeno.id), headers=headers)
    inexistente = cliente.get(_ruta(9999), headers=headers)

    assert sin_acceso.status_code == 404
    assert sin_acceso.json() == inexistente.json()


# ==========================================================================
# VER NO ES ESCRIBIR
# ==========================================================================


@pytest.mark.parametrize(
    "rol",
    [
        autorizacion.ENCARGADO,
        autorizacion.PROPIETARIO,
        autorizacion.INQUILINO,
        autorizacion.SEGURIDAD,
    ],
)
def test_quien_ve_un_espacio_comun_no_puede_crearlo(cliente, como, db, rol):
    """"Crear un espacio comun si es exclusivo del administrador; verlo, no."

    Es la frase del Roadmap, y las dos mitades necesitan su test: sin la
    primera el listado queda admin-only otra vez, sin la segunda cualquier
    residente agrega un quincho.
    """
    headers = como(rol)
    usuario = _ultimo(db, rol)
    edificio = _edificio(db, encargado_id=usuario.id if rol == autorizacion.ENCARGADO else None)
    if rol in (autorizacion.PROPIETARIO, autorizacion.INQUILINO):
        _con_unidad(db, edificio, usuario, f"{rol}_id")
    if rol == autorizacion.SEGURIDAD:
        db.add(AsignacionEdificio(usuario_id=usuario.id, edificio_id=edificio.id))
        db.commit()

    # Lo ve...
    assert cliente.get(_ruta(edificio.id), headers=headers).status_code == 200
    # ...y no lo crea.
    respuesta = cliente.post(
        _ruta(edificio.id), json={"nombre": "Quincho"}, headers=headers
    )
    assert respuesta.status_code == 403

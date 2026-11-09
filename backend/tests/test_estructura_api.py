"""Pruebas del CRUD anidado de la estructura (`F1-T23`).

Trece endpoints bajo `/api/edificios/{id}/...`. Lo que se prueba, en este
orden:

  1. **El anidado es un permiso, no una decoracion.** Pedir el piso de un
     edificio pasando el id de otro tiene que dar 404 aunque los dos ids
     existan. Hay un test por cada entidad, porque este es el agujero que no se
     ve leyendo un endpoint: se ve comparandolo con los otros doce.
  2. **Lo que cuelga se desarma antes de borrar:** un piso con unidades y una
     unidad con residente o con cochera no se borran.
  3. **La asignacion de residentes valida cuatro cosas**, y la cuarta —que el
     rol este habilitado en ESE edificio— es la que le da sentido a
     `roles_habilitados` de `F1-T22`.
  4. **La regla "un inquilino, una sola unidad"**, con el mensaje que dice en
     que unidad ya figura.
  5. **El caso permitido y el prohibido de cada endpoint.**
"""

import pytest
from sqlalchemy import select

from app.models.edificio import Cochera, Departamento, Edificio, EspacioComun, Piso
from app.models.usuario import Usuario
from app.services import autorizacion


def _edificio(db, nombre: str = "Consorcio Mitre 500", **columnas) -> Edificio:
    edificio = Edificio(nombre=nombre, direccion="Mitre 500", cp="C1000", **columnas)
    db.add(edificio)
    db.commit()
    return edificio


def _piso(db, edificio: Edificio, numero: int = 1, orden: int | None = None) -> Piso:
    piso = Piso(edificio_id=edificio.id, numero=numero, orden=orden or numero)
    db.add(piso)
    db.commit()
    return piso


def _departamento(db, piso: Piso, identificador: str = "1A", **columnas) -> Departamento:
    departamento = Departamento(
        piso_id=piso.id, identificador=identificador, **columnas
    )
    db.add(departamento)
    db.commit()
    return departamento


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


def _admin(como) -> dict:
    return como(autorizacion.ADMIN_GENERAL)


def ruta_pisos(edificio_id: int) -> str:
    return f"/api/edificios/{edificio_id}/pisos"


def ruta_deptos(edificio_id: int, piso_id: int) -> str:
    return f"/api/edificios/{edificio_id}/pisos/{piso_id}/departamentos"


def ruta_depto(edificio_id: int, departamento_id: int) -> str:
    return f"/api/edificios/{edificio_id}/departamentos/{departamento_id}"


def ruta_cocheras(edificio_id: int) -> str:
    return f"/api/edificios/{edificio_id}/cocheras"


def ruta_espacios(edificio_id: int) -> str:
    return f"/api/edificios/{edificio_id}/espacios-comunes"


# ==========================================================================
# PISOS
# ==========================================================================


def test_agrega_un_piso(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.post(ruta_pisos(edificio.id), json={"numero": 1}, headers=_admin(como))

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["numero"] == 1
    assert cuerpo["orden"] == 1
    assert cuerpo["departamentos"] == []


def test_un_piso_sin_orden_va_arriba_del_ultimo(cliente, como, db):
    """Es el caso normal —se construyo una planta mas— y evita que quien carga
    tenga que saber como se numera internamente."""
    edificio = _edificio(db)
    _piso(db, edificio, numero=1, orden=1)
    _piso(db, edificio, numero=2, orden=2)

    respuesta = cliente.post(
        ruta_pisos(edificio.id), json={"numero": 3}, headers=_admin(como)
    )

    assert respuesta.json()["orden"] == 3


def test_el_primer_piso_de_un_edificio_vacio_queda_en_la_posicion_uno(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.post(
        ruta_pisos(edificio.id), json={"numero": 0}, headers=_admin(como)
    )

    assert respuesta.json()["orden"] == 1


def test_un_piso_puede_ser_la_planta_baja_o_un_subsuelo(cliente, como, db):
    """El numero del piso no empieza en 1: la planta baja se llama 0 y un
    subsuelo, -1."""
    edificio = _edificio(db)
    headers = _admin(como)

    for numero in (0, -1):
        respuesta = cliente.post(
            ruta_pisos(edificio.id), json={"numero": numero}, headers=headers
        )
        assert respuesta.status_code == 201, numero


def test_un_numero_de_piso_repetido_se_rechaza(cliente, como, db):
    edificio = _edificio(db)
    _piso(db, edificio, numero=5)

    respuesta = cliente.post(
        ruta_pisos(edificio.id), json={"numero": 5}, headers=_admin(como)
    )

    assert respuesta.status_code == 400
    assert "piso 5" in respuesta.json()["detail"]


def test_una_posicion_de_piso_repetida_se_rechaza(cliente, como, db):
    edificio = _edificio(db)
    _piso(db, edificio, numero=1, orden=1)

    respuesta = cliente.post(
        ruta_pisos(edificio.id), json={"numero": 2, "orden": 1}, headers=_admin(como)
    )

    assert respuesta.status_code == 400


def test_el_duplicado_es_400_y_no_409(cliente, como, db):
    """El 409 esta reservado: el envoltorio de `fetch` del frontend lo mapea a
    `error.necesitaConfirmacion` y abre un dialogo de "¿seguro?". Un piso
    repetido no es algo que se pueda confirmar."""
    edificio = _edificio(db)
    _piso(db, edificio, numero=1)

    respuesta = cliente.post(
        ruta_pisos(edificio.id), json={"numero": 1}, headers=_admin(como)
    )

    assert respuesta.status_code == 400


def test_edita_el_numero_de_un_piso(cliente, como, db):
    edificio = _edificio(db)
    piso = _piso(db, edificio, numero=13)

    respuesta = cliente.patch(
        f"{ruta_pisos(edificio.id)}/{piso.id}",
        json={"numero": 14},
        headers=_admin(como),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["numero"] == 14


def test_editar_un_piso_sin_campos_se_rechaza(cliente, como, db):
    edificio = _edificio(db)
    piso = _piso(db, edificio)

    respuesta = cliente.patch(
        f"{ruta_pisos(edificio.id)}/{piso.id}", json={}, headers=_admin(como)
    )

    assert respuesta.status_code == 422


def test_borra_un_piso_vacio(cliente, como, db):
    edificio = _edificio(db)
    piso = _piso(db, edificio)

    respuesta = cliente.delete(
        f"{ruta_pisos(edificio.id)}/{piso.id}", headers=_admin(como)
    )

    assert respuesta.status_code == 204
    assert db.scalars(select(Piso)).all() == []


def test_no_borra_un_piso_que_tiene_unidades(cliente, como, db):
    """No hay borrado en cascada, y es una decision de `F1-T19`: un
    departamento puede tener expensas y pagos apuntandole."""
    edificio = _edificio(db)
    piso = _piso(db, edificio)
    _departamento(db, piso, "1A")
    _departamento(db, piso, "1B")

    respuesta = cliente.delete(
        f"{ruta_pisos(edificio.id)}/{piso.id}", headers=_admin(como)
    )

    assert respuesta.status_code == 400
    assert "2 unidades" in respuesta.json()["detail"]
    assert len(db.scalars(select(Piso)).all()) == 1


def test_el_mensaje_de_una_sola_unidad_esta_en_singular(cliente, como, db):
    edificio = _edificio(db)
    piso = _piso(db, edificio)
    _departamento(db, piso, "1A")

    respuesta = cliente.delete(
        f"{ruta_pisos(edificio.id)}/{piso.id}", headers=_admin(como)
    )

    assert "1 unidad." in respuesta.json()["detail"]


# ==========================================================================
# EL ANIDADO ES UN PERMISO
# ==========================================================================


def test_un_piso_de_otro_edificio_es_404(cliente, como, db):
    """El agujero que esta tarea tiene que no tener.

    Si la busqueda del hijo no llevara la condicion del padre, pasar el id del
    edificio propio y el id de un piso ajeno dejaria editar la estructura de
    otro consorcio.
    """
    mio = _edificio(db, "El mio")
    ajeno = _edificio(db, "De otro")
    piso_ajeno = _piso(db, ajeno, numero=1)

    respuesta = cliente.patch(
        f"{ruta_pisos(mio.id)}/{piso_ajeno.id}",
        json={"numero": 99},
        headers=_admin(como),
    )

    assert respuesta.status_code == 404
    db.refresh(piso_ajeno)
    assert piso_ajeno.numero == 1


def test_una_unidad_de_otro_edificio_es_404(cliente, como, db):
    mio = _edificio(db, "El mio")
    ajeno = _edificio(db, "De otro")
    depto_ajeno = _departamento(db, _piso(db, ajeno), "1A")

    respuesta = cliente.patch(
        ruta_depto(mio.id, depto_ajeno.id), json={"m2": "50"}, headers=_admin(como)
    )

    assert respuesta.status_code == 404


def test_una_cochera_de_otro_edificio_es_404(cliente, como, db):
    mio = _edificio(db, "El mio")
    ajeno = _edificio(db, "De otro")
    cochera = Cochera(edificio_id=ajeno.id, numero="1", tipo="fija")
    db.add(cochera)
    db.commit()

    respuesta = cliente.delete(
        f"{ruta_cocheras(mio.id)}/{cochera.id}", headers=_admin(como)
    )

    assert respuesta.status_code == 404


def test_un_espacio_comun_de_otro_edificio_es_404(cliente, como, db):
    mio = _edificio(db, "El mio")
    ajeno = _edificio(db, "De otro")
    espacio = EspacioComun(edificio_id=ajeno.id, nombre="SUM")
    db.add(espacio)
    db.commit()

    respuesta = cliente.patch(
        f"{ruta_espacios(mio.id)}/{espacio.id}",
        json={"nombre": "Otro"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 404


def test_una_unidad_no_se_puede_crear_en_un_piso_ajeno(cliente, como, db):
    mio = _edificio(db, "El mio")
    ajeno = _edificio(db, "De otro")
    piso_ajeno = _piso(db, ajeno)

    respuesta = cliente.post(
        ruta_deptos(mio.id, piso_ajeno.id),
        json={"identificador": "1A"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 404


# ==========================================================================
# DEPARTAMENTOS
# ==========================================================================


def test_agrega_una_unidad_a_un_piso(cliente, como, db):
    edificio = _edificio(db)
    piso = _piso(db, edificio)

    respuesta = cliente.post(
        ruta_deptos(edificio.id, piso.id),
        json={"identificador": "1A", "m2": "62.50"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["identificador"] == "1A"
    assert cuerpo["m2"] == "62.50"
    assert cuerpo["ocupado"] is False
    assert cuerpo["coeficiente"] is None


def test_la_unidad_nace_sin_coeficiente_y_no_se_puede_mandar(cliente, como, db):
    """La carga de coeficientes es `F1-T24` y tiene su propio endpoint: un
    coeficiente inventado reparte plata mal sin que nadie lo note."""
    edificio = _edificio(db)
    piso = _piso(db, edificio)

    respuesta = cliente.post(
        ruta_deptos(edificio.id, piso.id),
        json={"identificador": "1A", "coeficiente": "3.5"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 422


def test_un_identificador_repetido_en_el_mismo_piso_se_rechaza(cliente, como, db):
    edificio = _edificio(db)
    piso = _piso(db, edificio)
    _departamento(db, piso, "1A")

    respuesta = cliente.post(
        ruta_deptos(edificio.id, piso.id),
        json={"identificador": "1A"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 400


def test_el_mismo_identificador_en_otro_piso_se_acepta(cliente, como, db):
    """La unicidad es por piso, no por edificio: el "A" del primer piso y el
    "A" del segundo son dos unidades distintas."""
    edificio = _edificio(db)
    primero = _piso(db, edificio, numero=1)
    segundo = _piso(db, edificio, numero=2)
    _departamento(db, primero, "A")

    respuesta = cliente.post(
        ruta_deptos(edificio.id, segundo.id),
        json={"identificador": "A"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 201


@pytest.mark.parametrize("m2", ["0", "-5", "45.678"])
def test_una_superficie_invalida_se_rechaza(cliente, como, db, m2):
    """El cero se rechaza y no es un detalle: el atajo de coeficientes reparte
    proporcionalmente a la superficie, y una unidad con 0 m2 quedaria con
    coeficiente 0 — o sea, sin pagar expensas."""
    edificio = _edificio(db)
    piso = _piso(db, edificio)

    respuesta = cliente.post(
        ruta_deptos(edificio.id, piso.id),
        json={"identificador": "1A", "m2": m2},
        headers=_admin(como),
    )

    assert respuesta.status_code == 422


def test_edita_la_superficie_sin_tocar_lo_demas(cliente, como, db):
    edificio = _edificio(db, roles_habilitados=list(autorizacion.ROLES_HABILITABLES))
    piso = _piso(db, edificio)
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Ana")
    depto = _departamento(db, piso, "1A", propietario_id=propietario.id)

    respuesta = cliente.patch(
        ruta_depto(edificio.id, depto.id), json={"m2": "80.00"}, headers=_admin(como)
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["m2"] == "80.00"
    # El PATCH no borro al propietario, que es el error que un PUT comete solo.
    assert respuesta.json()["propietario_id"] == propietario.id


def test_borra_una_unidad_desocupada(cliente, como, db):
    edificio = _edificio(db)
    piso = _piso(db, edificio)
    depto = _departamento(db, piso, "1A")

    respuesta = cliente.delete(
        ruta_depto(edificio.id, depto.id), headers=_admin(como)
    )

    assert respuesta.status_code == 204
    assert db.scalars(select(Departamento)).all() == []


def test_no_borra_una_unidad_con_residente(cliente, como, db):
    edificio = _edificio(db)
    piso = _piso(db, edificio)
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Beto")
    depto = _departamento(db, piso, "1A", propietario_id=propietario.id)

    respuesta = cliente.delete(
        ruta_depto(edificio.id, depto.id), headers=_admin(como)
    )

    assert respuesta.status_code == 400
    assert "Desvinculá" in respuesta.json()["detail"]


def test_no_borra_una_unidad_con_cochera_asignada(cliente, como, db):
    """Una cochera fija apuntando a una unidad que ya no esta queda apuntando a
    la nada."""
    edificio = _edificio(db)
    piso = _piso(db, edificio)
    depto = _departamento(db, piso, "1A")
    db.add(Cochera(edificio_id=edificio.id, numero="12", tipo="fija", departamento_id=depto.id))
    db.commit()

    respuesta = cliente.delete(
        ruta_depto(edificio.id, depto.id), headers=_admin(como)
    )

    assert respuesta.status_code == 400
    assert "cochera" in respuesta.json()["detail"]


# ==========================================================================
# ASIGNACION Y DESVINCULACION DE RESIDENTES
# ==========================================================================


def test_asigna_un_propietario(cliente, como, db):
    edificio = _edificio(db)
    depto = _departamento(db, _piso(db, edificio), "1A")
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Carla")

    respuesta = cliente.patch(
        ruta_depto(edificio.id, depto.id),
        json={"propietario_id": propietario.id},
        headers=_admin(como),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["propietario_id"] == propietario.id
    assert respuesta.json()["ocupado"] is True


def test_desvincula_con_null(cliente, como, db):
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Diego")
    edificio = _edificio(db)
    depto = _departamento(db, _piso(db, edificio), "1A", propietario_id=propietario.id)

    respuesta = cliente.patch(
        ruta_depto(edificio.id, depto.id),
        json={"propietario_id": None},
        headers=_admin(como),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["propietario_id"] is None
    assert respuesta.json()["ocupado"] is False


def test_un_propietario_puede_tener_varias_unidades(cliente, como, db):
    """La regla del enunciado: el propietario varias, el inquilino una."""
    edificio = _edificio(db)
    piso = _piso(db, edificio)
    uno = _departamento(db, piso, "1A")
    dos = _departamento(db, piso, "1B")
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Elsa")
    headers = _admin(como)

    for depto in (uno, dos):
        respuesta = cliente.patch(
            ruta_depto(edificio.id, depto.id),
            json={"propietario_id": propietario.id},
            headers=headers,
        )
        assert respuesta.status_code == 200, depto.identificador


def test_un_inquilino_no_puede_estar_en_dos_unidades(cliente, como, db):
    """La base tambien lo prohibe, pero una restriccion que salta devuelve un
    500 sin explicacion: el mensaje dice en que unidad ya figura, que es lo
    unico que permite resolverlo."""
    edificio = _edificio(db)
    piso = _piso(db, edificio)
    inquilino = _usuario(db, autorizacion.INQUILINO, "Franco")
    _departamento(db, piso, "1A", inquilino_id=inquilino.id)
    otra = _departamento(db, piso, "1B")

    respuesta = cliente.patch(
        ruta_depto(edificio.id, otra.id),
        json={"inquilino_id": inquilino.id},
        headers=_admin(como),
    )

    assert respuesta.status_code == 400
    assert "1A" in respuesta.json()["detail"]


def test_reasignar_el_mismo_inquilino_a_su_propia_unidad_no_es_un_duplicado(
    cliente, como, db
):
    """El caso que se rompe si la verificacion no excluye la unidad propia:
    cambiar los metros cuadrados y el inquilino en el mismo pedido."""
    edificio = _edificio(db)
    inquilino = _usuario(db, autorizacion.INQUILINO, "Gisela")
    depto = _departamento(db, _piso(db, edificio), "1A", inquilino_id=inquilino.id)

    respuesta = cliente.patch(
        ruta_depto(edificio.id, depto.id),
        json={"inquilino_id": inquilino.id, "m2": "55.00"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 200


def test_un_residente_con_el_rol_equivocado_se_rechaza(cliente, como, db):
    edificio = _edificio(db)
    depto = _departamento(db, _piso(db, edificio), "1A")
    proveedor = _usuario(db, autorizacion.PROVEEDOR, "Hector")

    respuesta = cliente.patch(
        ruta_depto(edificio.id, depto.id),
        json={"propietario_id": proveedor.id},
        headers=_admin(como),
    )

    assert respuesta.status_code == 400
    assert "Hector" in respuesta.json()["detail"]


def test_un_propietario_no_sirve_como_inquilino(cliente, como, db):
    edificio = _edificio(db)
    depto = _departamento(db, _piso(db, edificio), "1A")
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Irma")

    respuesta = cliente.patch(
        ruta_depto(edificio.id, depto.id),
        json={"inquilino_id": propietario.id},
        headers=_admin(como),
    )

    assert respuesta.status_code == 400


def test_un_residente_desactivado_se_rechaza(cliente, como, db):
    edificio = _edificio(db)
    depto = _departamento(db, _piso(db, edificio), "1A")
    inactivo = _usuario(db, autorizacion.PROPIETARIO, "Jorge", activo=False)

    respuesta = cliente.patch(
        ruta_depto(edificio.id, depto.id),
        json={"propietario_id": inactivo.id},
        headers=_admin(como),
    )

    assert respuesta.status_code == 400
    assert "desactivad" in respuesta.json()["detail"]


def test_un_residente_que_no_existe_se_rechaza(cliente, como, db):
    edificio = _edificio(db)
    depto = _departamento(db, _piso(db, edificio), "1A")

    respuesta = cliente.patch(
        ruta_depto(edificio.id, depto.id),
        json={"propietario_id": 9999},
        headers=_admin(como),
    )

    assert respuesta.status_code == 400


def test_no_se_puede_asignar_un_rol_que_el_edificio_no_habilito(cliente, como, db):
    """Es lo que le da sentido a `roles_habilitados` de `F1-T22`.

    Si un consorcio decidio no habilitar inquilinos, asignar uno igual seria
    guardar un dato que la configuracion del edificio dice que no existe.
    """
    edificio = _edificio(db, roles_habilitados=[autorizacion.PROPIETARIO])
    depto = _departamento(db, _piso(db, edificio), "1A")
    inquilino = _usuario(db, autorizacion.INQUILINO, "Karen")

    respuesta = cliente.patch(
        ruta_depto(edificio.id, depto.id),
        json={"inquilino_id": inquilino.id},
        headers=_admin(como),
    )

    assert respuesta.status_code == 400
    assert "habilit" in respuesta.json()["detail"]


def test_desvincular_funciona_aunque_el_rol_ya_no_este_habilitado(cliente, como, db):
    """Si no fuera asi, deshabilitar un rol dejaria a esas personas pegadas a
    sus unidades para siempre."""
    inquilino = _usuario(db, autorizacion.INQUILINO, "Lali")
    edificio = _edificio(db, roles_habilitados=[autorizacion.PROPIETARIO])
    depto = _departamento(db, _piso(db, edificio), "1A", inquilino_id=inquilino.id)

    respuesta = cliente.patch(
        ruta_depto(edificio.id, depto.id),
        json={"inquilino_id": None},
        headers=_admin(como),
    )

    assert respuesta.status_code == 200


# ==========================================================================
# COCHERAS
# ==========================================================================


def test_agrega_una_cochera_rotulada(cliente, como, db):
    """El `numero` es texto: el rotulo real dice "S2-14" tan seguido como
    dice "12"."""
    edificio = _edificio(db)

    respuesta = cliente.post(
        ruta_cocheras(edificio.id),
        json={"numero": "S2-14", "tipo": "rotativa"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["numero"] == "S2-14"
    assert respuesta.json()["tipo"] == "rotativa"


def test_una_cochera_fija_se_asigna_a_una_unidad(cliente, como, db):
    edificio = _edificio(db)
    depto = _departamento(db, _piso(db, edificio), "1A")

    respuesta = cliente.post(
        ruta_cocheras(edificio.id),
        json={"numero": "12", "tipo": "fija", "departamento_id": depto.id},
        headers=_admin(como),
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["departamento_id"] == depto.id


def test_una_cochera_rotativa_no_se_asigna_a_una_unidad(cliente, como, db):
    """Rotativa significa justamente que no es de nadie en particular."""
    edificio = _edificio(db)
    depto = _departamento(db, _piso(db, edificio), "1A")

    respuesta = cliente.post(
        ruta_cocheras(edificio.id),
        json={"numero": "12", "tipo": "rotativa", "departamento_id": depto.id},
        headers=_admin(como),
    )

    assert respuesta.status_code == 400
    assert "rotativa" in respuesta.json()["detail"]


def test_no_se_puede_asignar_una_cochera_a_una_unidad_de_otro_edificio(cliente, como, db):
    mio = _edificio(db, "El mio")
    ajeno = _edificio(db, "De otro")
    depto_ajeno = _departamento(db, _piso(db, ajeno), "1A")

    respuesta = cliente.post(
        ruta_cocheras(mio.id),
        json={"numero": "12", "tipo": "fija", "departamento_id": depto_ajeno.id},
        headers=_admin(como),
    )

    assert respuesta.status_code == 404


def test_un_tipo_de_cochera_inventado_se_rechaza(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.post(
        ruta_cocheras(edificio.id),
        json={"numero": "12", "tipo": "semifija"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 422


def test_un_numero_de_cochera_repetido_se_rechaza(cliente, como, db):
    edificio = _edificio(db)
    db.add(Cochera(edificio_id=edificio.id, numero="12", tipo="fija"))
    db.commit()

    respuesta = cliente.post(
        ruta_cocheras(edificio.id),
        json={"numero": "12", "tipo": "rotativa"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 400


def test_pasar_una_cochera_fija_a_rotativa_sin_desasignarla_se_rechaza(cliente, como, db):
    """Se valida el resultado FINAL y no lo que vino en el pedido: en este
    pedido `departamento_id` no viaja."""
    edificio = _edificio(db)
    depto = _departamento(db, _piso(db, edificio), "1A")
    cochera = Cochera(
        edificio_id=edificio.id, numero="12", tipo="fija", departamento_id=depto.id
    )
    db.add(cochera)
    db.commit()

    respuesta = cliente.patch(
        f"{ruta_cocheras(edificio.id)}/{cochera.id}",
        json={"tipo": "rotativa"},
        headers=_admin(como),
    )

    assert respuesta.status_code == 400


def test_pasarla_a_rotativa_y_desasignarla_en_el_mismo_pedido_funciona(cliente, como, db):
    edificio = _edificio(db)
    depto = _departamento(db, _piso(db, edificio), "1A")
    cochera = Cochera(
        edificio_id=edificio.id, numero="12", tipo="fija", departamento_id=depto.id
    )
    db.add(cochera)
    db.commit()

    respuesta = cliente.patch(
        f"{ruta_cocheras(edificio.id)}/{cochera.id}",
        json={"tipo": "rotativa", "departamento_id": None},
        headers=_admin(como),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["departamento_id"] is None


def test_borra_una_cochera(cliente, como, db):
    edificio = _edificio(db)
    cochera = Cochera(edificio_id=edificio.id, numero="12", tipo="rotativa")
    db.add(cochera)
    db.commit()

    respuesta = cliente.delete(
        f"{ruta_cocheras(edificio.id)}/{cochera.id}", headers=_admin(como)
    )

    assert respuesta.status_code == 204
    assert db.scalars(select(Cochera)).all() == []


# ==========================================================================
# ESPACIOS COMUNES
# ==========================================================================


def test_crea_un_espacio_comun(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.post(
        ruta_espacios(edificio.id),
        json={"nombre": "SUM", "capacidad": 40, "reglas_uso": "Hasta las 23."},
        headers=_admin(como),
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["nombre"] == "SUM"
    assert respuesta.json()["capacidad"] == 40


def test_un_espacio_sin_aforo_es_valido(cliente, como, db):
    """Un laundry con dos lavarropas no se mide en personas."""
    edificio = _edificio(db)

    respuesta = cliente.post(
        ruta_espacios(edificio.id), json={"nombre": "Laundry"}, headers=_admin(como)
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["capacidad"] is None


def test_un_aforo_de_cero_se_rechaza(cliente, como, db):
    """Un 0 usado como "sin dato" seria un espacio que no admite a nadie, y la
    pantalla de reservas lo mostraria como lleno para siempre."""
    edificio = _edificio(db)

    respuesta = cliente.post(
        ruta_espacios(edificio.id),
        json={"nombre": "Pileta", "capacidad": 0},
        headers=_admin(como),
    )

    assert respuesta.status_code == 422


def test_un_nombre_de_espacio_repetido_se_rechaza(cliente, como, db):
    edificio = _edificio(db)
    db.add(EspacioComun(edificio_id=edificio.id, nombre="SUM"))
    db.commit()

    respuesta = cliente.post(
        ruta_espacios(edificio.id), json={"nombre": "SUM"}, headers=_admin(como)
    )

    assert respuesta.status_code == 400


def test_edita_y_borra_un_espacio_comun(cliente, como, db):
    edificio = _edificio(db)
    espacio = EspacioComun(edificio_id=edificio.id, nombre="SUM", capacidad=40)
    db.add(espacio)
    db.commit()
    headers = _admin(como)

    editado = cliente.patch(
        f"{ruta_espacios(edificio.id)}/{espacio.id}",
        json={"capacidad": 30, "reglas_uso": "Reservar con 48 h."},
        headers=headers,
    )
    assert editado.status_code == 200
    assert editado.json()["capacidad"] == 30

    borrado = cliente.delete(
        f"{ruta_espacios(edificio.id)}/{espacio.id}", headers=headers
    )
    assert borrado.status_code == 204
    assert db.scalars(select(EspacioComun)).all() == []


def test_el_listado_de_espacios_viene_ordenado_por_nombre(cliente, como, db):
    edificio = _edificio(db)
    for nombre in ("SUM", "Laundry", "Pileta"):
        db.add(EspacioComun(edificio_id=edificio.id, nombre=nombre))
    db.commit()

    nombres = [
        e["nombre"]
        for e in cliente.get(ruta_espacios(edificio.id), headers=_admin(como)).json()
    ]

    assert nombres == ["Laundry", "Pileta", "SUM"]


# ==========================================================================
# PERMISOS DE ESCRITURA
# ==========================================================================

ESCRITURAS = [
    ("post", lambda e: ruta_pisos(e.id), {"numero": 9}),
    ("post", lambda e: ruta_cocheras(e.id), {"numero": "99", "tipo": "fija"}),
    ("post", lambda e: ruta_espacios(e.id), {"nombre": "Quincho"}),
]


@pytest.mark.parametrize("rol", [autorizacion.ENCARGADO, autorizacion.PROPIETARIO, autorizacion.INQUILINO, autorizacion.AUDITOR])
@pytest.mark.parametrize("metodo,ruta,cuerpo", ESCRITURAS)
def test_los_no_administradores_no_pueden_escribir_la_estructura(
    cliente, como, db, rol, metodo, ruta, cuerpo
):
    edificio = _edificio(db)

    respuesta = getattr(cliente, metodo)(ruta(edificio), json=cuerpo, headers=como(rol))

    assert respuesta.status_code == 403


def test_sin_autenticacion_no_se_escribe(cliente, db):
    edificio = _edificio(db)

    assert cliente.post(ruta_pisos(edificio.id), json={"numero": 1}).status_code == 401


def test_el_administrador_de_consorcio_escribe_en_su_edificio(cliente, como, db):
    headers = como(autorizacion.ADMIN_CONSORCIO)
    admin = db.scalars(
        select(Usuario)
        .where(Usuario.rol == autorizacion.ADMIN_CONSORCIO)
        .order_by(Usuario.id.desc())
    ).first()
    edificio = _edificio(db, admin_consorcio_id=admin.id)

    respuesta = cliente.post(ruta_pisos(edificio.id), json={"numero": 1}, headers=headers)

    assert respuesta.status_code == 201


def test_el_administrador_de_consorcio_no_escribe_en_un_edificio_ajeno(cliente, como, db):
    headers = como(autorizacion.ADMIN_CONSORCIO)
    ajeno = _edificio(db, "De otro")

    respuesta = cliente.post(ruta_pisos(ajeno.id), json={"numero": 1}, headers=headers)

    assert respuesta.status_code == 404


def test_ningun_mensaje_nombra_tablas_ni_columnas(cliente, como, db):
    """Regla `FX-T11`."""
    edificio = _edificio(db)
    piso = _piso(db, edificio)
    _departamento(db, piso, "1A")
    headers = _admin(como)

    mensajes = [
        cliente.delete(f"{ruta_pisos(edificio.id)}/{piso.id}", headers=headers).json()["detail"],
        cliente.post(ruta_pisos(edificio.id), json={"numero": 1}, headers=headers).json()["detail"],
        cliente.patch(f"{ruta_pisos(edificio.id)}/9999", json={"numero": 2}, headers=headers).json()["detail"],
    ]

    for mensaje in mensajes:
        texto = mensaje.lower()
        for palabra in ("pisos", "departamentos", "select", "insert", "constraint", "null"):
            assert palabra not in texto, mensaje

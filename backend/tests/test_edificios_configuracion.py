"""Pruebas de `PATCH /api/edificios/{id}` — configuracion del edificio (F1-T22).

Lo que hay que probar aca no es que los campos se guarden —eso lo cumple
cualquier UPDATE— sino las cuatro reglas que hacen que la configuracion no se
pueda dejar en un estado invalido:

  1. **Es un PATCH de verdad:** lo que no viaja no se toca, y lo que viaja en
     `null` se vacia. Son dos cosas distintas y el test las separa.
  2. **Los responsables son reales:** el usuario existe, esta activo y tiene
     ese rol en la matriz. Un "encargado" que en realidad es Proveedor no tiene
     ninguno de los permisos de la pantalla del encargado, y eso se descubre
     recien cuando esa persona intenta entrar.
  3. **Quien administra el edificio lo decide la plataforma**, no el consorcio:
     un Administrador de Consorcio no puede tocar los responsables ni sacarse a
     si mismo.
  4. **Los datos de cobranza se validan antes de la base:** el CBU, el alias y
     los decimales del recargo, para que el error sea un 422 con explicacion y
     no un 500 de la base.
"""

import pytest
from sqlalchemy import select

from app.models.edificio import Edificio
from app.models.usuario import Usuario
from app.services import autorizacion

RUTA = "/api/edificios"

CBU_VALIDO = "0170099920000000123456"

OTROS_ROLES = [
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


def _usuario(db, rol: str, nombre: str = "Persona", activo: bool = True) -> Usuario:
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
    """El header de un Administrador de Consorcio y su fila en la base."""
    headers = como(autorizacion.ADMIN_CONSORCIO)
    usuario = db.scalars(
        select(Usuario)
        .where(Usuario.rol == autorizacion.ADMIN_CONSORCIO)
        .order_by(Usuario.id.desc())
    ).first()
    return headers, usuario


# ==========================================================================
# EL PATCH ES UN PATCH
# ==========================================================================


def test_guarda_solo_los_campos_que_viajaron(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"dias_vencimiento_expensas": 15},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["dias_vencimiento_expensas"] == 15
    # Lo que no viajo quedo como estaba.
    assert cuerpo["nombre"] == "Consorcio Mitre 500"
    assert cuerpo["recargo_mora_porcentual"] == "0.00"


def test_un_campo_ausente_no_borra_lo_que_ya_estaba(cliente, como, db):
    """La diferencia entre PATCH y PUT, probada.

    Con un PUT, guardar el bloque de cobranza obligaria a mandar tambien el
    contacto de emergencia, y el dia que ese campo no viaje en el formulario
    guardar la cobranza lo borraria sin que nadie lo pida.
    """
    edificio = _edificio(db, contacto_emergencia_telefono="11-5555-5555")
    headers = como(autorizacion.ADMIN_GENERAL)

    cliente.patch(f"{RUTA}/{edificio.id}", json={"alias_cbu": "mitre.500"}, headers=headers)

    db.refresh(edificio)
    assert edificio.contacto_emergencia_telefono == "11-5555-5555"
    assert edificio.alias_cbu == "mitre.500"


def test_un_campo_en_null_si_vacia_el_dato(cliente, como, db):
    """Tiene que poder borrarse el telefono de emergencia.

    Con un centinela tipo cadena vacia, "borralo" seria indistinguible de "no
    lo toques". Por eso el endpoint usa `exclude_unset` y no un valor especial.
    """
    edificio = _edificio(db, contacto_emergencia_telefono="11-5555-5555")

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"contacto_emergencia_telefono": None},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["contacto_emergencia_telefono"] is None


def test_un_pedido_sin_ningun_campo_es_400(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}", json={}, headers=como(autorizacion.ADMIN_GENERAL)
    )

    assert respuesta.status_code == 400


def test_un_campo_que_el_esquema_no_conoce_se_rechaza(cliente, como, db):
    """Se rechaza, no se ignora: el default de Pydantic es descartarlo en
    silencio, y en un formulario eso significa un 200 sin haber guardado."""
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"nombre_del_consorcio": "otro"},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 422


def test_no_se_pueden_vaciar_los_campos_obligatorios(cliente, como, db):
    edificio = _edificio(db)
    headers = como(autorizacion.ADMIN_GENERAL)

    for campo in (
        "dias_vencimiento_expensas",
        "recargo_mora_porcentual",
        "roles_habilitados",
    ):
        respuesta = cliente.patch(
            f"{RUTA}/{edificio.id}", json={campo: None}, headers=headers
        )
        assert respuesta.status_code == 422, campo


def test_la_identidad_del_edificio_no_se_toca_por_aca(cliente, como, db):
    """El nombre, la direccion y el CP no son configuracion.

    No estan en el esquema a proposito: esta tarea es la configuracion del
    edificio. Si hace falta corregir una direccion mal cargada, es otra tarea
    con su propio permiso.
    """
    edificio = _edificio(db)
    headers = como(autorizacion.ADMIN_GENERAL)

    for campo, valor in (("nombre", "Otro"), ("direccion", "Otra 1"), ("cp", "X")):
        respuesta = cliente.patch(
            f"{RUTA}/{edificio.id}", json={campo: valor}, headers=headers
        )
        assert respuesta.status_code == 422, campo


# ==========================================================================
# LOS RESPONSABLES
# ==========================================================================


def test_asigna_los_dos_responsables(cliente, como, db):
    edificio = _edificio(db)
    admin = _usuario(db, autorizacion.ADMIN_CONSORCIO, "Ana")
    encargado = _usuario(db, autorizacion.ENCARGADO, "Beto")

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"admin_consorcio_id": admin.id, "encargado_id": encargado.id},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["admin_consorcio_id"] == admin.id
    assert respuesta.json()["encargado_id"] == encargado.id


def test_un_responsable_con_el_rol_equivocado_se_rechaza(cliente, como, db):
    """Es lo que el Roadmap pide explicitamente.

    Un "encargado" que en la matriz de roles es Proveedor no tiene ninguno de
    los permisos que la pantalla del encargado necesita, y la falla aparece
    recien cuando esa persona intenta entrar.
    """
    edificio = _edificio(db)
    proveedor = _usuario(db, autorizacion.PROVEEDOR, "Carlos")

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"encargado_id": proveedor.id},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 400
    assert "Carlos" in respuesta.json()["detail"]


def test_un_encargado_no_sirve_como_administrador_de_consorcio(cliente, como, db):
    """El cruce al reves: cada puesto exige SU rol, no "un rol cualquiera"."""
    edificio = _edificio(db)
    encargado = _usuario(db, autorizacion.ENCARGADO, "Dario")

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"admin_consorcio_id": encargado.id},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 400


def test_un_responsable_desactivado_se_rechaza(cliente, como, db):
    edificio = _edificio(db)
    inactivo = _usuario(db, autorizacion.ENCARGADO, "Elena", activo=False)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"encargado_id": inactivo.id},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 400
    assert "desactivad" in respuesta.json()["detail"]


def test_un_responsable_que_no_existe_se_rechaza(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"encargado_id": 9999},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 400


def test_un_responsable_se_puede_desvincular_con_null(cliente, como, db):
    admin = _usuario(db, autorizacion.ADMIN_CONSORCIO, "Fabian")
    edificio = _edificio(db, admin_consorcio_id=admin.id)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"admin_consorcio_id": None},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["admin_consorcio_id"] is None


def test_la_misma_persona_no_puede_ocupar_los_dos_puestos(cliente, como, db):
    """Y el motivo que da es el rol, no el cruce.

    Un usuario tiene UN rol, y cada puesto exige el suyo: quien puede ser
    Administrador de Consorcio nunca puede ser Encargado al mismo tiempo. Asi
    que el cruce se rechaza antes, por rol, y el mensaje dice algo util
    ("Gabriela es Administrador de Consorcio, no Encargado") en vez de hablar
    de una regla que la persona no violo a proposito.

    El chequeo de puestos distintos del endpoint queda igual, como respaldo del
    CHECK de la tabla: hoy es inalcanzable, y lo seria el dia que un puesto
    admita mas de un rol.
    """
    edificio = _edificio(db)
    admin = _usuario(db, autorizacion.ADMIN_CONSORCIO, "Gabriela")

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"admin_consorcio_id": admin.id, "encargado_id": admin.id},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 400
    assert "Encargado" in respuesta.json()["detail"]


def test_tampoco_en_dos_pedidos_separados(cliente, como, db):
    """El mismo cruce, repartido en dos pedidos.

    Asignar como encargado a quien YA era el administrador viaja con un solo
    campo, asi que no alcanzaria con comparar los dos valores del pedido. Lo
    frena la validacion de rol, y el edificio queda como estaba.
    """
    admin = _usuario(db, autorizacion.ADMIN_CONSORCIO, "Hugo")
    edificio = _edificio(db, admin_consorcio_id=admin.id)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"encargado_id": admin.id},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 400
    db.refresh(edificio)
    assert edificio.encargado_id is None


def test_el_rechazo_del_cruce_no_deja_nada_guardado(cliente, como, db):
    """Un 400 que ya hubiera escrito la mitad de los campos seria peor que el
    error: el edificio quedaria con un vencimiento nuevo y sin responsables."""
    admin = _usuario(db, autorizacion.ADMIN_CONSORCIO, "Ines")
    edificio = _edificio(db, admin_consorcio_id=admin.id)

    cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"encargado_id": admin.id, "dias_vencimiento_expensas": 20},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    db.refresh(edificio)
    assert edificio.dias_vencimiento_expensas == 10
    assert edificio.encargado_id is None


# ==========================================================================
# COBRANZA
# ==========================================================================


def test_guarda_el_cbu_limpio(cliente, como, db):
    """Un CBU se copia y se pega de un resumen, casi siempre en bloques."""
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"cbu": "0170 0999 2000 0000 1234 56"},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["cbu"] == CBU_VALIDO


@pytest.mark.parametrize(
    "cbu",
    [
        "017009992000000012345",  # 21 digitos: el error de tipeo frecuente
        "01700999200000001234567",  # 23
        "017009992000000012345a",  # una letra
        "",  # vacio
    ],
)
def test_un_cbu_que_no_son_22_digitos_se_rechaza(cliente, como, db, cbu):
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}", json={"cbu": cbu}, headers=como(autorizacion.ADMIN_GENERAL)
    )

    if cbu == "":
        # Vacio es "sin cargar", no un error: el campo se limpia.
        assert respuesta.status_code == 200
        assert respuesta.json()["cbu"] is None
    else:
        assert respuesta.status_code == 422


@pytest.mark.parametrize("alias", ["corto", "a" * 21, "con espacio", "con_guion_bajo"])
def test_un_alias_invalido_se_rechaza(cliente, como, db, alias):
    """Si no se validara, un alias de 30 caracteres lo rechazaria la columna
    `String(20)` y la persona veria un 500 sin explicacion."""
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"alias_cbu": alias},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 422


def test_guarda_un_alias_valido(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"alias_cbu": "mitre.500-sum"},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["alias_cbu"] == "mitre.500-sum"


def test_el_recargo_con_mas_de_dos_decimales_se_rechaza(cliente, como, db):
    """La columna es `Numeric(5,2)`: un 1,555 se guardaria redondeado y la
    persona que lo escribio nunca se enteraria. Es plata ajena."""
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"recargo_mora_porcentual": "1.555"},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 422


def test_guarda_el_recargo_con_dos_decimales(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"recargo_mora_porcentual": "2.50"},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["recargo_mora_porcentual"] == "2.50"


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("dias_vencimiento_expensas", 0),
        ("dias_vencimiento_expensas", 32),
        ("recargo_mora_porcentual", "-1"),
        ("recargo_mora_porcentual", "101"),
    ],
)
def test_los_limites_de_cobranza_son_un_422_y_no_un_500(cliente, como, db, campo, valor):
    """Los mismos limites estan en el CHECK de la tabla. Estan en los dos
    lados a proposito: aca para que el error explique que esta mal, y en la
    tabla para que un UPDATE que no pase por la API tampoco pueda."""
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={campo: valor},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 422


# ==========================================================================
# ROLES HABILITADOS
# ==========================================================================


def test_guarda_los_roles_habilitados(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={
            "roles_habilitados": [
                autorizacion.PROPIETARIO,
                autorizacion.INQUILINO,
            ]
        },
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["roles_habilitados"] == [
        autorizacion.PROPIETARIO,
        autorizacion.INQUILINO,
    ]


def test_el_edificio_nace_con_todos_los_roles_habilitados(cliente, como, db):
    """El valor por defecto es "todos" y no "ninguno": una lista vacia por
    omision bloquearia cada asignacion sin que nadie lo haya pedido."""
    edificio = _edificio(db)

    respuesta = cliente.get(
        f"{RUTA}/{edificio.id}", headers=como(autorizacion.ADMIN_GENERAL)
    )

    assert respuesta.json()["edificio"]["roles_habilitados"] == list(
        autorizacion.ROLES_HABILITABLES
    )


def test_un_rol_que_no_se_puede_habilitar_se_rechaza(cliente, como, db):
    """`admin_general` es un rol real pero su alcance es la cartera entera: no
    es algo que se habilite "dentro de" un edificio."""
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"roles_habilitados": [autorizacion.ADMIN_GENERAL]},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 422


def test_un_rol_inventado_se_rechaza(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"roles_habilitados": ["encargdo"]},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 422


def test_los_roles_repetidos_se_guardan_una_sola_vez(cliente, como, db):
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"roles_habilitados": [autorizacion.PROPIETARIO] * 3},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.json()["roles_habilitados"] == [autorizacion.PROPIETARIO]


def test_la_lista_vacia_se_acepta_porque_es_una_decision_explicita(cliente, como, db):
    """Distinto del default: pedir "ninguno" a proposito es legitimo; quedarse
    sin roles por omision, no."""
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"roles_habilitados": []},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["roles_habilitados"] == []


def test_la_lista_de_roles_se_reemplaza_y_el_cambio_queda_guardado(cliente, como, db):
    """Una columna JSON no se da cuenta de un `.append()` sobre la lista que ya
    tiene cargada: ese cambio no se guardaria y tampoco daria error. El
    endpoint asigna una lista nueva, y esto lo verifica contra la base."""
    edificio = _edificio(db)

    cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"roles_habilitados": [autorizacion.SEGURIDAD]},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    db.expire_all()
    guardado = db.scalars(select(Edificio).where(Edificio.id == edificio.id)).first()
    assert guardado.roles_habilitados == [autorizacion.SEGURIDAD]


# ==========================================================================
# PERMISOS Y ALCANCE
# ==========================================================================


def test_el_administrador_de_consorcio_configura_su_edificio(cliente, como, db):
    headers, admin = _admin_consorcio_logueado(db, como)
    edificio = _edificio(db, admin_consorcio_id=admin.id)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"cbu": CBU_VALIDO, "dias_vencimiento_expensas": 5},
        headers=headers,
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["cbu"] == CBU_VALIDO


def test_el_administrador_de_consorcio_no_puede_cambiar_los_responsables(
    cliente, como, db
):
    """Si pudiera, podria sacarse a si mismo —perdiendo el acceso al edificio
    sin forma de recuperarlo— o asignarse un edificio ajeno."""
    headers, admin = _admin_consorcio_logueado(db, como)
    edificio = _edificio(db, admin_consorcio_id=admin.id)
    otro = _usuario(db, autorizacion.ADMIN_CONSORCIO, "Julia")

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"admin_consorcio_id": otro.id},
        headers=headers,
    )

    assert respuesta.status_code == 403
    db.refresh(edificio)
    assert edificio.admin_consorcio_id == admin.id


def test_tampoco_puede_desvincularse_a_si_mismo(cliente, como, db):
    headers, admin = _admin_consorcio_logueado(db, como)
    edificio = _edificio(db, admin_consorcio_id=admin.id)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"admin_consorcio_id": None},
        headers=headers,
    )

    assert respuesta.status_code == 403


def test_tampoco_puede_cambiar_al_encargado(cliente, como, db):
    headers, admin = _admin_consorcio_logueado(db, como)
    edificio = _edificio(db, admin_consorcio_id=admin.id)
    encargado = _usuario(db, autorizacion.ENCARGADO, "Karina")

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"encargado_id": encargado.id},
        headers=headers,
    )

    assert respuesta.status_code == 403


def test_el_403_de_responsables_llega_antes_que_el_404_de_alcance(cliente, como, db):
    """Un Administrador de Consorcio que intenta tocar los responsables recibe
    el 403 que explica el motivo, y no un 404 que lo mandaria a buscar un
    problema de id que no existe."""
    headers, _ = _admin_consorcio_logueado(db, como)
    ajeno = _edificio(db, "De otro")
    encargado = _usuario(db, autorizacion.ENCARGADO, "Lucas")

    respuesta = cliente.patch(
        f"{RUTA}/{ajeno.id}",
        json={"encargado_id": encargado.id},
        headers=headers,
    )

    assert respuesta.status_code == 403


def test_un_edificio_ajeno_responde_igual_que_uno_inexistente(cliente, como, db):
    headers, _ = _admin_consorcio_logueado(db, como)
    ajeno = _edificio(db, "De otro")

    fuera_de_alcance = cliente.patch(
        f"{RUTA}/{ajeno.id}", json={"dias_vencimiento_expensas": 5}, headers=headers
    )
    inexistente = cliente.patch(
        f"{RUTA}/9999", json={"dias_vencimiento_expensas": 5}, headers=headers
    )

    assert fuera_de_alcance.status_code == 404
    assert fuera_de_alcance.json() == inexistente.json()
    db.refresh(ajeno)
    assert ajeno.dias_vencimiento_expensas == 10


@pytest.mark.parametrize("rol", OTROS_ROLES)
def test_los_demas_roles_no_pueden_configurar(cliente, como, db, rol):
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}",
        json={"dias_vencimiento_expensas": 5},
        headers=como(rol),
    )

    assert respuesta.status_code == 403


def test_sin_autenticacion_es_401(cliente, db):
    edificio = _edificio(db)

    respuesta = cliente.patch(
        f"{RUTA}/{edificio.id}", json={"dias_vencimiento_expensas": 5}
    )

    assert respuesta.status_code == 401


def test_un_edificio_que_no_existe_es_404(cliente, como):
    respuesta = cliente.patch(
        f"{RUTA}/9999",
        json={"dias_vencimiento_expensas": 5},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 404


def test_ningun_mensaje_de_error_nombra_tablas_ni_columnas_de_la_base(cliente, como, db):
    """Regla `FX-T11`: ningun mensaje que ve un usuario nombra tablas,
    columnas, consultas ni archivos."""
    edificio = _edificio(db)
    proveedor = _usuario(db, autorizacion.PROVEEDOR, "Mario")
    headers = como(autorizacion.ADMIN_GENERAL)

    mensajes = [
        cliente.patch(f"{RUTA}/{edificio.id}", json={"encargado_id": proveedor.id}, headers=headers).json()["detail"],
        cliente.patch(f"{RUTA}/9999", json={"dias_vencimiento_expensas": 5}, headers=headers).json()["detail"],
        cliente.patch(f"{RUTA}/{edificio.id}", json={}, headers=headers).json()["detail"],
    ]

    for mensaje in mensajes:
        texto = mensaje.lower()
        for palabra in ("edificios", "usuarios", "select", "update", "check", "null"):
            assert palabra not in texto, mensaje

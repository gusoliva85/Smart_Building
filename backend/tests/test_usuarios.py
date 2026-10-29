"""Pruebas del CRUD de usuarios.

Tres cosas se prueban con mas insistencia que el resto, porque son las que
tienen consecuencias que no se arreglan desde la aplicacion:

  - que **nadie que no sea Administrador General** llegue a ninguno de los
    cinco endpoints,
  - que un administrador **no pueda dejarse afuera a si mismo** —ni
    desactivandose ni cambiandose el rol—,
  - que el PATCH sea un PATCH de verdad: lo que no viene no se toca.
"""

import pytest
from sqlalchemy import select

from app.core import security
from app.models.usuario import Usuario
from app.services import autorizacion
from tests.conftest import PASSWORD_DE_PRUEBA

USUARIOS = "/api/usuarios"

ALTA_VALIDA = {
    "nombre": "Ana Suarez",
    "email": "ana@ejemplo.com",
    "password": "ClaveFuerte1!",
    "rol": autorizacion.PROPIETARIO,
    "telefono": "11 5555 4444",
}


@pytest.fixture
def admin(como):
    """El header de un Administrador General, que es quien puede todo acá."""
    return como(autorizacion.ADMIN_GENERAL)


def _crear(cliente, admin, **cambios):
    cuerpo = ALTA_VALIDA | cambios
    return cliente.post(USUARIOS, json=cuerpo, headers=admin)


# ------------------------------------------------------------------- alta ----


def test_el_administrador_general_puede_dar_de_alta(cliente, admin):
    respuesta = _crear(cliente, admin)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["email"] == "ana@ejemplo.com"
    assert cuerpo["rol"] == autorizacion.PROPIETARIO
    assert cuerpo["activo"] is True


def test_el_alta_no_devuelve_la_contrasenia_ni_su_hash(cliente, admin):
    respuesta = _crear(cliente, admin)

    assert ALTA_VALIDA["password"] not in respuesta.text
    assert "password" not in respuesta.json()


def test_la_contrasenia_queda_hasheada_y_sirve_para_entrar(cliente, db, admin):
    """El alta no esta terminada si la persona no puede iniciar sesion: eso es
    lo unico que prueba que el hash se guardo bien y no, por ejemplo, la
    contrasenia en texto plano en la columna del hash."""
    _crear(cliente, admin)

    login = cliente.post(
        "/api/auth/login",
        data={"username": "ana@ejemplo.com", "password": ALTA_VALIDA["password"]},
    )

    assert login.status_code == 200, login.text
    guardado = db.scalar(select(Usuario).where(Usuario.email == "ana@ejemplo.com"))
    assert ALTA_VALIDA["password"] not in guardado.password_hash


def test_el_email_se_guarda_normalizado(cliente, admin):
    """Misma regla que el alta de `F1-T05` y que el login. Si el CRUD guardara
    sin normalizar, la persona que se da de alta con mayusculas no entraria."""
    respuesta = _crear(cliente, admin, email="  ANA@Ejemplo.COM  ")

    assert respuesta.json()["email"] == "ana@ejemplo.com"


def test_un_email_repetido_se_rechaza(cliente, admin):
    _crear(cliente, admin)

    repetido = _crear(cliente, admin, nombre="Otra Persona")

    assert repetido.status_code == 400
    assert "email" in repetido.json()["detail"].lower()


def test_el_email_repetido_no_da_409(cliente, admin):
    """`409` tiene significado reservado en este proyecto: `api.js` lo traduce
    a `necesitaConfirmacion`, asi que la pantalla ofreceria confirmar y repetir
    una operacion que va a fallar igual."""
    _crear(cliente, admin)

    repetido = _crear(cliente, admin)

    assert repetido.status_code != 409


def test_un_email_repetido_con_otra_capitalizacion_tambien_se_rechaza(cliente, admin):
    """El indice unico distingue mayusculas, asi que si la normalizacion no
    corriera antes de guardar, `Ana@` y `ana@` serian DOS usuarios para una
    sola persona, con dos contrasenias y dos historiales."""
    _crear(cliente, admin)

    repetido = _crear(cliente, admin, email="ANA@EJEMPLO.COM")

    assert repetido.status_code == 400


def test_una_contrasenia_debil_se_rechaza_con_422(cliente, admin):
    """La politica de `core/security.py` se aplica tambien acá, que es la via
    real por la que se crean los usuarios."""
    respuesta = _crear(cliente, admin, password="corta")

    assert respuesta.status_code == 422


def test_un_rol_inexistente_se_rechaza_con_422(cliente, admin):
    respuesta = _crear(cliente, admin, rol="jefe_supremo")

    assert respuesta.status_code == 422


def test_el_telefono_es_opcional(cliente, admin):
    cuerpo = {k: v for k, v in ALTA_VALIDA.items() if k != "telefono"}

    respuesta = cliente.post(USUARIOS, json=cuerpo, headers=admin)

    assert respuesta.status_code == 201
    assert respuesta.json()["telefono"] is None


# ---------------------------------------------------------------- lectura ----


def test_el_listado_trae_los_usuarios_ordenados_por_nombre(cliente, admin):
    _crear(cliente, admin, nombre="Zulema Diaz", email="zulema@ejemplo.com")
    _crear(cliente, admin, nombre="Ana Suarez", email="ana@ejemplo.com")

    cuerpo = cliente.get(USUARIOS, headers=admin).json()
    nombres = [u["nombre"] for u in cuerpo]

    assert nombres == sorted(nombres)


def test_el_listado_incluye_a_los_inactivos(cliente, db, admin):
    """Esconderlos dejaria al administrador sin forma de reactivar a nadie
    desde la pantalla, y la baja de este sistema es logica justamente para que
    la persona siga estando."""
    creado = _crear(cliente, admin).json()
    cliente.post(
        f"{USUARIOS}/{creado['id']}/estado", json={"activo": False}, headers=admin
    )

    cuerpo = cliente.get(USUARIOS, headers=admin).json()

    assert creado["id"] in [u["id"] for u in cuerpo]


def test_el_listado_nunca_trae_el_hash(cliente, admin):
    _crear(cliente, admin)

    respuesta = cliente.get(USUARIOS, headers=admin)

    assert "password_hash" not in respuesta.text


def test_el_detalle_trae_los_permisos_del_rol(cliente, admin):
    """La misma fila de la matriz que viaja en `/auth/me`, por el mismo motivo:
    que el frontend no vuelva a declarar la matriz."""
    creado = _crear(cliente, admin, rol=autorizacion.ENCARGADO).json()

    cuerpo = cliente.get(f"{USUARIOS}/{creado['id']}", headers=admin).json()

    assert cuerpo["rol_etiqueta"] == "Encargado"
    assert cuerpo["permisos"]["ve_financiero_edificio"] is False


def test_un_id_que_no_existe_da_404(cliente, admin):
    respuesta = cliente.get(f"{USUARIOS}/9999", headers=admin)

    assert respuesta.status_code == 404


# ---------------------------------------------------------------- permisos ---


@pytest.mark.parametrize(
    "rol", [r for r in autorizacion.ROLES if r != autorizacion.ADMIN_GENERAL]
)
def test_ningun_otro_rol_entra_a_ninguno_de_los_endpoints(cliente, como, rol):
    """El caso prohibido, contra los siete roles y los cinco endpoints.

    Se recorren todos y no uno de muestra: el agujero tipico no es olvidarse de
    proteger el modulo, es olvidarse de proteger **un** endpoint del modulo, y
    el que suele quedar afuera es el que se agrego ultimo.
    """
    header = como(rol)

    assert cliente.post(USUARIOS, json=ALTA_VALIDA, headers=header).status_code == 403
    assert cliente.get(USUARIOS, headers=header).status_code == 403
    assert cliente.get(f"{USUARIOS}/1", headers=header).status_code == 403
    assert cliente.patch(f"{USUARIOS}/1", json={}, headers=header).status_code == 403
    assert (
        cliente.post(
            f"{USUARIOS}/1/estado", json={"activo": False}, headers=header
        ).status_code
        == 403
    )


def test_sin_token_el_rechazo_es_401_y_no_403(cliente):
    assert cliente.get(USUARIOS).status_code == 401


def test_el_rechazo_por_rol_ocurre_antes_de_tocar_la_base(cliente, db, como):
    """Un 403 no puede dejar rastro. Si el endpoint creara el usuario y recien
    despues verificara el permiso, el rechazo seria cosmetico."""
    respuesta = cliente.post(
        USUARIOS, json=ALTA_VALIDA, headers=como(autorizacion.PROPIETARIO)
    )

    assert respuesta.status_code == 403
    assert db.scalar(select(Usuario).where(Usuario.email == "ana@ejemplo.com")) is None


# ---------------------------------------------------------------- edicion ----


def test_se_puede_editar_un_solo_campo(cliente, admin):
    creado = _crear(cliente, admin).json()

    respuesta = cliente.patch(
        f"{USUARIOS}/{creado['id']}", json={"nombre": "Ana Maria Suarez"}, headers=admin
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Ana Maria Suarez"


def test_lo_que_no_se_manda_queda_como_estaba(cliente, admin):
    """La mitad de la semantica de PATCH. Sin `exclude_unset`, cada campo
    ausente llegaria como `None` y editar el nombre borraria el telefono."""
    creado = _crear(cliente, admin).json()

    cuerpo = cliente.patch(
        f"{USUARIOS}/{creado['id']}", json={"nombre": "Ana Maria"}, headers=admin
    ).json()

    assert cuerpo["telefono"] == ALTA_VALIDA["telefono"]
    assert cuerpo["email"] == ALTA_VALIDA["email"]
    assert cuerpo["rol"] == ALTA_VALIDA["rol"]


def test_mandar_null_borra_el_campo_opcional(cliente, admin):
    """La otra mitad. Si no se pudiera distinguir de "no lo mandes", no habria
    forma de borrar un telefono mal cargado."""
    creado = _crear(cliente, admin).json()

    cuerpo = cliente.patch(
        f"{USUARIOS}/{creado['id']}", json={"telefono": None}, headers=admin
    ).json()

    assert cuerpo["telefono"] is None


def test_mandar_null_en_un_campo_obligatorio_da_422_y_no_500(cliente, admin):
    """Los campos obligatorios se escriben `tipo | None` para poder omitirlos,
    asi que el tipo acepta `null`. Sin la guarda del esquema, un
    `{"nombre": null}` reventaria en `None.strip()` con un 500."""
    creado = _crear(cliente, admin).json()

    respuesta = cliente.patch(
        f"{USUARIOS}/{creado['id']}", json={"nombre": None}, headers=admin
    )

    assert respuesta.status_code == 422


def test_un_patch_vacio_no_cambia_nada(cliente, admin):
    creado = _crear(cliente, admin).json()

    respuesta = cliente.patch(f"{USUARIOS}/{creado['id']}", json={}, headers=admin)

    assert respuesta.status_code == 200
    assert respuesta.json() == creado


def test_se_puede_cambiar_el_email_y_el_nuevo_sirve_para_entrar(cliente, admin):
    creado = _crear(cliente, admin).json()

    cliente.patch(
        f"{USUARIOS}/{creado['id']}", json={"email": "ANA.NUEVA@Ejemplo.com"}, headers=admin
    )

    login = cliente.post(
        "/api/auth/login",
        data={"username": "ana.nueva@ejemplo.com", "password": ALTA_VALIDA["password"]},
    )
    assert login.status_code == 200, login.text


def test_reenviar_el_mismo_email_sin_cambiarlo_no_es_un_duplicado(cliente, admin):
    """Un formulario que manda todos sus campos reenvia el email tal cual. Sin
    la excepcion por id, cada edicion desde la pantalla seria rechazada."""
    creado = _crear(cliente, admin).json()

    respuesta = cliente.patch(
        f"{USUARIOS}/{creado['id']}", json={"email": creado["email"]}, headers=admin
    )

    assert respuesta.status_code == 200


def test_no_se_puede_tomar_el_email_de_otro_usuario(cliente, admin):
    primero = _crear(cliente, admin).json()
    _crear(cliente, admin, email="otro@ejemplo.com", nombre="Otra Persona")

    respuesta = cliente.patch(
        f"{USUARIOS}/{primero['id']}", json={"email": "otro@ejemplo.com"}, headers=admin
    )

    assert respuesta.status_code == 400


def test_se_puede_cambiarle_el_rol_a_otro(cliente, admin):
    creado = _crear(cliente, admin).json()

    cuerpo = cliente.patch(
        f"{USUARIOS}/{creado['id']}", json={"rol": autorizacion.ENCARGADO}, headers=admin
    ).json()

    assert cuerpo["rol"] == autorizacion.ENCARGADO
    assert cuerpo["permisos"]["alcance"] == autorizacion.ALCANCE_EDIFICIO


def test_el_patch_no_acepta_una_contrasenia(cliente, db, admin):
    """No esta en el esquema a proposito: cambiar la contrasenia de alguien es
    otra operacion, con otras reglas. Si colara por acá, un administrador le
    pisaria la contrasenia a cualquiera sin que la persona se entere."""
    creado = _crear(cliente, admin).json()

    cliente.patch(
        f"{USUARIOS}/{creado['id']}", json={"password": "OtraClave999!"}, headers=admin
    )

    usuario = db.scalar(select(Usuario).where(Usuario.id == creado["id"]))
    assert security.verificar_password("OtraClave999!", usuario.password_hash) is False
    assert security.verificar_password(ALTA_VALIDA["password"], usuario.password_hash)


# ------------------------------------------- no dejarse afuera a si mismo ----


def test_un_administrador_no_puede_desactivarse_a_si_mismo_por_el_endpoint(
    cliente, db, admin
):
    """No es teorico: paso. El login rechaza inactivos, hace falta otro
    administrador para reactivar, y la cuenta quedo irrecuperable."""
    yo = db.scalar(select(Usuario).where(Usuario.rol == autorizacion.ADMIN_GENERAL))

    respuesta = cliente.post(
        f"{USUARIOS}/{yo.id}/estado", json={"activo": False}, headers=admin
    )

    assert respuesta.status_code == 400
    db.refresh(yo)
    assert yo.activo is True


def test_un_administrador_no_puede_desactivarse_a_si_mismo_por_el_patch(
    cliente, db, admin
):
    """La misma regla por la otra via. Protegerla en un solo endpoint la deja
    sin proteger: el PATCH tambien escribe `activo`."""
    yo = db.scalar(select(Usuario).where(Usuario.rol == autorizacion.ADMIN_GENERAL))

    respuesta = cliente.patch(
        f"{USUARIOS}/{yo.id}", json={"activo": False}, headers=admin
    )

    assert respuesta.status_code == 400
    db.refresh(yo)
    assert yo.activo is True


def test_un_administrador_no_puede_cambiarse_el_rol_a_si_mismo(cliente, db, admin):
    """Misma familia que la auto-desactivacion y el mismo resultado: al dejar
    de ser Administrador General pierde en ese instante el permiso para volver
    a cambiarselo."""
    yo = db.scalar(select(Usuario).where(Usuario.rol == autorizacion.ADMIN_GENERAL))

    respuesta = cliente.patch(
        f"{USUARIOS}/{yo.id}", json={"rol": autorizacion.PROPIETARIO}, headers=admin
    )

    assert respuesta.status_code == 400
    db.refresh(yo)
    assert yo.rol == autorizacion.ADMIN_GENERAL


def test_mandarse_el_rol_que_ya_tiene_no_es_un_cambio(cliente, db, admin):
    """Un formulario que reenvia todos los campos manda tambien el rol actual.
    Rechazar eso bloquearia a un administrador para editarse el telefono."""
    yo = db.scalar(select(Usuario).where(Usuario.rol == autorizacion.ADMIN_GENERAL))

    respuesta = cliente.patch(
        f"{USUARIOS}/{yo.id}",
        json={"rol": autorizacion.ADMIN_GENERAL, "telefono": "11 1234 5678"},
        headers=admin,
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["telefono"] == "11 1234 5678"


def test_un_administrador_puede_editarse_lo_demas_a_si_mismo(cliente, db, admin):
    """Las guardas tienen que ser lo mas chicas posible: impiden quedarse
    afuera, no editarse."""
    yo = db.scalar(select(Usuario).where(Usuario.rol == autorizacion.ADMIN_GENERAL))

    respuesta = cliente.patch(
        f"{USUARIOS}/{yo.id}", json={"nombre": "Gustavo Oliva"}, headers=admin
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Gustavo Oliva"


def test_un_pedido_rechazado_no_deja_a_medias_los_otros_campos(cliente, db, admin):
    """Por eso las guardas corren antes de aplicar cualquier cambio. Si
    corrieran despues, este pedido quedaria rechazado con el nombre ya
    modificado."""
    yo = db.scalar(select(Usuario).where(Usuario.rol == autorizacion.ADMIN_GENERAL))
    nombre_original = yo.nombre

    respuesta = cliente.patch(
        f"{USUARIOS}/{yo.id}",
        json={"nombre": "Nombre Nuevo", "activo": False},
        headers=admin,
    )

    assert respuesta.status_code == 400
    db.refresh(yo)
    assert yo.nombre == nombre_original


def test_otro_administrador_si_puede_desactivarlo(cliente, db, admin):
    """La guarda es contra quedarse afuera uno mismo, no contra dar de baja a
    un administrador. Y como siempre la aplica otro usuario —que por definicion
    sigue activo—, el sistema nunca puede quedar sin ningun administrador."""
    otro = _crear(
        cliente,
        admin,
        email="otro.admin@ejemplo.com",
        nombre="Otro Admin",
        rol=autorizacion.ADMIN_GENERAL,
    ).json()

    respuesta = cliente.post(
        f"{USUARIOS}/{otro['id']}/estado", json={"activo": False}, headers=admin
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False


# ----------------------------------------------------------------- estado ----


def test_se_puede_desactivar_y_reactivar(cliente, admin):
    creado = _crear(cliente, admin).json()
    ruta = f"{USUARIOS}/{creado['id']}/estado"

    baja = cliente.post(ruta, json={"activo": False}, headers=admin)
    assert baja.json()["activo"] is False

    alta = cliente.post(ruta, json={"activo": True}, headers=admin)
    assert alta.json()["activo"] is True


def test_desactivar_dos_veces_no_es_un_error(cliente, admin):
    """El pedido dice el estado deseado, no la transicion: asi no depende de
    que el frontend tenga el estado actual al dia, que es una suposicion que se
    rompe con dos pestanias abiertas."""
    creado = _crear(cliente, admin).json()
    ruta = f"{USUARIOS}/{creado['id']}/estado"

    cliente.post(ruta, json={"activo": False}, headers=admin)
    segunda = cliente.post(ruta, json={"activo": False}, headers=admin)

    assert segunda.status_code == 200
    assert segunda.json()["activo"] is False


def test_el_desactivado_no_puede_iniciar_sesion(cliente, admin):
    """La baja tiene que tener efecto de verdad, no solo cambiar un campo."""
    creado = _crear(cliente, admin).json()
    cliente.post(
        f"{USUARIOS}/{creado['id']}/estado", json={"activo": False}, headers=admin
    )

    login = cliente.post(
        "/api/auth/login",
        data={"username": creado["email"], "password": ALTA_VALIDA["password"]},
    )

    assert login.status_code == 401


def test_el_token_de_un_usuario_recien_desactivado_deja_de_valer(cliente, db, admin):
    """De punta a punta: la baja desde el CRUD corta la sesion que ya estaba
    abierta, sin esperar a que el token venza."""
    creado = _crear(cliente, admin).json()
    token = cliente.post(
        "/api/auth/login",
        data={"username": creado["email"], "password": ALTA_VALIDA["password"]},
    ).json()["access_token"]
    suyo = {"Authorization": f"Bearer {token}"}
    assert cliente.get("/api/auth/me", headers=suyo).status_code == 200

    cliente.post(
        f"{USUARIOS}/{creado['id']}/estado", json={"activo": False}, headers=admin
    )

    assert cliente.get("/api/auth/me", headers=suyo).status_code == 401


def test_cambiar_el_estado_de_un_id_inexistente_da_404(cliente, admin):
    respuesta = cliente.post(
        f"{USUARIOS}/9999/estado", json={"activo": False}, headers=admin
    )

    assert respuesta.status_code == 404


def test_el_cuerpo_del_cambio_de_estado_es_obligatorio(cliente, admin):
    """`activo` va en el cuerpo y no en la URL: `?activo=false` se copia, se
    comparte y se llama por accidente desde la barra de direcciones, y esto
    cambia quien puede entrar al sistema."""
    creado = _crear(cliente, admin).json()

    respuesta = cliente.post(f"{USUARIOS}/{creado['id']}/estado", headers=admin)

    assert respuesta.status_code == 422


def test_el_usuario_de_prueba_sigue_teniendo_su_contrasenia(cliente, db, admin):
    """Guarda contra un error de fixture, no del codigo: si `como()` dejara de
    crear usuarios con `PASSWORD_DE_PRUEBA`, media docena de tests de este
    archivo pasarian a fallar por un motivo que no tiene nada que ver con lo
    que prueban."""
    yo = db.scalar(select(Usuario).where(Usuario.rol == autorizacion.ADMIN_GENERAL))

    assert security.verificar_password(PASSWORD_DE_PRUEBA, yo.password_hash)


def test_un_campo_mal_escrito_se_rechaza_en_vez_de_ignorarse(cliente, admin):
    """Pydantic por defecto descarta en silencio lo que no conoce, y en un
    formulario eso devuelve 200 sin haber guardado nada: la persona ve que se
    guardo bien y no se guardo."""
    creado = _crear(cliente, admin).json()

    respuesta = cliente.patch(
        f"{USUARIOS}/{creado['id']}", json={"nombres": "Ana Maria"}, headers=admin
    )

    assert respuesta.status_code == 422
    assert "nombres" in respuesta.text


def test_el_alta_no_acepta_fijar_el_estado(cliente, admin):
    """`activo` no esta en el esquema de alta: un usuario nace activo. Mandarlo
    es un error explicito y no un campo que se descarta sin avisar."""
    respuesta = _crear(cliente, admin, activo=False)

    assert respuesta.status_code == 422

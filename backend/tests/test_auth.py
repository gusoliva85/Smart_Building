"""Pruebas de `routers/auth.py` — login y sesion.

Son los primeros tests de la suite que pegan contra HTTP de verdad, y fijan el
patron del resto del proyecto: **siempre el caso permitido Y el prohibido.**

Lo que mas importa acá no es que el login funcione, sino que no cuente nada que
no deba: que no se pueda averiguar si un email esta registrado, y que la baja
de un usuario tenga efecto en el momento y no cuando su token venza.
"""

import pytest
from sqlalchemy import select

from app.core import security
from app.models.usuario import Usuario
from app.services import autorizacion
from tests.conftest import PASSWORD_DE_PRUEBA

LOGIN = "/api/auth/login"
ME = "/api/auth/me"


@pytest.fixture
def usuario(db):
    """Un administrador de consorcio activo, con contrasenia conocida."""
    u = Usuario(
        nombre="Ana Suarez",
        email="ana@ejemplo.com",
        password_hash=security.hashear_password(PASSWORD_DE_PRUEBA),
        rol=autorizacion.ADMIN_CONSORCIO,
    )
    db.add(u)
    db.commit()
    return u


def _login(cliente, email, password):
    return cliente.post(LOGIN, data={"username": email, "password": password})


# ------------------------------------------------------- login que anda -----


def test_el_login_con_credenciales_correctas_devuelve_un_token(cliente, usuario):
    respuesta = _login(cliente, usuario.email, PASSWORD_DE_PRUEBA)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    assert security.usuario_id_del_token(cuerpo["access_token"]) == usuario.id


def test_el_token_del_login_sirve_para_entrar_a_me(cliente, usuario):
    """El circuito completo, que es lo que hace el frontend al cargar."""
    token = _login(cliente, usuario.email, PASSWORD_DE_PRUEBA).json()["access_token"]

    respuesta = cliente.get(ME, headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json()["email"] == usuario.email


def test_se_puede_entrar_escribiendo_el_email_con_mayusculas(cliente, usuario):
    """La normalizacion del login tiene que ser la misma que la del alta.

    Sin esto, quien se da de alta como `Ana@...` queda guardado en minusculas y
    no entra escribiendo exactamente lo mismo que puso al registrarse — y lo
    unico que ve es "credenciales incorrectas".
    """
    respuesta = _login(cliente, "  ANA@Ejemplo.COM  ", PASSWORD_DE_PRUEBA)

    assert respuesta.status_code == 200


def test_el_login_no_devuelve_el_hash_ni_la_contrasenia(cliente, usuario):
    respuesta = _login(cliente, usuario.email, PASSWORD_DE_PRUEBA)

    assert PASSWORD_DE_PRUEBA not in respuesta.text
    assert "password" not in respuesta.text


# ------------------------------------------------------ login que no anda ----


@pytest.mark.parametrize(
    "email, password, caso",
    [
        ("ana@ejemplo.com", "OtraClave123!", "contrasenia incorrecta"),
        ("nadie@ejemplo.com", PASSWORD_DE_PRUEBA, "el email no existe"),
        ("nadie@ejemplo.com", "OtraClave123!", "ninguna de las dos"),
    ],
)
def test_las_credenciales_malas_dan_401(cliente, usuario, email, password, caso):
    respuesta = _login(cliente, email, password)

    assert respuesta.status_code == 401, caso


def test_el_error_es_identico_exista_o_no_el_email(cliente, usuario):
    """El que de verdad importa de este archivo.

    Si "ese email no existe" y "esa contrasenia es incorrecta" dieran
    respuestas distintas, el login se convertiria en una herramienta para
    averiguar que direcciones estan registradas, probando emails de a uno.
    """
    existe = _login(cliente, usuario.email, "ClaveEquivocada1!")
    no_existe = _login(cliente, "fantasma@ejemplo.com", "ClaveEquivocada1!")

    assert existe.status_code == no_existe.status_code
    assert existe.json() == no_existe.json()


def test_un_usuario_inactivo_no_puede_iniciar_sesion(cliente, db, usuario):
    usuario.activo = False
    db.commit()

    respuesta = _login(cliente, usuario.email, PASSWORD_DE_PRUEBA)

    assert respuesta.status_code == 401


def test_el_usuario_inactivo_da_el_mismo_error_que_la_contrasenia_mala(
    cliente, db, usuario
):
    """Distinguirlo le confirmaria a quien prueba que esa cuenta existe."""
    inactivo = _login(cliente, usuario.email, PASSWORD_DE_PRUEBA)  # todavia activo
    assert inactivo.status_code == 200

    usuario.activo = False
    db.commit()

    desactivado = _login(cliente, usuario.email, PASSWORD_DE_PRUEBA)
    clave_mala = _login(cliente, usuario.email, "ClaveEquivocada1!")

    assert desactivado.json() == clave_mala.json()


# -------------------------------------------------------------- /auth/me -----


def test_me_sin_token_da_401(cliente):
    assert cliente.get(ME).status_code == 401


def test_el_mensaje_es_el_mismo_falte_el_token_o_sea_invalido(cliente):
    """Con el comportamiento por defecto de FastAPI no lo era: cuando falta el
    header, el esquema de OAuth2 corta antes que la dependencia y responde
    `"Not authenticated"` —en ingles, y distinto del mensaje del token
    invalido—. Dos textos para la misma situacion, y uno en otro idioma que el
    resto de la aplicacion, apareciendo en la pantalla del usuario.
    """
    sin_token = cliente.get(ME)
    invalido = cliente.get(ME, headers={"Authorization": "Bearer cualquier-cosa"})

    assert sin_token.json() == invalido.json()
    assert "authenticated" not in sin_token.text.lower()


@pytest.mark.parametrize(
    "header",
    [
        {"Authorization": "Bearer no-es-un-token"},
        {"Authorization": "Bearer "},
        {"Authorization": "token-sin-el-esquema"},
    ],
)
def test_me_con_un_token_invalido_da_401(cliente, header):
    assert cliente.get(ME, headers=header).status_code == 401


def test_me_con_un_token_vencido_da_401(cliente, usuario):
    vencido = security.crear_token_de_acceso(usuario.id, minutos=-1)

    respuesta = cliente.get(ME, headers={"Authorization": f"Bearer {vencido}"})

    assert respuesta.status_code == 401


def test_el_token_de_un_usuario_desactivado_deja_de_valer_en_el_momento(
    cliente, db, usuario
):
    """La regla central de la tarea: el estado del usuario se verifica en CADA
    request, no solo la firma del token.

    Un token vive 60 minutos. Si solo se validara la firma, alguien que acaba
    de ser desactivado seguiria operando con todos sus permisos durante casi
    una hora.
    """
    token = _login(cliente, usuario.email, PASSWORD_DE_PRUEBA).json()["access_token"]
    header = {"Authorization": f"Bearer {token}"}
    assert cliente.get(ME, headers=header).status_code == 200

    usuario.activo = False
    db.commit()

    assert cliente.get(ME, headers=header).status_code == 401


def test_el_token_de_un_usuario_borrado_no_sirve(cliente, db, usuario):
    """La baja del sistema es logica, pero un borrado a mano en la base no
    puede dejar un token con firma valida funcionando."""
    token = _login(cliente, usuario.email, PASSWORD_DE_PRUEBA).json()["access_token"]
    db.delete(usuario)
    db.commit()

    respuesta = cliente.get(ME, headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 401


def test_me_nunca_devuelve_el_hash_de_la_contrasenia(cliente, usuario):
    """Que el esquema de salida sea una clase aparte es lo que lo hace
    imposible: no alcanza con olvidarse de excluirlo, habria que agregarlo."""
    token = _login(cliente, usuario.email, PASSWORD_DE_PRUEBA).json()["access_token"]

    cuerpo = cliente.get(ME, headers={"Authorization": f"Bearer {token}"}).json()

    assert "password_hash" not in cuerpo
    assert usuario.password_hash not in str(cuerpo)


# ---------------------------------------- la matriz que viaja en /auth/me ----


def test_me_trae_la_etiqueta_legible_del_rol(cliente, usuario):
    """La resuelve la matriz, no el frontend: "Administrador de Consorcio" es
    un dato del rol, y escribirlo en el HTML seria una traduccion paralela."""
    token = _login(cliente, usuario.email, PASSWORD_DE_PRUEBA).json()["access_token"]

    cuerpo = cliente.get(ME, headers={"Authorization": f"Bearer {token}"}).json()

    assert cuerpo["rol"] == autorizacion.ADMIN_CONSORCIO
    assert cuerpo["rol_etiqueta"] == "Administrador de Consorcio"


@pytest.mark.parametrize("rol", autorizacion.ROLES)
def test_me_trae_los_permisos_de_la_matriz_para_cada_rol(cliente, como, rol):
    """Los ocho roles, contra la matriz. Asi el frontend no vuelve a declarar
    quien ve montos y quien es de solo lectura: si tuviera su propia copia,
    el dia que una cambie la interfaz mostraria botones que el backend rechaza.
    """
    cuerpo = cliente.get(ME, headers=como(rol)).json()
    esperado = autorizacion.obtener(rol)

    assert cuerpo["permisos"] == {
        "alcance": esperado.alcance,
        "ve_financiero_unidad": esperado.ve_financiero_unidad,
        "ve_financiero_edificio": esperado.ve_financiero_edificio,
        "solo_lectura": esperado.solo_lectura,
    }


def test_el_encargado_recibe_que_no_ve_montos(cliente, como):
    """La regla de negocio mas repetida del proyecto, verificada de punta a
    punta: ve el semaforo del edificio, nunca los importes."""
    cuerpo = cliente.get(ME, headers=como(autorizacion.ENCARGADO)).json()

    assert cuerpo["permisos"]["ve_financiero_edificio"] is False
    assert cuerpo["permisos"]["ve_financiero_unidad"] is False


def test_el_auditor_recibe_que_es_de_solo_lectura(cliente, como):
    cuerpo = cliente.get(ME, headers=como(autorizacion.AUDITOR)).json()

    assert cuerpo["permisos"]["solo_lectura"] is True


# ------------------------------------------------- el helper de la suite -----


def test_el_helper_como_crea_un_usuario_por_llamada(cliente, db, como):
    """Dos llamadas al mismo rol no pueden chocar por el email, para que un
    test pueda pedir dos usuarios del mismo rol."""
    primero = como(autorizacion.PROPIETARIO)
    segundo = como(autorizacion.PROPIETARIO)

    assert primero != segundo
    assert len(db.scalars(select(Usuario)).all()) == 2

"""Pruebas de las dependencias de autorizacion de `core/dependencies.py`.

La autenticacion (`obtener_usuario_actual`) ya esta probada en `test_auth.py`,
a traves de `/auth/me`. Acá se prueba la otra mitad: quien puede hacer que, y
que el rechazo sea un **403 y no un 401**.

============================================================================
POR QUE ESTOS TESTS MONTAN SU PROPIA APLICACION
============================================================================

Las dependencias son genericas y todavia no hay ningun endpoint del proyecto
que las use: el primero es el CRUD de usuarios de `F1-T09`. Probarlas recien
cuando exista ese CRUD mezclaria dos cosas —las reglas de la dependencia y las
reglas del endpoint— y dejaria la dependencia sin test propio.

Asi que se montan endpoints de juguete en una aplicacion aparte. **Aparte y no
sobre `app.main.app`** a proposito: agregar rutas de prueba a la aplicacion
real las deja registradas en el objeto que se despliega.
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.dependencies import (
    SoloAdminGeneral,
    SoloAdministradores,
    UsuarioActual,
    UsuarioQuePuedeEscribir,
    exigir_que_pueda_escribir,
    exigir_roles,
)
from app.database import obtener_db
from app.services import autorizacion

# --------------------------------------------------- aplicacion de juguete ---

juguete = FastAPI()


@juguete.get("/cualquiera")
def cualquiera(usuario: UsuarioActual):
    return {"rol": usuario.rol}


@juguete.get("/solo-admin-general")
def solo_admin_general(usuario: SoloAdminGeneral):
    return {"rol": usuario.rol}


@juguete.get("/solo-administradores")
def solo_administradores(usuario: SoloAdministradores):
    return {"rol": usuario.rol}


@juguete.get("/escritura")
def escritura(usuario: UsuarioQuePuedeEscribir):
    return {"rol": usuario.rol}


@juguete.get(
    "/escritura-de-administrador",
    dependencies=[Depends(exigir_que_pueda_escribir)],
)
def escritura_de_administrador(usuario: SoloAdministradores):
    """El caso compuesto, que es el que de verdad se va a usar: hay que ser
    administrador Y no ser de solo lectura."""
    return {"rol": usuario.rol}


@juguete.get("/encargado-o-seguridad")
def encargado_o_seguridad(
    usuario=Depends(exigir_roles(autorizacion.ENCARGADO, autorizacion.SEGURIDAD)),
):
    return {"rol": usuario.rol}


@pytest.fixture
def cliente_juguete(db):
    """Cliente sobre la aplicacion de juguete, con la base de prueba.

    Se limpian los reemplazos al terminar, por la misma razon que en el cliente
    de `conftest.py`: si quedaran activos, el origen del problema en un test
    posterior seria imposible de adivinar.
    """

    def obtener_db_de_prueba():
        yield db

    juguete.dependency_overrides[obtener_db] = obtener_db_de_prueba
    try:
        yield TestClient(juguete)
    finally:
        juguete.dependency_overrides.clear()


# ------------------------------------------------------------ exigir_roles ---


def test_el_rol_permitido_pasa(cliente_juguete, como):
    respuesta = cliente_juguete.get(
        "/solo-admin-general", headers=como(autorizacion.ADMIN_GENERAL)
    )

    assert respuesta.status_code == 200


@pytest.mark.parametrize(
    "rol", [r for r in autorizacion.ROLES if r != autorizacion.ADMIN_GENERAL]
)
def test_los_otros_siete_roles_reciben_403(cliente_juguete, como, rol):
    """El caso prohibido para **todos** los roles que no son el permitido, no
    para uno de muestra: una lista mal escrita puede dejar pasar justo al que
    nadie probo."""
    respuesta = cliente_juguete.get("/solo-admin-general", headers=como(rol))

    assert respuesta.status_code == 403


def test_una_dependencia_de_varios_roles_deja_pasar_a_todos_los_de_la_lista(
    cliente_juguete, como
):
    for rol in (autorizacion.ENCARGADO, autorizacion.SEGURIDAD):
        respuesta = cliente_juguete.get("/encargado-o-seguridad", headers=como(rol))
        assert respuesta.status_code == 200, rol

    ajeno = cliente_juguete.get(
        "/encargado-o-seguridad", headers=como(autorizacion.PROPIETARIO)
    )
    assert ajeno.status_code == 403


def test_el_administrador_general_entra_a_lo_de_los_administradores(
    cliente_juguete, como
):
    """Regla del proyecto: el Administrador General alcanza todo lo del
    Administrador de Consorcio. Si esa lista se escribiera sin el, quedaria
    afuera de pantallas que justamente administra."""
    respuesta = cliente_juguete.get(
        "/solo-administradores", headers=como(autorizacion.ADMIN_GENERAL)
    )

    assert respuesta.status_code == 200


def test_el_mensaje_del_403_dice_para_quien_es_la_accion(cliente_juguete, como):
    """Un 403 sin explicacion obliga a leer el codigo para saber que hacia
    falta. El mensaje usa la etiqueta legible, no el nombre tecnico del rol."""
    respuesta = cliente_juguete.get(
        "/solo-admin-general", headers=como(autorizacion.PROPIETARIO)
    )

    assert "Administrador General" in respuesta.json()["detail"]


# ---------------------------------------------- 403 y 401 no son lo mismo ----


def test_sin_token_el_rechazo_es_401_y_no_403(cliente_juguete):
    """La distincion importa de verdad: el envoltorio de `fetch` del frontend
    trata el 401 limpiando la sesion y mandando al login. Si un permiso
    insuficiente diera 401, desloguearia a alguien perfectamente logueado y le
    mostraria "tu sesion vencio", que no tiene nada que ver con lo que paso.
    """
    assert cliente_juguete.get("/solo-admin-general").status_code == 401


def test_con_token_valido_y_rol_insuficiente_el_rechazo_es_403(cliente_juguete, como):
    respuesta = cliente_juguete.get(
        "/solo-admin-general", headers=como(autorizacion.INQUILINO)
    )

    assert respuesta.status_code == 403


def test_el_403_no_lleva_el_header_de_volver_a_autenticarse(cliente_juguete, como):
    """`WWW-Authenticate` significa "volve a autenticarte", y la autenticacion
    salio bien. Mandarlo haria que el boton Authorize de /docs vuelva a pedir
    credenciales para un problema que las credenciales no resuelven."""
    respuesta = cliente_juguete.get(
        "/solo-admin-general", headers=como(autorizacion.INQUILINO)
    )

    assert "WWW-Authenticate" not in respuesta.headers


def test_un_usuario_desactivado_recibe_401_aunque_tenga_el_rol(
    cliente_juguete, db, como
):
    """La autorizacion corre **despues** de la autenticacion, no en paralelo:
    el rol correcto no salva a una cuenta dada de baja."""
    from sqlalchemy import select

    from app.models.usuario import Usuario

    header = como(autorizacion.ADMIN_GENERAL)
    assert cliente_juguete.get("/solo-admin-general", headers=header).status_code == 200

    usuario = db.scalar(select(Usuario).where(Usuario.rol == autorizacion.ADMIN_GENERAL))
    usuario.activo = False
    db.commit()

    respuesta = cliente_juguete.get("/solo-admin-general", headers=header)

    assert respuesta.status_code == 401


# ------------------------------------------------ exigir_que_pueda_escribir --


def test_el_auditor_no_puede_escribir(cliente_juguete, como):
    """La regla de `F1-T01`: el Auditor ve todo y no modifica nada."""
    respuesta = cliente_juguete.get("/escritura", headers=como(autorizacion.AUDITOR))

    assert respuesta.status_code == 403


@pytest.mark.parametrize(
    "rol", [r for r in autorizacion.ROLES if not autorizacion.es_solo_lectura(r)]
)
def test_los_roles_que_no_son_de_solo_lectura_pasan(cliente_juguete, como, rol):
    """Se recorren contra la matriz, no contra una lista escrita a mano: el dia
    que un rol pase a ser de solo lectura, este test lo sigue sin tocarlo."""
    respuesta = cliente_juguete.get("/escritura", headers=como(rol))

    assert respuesta.status_code == 200


def test_el_mensaje_explica_que_es_un_rol_de_consulta(cliente_juguete, como):
    respuesta = cliente_juguete.get("/escritura", headers=como(autorizacion.AUDITOR))

    assert "consulta" in respuesta.json()["detail"].lower()


# ----------------------------------------------------- las dos combinadas ----


def test_el_endpoint_compuesto_exige_las_dos_condiciones(cliente_juguete, como):
    """El caso que explica por que la guarda de escritura es independiente del
    rol: el Auditor **ve** lo mismo que un administrador, asi que protegerlo
    solo con una lista de roles amplia lo dejaria escribir."""
    ruta = "/escritura-de-administrador"

    admin = cliente_juguete.get(ruta, headers=como(autorizacion.ADMIN_CONSORCIO))
    assert admin.status_code == 200

    propietario = cliente_juguete.get(ruta, headers=como(autorizacion.PROPIETARIO))
    assert propietario.status_code == 403


# ------------------------------------- validacion al construir, no al correr --


def test_un_rol_mal_escrito_revienta_al_declarar_la_dependencia():
    """El test mas importante del archivo.

    Si la validacion fuera al atender el request, `exigir_roles("encargdo")`
    dejaria ese endpoint rechazando a **todos** para siempre y sin un solo
    error en los logs: un rol que no existe no coincide con nadie. Se
    descubriria meses despues, cuando alguien reporte que no puede entrar a una
    pantalla.
    """
    with pytest.raises(autorizacion.RolDesconocido):
        exigir_roles("encargdo")


def test_exigir_roles_sin_roles_no_se_permite():
    """`exigir_roles()` vacio no deja pasar a nadie, que nunca es lo que se
    queria escribir."""
    with pytest.raises(ValueError, match="UsuarioActual"):
        exigir_roles()

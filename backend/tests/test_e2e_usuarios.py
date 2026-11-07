"""Prueba de punta a punta del Tema 1.4 — usuarios (F1-T16).

Que la diferencia de los otros archivos de tests
============================================================================

El resto de la suite prueba piezas: un servicio, un endpoint, una regla.
Este archivo prueba el RECORRIDO COMPLETO, en el orden en que lo hace una
persona el primer dia:

    sembrar -> entrar como Administrador General -> dar de alta un usuario de
    cada rol -> que cada uno entre -> que cada uno vea solo lo que le toca ->
    que nadie pueda desactivarse a si mismo -> que una contrasenia debil se
    rechace.

Por que vale la pena si cada pieza ya esta probada aparte: porque los errores
de integracion no viven dentro de una pieza, viven en las juntas. Dos casos
reales que un test de unidad no habria visto:

  - `/usuarios/opciones` devolvia 422 porque la ruta parametrizada
    `/usuarios/{usuario_id}` estaba declarada antes y se comia la literal. Los
    dos endpoints funcionaban; lo que estaba mal era el orden entre ellos.
  - El primer usuario creado en la iteracion anterior quedo inutilizable
    porque su contrasenia nunca se anoto. Ningun test lo detecto: cada pieza
    funcionaba, lo que faltaba era el recorrido.

Todo pasa por HTTP, con el login real
============================================================================

Ningun paso de este archivo toca la base directamente ni fabrica un token a
mano, con UNA excepcion: el administrador inicial, que se crea llamando a
`sembrar()` porque es exactamente lo que hace el sistema real — es el unico
usuario que no puede crear nadie desde la aplicacion.

A partir de ahi, todo es HTTP. Por eso este archivo NO usa el fixture `como`:
ese atajo inserta el usuario en la base y despues se loguea, lo cual es
perfecto para probar un endpoint, pero acortaria justamente el camino que esta
prueba viene a recorrer.

Lo que esta prueba NO cubre, y donde se cubre
============================================================================

El sidebar acotado por rol y el bloqueo de las pantallas ajenas viven en
`frontend/assets/js/layout.js`, que es JavaScript de navegador: no hay forma
de verificarlo desde pytest. Lo que SI se verifica aca es la mitad que
importa de verdad para la seguridad: que el backend rechace al rol que no
corresponde, pase lo que pase en la interfaz. La tabla de accesos del sidebar
decide que se MUESTRA; esto decide que se PUEDE. Ver la nota de F1-T16 en el
Roadmap para el detalle de como se verifico la parte de navegador.
"""

import pytest

from app.core import security
from app.seed import PASSWORD_ADMIN, sembrar
from app.services import autorizacion

# Los siete roles que el Administrador General da de alta. Sale de
# `autorizacion.ROLES` y no de una lista escrita a mano: el dia que se agregue
# un rol, esta prueba lo incluye sola y falla si el alta no lo soporta. Eso es
# el punto — una lista copiada aca envejeceria en silencio.
ROLES_A_CREAR = tuple(r for r in autorizacion.ROLES if r != autorizacion.ADMIN_GENERAL)

# La misma para todos y deliberadamente trivial, igual que la del seed. Cumple
# la politica: ocho caracteres, mayuscula, minuscula, numero y simbolo.
PASSWORD_E2E = "Test1234!"


def _entrar(cliente, email, password):
    """Login real. Devuelve (codigo, header de autorizacion o None)."""
    respuesta = cliente.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )
    if respuesta.status_code != 200:
        return respuesta.status_code, None
    token = respuesta.json()["access_token"]
    return 200, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin(db, cliente):
    """Siembra el administrador inicial y entra con el. El punto de partida."""
    resultado = sembrar(db)
    assert resultado.creado, "el seed deberia crear el admin en una base vacia"

    codigo, cabecera = _entrar(cliente, resultado.email, PASSWORD_ADMIN)
    assert codigo == 200, "el admin recien sembrado tiene que poder entrar"
    return cabecera


# ===========================================================================
# PASO 1 — el seed
# ===========================================================================


def test_el_seed_es_idempotente_y_deja_un_admin_que_puede_entrar(db, cliente):
    """Correrlo dos veces no duplica nada y la contrasenia sigue sirviendo.

    Lo segundo es lo que importa y es facil de pasar por alto: un seed que
    "no toca" al usuario existente pero le pisa el hash dejaria la base
    coherente y el login roto.
    """
    primero = sembrar(db)
    assert primero.creado

    segundo = sembrar(db)
    assert segundo.ya_existia
    assert segundo.email == primero.email

    codigo, cabecera = _entrar(cliente, primero.email, PASSWORD_ADMIN)
    assert codigo == 200
    assert cabecera is not None

    # Y sigue habiendo UNO solo.
    listado = cliente.get("/api/usuarios", headers=cabecera)
    assert listado.status_code == 200
    assert len(listado.json()) == 1
    assert listado.json()[0]["rol"] == autorizacion.ADMIN_GENERAL


# ===========================================================================
# PASO 2 — el alta de un usuario de cada rol
# ===========================================================================


def test_el_admin_da_de_alta_un_usuario_de_cada_rol_y_todos_pueden_entrar(
    cliente, admin
):
    """El recorrido central: siete altas y siete logins.

    Se verifica el login de CADA uno, no solo que el alta devuelva 201. Es la
    leccion de la iteracion anterior: un alta que responde 201 y despues no
    deja entrar es una cuenta perdida, porque no hay endpoint de recuperacion.
    """
    creados = {}

    for rol in ROLES_A_CREAR:
        email = f"{rol}@test.com"
        alta = cliente.post(
            "/api/usuarios",
            headers=admin,
            json={
                "nombre": f"Prueba {autorizacion.etiqueta(rol)}",
                "email": email,
                "password": PASSWORD_E2E,
                "rol": rol,
            },
        )
        assert alta.status_code == 201, f"{rol}: {alta.text}"

        cuerpo = alta.json()
        assert cuerpo["rol"] == rol
        assert cuerpo["activo"] is True
        # La contrasenia no vuelve nunca, ni hasheada.
        assert "password" not in cuerpo
        assert "password_hash" not in cuerpo

        codigo, cabecera = _entrar(cliente, email, PASSWORD_E2E)
        assert codigo == 200, f"{rol} no pudo entrar despues de ser creado"
        creados[rol] = cabecera

    # Los ocho: el sembrado mas los siete.
    listado = cliente.get("/api/usuarios", headers=admin).json()
    assert len(listado) == 1 + len(ROLES_A_CREAR)
    assert {u["rol"] for u in listado} == set(autorizacion.ROLES)

    # Y cada uno se ve a si mismo con su rol: confirma que el token emitido es
    # del usuario correcto y no de otro.
    for rol, cabecera in creados.items():
        yo = cliente.get("/api/auth/me", headers=cabecera)
        assert yo.status_code == 200
        assert yo.json()["rol"] == rol


# ===========================================================================
# PASO 3 — cada uno ve solo lo que le corresponde
# ===========================================================================


@pytest.mark.parametrize("rol", ROLES_A_CREAR)
def test_ningun_rol_que_no_sea_admin_general_llega_a_la_gestion_de_usuarios(
    cliente, admin, rol
):
    """La contracara del paso 2, y la que de verdad protege.

    El sidebar le oculta la pantalla a estos siete roles, pero ocultar un
    acceso es una cortesia, no un control: quien escriba la URL a mano llega
    igual. Asi que se prueba contra los CUATRO endpoints de la pantalla, uno
    por uno. Un 403 en el listado y un hueco en el alta seria exactamente el
    tipo de agujero que un test del listado solo no encuentra.
    """
    alta = cliente.post(
        "/api/usuarios",
        headers=admin,
        json={
            "nombre": "Ajeno",
            "email": f"ajeno-{rol}@test.com",
            "password": PASSWORD_E2E,
            "rol": rol,
        },
    )
    assert alta.status_code == 201
    ajeno_id = alta.json()["id"]

    codigo, cabecera = _entrar(cliente, f"ajeno-{rol}@test.com", PASSWORD_E2E)
    assert codigo == 200

    assert cliente.get("/api/usuarios", headers=cabecera).status_code == 403
    assert cliente.get("/api/usuarios/opciones", headers=cabecera).status_code == 403
    assert (
        cliente.post(
            "/api/usuarios",
            headers=cabecera,
            json={
                "nombre": "Intruso",
                "email": "intruso@test.com",
                "password": PASSWORD_E2E,
                "rol": autorizacion.ADMIN_GENERAL,
            },
        ).status_code
        == 403
    ), "un rol sin permiso no puede crear un administrador"
    assert (
        cliente.patch(
            f"/api/usuarios/{ajeno_id}",
            headers=cabecera,
            json={"nombre": "Yo mismo"},
        ).status_code
        == 403
    ), "ni siquiera puede editarse a si mismo por esta via"
    assert (
        cliente.post(
            f"/api/usuarios/{ajeno_id}/estado",
            headers=cabecera,
            json={"activo": False},
        ).status_code
        == 403
    )


def test_sin_sesion_no_se_llega_a_ningun_endpoint_de_usuarios(cliente):
    """Y sin token, 401 en todos. El paso que es facil dar por obvio."""
    assert cliente.get("/api/usuarios").status_code == 401
    assert cliente.get("/api/usuarios/opciones").status_code == 401
    assert cliente.get("/api/usuarios/1").status_code == 401
    assert cliente.patch("/api/usuarios/1", json={"nombre": "x"}).status_code == 401
    assert (
        cliente.post("/api/usuarios/1/estado", json={"activo": False}).status_code == 401
    )


# ===========================================================================
# PASO 4 — nadie se desactiva a si mismo
# ===========================================================================


def test_el_admin_no_puede_desactivarse_a_si_mismo_por_ninguna_via(cliente, admin):
    """Las DOS vias, porque son dos endpoints distintos.

    Si solo se cubriera `/estado` —que es el que usa el boton— quedaria
    abierta la de PATCH, que es la que usaria cualquiera con la API en la
    mano. Y el resultado de equivocarse no es un error cualquiera: es un
    sistema sin ningun administrador que pueda entrar, sin forma de arreglarlo
    desde la aplicacion.
    """
    yo = cliente.get("/api/auth/me", headers=admin).json()

    por_estado = cliente.post(
        f"/api/usuarios/{yo['id']}/estado", headers=admin, json={"activo": False}
    )
    assert por_estado.status_code == 400
    assert "propia cuenta" in por_estado.json()["detail"]

    por_patch = cliente.patch(
        f"/api/usuarios/{yo['id']}", headers=admin, json={"activo": False}
    )
    assert por_patch.status_code == 400

    # Y sigue entrando, que es lo unico que prueba que no se rompio nada.
    codigo, _ = _entrar(cliente, yo["email"], PASSWORD_ADMIN)
    assert codigo == 200

    # Tampoco puede sacarse el rol, que lo dejaria sin poder volver a entrar
    # a la pantalla aunque la cuenta siga activa.
    sin_rol = cliente.patch(
        f"/api/usuarios/{yo['id']}", headers=admin, json={"rol": "propietario"}
    )
    assert sin_rol.status_code == 400


def test_un_usuario_desactivado_deja_de_entrar_y_vuelve_al_reactivarse(cliente, admin):
    """El ciclo completo del boton de estado, visto desde la puerta.

    Importa el regreso tanto como la ida: desactivar es reversible, y si al
    reactivar la contrasenia no sirviera, "desactivar" seria en la practica
    borrar — exactamente lo contrario de lo que dice el mensaje de la
    confirmacion de F1-T15.
    """
    alta = cliente.post(
        "/api/usuarios",
        headers=admin,
        json={
            "nombre": "Prueba Encargado",
            "email": "encargado-ciclo@test.com",
            "password": PASSWORD_E2E,
            "rol": autorizacion.ENCARGADO,
        },
    )
    assert alta.status_code == 201
    id_usuario = alta.json()["id"]

    assert _entrar(cliente, "encargado-ciclo@test.com", PASSWORD_E2E)[0] == 200

    baja = cliente.post(
        f"/api/usuarios/{id_usuario}/estado", headers=admin, json={"activo": False}
    )
    assert baja.status_code == 200
    assert baja.json()["activo"] is False

    assert _entrar(cliente, "encargado-ciclo@test.com", PASSWORD_E2E)[0] == 401

    # Y sigue apareciendo en el listado: desactivado no es borrado.
    listado = cliente.get("/api/usuarios", headers=admin).json()
    assert any(u["id"] == id_usuario and u["activo"] is False for u in listado)

    alta_de_nuevo = cliente.post(
        f"/api/usuarios/{id_usuario}/estado", headers=admin, json={"activo": True}
    )
    assert alta_de_nuevo.status_code == 200
    assert _entrar(cliente, "encargado-ciclo@test.com", PASSWORD_E2E)[0] == 200


# ===========================================================================
# PASO 5 — la politica de contrasenias se aplica en el alta real
# ===========================================================================


@pytest.mark.parametrize(
    "password, por_que",
    [
        ("Ab1!", "corta: menos de ocho caracteres"),
        ("test1234!", "sin mayuscula"),
        ("TEST1234!", "sin minuscula"),
        ("TestTest!", "sin numero"),
        ("Test12345", "sin caracter especial"),
        ("", "vacia"),
    ],
)
def test_el_alta_rechaza_una_contrasenia_debil(cliente, admin, password, por_que):
    """Una por cada requisito, no "una debil" generica.

    Un solo caso debil pasa aunque haya exactamente un requisito funcionando:
    la contrasenia se rechaza igual y el test queda verde. Con uno por
    requisito, si alguno deja de aplicarse, falla ese y se sabe cual.
    """
    respuesta = cliente.post(
        "/api/usuarios",
        headers=admin,
        json={
            "nombre": "Debil",
            "email": "debil@test.com",
            "password": password,
            "rol": autorizacion.PROPIETARIO,
        },
    )
    assert respuesta.status_code == 422, f"se acepto una contrasenia {por_que}"

    # Y no quedo creado a medias.
    listado = cliente.get("/api/usuarios", headers=admin).json()
    assert not any(u["email"] == "debil@test.com" for u in listado)


def test_el_motivo_del_rechazo_enumera_los_requisitos_que_faltan(cliente, admin):
    """El 422 tiene que decir QUE falta, no "contrasenia invalida".

    Es la diferencia entre un formulario que se puede completar y uno donde se
    adivina. Y los textos son los MISMOS que anuncia `/usuarios/opciones`, asi
    que la ayuda del formulario y el error no pueden divergir.
    """
    respuesta = cliente.post(
        "/api/usuarios",
        headers=admin,
        json={
            "nombre": "Debil",
            "email": "debil2@test.com",
            "password": "",
            "rol": autorizacion.PROPIETARIO,
        },
    )
    assert respuesta.status_code == 422
    detalle = respuesta.text

    for texto in security.textos_de_requisitos():
        assert texto in detalle, f"el rechazo no menciona {texto!r}"


def test_la_ayuda_del_formulario_sale_del_mismo_lugar_que_la_validacion(
    cliente, admin
):
    """`/usuarios/opciones` no puede tener su propia copia de la politica."""
    opciones = cliente.get("/api/usuarios/opciones", headers=admin)
    assert opciones.status_code == 200
    cuerpo = opciones.json()

    assert cuerpo["password"]["minimo_caracteres"] == security.MIN_CARACTERES_PASSWORD
    assert cuerpo["password"]["maximo_bytes"] == security.MAX_BYTES_PASSWORD
    assert cuerpo["password"]["requisitos"] == list(security.textos_de_requisitos())

    # Y el catalogo de roles es el de la matriz, en el mismo orden.
    assert [r["nombre"] for r in cuerpo["roles"]] == list(autorizacion.ROLES)

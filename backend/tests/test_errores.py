"""Pruebas del catalogo unico de mensajes de error (`F1-T29`).

Lo que hay que probar aca no es que un endpoint devuelva 400 —eso ya lo
prueban los tests de cada dominio— sino las cuatro propiedades que hacen que
el catalogo sirva para algo:

  1. **La respuesta tiene la misma forma siempre**, venga de un endpoint, de
     una dependencia, de la validacion de Pydantic o del ruteo de FastAPI. Si
     cada origen devolviera una forma distinta, el frontend seguiria
     adivinando.
  2. **Ningun codigo esta duplicado** y todos tienen texto. Un codigo repetido
     dejaria dos errores distintos indistinguibles para el cliente.
  3. **Ningun mensaje esta en ingles.** Es la razon de la mitad de la tarea: el
     422 de Pydantic llegaba crudo a la pantalla.
  4. **Ningun mensaje nombra la estructura interna** (`FX-T11`). El catalogo
     vuelve esa regla verificable de una sola lectura, y este test la verifica
     de verdad en vez de confiar en la lectura.
"""

import re

import pytest

from app.core import errores
from app.services import autorizacion, finanzas

FORMA = {"codigo", "mensaje", "campos", "detail"}


# ===========================================================================
# 1. LA FORMA ES SIEMPRE LA MISMA
# ===========================================================================


def _forma_correcta(cuerpo: dict) -> bool:
    return (
        set(cuerpo) == FORMA
        and isinstance(cuerpo["codigo"], str)
        and isinstance(cuerpo["mensaje"], str)
        and isinstance(cuerpo["campos"], dict)
        and cuerpo["detail"] == cuerpo["mensaje"]
    )


def test_un_error_de_negocio_tiene_la_forma_del_catalogo(cliente, como):
    """El 400 de un endpoint: lo levanta `ErrorDeNegocio`."""
    respuesta = cliente.patch(
        "/api/edificios/1", json={}, headers=como(autorizacion.ADMIN_GENERAL)
    )

    assert respuesta.status_code == 400
    cuerpo = respuesta.json()
    assert _forma_correcta(cuerpo)
    assert cuerpo["codigo"] == errores.SIN_CAMBIOS


def test_un_422_de_validacion_tiene_la_misma_forma(cliente, como):
    """Es el test que pide el Roadmap: la misma forma para un error de negocio
    y para uno de validacion. Antes el 422 traia una lista de objetos en
    `detail` y el frontend tenia que armar el texto por su cuenta."""
    respuesta = cliente.post(
        "/api/edificios",
        json={"nombre": "A"},
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 422
    cuerpo = respuesta.json()
    assert _forma_correcta(cuerpo)
    assert cuerpo["codigo"] == errores.DATOS_INVALIDOS
    # Y ademas trae el problema por campo, que es lo que un formulario necesita
    # para marcar el campo que esta mal.
    assert cuerpo["campos"]


def test_un_rechazo_de_permiso_tiene_la_misma_forma(cliente, como):
    respuesta = cliente.get("/api/usuarios", headers=como(autorizacion.ENCARGADO))

    assert respuesta.status_code == 403
    cuerpo = respuesta.json()
    assert _forma_correcta(cuerpo)
    assert cuerpo["codigo"] == errores.SIN_PERMISO


def test_una_ruta_que_no_existe_tiene_la_misma_forma(cliente):
    """Lo levanta el ruteo de Starlette, no el proyecto. Igual sale con la
    forma del catalogo y en castellano: antes devolvia `{"detail":"Not
    Found"}`, que es lo primero que ve cualquiera que escriba una URL a mano.
    """
    respuesta = cliente.get("/api/esta-ruta-no-existe")

    assert respuesta.status_code == 404
    cuerpo = respuesta.json()
    assert _forma_correcta(cuerpo)
    assert cuerpo["codigo"] == errores.NO_ENCONTRADO
    assert cuerpo["mensaje"] != "Not Found"


def test_un_metodo_que_no_corresponde_tiene_la_misma_forma(cliente):
    respuesta = cliente.delete("/api/auth/login")

    assert respuesta.status_code == 405
    cuerpo = respuesta.json()
    assert _forma_correcta(cuerpo)
    assert cuerpo["codigo"] == errores.METODO_NO_PERMITIDO


def test_el_401_sigue_llevando_el_header_de_autenticacion(cliente):
    """La forma uniforme no se come las cabeceras. Sin `WWW-Authenticate` la
    respuesta no cumple el estandar de HTTP para un 401 y el boton "Authorize"
    de /docs no se da cuenta de que tiene que volver a pedir credenciales."""
    respuesta = cliente.get("/api/auth/me")

    assert respuesta.status_code == 401
    assert respuesta.headers.get("www-authenticate") == "Bearer"
    assert respuesta.json()["codigo"] == errores.SESION_INVALIDA


# ===========================================================================
# 2. EL CATALOGO ES CONSISTENTE
# ===========================================================================


def test_no_hay_codigos_duplicados():
    """Lo garantiza `_definir`, que revienta al importar si se repite uno. Este
    test verifica que esa guarda siga existiendo: dos errores distintos con el
    mismo codigo son indistinguibles para el cliente."""
    with pytest.raises(ValueError):
        errores._definir(errores.SIN_CAMBIOS, 400, "otro texto cualquiera")


def test_todas_las_entradas_tienen_codigo_http_y_texto():
    for codigo, definicion in errores.CATALOGO.items():
        assert definicion.codigo == codigo
        assert 400 <= definicion.http <= 599, codigo
        assert definicion.plantilla.strip(), codigo


def test_el_codigo_es_el_mismo_que_la_constante():
    """Las constantes del modulo y las claves del catalogo no pueden
    divergir: el endpoint usa la constante y el frontend lee la clave."""
    constantes = {
        valor
        for nombre, valor in vars(errores).items()
        if nombre.isupper() and isinstance(valor, str) and valor in errores.CATALOGO
    }

    assert constantes == set(errores.CATALOGO)


def test_un_codigo_que_no_esta_en_el_catalogo_no_se_puede_levantar():
    with pytest.raises(ValueError):
        errores.ErrorDeNegocio("ESTE_CODIGO_NO_EXISTE")


def test_un_parametro_que_falta_no_rompe_la_respuesta():
    """Un error mostrado a medias es molesto; una excepcion mientras se esta
    reportando un error deja al usuario frente a un 500 sin explicacion."""
    error = errores.ErrorDeNegocio(errores.PISO_CON_UNIDADES)

    assert error.mensaje
    assert error.http == 400


# ===========================================================================
# 3. NADA EN INGLES
# ===========================================================================

# Palabras que solo aparecen si un mensaje quedo en el idioma de la libreria.
_DELATORAS_DE_INGLES = (
    "should",
    "input",
    "field",
    "value is not",
    "not permitted",
    "invalid",
    "required",
    "error",
    "string",
)


def _parece_ingles(texto: str) -> list[str]:
    bajo = texto.lower()
    return [p for p in _DELATORAS_DE_INGLES if p in bajo]


def test_ningun_mensaje_del_catalogo_esta_en_ingles():
    for codigo, definicion in errores.CATALOGO.items():
        assert not _parece_ingles(definicion.plantilla), (codigo, definicion.plantilla)


def test_ninguna_plantilla_de_validacion_esta_en_ingles():
    for tipo, plantilla in errores._PLANTILLAS_DE_VALIDACION.items():
        assert not _parece_ingles(plantilla), (tipo, plantilla)


def test_el_tope_de_pisos_se_explica_en_castellano(cliente, como):
    """El caso concreto que se veia en la pantalla: antes decia
    "cantidad_pisos: Input should be less than or equal to 40"."""
    respuesta = cliente.post(
        "/api/edificios",
        json={
            "nombre": "Consorcio de prueba",
            "direccion": "Calle 1",
            "cp": "C1000",
            "cantidad_pisos": finanzas.MAX_PISOS + 30,
            "unidades_por_piso": 4,
        },
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    cuerpo = respuesta.json()
    assert respuesta.status_code == 422
    assert not _parece_ingles(cuerpo["mensaje"]), cuerpo["mensaje"]
    # El numero sale de la constante y no escrito a mano: el tope ya se bajo
    # tres veces y un test que lo repita se rompe en cada cambio por un motivo
    # que no tiene nada que ver con lo que esta probando.
    assert str(finanzas.MAX_PISOS) in cuerpo["mensaje"]
    # Y el campo se nombra como lo lee una persona, no como se llama la columna.
    assert "cantidad de pisos" in cuerpo["mensaje"]
    assert "cantidad_pisos" not in cuerpo["mensaje"]


def test_un_campo_que_falta_se_pide_por_su_nombre_legible(cliente, como):
    respuesta = cliente.post(
        "/api/edificios", json={}, headers=como(autorizacion.ADMIN_GENERAL)
    )

    campos = respuesta.json()["campos"]
    assert campos["nombre"] == "Completá el nombre."
    assert campos["direccion"] == "Completá la dirección."
    assert campos["cp"] == "Completá el código postal."


def test_un_campo_de_mas_lo_dice_sin_hablar_de_esquemas(cliente, como):
    respuesta = cliente.post(
        "/api/edificios",
        json={
            "nombre": "Consorcio de prueba",
            "direccion": "Calle 1",
            "cp": "C1000",
            "cantidad_pisos": 1,
            "unidades_por_piso": 1,
            "inventado": 9,
        },
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 422
    assert not _parece_ingles(respuesta.json()["mensaje"])


def test_el_mensaje_de_un_validador_propio_se_respeta(cliente, db, como):
    """Los validadores del proyecto ya escriben en castellano, y su texto sabe
    cosas que el tipo de error no: "El coeficiente admite hasta 3 decimales".
    El traductor no lo tiene que pisar con una frase generica."""
    respuesta = cliente.post(
        "/api/usuarios",
        json={
            "nombre": "Prueba Politica",
            "email": "politica-errores@prueba.com.ar",
            "password": "corta",
            "rol": autorizacion.PROPIETARIO,
        },
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 422
    mensaje = respuesta.json()["campos"]["password"]
    assert "caracteres" in mensaje
    assert "mayúscula" in mensaje


def test_un_email_mal_escrito_se_explica_en_castellano(cliente, como):
    """El validador de email es de una libreria y su texto es en ingles
    ("An email address must have an @-sign"), asi que este caso se reconoce y
    se contesta con texto propio."""
    respuesta = cliente.post(
        "/api/usuarios",
        json={
            "nombre": "Prueba Email",
            "email": "esto-no-es-un-email",
            "password": "Prueba123!",
            "rol": autorizacion.PROPIETARIO,
        },
        headers=como(autorizacion.ADMIN_GENERAL),
    )

    assert respuesta.status_code == 422
    assert not _parece_ingles(respuesta.json()["campos"]["email"])


# ===========================================================================
# 4. NINGUN MENSAJE FILTRA LA ESTRUCTURA INTERNA (FX-T11)
# ===========================================================================

# Los nombres de las tablas, los sufijos de columna y las palabras que delatan
# que el texto salio de la base o del codigo y no de una persona.
_PALABRAS_PROHIBIDAS = (
    "tabla",
    "columna",
    "select",
    "insert",
    "update ",
    "constraint",
    "foreign key",
    "sqlalchemy",
    ".py",
    "traceback",
    "usuarios",
    "departamentos",
    "edificios",
    "coeficientes_",
    "_id",
)


def test_ningun_mensaje_nombra_tablas_columnas_ni_archivos():
    """La regla `FX-T11`, verificada en vez de leida.

    Antes de este catalogo, auditarla era recorrer cuarenta endpoints. Ahora es
    recorrer un diccionario, y este test lo hace en cada corrida.
    """
    for codigo, definicion in errores.CATALOGO.items():
        bajo = definicion.plantilla.lower()
        encontradas = [p for p in _PALABRAS_PROHIBIDAS if p in bajo]
        assert not encontradas, (codigo, encontradas, definicion.plantilla)


def test_ningun_mensaje_muestra_un_id_interno():
    """Los ids son internos: "No existe un usuario con id 37" no le dice nada a
    quien esta del otro lado de la pantalla. Se saco al migrar el 404 de
    usuarios al catalogo."""
    for codigo, definicion in errores.CATALOGO.items():
        assert not re.search(r"\bid\b", definicion.plantilla.lower()), codigo


def test_el_404_de_un_usuario_no_nombra_el_id(cliente, como):
    respuesta = cliente.get("/api/usuarios/9999", headers=como(autorizacion.ADMIN_GENERAL))

    assert respuesta.status_code == 404
    assert "9999" not in respuesta.json()["mensaje"]
    assert respuesta.json()["codigo"] == errores.USUARIO_NO_ENCONTRADO


def test_los_nombres_legibles_de_campo_no_son_los_de_la_columna():
    """Si el diccionario devolviera el nombre crudo, el mensaje diria
    "Completá cantidad_pisos" y estaria nombrando una columna."""
    for columna, legible in errores.CAMPOS_LEGIBLES.items():
        assert legible != columna
        assert "_" not in legible, columna

"""La guarda que impide arrancar en produccion con configuracion de desarrollo.

Es la unica linea de defensa entre un despliegue apurado y un backend firmando
tokens con un secreto publico. Un backend caido se ve enseguida; uno inseguro
puede pasar meses sin que nadie lo advierta, asi que conviene tenerla probada.
"""

import importlib
import logging

import pytest

from app.core import config as config_modulo

VARIABLES = ("VERCEL", "JWT_SECRETO", "DATABASE_URL", "CORS_ORIGENES_EXTRA")


@pytest.fixture
def configuracion(monkeypatch):
    """Recarga `config` con el entorno que pida cada test.

    El modulo lee el entorno una sola vez, al importarse, asi que para probar
    otro escenario hay que volver a importarlo. Al terminar se restaura el
    estado original: sin eso, el modulo quedaria contaminado para el resto de
    la suite y el origen del problema seria imposible de adivinar.
    """

    def recargar(**entorno):
        for nombre in VARIABLES:
            monkeypatch.delenv(nombre, raising=False)
        for nombre, valor in entorno.items():
            monkeypatch.setenv(nombre, valor)
        return importlib.reload(config_modulo)

    yield recargar

    monkeypatch.undo()
    importlib.reload(config_modulo)


PRODUCCION_SANA = {
    "VERCEL": "1",
    "JWT_SECRETO": "un-secreto-real-largo-y-aleatorio",
    "DATABASE_URL": "postgresql://u:p@pooler.supabase.com:6543/postgres",
    "CORS_ORIGENES_EXTRA": "https://smart-building.vercel.app",
}


# --------------------------------------------------------------- desarrollo --


def test_en_desarrollo_arranca_sin_ninguna_variable(configuracion):
    """El proyecto se clona, se instala y levanta. Sin configurar nada."""
    config = configuracion()

    assert config.ES_PRODUCCION is False
    assert config.USA_SQLITE is True
    assert config.JWT_SECRETO == config.JWT_SECRETO_DESARROLLO
    config.verificar_configuracion_produccion()  # no debe levantar nada


def test_la_ruta_de_sqlite_es_absoluta(configuracion):
    """Si dependiera del directorio actual, levantar el backend desde la raiz
    del proyecto crearia una segunda base vacia y el login fallaria con
    usuarios que existen en la otra."""
    config = configuracion()

    assert config.DATABASE_URL.startswith("sqlite:///")
    assert config.DATABASE_URL.endswith("smart_building.db")
    assert "backend" in config.DATABASE_URL


# --------------------------------------------------------------- produccion --


def test_produccion_con_el_secreto_de_desarrollo_no_arranca(configuracion):
    config = configuracion(**{**PRODUCCION_SANA, "JWT_SECRETO": config_modulo.JWT_SECRETO_DESARROLLO})

    with pytest.raises(config.ConfiguracionInsegura, match="JWT_SECRETO"):
        config.verificar_configuracion_produccion()


def test_produccion_sobre_sqlite_no_arranca(configuracion):
    """El entorno serverless no tiene disco persistente: todo lo que se
    escriba se pierde al terminar la invocacion. Es el fallo mas caro del
    proyecto porque no da error, simplemente se pierden los datos."""
    entorno = {k: v for k, v in PRODUCCION_SANA.items() if k != "DATABASE_URL"}
    config = configuracion(**entorno)

    with pytest.raises(config.ConfiguracionInsegura, match="SQLite"):
        config.verificar_configuracion_produccion()


def test_produccion_sin_origenes_cors_arranca_pero_avisa(configuracion, caplog):
    """Frontend y backend comparten dominio en Vercel, asi que no hay CORS que
    declarar. Exigirlo bloquearia el primer despliegue: el dominio lo asigna
    Vercel recien DESPUES de desplegar. Se avisa en el log y se sigue."""
    entorno = {k: v for k, v in PRODUCCION_SANA.items() if k != "CORS_ORIGENES_EXTRA"}
    config = configuracion(**entorno)

    with caplog.at_level(logging.WARNING):
        config.verificar_configuracion_produccion()   # no debe levantar nada

    assert "CORS_ORIGENES_EXTRA" in caplog.text


def test_informa_todos_los_problemas_juntos(configuracion):
    """Que no haya que desplegar dos veces para enterarse de los dos."""
    config = configuracion(VERCEL="1")

    with pytest.raises(config.ConfiguracionInsegura) as error:
        config.verificar_configuracion_produccion()

    mensaje = str(error.value)
    assert "JWT_SECRETO" in mensaje
    assert "SQLite" in mensaje


def test_solo_el_secreto_y_la_base_bloquean_el_arranque(configuracion):
    """Los dos que si bloquean son los que dejan el sistema inseguro o
    pierden datos en silencio. Lo demas se avisa, no se bloquea."""
    config = configuracion(VERCEL="1")

    with pytest.raises(config.ConfiguracionInsegura) as error:
        config.verificar_configuracion_produccion()

    assert str(error.value).count("  - ") == 2


def test_produccion_bien_configurada_arranca(configuracion):
    config = configuracion(**PRODUCCION_SANA)

    assert config.ES_PRODUCCION is True
    assert config.USA_SQLITE is False
    config.verificar_configuracion_produccion()


# ---------------------------------------------- longitud del secreto ---------


def test_produccion_con_un_secreto_corto_no_arranca(configuracion):
    """Un secreto propio pero corto pasaba la guarda, porque solo se comparaba
    contra el de desarrollo. PyJWT avisa por log cuando la clave HMAC es menor
    a 32 bytes, pero firma igual — y un warning en los logs de una funcion
    serverless es un aviso que nadie lee."""
    config = configuracion(**{**PRODUCCION_SANA, "JWT_SECRETO": "corto"})

    with pytest.raises(config.ConfiguracionInsegura, match="32"):
        config.verificar_configuracion_produccion()


def test_el_secreto_se_mide_en_bytes_y_no_en_caracteres(configuracion):
    """Misma trampa que en las contrasenias: 20 caracteres acentuados son 40
    bytes, pero 20 caracteres ASCII son 20. Medir caracteres aceptaria una
    clave de 20 bytes."""
    config = configuracion(**{**PRODUCCION_SANA, "JWT_SECRETO": "a" * 31})

    with pytest.raises(config.ConfiguracionInsegura, match="31 bytes"):
        config.verificar_configuracion_produccion()

    config = configuracion(**{**PRODUCCION_SANA, "JWT_SECRETO": "á" * 16})
    config.verificar_configuracion_produccion()  # 32 bytes en 16 caracteres


def test_un_secreto_de_exactamente_32_bytes_arranca(configuracion):
    """El limite exacto, para que el control sea `<` y no `<=`."""
    config = configuracion(**{**PRODUCCION_SANA, "JWT_SECRETO": "a" * 32})

    config.verificar_configuracion_produccion()


def test_el_secreto_de_desarrollo_se_reporta_como_tal_y_no_por_su_largo(configuracion):
    """El secreto de desarrollo tiene 41 bytes, asi que pasaria el control de
    longitud. Pero aunque fuera corto, el mensaje tiene que ser el de "es el
    secreto publico del repositorio": es un problema distinto y mas grave, y
    dos mensajes a la vez dispersan a quien tiene que arreglarlo."""
    config = configuracion(
        **{**PRODUCCION_SANA, "JWT_SECRETO": config_modulo.JWT_SECRETO_DESARROLLO}
    )

    with pytest.raises(config.ConfiguracionInsegura) as excepcion:
        config.verificar_configuracion_produccion()

    assert "valor de desarrollo" in str(excepcion.value)
    assert "minimo es 32" not in str(excepcion.value)


# ------------------------------------------------- cadena de conexion --------


def test_produccion_con_la_conexion_directa_de_supabase_no_arranca(configuracion):
    """El host directo de Supabase resuelve a IPv6 y una funcion serverless no
    puede abrir conexiones IPv6 salientes. Falla igual, pero con un traceback
    de ochenta lineas que no dice cual es el problema: mejor detectarlo al
    arrancar y explicar que cadena hay que usar."""
    config = configuracion(
        **{
            **PRODUCCION_SANA,
            "DATABASE_URL": "postgresql://postgres:clave@db.abcdefgh.supabase.co:5432/postgres",
        }
    )

    with pytest.raises(config.ConfiguracionInsegura, match="Transaction pooler"):
        config.verificar_configuracion_produccion()


def test_produccion_con_el_pooler_arranca(configuracion):
    config = configuracion(
        **{
            **PRODUCCION_SANA,
            "DATABASE_URL": (
                "postgresql://postgres.abcdefgh:clave"
                "@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
            ),
        }
    )

    config.verificar_configuracion_produccion()


def test_una_base_que_no_es_de_supabase_no_dispara_la_verificacion(configuracion):
    """La comprobacion es especifica de Supabase: cualquier otro PostgreSQL
    tiene que poder usarse sin que esta regla se meta en el medio."""
    config = configuracion(
        **{**PRODUCCION_SANA, "DATABASE_URL": "postgresql://u:p@mi-servidor.example.com:5432/db"}
    )

    config.verificar_configuracion_produccion()


# --------------------------------------------------------------------- CORS --


def test_los_origenes_extra_se_leen_separados_por_coma(configuracion):
    """Se parten a mano a proposito: una lista tipada esperaria JSON en la
    variable de entorno, y quien la carga en el panel de Vercel escribe una
    lista separada por comas."""
    config = configuracion(
        **{**PRODUCCION_SANA, "CORS_ORIGENES_EXTRA": "https://uno.ar, https://dos.ar ,, "}
    )

    assert config.CORS_ORIGENES == ["https://uno.ar", "https://dos.ar"]


def test_en_produccion_no_se_permiten_los_origenes_locales(configuracion):
    """Dejar localhost habilitado contra la API de produccion es una puerta
    que no hace falta tener abierta."""
    config = configuracion(**PRODUCCION_SANA)

    assert not any("localhost" in origen for origen in config.CORS_ORIGENES)


def test_en_desarrollo_se_permiten_los_puertos_locales(configuracion):
    config = configuracion()

    assert "http://localhost:8090" in config.CORS_ORIGENES

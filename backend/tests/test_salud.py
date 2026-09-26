"""El endpoint de salud y el comportamiento base de la API."""


def test_salud_responde_ok(cliente):
    respuesta = cliente.get("/api/salud")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "ok"
    assert cuerpo["aplicacion"] == "SMART Building"
    assert cuerpo["version"]


def test_en_desarrollo_informa_entorno_y_motor(cliente):
    cuerpo = cliente.get("/api/salud").json()

    assert cuerpo["entorno"] == "desarrollo"
    assert cuerpo["base_de_datos"] in {"sqlite", "postgresql"}


def test_una_ruta_inexistente_devuelve_404(cliente):
    assert cliente.get("/api/no-existe").status_code == 404


def test_cors_permite_el_frontend_local(cliente):
    respuesta = cliente.get("/api/salud", headers={"Origin": "http://localhost:8090"})

    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:8090"


def test_cors_no_permite_un_origen_ajeno(cliente):
    """La whitelist es explicita: un origen que no este declarado no pasa."""
    respuesta = cliente.get("/api/salud", headers={"Origin": "http://sitio-ajeno.com"})

    assert "access-control-allow-origin" not in respuesta.headers


def test_la_documentacion_interactiva_esta_disponible_en_desarrollo(cliente):
    """Es la herramienta con la que se aprueba cada tarea de backend."""
    assert cliente.get("/docs").status_code == 200
    assert cliente.get("/openapi.json").status_code == 200

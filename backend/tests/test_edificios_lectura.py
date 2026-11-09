"""Pruebas de `GET /api/edificios` y `GET /api/edificios/{id}` — F1-T21.

Lo que esta tarea promete no es que los endpoints devuelvan el dato correcto
—eso lo tiene que cumplir cualquier endpoint— sino que lo devuelvan en una
cantidad **fija** de consultas. Asi que aca hay tres clases de prueba:

  1. La forma de la respuesta: el listado NO trae la estructura y el detalle si.
  2. El control de acceso, permitido y prohibido, incluido el alcance: un
     Administrador de Consorcio no ve los edificios que no administra.
  3. **La cantidad de consultas SQL disparadas.** Se cuentan, no se miden en
     tiempo: un tiempo depende de la maquina y de la carga del momento, asi que
     un N+1 que vuelva a aparecer pasaria un test de tiempo en silencio y solo
     se notaria en produccion, donde cada consulta paga ida y vuelta de red.
"""

from contextlib import contextmanager

import pytest
from sqlalchemy import event, select

from app.models.edificio import Cochera, Departamento, Edificio, EspacioComun
from app.models.usuario import Usuario
from app.services import autorizacion

RUTA = "/api/edificios"

ALTA = {
    "nombre": "Consorcio Rivadavia 1234",
    "direccion": "Av. Rivadavia 1234",
    "cp": "C1033",
    "cantidad_pisos": 7,
    "unidades_por_piso": 4,
}

# Los roles que NO tienen que poder leer la cartera de edificios: todos los
# asignables menos los dos administradores.
OTROS_ROLES = [
    rol
    for rol in autorizacion.ROLES_ASIGNABLES
    if rol not in (autorizacion.ADMIN_GENERAL, autorizacion.ADMIN_CONSORCIO)
]

# Las tablas cuyas consultas cuenta el contador. Deja afuera la de `usuarios`,
# que es la que dispara la dependencia de sesion en cada request y no tiene
# nada que ver con lo que esta tarea mide.
TABLAS_DE_LA_ESTRUCTURA = ("edificios", "pisos", "departamentos", "cocheras", "espacios_comunes")


def _alta(**cambios) -> dict:
    datos = dict(ALTA)
    datos.update(cambios)
    return datos


def _crear_por_api(cliente, headers, **cambios) -> dict:
    respuesta = cliente.post(RUTA, json=_alta(**cambios), headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _edificio_de(db, nombre: str, **columnas) -> Edificio:
    """Un edificio sin estructura, para las pruebas de alcance y de orden."""
    edificio = Edificio(
        nombre=nombre,
        direccion=f"Calle {nombre} 100",
        cp="C1000",
        **columnas,
    )
    db.add(edificio)
    db.commit()
    return edificio


def _usuario(db, rol: str, nombre: str = "Persona") -> Usuario:
    usuario = Usuario(
        nombre=nombre,
        email=f"{nombre.lower()}-{rol}@prueba.com.ar",
        password_hash="x",
        rol=rol,
    )
    db.add(usuario)
    db.commit()
    return usuario


@contextmanager
def contar_consultas(engine, db):
    """Registra las consultas que toquen las tablas de la estructura.

    `db.expire_all()` antes de contar es imprescindible y no es un detalle del
    andamio: los tests comparten la misma sesion que el endpoint, asi que un
    edificio creado por el test ya esta en la sesion con sus relaciones
    cargadas. Sin expirar, `selectinload` no tendria nada que cargar y el
    contador daria menos consultas de las que la aplicacion real dispara —o
    sea, un test que confirma un rendimiento que no existe.
    """
    db.expire_all()
    consultas: list[str] = []

    def registrar(conexion, cursor, sentencia, parametros, contexto, muchos):
        texto = sentencia.lower()
        if any(tabla in texto for tabla in TABLAS_DE_LA_ESTRUCTURA):
            consultas.append(sentencia)

    event.listen(engine, "before_cursor_execute", registrar)
    try:
        yield consultas
    finally:
        event.remove(engine, "before_cursor_execute", registrar)


# ==========================================================================
# EL LISTADO: FORMA DE LA RESPUESTA
# ==========================================================================


def test_el_listado_devuelve_el_edificio_con_sus_dos_conteos(cliente, como):
    headers = como(autorizacion.ADMIN_GENERAL)
    _crear_por_api(cliente, headers)

    respuesta = cliente.get(RUTA, headers=headers)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo) == 1
    assert cuerpo[0]["nombre"] == "Consorcio Rivadavia 1234"
    assert cuerpo[0]["cantidad_pisos"] == 7
    assert cuerpo[0]["cantidad_departamentos"] == 28


def test_el_listado_no_trae_la_estructura(cliente, como):
    """Es la decision central del listado, no una omision.

    Si el resumen incluyera las colecciones, cada renglon de la pantalla
    arrastraria los pisos y los departamentos del edificio entero: para una
    cartera de treinta edificios son miles de filas que nadie va a mirar.
    """
    headers = como(autorizacion.ADMIN_GENERAL)
    _crear_por_api(cliente, headers)

    fila = cliente.get(RUTA, headers=headers).json()[0]

    assert "pisos" not in fila
    assert "cocheras" not in fila
    assert "espacios_comunes" not in fila


def test_el_listado_vacio_es_una_lista_vacia_y_no_un_error(cliente, como):
    respuesta = cliente.get(RUTA, headers=como(autorizacion.ADMIN_GENERAL))

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_el_listado_viene_ordenado_por_nombre(cliente, como, db):
    headers = como(autorizacion.ADMIN_GENERAL)
    for nombre in ("Zarate", "Alvear", "Mitre"):
        _edificio_de(db, nombre)

    nombres = [fila["nombre"] for fila in cliente.get(RUTA, headers=headers).json()]

    assert nombres == ["Alvear", "Mitre", "Zarate"]


def test_el_listado_incluye_los_edificios_inactivos(cliente, como, db):
    """Igual que el listado de usuarios: la baja es logica para que el
    edificio siga estando, y esconderlo dejaria al administrador sin forma de
    reactivarlo desde la pantalla."""
    headers = como(autorizacion.ADMIN_GENERAL)
    _edificio_de(db, "Dado de baja", activo=False)

    filas = cliente.get(RUTA, headers=headers).json()

    assert len(filas) == 1
    assert filas[0]["activo"] is False


def test_los_conteos_son_de_cada_edificio_y_no_del_total(cliente, como):
    """La trampa de las subconsultas correlacionadas.

    Sin `correlate(Edificio)`, SQLAlchemy vuelve a nombrar `edificios` en el
    FROM de la subconsulta y el conteo sale sobre TODOS los edificios: el
    mismo numero repetido en cada renglon. Es un error que pasa los tests de
    permisos y de forma sin chistar, asi que hace falta un test que mire dos
    edificios de tamanios distintos.
    """
    headers = como(autorizacion.ADMIN_GENERAL)
    _crear_por_api(cliente, headers, nombre="Chico", cantidad_pisos=2, unidades_por_piso=2)
    _crear_por_api(cliente, headers, nombre="Grande", cantidad_pisos=5, unidades_por_piso=3)

    por_nombre = {f["nombre"]: f for f in cliente.get(RUTA, headers=headers).json()}

    assert (por_nombre["Chico"]["cantidad_pisos"], por_nombre["Chico"]["cantidad_departamentos"]) == (2, 4)
    assert (por_nombre["Grande"]["cantidad_pisos"], por_nombre["Grande"]["cantidad_departamentos"]) == (5, 15)


def test_un_edificio_sin_estructura_cuenta_cero_y_aparece_igual(cliente, como, db):
    """El `COUNT` va por subconsulta y no por un JOIN justamente por esto: un
    JOIN interno dejaria afuera del listado al edificio sin pisos."""
    headers = como(autorizacion.ADMIN_GENERAL)
    _edificio_de(db, "Recien cargado")

    filas = cliente.get(RUTA, headers=headers).json()

    assert len(filas) == 1
    assert filas[0]["cantidad_pisos"] == 0
    assert filas[0]["cantidad_departamentos"] == 0


# ==========================================================================
# EL LISTADO: CONTROL DE ACCESO Y ALCANCE
# ==========================================================================


def test_el_administrador_de_consorcio_solo_ve_los_edificios_que_administra(
    cliente, como, db
):
    """El filtro vive en la consulta, no en la pantalla.

    Un filtro que vive en el frontend no es un permiso: la respuesta ya trajo
    los datos de los otros edificios y cualquiera los ve en la pestania de red
    del navegador.
    """
    headers_admin = como(autorizacion.ADMIN_CONSORCIO)
    admin = db.scalars(
        select(Usuario).where(Usuario.rol == autorizacion.ADMIN_CONSORCIO)
    ).first()

    _edificio_de(db, "El mio", admin_consorcio_id=admin.id)
    _edificio_de(db, "De otro")

    filas = cliente.get(RUTA, headers=headers_admin).json()

    assert [f["nombre"] for f in filas] == ["El mio"]


def test_el_administrador_general_ve_toda_la_cartera(cliente, como, db):
    otro = _usuario(db, autorizacion.ADMIN_CONSORCIO, "Otro")
    _edificio_de(db, "De otro", admin_consorcio_id=otro.id)
    _edificio_de(db, "Sin administrador")

    filas = cliente.get(RUTA, headers=como(autorizacion.ADMIN_GENERAL)).json()

    assert len(filas) == 2


def test_un_administrador_de_consorcio_sin_edificios_recibe_una_lista_vacia(
    cliente, como, db
):
    _edificio_de(db, "De nadie")

    respuesta = cliente.get(RUTA, headers=como(autorizacion.ADMIN_CONSORCIO))

    assert respuesta.status_code == 200
    assert respuesta.json() == []


@pytest.mark.parametrize("rol", OTROS_ROLES)
def test_los_demas_roles_no_pueden_listar_edificios(cliente, como, rol):
    respuesta = cliente.get(RUTA, headers=como(rol))

    assert respuesta.status_code == 403


def test_el_listado_sin_autenticacion_es_401(cliente):
    assert cliente.get(RUTA).status_code == 401


def test_el_rechazo_por_rol_es_403_y_no_401(cliente, como):
    """La distincion no es cosmetica: el envoltorio de `fetch` del frontend
    trata el 401 limpiando la sesion y mandando al login, asi que un 401 de
    mas desloguearia a alguien que esta perfectamente logueado."""
    respuesta = cliente.get(RUTA, headers=como(autorizacion.PROPIETARIO))

    assert respuesta.status_code == 403
    assert "sesión" not in respuesta.json()["detail"].lower()


# ==========================================================================
# EL DETALLE
# ==========================================================================


def test_el_detalle_trae_la_estructura_completa(cliente, como):
    headers = como(autorizacion.ADMIN_GENERAL)
    creado = _crear_por_api(cliente, headers, cantidad_pisos=2, unidades_por_piso=3)
    edificio_id = creado["edificio"]["id"]

    respuesta = cliente.get(f"{RUTA}/{edificio_id}", headers=headers)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["edificio"]["id"] == edificio_id
    assert cuerpo["cantidad_pisos"] == 2
    assert cuerpo["cantidad_departamentos"] == 6
    assert [p["numero"] for p in cuerpo["pisos"]] == [1, 2]
    assert [d["identificador"] for d in cuerpo["pisos"][0]["departamentos"]] == [
        "1A",
        "1B",
        "1C",
    ]


def test_los_pisos_del_detalle_vienen_en_orden(cliente, como):
    headers = como(autorizacion.ADMIN_GENERAL)
    creado = _crear_por_api(cliente, headers, cantidad_pisos=12, unidades_por_piso=1)

    cuerpo = cliente.get(f"{RUTA}/{creado['edificio']['id']}", headers=headers).json()

    assert [p["orden"] for p in cuerpo["pisos"]] == list(range(1, 13))


def test_el_detalle_dice_que_las_unidades_estan_desocupadas(cliente, como):
    headers = como(autorizacion.ADMIN_GENERAL)
    creado = _crear_por_api(cliente, headers, cantidad_pisos=1, unidades_por_piso=2)

    cuerpo = cliente.get(f"{RUTA}/{creado['edificio']['id']}", headers=headers).json()

    for depto in cuerpo["pisos"][0]["departamentos"]:
        assert depto["ocupado"] is False
        assert depto["propietario_id"] is None
        assert depto["inquilino_id"] is None
        assert depto["coeficiente"] is None


def test_una_unidad_con_propietario_viaja_como_ocupada(cliente, como, db):
    """`ocupado` no es una columna: lo calcula el modelo. Viaja resuelto para
    que el frontend no reimplemente la regla —y la reimplemente distinto."""
    headers = como(autorizacion.ADMIN_GENERAL)
    creado = _crear_por_api(cliente, headers, cantidad_pisos=1, unidades_por_piso=2)
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Dueño")

    depto = db.scalars(select(Departamento)).first()
    depto.propietario_id = propietario.id
    db.commit()

    cuerpo = cliente.get(f"{RUTA}/{creado['edificio']['id']}", headers=headers).json()
    ocupadas = [
        d for d in cuerpo["pisos"][0]["departamentos"] if d["ocupado"] is True
    ]

    assert len(ocupadas) == 1
    assert ocupadas[0]["propietario_id"] == propietario.id


def test_el_detalle_trae_las_cocheras_y_los_espacios_comunes(cliente, como, db):
    headers = como(autorizacion.ADMIN_GENERAL)
    creado = _crear_por_api(cliente, headers, cantidad_pisos=1, unidades_por_piso=1)
    edificio_id = creado["edificio"]["id"]

    db.add(Cochera(edificio_id=edificio_id, numero="S2-14", tipo="rotativa"))
    db.add(EspacioComun(edificio_id=edificio_id, nombre="SUM", capacidad=40))
    db.commit()

    cuerpo = cliente.get(f"{RUTA}/{edificio_id}", headers=headers).json()

    assert [c["numero"] for c in cuerpo["cocheras"]] == ["S2-14"]
    assert cuerpo["cocheras"][0]["tipo"] == "rotativa"
    assert [e["nombre"] for e in cuerpo["espacios_comunes"]] == ["SUM"]
    assert cuerpo["espacios_comunes"][0]["capacidad"] == 40


def test_un_edificio_sin_cocheras_devuelve_listas_vacias(cliente, como):
    headers = como(autorizacion.ADMIN_GENERAL)
    creado = _crear_por_api(cliente, headers, cantidad_pisos=1, unidades_por_piso=1)

    cuerpo = cliente.get(f"{RUTA}/{creado['edificio']['id']}", headers=headers).json()

    assert cuerpo["cocheras"] == []
    assert cuerpo["espacios_comunes"] == []


def test_un_edificio_que_no_existe_es_404(cliente, como):
    respuesta = cliente.get(f"{RUTA}/9999", headers=como(autorizacion.ADMIN_GENERAL))

    assert respuesta.status_code == 404


def test_un_id_que_no_es_numero_es_422(cliente, como):
    respuesta = cliente.get(f"{RUTA}/abc", headers=como(autorizacion.ADMIN_GENERAL))

    assert respuesta.status_code == 422


def test_un_edificio_fuera_del_alcance_responde_igual_que_uno_inexistente(
    cliente, como, db
):
    """Un 403 distinguible le iria contando a un Administrador de Consorcio
    que edificios hay en la cartera probando ids."""
    headers = como(autorizacion.ADMIN_CONSORCIO)
    ajeno = _edificio_de(db, "De otro")

    fuera_de_alcance = cliente.get(f"{RUTA}/{ajeno.id}", headers=headers)
    inexistente = cliente.get(f"{RUTA}/9999", headers=headers)

    assert fuera_de_alcance.status_code == 404
    assert fuera_de_alcance.json() == inexistente.json()


def test_el_administrador_de_consorcio_ve_el_detalle_de_su_edificio(cliente, como, db):
    headers = como(autorizacion.ADMIN_CONSORCIO)
    admin = db.scalars(
        select(Usuario).where(Usuario.rol == autorizacion.ADMIN_CONSORCIO)
    ).first()
    mio = _edificio_de(db, "El mio", admin_consorcio_id=admin.id)

    respuesta = cliente.get(f"{RUTA}/{mio.id}", headers=headers)

    assert respuesta.status_code == 200
    assert respuesta.json()["edificio"]["nombre"] == "El mio"


@pytest.mark.parametrize("rol", OTROS_ROLES)
def test_los_demas_roles_no_pueden_ver_el_detalle(cliente, como, db, rol):
    edificio = _edificio_de(db, "Cualquiera")

    respuesta = cliente.get(f"{RUTA}/{edificio.id}", headers=como(rol))

    assert respuesta.status_code == 403


def test_el_detalle_sin_autenticacion_es_401(cliente, como, db):
    edificio = _edificio_de(db, "Cualquiera")

    assert cliente.get(f"{RUTA}/{edificio.id}").status_code == 401


def test_el_mensaje_del_404_no_nombra_tablas_ni_consultas(cliente, como):
    respuesta = cliente.get(f"{RUTA}/9999", headers=como(autorizacion.ADMIN_GENERAL))

    detalle = respuesta.json()["detail"].lower()
    for palabra in ("edificios", "select", "pisos", "departamentos", "query"):
        assert palabra not in detalle


# ==========================================================================
# LA CANTIDAD DE CONSULTAS, QUE ES EL "LISTO CUANDO" DE LA TAREA
# ==========================================================================


def test_el_listado_dispara_una_sola_consulta(cliente, como, db, engine_prueba):
    headers = como(autorizacion.ADMIN_GENERAL)
    _crear_por_api(cliente, headers)

    with contar_consultas(engine_prueba, db) as consultas:
        respuesta = cliente.get(RUTA, headers=headers)

    assert respuesta.status_code == 200
    assert len(consultas) == 1, consultas


def test_el_listado_dispara_la_misma_consulta_con_siete_edificios(
    cliente, como, db, engine_prueba
):
    """El numero 7 no es casual: en la iteracion anterior este mismo listado
    disparaba 29 consultas para 7 edificios de prueba."""
    headers = como(autorizacion.ADMIN_GENERAL)
    for indice in range(7):
        _crear_por_api(cliente, headers, nombre=f"Edificio {indice}")

    with contar_consultas(engine_prueba, db) as consultas:
        respuesta = cliente.get(RUTA, headers=headers)

    assert len(respuesta.json()) == 7
    assert len(consultas) == 1, consultas


def test_el_listado_no_crece_en_consultas_con_edificios_mas_grandes(
    cliente, como, db, engine_prueba
):
    headers = como(autorizacion.ADMIN_GENERAL)
    _crear_por_api(cliente, headers, nombre="Grande", cantidad_pisos=20, unidades_por_piso=8)

    with contar_consultas(engine_prueba, db) as consultas:
        cliente.get(RUTA, headers=headers)

    assert len(consultas) == 1, consultas


def test_el_detalle_dispara_cinco_consultas_fijas(cliente, como, db, engine_prueba):
    headers = como(autorizacion.ADMIN_GENERAL)
    creado = _crear_por_api(cliente, headers, cantidad_pisos=3, unidades_por_piso=2)

    with contar_consultas(engine_prueba, db) as consultas:
        respuesta = cliente.get(f"{RUTA}/{creado['edificio']['id']}", headers=headers)

    assert respuesta.status_code == 200
    assert len(consultas) == 5, consultas


def test_el_detalle_dispara_las_mismas_cinco_con_veinte_pisos(
    cliente, como, db, engine_prueba
):
    """La prueba de que no hay N+1: veinte pisos con ocho unidades cada uno son
    161 filas de estructura, y siguen viajando en las mismas cinco consultas."""
    headers = como(autorizacion.ADMIN_GENERAL)
    creado = _crear_por_api(cliente, headers, cantidad_pisos=20, unidades_por_piso=8)

    with contar_consultas(engine_prueba, db) as consultas:
        respuesta = cliente.get(f"{RUTA}/{creado['edificio']['id']}", headers=headers)

    assert respuesta.json()["cantidad_departamentos"] == 160
    assert len(consultas) == 5, consultas


def test_el_detalle_no_crece_en_consultas_con_cocheras_y_espacios(
    cliente, como, db, engine_prueba
):
    headers = como(autorizacion.ADMIN_GENERAL)
    creado = _crear_por_api(cliente, headers, cantidad_pisos=2, unidades_por_piso=2)
    edificio_id = creado["edificio"]["id"]

    for indice in range(10):
        db.add(Cochera(edificio_id=edificio_id, numero=f"S1-{indice}", tipo="rotativa"))
        db.add(EspacioComun(edificio_id=edificio_id, nombre=f"Espacio {indice}"))
    db.commit()

    with contar_consultas(engine_prueba, db) as consultas:
        respuesta = cliente.get(f"{RUTA}/{edificio_id}", headers=headers)

    assert len(respuesta.json()["cocheras"]) == 10
    assert len(consultas) == 5, consultas


def test_el_contador_veria_un_n_mas_uno_si_volviera_a_aparecer(
    cliente, como, db, engine_prueba
):
    """El test del propio contador.

    Un contador roto —que no registre nada, o que filtre mal— haria pasar los
    cinco tests de arriba sin verificar nada. Asi que aca se provoca a mano el
    N+1 que los endpoints evitan: traer los edificios y pedirle los pisos a
    cada uno. Con tres edificios tienen que ser 1 + 3 consultas.
    """
    headers = como(autorizacion.ADMIN_GENERAL)
    for indice in range(3):
        _crear_por_api(cliente, headers, nombre=f"Edificio {indice}", cantidad_pisos=1, unidades_por_piso=1)

    with contar_consultas(engine_prueba, db) as consultas:
        for edificio in db.scalars(select(Edificio)).all():
            len(edificio.pisos)

    assert len(consultas) == 4, consultas

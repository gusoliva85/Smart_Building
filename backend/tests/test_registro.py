"""El registro publico y el rol `pendiente` (F1-T16A).

============================================================================
POR QUE ESTE ARCHIVO ES DISTINTO DE TODOS LOS DEMAS
============================================================================

`POST /api/auth/registro` es el **unico endpoint de escritura sin
autenticacion** del sistema. Todos los demas empiezan por "quien sos"; este
no. Eso significa que la lista de cosas que pueden salir mal no es la de un
endpoint cualquiera, y por eso los tests estan agrupados por la defensa que
prueban y no por el campo que tocan:

  1. **El rol no viene en el pedido.** Si viniera, cualquiera en internet se
     daria de alta como Administrador General. Es la unica falla de este
     archivo que no seria un bug sino una vulnerabilidad.
  2. **Una cuenta pendiente es inerte.** Entra al sistema y no puede nada. Es
     lo que hace que un registro abierto sea aceptable: lo peor que logra un
     abuso es crear filas que no sirven para nada.
  3. **La respuesta no dice si el email existia.** Si lo dijera, el endpoint
     seria una herramienta para averiguar quien vive en el edificio, probando
     direcciones de a una.
  4. **`pendiente` es valido pero no asignable.** Las dos listas de
     `autorizacion` existen para eso, y lo que hay que probar es que cada
     consumidor consulte la que le corresponde.

============================================================================
LO QUE NO SE PRUEBA ACA Y DONDE SE PRUEBA
============================================================================

La politica de contrasenia tiene su archivo (`test_password.py`): aca solo se
verifica que el registro la **aplique**, no se vuelve a enumerar que pide. Y
los invariantes de la matriz —que `pendiente` no alcance nada, que no vea
montos— viven en `test_autorizacion.py`, que es logica pura y corre en
milisegundos.
"""

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models.usuario import Usuario
from app.schemas.usuario import RegistroPublico
from app.services import autorizacion

PASSWORD_VALIDA = "Registro123!"

DATOS_BASE = {
    "nombre": "Ana Registrada",
    "email": "ana.registrada@ejemplo.com.ar",
    "password": PASSWORD_VALIDA,
}


def _registrar(cliente, **cambios):
    """Manda un registro con los datos base y los cambios que se pidan.

    Un campo en `None` se SACA del cuerpo, que no es lo mismo que mandarlo en
    `null`: hace falta para probar el caso "sin telefono" sin mandar un `null`
    explicito, que es otra cosa.
    """
    cuerpo = dict(DATOS_BASE)
    cuerpo.update(cambios)
    cuerpo = {k: v for k, v in cuerpo.items() if v is not None}
    return cliente.post("/api/auth/registro", json=cuerpo)


def _entrar(cliente, email, password=PASSWORD_VALIDA):
    """Login real. Devuelve (codigo, header de autorizacion o None)."""
    respuesta = cliente.post(
        "/api/auth/login", data={"username": email, "password": password}
    )
    if respuesta.status_code != 200:
        return respuesta.status_code, None
    return 200, {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


# ===========================================================================
# EL CAMINO FELIZ
# ===========================================================================


def test_el_registro_no_pide_autenticacion(cliente):
    """Es el punto de todo el endpoint, asi que se fija expresamente.

    Si alguien le agregara una dependencia de sesion sin darse cuenta, el
    resto de los tests de este archivo seguirian pasando —usan el cliente sin
    token igual— pero empezarian a fallar todos juntos con 401, y el motivo
    no quedaria claro. Este test lo nombra.
    """
    assert _registrar(cliente).status_code == 202


def test_el_registro_crea_el_usuario_con_rol_pendiente(cliente, db):
    assert _registrar(cliente).status_code == 202

    usuario = db.scalar(
        select(Usuario).where(Usuario.email == DATOS_BASE["email"])
    )
    assert usuario is not None
    assert usuario.rol == autorizacion.PENDIENTE
    assert usuario.nombre == "Ana Registrada"


def test_el_registrado_queda_activo_para_poder_entrar_y_ver_su_estado(cliente, db):
    """`activo=True` es una decision, no el valor por defecto que quedo.

    Si quedara inactivo, el login le diria "email o contraseña incorrectos",
    que es mentira y lo manda a pedir ayuda por el problema equivocado.
    """
    _registrar(cliente)

    usuario = db.scalar(
        select(Usuario).where(Usuario.email == DATOS_BASE["email"])
    )
    assert usuario.activo is True

    codigo, _ = _entrar(cliente, DATOS_BASE["email"])
    assert codigo == 200


def test_el_telefono_es_opcional(cliente, db):
    _registrar(cliente)

    usuario = db.scalar(
        select(Usuario).where(Usuario.email == DATOS_BASE["email"])
    )
    assert usuario.telefono is None


def test_el_telefono_se_guarda_si_viene(cliente, db):
    _registrar(cliente, telefono="11 2345 6789")

    usuario = db.scalar(
        select(Usuario).where(Usuario.email == DATOS_BASE["email"])
    )
    assert usuario.telefono == "11 2345 6789"


def test_la_contrasenia_se_guarda_hasheada_y_sirve_para_entrar(cliente, db):
    """Dos cosas en un test porque una sin la otra no prueba nada.

    Que el hash no sea la contrasenia es facil de conseguir guardando
    cualquier cosa; que el login funcione prueba que lo que se guardo es el
    hash correcto.
    """
    _registrar(cliente)

    usuario = db.scalar(
        select(Usuario).where(Usuario.email == DATOS_BASE["email"])
    )
    assert usuario.password_hash != PASSWORD_VALIDA
    assert PASSWORD_VALIDA not in usuario.password_hash

    codigo, _ = _entrar(cliente, DATOS_BASE["email"])
    assert codigo == 200


# ===========================================================================
# DEFENSA 1 — EL ROL NO VIENE EN EL PEDIDO
# ===========================================================================


def test_el_esquema_del_registro_no_tiene_el_campo_rol():
    """La barrera, fijada directamente y no a traves de su consecuencia.

    Sale de un ejercicio de mutacion. Romper SOLO el endpoint —hacerle leer un
    `rol` del pedido en vez de usar la constante— no hizo fallar ningun test,
    y la razon no es que falte cobertura: sin el campo en el esquema, no hay
    nada que leer, asi que el comportamiento es identico. Es un mutante
    equivalente, y es literalmente lo que significa tener dos barreras —
    romper una sola no cambia nada.

    Pero deja algo a la vista: la que de verdad sostiene todo es esta, la
    ausencia del campo. El test de abajo la verifica por su consecuencia (un
    422), que es lo correcto porque es lo que se ve desde afuera. Este la
    verifica por si misma, para que el dia que alguien agregue el campo
    —pensando en "dejar que el frontend mande el rol y validarlo en el
    endpoint"— el error que lea nombre el problema en vez de ser un codigo
    HTTP inesperado.
    """
    assert "rol" not in RegistroPublico.model_fields, (
        "El esquema del registro publico NO puede tener el campo `rol`. Es un "
        "endpoint sin autenticacion: con ese campo, cualquiera se da de alta "
        "como Administrador General mandando un dato mas. El rol lo pone el "
        "endpoint como constante."
    )
    assert RegistroPublico.model_config["extra"] == "forbid", (
        "Sin extra='forbid', un `rol` de mas se descarta en silencio, y un "
        "descarte silencioso es indistinguible de un rechazo desde afuera: no "
        "habria forma de probar que la barrera esta puesta."
    )


@pytest.mark.parametrize("rol", autorizacion.ROLES)
def test_mandar_un_rol_en_el_registro_es_un_422(cliente, db, rol):
    """La prueba mas importante del archivo, y por eso va contra los NUEVE.

    No alcanza con probar `admin_general`, que es el rol que buscaria un
    atacante: si el esquema aceptara el campo, lo aceptaria para cualquier
    valor, y un test de un solo rol no distingue "el campo esta prohibido" de
    "ese valor no pasa la validacion". Contra los nueve, la unica forma de que
    pase es que el campo no exista.

    Y tiene que ser un **422** y no un descarte silencioso: el comportamiento
    por defecto de Pydantic es tirar el campo desconocido sin avisar, y un
    descarte silencioso es indistinguible —desde afuera— de un rechazo. Que
    falle ruidosamente es lo que permite probarlo.
    """
    respuesta = _registrar(cliente, rol=rol)

    assert respuesta.status_code == 422
    assert "rol" in respuesta.text

    # Y no dejo nada a medio crear.
    assert db.scalar(select(func.count()).select_from(Usuario)) == 0


def test_mandar_activo_en_el_registro_es_un_422(cliente):
    """El otro campo que, si se colara, cambiaria algo que importa.

    `extra="forbid"` los cubre todos de una vez, pero este se nombra porque es
    el que tiene consecuencia real: un registro que se autoactivara no serviria
    de nada hoy —el rol sigue siendo `pendiente`— pero si manana el acceso
    dependiera de `activo`, el agujero ya estaria abierto.
    """
    assert _registrar(cliente, activo=True).status_code == 422


def test_un_campo_desconocido_cualquiera_es_un_422(cliente):
    assert _registrar(cliente, edificio_id=1).status_code == 422


# ===========================================================================
# DEFENSA 2 — UNA CUENTA PENDIENTE ES INERTE
# ===========================================================================


def test_un_pendiente_entra_al_sistema_y_se_ve_a_si_mismo(cliente):
    """Puede entrar y leer su propio estado. Es todo lo que puede hacer."""
    _registrar(cliente)
    codigo, cabecera = _entrar(cliente, DATOS_BASE["email"])
    assert codigo == 200

    yo = cliente.get("/api/auth/me", headers=cabecera)

    assert yo.status_code == 200
    cuerpo = yo.json()
    assert cuerpo["rol"] == autorizacion.PENDIENTE
    assert cuerpo["rol_etiqueta"] == "Pendiente de aprobación"


def test_la_etiqueta_del_pendiente_le_dice_a_la_persona_en_que_estado_esta(cliente):
    """El frontend arma su mensaje con esto, asi que el texto es contrato.

    "Pendiente de aprobación" tiene que decir que falta que alguien apruebe —
    no "sin rol", que describe la fila de la base y no la situacion de la
    persona.
    """
    _registrar(cliente)
    _, cabecera = _entrar(cliente, DATOS_BASE["email"])

    etiqueta = cliente.get("/api/auth/me", headers=cabecera).json()["rol_etiqueta"]

    assert "robaci" in etiqueta  # aprobación, sin depender del acento


def test_un_pendiente_no_alcanza_ningun_endpoint_de_la_pantalla(cliente, db, como):
    """Los cinco endpoints, uno por uno, y no solo el listado.

    Es la misma leccion que dejo `F1-T16`: hay mas de una via para lo mismo, y
    cubrir solo la que usa la pantalla deja abierta la que usaria cualquiera
    con `curl` en la mano. Un 403 en el listado y un hueco en el PATCH es
    exactamente el agujero que un test del listado solo no encuentra.
    """
    # Un usuario ajeno al que intentar tocar, creado por un admin de verdad.
    admin = como(autorizacion.ADMIN_GENERAL)
    alta = cliente.post(
        "/api/usuarios",
        headers=admin,
        json={
            "nombre": "Ajeno",
            "email": "ajeno@ejemplo.com.ar",
            "password": PASSWORD_VALIDA,
            "rol": autorizacion.PROPIETARIO,
        },
    )
    assert alta.status_code == 201
    ajeno_id = alta.json()["id"]

    _registrar(cliente)
    codigo, cabecera = _entrar(cliente, DATOS_BASE["email"])
    assert codigo == 200

    assert cliente.get("/api/usuarios", headers=cabecera).status_code == 403
    assert (
        cliente.get("/api/usuarios/opciones", headers=cabecera).status_code == 403
    )
    assert (
        cliente.post(
            "/api/usuarios",
            headers=cabecera,
            json={
                "nombre": "Intruso",
                "email": "intruso@ejemplo.com.ar",
                "password": PASSWORD_VALIDA,
                "rol": autorizacion.ADMIN_GENERAL,
            },
        ).status_code
        == 403
    ), "un pendiente no puede crear un administrador"
    assert (
        cliente.patch(
            f"/api/usuarios/{ajeno_id}",
            headers=cabecera,
            json={"nombre": "Cambiado"},
        ).status_code
        == 403
    )
    assert (
        cliente.post(
            f"/api/usuarios/{ajeno_id}/estado",
            headers=cabecera,
            json={"activo": False},
        ).status_code
        == 403
    )


def test_un_pendiente_no_puede_ascenderse_a_si_mismo(cliente, db):
    """El intento directo, por si el PATCH tuviera una excepcion para "uno
    mismo" que en algun momento pareciera razonable agregar."""
    _registrar(cliente)
    _, cabecera = _entrar(cliente, DATOS_BASE["email"])
    yo_id = cliente.get("/api/auth/me", headers=cabecera).json()["id"]

    respuesta = cliente.patch(
        f"/api/usuarios/{yo_id}",
        headers=cabecera,
        json={"rol": autorizacion.ADMIN_GENERAL},
    )

    assert respuesta.status_code == 403
    usuario = db.get(Usuario, yo_id)
    assert usuario.rol == autorizacion.PENDIENTE


def test_el_administrador_ve_al_pendiente_en_el_listado(cliente, como):
    """Tiene que poder encontrarlo: si no apareciera, no habria forma de
    aprobarlo desde la aplicacion y el registro no serviria para nada."""
    _registrar(cliente)
    admin = como(autorizacion.ADMIN_GENERAL)

    listado = cliente.get("/api/usuarios", headers=admin)

    assert listado.status_code == 200
    pendientes = [
        u for u in listado.json() if u["rol"] == autorizacion.PENDIENTE
    ]
    assert len(pendientes) == 1
    assert pendientes[0]["email"] == DATOS_BASE["email"]


def test_el_administrador_puede_aprobar_al_pendiente_y_entonces_el_rol_cambia(
    cliente, db, como
):
    """El recorrido completo que justifica la tarea, de punta a punta.

    Es lo que hay que poder hacer sin tocar la base de datos en ningun paso, y
    era exactamente el problema del que salio esta tarea.
    """
    _registrar(cliente)
    admin = como(autorizacion.ADMIN_GENERAL)
    pendiente_id = [
        u
        for u in cliente.get("/api/usuarios", headers=admin).json()
        if u["rol"] == autorizacion.PENDIENTE
    ][0]["id"]

    aprobacion = cliente.patch(
        f"/api/usuarios/{pendiente_id}",
        headers=admin,
        json={"rol": autorizacion.PROPIETARIO},
    )

    assert aprobacion.status_code == 200
    assert aprobacion.json()["rol"] == autorizacion.PROPIETARIO

    # Y la persona sigue entrando con la contrasenia que eligio ELLA. Aprobar
    # no puede tocarle la credencial: si la tocara, habria que avisarle la
    # nueva por algun canal que el sistema no tiene.
    codigo, _ = _entrar(cliente, DATOS_BASE["email"])
    assert codigo == 200
    assert db.get(Usuario, pendiente_id).rol == autorizacion.PROPIETARIO


# ===========================================================================
# DEFENSA 3 — LA RESPUESTA NO DICE SI EL EMAIL EXISTIA
# ===========================================================================


def test_un_email_repetido_responde_exactamente_lo_mismo_que_uno_nuevo(cliente):
    """Byte por byte: mismo codigo y mismo cuerpo.

    Comparar los dos cuerpos enteros, y no solo el codigo, es lo que ataja el
    error realista: alguien agrega un campo util a la respuesta —el id, un
    "creado": true— y sin querer reabre el oraculo con un 202 en los dos
    casos.
    """
    primero = _registrar(cliente)
    segundo = _registrar(cliente)

    assert primero.status_code == segundo.status_code == 202
    assert primero.json() == segundo.json()


def test_una_falla_de_integridad_que_no_sea_el_email_no_se_traga(
    cliente, db, monkeypatch
):
    """El test que nacio de un bug real, encontrado fuera de pytest.

    ========================================================================
    QUE PASO
    ========================================================================

    La primera version del endpoint atrapaba `IntegrityError` a secas para
    responder igual ante un email repetido. Probandolo contra el backend de
    desarrollo —no con pytest— el registro devolvio **202 sin crear nada**: la
    tabla de esa base se habia creado antes de que existiera `pendiente`, asi
    que su CHECK de `rol` listaba ocho valores y rechazaba el INSERT. El
    `except` se tragaba ese error igual que el del email duplicado.

    O sea que la defensa contra la enumeracion de emails estaba convirtiendo
    **cualquier** falla de integridad en un exito silencioso. Es el peor tipo
    de bug que se puede escribir: no hay log, no hay error, y la persona cree
    que se registro.

    ========================================================================
    POR QUE PYTEST NO LO ENCONTRABA, Y POR QUE ESTE TEST SI
    ========================================================================

    El andamio de pruebas crea las tablas desde los modelos actuales, asi que
    su CHECK incluye los nueve valores y el INSERT nunca falla. No es un
    descuido del andamio: es correcto que las pruebas corran contra el esquema
    declarado. Lo que falta —y es la leccion que queda— es que **un esquema
    declarado y una base real no son lo mismo**, y ningun test de integracion
    contra una base recien creada va a notar la diferencia.

    Este test no reproduce ese desfasaje: reproduce la **clase** de problema,
    forzando un INSERT que la tabla rechaza por un motivo que no es el email.
    Lo que fija es la unica cosa que de verdad importa y que no depende de cual
    sea el motivo: que el endpoint NO conteste que todo salio bien.
    """
    # Se fuerza un rol que el CHECK de la tabla no acepta. Es la forma mas
    # directa de provocar un IntegrityError que no sea el del indice unico.
    monkeypatch.setattr(autorizacion, "PENDIENTE", "rol_que_no_existe")

    with pytest.raises(IntegrityError):
        _registrar(cliente)

    # Y lo que hay que verificar: no quedo nada a medias y, sobre todo, nadie
    # recibio un 202 por algo que no se hizo.
    db.rollback()
    assert db.scalar(select(func.count()).select_from(Usuario)) == 0


def test_un_email_repetido_no_crea_una_segunda_fila(cliente, db):
    """La respuesta es la misma; lo que pasa en la base no."""
    _registrar(cliente)
    _registrar(cliente)

    assert db.scalar(select(func.count()).select_from(Usuario)) == 1


def test_un_email_repetido_no_le_pisa_los_datos_al_que_ya_existia(cliente, db):
    """El riesgo concreto de tragarse el error en vez de consultar antes.

    Si el INSERT fallido dejara algo escrito —o si alguien "arreglara" el
    duplicado haciendo un UPDATE—, cualquiera podria cambiarle el nombre, el
    telefono o la CONTRASENIA a una cuenta ajena mandando un registro con el
    email de esa persona. Seria un robo de cuenta por el endpoint publico.
    """
    _registrar(cliente)
    original = db.scalar(
        select(Usuario).where(Usuario.email == DATOS_BASE["email"])
    )
    hash_original = original.password_hash
    nombre_original = original.nombre

    _registrar(
        cliente,
        nombre="Intruso Suplantador",
        password="OtraClave456!",
        telefono="11 0000 0000",
    )

    db.expire_all()
    despues = db.scalar(
        select(Usuario).where(Usuario.email == DATOS_BASE["email"])
    )
    assert despues.nombre == nombre_original
    assert despues.password_hash == hash_original
    assert despues.telefono is None

    # Y la verificacion que de verdad importa: la persona original sigue
    # entrando con SU contrasenia, y la del intruso no sirve.
    assert _entrar(cliente, DATOS_BASE["email"])[0] == 200
    assert _entrar(cliente, DATOS_BASE["email"], "OtraClave456!")[0] == 401


def test_el_email_repetido_no_depende_de_mayusculas(cliente, db):
    """El duplicado se tiene que detectar aunque venga escrito distinto.

    Sin la normalizacion, `ANA@...` y `ana@...` serian dos filas para una sola
    persona —dos contrasenias y dos historiales—, y el indice unico no
    impediria nada porque distingue mayusculas.
    """
    _registrar(cliente)
    repetido = _registrar(cliente, email=DATOS_BASE["email"].upper())

    assert repetido.status_code == 202
    assert db.scalar(select(func.count()).select_from(Usuario)) == 1


def test_el_email_se_guarda_normalizado(cliente, db):
    _registrar(cliente, email="Ana.Mayuscula@Ejemplo.Com.Ar")

    usuario = db.scalar(select(Usuario))

    assert usuario.email == "ana.mayuscula@ejemplo.com.ar"
    # Y entra escribiendolo como quiera.
    assert _entrar(cliente, "ANA.MAYUSCULA@EJEMPLO.COM.AR")[0] == 200


def test_la_respuesta_no_filtra_nada_del_usuario(cliente):
    """Un solo campo de texto, y ninguno que dependa de lo que paso.

    Si llevara el id, el oraculo volveria por otra puerta: un id que avanza
    cuenta cuantas cuentas hay, y un id ausente delata el duplicado.
    """
    cuerpo = _registrar(cliente).json()

    assert set(cuerpo) == {"mensaje"}
    assert DATOS_BASE["email"] not in cuerpo["mensaje"]


def test_el_mensaje_le_dice_a_la_persona_que_hacer(cliente):
    """El texto es lo unico que recibe quien se registra, asi que tiene que
    decir las dos cosas: que falta una aprobacion y que ya puede entrar."""
    mensaje = _registrar(cliente).json()["mensaje"]

    assert "administrador" in mensaje.lower()
    assert "aprobar" in mensaje.lower()


# ===========================================================================
# DEFENSA 4 — `pendiente` ES VALIDO PERO NO ASIGNABLE
# ===========================================================================


def test_pendiente_no_aparece_entre_los_roles_del_formulario(cliente, como):
    """Si apareciera, el `<select>` del alta ofreceria "Pendiente de
    aprobación" como si fuera un rol del consorcio."""
    admin = como(autorizacion.ADMIN_GENERAL)

    cuerpo = cliente.get("/api/usuarios/opciones", headers=admin).json()

    nombres = [r["nombre"] for r in cuerpo["roles"]]
    assert autorizacion.PENDIENTE not in nombres
    assert nombres == list(autorizacion.ROLES_ASIGNABLES)


def test_el_alta_del_administrador_rechaza_el_rol_pendiente(cliente, db, como):
    """Nadie crea un pendiente a mano: lo crea el registro y nada mas."""
    admin = como(autorizacion.ADMIN_GENERAL)

    respuesta = cliente.post(
        "/api/usuarios",
        headers=admin,
        json={
            "nombre": "A mano",
            "email": "amano@ejemplo.com.ar",
            "password": PASSWORD_VALIDA,
            "rol": autorizacion.PENDIENTE,
        },
    )

    assert respuesta.status_code == 422
    assert "pendiente" in respuesta.text
    assert (
        db.scalar(
            select(Usuario).where(Usuario.email == "amano@ejemplo.com.ar")
        )
        is None
    )


def test_la_edicion_no_puede_devolver_a_alguien_al_estado_de_no_aprobado(
    cliente, db, como
):
    """No existe la operacion de desaprobar.

    Es el motivo concreto por el que `validar_rol` pregunta por
    `es_asignable` y no por `es_rol_valido`: con la segunda, este PATCH seria
    valido y le sacaria el acceso a alguien dejandolo en un estado que la
    aplicacion solo sabe crear, no deshacer. Para quitarle el acceso a una
    persona existe la baja logica, que es reversible y queda registrada.
    """
    admin = como(autorizacion.ADMIN_GENERAL)
    alta = cliente.post(
        "/api/usuarios",
        headers=admin,
        json={
            "nombre": "Aprobado",
            "email": "aprobado@ejemplo.com.ar",
            "password": PASSWORD_VALIDA,
            "rol": autorizacion.PROPIETARIO,
        },
    )
    usuario_id = alta.json()["id"]

    respuesta = cliente.patch(
        f"/api/usuarios/{usuario_id}",
        headers=admin,
        json={"rol": autorizacion.PENDIENTE},
    )

    assert respuesta.status_code == 422
    assert db.get(Usuario, usuario_id).rol == autorizacion.PROPIETARIO


def test_el_mensaje_del_rol_pendiente_explica_por_que_no_se_puede(cliente, como):
    """El mensaje generico —"los válidos son..." seguido de una lista que no lo
    incluye— no explica nada ante un valor que la persona vio en la interfaz.
    """
    admin = como(autorizacion.ADMIN_GENERAL)

    respuesta = cliente.post(
        "/api/usuarios",
        headers=admin,
        json={
            "nombre": "A mano",
            "email": "amano2@ejemplo.com.ar",
            "password": PASSWORD_VALIDA,
            "rol": autorizacion.PENDIENTE,
        },
    )

    assert "registra" in respuesta.text


# ===========================================================================
# LA POLITICA DE CONTRASENIA Y LA VALIDACION DE LOS DATOS
# ===========================================================================


@pytest.mark.parametrize(
    "password",
    [
        "corta1!",          # menos del minimo
        "sinmayuscula1!",   # sin mayuscula
        "SINMINUSCULA1!",   # sin minuscula
        "SinNumeroAca!",    # sin numero
        "SinSimbolo123",    # sin simbolo
    ],
)
def test_el_registro_aplica_la_misma_politica_de_contrasenia(cliente, db, password):
    """Que la persona se registre sola no es motivo para pedirle menos.

    La contrasenia debil de un propietario es la misma puerta de entrada que
    la de un administrador; la unica diferencia es lo que hay detras.
    """
    respuesta = _registrar(cliente, password=password)

    assert respuesta.status_code == 422
    assert db.scalar(select(func.count()).select_from(Usuario)) == 0


def test_un_email_mal_formado_no_se_registra(cliente, db):
    assert _registrar(cliente, email="esto-no-es-un-email").status_code == 422
    assert db.scalar(select(func.count()).select_from(Usuario)) == 0


def test_un_nombre_de_solo_espacios_no_se_registra(cliente, db):
    """Pasa el `min_length` de Pydantic porque tiene largo, y despues aparece
    como una fila en blanco en el listado y nadie sabe quien es."""
    assert _registrar(cliente, nombre="     ").status_code == 422
    assert db.scalar(select(func.count()).select_from(Usuario)) == 0


def test_el_nombre_se_guarda_sin_los_espacios_de_los_extremos(cliente, db):
    _registrar(cliente, nombre="  Ana Registrada  ")

    assert db.scalar(select(Usuario)).nombre == "Ana Registrada"


@pytest.mark.parametrize("falta", ["nombre", "email", "password"])
def test_los_tres_campos_obligatorios_lo_son(cliente, falta):
    cuerpo = {k: v for k, v in DATOS_BASE.items() if k != falta}

    respuesta = cliente.post("/api/auth/registro", json=cuerpo)

    assert respuesta.status_code == 422
    assert falta in respuesta.text


# ===========================================================================
# LA POLITICA DE CONTRASENIA, PUBLICA
# ===========================================================================
# El formulario de registro la usa para explicar que pide ANTES de que la
# persona escriba, y lo usa alguien que todavia no tiene cuenta. Lo que hay
# que fijar son dos cosas: que no pida sesion, y que diga exactamente lo
# mismo que el endpoint de admin, porque el dia que se desacoplen el alta y
# el registro van a pedir contrasenias distintas.


def test_la_politica_de_password_no_pide_autenticacion(cliente):
    respuesta = cliente.get("/api/auth/politica-password")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["requisitos"]
    assert cuerpo["minimo_caracteres"] > 0


def test_la_politica_publica_dice_lo_mismo_que_la_del_alta(cliente, como):
    publica = cliente.get("/api/auth/politica-password").json()
    delalta = cliente.get(
        "/api/usuarios/opciones", headers=como("admin_general")
    ).json()

    assert publica == delalta["password"]


def test_los_requisitos_publicados_son_los_que_el_registro_aplica(cliente):
    """Que la lista sea la misma tupla no alcanza: lo que importa es que una
    contrasenia rechazada lo sea por un motivo que esta en esa lista."""
    requisitos = cliente.get("/api/auth/politica-password").json()["requisitos"]

    respuesta = _registrar(cliente, password="corta")

    assert respuesta.status_code == 422
    # El 422 nombra al menos uno de los requisitos publicados, con las mismas
    # palabras: es lo unico que garantiza que el texto de ayuda y el del
    # rechazo no sean dos redacciones distintas de la misma regla.
    assert any(requisito in respuesta.text for requisito in requisitos)

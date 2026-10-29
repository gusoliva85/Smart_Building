"""Pruebas de `core/security.py`.

Lo que se prueba no es que bcrypt sepa hashear ni que PyJWT sepa firmar — eso
es responsabilidad de esas librerias y ya tienen sus propias pruebas. Lo que se
prueba es lo que ESTE modulo decidio:

  - que el mismo texto no produzca nunca el mismo hash (hay salt),
  - que el limite de 72 BYTES de bcrypt se trate como bytes y no caracteres,
  - que hashear falle ruidosamente y verificar nunca falle,
  - que un token no pueda falsificarse cambiando el algoritmo,
  - que un token sin vencimiento no se acepte.

Los dos ultimos son la razon por la que el proyecto dejo python-jose. Estan acá
para que no se puedan reintroducir sin que algo se ponga rojo.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core import config, security

# Una clave distinta de la del proyecto, para los tests que fabrican un token
# ajeno. Tiene 32 bytes a proposito: PyJWT avisa (y tiene razon) cuando una
# clave HMAC es mas corta que eso para SHA-256, y un warning de prueba que no
# importa termina tapando uno que si.
_CLAVE_AJENA = "clave-ajena-de-treinta-y-dos-byt"

# ------------------------------------------------------------ contrasenias ---


def test_el_hash_no_contiene_la_contrasenia(_=None):
    """Lo mas basico y lo mas importante: el texto plano no sobrevive."""
    hash_ = security.hashear_password("Secreta123!")

    assert "Secreta123!" not in hash_


def test_dos_hashes_de_la_misma_contrasenia_son_distintos():
    """Hay salt. Sin salt, dos usuarios con la misma contrasenia tendrian el
    mismo hash, y ver la tabla alcanzaria para saber quienes la comparten — y
    una sola tabla precalculada rompería todas juntas."""
    primero = security.hashear_password("Secreta123!")
    segundo = security.hashear_password("Secreta123!")

    assert primero != segundo


def test_la_contrasenia_correcta_verifica_contra_su_hash():
    hash_ = security.hashear_password("Secreta123!")

    assert security.verificar_password("Secreta123!", hash_) is True


def test_una_contrasenia_incorrecta_no_verifica():
    hash_ = security.hashear_password("Secreta123!")

    assert security.verificar_password("Secreta123", hash_) is False


def test_la_verificacion_distingue_mayusculas():
    hash_ = security.hashear_password("Secreta123!")

    assert security.verificar_password("secreta123!", hash_) is False


def test_una_contrasenia_con_acentos_y_enie_funciona():
    """UTF-8 ida y vuelta. Si en algun punto se codificara con otra cosa, la
    contrasenia dejaria de verificar justo para las personas que usan enie."""
    clave = "Contrasenia-Ñandú-123!"
    hash_ = security.hashear_password(clave)

    assert security.verificar_password(clave, hash_) is True


# --------------------------------------------- el limite de 72 bytes ---------


def test_una_contrasenia_de_72_bytes_todavia_entra():
    """El limite exacto, para que el control sea `>` y no `>=`.

    Un error de borde acá rechazaría una contrasenia perfectamente valida sin
    que nadie entienda por que.
    """
    al_limite = "a" * security.MAX_BYTES_PASSWORD
    hash_ = security.hashear_password(al_limite)

    assert security.verificar_password(al_limite, hash_) is True


def test_hashear_una_contrasenia_demasiado_larga_falla_ruidosamente():
    """Antes de bcrypt 4.1 el exceso se truncaba EN SILENCIO, y eso es peor que
    fallar: dos contrasenias distintas que comparten los primeros 72 bytes
    quedaban equivalentes para entrar."""
    with pytest.raises(security.PasswordDemasiadoLarga):
        security.hashear_password("a" * 73)


def test_el_limite_se_mide_en_bytes_y_no_en_caracteres():
    """La trampa concreta del castellano.

    37 caracteres acentuados son 74 bytes en UTF-8: pasa el limite sin llegar a
    40 letras. El error tiene que poder explicar esa diferencia, porque quien
    la escribio cuenta letras, no bytes.
    """
    acentuada = "á" * 37

    assert len(acentuada) == 37
    assert len(acentuada.encode("utf-8")) == 74

    with pytest.raises(security.PasswordDemasiadoLarga) as excepcion:
        security.hashear_password(acentuada)

    assert excepcion.value.caracteres == 37
    assert excepcion.value.bytes_recibidos == 74


def test_el_mensaje_del_error_no_incluye_la_contrasenia():
    """Los mensajes de error terminan en logs. Un log con contrasenias es una
    filtracion con fecha diferida."""
    secreto = "á" * 40

    with pytest.raises(security.PasswordDemasiadoLarga) as excepcion:
        security.hashear_password(secreto)

    assert secreto not in str(excepcion.value)


@pytest.mark.parametrize(
    "entrada_mala",
    [
        ("a" * 200, "$2b$12$hash-irrelevante"),  # contrasenia larguisima
        ("Secreta123!", ""),  # hash vacio
        ("Secreta123!", "esto-no-es-un-hash"),  # hash con formato invalido
        ("Secreta123!", "$2b$12$truncado"),  # hash bcrypt incompleto
    ],
)
def test_verificar_nunca_levanta_excepcion_ante_entrada_mala(entrada_mala):
    """En el login, una excepcion es un 500 en vez de un "credenciales
    invalidas" — y la diferencia entre un 500 y un 401 le dice a quien esta
    probando cual de sus intentos toco algo distinto."""
    password, hash_ = entrada_mala

    assert security.verificar_password(password, hash_) is False


# ----------------------------------------------------------------- JWT -------


def test_un_token_recien_emitido_identifica_a_su_usuario():
    token = security.crear_token_de_acceso(usuario_id=42)

    assert security.usuario_id_del_token(token) == 42


def test_el_sub_viaja_como_string_pero_vuelve_como_entero():
    """`sub` tiene que ser string por el estandar, y PyJWT lo valida. La
    conversion la hace este modulo para que ningun llamador tenga que
    acordarse: comparar un string con un int no da error, da False — y el
    usuario simplemente "no existe"."""
    token = security.crear_token_de_acceso(usuario_id=42)

    assert security.decodificar_token(token)["sub"] == "42"
    assert security.usuario_id_del_token(token) == 42


def test_el_token_no_lleva_el_rol():
    """Decision, no olvido: en los 60 minutos que vive un token le pueden
    cambiar el rol al usuario o desactivarlo. Un endpoint que confiara en el
    rol del token autorizaria con un dato viejo, y un usuario degradado
    seguiria operando como administrador hasta que su token venza."""
    cuerpo = security.decodificar_token(security.crear_token_de_acceso(usuario_id=42))

    assert set(cuerpo) == {"sub", "iat", "exp"}


def test_el_token_vence_a_los_sesenta_minutos():
    """El valor lo fija la configuracion; el test fija que se respete."""
    assert config.JWT_MINUTOS_EXPIRACION == 60

    cuerpo = security.decodificar_token(security.crear_token_de_acceso(usuario_id=1))
    duracion = cuerpo["exp"] - cuerpo["iat"]

    assert duracion == 60 * 60


def test_un_token_vencido_se_rechaza():
    token = security.crear_token_de_acceso(usuario_id=1, minutos=-1)

    with pytest.raises(security.TokenInvalido):
        security.decodificar_token(token)


def test_un_token_firmado_con_otra_clave_se_rechaza():
    """El caso de alguien que arma un token con la estructura correcta pero sin
    conocer el secreto."""
    ahora = datetime.now(timezone.utc)
    ajeno = jwt.encode(
        {"sub": "1", "iat": ahora, "exp": ahora + timedelta(minutes=60)},
        _CLAVE_AJENA,
        algorithm="HS256",
    )

    with pytest.raises(security.TokenInvalido):
        security.decodificar_token(ajeno)


def test_un_token_sin_firma_se_rechaza():
    """`alg: none` es la version mas directa del ataque de confusion de
    algoritmo: un token que declara no estar firmado. Si la decodificacion
    aceptara el algoritmo que el propio token declara, esto seria una sesion
    valida fabricada desde cero, sin secreto ninguno.

    Es, en esencia, la clase de vulnerabilidad por la que este proyecto dejo de
    usar python-jose. Este test existe para que no se pueda reintroducir a mano.
    """
    ahora = datetime.now(timezone.utc)
    sin_firma = jwt.encode(
        {"sub": "1", "iat": ahora, "exp": ahora + timedelta(minutes=60)},
        key="",
        algorithm="none",
    )

    with pytest.raises(security.TokenInvalido):
        security.decodificar_token(sin_firma)


def test_un_token_sin_vencimiento_se_rechaza():
    """Un token sin `exp` no vence nunca. Si la ausencia del campo se aceptara,
    alcanzaria con emitir uno sin el para tener una sesion eterna."""
    eterno = jwt.encode({"sub": "1"}, config.JWT_SECRETO, algorithm=config.JWT_ALGORITMO)

    with pytest.raises(security.TokenInvalido):
        security.decodificar_token(eterno)


def test_un_token_sin_sub_se_rechaza():
    ahora = datetime.now(timezone.utc)
    anonimo = jwt.encode(
        {"iat": ahora, "exp": ahora + timedelta(minutes=60)},
        config.JWT_SECRETO,
        algorithm=config.JWT_ALGORITMO,
    )

    with pytest.raises(security.TokenInvalido):
        security.decodificar_token(anonimo)


@pytest.mark.parametrize(
    "basura",
    ["", "no-es-un-token", "a.b.c", "Bearer algo"],
)
def test_una_cadena_que_no_es_un_token_se_rechaza(basura):
    """Incluye el caso de mandar el header completo ("Bearer algo") en vez del
    token solo, que es un error de integracion facil de cometer."""
    with pytest.raises(security.TokenInvalido):
        security.decodificar_token(basura)


def test_el_error_del_token_no_distingue_vencido_de_firma_invalida():
    """Hacia afuera es un solo error. Distinguirlos le diria a quien prueba
    tokens al azar cual de sus intentos estuvo mas cerca. Adentro, el detalle
    queda en `causa` para poder diagnosticar."""
    vencido = security.crear_token_de_acceso(usuario_id=1, minutos=-1)
    mal_firmado = jwt.encode({"sub": "1", "exp": 9999999999}, _CLAVE_AJENA, algorithm="HS256")

    mensajes = []
    causas = []
    for token in (vencido, mal_firmado):
        with pytest.raises(security.TokenInvalido) as excepcion:
            security.decodificar_token(token)
        mensajes.append(str(excepcion.value))
        causas.append(excepcion.value.causa)

    assert mensajes[0] == mensajes[1]
    assert causas[0] != causas[1]

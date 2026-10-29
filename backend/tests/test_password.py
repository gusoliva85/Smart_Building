"""Pruebas de la politica de contrasenia y del esquema de alta de usuario.

La politica es el requisito 4 de los lineamientos de seguridad de la facultad,
asi que lo que se prueba acá no es solo que rechace lo debil: es que el mensaje
diga **todo** lo que falta de una sola vez, y que el minimo y el maximo no se
contradigan entre si.
"""

import pytest
from pydantic import ValidationError

from app.core import security
from app.schemas.usuario import UsuarioCrear
from app.services import autorizacion

VALIDA = "Segura123!"


def _alta(**cambios):
    datos = {
        "nombre": "Ana Suarez",
        "email": "ana@ejemplo.com",
        "password": VALIDA,
        "rol": autorizacion.ADMIN_CONSORCIO,
    }
    datos.update(cambios)
    return UsuarioCrear(**datos)


# ------------------------------------------------------- la politica --------


def test_una_contrasenia_que_cumple_todo_no_tiene_faltantes():
    assert security.requisitos_faltantes(VALIDA) == ()


def test_validar_una_contrasenia_valida_no_levanta_nada():
    security.validar_password(VALIDA)


@pytest.mark.parametrize(
    "password, falta",
    [
        ("Corta1!", "al menos 8 caracteres"),
        ("segura123!", "una letra mayuscula"),
        ("SEGURA123!", "una letra minuscula"),
        ("SeguraSegura!", "un numero"),
        ("Segura123456", "un caracter especial"),
    ],
)
def test_cada_requisito_se_reporta_cuando_falta(password, falta):
    """Uno por requisito, cambiando SOLO ese, para que cada test diga cual es
    la regla que fija y no se tape un requisito roto con otro."""
    faltantes = security.requisitos_faltantes(password)

    assert any(falta in f for f in faltantes), faltantes


def test_se_reportan_TODOS_los_faltantes_juntos_y_no_solo_el_primero():
    """Un validador que corta en el primer problema obliga a reintentar de a
    una vez por requisito. Son cinco: en el peor caso, cinco rechazos seguidos
    para enterarse de todo lo que hacia falta de entrada."""
    with pytest.raises(security.PasswordInsegura) as excepcion:
        security.validar_password("abc")

    assert len(excepcion.value.faltantes) == 4  # largo, mayuscula, numero, especial
    mensaje = str(excepcion.value)
    for esperado in ("8 caracteres", "mayuscula", "numero", "caracter especial"):
        assert esperado in mensaje


def test_una_contrasenia_de_exactamente_ocho_caracteres_entra():
    """El borde del minimo, para que el control sea `>=` y no `>`."""
    assert security.requisitos_faltantes("Abcdef1!") == ()


# ------------------------------------- acentos, enie y el limite de bytes ----


def test_los_acentos_y_la_enie_cuentan_como_las_letras_que_son():
    """Un control hecho con a-z y A-Z le diria a quien usa una contrasenia en
    castellano que le falta una minuscula cuando no le falta.

    Acá la unica minuscula es la enie y la unica mayuscula lleva tilde.
    """
    assert security.requisitos_faltantes("Ñ1!ñandu") == ()
    assert security.requisitos_faltantes("Á1!ñññññ") == ()


@pytest.mark.parametrize("especial", ["!", "_", "¿", "€", " ", "-", "."])
def test_se_acepta_cualquier_caracter_no_alfanumerico_como_especial(especial):
    """Una lista fija de simbolos permitidos rechaza caracteres perfectamente
    validos que no figuran en ella —el guion bajo, los signos de apertura del
    castellano, el euro— y lo hace con un mensaje incomprensible: la persona
    puso un caracter especial y el sistema le dice que falta uno."""
    assert security.requisitos_faltantes(f"Segura12{especial}") == ()


def test_el_minimo_y_el_maximo_no_se_contradicen():
    """Los dos viven en el mismo modulo justamente para esto.

    Si el minimo de caracteres pudiera superar el maximo de bytes, habria
    contrasenias imposibles de crear: el esquema pediria mas largo y bcrypt
    rechazaria por largo. En el peor caso —todos los caracteres de 4 bytes—
    el minimo tiene que seguir entrando.
    """
    assert security.MIN_CARACTERES_PASSWORD * 4 <= security.MAX_BYTES_PASSWORD


def test_una_contrasenia_que_pasa_el_maximo_de_bytes_se_reporta_en_la_politica():
    """El tope de bcrypt tiene que atajarse en la validacion, con un 422 claro,
    y no explotar despues en el hasheo con un 500."""
    larga = "Añ1!" + "á" * 40

    faltantes = security.requisitos_faltantes(larga)

    assert any("72 bytes" in f for f in faltantes), faltantes


def test_el_maximo_se_reporta_ultimo():
    """Lo primero que se lee tiene que ser lo que falta, no lo que sobra."""
    faltantes = security.requisitos_faltantes("á" * 40)

    assert "72 bytes" in faltantes[-1]
    assert len(faltantes) > 1


# -------------------------------------------- el esquema de alta ------------


def test_el_alta_acepta_un_usuario_valido():
    usuario = _alta()

    assert usuario.email == "ana@ejemplo.com"
    assert usuario.telefono is None


def test_el_alta_rechaza_una_contrasenia_debil_con_el_detalle_completo():
    with pytest.raises(ValidationError) as excepcion:
        _alta(password="abc")

    mensaje = str(excepcion.value)
    for esperado in ("8 caracteres", "mayuscula", "numero", "caracter especial"):
        assert esperado in mensaje


def test_el_alta_rechaza_un_email_invalido():
    with pytest.raises(ValidationError):
        _alta(email="no-es-un-email")


@pytest.mark.parametrize(
    "escrito",
    ["ANA@EJEMPLO.COM", "Ana@Ejemplo.com", "ana@EJEMPLO.com", " Ana@ejemplo.com "],
)
def test_el_email_se_normaliza_a_minusculas(escrito):
    """Pydantic pasa el DOMINIO a minusculas por su cuenta, pero deja la parte
    local como vino. Sin este validador, `ANA@ejemplo.com` y `ana@ejemplo.com`
    serian dos filas distintas —dos usuarios, dos contrasenias, dos
    historiales— para una sola persona, porque el indice unico de la tabla
    distingue mayusculas."""
    assert _alta(email=escrito).email == "ana@ejemplo.com"


def test_dos_formas_de_escribir_el_mismo_email_terminan_en_el_mismo_valor():
    """El que importa de verdad: es lo que hace que el indice unico de la tabla
    pueda impedir el duplicado. Y en el login, es lo que evita que quien se dio
    de alta con mayuscula no pueda entrar escribiendo en minuscula."""
    assert _alta(email="Ana.Suarez@Ejemplo.COM").email == _alta(
        email="ana.suarez@ejemplo.com"
    ).email


def test_el_alta_rechaza_un_rol_que_no_esta_en_la_matriz():
    """Primera de las dos validaciones del rol: la que explica cuales valen."""
    with pytest.raises(ValidationError) as excepcion:
        _alta(rol="superadmin")

    assert "admin_general" in str(excepcion.value)


@pytest.mark.parametrize("rol", autorizacion.ROLES)
def test_el_alta_acepta_los_ocho_roles(rol):
    assert _alta(rol=rol).rol == rol


def test_el_alta_recorta_los_espacios_del_nombre():
    assert _alta(nombre="  Ana Suarez  ").nombre == "Ana Suarez"


def test_el_alta_rechaza_un_nombre_de_solo_espacios():
    """Pasa el `min_length` de Pydantic porque tiene largo, y despues aparece
    como una fila en blanco en el listado y nadie sabe quien es."""
    with pytest.raises(ValidationError):
        _alta(nombre="      ")


def test_lo_que_el_esquema_acepta_se_puede_hashear():
    """El cierre del circulo: la politica y el hasheo tienen que estar de
    acuerdo. Una contrasenia que el esquema aprueba y bcrypt rechaza seria un
    500 en el alta de usuario."""
    usuario = _alta(password="Añ1!" + "á" * 30)

    hash_ = security.hashear_password(usuario.password)

    assert security.verificar_password(usuario.password, hash_) is True

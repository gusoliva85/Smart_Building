"""Pruebas del seed del primer Administrador General.

Tres cosas que tienen que valer siempre:

  - que cree el administrador, con el rol correcto y la contrasenia hasheada,
  - que correrlo dos veces no duplique ni pise nada,
  - que NO pueda dejar un administrador de credenciales publicas en produccion.
"""

import importlib

import pytest
from sqlalchemy import select

from app import seed as seed_modulo
from app.core import security
from app.models.usuario import Usuario
from app.services import autorizacion


@pytest.fixture
def seed(monkeypatch):
    """Recarga el modulo del seed con el entorno que pida cada test.

    El modulo lee las variables al importarse, igual que `config`, asi que para
    probar otro escenario hay que volver a importarlo. Al terminar se restaura,
    porque si no el modulo queda contaminado para el resto de la suite.
    """

    def recargar(**entorno):
        for nombre in ("VERCEL", "SEED_ADMIN_EMAIL", "SEED_ADMIN_PASSWORD"):
            monkeypatch.delenv(nombre, raising=False)
        for nombre, valor in entorno.items():
            monkeypatch.setenv(nombre, valor)
        importlib.reload(seed_modulo.config)
        return importlib.reload(seed_modulo)

    yield recargar

    monkeypatch.undo()
    importlib.reload(seed_modulo.config)
    importlib.reload(seed_modulo)


# ------------------------------------------------------- el caso normal -----


def test_crea_el_administrador_general(db, seed):
    modulo = seed()

    resultado = modulo.sembrar(db)

    assert resultado.creado is True

    usuario = db.scalar(select(Usuario).where(Usuario.email == resultado.email))
    assert usuario is not None
    assert usuario.rol == autorizacion.ADMIN_GENERAL
    assert usuario.activo is True


def test_las_credenciales_del_readme_sirven_para_entrar(db, seed):
    """El test que de verdad importa: si esto falla, las credenciales anotadas
    en el README no sirven y el primer login es imposible."""
    modulo = seed()
    modulo.sembrar(db)

    usuario = db.scalar(select(Usuario).where(Usuario.email == "administrador@test.com"))

    assert usuario is not None
    assert security.verificar_password("Test1234!", usuario.password_hash) is True


def test_la_contrasenia_queda_hasheada_y_no_en_texto_plano(db, seed):
    modulo = seed()
    modulo.sembrar(db)

    usuario = db.scalar(select(Usuario).where(Usuario.email == modulo.EMAIL_ADMIN))

    assert modulo.PASSWORD_ADMIN not in usuario.password_hash
    assert usuario.password_hash.startswith("$2b$")


def test_la_contrasenia_sembrada_cumple_la_politica_del_sistema(seed):
    """El administrador inicial no puede ser la excepcion a la regla que el
    sistema le exige a todos los demas. Si alguien cambia la contrasenia de
    desarrollo por una debil, esto falla en el momento."""
    modulo = seed()

    assert security.requisitos_faltantes(modulo.PASSWORD_ADMIN_DESARROLLO) == ()


# -------------------------------------------------------- idempotencia ------


def test_correrlo_dos_veces_no_duplica_el_usuario(db, seed):
    modulo = seed()
    modulo.sembrar(db)

    segundo = modulo.sembrar(db)

    assert segundo.ya_existia is True
    assert len(db.scalars(select(Usuario)).all()) == 1


def test_no_pisa_la_contrasenia_de_un_administrador_existente(db, seed):
    """Si alguien le cambio la contrasenia al administrador, un seed que la
    pisara volveria a dejar la del README sin avisarle a nadie."""
    modulo = seed()
    modulo.sembrar(db)

    usuario = db.scalar(select(Usuario).where(Usuario.email == modulo.EMAIL_ADMIN))
    usuario.password_hash = security.hashear_password("OtraClave456$")
    db.commit()

    modulo.sembrar(db)

    db.refresh(usuario)
    assert security.verificar_password("OtraClave456$", usuario.password_hash) is True
    assert security.verificar_password(modulo.PASSWORD_ADMIN, usuario.password_hash) is False


# ---------------------------------------------------- guarda de produccion --


def test_en_produccion_no_siembra_con_las_credenciales_de_desarrollo(db, seed):
    """Un administrador con la contrasenia que figura en el README es, en
    produccion, una puerta abierta."""
    modulo = seed(VERCEL="1")

    with pytest.raises(modulo.SeedInseguro, match="SEED_ADMIN_PASSWORD"):
        modulo.sembrar(db)

    assert db.scalars(select(Usuario)).all() == []


def test_en_produccion_no_siembra_con_el_email_de_desarrollo(db, seed):
    """La contrasenia propia no alcanza: el email tambien es publico, y dejarlo
    le dice a cualquiera cual es la cuenta que tiene permisos totales."""
    modulo = seed(VERCEL="1", SEED_ADMIN_PASSWORD="UnaClaveReal789$")

    with pytest.raises(modulo.SeedInseguro, match="SEED_ADMIN_EMAIL"):
        modulo.sembrar(db)


def test_en_produccion_siembra_con_credenciales_propias(db, seed):
    """La otra mitad: la guarda no puede dejar al proyecto sin forma de crear
    su administrador real."""
    modulo = seed(
        VERCEL="1",
        SEED_ADMIN_EMAIL="admin@consorcio-real.com.ar",
        SEED_ADMIN_PASSWORD="UnaClaveReal789$",
    )

    resultado = modulo.sembrar(db)

    assert resultado.creado is True
    assert resultado.email == "admin@consorcio-real.com.ar"


def test_una_contrasenia_debil_por_variable_de_entorno_se_rechaza(db, seed):
    """La validacion se aplica tambien a lo que viene del entorno. Sin esto, la
    guarda de produccion se pasaria poniendo SEED_ADMIN_PASSWORD=1234."""
    modulo = seed(
        VERCEL="1",
        SEED_ADMIN_EMAIL="admin@consorcio-real.com.ar",
        SEED_ADMIN_PASSWORD="1234",
    )

    with pytest.raises(security.PasswordInsegura):
        modulo.sembrar(db)


def test_un_email_invalido_por_variable_de_entorno_se_rechaza(db, seed):
    """El seed es la UNICA via por la que entra un usuario sin pasar por el
    esquema de alta, asi que es la unica que podria guardar un email que el
    resto del sistema no considera valido. Y eso no se nota al sembrar: se nota
    despues, sobre una fila que ya existe."""
    modulo = seed(
        VERCEL="1",
        SEED_ADMIN_EMAIL="esto-no-es-un-email",
        SEED_ADMIN_PASSWORD="UnaClaveReal789$",
    )

    with pytest.raises(modulo.SeedEmailInvalido):
        modulo.sembrar(db)

    assert db.scalars(select(Usuario)).all() == []


def test_un_dominio_de_uso_reservado_se_rechaza(db, seed):
    """`.local` parece un dominio interno razonable y no lo es: los dominios de
    uso reservado los rechaza `email-validator`, asi que guardar uno dejaria
    una fila que despues falla en cualquier validacion."""
    modulo = seed(
        VERCEL="1",
        SEED_ADMIN_EMAIL="admin@consorcio.local",
        SEED_ADMIN_PASSWORD="UnaClaveReal789$",
    )

    with pytest.raises(modulo.SeedEmailInvalido):
        modulo.sembrar(db)


def test_el_email_del_entorno_se_normaliza(db, seed):
    """Misma normalizacion que el alta. Si el seed guardara con mayusculas, el
    login —que normaliza— no encontraria al usuario que acaba de crear."""
    modulo = seed(
        VERCEL="1",
        SEED_ADMIN_EMAIL="  Admin@Consorcio-Real.COM.AR  ",
        SEED_ADMIN_PASSWORD="UnaClaveReal789$",
    )

    assert modulo.sembrar(db).email == "admin@consorcio-real.com.ar"

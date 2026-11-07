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


# ---------------------------------------- los usuarios de prueba ------------
#
# Van detras de la bandera --con-pruebas, asi que lo que se prueba es tanto
# que los cree cuando se piden como que NO los cree cuando no se piden: lo
# segundo es lo que impide que un despliegue con datos reales se llene de
# cuentas con una contrasenia publicada.


def test_siembra_un_usuario_por_cada_rol_de_prueba(db, seed):
    modulo = seed()
    modulo.sembrar(db)

    resultados = modulo.sembrar_usuarios_de_prueba(db)

    assert len(resultados) == len(modulo.USUARIOS_DE_PRUEBA)
    assert all(r.creado for r in resultados)

    for rol, nombre, email in modulo.USUARIOS_DE_PRUEBA:
        usuario = db.scalar(select(Usuario).where(Usuario.email == email))
        assert usuario is not None, f"falta {email}"
        assert usuario.rol == rol
        assert usuario.nombre == nombre
        assert usuario.activo is True


def test_los_usuarios_de_prueba_pueden_entrar_con_la_clave_del_readme(
    db, cliente, seed
):
    """Lo unico que de verdad importa: que el login funcione.

    Un alta que deja la fila bien y despues no deja entrar es una cuenta
    perdida, porque no hay endpoint de recuperacion de contrasenia.
    """
    modulo = seed()
    modulo.sembrar(db)
    modulo.sembrar_usuarios_de_prueba(db)

    for _, _, email in modulo.USUARIOS_DE_PRUEBA:
        respuesta = cliente.post(
            "/api/auth/login",
            data={"username": email, "password": modulo.PASSWORD_ADMIN},
        )
        assert respuesta.status_code == 200, f"{email}: {respuesta.text}"


def test_correrlo_dos_veces_no_duplica_los_usuarios_de_prueba(db, seed):
    modulo = seed()
    modulo.sembrar(db)
    modulo.sembrar_usuarios_de_prueba(db)

    segundos = modulo.sembrar_usuarios_de_prueba(db)

    assert all(r.ya_existia for r in segundos)
    assert len(db.scalars(select(Usuario)).all()) == 1 + len(modulo.USUARIOS_DE_PRUEBA)


def test_no_pisa_la_contrasenia_de_un_usuario_de_prueba_existente(db, seed):
    """Misma regla que el administrador: si alguien le cambio la contrasenia,
    un seed que la pisara volveria a dejar la del README sin avisar."""
    modulo = seed()
    modulo.sembrar(db)
    modulo.sembrar_usuarios_de_prueba(db)

    _, _, email = modulo.USUARIOS_DE_PRUEBA[0]
    usuario = db.scalar(select(Usuario).where(Usuario.email == email))
    usuario.password_hash = security.hashear_password("OtraClaveDistinta9$")
    db.commit()
    hash_propio = usuario.password_hash

    modulo.sembrar_usuarios_de_prueba(db)

    db.refresh(usuario)
    assert usuario.password_hash == hash_propio


def test_los_roles_de_prueba_existen_en_la_matriz_de_autorizacion(seed):
    """Un rol mal escrito en la tabla crearia un usuario que el sistema no sabe
    autorizar, y el CheckConstraint del modelo lo rechazaria en produccion
    recien al correr el seed contra Postgres."""
    modulo = seed()

    for rol, _, _ in modulo.USUARIOS_DE_PRUEBA:
        assert rol in autorizacion.ROLES


def test_los_emails_de_prueba_usan_el_dominio_de_los_documentados(seed):
    """@test.com es lo que los distingue de los que crean los arneses, que usan
    @ejemplo.com. Sin esa convencion no hay forma mecanica de separar lo que se
    conserva de lo que se puede borrar."""
    modulo = seed()

    for _, _, email in modulo.USUARIOS_DE_PRUEBA:
        assert email.endswith("@test.com")


def test_sin_la_bandera_el_seed_no_crea_ningun_usuario_de_prueba(db, seed, monkeypatch):
    """El resguardo: por defecto se siembra SOLO el administrador."""
    modulo = seed()
    monkeypatch.setattr(modulo.sys, "argv", ["app.seed"])
    monkeypatch.setattr(modulo, "sincronizar_esquema", lambda: None)
    monkeypatch.setattr(modulo, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)

    assert modulo.main() == 0

    usuarios = db.scalars(select(Usuario)).all()
    assert len(usuarios) == 1
    assert usuarios[0].rol == autorizacion.ADMIN_GENERAL


def test_con_la_bandera_el_seed_crea_el_admin_y_los_de_prueba(db, seed, monkeypatch):
    modulo = seed()
    monkeypatch.setattr(modulo.sys, "argv", ["app.seed", "--con-pruebas"])
    monkeypatch.setattr(modulo, "sincronizar_esquema", lambda: None)
    monkeypatch.setattr(modulo, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)

    assert modulo.main() == 0

    usuarios = db.scalars(select(Usuario)).all()
    assert len(usuarios) == 1 + len(modulo.USUARIOS_DE_PRUEBA)
    assert {u.rol for u in usuarios} == {autorizacion.ADMIN_GENERAL} | {
        rol for rol, _, _ in modulo.USUARIOS_DE_PRUEBA
    }


def test_la_salida_sin_la_bandera_recuerda_que_la_bandera_existe(
    db, seed, monkeypatch, capsys
):
    """Correr el seed y no entender por que faltan los otros usuarios es el
    error facil de cometer. El aviso es la prevencion."""
    modulo = seed()
    monkeypatch.setattr(modulo.sys, "argv", ["app.seed"])
    monkeypatch.setattr(modulo, "sincronizar_esquema", lambda: None)
    monkeypatch.setattr(modulo, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)

    modulo.main()

    assert "--con-pruebas" in capsys.readouterr().out


def test_la_salida_nunca_imprime_la_contrasenia(db, seed, monkeypatch, capsys):
    """La regla de core/security.py: ninguna contrasenia se loguea en texto
    plano en ningun punto. La salida de un seed termina en la consola de un
    deploy o en el historial de una terminal."""
    modulo = seed()
    monkeypatch.setattr(modulo.sys, "argv", ["app.seed", "--con-pruebas"])
    monkeypatch.setattr(modulo, "sincronizar_esquema", lambda: None)
    monkeypatch.setattr(modulo, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)

    modulo.main()

    assert modulo.PASSWORD_ADMIN not in capsys.readouterr().out

"""Pruebas del modelo `Edificio` y de la clave foranea que cierra `F1-T03`.

No se prueba que SQLAlchemy sepa guardar una fila. Se prueba lo que la tabla
tiene que GARANTIZAR aunque el codigo de la aplicacion se equivoque:

  - que un dia de vencimiento, un recargo o una coordenada imposibles no
    puedan entrar ni por un INSERT directo,
  - que un CBU mal copiado se rechace al guardarlo y no cuando alguien
    intente transferir,
  - que la misma persona no quede como administrador y encargado del mismo
    edificio,
  - que un edificio nuevo nazca usable: activo, con dia de vencimiento y con
    todos los roles habilitados,
  - que las dos relaciones a `usuarios` apunten cada una a su columna,
  - y que `asignacion_edificio.edificio_id` tenga por fin su clave foranea.
"""

from decimal import Decimal

import pytest
from sqlalchemy import insert, inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.models.edificio import Edificio
from app.models.usuario import AsignacionEdificio, Usuario
from app.services import autorizacion

CBU_VALIDO = "0170099220000067797890"


def _edificio(**cambios) -> Edificio:
    """Un edificio valido, para que cada test declare solo lo que le importa."""
    datos = {
        "nombre": "Consorcio Rivadavia 1234",
        "direccion": "Av. Rivadavia 1234",
        "cp": "C1033",
    }
    datos.update(cambios)
    return Edificio(**datos)


def _usuario(rol, email) -> Usuario:
    return Usuario(
        nombre="Persona de prueba",
        email=email,
        password_hash="hash-irrelevante-para-estas-pruebas",
        rol=rol,
    )


def _insertar_crudo(db, **valores):
    """INSERT salteando SQLAlchemy entero, para probar lo que garantiza la base.

    Con `insert()` de Core, SQLAlchemy completa los defaults de Python antes de
    mandar la sentencia, asi que no sirve para ver que pone la BASE cuando la
    fila nace de un script o de una consola de psql. Esto si.
    """
    columnas = ", ".join(valores)
    marcadores = ", ".join(f":{nombre}" for nombre in valores)
    db.execute(
        text(f"INSERT INTO edificios ({columnas}) VALUES ({marcadores})"),
        valores,
    )
    db.commit()


# ------------------------------------------------- un edificio nace usable --


def test_un_edificio_nuevo_nace_activo(db):
    db.add(_edificio())
    db.commit()

    assert db.scalar(select(Edificio.activo)) is True


def test_un_edificio_nuevo_nace_con_un_dia_de_vencimiento_valido(db):
    """Sin esto, el primer calculo de expensas se encontraria con un NULL."""
    db.add(_edificio())
    db.commit()

    dia = db.scalar(select(Edificio.dias_vencimiento_expensas))
    assert 1 <= dia <= 31


def test_un_edificio_nuevo_nace_sin_recargo_por_mora(db):
    db.add(_edificio())
    db.commit()

    assert db.scalar(select(Edificio.recargo_mora_porcentual)) == Decimal("0")


def test_un_edificio_nuevo_nace_con_todos_los_roles_habilitados(db):
    """El default es "todos", no "ninguno".

    Una lista vacia bloquearia en silencio toda asignacion de un edificio
    recien creado, y nadie tendria forma de saber por que.
    """
    db.add(_edificio())
    db.commit()

    habilitados = db.scalar(select(Edificio.roles_habilitados))
    assert sorted(habilitados) == sorted(autorizacion.ROLES_HABILITABLES)


def test_la_base_pone_la_misma_lista_de_roles_que_la_aplicacion(db):
    """Una fila nacida desde un script tiene que quedar igual que una de la API.

    Son dos defaults distintos —el de Python y el `server_default`— y por eso
    se escriben desde la misma constante. Si alguien cambia uno solo, este test
    es el que lo encuentra.
    """
    _insertar_crudo(db, nombre="Desde un script", direccion="Calle 1", cp="1000")

    desde_script = db.scalar(select(Edificio.roles_habilitados))

    db.add(_edificio(nombre="Desde la aplicacion"))
    db.commit()
    desde_app = db.scalar(
        select(Edificio.roles_habilitados).where(
            Edificio.nombre == "Desde la aplicacion"
        )
    )

    assert sorted(desde_script) == sorted(desde_app)


def test_la_base_tambien_pone_el_estado_y_el_dia_de_vencimiento(db):
    _insertar_crudo(db, nombre="Desde un script", direccion="Calle 1", cp="1000")

    fila = db.execute(
        select(
            Edificio.activo,
            Edificio.dias_vencimiento_expensas,
            Edificio.recargo_mora_porcentual,
        )
    ).one()

    assert fila.activo
    assert 1 <= fila.dias_vencimiento_expensas <= 31
    assert fila.recargo_mora_porcentual == Decimal("0")


# -------------------------------------------- los roles que se habilitan ----


def test_los_roles_habilitables_son_los_asignables_sin_el_admin_general():
    """Su alcance es la cartera entera: no se habilita por edificio."""
    assert autorizacion.ADMIN_GENERAL not in autorizacion.ROLES_HABILITABLES
    assert autorizacion.PENDIENTE not in autorizacion.ROLES_HABILITABLES
    assert set(autorizacion.ROLES_HABILITABLES) == set(
        autorizacion.ROLES_ASIGNABLES
    ) - {autorizacion.ADMIN_GENERAL}


def test_los_roles_habilitados_se_guardan_como_lista(db):
    db.add(_edificio(roles_habilitados=[autorizacion.PROPIETARIO]))
    db.commit()
    db.expire_all()

    assert db.scalar(select(Edificio.roles_habilitados)) == [
        autorizacion.PROPIETARIO
    ]


def test_una_lista_vacia_de_roles_es_un_valor_valido(db):
    """"Ningun rol habilitado" tiene que poder expresarse, no ser un NULL."""
    db.add(_edificio(roles_habilitados=[]))
    db.commit()
    db.expire_all()

    assert db.scalar(select(Edificio.roles_habilitados)) == []


# ----------------------------------------------------- la configuracion -----


@pytest.mark.parametrize("dia", [0, 32, -1, 100])
def test_un_dia_de_vencimiento_que_no_es_un_dia_lo_rechaza_la_base(db, dia):
    with pytest.raises(IntegrityError):
        db.execute(
            insert(Edificio).values(
                nombre="X",
                direccion="Calle 1",
                cp="1000",
                dias_vencimiento_expensas=dia,
            )
        )
        db.commit()


@pytest.mark.parametrize("dia", [1, 10, 31])
def test_los_dias_de_vencimiento_reales_si_se_aceptan(db, dia):
    """La mitad que falta del test de arriba: un CHECK que rechace TODO
    tambien pasaria la prueba del valor invalido."""
    db.add(_edificio(dias_vencimiento_expensas=dia))
    db.commit()

    assert db.scalar(select(Edificio.dias_vencimiento_expensas)) == dia


@pytest.mark.parametrize("recargo", ["-0.01", "-5", "100.01", "500"])
def test_un_recargo_por_mora_imposible_lo_rechaza_la_base(db, recargo):
    """Negativo seria un descuento por pagar tarde."""
    with pytest.raises(IntegrityError):
        db.execute(
            insert(Edificio).values(
                nombre="X",
                direccion="Calle 1",
                cp="1000",
                recargo_mora_porcentual=Decimal(recargo),
            )
        )
        db.commit()


@pytest.mark.parametrize("recargo", ["0", "2.50", "10", "100"])
def test_los_recargos_reales_si_se_aceptan(db, recargo):
    db.add(_edificio(recargo_mora_porcentual=Decimal(recargo)))
    db.commit()

    assert db.scalar(select(Edificio.recargo_mora_porcentual)) == Decimal(recargo)


# ------------------------------------------------ la cuenta del consorcio ---


def test_un_cbu_de_veintidos_digitos_se_acepta(db):
    db.add(_edificio(cbu=CBU_VALIDO))
    db.commit()

    assert db.scalar(select(Edificio.cbu)) == CBU_VALIDO


def test_el_cbu_puede_quedar_sin_cargar(db):
    db.add(_edificio(cbu=None))
    db.commit()

    assert db.scalar(select(Edificio.cbu)) is None


@pytest.mark.parametrize("cbu", ["017009922000006779789", "01700992", ""])
def test_un_cbu_con_otra_cantidad_de_digitos_lo_rechaza_la_base(db, cbu):
    """Un CBU de 21 digitos es uno mal copiado, y el error tiene que aparecer
    al guardarlo, no cuando un propietario intente transferir."""
    with pytest.raises(IntegrityError):
        db.execute(
            insert(Edificio).values(
                nombre="X", direccion="Calle 1", cp="1000", cbu=cbu
            )
        )
        db.commit()


def test_el_cbu_conserva_el_cero_inicial(db):
    """Por eso es texto y no numero: como entero dejaria de ser un CBU."""
    db.add(_edificio(cbu=CBU_VALIDO))
    db.commit()

    assert db.scalar(select(Edificio.cbu)).startswith("0")


# ------------------------------------------------------------ ubicacion -----


def test_un_edificio_sin_coordenadas_es_valido(db):
    """`F1-T25`: una direccion que no se geocodifica avisa, pero no bloquea."""
    db.add(_edificio(latitud=None, longitud=None))
    db.commit()

    fila = db.execute(select(Edificio.latitud, Edificio.longitud)).one()
    assert fila.latitud is None and fila.longitud is None


def test_las_coordenadas_se_guardan_con_seis_decimales(db):
    db.add(
        _edificio(latitud=Decimal("-34.609722"), longitud=Decimal("-58.392222"))
    )
    db.commit()

    fila = db.execute(select(Edificio.latitud, Edificio.longitud)).one()
    assert fila.latitud == Decimal("-34.609722")
    assert fila.longitud == Decimal("-58.392222")


@pytest.mark.parametrize(
    "latitud,longitud",
    [
        ("91", "0"),
        ("-91", "0"),
        ("0", "181"),
        ("0", "-181"),
        ("200", "200"),
    ],
)
def test_una_coordenada_fuera_del_planeta_la_rechaza_la_base(db, latitud, longitud):
    with pytest.raises(IntegrityError):
        db.execute(
            insert(Edificio).values(
                nombre="X",
                direccion="Calle 1",
                cp="1000",
                latitud=Decimal(latitud),
                longitud=Decimal(longitud),
            )
        )
        db.commit()


# --------------------------------------------------------- responsables -----


def test_las_dos_relaciones_apuntan_cada_una_a_su_columna(db):
    """Hay DOS claves foraneas a `usuarios` y la ambiguedad no falla al
    importar: falla al primer uso de la relacion.

    Por eso se prueba usandolas, no leyendo la declaracion.
    """
    admin = _usuario(autorizacion.ADMIN_CONSORCIO, "admin@ejemplo.com")
    encargado = _usuario(autorizacion.ENCARGADO, "encargado@ejemplo.com")
    db.add_all([admin, encargado])
    db.commit()

    db.add(_edificio(admin_consorcio_id=admin.id, encargado_id=encargado.id))
    db.commit()
    db.expire_all()

    edificio = db.scalar(select(Edificio))
    assert edificio.admin_consorcio.email == "admin@ejemplo.com"
    assert edificio.encargado.email == "encargado@ejemplo.com"


def test_un_edificio_puede_no_tener_responsables_cargados_todavia(db):
    """Un edificio recien cargado puede no tener a su administrador dado de
    alta como usuario, y hay edificios sin encargado."""
    db.add(_edificio())
    db.commit()
    db.expire_all()

    edificio = db.scalar(select(Edificio))
    assert edificio.admin_consorcio is None
    assert edificio.encargado is None


def test_la_misma_persona_no_puede_ser_administrador_y_encargado(db):
    """Un usuario tiene UN rol: si las dos columnas coinciden, uno esta mal."""
    persona = _usuario(autorizacion.ADMIN_CONSORCIO, "dos.sombreros@ejemplo.com")
    db.add(persona)
    db.commit()

    with pytest.raises(IntegrityError):
        db.execute(
            insert(Edificio).values(
                nombre="X",
                direccion="Calle 1",
                cp="1000",
                admin_consorcio_id=persona.id,
                encargado_id=persona.id,
            )
        )
        db.commit()


def test_tener_uno_solo_de_los_dos_responsables_es_valido(db):
    persona = _usuario(autorizacion.ENCARGADO, "solo.encargado@ejemplo.com")
    db.add(persona)
    db.commit()

    db.add(_edificio(encargado_id=persona.id))
    db.commit()

    assert db.scalar(select(Edificio.encargado_id)) == persona.id


# ------------------------------- la clave foranea que cierra F1-T03 ---------


def test_asignacion_edificio_ya_tiene_su_clave_foranea(engine_prueba):
    """La deuda que `F1-T03` dejo anotada, cerrada.

    Se lee la declaracion con el inspector y no se prueba insertando un
    edificio inexistente, porque **SQLite no valida claves foraneas si no se
    enciende `PRAGMA foreign_keys`**, y en la base de prueba esta apagado. Lo
    que se verifica entonces es que la restriccion este declarada, que es lo
    que la hace existir en PostgreSQL, donde si se valida.
    """
    foraneas = inspect(engine_prueba).get_foreign_keys(
        AsignacionEdificio.__tablename__
    )

    destinos = {
        columna: fk["referred_table"]
        for fk in foraneas
        for columna in fk["constrained_columns"]
    }

    assert destinos.get("edificio_id") == Edificio.__tablename__
    assert destinos.get("usuario_id") == Usuario.__tablename__


def test_la_tabla_de_edificios_existe_en_la_base_de_prueba(engine_prueba):
    """Si falta en `TABLAS_DE_PRUEBA`, la FK de arriba no se puede crear."""
    assert Edificio.__tablename__ in inspect(engine_prueba).get_table_names()

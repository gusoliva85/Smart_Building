"""Pruebas del modelo `Usuario` y de `AsignacionEdificio`.

No se prueba que SQLAlchemy sepa guardar una fila. Se prueba lo que la tabla
tiene que GARANTIZAR aunque el codigo de la aplicacion se equivoque:

  - que un rol inexistente no pueda entrar ni por un INSERT directo,
  - que la lista de roles de la base no se desfase de la de la autorizacion,
  - que dos usuarios no puedan compartir email,
  - que un usuario nazca activo,
  - que la misma asignacion no se pueda cargar dos veces.
"""

import pytest
from sqlalchemy import insert, inspect, select
from sqlalchemy.exc import IntegrityError

from app.models.usuario import AsignacionEdificio, Usuario
from app.services import autorizacion


def _usuario(**cambios) -> Usuario:
    """Un usuario valido, para que cada test solo declare lo que le importa."""
    datos = {
        "nombre": "Ana Suarez",
        "email": "ana@ejemplo.com",
        "password_hash": "hash-irrelevante-para-estas-pruebas",
        "rol": autorizacion.ADMIN_CONSORCIO,
    }
    datos.update(cambios)
    return Usuario(**datos)


# ------------------------------------------------------------- el rol -------


@pytest.mark.parametrize("rol", autorizacion.ROLES)
def test_los_ocho_roles_de_la_matriz_son_aceptados(db, rol):
    """Lo que la autorizacion considera valido, la base lo acepta.

    Es la mitad que falta del test de abajo: sin esto, un CHECK mal escrito que
    rechazara TODO tambien pasaria la prueba del rol invalido.
    """
    db.add(_usuario(rol=rol, email=f"{rol}@ejemplo.com"))
    db.commit()

    assert db.scalar(select(Usuario.rol).where(Usuario.rol == rol)) == rol


def test_un_rol_inexistente_lo_rechaza_la_base(db):
    """El CHECK es la ultima linea de defensa, no un duplicado decorativo.

    Se prueba con `insert()` directo y no con el modelo a proposito: asi se
    saltea cualquier validacion de Python y se verifica que lo que rechaza es
    la BASE. Un rol invalido tiene que ser imposible tambien para un script de
    carga o para un arreglo a mano en una consola de psql.
    """
    with pytest.raises(IntegrityError):
        db.execute(
            insert(Usuario).values(
                nombre="Intruso",
                email="intruso@ejemplo.com",
                password_hash="x",
                rol="superadmin",
            )
        )
        db.commit()


def test_el_check_de_la_base_cubre_exactamente_los_roles_de_la_autorizacion(db):
    """La base y la aplicacion no pueden discrepar sobre que roles existen.

    Este test es el que avisa si alguien agrega un rol a `services/autorizacion`
    y el CHECK queda atras — o al reves. El desfasaje no da error al arrancar:
    da una base que acepta un rol que la aplicacion no sabe interpretar, y eso
    se descubre tarde y lejos.
    """
    restricciones = inspect(db.get_bind()).get_check_constraints("usuarios")
    rol_valido = next(r for r in restricciones if r["name"] == "ck_usuarios_rol_valido")

    en_la_base = {
        fragmento.strip().strip("'")
        for fragmento in rol_valido["sqltext"].split("(")[1].rstrip(")").split(",")
    }

    assert en_la_base == set(autorizacion.ROLES)


# -------------------------------------------------------- email y estado ----


def test_dos_usuarios_no_pueden_compartir_email(db):
    """La unicidad la garantiza la base, no una consulta previa del endpoint.

    Entre el "¿ya existe este email?" y el INSERT hay una ventana en la que
    otro request puede insertar el mismo: con dos altas simultaneas, las dos
    consultas dicen que no existe y las dos insertan.
    """
    db.add(_usuario(email="repetido@ejemplo.com"))
    db.commit()

    db.add(_usuario(nombre="Otra persona", email="repetido@ejemplo.com"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_un_usuario_nace_activo(db):
    """Nadie tiene que acordarse de pasar `activo=True` al crear un usuario."""
    usuario = _usuario()
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    assert usuario.activo is True


def test_la_fecha_de_creacion_la_pone_la_base(db):
    usuario = _usuario()
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    assert usuario.creado_en is not None


def test_el_telefono_es_opcional(db):
    """Un residente cargado por el administrador puede no haberlo dado."""
    usuario = _usuario(telefono=None)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    assert usuario.telefono is None


def test_la_baja_es_logica_y_conserva_la_fila(db):
    """Desactivar no borra: la trazabilidad de lo que cargo tiene que sobrevivir."""
    usuario = _usuario()
    db.add(usuario)
    db.commit()

    usuario.activo = False
    db.commit()

    assert db.scalar(select(Usuario).where(Usuario.email == usuario.email)) is not None


# ------------------------------------------------------- la asignacion ------


def test_una_asignacion_vincula_un_usuario_con_un_edificio(db):
    """El caso normal: un agente de seguridad asignado a dos edificios.

    Es lo que la tabla existe para poder expresar y una columna en `edificios`
    no podria: varios edificios para el mismo usuario.
    """
    guardia = _usuario(rol=autorizacion.SEGURIDAD, email="guardia@ejemplo.com")
    db.add(guardia)
    db.commit()

    db.add_all(
        [
            AsignacionEdificio(usuario_id=guardia.id, edificio_id=1),
            AsignacionEdificio(usuario_id=guardia.id, edificio_id=2),
        ]
    )
    db.commit()

    asignados = db.scalars(
        select(AsignacionEdificio.edificio_id).where(
            AsignacionEdificio.usuario_id == guardia.id
        )
    ).all()

    assert sorted(asignados) == [1, 2]


def test_la_misma_asignacion_no_se_puede_cargar_dos_veces(db):
    """La fila repetida no significa nada distinto de la primera.

    Dejarla entrar obligaria a desduplicar en cada consulta de alcance, para
    siempre y en todos lados.
    """
    auditor = _usuario(rol=autorizacion.AUDITOR, email="auditor@ejemplo.com")
    db.add(auditor)
    db.commit()

    db.add(AsignacionEdificio(usuario_id=auditor.id, edificio_id=7))
    db.commit()

    db.add(AsignacionEdificio(usuario_id=auditor.id, edificio_id=7))
    with pytest.raises(IntegrityError):
        db.commit()


def test_un_mismo_edificio_admite_varios_agentes_de_seguridad(db):
    """El hueco que esta tabla cierra: los turnos de seguridad.

    Con una columna `seguridad_id` en `edificios` esto seria imposible, y es el
    caso real — un edificio con portero de dia y de noche.
    """
    manana = _usuario(rol=autorizacion.SEGURIDAD, email="manana@ejemplo.com")
    noche = _usuario(rol=autorizacion.SEGURIDAD, email="noche@ejemplo.com")
    db.add_all([manana, noche])
    db.commit()

    db.add_all(
        [
            AsignacionEdificio(usuario_id=manana.id, edificio_id=3),
            AsignacionEdificio(usuario_id=noche.id, edificio_id=3),
        ]
    )
    db.commit()

    cuantos = db.scalars(
        select(AsignacionEdificio.usuario_id).where(AsignacionEdificio.edificio_id == 3)
    ).all()

    assert len(cuantos) == 2

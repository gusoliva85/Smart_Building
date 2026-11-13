"""Pruebas de la consulta de expensas (`F2-T06`).

Tres endpoints y una sola pregunta de fondo: **quien ve que**.

  - El listado y el detalle son de la administracion, con el alcance de
    siempre.
  - La vista por unidad la abre tambien el residente de esa unidad, y ahi esta
    todo lo que importa: **el residente ve solo las publicadas**, el Encargado
    no entra, y la unidad se busca dentro del edificio de la ruta.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models.edificio import Departamento, Edificio, Piso
from app.models.finanzas import Gasto
from app.models.usuario import Usuario
from app.services import autorizacion, finanzas


# ===========================================================================
# ESCENARIO
# ===========================================================================


def _usuario(db, rol: str, nombre: str) -> Usuario:
    from app.core import security

    usuario = Usuario(
        nombre=nombre,
        email=f"{nombre.lower().replace(' ', '')}@prueba.com.ar",
        password_hash=security.hashear_password("Prueba123!"),
        rol=rol,
        activo=True,
    )
    db.add(usuario)
    db.commit()
    return usuario


def _edificio_listo(db, cantidad_unidades: int = 2) -> Edificio:
    edificio = Edificio(nombre="Consorcio Mitre 500", direccion="Mitre 500", cp="C1000")
    db.add(edificio)
    db.commit()

    piso = Piso(edificio_id=edificio.id, numero="1", orden=1)
    db.add(piso)
    db.commit()

    for numero, coeficiente in enumerate(
        finanzas.calcular_partes_iguales(cantidad_unidades), start=1
    ):
        db.add(
            Departamento(
                piso_id=piso.id,
                identificador=f"1{chr(64 + numero)}",
                coeficiente=coeficiente,
            )
        )
    db.commit()
    return edificio


def _gasto(db, edificio, **columnas) -> Gasto:
    datos = {
        "edificio_id": edificio.id,
        "rubro": "limpieza",
        "monto": Decimal("100000.00"),
        "fecha": date(2026, 11, 5),
    }
    datos.update(columnas)
    gasto = Gasto(**datos)
    db.add(gasto)
    db.commit()
    return gasto


def _generar(cliente, edificio, headers, mes=11):
    return cliente.post(
        f"/api/edificios/{edificio.id}/expensas",
        json={"anio": 2026, "mes": mes},
        headers=headers,
    )


def _publicar(cliente, edificio, expensa_id, headers):
    return cliente.post(
        f"/api/edificios/{edificio.id}/expensas/{expensa_id}/publicar",
        headers=headers,
    )


# ===========================================================================
# EL LISTADO
# ===========================================================================


def test_el_listado_sale_de_la_mas_nueva_a_la_mas_vieja(cliente, como, db):
    edificio = _edificio_listo(db)
    _gasto(db, edificio, fecha=date(2026, 10, 5))
    _gasto(db, edificio, fecha=date(2026, 11, 5))
    _gasto(db, edificio, fecha=date(2026, 12, 5))
    headers = como("admin_general")
    for mes in (10, 11, 12):
        _generar(cliente, edificio, headers, mes=mes)

    cuerpo = cliente.get(
        f"/api/edificios/{edificio.id}/expensas", headers=headers
    ).json()

    assert [fila["periodo"] for fila in cuerpo] == ["12/2026", "11/2026", "10/2026"]


def test_el_listado_trae_los_borradores(cliente, como, db):
    """Deliberado: una expensa en borrador que nadie publico es plata que no se
    esta cobrando, asi que tiene que estar a la vista."""
    edificio = _edificio_listo(db)
    _gasto(db, edificio)
    headers = como("admin_general")
    _generar(cliente, edificio, headers)

    cuerpo = cliente.get(
        f"/api/edificios/{edificio.id}/expensas", headers=headers
    ).json()

    assert cuerpo[0]["estado"] == "borrador"


def test_el_listado_dice_si_se_puede_regenerar(cliente, como, db):
    """Lo calcula el servidor. Una pantalla que lo deduzca del estado es una
    pantalla que algun dia ofrece un boton que el servidor va a rechazar."""
    edificio = _edificio_listo(db)
    _gasto(db, edificio)
    headers = como("admin_general")
    expensa = _generar(cliente, edificio, headers).json()

    antes = cliente.get(f"/api/edificios/{edificio.id}/expensas", headers=headers)
    _publicar(cliente, edificio, expensa["id"], headers)
    despues = cliente.get(f"/api/edificios/{edificio.id}/expensas", headers=headers)

    assert antes.json()[0]["se_puede_regenerar"] is True
    assert despues.json()[0]["se_puede_regenerar"] is False


def test_el_listado_cuenta_unidades_y_rubros(cliente, como, db):
    edificio = _edificio_listo(db, cantidad_unidades=2)
    _gasto(db, edificio, rubro="limpieza")
    _gasto(db, edificio, rubro="sueldos")
    headers = como("admin_general")
    _generar(cliente, edificio, headers)

    fila = cliente.get(
        f"/api/edificios/{edificio.id}/expensas", headers=headers
    ).json()[0]

    assert fila["cantidad_unidades"] == 2
    assert fila["cantidad_rubros"] == 2


def test_el_listado_se_filtra_por_anio(cliente, como, db):
    edificio = _edificio_listo(db)
    _gasto(db, edificio, fecha=date(2026, 11, 5))
    headers = como("admin_general")
    _generar(cliente, edificio, headers)

    cuerpo = cliente.get(
        f"/api/edificios/{edificio.id}/expensas?anio=2025", headers=headers
    ).json()

    assert cuerpo == []


def test_un_edificio_sin_liquidaciones_devuelve_lista_vacia(cliente, como, db):
    """El estado inicial de todo edificio. Un 404 obligaria a la pantalla a
    tratar lo normal como una excepcion."""
    edificio = _edificio_listo(db)

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/expensas", headers=como("admin_general")
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_un_residente_no_ve_el_listado_del_edificio(cliente, como, db):
    """El listado completo es de la administracion. El residente tiene su
    propia vista, la de su unidad."""
    edificio = _edificio_listo(db)

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/expensas", headers=como("propietario")
    )

    assert respuesta.status_code == 403


def test_un_admin_de_consorcio_no_ve_el_listado_de_un_edificio_ajeno(
    cliente, como, db
):
    ajeno = _edificio_listo(db)

    respuesta = cliente.get(
        f"/api/edificios/{ajeno.id}/expensas",
        headers=como(autorizacion.ADMIN_CONSORCIO),
    )

    assert respuesta.status_code == 404


# ===========================================================================
# EL DETALLE
# ===========================================================================


def test_el_detalle_es_igual_al_que_devuelve_generar(cliente, como, db):
    """A proposito: la pantalla que muestra una expensa recien generada y la
    que muestra una vieja son la misma pantalla."""
    edificio = _edificio_listo(db)
    _gasto(db, edificio)
    headers = como("admin_general")
    generada = _generar(cliente, edificio, headers).json()

    leida = cliente.get(
        f"/api/edificios/{edificio.id}/expensas/{generada['id']}", headers=headers
    ).json()

    assert leida == generada


def test_el_detalle_de_una_expensa_que_no_existe(cliente, como, db):
    edificio = _edificio_listo(db)

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/expensas/9999", headers=como("admin_general")
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "EXPENSA_NO_ENCONTRADA"


def test_no_se_lee_el_detalle_de_la_expensa_de_otro_edificio(cliente, como, db):
    """Se la busca siempre dentro del edificio ya verificado: sin eso, el id de
    una liquidacion de otro consorcio entraria igual."""
    mio = _edificio_listo(db)
    otro = _edificio_listo(db)
    _gasto(db, otro)
    headers = como("admin_general")
    ajena = _generar(cliente, otro, headers).json()

    respuesta = cliente.get(
        f"/api/edificios/{mio.id}/expensas/{ajena['id']}", headers=headers
    )

    assert respuesta.status_code == 404


# ===========================================================================
# LA VISTA DE LA UNIDAD — "MI CUENTA"
# ===========================================================================


def _ruta_unidad(edificio, unidad) -> str:
    return f"/api/edificios/{edificio.id}/departamentos/{unidad.id}/expensas"


def _login(cliente, usuario) -> dict:
    respuesta = cliente.post(
        "/api/auth/login",
        data={"username": usuario.email, "password": "Prueba123!"},
    )
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def test_el_propietario_ve_la_expensa_de_su_unidad(cliente, como, db):
    edificio = _edificio_listo(db)
    unidad = db.scalars(select(Departamento)).first()
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Dueno Uno")
    unidad.propietario_id = propietario.id
    db.commit()
    _gasto(db, edificio, monto=Decimal("100000.00"))
    admin = como("admin_general")
    expensa = _generar(cliente, edificio, admin).json()
    _publicar(cliente, edificio, expensa["id"], admin)

    cuerpo = cliente.get(
        _ruta_unidad(edificio, unidad), headers=_login(cliente, propietario)
    ).json()

    assert len(cuerpo) == 1
    assert cuerpo[0]["total_a_pagar"] == "50000.00"
    assert cuerpo[0]["total_edificio"] == "100000.00"


def test_la_vista_de_la_unidad_trae_la_apertura_por_rubro(cliente, como, db):
    """La transparencia que pide el Documento General: el consorcista tiene
    derecho a ver **en que** se gasto, no solo cuanto le toca."""
    edificio = _edificio_listo(db)
    unidad = db.scalars(select(Departamento)).first()
    inquilino = _usuario(db, autorizacion.INQUILINO, "Inquilino Uno")
    unidad.inquilino_id = inquilino.id
    db.commit()
    _gasto(db, edificio, rubro="limpieza", monto=Decimal("40000.00"))
    _gasto(db, edificio, rubro="sueldos", monto=Decimal("60000.00"))
    admin = como("admin_general")
    expensa = _generar(cliente, edificio, admin).json()
    _publicar(cliente, edificio, expensa["id"], admin)

    cuerpo = cliente.get(
        _ruta_unidad(edificio, unidad), headers=_login(cliente, inquilino)
    ).json()

    rubros_vistos = {linea["rubro"]: linea["monto"] for linea in cuerpo[0]["detalle"]}
    assert rubros_vistos == {"sueldos": "60000.00", "limpieza": "40000.00"}


def test_el_residente_no_ve_los_borradores(cliente, como, db):
    """**La regla que importa.** Mostrarle un borrador seria anticiparle un
    monto que la administracion todavia puede cambiar, y despues reclamaria por
    la diferencia."""
    edificio = _edificio_listo(db)
    unidad = db.scalars(select(Departamento)).first()
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Dueno Dos")
    unidad.propietario_id = propietario.id
    db.commit()
    _gasto(db, edificio)
    _generar(cliente, edificio, como("admin_general"))

    cuerpo = cliente.get(
        _ruta_unidad(edificio, unidad), headers=_login(cliente, propietario)
    ).json()

    assert cuerpo == []


def test_la_administracion_si_ve_los_borradores_de_una_unidad(cliente, como, db):
    edificio = _edificio_listo(db)
    unidad = db.scalars(select(Departamento)).first()
    _gasto(db, edificio)
    headers = como("admin_general")
    _generar(cliente, edificio, headers)

    cuerpo = cliente.get(_ruta_unidad(edificio, unidad), headers=headers).json()

    assert len(cuerpo) == 1
    assert cuerpo[0]["estado"] == "borrador"


def test_un_residente_no_ve_la_cuenta_de_otra_unidad(cliente, como, db):
    """404 y no 403: con un 403, probar ids seria una forma de averiguar que
    unidades existen."""
    edificio = _edificio_listo(db)
    unidades = db.scalars(select(Departamento)).all()
    propietario = _usuario(db, autorizacion.PROPIETARIO, "Dueno Tres")
    unidades[0].propietario_id = propietario.id
    db.commit()

    respuesta = cliente.get(
        _ruta_unidad(edificio, unidades[1]), headers=_login(cliente, propietario)
    )

    assert respuesta.status_code == 404


def test_el_encargado_no_ve_la_cuenta_de_una_unidad(cliente, como, db):
    """Puede ver el edificio porque trabaja ahi, pero cuanto debe el 3B es
    informacion economica de una familia. Es la clase de permiso que se concede
    "porque ya veia el edificio" y despues nadie revisa."""
    edificio = _edificio_listo(db)
    unidad = db.scalars(select(Departamento)).first()
    encargado = _usuario(db, autorizacion.ENCARGADO, "Encargado Uno")
    edificio.encargado_id = encargado.id
    db.commit()

    respuesta = cliente.get(
        _ruta_unidad(edificio, unidad), headers=_login(cliente, encargado)
    )

    assert respuesta.status_code == 404


def test_la_unidad_se_busca_dentro_del_edificio_de_la_ruta(cliente, como, db):
    """Sin eso, el id del edificio en la ruta seria decorativo: pedir la unidad
    del edificio 2 por la ruta del edificio 1 contestaria igual."""
    uno = _edificio_listo(db)
    otro = _edificio_listo(db)
    ajena = db.scalars(
        select(Departamento)
        .join(Piso, Piso.id == Departamento.piso_id)
        .where(Piso.edificio_id == otro.id)
    ).first()

    respuesta = cliente.get(
        f"/api/edificios/{uno.id}/departamentos/{ajena.id}/expensas",
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 404


def test_una_unidad_que_no_existe(cliente, como, db):
    edificio = _edificio_listo(db)

    respuesta = cliente.get(
        f"/api/edificios/{edificio.id}/departamentos/9999/expensas",
        headers=como("admin_general"),
    )

    assert respuesta.status_code == 404


def test_sin_sesion_no_se_ve_la_cuenta_de_una_unidad(cliente, db):
    edificio = _edificio_listo(db)
    unidad = db.scalars(select(Departamento)).first()

    respuesta = cliente.get(_ruta_unidad(edificio, unidad))

    assert respuesta.status_code == 401


def test_una_unidad_sin_liquidaciones_devuelve_lista_vacia(cliente, como, db):
    edificio = _edificio_listo(db)
    unidad = db.scalars(select(Departamento)).first()

    respuesta = cliente.get(_ruta_unidad(edificio, unidad), headers=como("admin_general"))

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_las_liquidaciones_de_la_unidad_salen_de_la_mas_nueva_a_la_mas_vieja(
    cliente, como, db
):
    edificio = _edificio_listo(db)
    unidad = db.scalars(select(Departamento)).first()
    _gasto(db, edificio, fecha=date(2026, 10, 5))
    _gasto(db, edificio, fecha=date(2026, 11, 5))
    headers = como("admin_general")
    _generar(cliente, edificio, headers, mes=10)
    _generar(cliente, edificio, headers, mes=11)

    cuerpo = cliente.get(_ruta_unidad(edificio, unidad), headers=headers).json()

    assert [fila["periodo"] for fila in cuerpo] == ["11/2026", "10/2026"]


def test_el_coeficiente_con_el_que_se_calculo_viaja_en_la_respuesta(cliente, como, db):
    """Es lo que le permite al propietario verificar la cuenta: su porcentual
    sobre el total del edificio."""
    edificio = _edificio_listo(db)
    unidad = db.scalars(select(Departamento)).first()
    _gasto(db, edificio)
    headers = como("admin_general")
    _generar(cliente, edificio, headers)

    cuerpo = cliente.get(_ruta_unidad(edificio, unidad), headers=headers).json()

    assert Decimal(cuerpo[0]["coeficiente"]) == Decimal("50.000")

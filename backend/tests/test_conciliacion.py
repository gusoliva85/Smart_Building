"""Pruebas de la conciliacion y de la cola de pagos (`F2-T09`).

Es el acto que mueve el saldo, asi que lo que se prueba son las tres barreras
que lo protegen y el efecto que tiene:

  1. **Solo la administracion concilia**, y solo en su edificio.
  2. **Quien cargo el pago no lo concilia**, ni siquiera siendo administrador.
  3. **Un pago ya conciliado no se vuelve a conciliar**, en ningun sentido.
  4. Y lo que importa de verdad: **confirmar baja la deuda, rechazar no**.

El cuarto punto cierra el circuito del dinero. Hasta esta tarea, ningun pago
podia llegar a `confirmado` por la via normal — en los tests de `F2-T08` hubo
que escribirlo a mano en la base.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core import security
from app.models.edificio import Departamento, Edificio, Piso
from app.models.finanzas import Gasto, Pago
from app.models.usuario import Usuario
from app.services import autorizacion, finanzas


# ===========================================================================
# ESCENARIO
# ===========================================================================


def _usuario(db, rol: str, nombre: str) -> Usuario:
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


def _login(cliente, usuario) -> dict:
    respuesta = cliente.post(
        "/api/auth/login",
        data={"username": usuario.email, "password": "Prueba123!"},
    )
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def _edificio_listo(db, nombre="Mitre 500") -> Edificio:
    edificio = Edificio(nombre=nombre, direccion=f"{nombre} 1", cp="C1000")
    db.add(edificio)
    db.commit()
    piso = Piso(edificio_id=edificio.id, numero="1", orden=1)
    db.add(piso)
    db.commit()
    for numero, coeficiente in enumerate(finanzas.calcular_partes_iguales(2), start=1):
        db.add(
            Departamento(
                piso_id=piso.id,
                identificador=f"1{chr(64 + numero)}",
                coeficiente=coeficiente,
            )
        )
    db.commit()
    return edificio


def _escenario(cliente, como, db, nombre="Mitre 500"):
    """Edificio liquidado y publicado, con un propietario que ya cargo un pago.

    Devuelve todo lo que los tests necesitan: el edificio, su unidad 1A, el
    propietario, el pago cargado y el header del administrador.
    """
    admin = como("admin_general")
    edificio = _edificio_listo(db, nombre)
    unidad = db.scalars(
        select(Departamento)
        .join(Piso, Piso.id == Departamento.piso_id)
        .where(Piso.edificio_id == edificio.id)
        .order_by(Departamento.identificador)
    ).first()

    propietario = _usuario(db, autorizacion.PROPIETARIO, f"Dueno {nombre}")
    unidad.propietario_id = propietario.id
    db.commit()

    db.add(
        Gasto(
            edificio_id=edificio.id,
            rubro="limpieza",
            monto=Decimal("100000.00"),
            fecha=date(2026, 11, 5),
        )
    )
    db.commit()

    expensa = cliente.post(
        f"/api/edificios/{edificio.id}/expensas",
        json={"anio": 2026, "mes": 11},
        headers=admin,
    ).json()
    cliente.post(
        f"/api/edificios/{edificio.id}/expensas/{expensa['id']}/publicar",
        headers=admin,
    )

    pago = cliente.post(
        "/api/mis-pagos",
        json={
            "expensa_id": expensa["id"],
            "monto": "50000.00",
            "fecha": "2026-12-05",
            "medio_pago": "transferencia",
        },
        headers=_login(cliente, propietario),
    ).json()

    return edificio, unidad, propietario, pago, admin


MOTIVO = "El monto no coincide con el comprobante"


def _conciliar(cliente, edificio, pago_id, headers, estado="confirmado", motivo=None):
    """Concilia un pago. Al rechazar manda un motivo, porque es obligatorio.

    El valor por defecto no es `None` para el rechazo a proposito: casi todos
    los tests de rechazo prueban **otra cosa** y no la regla del motivo, asi
    que el helper pone uno valido. Los tests de la regla lo pasan explicito.
    """
    cuerpo = {"estado": estado}
    if motivo is not None:
        cuerpo["motivo"] = motivo
    elif estado == "rechazado":
        cuerpo["motivo"] = MOTIVO

    return cliente.patch(
        f"/api/edificios/{edificio.id}/pagos/{pago_id}",
        json=cuerpo,
        headers=headers,
    )


# ===========================================================================
# CONFIRMAR Y RECHAZAR
# ===========================================================================


def test_confirmar_un_pago_baja_la_deuda(cliente, como, db):
    """**El circuito completo del dinero, de punta a punta.** Es lo que esta
    tarea habilita: hasta aca, ningun pago podia llegar a confirmado por la via
    normal."""
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)
    residente = _login(cliente, propietario)

    antes = cliente.get("/api/mis-unidades", headers=residente).json()[0]
    _conciliar(cliente, edificio, pago["id"], admin)
    despues = cliente.get("/api/mis-unidades", headers=residente).json()[0]

    assert antes["deuda"] == "50000.00"
    assert despues["deuda"] == "0.00"
    assert despues["pendiente_de_confirmar"] == "0.00"


def test_rechazar_un_pago_no_baja_la_deuda(cliente, como, db):
    """Plata que no entro. Y el pendiente deja de contar como pendiente: el
    residente tiene que ver que su pago no prospero."""
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    _conciliar(cliente, edificio, pago["id"], admin, estado="rechazado")

    cuenta = cliente.get(
        "/api/mis-unidades", headers=_login(cliente, propietario)
    ).json()[0]
    assert cuenta["deuda"] == "50000.00"
    assert cuenta["pendiente_de_confirmar"] == "0.00"


def test_queda_registrado_quien_concilio_y_cuando(cliente, como, db):
    """Un circuito de dinero sin ese nombre no se puede auditar."""
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    cuerpo = _conciliar(cliente, edificio, pago["id"], admin).json()

    assert cuerpo["estado"] == "confirmado"
    assert cuerpo["conciliado_por"]
    assert cuerpo["conciliado_en"] is not None


def test_un_pago_confirmado_no_se_puede_rechazar_despues(cliente, como, db):
    """Si se confirmo por equivocacion, lo que corresponde es registrar el
    movimiento que lo corrige, no reescribir el historial."""
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)
    _conciliar(cliente, edificio, pago["id"], admin)

    respuesta = _conciliar(cliente, edificio, pago["id"], admin, estado="rechazado")

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "PAGO_YA_CONCILIADO"


def test_un_pago_rechazado_no_se_reactiva(cliente, como, db):
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)
    _conciliar(cliente, edificio, pago["id"], admin, estado="rechazado")

    respuesta = _conciliar(cliente, edificio, pago["id"], admin)

    assert respuesta.json()["codigo"] == "PAGO_YA_CONCILIADO"


def test_confirmar_dos_veces_el_mismo_pago_no_vuelve_a_registrar_nada(
    cliente, como, db
):
    """No es inofensivo: pisaria quien lo concilio y cuando."""
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)
    _conciliar(cliente, edificio, pago["id"], admin)

    respuesta = _conciliar(cliente, edificio, pago["id"], admin)

    assert respuesta.status_code == 400


def test_no_se_puede_conciliar_a_pendiente(cliente, como, db):
    """Nadie "concilia a pendiente": es un pedido mal formado."""
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    respuesta = _conciliar(cliente, edificio, pago["id"], admin, estado="pendiente")

    assert respuesta.status_code == 422


def test_un_estado_inventado_se_rechaza(cliente, como, db):
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    respuesta = _conciliar(cliente, edificio, pago["id"], admin, estado="acreditado")

    assert respuesta.status_code == 422


# ===========================================================================
# QUIEN PUEDE CONCILIAR
# ===========================================================================


def test_el_residente_no_concilia_su_propio_pago(cliente, como, db):
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    respuesta = _conciliar(
        cliente, edificio, pago["id"], _login(cliente, propietario)
    )

    assert respuesta.status_code == 403


def test_el_encargado_no_concilia(cliente, como, db):
    """Gestiona reclamos, no la plata del consorcio."""
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    respuesta = _conciliar(cliente, edificio, pago["id"], como("encargado"))

    assert respuesta.status_code == 403


def test_el_administrador_que_vive_en_el_edificio_no_concilia_su_propio_pago(
    cliente, como, db
):
    """**El caso que de verdad pasa**, y la razon por la que la regla se
    escribe por quien cargo el pago y no por rol: una persona administra el
    consorcio y es propietaria de una unidad. Concilia los pagos de sus
    vecinos, no el suyo.
    """
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    # El administrador general tambien es propietario de la unidad 1B y carga
    # su propio pago.
    administrador = db.scalars(
        select(Usuario)
        .where(Usuario.rol == autorizacion.ADMIN_GENERAL)
        .order_by(Usuario.id.desc())
    ).first()
    otra = db.scalars(
        select(Departamento)
        .join(Piso, Piso.id == Departamento.piso_id)
        .where(Piso.edificio_id == edificio.id)
        .order_by(Departamento.identificador.desc())
    ).first()
    otra.propietario_id = administrador.id
    db.commit()

    suyo = cliente.post(
        "/api/mis-pagos",
        json={
            "expensa_id": pago["expensa_id"],
            "monto": "10000.00",
            "fecha": "2026-12-06",
            "medio_pago": "transferencia",
        },
        headers=admin,
    ).json()

    propio = _conciliar(cliente, edificio, suyo["id"], admin)
    ajeno = _conciliar(cliente, edificio, pago["id"], admin)

    assert propio.status_code == 403
    assert propio.json()["codigo"] == "NO_PODES_CONCILIAR_TU_PAGO"
    assert ajeno.status_code == 200, ajeno.text


def test_otro_administrador_si_puede_conciliar_ese_pago(cliente, como, db):
    """La regla no bloquea el pago: bloquea que lo valide quien lo declaro."""
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)
    otro_admin = como("admin_general")

    respuesta = _conciliar(cliente, edificio, pago["id"], otro_admin)

    assert respuesta.status_code == 200, respuesta.text


def test_un_admin_de_consorcio_no_concilia_pagos_de_un_edificio_ajeno(
    cliente, como, db
):
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    respuesta = _conciliar(
        cliente, edificio, pago["id"], como(autorizacion.ADMIN_CONSORCIO)
    )

    assert respuesta.status_code == 404


def test_un_pago_de_otro_edificio_no_se_concilia_por_la_ruta_equivocada(
    cliente, como, db
):
    """La tabla de pagos no tiene `edificio_id`: cuelga de la unidad. Sin el
    salto por el piso, el id de un pago de otro consorcio entraria igual."""
    uno = _escenario(cliente, como, db, nombre="Mitre 500")
    otro = _escenario(cliente, como, db, nombre="Otro 900")
    mi_edificio = uno[0]
    pago_ajeno = otro[3]

    respuesta = _conciliar(cliente, mi_edificio, pago_ajeno["id"], uno[4])

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "PAGO_NO_ENCONTRADO"


def test_conciliar_un_pago_que_no_existe(cliente, como, db):
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    respuesta = _conciliar(cliente, edificio, 9999, admin)

    assert respuesta.status_code == 404


def test_sin_sesion_no_se_concilia(cliente, como, db):
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/pagos/{pago['id']}",
        json={"estado": "confirmado"},
    )

    assert respuesta.status_code == 401


# ===========================================================================
# LA COLA DE CONCILIACION
# ===========================================================================


def _cola(cliente, edificio, headers, **filtros):
    consulta = "&".join(f"{k}={v}" for k, v in filtros.items())
    ruta = f"/api/edificios/{edificio.id}/pagos"
    if consulta:
        ruta += f"?{consulta}"
    return cliente.get(ruta, headers=headers)


def test_la_cola_trae_los_pagos_con_su_total(cliente, como, db):
    """"Hay 2 pagos esperando por $60.000" es la frase que hace que alguien se
    siente a conciliar. Sumarlo en el navegador daria el total de la pagina, no
    el del filtro."""
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)
    cliente.post(
        "/api/mis-pagos",
        json={
            "expensa_id": pago["expensa_id"],
            "monto": "10000.00",
            "fecha": "2026-12-06",
            "medio_pago": "efectivo",
        },
        headers=_login(cliente, propietario),
    )

    cuerpo = _cola(cliente, edificio, admin).json()

    assert cuerpo["cantidad"] == 2
    assert cuerpo["total"] == "60000.00"


def test_la_cola_sale_del_mas_viejo_al_mas_nuevo(cliente, como, db):
    """**Al reves que todos los demas listados del proyecto, y a proposito:**
    esto es una cola de trabajo. El pago que lleva cinco dias esperando es el
    que hay que mirar."""
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)
    residente = _login(cliente, propietario)
    cliente.post(
        "/api/mis-pagos",
        json={
            "expensa_id": pago["expensa_id"],
            "monto": "1.00",
            "fecha": "2026-12-01",
            "medio_pago": "efectivo",
        },
        headers=residente,
    )

    fechas = [p["fecha"] for p in _cola(cliente, edificio, admin).json()["pagos"]]

    assert fechas == ["2026-12-01", "2026-12-05"]


def test_la_cola_se_filtra_por_estado(cliente, como, db):
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)
    _conciliar(cliente, edificio, pago["id"], admin)

    pendientes = _cola(cliente, edificio, admin, estado="pendiente").json()
    confirmados = _cola(cliente, edificio, admin, estado="confirmado").json()

    assert pendientes["cantidad"] == 0
    assert confirmados["cantidad"] == 1


def test_la_cola_se_filtra_por_unidad(cliente, como, db):
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    cuerpo = _cola(cliente, edificio, admin, departamento_id=unidad.id).json()
    otra = _cola(cliente, edificio, admin, departamento_id=99999).json()

    assert cuerpo["cantidad"] == 1
    assert otra["cantidad"] == 0


def test_un_estado_inventado_en_el_filtro_se_rechaza(cliente, como, db):
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    respuesta = _cola(cliente, edificio, admin, estado="acreditado")

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "ESTADO_DE_PAGO_INVALIDO"


def test_la_cola_dice_de_que_unidad_y_periodo_es_cada_pago(cliente, como, db):
    """Conciliar sin saber de quien es el pago es imposible: el extracto
    bancario dice un nombre y un monto."""
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    fila = _cola(cliente, edificio, admin).json()["pagos"][0]

    assert fila["identificador"] == "1A"
    assert fila["periodo"] == "11/2026"
    assert fila["cargado_por"] == propietario.nombre
    assert fila["medio_pago_etiqueta"] == "Transferencia bancaria"


def test_la_cola_dice_si_puedo_conciliar_cada_pago(cliente, como, db):
    """Lo calcula el servidor: la pantalla no tiene por que saber la regla de
    que quien carga no concilia, y si la supiera tendria una copia que algun
    dia no coincide."""
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    ajeno = _cola(cliente, edificio, admin).json()["pagos"][0]
    assert ajeno["puedo_conciliarlo"] is True

    _conciliar(cliente, edificio, pago["id"], admin)
    ya_conciliado = _cola(cliente, edificio, admin).json()["pagos"][0]
    assert ya_conciliado["puedo_conciliarlo"] is False


def test_la_cola_de_un_edificio_sin_pagos_esta_vacia(cliente, como, db):
    edificio = _edificio_listo(db)

    respuesta = _cola(cliente, edificio, como("admin_general"))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"cantidad": 0, "total": "0.00", "pagos": []}


def test_la_cola_no_trae_pagos_de_otro_edificio(cliente, como, db):
    uno = _escenario(cliente, como, db, nombre="Mitre 500")
    _escenario(cliente, como, db, nombre="Otro 900")

    cuerpo = _cola(cliente, uno[0], uno[4]).json()

    assert cuerpo["cantidad"] == 1


def test_un_residente_no_ve_la_cola(cliente, como, db):
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    respuesta = _cola(cliente, edificio, _login(cliente, propietario))

    assert respuesta.status_code == 403


def test_sin_sesion_no_se_ve_la_cola(cliente, como, db):
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    assert cliente.get(f"/api/edificios/{edificio.id}/pagos").status_code == 401


# ===========================================================================
# EL MOTIVO DEL RECHAZO
# ===========================================================================


def test_rechazar_sin_motivo_no_se_puede(cliente, como, db):
    """**La regla.** Un pago rechazado sin explicacion le dice al residente que
    hable con la administracion y nada mas, y eso es justo el llamado
    telefonico que el sistema existe para evitar."""
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    respuesta = cliente.patch(
        f"/api/edificios/{edificio.id}/pagos/{pago['id']}",
        json={"estado": "rechazado"},
        headers=admin,
    )

    assert respuesta.status_code == 422
    assert "motivo" in respuesta.text


def test_un_motivo_de_dos_letras_no_es_un_motivo(cliente, como, db):
    """Con menos de cinco caracteres no se escribio un motivo: se escribio
    cualquier cosa para pasar la validacion."""
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    respuesta = _conciliar(cliente, edificio, pago["id"], admin, "rechazado", motivo="no")

    assert respuesta.status_code == 422


def test_un_motivo_de_solo_espacios_tampoco(cliente, como, db):
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    respuesta = _conciliar(
        cliente, edificio, pago["id"], admin, "rechazado", motivo="        "
    )

    assert respuesta.status_code == 422


def test_confirmar_no_admite_motivo(cliente, como, db):
    """Un motivo en un pago confirmado no significa nada: quedaria guardado un
    texto que ninguna pantalla muestra, que es como empiezan los datos que
    nadie sabe de donde salieron."""
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    respuesta = _conciliar(
        cliente, edificio, pago["id"], admin, "confirmado", motivo=MOTIVO
    )

    assert respuesta.status_code == 422


def test_el_motivo_queda_guardado_y_lo_ve_la_administracion(cliente, como, db):
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    _conciliar(cliente, edificio, pago["id"], admin, "rechazado")

    fila = _cola(cliente, edificio, admin).json()["pagos"][0]
    assert fila["motivo_rechazo"] == MOTIVO


def test_el_residente_lee_el_motivo_dentro_del_mensaje(cliente, como, db):
    """Un rechazo que dice "hablalo con la administracion" obliga a llamar por
    telefono; uno que dice "el monto no coincide con el comprobante" se
    resuelve solo."""
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)
    _conciliar(cliente, edificio, pago["id"], admin, "rechazado")

    # Se lee por la cola de gestion, que es la que devuelve el pago completo;
    # la pantalla del residente consume el mismo armador de mensaje.
    from app.models.finanzas import Pago as ModeloPago
    from app.routers.pagos import _mensaje_del_pago

    guardado = db.scalars(select(ModeloPago)).first()
    mensaje = _mensaje_del_pago(guardado.estado, guardado.motivo_rechazo)

    assert MOTIVO in mensaje
    assert "Corregilo" in mensaje


def test_un_pago_confirmado_no_guarda_motivo(cliente, como, db):
    edificio, unidad, propietario, pago, admin = _escenario(cliente, como, db)

    _conciliar(cliente, edificio, pago["id"], admin)

    fila = _cola(cliente, edificio, admin).json()["pagos"][0]
    assert fila["motivo_rechazo"] is None

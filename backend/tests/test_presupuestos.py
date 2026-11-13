"""Pruebas de `Presupuesto` y `Factura` (`F2-T14`).

Lo que se prueba es la cadena de trazabilidad y lo que la protege:

  1. **El estado registra la decision.** Tres presupuestos del mismo arreglo
     con uno aprobado: eso es lo que no se puede reconstruir sin estado.
  2. **Un presupuesto rechazado no puede estar ligado a un gasto.** Diria "no
     elegimos esto" y "esto es lo que gastamos" a la vez, y lo ataja la base.
  3. **Una factura siempre cuelga de un gasto**, y la misma factura no se puede
     cargar dos veces contra el mismo gasto.
  4. **No se exige ninguna cantidad de presupuestos**: cero, uno o diez.

Las decisiones de diseno vienen de `investigaciones/Presupuestos_y_Facturas.md`.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from app.core import security
from app.models.edificio import Edificio
from app.models.finanzas import Factura, Gasto, Presupuesto
from app.models.usuario import Usuario
from app.services import autorizacion, presupuestos


def _edificio(db) -> Edificio:
    edificio = Edificio(nombre="Consorcio Mitre 500", direccion="Mitre 500", cp="C1000")
    db.add(edificio)
    db.commit()
    return edificio


def _admin(db) -> Usuario:
    usuario = Usuario(
        nombre="Admin Ana",
        email="admin.presupuestos@prueba.com.ar",
        password_hash=security.hashear_password("Prueba123!"),
        rol=autorizacion.ADMIN_CONSORCIO,
        activo=True,
    )
    db.add(usuario)
    db.commit()
    return usuario


def _gasto(db, edificio, monto="180000.00") -> Gasto:
    gasto = Gasto(
        edificio_id=edificio.id,
        rubro="mantenimiento",
        monto=Decimal(monto),
        fecha=date(2026, 11, 20),
    )
    db.add(gasto)
    db.commit()
    return gasto


def _presupuesto(db, edificio, **extra) -> Presupuesto:
    datos = {
        "edificio_id": edificio.id,
        "descripcion": "Arreglo de la bomba de agua",
        "monto": Decimal("180000.00"),
        "fecha": date(2026, 11, 10),
    }
    datos.update(extra)
    presupuesto = Presupuesto(**datos)
    db.add(presupuesto)
    db.commit()
    return presupuesto


def _factura(db, gasto, **extra) -> Factura:
    datos = {
        "gasto_id": gasto.id,
        "numero": "B 0001-00000123",
        "monto": Decimal("180000.00"),
        "fecha": date(2026, 11, 25),
    }
    datos.update(extra)
    factura = Factura(**datos)
    db.add(factura)
    db.commit()
    return factura


# ===========================================================================
# LOS ESTADOS
# ===========================================================================


def test_son_tres_estados():
    assert presupuestos.ESTADOS == ("pendiente", "aprobado", "rechazado")


def test_un_presupuesto_pendiente_se_aprueba_o_se_rechaza():
    assert presupuestos.transicion_valida("pendiente", "aprobado")
    assert presupuestos.transicion_valida("pendiente", "rechazado")


def test_una_decision_tomada_no_se_reescribe():
    """Si se aprobó el presupuesto equivocado, lo que corresponde es rechazar
    el gasto que se generó y cargar la decision nueva, no reescribir cual se
    habia elegido — esa es la informacion que un consorcista puede pedir ver.
    """
    assert not presupuestos.transicion_valida("aprobado", "rechazado")
    assert not presupuestos.transicion_valida("rechazado", "aprobado")
    assert not presupuestos.transicion_valida("aprobado", "pendiente")


@pytest.mark.parametrize("estado", presupuestos.ESTADOS)
def test_pasar_al_mismo_estado_no_vale(estado):
    """Aprobar dos veces no es inofensivo si en el medio se vinculo un gasto."""
    assert not presupuestos.transicion_valida(estado, estado)


def test_un_estado_desconocido_no_habilita_nada():
    assert not presupuestos.transicion_valida("en_revision", "aprobado")
    assert presupuestos.estados_siguientes("en_revision") == ()
    assert not presupuestos.es_estado_valido("en_revision")


def test_los_dos_estados_finales_estan_decididos():
    assert presupuestos.esta_decidido("aprobado")
    assert presupuestos.esta_decidido("rechazado")
    assert not presupuestos.esta_decidido("pendiente")


def test_solo_el_aprobado_se_vincula_a_un_gasto():
    """Un presupuesto rechazado vinculado a un gasto es una contradiccion, y
    uno pendiente todavia no decidio nada."""
    assert presupuestos.puede_vincularse_a_un_gasto("aprobado")
    assert not presupuestos.puede_vincularse_a_un_gasto("rechazado")
    assert not presupuestos.puede_vincularse_a_un_gasto("pendiente")


# ===========================================================================
# EL MODELO DE PRESUPUESTO
# ===========================================================================


def test_un_presupuesto_nace_pendiente_y_sin_gasto(db):
    edificio = _edificio(db)

    presupuesto = _presupuesto(db, edificio)

    assert presupuesto.estado == "pendiente"
    assert presupuesto.gasto_id is None
    assert presupuesto.decidido_por_id is None
    assert not presupuesto.esta_decidido


def test_se_pueden_cargar_varios_presupuestos_del_mismo_arreglo(db):
    """**No se exige ninguna cantidad.** Ninguna norma argentina pide un minimo
    antes de aprobar un gasto: es buena practica, y lo fija el reglamento de
    cada consorcio. El modelo no objeta nada."""
    edificio = _edificio(db)

    for monto in ("180000.00", "210000.00", "165000.00"):
        _presupuesto(db, edificio, monto=Decimal(monto))

    assert len(db.scalars(select(Presupuesto)).all()) == 3


def test_el_estado_es_lo_que_registra_cual_se_eligio(db):
    """**Para esto existe el estado.** Sin el, tres presupuestos del mismo
    arreglo son tres filas indistinguibles y la decision no queda escrita en
    ningun lado."""
    edificio = _edificio(db)
    quien = _admin(db)
    elegido = _presupuesto(db, edificio, monto=Decimal("165000.00"))
    descartado = _presupuesto(db, edificio, monto=Decimal("210000.00"))

    elegido.estado = "aprobado"
    elegido.decidido_por_id = quien.id
    elegido.decidido_en = datetime(2026, 11, 15, 10, 0)
    descartado.estado = "rechazado"
    descartado.decidido_por_id = quien.id
    db.commit()

    aprobados = db.scalars(
        select(Presupuesto).where(Presupuesto.estado == "aprobado")
    ).all()
    assert len(aprobados) == 1
    assert aprobados[0].monto == Decimal("165000.00")
    assert aprobados[0].decidido_por.nombre == "Admin Ana"


def test_un_presupuesto_aprobado_se_liga_al_gasto_que_genero(db):
    """Es lo que cierra la comparacion entre lo que se presupuesto y lo que
    finalmente se pago."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio, monto="172000.00")
    presupuesto = _presupuesto(db, edificio, monto=Decimal("165000.00"))

    presupuesto.estado = "aprobado"
    presupuesto.gasto_id = gasto.id
    db.commit()

    assert presupuesto.gasto.monto == Decimal("172000.00")
    # Lo presupuestado y lo pagado no coinciden, y eso es justo lo que se
    # quiere poder ver.
    assert presupuesto.gasto.monto != presupuesto.monto


def test_un_presupuesto_rechazado_no_puede_tener_gasto(db):
    """**Lo ataja la base**, porque es una contradiccion de datos y no una
    regla de flujo: diria "no elegimos esto" y "esto es lo que gastamos" a la
    vez."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)

    db.add(
        Presupuesto(
            edificio_id=edificio.id,
            descripcion="Arreglo de la bomba",
            monto=Decimal("180000.00"),
            fecha=date(2026, 11, 10),
            estado="rechazado",
            gasto_id=gasto.id,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_un_presupuesto_pendiente_sin_gasto_es_valido(db):
    """El CHECK solo prohibe el rechazado con gasto: el pendiente sin gasto es
    el estado normal de todo presupuesto recien cargado."""
    edificio = _edificio(db)

    presupuesto = _presupuesto(db, edificio)

    assert presupuesto.id is not None


@pytest.mark.parametrize("monto", ["0.00", "-1000.00"])
def test_un_monto_que_no_es_positivo_lo_rechaza_la_base(db, monto):
    edificio = _edificio(db)

    with pytest.raises(IntegrityError):
        _presupuesto(db, edificio, monto=Decimal(monto))


def test_un_estado_fuera_del_catalogo_lo_rechaza_la_base(db):
    edificio = _edificio(db)

    with pytest.raises(IntegrityError):
        _presupuesto(db, edificio, estado="en_revision")


def test_la_descripcion_es_obligatoria(db):
    """Al contrario que en un gasto: un gasto se entiende por su rubro y su
    monto, pero **comparar tres numeros sin saber de que son no es comparar
    nada**."""
    columnas = {c["name"]: c for c in inspect(db.bind).get_columns("presupuestos")}

    assert columnas["descripcion"]["nullable"] is False


def test_el_proveedor_sigue_siendo_un_entero_suelto(db):
    """La tabla `proveedores` no existe hasta la Fase 7. Mismo criterio que en
    `Gasto`: la columna se puede empezar a usar, lo que falta es la
    restriccion."""
    edificio = _edificio(db)
    presupuesto = _presupuesto(db, edificio, proveedor_id=77)

    claves = inspect(db.bind).get_foreign_keys("presupuestos")
    columnas_con_fk = {c for k in claves for c in k["constrained_columns"]}

    assert presupuesto.proveedor_id == 77
    assert "proveedor_id" not in columnas_con_fk
    assert "gasto_id" in columnas_con_fk


# ===========================================================================
# EL MODELO DE FACTURA
# ===========================================================================


def test_una_factura_cuelga_de_un_gasto(db):
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)

    factura = _factura(db, gasto)

    assert factura.gasto_id == gasto.id
    assert factura.gasto.rubro == "mantenimiento"


def test_una_factura_sin_gasto_no_existe(db):
    """**No es opcional.** Una factura suelta no sirve para nada: lo que se
    audita es el gasto, y la factura es lo que lo respalda."""
    columnas = {c["name"]: c for c in inspect(db.bind).get_columns("facturas")}

    assert columnas["gasto_id"]["nullable"] is False


def test_la_factura_no_tiene_edificio_propio(db):
    """El edificio sale del gasto. Repetirlo seria poder guardar una factura de
    un edificio contra un gasto de otro."""
    columnas = {c["name"] for c in inspect(db.bind).get_columns("facturas")}

    assert "edificio_id" not in columnas


def test_la_misma_factura_no_se_carga_dos_veces_en_el_mismo_gasto(db):
    """Es el error de doble carga mas facil de cometer — dos personas
    archivando el mismo papel— y duplicaria el respaldo de un gasto que es uno
    solo."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)
    _factura(db, gasto, numero="B 0001-00000123")

    db.add(
        Factura(
            gasto_id=gasto.id,
            numero="B 0001-00000123",
            monto=Decimal("180000.00"),
            fecha=date(2026, 11, 25),
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_un_gasto_puede_tener_dos_facturas_distintas(db):
    """Pasa de verdad: un arreglo que se factura en dos partes."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)

    _factura(db, gasto, numero="B 0001-00000123", monto=Decimal("100000.00"))
    segunda = _factura(db, gasto, numero="B 0001-00000124", monto=Decimal("80000.00"))

    assert segunda.id is not None


def test_el_numero_de_factura_es_texto_libre(db):
    """**Decision tomada:** no se separan tipo, CUIT, punto de venta ni CAE,
    porque este sistema no tiene integracion con AFIP ni la tiene planeada en
    ninguna fase. Se guarda el comprobante completo, que es lo que alguien
    busca cuando quiere encontrar una factura."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)

    factura = _factura(db, gasto, numero="A 0003-00004521")

    assert factura.numero == "A 0003-00004521"
    columnas = {c["name"] for c in inspect(db.bind).get_columns("facturas")}
    assert "cae" not in columnas
    assert "punto_de_venta" not in columnas
    assert "tipo" not in columnas


def test_el_archivo_es_opcional(db):
    """Mientras no haya almacenamiento propio (Fase 7), es un enlace. Y una
    factura en papel archivada en una carpeta no tiene enlace."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)

    factura = _factura(db, gasto, archivo_url=None)

    assert factura.archivo_url is None


@pytest.mark.parametrize("monto", ["0.00", "-1000.00"])
def test_una_factura_que_no_es_positiva_la_rechaza_la_base(db, monto):
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)

    with pytest.raises(IntegrityError):
        _factura(db, gasto, monto=Decimal(monto))


def test_el_monto_de_la_factura_puede_diferir_del_gasto(db):
    """No se valida que coincidan, y es deliberado: una factura puede llegar
    con un ajuste, o un gasto puede cubrirse con dos facturas. Forzar la
    igualdad bloquearia los dos casos reales."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio, monto="180000.00")

    factura = _factura(db, gasto, monto=Decimal("181500.00"))

    assert factura.monto != gasto.monto


# ===========================================================================
# LA CADENA COMPLETA
# ===========================================================================


def test_la_cadena_presupuesto_gasto_factura_queda_recorrible(db):
    """**La trazabilidad que pide el Documento General**, verificada de punta a
    punta: desde la factura se llega al gasto, y desde el presupuesto aprobado
    tambien — asi que se puede contestar "que nos cotizaron, que gastamos y
    que nos facturaron" con tres consultas y ninguna ambiguedad.
    """
    edificio = _edificio(db)
    quien = _admin(db)

    cotizado = _presupuesto(db, edificio, monto=Decimal("165000.00"))
    gasto = _gasto(db, edificio, monto="172000.00")
    cotizado.estado = "aprobado"
    cotizado.gasto_id = gasto.id
    cotizado.decidido_por_id = quien.id
    db.commit()
    factura = _factura(db, gasto, monto=Decimal("172000.00"))

    assert cotizado.gasto_id == gasto.id == factura.gasto_id
    assert cotizado.monto == Decimal("165000.00")
    assert factura.monto == Decimal("172000.00")


# ===========================================================================
# LA FACTURA ES OPCIONAL, Y NO TIENE QUE SER UNA FACTURA (2026-11-13)
# ===========================================================================


def test_un_gasto_sin_facturas_es_valido(db):
    """**Lo que el usuario pidio confirmar, y ya era asi.** Muchos gastos
    reales no tienen comprobante formal: el arreglo que hizo un vecino, el
    flete que se pago en efectivo. Nada exige una factura para registrar un
    gasto."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)

    assert db.scalars(select(Factura).where(Factura.gasto_id == gasto.id)).all() == []


def test_un_recibo_sin_numero_se_puede_cargar(db):
    """Un recibo escrito a mano no tiene numero. Exigirlo haria que alguien
    escriba "sin numero" o "1" para poder guardar el dato que si tiene."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)

    factura = _factura(db, gasto, numero=None)

    assert factura.id is not None
    assert factura.numero is None


def test_dos_recibos_sin_numero_contra_el_mismo_gasto_conviven(db):
    """Son dos comprobantes distintos. El UNIQUE ataja repetir **un numero**,
    que es lo que identifica un papel concreto; con numero nulo no aplica."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)

    _factura(db, gasto, numero=None, monto=Decimal("50000.00"))
    segundo = _factura(db, gasto, numero=None, monto=Decimal("30000.00"))

    assert segundo.id is not None


def test_el_comprobante_no_tiene_que_ser_una_factura_fiscal(db):
    """Un recibo, un remito, un ticket. El campo es texto libre justamente
    para esto."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)

    recibo = _factura(db, gasto, numero="Recibo 45 del plomero")

    assert recibo.numero == "Recibo 45 del plomero"

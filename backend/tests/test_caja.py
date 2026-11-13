"""Pruebas de la caja chica como sistema de fondo fijo (`F2-T13`).

Lo que se prueba es la diferencia con un fondo, que es toda la tarea:

  1. **El disponible se mide contra el monto fijo**, no contra cero. Lo que
     falta para llegar a ese monto es **lo que el responsable gasto y todavia
     no le devolvieron**, que es la cifra de la rendicion.
  2. **Una reposicion es un movimiento de tipo ingreso**, no una operacion
     especial.
  3. **El aviso de "hay que reponer"** aparece por debajo del umbral.
  4. Y los dos casos que se informan sin impedirse: la caja **en rojo** y la
     caja que **excede su fondo fijo**.

El fundamento del modelo esta en `investigaciones/Caja_chica.md`, que registra
ademas el error del primer diseno: una caja sin movimientos.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from app.core import security
from app.models.edificio import Edificio
from app.models.finanzas import Caja, MovimientoCaja
from app.models.usuario import Usuario
from app.services import autorizacion, caja as servicio_caja, fondos


def _mov(tipo, monto) -> fondos.Movimiento:
    return fondos.Movimiento(tipo=tipo, monto=Decimal(monto))


def _edificio(db) -> Edificio:
    edificio = Edificio(nombre="Consorcio Mitre 500", direccion="Mitre 500", cp="C1000")
    db.add(edificio)
    db.commit()
    return edificio


def _usuario(db, nombre="Encargado Juan", rol=None) -> Usuario:
    usuario = Usuario(
        nombre=nombre,
        email=f"{nombre.lower().replace(' ', '')}@prueba.com.ar",
        password_hash=security.hashear_password("Prueba123!"),
        rol=rol or autorizacion.ENCARGADO,
        activo=True,
    )
    db.add(usuario)
    db.commit()
    return usuario


def _caja(db, edificio, responsable, monto_fijo="50000.00") -> Caja:
    caja = Caja(
        edificio_id=edificio.id,
        monto_fijo=Decimal(monto_fijo),
        responsable_id=responsable.id,
    )
    db.add(caja)
    db.commit()
    return caja


def _movimiento(db, caja, quien, tipo="egreso", monto="5000.00", **extra):
    movimiento = MovimientoCaja(
        caja_id=caja.id,
        tipo=tipo,
        monto=Decimal(monto),
        fecha=extra.pop("fecha", date(2026, 11, 5)),
        registrado_por_id=quien.id,
        **extra,
    )
    db.add(movimiento)
    db.commit()
    return movimiento


# ===========================================================================
# LOS TIPOS SON LOS MISMOS QUE LOS DE UN FONDO
# ===========================================================================


def test_los_tipos_son_el_mismo_catalogo_que_el_de_los_fondos():
    """Es el mismo concepto —entra plata o sale plata— y dos tuplas paralelas
    con los mismos valores son el camino corto a que un reporte sume lo que
    otro resta."""
    assert servicio_caja.TIPOS_DE_MOVIMIENTO is fondos.TIPOS_DE_MOVIMIENTO


# ===========================================================================
# EL ESTADO DE LA CAJA
# ===========================================================================


def test_una_caja_recien_abierta_esta_vacia_y_hay_que_reponerla_entera():
    """**El caso que muestra de que se trata el fondo fijo.** Una caja sin
    movimientos no tiene saldo cero "y listo": tiene 50.000 pendientes de
    reposicion, porque todavia no se le entrego el efectivo."""
    estado = servicio_caja.calcular_estado(Decimal("50000.00"), [])

    assert estado.disponible == Decimal("0.00")
    assert estado.pendiente_de_reposicion == Decimal("50000.00")
    assert estado.necesita_reposicion


def test_con_la_caja_completa_no_hay_nada_que_reponer():
    estado = servicio_caja.calcular_estado(
        Decimal("50000.00"), [_mov("ingreso", "50000.00")]
    )

    assert estado.disponible == Decimal("50000.00")
    assert estado.pendiente_de_reposicion == Decimal("0.00")
    assert not estado.necesita_reposicion


def test_lo_pendiente_de_reposicion_es_lo_que_el_responsable_gasto():
    """**La cifra de la rendicion.** El encargado puso 12.000 de su efectivo en
    gastos del edificio: eso es lo que hay que devolverle para que la caja
    vuelva a estar completa."""
    estado = servicio_caja.calcular_estado(
        Decimal("50000.00"),
        [
            _mov("ingreso", "50000.00"),
            _mov("egreso", "8000.00"),
            _mov("egreso", "4000.00"),
        ],
    )

    assert estado.disponible == Decimal("38000.00")
    assert estado.pendiente_de_reposicion == Decimal("12000.00")


def test_una_reposicion_es_un_movimiento_de_ingreso():
    """No hay operacion especial ni campo de "ultima reposicion": la reposicion
    **es** el movimiento que trae el disponible de vuelta al monto fijo."""
    antes = servicio_caja.calcular_estado(
        Decimal("50000.00"),
        [_mov("ingreso", "50000.00"), _mov("egreso", "40000.00")],
    )
    pendiente = antes.pendiente_de_reposicion

    despues = servicio_caja.calcular_estado(
        Decimal("50000.00"),
        [
            _mov("ingreso", "50000.00"),
            _mov("egreso", "40000.00"),
            _mov("ingreso", str(pendiente)),
        ],
    )

    assert pendiente == Decimal("40000.00")
    assert despues.disponible == Decimal("50000.00")
    assert despues.pendiente_de_reposicion == Decimal("0.00")


def test_la_reposicion_sugerida_es_lo_que_falta():
    """La pantalla lo pone como valor por defecto del formulario: quien repone
    casi nunca quiere otro numero, y tipearlo a mano es la forma de
    equivocarse."""
    estado = servicio_caja.calcular_estado(
        Decimal("50000.00"), [_mov("ingreso", "50000.00"), _mov("egreso", "7500.50")]
    )

    assert servicio_caja.reposicion_sugerida(estado) == Decimal("7500.50")


# ===========================================================================
# EL AVISO DE REPONER
# ===========================================================================


def test_por_encima_del_umbral_no_avisa():
    """Con 20.000 de 50.000 queda el 40%: todavia alcanza para operar."""
    estado = servicio_caja.calcular_estado(
        Decimal("50000.00"), [_mov("ingreso", "50000.00"), _mov("egreso", "30000.00")]
    )

    assert estado.disponible == Decimal("20000.00")
    assert not estado.necesita_reposicion


def test_por_debajo_del_umbral_avisa():
    """Con 10.000 de 50.000 queda el 20%: conviene juntar los comprobantes y
    rendir antes de quedarse sin efectivo."""
    estado = servicio_caja.calcular_estado(
        Decimal("50000.00"), [_mov("ingreso", "50000.00"), _mov("egreso", "40000.00")]
    )

    assert estado.necesita_reposicion


def test_el_umbral_es_un_valor_elegido_y_no_una_regla_contable():
    """Las fuentes dicen "cuando el efectivo baja a un minimo" sin fijar cual,
    porque depende de cada administracion. Si alguna vez hace falta que sea
    configurable por edificio, este valor pasa a ser el default."""
    assert servicio_caja.UMBRAL_DE_REPOSICION == Decimal("0.30")


# ===========================================================================
# LOS DOS CASOS QUE SE INFORMAN SIN IMPEDIRSE
# ===========================================================================


def test_la_caja_en_rojo_se_informa(cliente=None):
    """Casi siempre significa que falta cargar la reposicion con la que se
    financio el gasto. Bloquear el egreso obligaria a inventarla para registrar
    algo que ya se pago."""
    estado = servicio_caja.calcular_estado(
        Decimal("50000.00"), [_mov("egreso", "3000.00")]
    )

    assert estado.disponible == Decimal("-3000.00")
    assert estado.esta_en_rojo


def test_una_caja_que_excede_su_fondo_fijo_se_informa():
    """Significa que se repuso de mas, o que el fondo fijo cambio en la
    practica y nadie actualizo la columna. **Una caja chica que crece sola deja
    de ser una caja chica.**"""
    estado = servicio_caja.calcular_estado(
        Decimal("50000.00"), [_mov("ingreso", "80000.00")]
    )

    assert estado.excede_el_fondo_fijo
    assert estado.pendiente_de_reposicion == Decimal("0.00")


def test_una_caja_completa_no_excede_nada():
    """El limite exacto no es exceso."""
    estado = servicio_caja.calcular_estado(
        Decimal("50000.00"), [_mov("ingreso", "50000.00")]
    )

    assert not estado.excede_el_fondo_fijo
    assert not estado.esta_en_rojo


def test_un_tipo_invalido_rompe_el_calculo():
    with pytest.raises(ValueError):
        servicio_caja.calcular_estado(Decimal("50000.00"), [_mov("deposito", "1.00")])


def test_el_disponible_es_exacto_con_centavos():
    estado = servicio_caja.calcular_estado(
        Decimal("100.00"), [_mov("ingreso", "100.00"), _mov("egreso", "33.33")]
    )

    assert estado.disponible == Decimal("66.67")
    assert estado.pendiente_de_reposicion == Decimal("33.33")


# ===========================================================================
# EL MODELO
# ===========================================================================


def test_una_caja_se_guarda_con_su_monto_fijo_y_su_responsable(db):
    edificio = _edificio(db)
    responsable = _usuario(db)

    caja = _caja(db, edificio, responsable)

    assert caja.monto_fijo == Decimal("50000.00")
    assert caja.responsable.nombre == "Encargado Juan"
    assert caja.activo is True


def test_un_monto_fijo_que_no_es_positivo_lo_rechaza_la_base(db):
    """Una caja con monto fijo cero no es una caja: no hay nada que reponer ni
    contra que medir el disponible."""
    edificio = _edificio(db)
    responsable = _usuario(db)

    with pytest.raises(IntegrityError):
        _caja(db, edificio, responsable, monto_fijo="0.00")


def test_un_edificio_tiene_una_sola_caja(db):
    """Dos cajas en el mismo edificio no son dos cajas chicas: son un fondo mal
    modelado."""
    edificio = _edificio(db)
    responsable = _usuario(db)
    _caja(db, edificio, responsable)

    db.add(
        Caja(
            edificio_id=edificio.id,
            monto_fijo=Decimal("10000.00"),
            responsable_id=responsable.id,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_dos_edificios_tienen_su_propia_caja(db):
    uno = _edificio(db)
    otro = Edificio(nombre="Otro", direccion="Otra 100", cp="C1001")
    db.add(otro)
    db.commit()
    responsable = _usuario(db)

    _caja(db, uno, responsable)
    segunda = _caja(db, otro, responsable)

    assert segunda.id is not None


def test_no_hay_columna_de_disponible_ni_de_saldo(db):
    """Todo se deriva del monto fijo y los movimientos. Un disponible guardado
    hay que actualizarlo en cada gasto."""
    columnas = {c["name"] for c in inspect(db.bind).get_columns("cajas")}

    assert "disponible" not in columnas
    assert "saldo" not in columnas
    assert "monto_fijo" in columnas


@pytest.mark.parametrize("monto", ["0.00", "-500.00"])
def test_un_movimiento_que_no_es_positivo_lo_rechaza_la_base(db, monto):
    edificio = _edificio(db)
    responsable = _usuario(db)
    caja = _caja(db, edificio, responsable)

    with pytest.raises(IntegrityError):
        _movimiento(db, caja, responsable, monto=monto)


def test_un_tipo_fuera_del_catalogo_lo_rechaza_la_base(db):
    edificio = _edificio(db)
    responsable = _usuario(db)
    caja = _caja(db, edificio, responsable)

    with pytest.raises(IntegrityError):
        _movimiento(db, caja, responsable, tipo="reposicion")


def test_el_movimiento_sabe_quien_lo_registro(db):
    """Puede no ser el responsable: el administrador carga la reposicion que le
    entrego al encargado."""
    edificio = _edificio(db)
    responsable = _usuario(db, "Encargado Juan")
    administrador = _usuario(db, "Admin Ana", rol=autorizacion.ADMIN_CONSORCIO)
    caja = _caja(db, edificio, responsable)

    movimiento = _movimiento(db, caja, administrador, tipo="ingreso")

    assert movimiento.registrado_por_id == administrador.id
    assert caja.responsable_id == responsable.id


def test_los_movimientos_se_borran_con_su_caja(db):
    edificio = _edificio(db)
    responsable = _usuario(db)
    caja = _caja(db, edificio, responsable)
    _movimiento(db, caja, responsable)

    db.delete(caja)
    db.commit()

    assert db.scalars(select(MovimientoCaja)).all() == []


def test_hay_indice_por_caja_y_fecha(db):
    indices = {
        i["name"]: i["column_names"]
        for i in inspect(db.bind).get_indexes("movimientos_caja")
    }

    assert "ix_mov_caja_fecha" in indices
    assert indices["ix_mov_caja_fecha"] == ["caja_id", "fecha"]


def test_el_estado_de_la_caja_sale_de_sus_movimientos_guardados(db):
    """De punta a punta: se abre la caja con 50.000, se gastan 12.000 en dos
    movimientos, y el estado dice que hay 38.000 y que faltan 12.000."""
    edificio = _edificio(db)
    responsable = _usuario(db)
    caja = _caja(db, edificio, responsable, monto_fijo="50000.00")
    _movimiento(db, caja, responsable, tipo="ingreso", monto="50000.00")
    _movimiento(db, caja, responsable, tipo="egreso", monto="8000.00")
    _movimiento(db, caja, responsable, tipo="egreso", monto="4000.00")

    db.expire_all()
    guardada = db.get(Caja, caja.id)
    estado = servicio_caja.calcular_estado(
        guardada.monto_fijo,
        (fondos.Movimiento(tipo=m.tipo, monto=m.monto) for m in guardada.movimientos),
    )

    assert estado.disponible == Decimal("38000.00")
    assert estado.pendiente_de_reposicion == Decimal("12000.00")
    assert estado.cantidad_movimientos == 3

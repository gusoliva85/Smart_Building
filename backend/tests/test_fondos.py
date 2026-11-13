"""Pruebas de `Fondo`, `MovimientoFondo` y el calculo del saldo (`F2-T12`).

Dos reglas, y las dos son de plata:

  1. **El signo lo da el tipo, nunca el numero.** El monto se guarda siempre
     positivo; `ingreso` suma y `egreso` resta. Es lo que hace imposible el
     error clasico de cargar un egreso en positivo.
  2. **El saldo se calcula, no se guarda.** No hay columna `saldo`, y un test
     lo verifica leyendo la tabla: un saldo guardado se desincroniza el dia que
     alguien inserta un movimiento sin pasar por el endpoint.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from app.core import security
from app.models.edificio import Edificio
from app.models.finanzas import Fondo, MovimientoFondo
from app.models.usuario import Usuario
from app.services import autorizacion, fondos


def _edificio(db) -> Edificio:
    edificio = Edificio(nombre="Consorcio Mitre 500", direccion="Mitre 500", cp="C1000")
    db.add(edificio)
    db.commit()
    return edificio


def _admin(db) -> Usuario:
    usuario = Usuario(
        nombre="Administrador",
        email="admin.fondos@prueba.com.ar",
        password_hash=security.hashear_password("Prueba123!"),
        rol=autorizacion.ADMIN_GENERAL,
        activo=True,
    )
    db.add(usuario)
    db.commit()
    return usuario


def _fondo(db, edificio, nombre="Fondo de reserva") -> Fondo:
    fondo = Fondo(edificio_id=edificio.id, nombre=nombre)
    db.add(fondo)
    db.commit()
    return fondo


def _movimiento(db, fondo, quien, tipo="ingreso", monto="100000.00", **extra):
    movimiento = MovimientoFondo(
        fondo_id=fondo.id,
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
# EL CATALOGO DE TIPOS
# ===========================================================================


def test_son_dos_tipos():
    assert fondos.TIPOS_DE_MOVIMIENTO == ("ingreso", "egreso")


def test_un_tipo_inventado_no_es_valido():
    assert not fondos.es_tipo_valido("transferencia")


def test_cada_tipo_tiene_etiqueta():
    assert fondos.etiqueta("ingreso") == "Ingreso"
    assert fondos.etiqueta("egreso") == "Egreso"


def test_la_etiqueta_de_un_tipo_invalido_revienta():
    with pytest.raises(ValueError):
        fondos.etiqueta("deposito")


# ===========================================================================
# EL SIGNO
# ===========================================================================


def test_un_ingreso_suma_y_un_egreso_resta():
    """**La unica traduccion de tipo a signo del sistema.** Repetir
    `if tipo == "ingreso"` en cada consulta es como se termina con un reporte
    que resta lo que otro suma."""
    assert fondos.con_signo("ingreso", Decimal("100.00")) == Decimal("100.00")
    assert fondos.con_signo("egreso", Decimal("100.00")) == Decimal("-100.00")


def test_un_tipo_desconocido_revienta_en_vez_de_valer_cero():
    """Un movimiento que el sistema no sabe interpretar no puede valer cero en
    un saldo: desapareceria del total sin que nadie lo note."""
    with pytest.raises(ValueError):
        fondos.con_signo("deposito", Decimal("100.00"))


# ===========================================================================
# EL CALCULO DEL SALDO
# ===========================================================================


def _mov(tipo, monto) -> fondos.Movimiento:
    return fondos.Movimiento(tipo=tipo, monto=Decimal(monto))


def test_un_fondo_sin_movimientos_tiene_saldo_cero():
    saldo = fondos.calcular_saldo([])

    assert saldo.saldo == Decimal("0.00")
    assert saldo.cantidad_movimientos == 0
    assert not saldo.esta_en_rojo


def test_el_saldo_es_ingresos_menos_egresos():
    saldo = fondos.calcular_saldo(
        [
            _mov("ingreso", "500000.00"),
            _mov("ingreso", "300000.00"),
            _mov("egreso", "120000.50"),
        ]
    )

    assert saldo.ingresos == Decimal("800000.00")
    assert saldo.egresos == Decimal("120000.50")
    assert saldo.saldo == Decimal("679999.50")
    assert saldo.cantidad_movimientos == 3


def test_los_tres_totales_van_por_separado():
    """"Cuanto junto el consorcio para la obra" no es lo mismo que "cuanto
    queda disponible": un fondo con mucho movimiento y saldo chico es una
    situacion muy distinta de uno que nunca se uso."""
    mucho_movimiento = fondos.calcular_saldo(
        [_mov("ingreso", "1000000.00"), _mov("egreso", "990000.00")]
    )
    sin_usar = fondos.calcular_saldo([_mov("ingreso", "10000.00")])

    assert mucho_movimiento.saldo == sin_usar.saldo == Decimal("10000.00")
    assert mucho_movimiento.ingresos != sin_usar.ingresos


def test_un_saldo_negativo_se_informa_y_no_se_impide():
    """Casi siempre significa que falta cargar el ingreso que lo financio.
    Bloquear el egreso obligaria a inventar el ingreso para poder registrar un
    gasto que ya ocurrio."""
    saldo = fondos.calcular_saldo([_mov("egreso", "50000.00")])

    assert saldo.saldo == Decimal("-50000.00")
    assert saldo.esta_en_rojo


def test_el_saldo_es_exacto_con_centavos():
    """La regla de toda la fase: nunca `float`."""
    saldo = fondos.calcular_saldo(
        [_mov("ingreso", "0.10"), _mov("ingreso", "0.20"), _mov("egreso", "0.05")]
    )

    assert saldo.saldo == Decimal("0.25")


def test_un_movimiento_con_tipo_invalido_rompe_el_calculo():
    """Y no lo ignora: un saldo calculado sobre datos que no se entienden es
    peor que un error."""
    with pytest.raises(ValueError):
        fondos.calcular_saldo([_mov("deposito", "100.00")])


def test_el_total_de_los_fondos_suma_todos_los_saldos():
    """Es el numero del resumen del edificio y del Dashboard General. Se
    calcula una sola vez para que las dos pantallas muestren lo mismo."""
    uno = fondos.calcular_saldo([_mov("ingreso", "100.00")])
    otro = fondos.calcular_saldo([_mov("ingreso", "50.00"), _mov("egreso", "20.00")])

    assert fondos.total_de_los_fondos([uno, otro]) == Decimal("130.00")


def test_el_total_de_cero_fondos_es_cero():
    assert fondos.total_de_los_fondos([]) == Decimal("0.00")


# ===========================================================================
# EL MODELO
# ===========================================================================


def test_un_fondo_nace_activo(db):
    edificio = _edificio(db)

    fondo = _fondo(db, edificio)

    assert fondo.activo is True
    assert fondo.creado_en is not None


def test_no_hay_columna_de_saldo(db):
    """**La decision central del modelo, verificada contra la tabla real.** Un
    saldo guardado hay que actualizarlo en cada movimiento, y el dia que
    alguien inserte uno sin pasar por el endpoint queda mal sin que nada
    falle."""
    columnas = {c["name"] for c in inspect(db.bind).get_columns("fondos")}

    assert "saldo" not in columnas
    assert "total" not in columnas


def test_dos_fondos_no_pueden_llamarse_igual_en_el_mismo_edificio(db):
    """Serian dos bolsas indistinguibles en cualquier reporte."""
    edificio = _edificio(db)
    _fondo(db, edificio, "Fondo de obras")

    db.add(Fondo(edificio_id=edificio.id, nombre="Fondo de obras"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_dos_edificios_pueden_tener_un_fondo_con_el_mismo_nombre(db):
    """Todos los consorcios tienen un fondo de reserva."""
    uno = _edificio(db)
    otro = Edificio(nombre="Otro", direccion="Otra 100", cp="C1001")
    db.add(otro)
    db.commit()

    _fondo(db, uno, "Fondo de reserva")
    segundo = _fondo(db, otro, "Fondo de reserva")

    assert segundo.id is not None


@pytest.mark.parametrize("monto", ["0.00", "-1000.00"])
def test_un_movimiento_que_no_es_positivo_lo_rechaza_la_base(db, monto):
    """**El signo lo da el tipo.** Un monto negativo seria un egreso cargado
    como ingreso, o al reves, y el saldo saldria mal sin que nada falle."""
    edificio = _edificio(db)
    fondo = _fondo(db, edificio)
    quien = _admin(db)

    with pytest.raises(IntegrityError):
        _movimiento(db, fondo, quien, monto=monto)


def test_un_tipo_fuera_del_catalogo_lo_rechaza_la_base(db):
    """El CHECK se arma desde la misma tupla que usa la aplicacion."""
    edificio = _edificio(db)
    fondo = _fondo(db, edificio)
    quien = _admin(db)

    with pytest.raises(IntegrityError):
        _movimiento(db, fondo, quien, tipo="deposito")


def test_el_movimiento_sabe_quien_lo_registro(db):
    """En un circuito de dinero, cada movimiento tiene un responsable."""
    edificio = _edificio(db)
    fondo = _fondo(db, edificio)
    quien = _admin(db)

    movimiento = _movimiento(db, fondo, quien)

    assert movimiento.registrado_por_id == quien.id
    assert movimiento.registrado_por.nombre == "Administrador"


def test_el_movimiento_traduce_su_tipo_a_signo(db):
    edificio = _edificio(db)
    fondo = _fondo(db, edificio)
    quien = _admin(db)

    ingreso = _movimiento(db, fondo, quien, tipo="ingreso", monto="100.00")
    egreso = _movimiento(db, fondo, quien, tipo="egreso", monto="30.00")

    assert ingreso.con_signo == Decimal("100.00")
    assert egreso.con_signo == Decimal("-30.00")


def test_el_monto_es_numerico_con_dos_decimales(db):
    columnas = {
        c["name"]: c for c in inspect(db.bind).get_columns("movimientos_fondo")
    }

    tipo = str(columnas["monto"]["type"]).upper()
    assert "NUMERIC" in tipo or "DECIMAL" in tipo
    assert "12, 2" in tipo or "12,2" in tipo


def test_los_movimientos_se_borran_con_su_fondo(db):
    """Son parte del fondo, no datos sueltos. En la practica un fondo con
    historial se desactiva en vez de borrarse, pero si se borra no puede dejar
    movimientos huerfanos."""
    edificio = _edificio(db)
    fondo = _fondo(db, edificio)
    quien = _admin(db)
    _movimiento(db, fondo, quien)

    db.delete(fondo)
    db.commit()

    assert db.scalars(select(MovimientoFondo)).all() == []


def test_un_fondo_se_desactiva_en_vez_de_borrarse(db):
    """El historial de la plata de un consorcio no se tira."""
    edificio = _edificio(db)
    fondo = _fondo(db, edificio)
    quien = _admin(db)
    _movimiento(db, fondo, quien)

    fondo.activo = False
    db.commit()

    assert fondo.activo is False
    assert len(db.scalars(select(MovimientoFondo)).all()) == 1


def test_hay_indice_por_fondo_y_fecha(db):
    """Es la consulta del detalle: los movimientos de ESTE fondo por fecha."""
    indices = {
        i["name"]: i["column_names"]
        for i in inspect(db.bind).get_indexes("movimientos_fondo")
    }

    assert "ix_mov_fondo_fecha" in indices
    assert indices["ix_mov_fondo_fecha"] == ["fondo_id", "fecha"]


def test_el_saldo_del_fondo_se_calcula_desde_sus_movimientos(db):
    """De punta a punta: se guardan movimientos y el saldo sale de sumarlos,
    sin ninguna columna que mantener."""
    edificio = _edificio(db)
    fondo = _fondo(db, edificio)
    quien = _admin(db)
    _movimiento(db, fondo, quien, tipo="ingreso", monto="500000.00")
    _movimiento(db, fondo, quien, tipo="egreso", monto="120000.50")

    db.expire_all()
    guardado = db.get(Fondo, fondo.id)
    saldo = fondos.calcular_saldo(
        fondos.Movimiento(tipo=m.tipo, monto=m.monto) for m in guardado.movimientos
    )

    assert saldo.saldo == Decimal("379999.50")

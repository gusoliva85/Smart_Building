"""Pruebas de los modelos de la liquidacion y de sus dos estados (`F2-T04`).

Lo que se prueba son las reglas que el modelo tiene que garantizar **aunque el
endpoint se equivoque**, porque son las que sostienen toda la fase:

  1. **Un periodo, una expensa.** Sin eso, "regenerar la ultima" no tiene
     sentido: no se sabe cual de las dos es.
  2. **El flujo de estados es de ida.** `borrador → publicada` y nada mas. Lo
     que se puede regenerar es, exactamente, lo que el residente todavia no
     vio.
  3. **Los tres montos de la unidad y su total calculado**, incluido el caso
     del saldo a favor que cubre todo.
  4. **Que el detalle y el reparto no sobrevivan a su expensa**, porque son
     parte del documento y no datos sueltos.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from app.models.edificio import Departamento, Edificio, Piso
from app.models.finanzas import Expensa, ExpensaDepartamento, ExpensaDetalle
from app.services import expensas


def _edificio(db) -> Edificio:
    edificio = Edificio(nombre="Consorcio Mitre 500", direccion="Mitre 500", cp="C1000")
    db.add(edificio)
    db.commit()
    return edificio


def _departamento(db, edificio, identificador="1A") -> Departamento:
    piso = db.scalars(
        select(Piso).where(Piso.edificio_id == edificio.id)
    ).first()
    if piso is None:
        piso = Piso(edificio_id=edificio.id, numero="1", orden=1)
        db.add(piso)
        db.commit()

    departamento = Departamento(piso_id=piso.id, identificador=identificador)
    db.add(departamento)
    db.commit()
    return departamento


def _expensa(db, edificio, **columnas) -> Expensa:
    datos = {
        "edificio_id": edificio.id,
        "anio": 2026,
        "mes": 11,
        "total": Decimal("4849900.00"),
    }
    datos.update(columnas)
    expensa = Expensa(**datos)
    db.add(expensa)
    db.commit()
    return expensa


# ===========================================================================
# LOS DOS ESTADOS, COMO LOGICA PURA
# ===========================================================================


def test_los_estados_son_dos():
    """"Vencida" y "pagada" no son estados: se calculan. Guardarlos obligaria a
    un proceso diario, y el dia que no corra el sistema miente."""
    assert expensas.ESTADOS == ("borrador", "publicada")


def test_la_transicion_es_de_ida():
    assert expensas.transicion_valida(expensas.BORRADOR, expensas.PUBLICADA)
    assert not expensas.transicion_valida(expensas.PUBLICADA, expensas.BORRADOR)


def test_publicar_una_expensa_ya_publicada_no_es_valido():
    """No es inofensivo: volveria a escribir la fecha de publicacion y con eso
    correria el vencimiento de todo el edificio."""
    assert not expensas.transicion_valida(expensas.PUBLICADA, expensas.PUBLICADA)


def test_un_estado_desconocido_no_habilita_nada():
    """Una fila con un estado que el sistema no entiende no puede abrir
    ninguna puerta."""
    assert not expensas.transicion_valida("cualquier_cosa", expensas.PUBLICADA)
    assert not expensas.es_estado_valido("cualquier_cosa")


def test_solo_el_borrador_se_regenera():
    assert expensas.se_puede_regenerar(expensas.BORRADOR)
    assert not expensas.se_puede_regenerar(expensas.PUBLICADA)


def test_solo_la_publicada_la_ve_el_residente():
    """La otra cara de la misma regla: lo que se puede regenerar es,
    exactamente, lo que el residente todavia no vio."""
    assert not expensas.es_visible_para_el_residente(expensas.BORRADOR)
    assert expensas.es_visible_para_el_residente(expensas.PUBLICADA)


# ===========================================================================
# LA EXPENSA
# ===========================================================================


def test_una_expensa_nace_en_borrador_y_sin_fecha_de_publicacion(db):
    """El residente no tiene que verla hasta que la administracion la publique,
    y el vencimiento no empieza a correr antes."""
    edificio = _edificio(db)

    expensa = _expensa(db, edificio)

    assert expensa.estado == expensas.BORRADOR
    assert expensa.publicada_en is None
    assert not expensa.esta_publicada
    assert expensa.se_puede_regenerar


def test_publicar_deja_la_fecha_y_cierra_la_regeneracion(db):
    edificio = _edificio(db)
    expensa = _expensa(db, edificio)

    expensa.estado = expensas.PUBLICADA
    expensa.publicada_en = datetime(2026, 12, 1, 9, 0)
    db.commit()

    assert expensa.esta_publicada
    assert not expensa.se_puede_regenerar


def test_un_periodo_una_expensa(db):
    """**La restriccion que faltaba.** Sin ella se pueden generar dos
    liquidaciones del mismo mes y "regenerar la ultima" no tiene sentido."""
    edificio = _edificio(db)
    _expensa(db, edificio, anio=2026, mes=11)

    with pytest.raises(IntegrityError):
        _expensa(db, edificio, anio=2026, mes=11)


def test_dos_edificios_pueden_liquidar_el_mismo_periodo(db):
    """La restriccion es por edificio: noviembre de uno y noviembre del otro
    son dos liquidaciones distintas."""
    uno = _edificio(db)
    otro = Edificio(nombre="Otro", direccion="Otra 100", cp="C1001")
    db.add(otro)
    db.commit()

    _expensa(db, uno, anio=2026, mes=11)
    segunda = _expensa(db, otro, anio=2026, mes=11)

    assert segunda.id is not None


@pytest.mark.parametrize("mes", [0, 13, -1])
def test_un_mes_que_no_existe_lo_rechaza_la_base(db, mes):
    edificio = _edificio(db)

    with pytest.raises(IntegrityError):
        _expensa(db, edificio, mes=mes)


@pytest.mark.parametrize("total", ["0.00", "-1500.00"])
def test_un_total_que_no_es_positivo_lo_rechaza_la_base(db, total):
    """Un periodo sin gastos no se liquida; no se liquida en cero."""
    edificio = _edificio(db)

    with pytest.raises(IntegrityError):
        _expensa(db, edificio, total=Decimal(total))


def test_un_estado_invalido_lo_rechaza_la_base(db):
    """El CHECK se arma desde la misma tupla que usa la aplicacion, asi que no
    pueden quedar en desacuerdo."""
    edificio = _edificio(db)

    with pytest.raises(IntegrityError):
        _expensa(db, edificio, estado="emitida")


def test_el_total_es_numerico_con_dos_decimales(db):
    columnas = {c["name"]: c for c in inspect(db.bind).get_columns("expensas")}

    tipo = str(columnas["total"]["type"]).upper()
    assert "NUMERIC" in tipo or "DECIMAL" in tipo
    assert "12, 2" in tipo or "12,2" in tipo


def test_el_periodo_se_lee_como_lo_escribe_una_persona(db):
    edificio = _edificio(db)

    expensa = _expensa(db, edificio, anio=2026, mes=3)

    assert expensa.periodo == "03/2026"


# ===========================================================================
# EL DETALLE POR RUBRO
# ===========================================================================


def test_el_detalle_guarda_los_montos_copiados(db):
    """Copiados y no referenciados: es lo que permite que un gasto sea
    editable y que una liquidacion emitida no cambie."""
    edificio = _edificio(db)
    expensa = _expensa(db, edificio)

    expensa.detalle.append(ExpensaDetalle(rubro="sueldos", monto=Decimal("3000000.00")))
    expensa.detalle.append(ExpensaDetalle(rubro="limpieza", monto=Decimal("150000.00")))
    db.commit()

    assert len(expensa.detalle) == 2


def test_un_rubro_una_linea(db):
    """Dos renglones "Limpieza" en el mismo comprobante y el propietario que
    suma a mano no llega al total."""
    edificio = _edificio(db)
    expensa = _expensa(db, edificio)
    db.add(ExpensaDetalle(expensa_id=expensa.id, rubro="limpieza", monto=Decimal("1.00")))
    db.commit()

    db.add(ExpensaDetalle(expensa_id=expensa.id, rubro="limpieza", monto=Decimal("2.00")))
    with pytest.raises(IntegrityError):
        db.commit()


def test_un_rubro_fuera_del_catalogo_en_el_detalle_lo_rechaza_la_base(db):
    edificio = _edificio(db)
    expensa = _expensa(db, edificio)

    db.add(ExpensaDetalle(expensa_id=expensa.id, rubro="Limpieza", monto=Decimal("1.00")))
    with pytest.raises(IntegrityError):
        db.commit()


def test_el_detalle_se_borra_con_su_expensa(db):
    """No son datos sueltos: son parte del documento."""
    edificio = _edificio(db)
    expensa = _expensa(db, edificio)
    expensa.detalle.append(ExpensaDetalle(rubro="seguros", monto=Decimal("90000.00")))
    db.commit()

    db.delete(expensa)
    db.commit()

    assert db.scalars(select(ExpensaDetalle)).all() == []


# ===========================================================================
# LO QUE PAGA CADA UNIDAD
# ===========================================================================


def _reparto(db, expensa, departamento, **columnas) -> ExpensaDepartamento:
    datos = {
        "expensa_id": expensa.id,
        "departamento_id": departamento.id,
        "coeficiente": Decimal("3.571"),
        "monto_expensa": Decimal("173203.57"),
    }
    datos.update(columnas)
    fila = ExpensaDepartamento(**datos)
    db.add(fila)
    db.commit()
    return fila


def test_los_dos_montos_opcionales_nacen_en_cero(db):
    """El caso normal: nadie se atraso y nadie pago de mas."""
    edificio = _edificio(db)
    expensa = _expensa(db, edificio)
    departamento = _departamento(db, edificio)

    fila = _reparto(db, expensa, departamento)

    assert fila.recargo_mora == Decimal("0.00")
    assert fila.saldo_a_favor_aplicado == Decimal("0.00")
    assert fila.total_a_pagar == Decimal("173203.57")


def test_el_recargo_suma_y_el_saldo_a_favor_resta(db):
    """El saldo a favor se guarda en positivo y se resta: guardarlo con signo
    negativo obligaria a acordarse del signo en cada suma."""
    edificio = _edificio(db)
    expensa = _expensa(db, edificio)
    departamento = _departamento(db, edificio)

    fila = _reparto(
        db,
        expensa,
        departamento,
        monto_expensa=Decimal("100000.00"),
        recargo_mora=Decimal("5000.00"),
        saldo_a_favor_aplicado=Decimal("20000.00"),
    )

    assert fila.total_a_pagar == Decimal("85000.00")


def test_el_total_puede_dar_cero_cuando_el_saldo_a_favor_cubre_todo(db):
    """Pasa de verdad: alguien que adelanto plata y este mes no tiene que pagar
    nada. Cero no es un error."""
    edificio = _edificio(db)
    expensa = _expensa(db, edificio)
    departamento = _departamento(db, edificio)

    fila = _reparto(
        db,
        expensa,
        departamento,
        monto_expensa=Decimal("100000.00"),
        saldo_a_favor_aplicado=Decimal("100000.00"),
    )

    assert fila.total_a_pagar == Decimal("0.00")


def test_una_unidad_exenta_paga_cero(db):
    """Coeficiente 0%: existe por reglamento y el modelo tiene que admitirlo."""
    edificio = _edificio(db)
    expensa = _expensa(db, edificio)
    departamento = _departamento(db, edificio)

    fila = _reparto(
        db,
        expensa,
        departamento,
        coeficiente=Decimal("0.000"),
        monto_expensa=Decimal("0.00"),
    )

    assert fila.total_a_pagar == Decimal("0.00")


def test_una_unidad_aparece_una_sola_vez_en_una_liquidacion(db):
    edificio = _edificio(db)
    expensa = _expensa(db, edificio)
    departamento = _departamento(db, edificio)
    _reparto(db, expensa, departamento)

    db.add(
        ExpensaDepartamento(
            expensa_id=expensa.id,
            departamento_id=departamento.id,
            coeficiente=Decimal("1.000"),
            monto_expensa=Decimal("1.00"),
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize(
    "columna",
    ["monto_expensa", "recargo_mora", "saldo_a_favor_aplicado"],
)
def test_ningun_monto_de_la_unidad_puede_ser_negativo(db, columna):
    edificio = _edificio(db)
    expensa = _expensa(db, edificio)
    departamento = _departamento(db, edificio)

    with pytest.raises(IntegrityError):
        _reparto(db, expensa, departamento, **{columna: Decimal("-1.00")})


def test_el_coeficiente_copiado_no_puede_pasar_de_cien(db):
    edificio = _edificio(db)
    expensa = _expensa(db, edificio)
    departamento = _departamento(db, edificio)

    with pytest.raises(IntegrityError):
        _reparto(db, expensa, departamento, coeficiente=Decimal("100.001"))


def test_el_coeficiente_queda_congelado_aunque_cambie_el_de_la_unidad(db):
    """**La razon por la que se copia.** Un coeficiente mal cargado se corrige,
    y un reglamento de propiedad horizontal se modifica. Sin la copia, una
    expensa de hace ocho meses quedaria sin forma de explicarse: el monto no se
    deduciria del coeficiente actual."""
    edificio = _edificio(db)
    expensa = _expensa(db, edificio)
    departamento = _departamento(db, edificio)
    departamento.coeficiente = Decimal("3.571")
    db.commit()

    fila = _reparto(db, expensa, departamento, coeficiente=Decimal("3.571"))

    departamento.coeficiente = Decimal("4.000")
    db.commit()
    db.expire_all()

    assert db.get(ExpensaDepartamento, fila.id).coeficiente == Decimal("3.571")


def test_el_reparto_se_borra_con_su_expensa(db):
    edificio = _edificio(db)
    expensa = _expensa(db, edificio)
    departamento = _departamento(db, edificio)
    _reparto(db, expensa, departamento)

    db.delete(expensa)
    db.commit()

    assert db.scalars(select(ExpensaDepartamento)).all() == []


def test_hay_indice_por_departamento(db):
    """Es la consulta de "Mi cuenta" y la de deudores: todo lo de ESTA
    unidad."""
    indices = {
        i["name"]: i["column_names"]
        for i in inspect(db.bind).get_indexes("expensa_departamento")
    }

    assert "ix_ed_departamento" in indices


def test_hay_indice_por_edificio_y_periodo(db):
    """La consulta de todo el modulo: las expensas de ESTE edificio, de la mas
    nueva a la mas vieja."""
    indices = {
        i["name"]: i["column_names"] for i in inspect(db.bind).get_indexes("expensas")
    }

    assert "ix_expensas_edificio_periodo" in indices
    assert indices["ix_expensas_edificio_periodo"] == ["edificio_id", "anio", "mes"]


# ===========================================================================
# LA REGLA DE LA FASE, VISTA DESDE EL MODELO
# ===========================================================================


def test_la_suma_de_los_montos_prorrateados_cierra_contra_el_total(db):
    """**Lo que si tiene que cerrar exacto.** La suma de los `total_a_pagar` no
    tiene por que dar el total de la expensa —cada unidad lleva su propio
    recargo y su propio saldo a favor—, pero la suma de lo prorrateado si.
    """
    edificio = _edificio(db)
    expensa = _expensa(db, edificio, total=Decimal("300.00"))
    partes = [Decimal("100.01"), Decimal("99.99"), Decimal("100.00")]

    for numero, parte in enumerate(partes, start=1):
        departamento = _departamento(db, edificio, identificador=f"1{numero}")
        _reparto(
            db,
            expensa,
            departamento,
            coeficiente=Decimal("33.333"),
            monto_expensa=parte,
            recargo_mora=Decimal("500.00"),
        )

    db.expire_all()
    expensa = db.get(Expensa, expensa.id)
    prorrateado = sum(
        (fila.monto_expensa for fila in expensa.por_departamento), Decimal("0.00")
    )
    a_pagar = sum(
        (fila.total_a_pagar for fila in expensa.por_departamento), Decimal("0.00")
    )

    assert prorrateado == expensa.total
    assert a_pagar != expensa.total  # por los recargos, y esta bien que sea asi

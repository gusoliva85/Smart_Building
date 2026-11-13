"""Pruebas del modelo `Gasto` y del catalogo de rubros (`F2-T01`).

Lo que se prueba aca no es que una fila se guarde —eso lo hace cualquier
INSERT— sino las tres cosas que hacen que la plata del consorcio cierre:

  1. **El monto es `Numeric` y no `float`.** Un monto guardado como float es un
     monto guardado "casi", y cien montos casi exactos sumados dan un total que
     no cierra con ninguno de los dos lados. Es la regla que atraviesa toda la
     Fase 2.
  2. **El rubro es un catalogo cerrado.** La expensa y los reportes **agrupan**
     por ese valor: con texto libre, "Limpieza" y "limpieza" serian dos lineas
     distintas en la liquidacion que ve el consorcista.
  3. **Un gasto de cero o negativo no existe.** Si existiera, la suma de los
     gastos de un periodo dejaria de ser el total a repartir.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.models.edificio import Edificio
from app.models.finanzas import Gasto
from app.services import rubros


def _edificio(db) -> Edificio:
    edificio = Edificio(nombre="Consorcio Mitre 500", direccion="Mitre 500", cp="C1000")
    db.add(edificio)
    db.commit()
    return edificio


def _gasto(db, edificio, **columnas) -> Gasto:
    datos = {
        "edificio_id": edificio.id,
        "rubro": "limpieza",
        "monto": Decimal("150000.00"),
        "fecha": date(2026, 11, 5),
    }
    datos.update(columnas)
    gasto = Gasto(**datos)
    db.add(gasto)
    db.commit()
    return gasto


# ===========================================================================
# EL CATALOGO DE RUBROS
# ===========================================================================


def test_el_catalogo_no_tiene_rubros_repetidos():
    """Dos entradas con el mismo nombre serian dos lineas indistinguibles en
    la apertura de la expensa."""
    assert len(rubros.RUBROS) == len(set(rubros.RUBROS))


def test_cada_rubro_tiene_etiqueta_y_descripcion():
    for rubro in rubros.CATALOGO:
        assert rubro.nombre and rubro.nombre.islower()
        assert rubro.etiqueta and rubro.etiqueta != rubro.nombre
        assert rubro.descripcion


def test_existe_el_rubro_de_escape():
    """`otros` existe para que nadie quede bloqueado sin poder cargar un gasto
    real. Si desapareciera, un gasto que no encaja no se podria cargar."""
    assert rubros.OTROS in rubros.RUBROS


def test_un_rubro_inventado_no_es_valido():
    assert not rubros.es_rubro_valido("lo_que_se_me_ocurra")


def test_obtener_un_rubro_invalido_dice_cuales_son_los_validos():
    with pytest.raises(ValueError) as error:
        rubros.obtener("inventado")

    assert "limpieza" in str(error.value)


def test_la_etiqueta_es_la_que_se_muestra():
    assert rubros.etiqueta("sueldos") == "Sueldos y cargas sociales"


# ===========================================================================
# EL MODELO
# ===========================================================================


def test_un_gasto_se_guarda_con_sus_datos(db):
    edificio = _edificio(db)

    gasto = _gasto(db, edificio, descripcion="Servicio de limpieza de noviembre")

    assert gasto.id is not None
    assert gasto.monto == Decimal("150000.00")
    assert gasto.creado_en is not None


def test_el_monto_se_guarda_como_decimal_y_no_como_float(db):
    """La prueba que importa de todo este archivo.

    Un monto con dos decimales tiene que volver de la base **exacto**. Con una
    columna `Float`, 1234.56 vuelve como 1234.5599999999999 y la suma de
    treinta gastos deja de coincidir con el total de la expensa.
    """
    edificio = _edificio(db)
    gasto = _gasto(db, edificio, monto=Decimal("1234.56"))

    db.expire_all()
    guardado = db.get(Gasto, gasto.id)

    assert isinstance(guardado.monto, Decimal)
    assert guardado.monto == Decimal("1234.56")
    assert str(guardado.monto) == "1234.56"


def test_la_columna_del_monto_es_numerica_con_dos_decimales(db):
    """Se mira el tipo declarado, no solo el valor que vuelve: una columna
    `Float` tambien devolveria 1234.56 en un caso facil."""
    columnas = {c["name"]: c for c in inspect(db.bind).get_columns("gastos")}

    tipo = str(columnas["monto"]["type"]).upper()
    assert "NUMERIC" in tipo or "DECIMAL" in tipo
    assert "12, 2" in tipo or "12,2" in tipo


def test_un_monto_en_cero_se_rechaza(db):
    edificio = _edificio(db)

    with pytest.raises(IntegrityError):
        _gasto(db, edificio, monto=Decimal("0.00"))


def test_un_monto_negativo_se_rechaza(db):
    """Un gasto negativo seria un ingreso, y un ingreso se registra como
    movimiento de un fondo (`F2-T12`), no como un gasto con el signo
    cambiado."""
    edificio = _edificio(db)

    with pytest.raises(IntegrityError):
        _gasto(db, edificio, monto=Decimal("-1000.00"))


def test_un_rubro_fuera_del_catalogo_lo_rechaza_la_base(db):
    """La segunda barrera. El esquema de entrada valida el rubro antes, pero el
    CHECK ataja tambien lo que entre por fuera de la API — un script, una
    consola—, que es lo que termina rompiendo un reporte meses despues."""
    edificio = _edificio(db)

    with pytest.raises(IntegrityError):
        _gasto(db, edificio, rubro="Limpieza")  # con mayuscula: no es el valor


@pytest.mark.parametrize("rubro", rubros.RUBROS)
def test_los_diez_rubros_del_catalogo_son_aceptados_por_la_base(db, rubro):
    """El CHECK se arma desde la misma tupla que usa la aplicacion. Si alguna
    vez se escribieran por separado, este test falla en el rubro que quedo
    afuera."""
    edificio = _edificio(db)

    gasto = _gasto(db, edificio, rubro=rubro)

    assert gasto.rubro == rubro


def test_la_descripcion_es_opcional(db):
    edificio = _edificio(db)

    gasto = _gasto(db, edificio, descripcion=None)

    assert gasto.descripcion is None


def test_las_dos_columnas_diferidas_nacen_vacias_y_sin_clave_foranea(db):
    """`proveedor_id` (Fase 7) y `activo_id` (Fase 4) son enteros sueltos: la
    tabla destino no existe todavia. Guardan un valor sin que nada lo valide, y
    eso es deliberado — lo que falta es la restriccion, no el dato."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio, proveedor_id=77, activo_id=99)

    assert gasto.proveedor_id == 77
    assert gasto.activo_id == 99

    claves = inspect(db.bind).get_foreign_keys("gastos")
    columnas_con_fk = {c for clave in claves for c in clave["constrained_columns"]}
    assert columnas_con_fk == {"edificio_id"}


def test_el_gasto_cuelga_de_un_edificio(db):
    edificio = _edificio(db)
    gasto = _gasto(db, edificio)

    assert gasto.edificio.id == edificio.id


def test_la_fecha_es_una_fecha_sin_hora(db):
    """A una factura de luz no le importa la hora, y guardar una hora inventada
    invita a compararla con otra."""
    edificio = _edificio(db)
    gasto = _gasto(db, edificio, fecha=date(2026, 11, 5))

    assert gasto.fecha == date(2026, 11, 5)
    assert not hasattr(gasto.fecha, "hour")


def test_hay_indice_por_edificio_y_fecha(db):
    """Es la consulta que hacen el listado por periodo y la generacion de la
    expensa: los gastos de ESTE edificio en ESTE periodo."""
    indices = {i["name"]: i["column_names"] for i in inspect(db.bind).get_indexes("gastos")}

    assert "ix_gastos_edificio_fecha" in indices
    assert indices["ix_gastos_edificio_fecha"] == ["edificio_id", "fecha"]

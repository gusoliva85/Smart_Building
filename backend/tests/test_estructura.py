"""Pruebas de `Piso`, `Departamento`, `Cochera` y `EspacioComun`.

Lo que se prueba son las garantias de la estructura, no que SQLAlchemy sepa
guardar una fila:

  - que un inquilino no pueda figurar en dos unidades, y que un propietario si,
  - que `ocupado` se derive y no se pueda cargar a mano,
  - que un coeficiente, una superficie o un aforo imposibles no entren ni por
    un INSERT directo,
  - que una cochera rotativa no quede asignada a un departamento,
  - que no se repitan pisos, identificadores de unidad, numeros de cochera ni
    nombres de espacio comun dentro del mismo edificio,
  - y que la estructura generada por `services/finanzas.py` se pueda guardar
    tal cual y sus coeficientes sigan sumando 100% una vez persistidos.
"""

from decimal import Decimal

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from app.models.edificio import (
    COCHERA_FIJA,
    COCHERA_ROTATIVA,
    TIPOS_COCHERA,
    Cochera,
    Departamento,
    Edificio,
    EspacioComun,
    Piso,
)
from app.models.usuario import Usuario
from app.services import autorizacion, finanzas


# --------------------------------------------------------------- helpers ----


def _edificio(db, nombre="Consorcio Rivadavia 1234") -> Edificio:
    edificio = Edificio(nombre=nombre, direccion="Av. Rivadavia 1234", cp="C1033")
    db.add(edificio)
    db.commit()
    return edificio


def _piso(db, edificio, numero=1, orden=None) -> Piso:
    piso = Piso(
        edificio_id=edificio.id,
        numero=numero,
        orden=numero if orden is None else orden,
    )
    db.add(piso)
    db.commit()
    return piso


def _departamento(db, piso, identificador="1A", **cambios) -> Departamento:
    depto = Departamento(piso_id=piso.id, identificador=identificador, **cambios)
    db.add(depto)
    db.commit()
    return depto


def _usuario(db, rol, email) -> Usuario:
    usuario = Usuario(
        nombre="Persona de prueba",
        email=email,
        password_hash="hash-irrelevante-para-estas-pruebas",
        rol=rol,
    )
    db.add(usuario)
    db.commit()
    return usuario


# ==========================================================================
# PISO
# ==========================================================================


def test_dos_pisos_con_el_mismo_numero_en_un_edificio_los_rechaza_la_base(db):
    edificio = _edificio(db)
    _piso(db, edificio, numero=3)

    with pytest.raises(IntegrityError):
        db.execute(
            insert(Piso).values(edificio_id=edificio.id, numero=3, orden=99)
        )
        db.commit()


def test_dos_pisos_con_el_mismo_orden_en_un_edificio_los_rechaza_la_base(db):
    """Dos pisos en el mismo lugar de la pila no se pueden dibujar."""
    edificio = _edificio(db)
    _piso(db, edificio, numero=3, orden=3)

    with pytest.raises(IntegrityError):
        db.execute(
            insert(Piso).values(edificio_id=edificio.id, numero=4, orden=3)
        )
        db.commit()


def test_el_mismo_numero_de_piso_en_edificios_distintos_es_normal(db):
    uno = _edificio(db, "Edificio Uno")
    otro = _edificio(db, "Edificio Dos")

    _piso(db, uno, numero=3)
    _piso(db, otro, numero=3)

    assert db.scalar(select(Piso.id).where(Piso.edificio_id == uno.id))
    assert db.scalar(select(Piso.id).where(Piso.edificio_id == otro.id))


def test_el_numero_del_piso_y_su_lugar_en_la_pila_pueden_no_coincidir(db):
    """Es el motivo de que sean dos columnas: una planta baja se llama 0."""
    edificio = _edificio(db)
    _piso(db, edificio, numero=0, orden=1)
    _piso(db, edificio, numero=1, orden=2)
    db.expire_all()

    edificio = db.scalar(select(Edificio))
    assert [p.numero for p in edificio.pisos] == [0, 1]


def test_los_pisos_del_edificio_vienen_ordenados_por_su_lugar_en_la_pila(db):
    """Un piso 10 dibujado antes del 2 rompe una pantalla cuyo trabajo es
    parecerse a un edificio."""
    edificio = _edificio(db)
    for numero in (10, 2, 7, 1):
        _piso(db, edificio, numero=numero)
    db.expire_all()

    edificio = db.scalar(select(Edificio))
    assert [p.orden for p in edificio.pisos] == [1, 2, 7, 10]


# ==========================================================================
# DEPARTAMENTO — QUIEN LO USA
# ==========================================================================


def test_un_propietario_puede_tener_varias_unidades(db):
    edificio = _edificio(db)
    piso = _piso(db, edificio)
    duenio = _usuario(db, autorizacion.PROPIETARIO, "duenio@ejemplo.com")

    _departamento(db, piso, "1A", propietario_id=duenio.id)
    _departamento(db, piso, "1B", propietario_id=duenio.id)

    cuantas = db.scalar(
        select(Departamento.id).where(Departamento.propietario_id == duenio.id)
    )
    assert cuantas is not None
    assert (
        len(
            db.scalars(
                select(Departamento).where(
                    Departamento.propietario_id == duenio.id
                )
            ).all()
        )
        == 2
    )


def test_un_propietario_puede_tener_unidades_en_edificios_distintos(db):
    duenio = _usuario(db, autorizacion.PROPIETARIO, "duenio@ejemplo.com")
    uno = _piso(db, _edificio(db, "Edificio Uno"))
    otro = _piso(db, _edificio(db, "Edificio Dos"))

    _departamento(db, uno, "1A", propietario_id=duenio.id)
    _departamento(db, otro, "1A", propietario_id=duenio.id)

    assert (
        len(
            db.scalars(
                select(Departamento).where(
                    Departamento.propietario_id == duenio.id
                )
            ).all()
        )
        == 2
    )


def test_un_inquilino_en_dos_unidades_lo_rechaza_la_base(db):
    """La regla "un inquilino, una sola unidad", garantizada por la base.

    No es una limitacion arbitraria: es lo que permite que la interfaz del
    residente nunca le pregunte a un inquilino de cual de sus unidades esta
    hablando.
    """
    edificio = _edificio(db)
    piso = _piso(db, edificio)
    quien_alquila = _usuario(db, autorizacion.INQUILINO, "inqui@ejemplo.com")

    _departamento(db, piso, "1A", inquilino_id=quien_alquila.id)

    with pytest.raises(IntegrityError):
        db.execute(
            insert(Departamento).values(
                piso_id=piso.id,
                identificador="1B",
                inquilino_id=quien_alquila.id,
            )
        )
        db.commit()


def test_muchas_unidades_pueden_estar_sin_inquilino_a_la_vez(db):
    """La unicidad sobre una columna anulable permite muchos NULL.

    Si no fuera asi, la restriccion de arriba haria imposible tener dos
    unidades vacias en el mismo edificio, que es el estado normal de una
    estructura recien generada.
    """
    edificio = _edificio(db)
    piso = _piso(db, edificio)

    for identificador in ("1A", "1B", "1C", "1D"):
        _departamento(db, piso, identificador)

    assert len(db.scalars(select(Departamento)).all()) == 4


def test_nadie_se_alquila_su_propia_unidad(db):
    edificio = _edificio(db)
    piso = _piso(db, edificio)
    persona = _usuario(db, autorizacion.PROPIETARIO, "ambos@ejemplo.com")

    with pytest.raises(IntegrityError):
        db.execute(
            insert(Departamento).values(
                piso_id=piso.id,
                identificador="1A",
                propietario_id=persona.id,
                inquilino_id=persona.id,
            )
        )
        db.commit()


def test_las_dos_relaciones_apuntan_cada_una_a_su_columna(db):
    """Dos claves foraneas a `usuarios`: la ambiguedad no falla al importar."""
    edificio = _edificio(db)
    piso = _piso(db, edificio)
    duenio = _usuario(db, autorizacion.PROPIETARIO, "duenio@ejemplo.com")
    quien_alquila = _usuario(db, autorizacion.INQUILINO, "inqui@ejemplo.com")

    _departamento(
        db, piso, "1A", propietario_id=duenio.id, inquilino_id=quien_alquila.id
    )
    db.expire_all()

    depto = db.scalar(select(Departamento))
    assert depto.propietario.email == "duenio@ejemplo.com"
    assert depto.inquilino.email == "inqui@ejemplo.com"


# ==========================================================================
# DEPARTAMENTO — `ocupado` SE DERIVA
# ==========================================================================


def test_ocupado_no_es_una_columna_de_la_tabla(db):
    """Si fuera columna, algun dia diria que la unidad esta vacia mientras
    tiene un inquilino con contrato firmado."""
    assert "ocupado" not in Departamento.__table__.columns


def test_una_unidad_sin_nadie_no_esta_ocupada(db):
    edificio = _edificio(db)
    depto = _departamento(db, _piso(db, edificio), "1A")

    assert depto.ocupado is False


def test_una_unidad_con_propietario_esta_ocupada(db):
    edificio = _edificio(db)
    duenio = _usuario(db, autorizacion.PROPIETARIO, "duenio@ejemplo.com")
    depto = _departamento(
        db, _piso(db, edificio), "1A", propietario_id=duenio.id
    )

    assert depto.ocupado is True


def test_una_unidad_con_inquilino_esta_ocupada(db):
    edificio = _edificio(db)
    quien_alquila = _usuario(db, autorizacion.INQUILINO, "inqui@ejemplo.com")
    depto = _departamento(
        db, _piso(db, edificio), "1A", inquilino_id=quien_alquila.id
    )

    assert depto.ocupado is True


def test_ocupado_tambien_filtra_en_sql(db):
    """Es `hybrid_property` y no una `property` comun justamente por esto:
    filtrar en la base y no traer todo a Python para descartarlo."""
    edificio = _edificio(db)
    piso = _piso(db, edificio)
    duenio = _usuario(db, autorizacion.PROPIETARIO, "duenio@ejemplo.com")

    _departamento(db, piso, "1A", propietario_id=duenio.id)
    _departamento(db, piso, "1B")
    _departamento(db, piso, "1C")

    ocupadas = db.scalars(
        select(Departamento.identificador).where(Departamento.ocupado)
    ).all()
    libres = db.scalars(
        select(Departamento.identificador).where(~Departamento.ocupado)
    ).all()

    assert list(ocupadas) == ["1A"]
    assert sorted(libres) == ["1B", "1C"]


# ==========================================================================
# DEPARTAMENTO — IDENTIFICADOR, SUPERFICIE Y COEFICIENTE
# ==========================================================================


def test_dos_unidades_con_el_mismo_identificador_en_un_piso_las_rechaza_la_base(db):
    edificio = _edificio(db)
    piso = _piso(db, edificio)
    _departamento(db, piso, "1A")

    with pytest.raises(IntegrityError):
        db.execute(
            insert(Departamento).values(piso_id=piso.id, identificador="1A")
        )
        db.commit()


def test_el_mismo_identificador_en_pisos_distintos_es_normal(db):
    edificio = _edificio(db)
    uno = _piso(db, edificio, numero=1)
    otro = _piso(db, edificio, numero=2)

    _departamento(db, uno, "A")
    _departamento(db, otro, "A")

    assert len(db.scalars(select(Departamento)).all()) == 2


def test_una_unidad_nace_sin_superficie_y_sin_coeficiente(db):
    """La estructura automatica no puede inventar ni una ni el otro.

    Y un coeficiente inventado es peor que uno ausente: el ausente lo encuentra
    la validacion antes de generar una expensa, el inventado reparte plata mal
    sin que nadie lo note.
    """
    edificio = _edificio(db)
    depto = _departamento(db, _piso(db, edificio), "1A")

    assert depto.m2 is None
    assert depto.coeficiente is None


@pytest.mark.parametrize("m2", ["0", "-10", "-0.01"])
def test_una_superficie_imposible_la_rechaza_la_base(db, m2):
    edificio = _edificio(db)
    piso = _piso(db, edificio)

    with pytest.raises(IntegrityError):
        db.execute(
            insert(Departamento).values(
                piso_id=piso.id, identificador="1A", m2=Decimal(m2)
            )
        )
        db.commit()


@pytest.mark.parametrize("coeficiente", ["-0.001", "-1", "100.001", "500"])
def test_un_coeficiente_fuera_de_rango_lo_rechaza_la_base(db, coeficiente):
    edificio = _edificio(db)
    piso = _piso(db, edificio)

    with pytest.raises(IntegrityError):
        db.execute(
            insert(Departamento).values(
                piso_id=piso.id,
                identificador="1A",
                coeficiente=Decimal(coeficiente),
            )
        )
        db.commit()


@pytest.mark.parametrize("coeficiente", ["0", "3.571", "50", "100"])
def test_los_coeficientes_reales_si_se_aceptan(db, coeficiente):
    edificio = _edificio(db)
    depto = _departamento(
        db, _piso(db, edificio), "1A", coeficiente=Decimal(coeficiente)
    )
    db.expire_all()

    guardado = db.scalar(select(Departamento.coeficiente))
    assert guardado == Decimal(coeficiente)
    assert depto.id is not None


def test_el_coeficiente_guarda_los_tres_decimales_que_reparte_el_servicio(db):
    """`Numeric(6,3)`: es la precision a la que `services/finanzas.py` reparte.

    Si la columna guardara menos, la suma dejaria de dar 100% al persistir —
    que es exactamente el error de 99,989% de la iteracion anterior.
    """
    edificio = _edificio(db)
    _departamento(db, _piso(db, edificio), "1A", coeficiente=Decimal("3.572"))
    db.expire_all()

    assert db.scalar(select(Departamento.coeficiente)) == Decimal("3.572")


# ==========================================================================
# COCHERA
# ==========================================================================


@pytest.mark.parametrize("tipo", TIPOS_COCHERA)
def test_los_dos_tipos_de_cochera_se_aceptan(db, tipo):
    edificio = _edificio(db)
    db.add(Cochera(edificio_id=edificio.id, numero="1", tipo=tipo))
    db.commit()

    assert db.scalar(select(Cochera.tipo)) == tipo


def test_un_tipo_de_cochera_inexistente_lo_rechaza_la_base(db):
    edificio = _edificio(db)

    with pytest.raises(IntegrityError):
        db.execute(
            insert(Cochera).values(
                edificio_id=edificio.id, numero="1", tipo="flotante"
            )
        )
        db.commit()


def test_una_cochera_fija_puede_estar_asignada_a_una_unidad(db):
    edificio = _edificio(db)
    depto = _departamento(db, _piso(db, edificio), "1A")

    db.add(
        Cochera(
            edificio_id=edificio.id,
            numero="12",
            tipo=COCHERA_FIJA,
            departamento_id=depto.id,
        )
    )
    db.commit()
    db.expire_all()

    assert db.scalar(select(Cochera)).departamento.identificador == "1A"


def test_una_cochera_fija_puede_estar_sin_asignar(db):
    edificio = _edificio(db)
    db.add(Cochera(edificio_id=edificio.id, numero="12", tipo=COCHERA_FIJA))
    db.commit()

    assert db.scalar(select(Cochera.departamento_id)) is None


def test_una_cochera_rotativa_asignada_a_una_unidad_la_rechaza_la_base(db):
    """Rotativa significa justamente que no es de nadie en particular."""
    edificio = _edificio(db)
    depto = _departamento(db, _piso(db, edificio), "1A")

    with pytest.raises(IntegrityError):
        db.execute(
            insert(Cochera).values(
                edificio_id=edificio.id,
                numero="12",
                tipo=COCHERA_ROTATIVA,
                departamento_id=depto.id,
            )
        )
        db.commit()


def test_dos_cocheras_con_el_mismo_numero_en_un_edificio_las_rechaza_la_base(db):
    edificio = _edificio(db)
    db.add(Cochera(edificio_id=edificio.id, numero="S2-14", tipo=COCHERA_FIJA))
    db.commit()

    with pytest.raises(IntegrityError):
        db.execute(
            insert(Cochera).values(
                edificio_id=edificio.id, numero="S2-14", tipo=COCHERA_ROTATIVA
            )
        )
        db.commit()


def test_el_numero_de_cochera_admite_rotulos_que_no_son_numeros(db):
    """En la practica estan rotuladas, y el rotulo dice "S2-14" tan seguido
    como dice "12"."""
    edificio = _edificio(db)
    db.add(Cochera(edificio_id=edificio.id, numero="S2-14", tipo=COCHERA_FIJA))
    db.commit()

    assert db.scalar(select(Cochera.numero)) == "S2-14"


# ==========================================================================
# ESPACIO COMUN
# ==========================================================================


def test_un_espacio_comun_se_guarda_con_su_aforo_y_sus_reglas(db):
    edificio = _edificio(db)
    db.add(
        EspacioComun(
            edificio_id=edificio.id,
            nombre="SUM",
            capacidad=40,
            reglas_uso="Se reserva con 48 horas de anticipacion. No despues de las 23.",
        )
    )
    db.commit()

    espacio = db.scalar(select(EspacioComun))
    assert espacio.capacidad == 40
    assert "48 horas" in espacio.reglas_uso


def test_un_espacio_comun_puede_no_tener_aforo_declarado(db):
    """Un laundry con dos lavarropas no tiene aforo, y un 0 como "sin dato"
    seria un espacio que no admite a nadie."""
    edificio = _edificio(db)
    db.add(EspacioComun(edificio_id=edificio.id, nombre="Laundry"))
    db.commit()

    espacio = db.scalar(select(EspacioComun))
    assert espacio.capacidad is None
    assert espacio.reglas_uso is None


@pytest.mark.parametrize("capacidad", [0, -1])
def test_un_aforo_imposible_lo_rechaza_la_base(db, capacidad):
    edificio = _edificio(db)

    with pytest.raises(IntegrityError):
        db.execute(
            insert(EspacioComun).values(
                edificio_id=edificio.id, nombre="SUM", capacidad=capacidad
            )
        )
        db.commit()


def test_dos_espacios_con_el_mismo_nombre_en_un_edificio_los_rechaza_la_base(db):
    """Dos "Parrilla" no se distinguen en una lista de reserva."""
    edificio = _edificio(db)
    db.add(EspacioComun(edificio_id=edificio.id, nombre="Parrilla"))
    db.commit()

    with pytest.raises(IntegrityError):
        db.execute(
            insert(EspacioComun).values(
                edificio_id=edificio.id, nombre="Parrilla"
            )
        )
        db.commit()


def test_el_mismo_nombre_de_espacio_en_edificios_distintos_es_normal(db):
    uno = _edificio(db, "Edificio Uno")
    otro = _edificio(db, "Edificio Dos")

    db.add_all(
        [
            EspacioComun(edificio_id=uno.id, nombre="SUM"),
            EspacioComun(edificio_id=otro.id, nombre="SUM"),
        ]
    )
    db.commit()

    assert len(db.scalars(select(EspacioComun)).all()) == 2


# ==========================================================================
# LAS COLECCIONES DEL EDIFICIO
# ==========================================================================


def test_el_edificio_llega_a_sus_cocheras_y_a_sus_espacios_comunes(db):
    edificio = _edificio(db)
    db.add_all(
        [
            Cochera(edificio_id=edificio.id, numero="1", tipo=COCHERA_FIJA),
            Cochera(edificio_id=edificio.id, numero="2", tipo=COCHERA_ROTATIVA),
            EspacioComun(edificio_id=edificio.id, nombre="SUM"),
        ]
    )
    db.commit()
    db.expire_all()

    edificio = db.scalar(select(Edificio))
    assert [c.numero for c in edificio.cocheras] == ["1", "2"]
    assert [e.nombre for e in edificio.espacios_comunes] == ["SUM"]


def test_borrar_un_piso_que_todavia_tiene_unidades_falla_ruidosamente(db):
    """A proposito: dar de baja una unidad es una decision con consecuencias
    —puede tener expensas y pagos apuntandole— y la toma `F1-T23`, no un
    borrado en cascada silencioso."""
    edificio = _edificio(db)
    piso = _piso(db, edificio)
    _departamento(db, piso, "1A")

    with pytest.raises(IntegrityError):
        db.delete(piso)
        db.commit()


# ==========================================================================
# LAS DOS MITADES JUNTAS: F1-T17 GENERA, F1-T19 GUARDA
# ==========================================================================


def test_la_estructura_generada_se_guarda_tal_cual(db):
    """Es el precursor directo de `F1-T20`, que lo hace en una transaccion."""
    edificio = _edificio(db)

    for proyectado in finanzas.generar_estructura(
        cantidad_pisos=7, unidades_por_piso=4
    ):
        piso = Piso(
            edificio_id=edificio.id,
            numero=proyectado.numero,
            orden=proyectado.orden,
        )
        db.add(piso)
        db.flush()
        for unidad in proyectado.unidades:
            db.add(
                Departamento(
                    piso_id=piso.id, identificador=unidad.identificador
                )
            )
    db.commit()
    db.expire_all()

    assert len(db.scalars(select(Piso)).all()) == 7
    assert len(db.scalars(select(Departamento)).all()) == 28

    edificio = db.scalar(select(Edificio))
    primero = edificio.pisos[0]
    assert primero.numero == 1
    assert [d.identificador for d in primero.departamentos] == [
        "1A",
        "1B",
        "1C",
        "1D",
    ]


def test_los_coeficientes_del_atajo_siguen_sumando_cien_una_vez_guardados(db):
    """El error historico de 99,989%, probado contra la base y no en memoria.

    La iteracion anterior redondeaba a cuatro decimales y la columna guarda
    tres, asi que la suma en memoria daba 100% y la suma guardada no. Lo unico
    que prueba de verdad que eso no vuelve a pasar es sumar lo que quedo en la
    base, con una cantidad de unidades que no divide exacto.
    """
    edificio = _edificio(db)
    piso = _piso(db, edificio)

    coeficientes = finanzas.calcular_partes_iguales(28)
    for indice, coeficiente in enumerate(coeficientes):
        db.add(
            Departamento(
                piso_id=piso.id,
                identificador="U%02d" % indice,
                coeficiente=coeficiente,
            )
        )
    db.commit()
    db.expire_all()

    guardados = db.scalars(select(Departamento.coeficiente)).all()

    assert len(guardados) == 28
    assert sum(guardados, Decimal(0)) == Decimal("100.000")
    assert finanzas.validar_coeficientes(guardados)

"""Pruebas del ciclo de vida del pago (`F2-T07`).

Son cuatro reglas y las cuatro son de dinero, asi que se prueban una por una
incluidos los casos que "no deberian pasar":

  1. **Solo un pago confirmado reduce la deuda.**
  2. **Las dos transiciones salen de `pendiente` y ninguna vuelve.**
  3. **Quien carga no confirma**, ni siquiera siendo el administrador.
  4. **Un pago pendiente se le muestra al residente** sin tocar el saldo — la
     diferencia entre las dos preguntas es el problema que el modulo resuelve.
"""

import pytest

from app.services import pagos


# ===========================================================================
# LOS ESTADOS
# ===========================================================================


def test_son_tres_estados():
    assert pagos.ESTADOS == ("pendiente", "confirmado", "rechazado")


@pytest.mark.parametrize("estado", pagos.ESTADOS)
def test_los_tres_estados_son_validos(estado):
    assert pagos.es_estado_valido(estado)


def test_un_estado_inventado_no_es_valido():
    assert not pagos.es_estado_valido("acreditado")


# ===========================================================================
# LA REGLA FUNDAMENTAL
# ===========================================================================


def test_solo_el_confirmado_reduce_la_deuda():
    """**La regla que sostiene todo el modulo.** Si un pago pendiente bajara el
    saldo, cualquiera podria subir un comprobante falso y aparecer sin deuda
    sin que la plata haya entrado."""
    assert pagos.reduce_la_deuda(pagos.CONFIRMADO)
    assert not pagos.reduce_la_deuda(pagos.PENDIENTE)
    assert not pagos.reduce_la_deuda(pagos.RECHAZADO)


def test_un_estado_desconocido_no_reduce_la_deuda():
    """El default de una funcion que decide sobre plata tiene que ser el que no
    regala nada."""
    assert not pagos.reduce_la_deuda("lo_que_sea")


# ===========================================================================
# LAS TRANSICIONES
# ===========================================================================


def test_un_pago_pendiente_se_confirma_o_se_rechaza():
    assert pagos.transicion_valida(pagos.PENDIENTE, pagos.CONFIRMADO)
    assert pagos.transicion_valida(pagos.PENDIENTE, pagos.RECHAZADO)


def test_un_pago_confirmado_no_se_desconfirma():
    """Si la administracion confirmo por equivocacion, lo que corresponde es
    registrar el movimiento que lo corrige, no reescribir el historial."""
    assert not pagos.transicion_valida(pagos.CONFIRMADO, pagos.PENDIENTE)
    assert not pagos.transicion_valida(pagos.CONFIRMADO, pagos.RECHAZADO)


def test_un_pago_rechazado_no_se_reactiva():
    """El residente carga uno nuevo con su comprobante, y queda la traza de los
    dos intentos."""
    assert not pagos.transicion_valida(pagos.RECHAZADO, pagos.CONFIRMADO)
    assert not pagos.transicion_valida(pagos.RECHAZADO, pagos.PENDIENTE)


@pytest.mark.parametrize("estado", pagos.ESTADOS)
def test_pasar_al_mismo_estado_nunca_es_valido(estado):
    """Confirmar dos veces el mismo pago no es inofensivo si en el medio quedo
    registrado quien lo confirmo y cuando."""
    assert not pagos.transicion_valida(estado, estado)


def test_un_estado_desconocido_no_habilita_ninguna_transicion():
    assert not pagos.transicion_valida("acreditado", pagos.CONFIRMADO)
    assert pagos.estados_siguientes("acreditado") == ()


def test_los_estados_siguientes_son_los_que_la_pantalla_ofrece():
    """Para que el JavaScript no tenga su propia copia de la tabla de
    transiciones, que es la copia que un dia ofrece un boton que el servidor
    rechaza."""
    assert set(pagos.estados_siguientes(pagos.PENDIENTE)) == {
        pagos.CONFIRMADO,
        pagos.RECHAZADO,
    }
    assert pagos.estados_siguientes(pagos.CONFIRMADO) == ()
    assert pagos.estados_siguientes(pagos.RECHAZADO) == ()


def test_los_dos_estados_finales_estan_conciliados():
    """Preguntar por los dos por separado es como se termina olvidando uno."""
    assert pagos.esta_conciliado(pagos.CONFIRMADO)
    assert pagos.esta_conciliado(pagos.RECHAZADO)
    assert not pagos.esta_conciliado(pagos.PENDIENTE)


# ===========================================================================
# QUIEN CARGA NO CONFIRMA
# ===========================================================================


def test_el_residente_no_confirma_su_propio_pago():
    """La separacion de funciones mas basica de cualquier circuito de dinero:
    si quien declara el pago es tambien quien lo valida, la validacion no
    valida nada."""
    assert not pagos.puede_confirmar(quien_confirma_id=7, quien_cargo_id=7)


def test_otra_persona_si_puede_confirmar():
    assert pagos.puede_confirmar(quien_confirma_id=1, quien_cargo_id=7)


def test_el_administrador_que_vive_en_el_edificio_no_concilia_su_propio_pago():
    """**El caso que de verdad pasa**, y la razon por la que la regla se
    escribe por quien cargo el pago y no por el rol de quien lo mira: una
    persona puede administrar el consorcio y ser propietaria de una unidad.
    Concilia los pagos de sus vecinos, no el suyo.
    """
    administrador_propietario = 42

    assert not pagos.puede_confirmar(
        quien_confirma_id=administrador_propietario,
        quien_cargo_id=administrador_propietario,
    )
    assert pagos.puede_confirmar(
        quien_confirma_id=administrador_propietario, quien_cargo_id=99
    )


# ===========================================================================
# MOSTRAR SIN BAJAR EL SALDO
# ===========================================================================


@pytest.mark.parametrize("estado", pagos.ESTADOS)
def test_los_tres_estados_se_le_muestran_al_residente(estado):
    """El pendiente para que no vuelva a pagar, el confirmado porque es su
    recibo, y el rechazado porque es la unica forma de que se entere: un pago
    que desaparece sin explicacion es un llamado telefonico garantizado."""
    assert pagos.se_le_muestra_al_residente(estado)


def test_mostrar_y_reducir_la_deuda_son_dos_preguntas_distintas():
    """**La diferencia entre las dos funciones es exactamente el problema que
    este modulo resuelve:** el pago pendiente se muestra y no baja el saldo. Si
    alguien las unificara, o el residente deja de ver su pago cargado y vuelve
    a pagar, o un comprobante sin verificar le borra la deuda.
    """
    assert pagos.se_le_muestra_al_residente(pagos.PENDIENTE)
    assert not pagos.reduce_la_deuda(pagos.PENDIENTE)

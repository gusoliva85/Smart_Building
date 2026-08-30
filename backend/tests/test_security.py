"""Tests de core/security.py — hash de contraseñas y JWT.

Cubre exactamente las dos garantías que promete el Documento Técnico
(secciones 3.2 y 19): una contraseña nunca queda expuesta en texto plano
ni siquiera comparándola con su propio hash, y un token vencido o alterado
se rechaza siempre, nunca se decodifica "a medias".
"""

import pytest

from app.core.security import (
    TokenInvalido,
    crear_token_acceso,
    decodificar_token,
    hashear_password,
    verificar_password,
)


def test_el_hash_nunca_es_igual_a_la_password_original():
    hash_resultante = hashear_password("mi-clave-de-prueba")
    assert hash_resultante != "mi-clave-de-prueba"
    assert "mi-clave-de-prueba" not in hash_resultante


def test_la_misma_password_genera_hashes_distintos_cada_vez():
    # bcrypt agrega un salt aleatorio — dos hashes de la misma password
    # nunca deberían ser idénticos entre sí, aunque ambos la validen bien.
    hash_1 = hashear_password("otra-clave")
    hash_2 = hashear_password("otra-clave")
    assert hash_1 != hash_2
    assert verificar_password("otra-clave", hash_1) is True
    assert verificar_password("otra-clave", hash_2) is True


def test_verificar_password_correcta_e_incorrecta():
    hash_resultante = hashear_password("clave-correcta")
    assert verificar_password("clave-correcta", hash_resultante) is True
    assert verificar_password("clave-incorrecta", hash_resultante) is False


def test_crear_y_decodificar_token_devuelve_los_mismos_datos():
    token = crear_token_acceso({"sub": "ana@test.com", "rol": "admin_general"})
    datos = decodificar_token(token)
    assert datos["sub"] == "ana@test.com"
    assert datos["rol"] == "admin_general"
    assert "exp" in datos  # la expiración se agregó sola


def test_token_alterado_es_rechazado():
    token = crear_token_acceso({"sub": "ana@test.com"})
    token_alterado = token[:-3] + ("xxx" if not token.endswith("xxx") else "yyy")
    with pytest.raises(TokenInvalido):
        decodificar_token(token_alterado)


def test_token_ya_vencido_es_rechazado():
    token = crear_token_acceso({"sub": "ana@test.com"}, minutos_expiracion=-1)
    with pytest.raises(TokenInvalido):
        decodificar_token(token)

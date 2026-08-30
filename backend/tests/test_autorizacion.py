"""Tests de la lógica de RBAC (backend/app/services/autorizacion.py).

Primer módulo del proyecto con lógica de negocio no trivial (Documento
Técnico, sección 20) — el control de acceso es, además, el tipo de regla
donde un error es especialmente costoso (fuga de datos entre edificios),
así que se cubre con tests desde el día uno en vez de confiar solo en la
revisión manual.
"""

import pytest

from app.services import autorizacion as auth


def test_admin_general_accede_a_cualquier_edificio_aunque_no_este_en_su_lista():
    assert auth.tiene_acceso_a_edificio("admin_general", [], edificio_id=99) is True


@pytest.mark.parametrize(
    "rol",
    ["admin_consorcio", "encargado", "propietario", "inquilino", "proveedor", "auditor", "seguridad"],
)
def test_otros_roles_solo_acceden_a_sus_propios_edificios(rol):
    edificios_del_usuario = [1, 2]
    assert auth.tiene_acceso_a_edificio(rol, edificios_del_usuario, edificio_id=1) is True
    assert auth.tiene_acceso_a_edificio(rol, edificios_del_usuario, edificio_id=999) is False


def test_rol_invalido_lanza_error_en_vez_de_fallar_en_silencio():
    with pytest.raises(ValueError):
        auth.alcance_de("rol_que_no_existe")


def test_visibilidad_financiera_por_unidad_solo_propietario_y_auditor():
    assert auth.ve_financiero_unidad("propietario") is True
    assert auth.ve_financiero_unidad("auditor") is True
    assert auth.ve_financiero_unidad("inquilino") is False
    assert auth.ve_financiero_unidad("admin_general") is False


def test_visibilidad_financiera_de_edificio_admins_y_auditor_no_encargado():
    assert auth.ve_financiero_edificio("admin_general") is True
    assert auth.ve_financiero_edificio("admin_consorcio") is True
    assert auth.ve_financiero_edificio("auditor") is True
    # el Encargado ve solo el semáforo general, nunca montos (Documento Técnico, sección 1.1)
    assert auth.ve_financiero_edificio("encargado") is False


def test_solo_auditor_es_de_solo_lectura():
    roles_no_auditor = [r for r in auth.ROLES if r != "auditor"]
    assert auth.es_solo_lectura("auditor") is True
    assert all(auth.es_solo_lectura(rol) is False for rol in roles_no_auditor)


def test_todos_los_8_roles_del_documento_general_estan_en_la_matriz():
    assert len(auth.ROLES) == 8
    assert set(auth.ROLES) == set(auth.MATRIZ_ROLES.keys())

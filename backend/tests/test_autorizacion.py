"""La matriz de roles.

Es el modulo del que dependen todos los permisos del sistema, asi que se prueba
de dos maneras distintas y complementarias:

1. **Rol por rol**, contra la tabla del Documento Tecnico (seccion 4.2). Si
   alguien cambia un permiso sin querer, un test puntual lo dice.
2. **Por invariantes** — propiedades que tienen que valer sobre la matriz
   completa. Esos son los que atajan el error que nadie ve venir: agregar un
   noveno rol y olvidarse de decidir si ve montos, por ejemplo.
"""

import pytest

from app.services import autorizacion as auth

# La tabla del Documento Tecnico, seccion 4.2, transcrita a mano a proposito.
# Si esta tabla y la matriz del servicio se contradicen, uno de los dos esta
# mal — y para eso existe este test. Copiar la matriz con un import seria
# probar que un archivo es igual a si mismo.
#
# rol: (alcance, ve_financiero_unidad, ve_financiero_edificio, solo_lectura)
MATRIZ_ESPERADA = {
    "admin_general":   (auth.ALCANCE_CARTERA,        True,  True,  False),
    "admin_consorcio": (auth.ALCANCE_EDIFICIO,       True,  True,  False),
    "encargado":       (auth.ALCANCE_EDIFICIO,       False, False, False),
    "propietario":     (auth.ALCANCE_UNIDAD,         True,  False, False),
    "inquilino":       (auth.ALCANCE_UNIDAD,         True,  False, False),
    "proveedor":       (auth.ALCANCE_OTS_ASIGNADAS,  False, False, False),
    "auditor":         (auth.ALCANCE_ASIGNADO,       True,  True,  True),
    "seguridad":       (auth.ALCANCE_EDIFICIO,       False, False, False),
}


# ------------------------------------------------------------ rol por rol ----


@pytest.mark.parametrize("rol", MATRIZ_ESPERADA)
def test_cada_rol_coincide_con_la_documentacion(rol):
    esperado = MATRIZ_ESPERADA[rol]

    assert auth.alcance(rol) == esperado[0]
    assert auth.ve_financiero_unidad(rol) is esperado[1]
    assert auth.ve_financiero_edificio(rol) is esperado[2]
    assert auth.es_solo_lectura(rol) is esperado[3]


@pytest.mark.parametrize("rol", MATRIZ_ESPERADA)
def test_cada_rol_tiene_etiqueta_legible(rol):
    """La etiqueta es lo que ve una persona en pantalla, no el nombre tecnico."""
    etiqueta = auth.etiqueta(rol)

    assert etiqueta and etiqueta != rol
    assert etiqueta[0].isupper()


# ----------------------------------------------------------- invariantes -----


def test_son_exactamente_los_ocho_roles_documentados():
    assert auth.ROLES == tuple(MATRIZ_ESPERADA)
    assert len(auth.ROLES) == 8


def test_todo_rol_tiene_un_alcance_declarado_y_valido():
    """El error que ataja: agregar un rol y dejarle un alcance inventado."""
    for rol in auth.ROLES:
        assert auth.alcance(rol) in auth.ALCANCES


def test_el_auditor_es_el_unico_de_solo_lectura():
    de_solo_lectura = [r for r in auth.ROLES if auth.es_solo_lectura(r)]

    assert de_solo_lectura == [auth.AUDITOR]


def test_quien_ve_el_financiero_del_edificio_ve_tambien_el_de_la_unidad():
    """No puede existir un rol que vea los importes del edificio entero y no
    los de una de sus unidades: la unidad es parte del edificio."""
    for rol in auth.ROLES:
        if auth.ve_financiero_edificio(rol):
            assert auth.ve_financiero_unidad(rol), rol


def test_solo_tres_roles_ven_el_financiero_del_edificio():
    con_acceso = [r for r in auth.ROLES if auth.ve_financiero_edificio(r)]

    assert set(con_acceso) == {auth.ADMIN_GENERAL, auth.ADMIN_CONSORCIO, auth.AUDITOR}


def test_el_encargado_nunca_ve_montos():
    """Gestiona reclamos, ordenes y activos de su edificio; ve el semaforo.
    Los importes, no. Es una regla de negocio, no una restriccion tecnica."""
    assert auth.ve_financiero_unidad(auth.ENCARGADO) is False
    assert auth.ve_financiero_edificio(auth.ENCARGADO) is False


def test_propietario_e_inquilino_tienen_el_mismo_acceso_financiero():
    """Decision adoptada (Documento General 3.1). En la practica la expensa
    ordinaria la paga el inquilino, y uno que no puede ver su propia expensa no
    puede usar el modulo que mas va a usar. La diferencia entre los dos esta en
    la estructura (el propietario puede tener varias unidades, el inquilino
    una), no en los permisos."""
    assert auth.ve_financiero_unidad(auth.PROPIETARIO) is auth.ve_financiero_unidad(auth.INQUILINO)
    assert auth.ve_financiero_edificio(auth.PROPIETARIO) is auth.ve_financiero_edificio(auth.INQUILINO)
    assert auth.alcance(auth.PROPIETARIO) == auth.alcance(auth.INQUILINO)


def test_ningun_residente_ve_el_financiero_del_edificio():
    """Un vecino ve lo suyo. Los numeros del consorcio son de la administracion
    y del auditor."""
    for rol in (auth.PROPIETARIO, auth.INQUILINO):
        assert auth.ve_financiero_edificio(rol) is False


def test_el_proveedor_solo_alcanza_sus_ordenes():
    assert auth.alcance(auth.PROVEEDOR) == auth.ALCANCE_OTS_ASIGNADAS
    assert auth.ve_financiero_unidad(auth.PROVEEDOR) is False


def test_el_auditor_no_arranca_con_la_cartera_entera():
    """Su alcance se asigna por usuario. El valor por defecto tiene que ser
    "ningun edificio", no "todos": lo contrario es un sobre-permiso silencioso.
    El mecanismo del vinculo se decide en F1-T02."""
    assert auth.alcance(auth.AUDITOR) == auth.ALCANCE_ASIGNADO
    assert auth.alcance(auth.AUDITOR) != auth.ALCANCE_CARTERA


def test_solo_el_admin_general_alcanza_toda_la_cartera():
    assert auth.roles_con(auth.ALCANCE_CARTERA) == (auth.ADMIN_GENERAL,)


# -------------------------------------------------- rol invalido y utilidades --


def test_un_rol_que_no_existe_falla_ruidosamente():
    """No devuelve un rol por defecto ni None: un permiso que se resuelve en
    silencio es la forma mas facil de abrir un agujero sin darse cuenta."""
    with pytest.raises(auth.RolDesconocido, match="Rol desconocido"):
        auth.obtener("administrador")


def test_el_mensaje_del_error_lista_los_roles_validos():
    with pytest.raises(auth.RolDesconocido) as error:
        auth.alcance("gerente")

    for rol in auth.ROLES:
        assert rol in str(error.value)


@pytest.mark.parametrize("invalido", ["", "ADMIN_GENERAL", "admin general", None, "admin_generall"])
def test_es_rol_valido_rechaza_variantes_parecidas(invalido):
    """Sin distincion de mayusculas ni espacios: el nombre es exacto."""
    assert auth.es_rol_valido(invalido) is False


def test_puede_escribir_es_el_inverso_de_solo_lectura():
    for rol in auth.ROLES:
        assert auth.puede_escribir(rol) is not auth.es_solo_lectura(rol)


def test_la_definicion_de_un_rol_es_inmutable():
    """Nadie puede cambiar un permiso en caliente desde otro modulo."""
    rol = auth.obtener(auth.ENCARGADO)

    with pytest.raises(Exception):
        rol.ve_financiero_edificio = True

"""Reglas de RBAC (control de acceso basado en rol) — Documento Técnico, sección 6.

Esta es la "lógica" del bloque Usuarios y autenticación: define, en funciones
puras de Python (sin tocar la base de datos ni HTTP todavía), la matriz de
roles completa y las reglas de alcance/visibilidad que el resto del backend
va a reutilizar. En particular, la dependencia `get_current_user` de FastAPI
(tarea siguiente de esta misma fase) va a llamar a estas funciones en vez de
repetir el chequeo de permisos a mano en cada endpoint nuevo.

Modelo elegido para esta etapa (Documento Técnico, sección 6.1): RBAC simple,
un rol = un conjunto fijo de permisos. Los "permisos por excepción" (ej. un
inquilino puntual habilitado a ver expensas) quedan documentados como
extensión futura, implementados recién en la Fase 11.
"""

# Alcance: hasta dónde llega el rol dentro de la plataforma.
ALCANCE_CARTERA = "cartera"                # todos los edificios administrados
ALCANCE_EDIFICIO = "edificio"              # un edificio puntual
ALCANCE_UNIDAD = "unidad"                  # su(s) unidad(es) dentro de un edificio
ALCANCE_OTS_ASIGNADAS = "ots_asignadas"    # solo las órdenes de trabajo que le asignaron
ALCANCE_EDIFICIO_O_CARTERA = "edificio_o_cartera"  # definido caso a caso (Auditor)

# Los 8 roles del Documento General, sección 3 / Documento Técnico, sección 5.1.
ROLES = (
    "admin_general",
    "admin_consorcio",
    "encargado",
    "propietario",
    "inquilino",
    "proveedor",
    "auditor",
    "seguridad",
)

# Matriz de roles — transcripción directa de la tabla del Documento Técnico,
# sección 6.2. Cada endpoint futuro consulta esta matriz, nunca inventa su
# propia regla de visibilidad financiera o de alcance.
MATRIZ_ROLES = {
    "admin_general": {
        "alcance": ALCANCE_CARTERA,
        "ve_financiero_unidad": False,
        "ve_financiero_edificio": True,
        "solo_lectura": False,
    },
    "admin_consorcio": {
        "alcance": ALCANCE_EDIFICIO,
        "ve_financiero_unidad": False,
        "ve_financiero_edificio": True,
        "solo_lectura": False,
    },
    "encargado": {
        "alcance": ALCANCE_EDIFICIO,
        "ve_financiero_unidad": False,
        "ve_financiero_edificio": False,  # solo semáforo general, sin montos (Documento Técnico, sección 1.1)
        "solo_lectura": False,
    },
    "propietario": {
        "alcance": ALCANCE_UNIDAD,
        "ve_financiero_unidad": True,
        "ve_financiero_edificio": False,
        "solo_lectura": False,
    },
    "inquilino": {
        "alcance": ALCANCE_UNIDAD,
        "ve_financiero_unidad": False,  # por defecto — habilitable por excepción recién en la Fase 11
        "ve_financiero_edificio": False,
        "solo_lectura": False,
    },
    "proveedor": {
        "alcance": ALCANCE_OTS_ASIGNADAS,
        "ve_financiero_unidad": False,
        "ve_financiero_edificio": False,
        "solo_lectura": False,
    },
    "auditor": {
        "alcance": ALCANCE_EDIFICIO_O_CARTERA,
        "ve_financiero_unidad": True,
        "ve_financiero_edificio": True,
        "solo_lectura": True,
    },
    "seguridad": {
        "alcance": ALCANCE_EDIFICIO,
        "ve_financiero_unidad": False,
        "ve_financiero_edificio": False,
        "solo_lectura": False,
    },
}


def rol_valido(rol):
    return rol in MATRIZ_ROLES


def _dato_rol(rol, clave):
    if not rol_valido(rol):
        raise ValueError(f"Rol desconocido: {rol!r}. Roles válidos: {ROLES}")
    return MATRIZ_ROLES[rol][clave]


def alcance_de(rol):
    return _dato_rol(rol, "alcance")


def ve_financiero_unidad(rol):
    return _dato_rol(rol, "ve_financiero_unidad")


def ve_financiero_edificio(rol):
    return _dato_rol(rol, "ve_financiero_edificio")


def es_solo_lectura(rol):
    return _dato_rol(rol, "solo_lectura")


def tiene_acceso_a_edificio(rol, edificios_del_usuario, edificio_id):
    """Regla central de alcance: ¿este rol, vinculado a estos edificios,
    puede operar sobre `edificio_id`?

    - Administrador General: siempre sí (alcanza toda la cartera).
    - Cualquier otro rol: solo si `edificio_id` está entre los edificios a
      los que el usuario está vinculado (tabla `usuario_edificio`, Fase 1).

    Esta función no toca la base de datos: recibe la lista de edificios ya
    resuelta (el JWT del usuario la va a traer adentro) y responde con una
    regla pura, fácil de testear sin necesidad de una base de datos real.
    """
    if alcance_de(rol) == ALCANCE_CARTERA:
        return True
    return edificio_id in edificios_del_usuario

"""Lógica de generación de estructura vacía de un edificio.

Documento General, sección 5.1: al dar de alta un edificio, indicando
cantidad de pisos y unidades por piso, se genera automáticamente su
estructura vacía (pisos + departamentos, sin propietario todavía) — en vez
de cargarla a mano piso por piso. Esta es la regla, en Python puro, sin
tocar la base de datos ni HTTP: la próxima tarea de esta fase (modelos
`Piso`/`Departamento`) y la de después (endpoint de alta) van a reutilizarla
para escribir las filas reales.

Convención de numeración e identificadores — igual a la del mockup
aprobado (`Mockup_3D_Vidrio_Grafito.html`, `buildingData`): el piso 1 es la
planta más baja (numeración ascendente), y cada departamento se identifica
como "{número de piso}{letra}" (7A, 7B, 7C, 7D, ...), con letras A-Z en
orden. Máximo 26 unidades por piso — a partir de 27 haría falta un segundo
esquema de nombrado (AA, AB, ...) que no está en alcance hoy.
"""

import string

MAXIMO_UNIDADES_POR_PISO = len(string.ascii_uppercase)  # 26


def generar_estructura_vacia(cantidad_pisos: int, unidades_por_piso: int) -> list[dict]:
    """Devuelve la lista de pisos con sus departamentos vacíos:
    [{"numero": 1, "departamentos": ["1A", "1B", ...]}, {"numero": 2, ...}, ...]

    No escribe nada en la base — es responsabilidad de quien la llame
    (el endpoint de alta, en una tarea posterior) crear las filas reales
    de `Piso` y `Departamento` a partir de este resultado.
    """
    if cantidad_pisos < 1:
        raise ValueError("La cantidad de pisos debe ser al menos 1")
    if unidades_por_piso < 1:
        raise ValueError("La cantidad de unidades por piso debe ser al menos 1")
    if unidades_por_piso > MAXIMO_UNIDADES_POR_PISO:
        raise ValueError(f"No se pueden generar más de {MAXIMO_UNIDADES_POR_PISO} unidades por piso (A-Z)")

    letras = string.ascii_uppercase[:unidades_por_piso]
    return [
        {
            "numero": numero_piso,
            "departamentos": [f"{numero_piso}{letra}" for letra in letras],
        }
        for numero_piso in range(1, cantidad_pisos + 1)
    ]

"""Configuración central del backend: rutas, orígenes CORS y secretos.

Valores fijos por ahora (proyecto en etapa de desarrollo, sin variables de
entorno todavía) - si más adelante hace falta separarlos por entorno
(desarrollo/producción), este es el único archivo que cambia.
"""

from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parent.parent.parent
RUTA_BASE_DATOS = RAIZ_BACKEND / "smart_building.db"

NOMBRE_APP = "SMART Building API"

# Puertos de convención del proyecto: backend en 8000, frontend estático en
# 8090 (README.md, en la raíz del proyecto, explica cómo levantar cada uno a mano).
ORIGENES_CORS = [
    "http://127.0.0.1:8090",
    "http://localhost:8090",
]

# Nota de seguridad (Documento Técnico, sección 19): este secreto es válido
# únicamente para el modo test de este proyecto. Antes de un despliegue real
# (Fase 13, Roadmap) se reemplaza por un valor generado y fuera del código.
JWT_SECRETO = "smart-building-dev-secret-no-usar-en-produccion"
JWT_ALGORITMO = "HS256"
JWT_MINUTOS_EXPIRACION = 60

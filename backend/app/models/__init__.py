"""Modelos de SQLAlchemy — un archivo por dominio.

Un modelo puede importar constantes de un servicio (para declarar sus
CheckConstraint contra la misma lista de valores validos). La dependencia
inversa esta prohibida: crearia un ciclo de imports.

====================================================================
ESTE ARCHIVO ES, ADEMAS, EL MODULO AGREGADOR
====================================================================

`core/migraciones.py` importa este paquete antes de crear el esquema, y ese
import es lo que registra las tablas en `Base.metadata`.

**Todo modelo nuevo se agrega abajo, en la misma tarea que lo crea.** Un
modelo que no este importado aca no existe para SQLAlchemy al arrancar: su
tabla no se crea, y el error no aparece al iniciar sino al primer uso, lejos
de la causa y con un mensaje que no menciona este archivo.

El orden de los imports no importa: las relaciones entre modelos se resuelven
por nombre, despues de que todos esten cargados.
"""

# Los modelos se van sumando fase por fase. Fase 1: Usuario y la estructura
# del edificio. Todavia no hay ninguno.
__all__: list[str] = []

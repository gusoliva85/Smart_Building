"""Migraciones que hay que correr a mano, una vez por base de datos.

============================================================================
POR QUE EXISTE ESTA CARPETA
============================================================================

`core/migraciones.py` corre al arrancar la aplicacion y es **puramente
aditiva**: crea tablas que faltan y agrega columnas que faltan, y nada mas.
Esa limitacion es deliberada y esta documentada en su propio modulo — es la
unica forma de que una sincronizacion automatica sea segura contra una base
con datos.

La consecuencia es que hay una clase de cambio que ese mecanismo **no hace y
tampoco avisa que no hizo**: modificar algo que ya existe. Un CHECK nuevo
sobre una columna existente, un tipo distinto, una clave foranea agregada
despues. Contra una base cuyo esquema no coincide con los modelos, la
aplicacion arranca igual, informa "sin cambios" y trabaja contra una forma que
no es la que declaro.

Eso no es teorico. La primera migracion de esta carpeta nacio justamente de
ahi: el registro publico de `F1-T16A` devolvia **202 sin crear nada** contra la
base de desarrollo, porque su tabla `usuarios` tenia el CHECK de ocho roles
—se habia creado antes de que existiera `pendiente`— y la aplicacion no tenia
forma de notarlo.

============================================================================
LAS REGLAS
============================================================================

1. **Un archivo por migracion, numerado** (`m001_`, `m002_`, ...). El numero
   fija el orden y hace visible el conjunto completo de un vistazo.
2. **Cada una es idempotente**: mira el estado real de la base y, si el cambio
   ya esta, no hace nada y lo dice. Correrla dos veces tiene que ser seguro,
   porque nadie se acuerda de cual corrio en que base.
3. **Cada una funciona en SQLite y en PostgreSQL.** Desarrollo es SQLite y
   produccion es Supabase; una migracion que ande en una sola es media
   migracion.
4. **Nunca se corren solas.** No se enganchan al arranque de la aplicacion: se
   ejecutan a mano, con la base elegida a conciencia, igual que el seed.

        cd backend
        venv\\Scripts\\python.exe -m app.migraciones_manuales.m001_rol_pendiente

   Y para produccion, con `DATABASE_URL` apuntada al pooler de Supabase, lo
   mismo que el seed — con el mismo cuidado de cerrar esa terminal despues.

5. **Se anota en el README** cuales hay que correr y en que momento, porque el
   que clona el repositorio no las va a adivinar.

============================================================================
CUANDO ESTO DEJE DE ALCANZAR
============================================================================

Esta carpeta es el minimo honesto para un proyecto sin datos de clientes. El
dia que haya informacion real que no se pueda perder, el reemplazo es Alembic
—que lleva el registro de que migracion corrio en que base, que es justamente
lo que aca lo lleva una persona acordandose—. Antes de eso seria
infraestructura sin uso.
"""

# SMART Building (ver_4) — reglas de trabajo del proyecto

Este archivo lo lee cualquier asistente al abrir el repositorio, en todas las sesiones y
sin que nadie se lo pida. Está acá para que las reglas que no se pueden olvidar no
dependan de que yo me acuerde de repetirlas.

La fuente de verdad completa es `documentacion/05_Roadmap.md`, sección 1. Esto es el
resumen de lo que no se negocia.

---

## 1. Los datos de producción no se tocan sin avisar

**Regla, y la más importante de este archivo.** Antes de ejecutar algo que escriba,
borre, migre o reinicie datos del entorno de producción —o que pueda hacerlo como
efecto colateral— **se explica qué se va a tocar, qué se puede perder y cómo se vuelve
atrás**, y no se ejecuta hasta tener mi respuesta. Se avisa aunque el riesgo parezca
chico y aunque los datos parezcan descartables.

**El motivo, escrito ahora que todavía no duele.** Hoy lo que hay en producción son
datos de prueba y perderlos cuesta una tarde. Pero este sistema se prueba cargando a
mano un edificio entero: propietarios, inquilinos, alquileres, gastos de varios meses,
expensas ya generadas, pagos conciliados, deudores con su antigüedad, fichas y
reclamos con su historial. Eso es trabajo de días que ningún script reconstruye. El
momento de escribir esta regla es antes de tener esos datos, no después de borrarlos.

**Qué cuenta como tocar producción:**

- Correr migraciones o cualquier cambio de esquema contra la base de Supabase.
- `DELETE`, `UPDATE` o `TRUNCATE` sin un `WHERE` acotado y verificado.
- Recrear, resembrar o vaciar tablas.
- Cambiar variables de entorno del despliegue.
- Cualquier script de arreglo escrito a las apuradas.

**El mecanismo aditivo de arranque (`core/migraciones.py`) no es una excusa.** Hoy
agrega tablas y columnas que faltan y no borra nada, pero eso lo vuelve seguro solo
mientras nadie le agregue un paso que sí borre.

**La forma segura, cuando igual hay que hacerlo:** se prueba primero contra la base
local de desarrollo, se cuenta cuántas filas se van a ver afectadas **antes** de
ejecutar nada, y lo que se toca se toca una vez y se verifica.

## 2. Git lo manejo yo

**Nada se commitea ni se sube.** Ni `commit`, ni `push`, ni `merge`, ni ramas nuevas.
Los cambios quedan en el árbol de trabajo y yo decido qué entra y cuándo.

## 3. Una tarea por vez, y la apruebo yo

El Roadmap se recorre en orden. Se implementa **una sola tarea**, se explica qué se
hizo y cómo probarlo, y **se tilda recién después de mi aprobación explícita**. Sin esa
aprobación no se avanza a la siguiente. Si algo se puede mejorar, se propone y se
espera; no se hace por las dudas.

## 4. Si algo está mal, se dice

Además de hacer la tarea pedida, se señala lo que esté mal o se pueda mejorar en lo que
se toca. El Roadmap es viejo y tiene huecos: encontrarlos es parte del trabajo, y una
inconsistencia se revisa contra lo que viene más adelante antes de resolverla.

**Y toda decisión que se tome queda asentada en la tarea del Roadmap que la
implementa**, no en el chat y no en una lista suelta al final. Lo que no está escrito
en el Roadmap, no existe.

**Pero corta.** Una nota de tarea en el Roadmap son viñetas de una o dos líneas, y
**ninguna línea pasa de 120 caracteres**. La explicación larga de una decisión va en
el docstring del módulo que la implementa, que es donde la va a leer quien toque ese
código: repetirla en el Roadmap es escribirla dos veces y deja el archivo ilegible.
Ya pasó — las notas de la Fase 2 llegaron a párrafos de 1.300 caracteres en una sola
viñeta y la fase pasó de 15.000 a 94.000 caracteres. Se reescribió el 2026-11-13.

## 5. Cómo se escribe

- **La documentación va en primera persona, como si la hubiera escrito yo.** Sin rastros
  de asistente, sin emojis en ninguna parte.
- **Comentarios y docstrings del backend, sin tildes.** Texto que ve un usuario, con
  tildes y bien escrito.
- **Ningún secreto entra al repositorio ni pasa por la conversación** (`F05-T04`).
- Todo mensaje de error que ve un usuario sale de `core/errores.py`, y ninguno menciona
  tablas, columnas, consultas ni nombres de archivo (`FX-T11`).
- `entrega_tp1/` no admite contenido generado con IA.

## 6. Cómo se me informa

Conclusión primero y respuestas cortas. Sin vocabulario interno. Y los scripts de
prueba o de verificación que se escriben al pasar no se mezclan nunca con el estado
real del producto: si algo se probó con datos inventados, se dice que son inventados.

## 7. Entorno

- El intérprete del proyecto es `backend/venv/Scripts/python.exe`. Un `python` pelado
  falla (`ImportError: email-validator`).
- SQLite en desarrollo, PostgreSQL (Supabase) en producción. Despliegue en Vercel.
- Antes de dar una tarea por terminada se corre la **suite completa**, no solo el
  archivo nuevo.
- El frontend no tiene paso de compilación: los archivos que se editan son los que se
  sirven. Todo lo visual sale de la skill `premium-uiux`, que es obligatoria antes de
  tocar una sola línea de pantalla.
- **Antes de dar por terminada una pantalla se corre
  `python frontend/verificar_pantallas.py`.** Atrapa la clase de error que no falla y
  solo se ve mal: una clase inventada, un modificador usado solo, un modal que se abre
  invisible, un botón sin su clase de ancho. Y antes de escribir un componente nuevo,
  buscar uno igual en `usuarios.html` o `edificios.html` y copiar el `class` entero.

# Prorrateo de gastos — investigación legal y criterio adoptado

> **Qué es este documento.** El Roadmap (Fase 2, Tarea 1) advierte que el criterio de prorrateo es "la pieza más delicada del módulo financiero, porque un error afecta a todos los propietarios a la vez". Antes de escribir una sola línea de código se investigó cómo funciona realmente la distribución de gastos comunes en un consorcio argentino, y este documento deja registradas esa investigación y la decisión de diseño que salió de ella — separado del Documento General y el Documento Técnico porque es un tema con entidad propia (legal, no solo funcional) que **probablemente se revise más de una vez** a medida que el módulo financiero crezca. Cualquier cambio futuro al criterio de prorrateo actualiza primero este documento, y recién después el código — mismo orden que ya sigue el resto del proyecto (lógica → backend → frontend).
>
> Referencias cruzadas: Documento General, sección 6.1 · Documento Técnico, sección 8 · Roadmap, Fase 2 Tarea 1 · `que_hice.html`, slide `f2-t1` · código en `backend/app/services/finanzas.py`.

---

## 1. Marco legal (Argentina)

### 1.1 De dónde sale la norma

La propiedad horizontal en Argentina se rigió originalmente por la **Ley 13.512** (1948). Esa ley fue derogada como cuerpo independiente y sus reglas se incorporaron, actualizadas, al **Código Civil y Comercial de la Nación** (vigente desde 2015), **Libro Cuarto, Título V — "Propiedad Horizontal"**, artículos **2037 a 2072**.

### 1.2 La regla central: el porcentual, no un criterio global

El punto que cambia el diseño original de este proyecto: la ley **no establece un criterio de prorrateo elegible libremente** (del tipo "partes iguales" o "por m², a elección del edificio"). Lo que establece es que **cada unidad funcional tiene un porcentual fijo**, calculado (en general, en base a la superficie relativa de la unidad respecto del total del edificio) **al momento de redactar el reglamento de propiedad horizontal**, y registrado ahí. Ese porcentual:

- Es lo que efectivamente se usa para prorratear los **gastos comunes ordinarios** (administración, mantenimiento, reparación de partes comunes, y las obligaciones que la ley/el reglamento/la asamblea le imponen al administrador).
- **No se recalcula solo** en cada liquidación — es un dato fijo del edificio, que solo cambia si el reglamento mismo se modifica (ver 1.4).
- Es el dato **legalmente vinculante**, más allá de cómo se haya originado el número (m², valor de mercado al momento de construir, u otro criterio que decidieron los propietarios originales).

### 1.3 Quién está obligado a pagar

El Código Civil y Comercial amplía respecto de la vieja Ley 13.512: no es solo el propietario de la unidad funcional el obligado a las expensas — también quienes son **poseedores por cualquier título** (por ejemplo, un inquilino puede quedar alcanzado según cómo esté armado el contrato/reglamento). Para el alcance actual de SMART Building esto no cambia el diseño del prorrateo en sí (que sigue siendo por unidad, vía el propietario asociado al departamento) pero es relevante para el módulo de Pagos más adelante.

### 1.4 Excepciones por rubro (caso real, fuera de alcance por ahora)

El caso más citado en la práctica: **las unidades de planta baja pueden no pagar el gasto de ascensor**. La ley no lo impone de manera automática — depende de que:

- Esté **expresamente pactado en el reglamento de propiedad horizontal**, o
- Se **modifique por unanimidad** en una asamblea de propietarios, o
- Se resuelva judicialmente ante un conflicto.

Esto confirma que el criterio de prorrateo **puede variar por rubro dentro de un mismo edificio** — no es necesariamente un único coeficiente aplicado a absolutamente todos los gastos por igual. Es una funcionalidad real y contemplada por la ley, pero **se decidió, consultado con el usuario, dejarla fuera del alcance de esta primera tarea** — ver sección 4.

---

## 2. Fuentes consultadas

| Fuente | Qué aportó |
|---|---|
| [ARTS. CODIGO CIVIL Y COMERCIAL — Título V, Propiedad horizontal](https://www.cpcesfe2.org.ar/wp-content/uploads/2019/03/4305-Codigo_Civil_y_Comercial_TituloV.pdf) | Texto de los artículos 2037 y siguientes — base legal directa. |
| [Ley simple: Propiedad horizontal — Argentina.gob.ar](https://www.argentina.gob.ar/justicia/derechofacil/leysimple/propiedad-horizontal) | Explicación en lenguaje llano del régimen vigente, confirma la vigencia del CCyC sobre la Ley 13.512 derogada. |
| [Cómo se calculan las expensas de un consorcio — Ramos Estudio](https://www.ramosestudio.com.ar/blog/como-se-calculan-las-expensas-consorcio/) | Confirma el mecanismo del porcentual fijo por unidad como base del cálculo real usado en la práctica administrativa. |
| [¿Las plantas bajas pagan el ascensor de la comunidad de propietarios? — Idealista](https://www.idealista.com/news/inmobiliario/vivienda/2024/01/18/810420-tengo-que-pagar-el-ascensor-si-vivo-en-un-bajo) | Caso concreto de excepción por rubro y sus condiciones (reglamento / unanimidad / vía judicial). |

---

## 3. Qué decidimos tomar para SMART Building

| Decisión | Por qué |
|---|---|
| Cada `Departamento` tiene un **`coeficiente`** propio (%), no un criterio global de edificio. | Es el mecanismo real y legalmente vinculante (sección 1.2) — un criterio global tipo "este edificio usa partes iguales" no es fiel a cómo funciona un reglamento de propiedad horizontal real. |
| Los coeficientes de **todas** las unidades de un edificio deben sumar exactamente 100%. | Si no suman 100%, el prorrateo reparte de más o de menos entre propietarios reales — se valida antes de calcular nada (`validar_coeficientes`). |
| **"Partes iguales"** y **"por m²"** existen solo como **atajos de carga inicial** (no como el criterio en sí). | Sirven para no obligar a tipear 20 porcentuales a mano al dar de alta un edificio nuevo — pero el admin puede (y en la práctica va a necesitar) ajustar cualquier unidad después, porque el reglamento real casi nunca es matemáticamente parejo. |
| El coeficiente queda como un **dato editable por unidad**, no un cálculo que se rehace solo. | Coincide con la sección 1.2: el porcentual es fijo hasta que el reglamento cambie — no se recalcula en cada liquidación. |
| Visible y editable desde una pantalla de **Configuración**, para Administrador General (cualquier edificio) y Administrador de Consorcio (el suyo). | Pedido explícito del usuario — coincide además con quién tiene autoridad real sobre el reglamento en la práctica. |
| El **prorrateo de un monto** nunca pierde centavos por redondeo: todas las unidades menos la última se redondean normal; la última recibe el **resto exacto** (total menos la suma de las demás), no su parte redondeada. | Repartir dinero por porcentaje y redondear cada parte por separado puede dejar centavos sin asignar (de más o de menos) respecto al total real — inaceptable en un módulo financiero. |

### Explícitamente fuera de alcance (por ahora)

**Excepción de prorrateo por rubro** (ej. ascensor sin planta baja, sección 1.4). Es real, está contemplada por la ley, y probablemente se implemente más adelante — pero se decidió, consultado con el usuario, no incluirla en el diseño inicial para no volver la primera tarea de la fase innecesariamente grande. La base actual (coeficiente por unidad + función pura de prorrateo) **no bloquea** agregar esto después: la forma más directa sería que un `Gasto` pueda declarar su propio subconjunto de unidades participantes y/o coeficientes propios, cayendo al coeficiente general del edificio cuando no se especifique nada distinto.

---

## 4. Estado de la implementación

Implementado como lógica pura, sin modelos ni base de datos todavía (mismo patrón que `services/edificios.py` para la estructura vacía del edificio en la Fase 1) — `backend/app/services/finanzas.py`:

| Función | Qué hace |
|---|---|
| `validar_coeficientes(coeficientes)` | Confirma que una lista de coeficientes suma 100% (con una tolerancia mínima para redondeo, no para errores reales). |
| `calcular_partes_iguales(cantidad_unidades)` | Atajo: reparte 100% en partes iguales. |
| `calcular_por_metros_cuadrados(metros_cuadrados)` | Atajo: coeficiente proporcional a la superficie de cada unidad. |
| `prorratear_gasto(monto_total, coeficientes)` | Reparte un monto real entre unidades según sus coeficientes, sin perder centavos por redondeo. |

Verificado con 18 tests (`backend/tests/test_servicio_finanzas.py`), incluyendo el caso crítico de reparto no exacto (repartir $100 entre tres partes de 33,33...% y confirmar que la suma da $100,00 justo) y un caso realista con 7 unidades y un monto con decimales. Suite completa del backend: 105/105.

## 5. Lo que falta (próximas tareas de la Fase 2)

- Agregar el campo `coeficiente` al modelo `Departamento` (hoy no existe — esta tarea fue deliberadamente "antes de tocar modelos").
- Modelos `Gasto`, `Expensa`, `ExpensaDetalle`.
- Servicio de prorrateo automático (`services/finanzas.py` va a crecer acá) que llame a `prorratear_gasto()` con los coeficientes reales de la base.
- Pantalla de Configuración donde Administrador General/de Consorcio vean y editen los coeficientes por unidad.
- (Más adelante, fuera de esta fase) excepción de prorrateo por rubro.

---

*Última actualización: aprobado el diseño inicial (coeficiente por unidad + atajos de carga) — 2026-09-03. Este documento se actualiza antes que el código cada vez que el criterio de prorrateo cambie.*

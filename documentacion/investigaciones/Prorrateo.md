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

- ~~Pantalla de Configuración donde Administrador General/de Consorcio vean y editen los coeficientes por unidad~~ — **resuelto el 2026-09-08**, ver sección 7.
- (Más adelante, fuera de esta fase) excepción de prorrateo por rubro.

## 6. Cómo se persiste el monto por departamento (Tarea 8: generación de expensa mensual)

Antes de implementar el endpoint `POST /api/edificios/{id}/expensas`, apareció una pregunta de diseño real: `calcular_prorrateo_periodo()` (Tarea 7) devuelve cuánto le toca a cada departamento, pero **nada lo guardaba todavía** — ni `Expensa` ni `ExpensaDetalle` (que es por rubro, no por unidad) tienen dónde poner ese número.

**La pregunta:** ¿se guarda ese monto como una foto fija al generar la expensa, o se recalcula en el momento cada vez que hace falta mostrarlo (ej. el "estado de cuenta por unidad" del Documento General 6.2)?

**Investigado:** la práctica estándar de facturación (Stripe, Zuora, y la literatura de billing en general) es unánime: una liquidación ya generada **es inmutable** — se guarda una foto fija de cada monto al momento de emitirla, nunca se recalcula después con datos que cambiaron. Aplicar reglas/coeficientes actuales a un período pasado da resultados incorrectos; si algo estuvo mal, se corrige con un ajuste nuevo (nota de crédito/reliquidación), nunca reescribiendo la expensa original. Es exactamente el mismo motivo por el que este proyecto ya decidió (sección 3) que el coeficiente "no se recalcula solo en cada liquidación" — acá es la misma lógica aplicada un nivel más abajo, al monto ya liquidado de cada unidad.

**Decisión:** se agrega el modelo `ExpensaDepartamento` (`expensa_id`, `departamento_id`, `monto`, `UniqueConstraint` para que cada departamento tenga como máximo una fila por expensa) — la foto fija de lo que le tocó pagar a esa unidad en ese período exacto, calculada una sola vez al generar la expensa. Si el coeficiente de un departamento cambia después, las expensas viejas quedan tal cual se emitieron; solo las nuevas usan el coeficiente nuevo. Es también la pieza que la futura tarea de "cálculo de deudores" va a necesitar (comparar esto contra la suma de `Pago` de ese departamento+expensa).

Sources:
- [Usage-Based Billing for AI Companies — Stripe](https://stripe.com/resources/more/ai-companies-and-usage-based-billing)
- [Taxable Item Snapshot — Zuora Knowledge Center](https://knowledgecenter.zuora.com/Zuora_Central/Billing_and_Payments/J_Billing_Operations/L_Taxes/Taxable_Item_Snapshot)

### Cerrado en esta actualización

- **`Departamento.coeficiente`**: agregado (`Numeric(6,3)`, `CHECK` de rango 0-100, nace en `NULL`). Como la tabla `departamentos` ya tenía filas reales (65 en desarrollo, datos reales en producción), hizo falta un mecanismo de migración que el proyecto no tenía — ver `core/migraciones.py` y la nota técnica abajo.
- **`services/finanzas.py::calcular_prorrateo_periodo(db, edificio_id, anio, mes)`**: la versión automática ya anticipada acá — resuelve el monto real (suma de `Gasto` del período) y los coeficientes reales de la base, y llama a `prorratear_gasto()`. Único punto del archivo que toca la base (el resto sigue siendo lógica pura).
- Verificado de punta a punta contra la base real de desarrollo (no solo tests en memoria): edificio real de 12 departamentos, coeficientes cargados con el atajo de partes iguales, 3 gastos reales de un período — el prorrateo devuelto suma exactamente el total de gastos, sin perder un centavo.

### Nota técnica: por qué hizo falta `core/migraciones.py`

`Base.metadata.create_all()` (lo único que este proyecto usa para el esquema, sin Alembic) crea tablas que no existen, pero **no les agrega columnas nuevas a tablas que ya existen**. Hasta esta tarea nunca hizo falta nada más porque cada modelo nuevo fue siempre una tabla nueva — `coeficiente` es la primera columna que se suma a una tabla vieja con datos reales. Se resolvió con un helper mínimo (`agregar_columnas_faltantes`, ver `que_hice.html`) que compara columnas del modelo contra la tabla real y agrega solo las que faltan, con `ALTER TABLE`. Detalle importante encontrado al escribir sus tests: el `CheckConstraint` de `coeficiente` tiene que declararse pegado a la columna (no en `__table_args__`), porque solo así viaja en el propio `ADD COLUMN` — la única forma en que SQLite acepta un `CHECK` agregado después de crear la tabla.

## 7. La pantalla de Configuración de coeficientes — construida (2026-09-08)

Se descubrió al usar la app de verdad: el usuario intentó generar la expensa de un edificio de prueba distinto al que se venía usando en las demás tareas de la Fase 2 (ese sí tenía coeficientes, cargados a mano en la base durante el desarrollo) y recibió `"Hay departamentos sin coeficiente cargado: ..."`. La causa real no era un dato faltante puntual: **nunca existió ningún endpoint ni pantalla para cargar `coeficiente`** — la sección 5 de este documento ya lo marcaba como pendiente, pero quedó pendiente en silencio hasta que una prueba real lo encontró.

**Resuelto:**
- `PATCH /api/edificios/departamentos/{id}/coeficiente` — edición manual de un departamento por vez, siempre disponible (incluso después de autocompletar).
- `POST /api/edificios/{id}/coeficientes/auto` — completa TODOS los departamentos del edificio de una vez, con los dos atajos ya anticipados en la sección 3 (partes iguales / por m²), reutilizando `calcular_partes_iguales()`/`calcular_por_metros_cuadrados()` de `services/finanzas.py` sin cambiarles la lógica.
- Frontend: `edificios.html`, pestaña Estructura — cada departamento muestra su coeficiente y un botón para editarlo; un botón "Autocompletar coeficientes" arriba de la lista; un resumen en vivo ("Coeficientes: 28/28 unidades · suma 100.00% ✓") para que el Administrador vea de un vistazo si el edificio ya está en condiciones de generar una expensa, sin sumarlo a mano.

**Bug real encontrado al verificar con un edificio de 28 unidades (no divide exacto):** `calcular_partes_iguales()`/`calcular_por_metros_cuadrados()` redondeaban a 4 decimales, pero `Departamento.coeficiente` es `Numeric(6,3)` — solo 3. Cada valor calculado se truncaba un decimal al guardarse, y la suma real en la base dejaba de dar 100% (99.989% en el caso de 28 unidades) aunque la función, en memoria, sí sumara exacto. El "la última unidad se lleva el resto exacto" que garantiza la suma perfecta solo funciona si el redondeo interno coincide con la precisión real de guardado — se corrigió pasando ambas funciones a 3 decimales (`DECIMALES_COEFICIENTE`), y se agregó un test de regresión que verifica la suma ya persistida (no la que devuelve la función en memoria) con una cantidad de unidades que no divide exacto.

---

*Última actualización: se construye la pantalla de Configuración de coeficientes (edición manual + autocompletado) y se corrige un bug real de precisión decimal en la persistencia — 2026-09-08. Este documento se actualiza antes que el código cada vez que el criterio de prorrateo cambie.*

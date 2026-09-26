# Documento de Frontend y Sistema de Diseño — SMART Building

> **Estado del documento:** nuevo, creado el **2026-09-25**. Reúne en un solo lugar todo lo relativo a la interfaz: identidad visual, tokens, catálogo de componentes, arquitectura de pantallas, módulos de JavaScript compartidos, reglas de interacción y errores conocidos.
>
> **Por qué existe.** Antes esto vivía disperso en tres lugares: una sección del Documento Técnico, la skill `premium-uiux` y el propio código. Durante la construcción de las Fases 0 a 3 el sistema visual creció mucho más de lo que preveía aquella sección —de una sola pantalla de dashboard a un vocabulario completo de más de 100 clases y 17 módulos de JavaScript—, con decisiones tomadas sobre errores reales. Nada de eso podía seguir siendo "una subsección".
>
> **Qué NO es este documento.** No es la skill. **El contrato visual del proyecto es `.claude/skills/premium-uiux/`** — la skill es la fuente de verdad y se carga automáticamente antes de tocar cualquier pantalla. **Este documento es la versión legible y completa para una persona**: lo que hay que leer para entender cómo se ve y cómo se comporta la aplicación, sin abrir el código.
>
> **Sobre los mockups.** La carpeta `documentacion/mockups/` es exploración visual histórica y **no manda sobre nada**: su contenido ya fue absorbido por la skill y por este documento. No se consulta para construir una pantalla.
>
> **Regla de sincronización:** si una regla de acá cambia, cambia también en la skill, y viceversa. Son dos formatos del mismo contrato, no dos fuentes de verdad.

---

## 1. Las dos fuentes y qué manda cada una

| Fuente | Qué es | Autoridad |
|---|---|---|
| `.claude/skills/premium-uiux/` | El sistema de diseño en formato ejecutable, con sus dos referencias (`paleta-color.md`, `componentes.md`). | **Contrato visual y obligatoria en ejecución.** Se carga antes de crear o tocar cualquier pantalla, y ante una duda de aspecto, gana la skill. |
| Este documento | La especificación completa y razonada, con el porqué de cada decisión y las lecciones aprendidas. | **Referencia para entender.** Es lo que se lee para diseñar algo nuevo. |

**Regla de oro, común a las dos:** ante un componente nuevo, la pregunta correcta no es *"¿cómo lo diseño?"* sino **"¿cuál de los patrones ya definidos uso acá?"**. Si de verdad no existe, se deriva uno de los mismos tokens y **se agrega al catálogo** (sección 5 de este documento y `componentes.md` de la skill) para que la próxima pantalla lo reutilice. La consistencia es el producto: el usuario que pasa de Reclamos a Financiero a Activos tiene que sentir que es la misma aplicación, no tres experimentos.

---

## 2. Identidad visual

### 2.1 Los tres pilares

1. **Vidrio auténtico en dos capas, no `backdrop-blur` suelto.** La lección de diseño más importante del sistema, tomada de las guías de Apple *Liquid Glass*: **el vidrio no va debajo de contenido denso.** Un blur fuerte se ve espectacular detrás de un titular, y vuelve ilegible una grilla de texto chico. De ahí dos niveles, no uno (sección 2.3).
2. **Un solo acento de marca — acero/grafito — deliberadamente fuera de la familia del semáforo.** Si el acento se pareciera a "verde" o "rojo", el usuario confundiría una interacción de marca (un botón activo, un enlace) con un estado real del edificio. Es una decisión funcional, no estética.
3. **El Dashboard Visual del Edificio es intocable en su arquitectura.** Es el diferencial del producto (sección 6). Su jerarquía de contenedores no se improvisa: romperla rompe el layout responsive.

### 2.2 Antipatrones prohibidos

Son la estética "por defecto" a la que converge cualquier generador de interfaces dejado a su criterio. **Ninguno tiene excepción en este proyecto.**

1. **Ningún morado, lila o violeta**, ni solo ni en degradé. No forma parte de la identidad.
2. **Ningún color primario genérico de librería** (azules e índigos de manual). Todo color sale de los tokens.
3. **Ninguna tarjeta "de catálogo"** (`border gris + rounded-lg + shadow-md` repetido en todos lados). Las superficies son vidrio en dos capas con brillo especular y sombra compuesta.
4. **Cero emojis**, en ningún lado: ni interfaz, ni textos, ni comentarios de código. Todo ícono es SVG inline dibujado a mano (`viewBox="0 0 24 24"`, `fill="none"`, `stroke="currentColor"`, `stroke-width` 1.7–1.9, extremos redondeados).
5. **Nunca `Inter` en titulares, números grandes o marca** — eso es `Outfit`. Inter es solo cuerpo, labels e inputs.
6. **Nada de *hero* centrado con texto en degradé sobre un blob difuminado.** Esto es una herramienta de trabajo densa en datos, no una landing.
7. **Nada de animaciones elásticas o con rebote.** Todo es `ease-out`, sutil, 180–340 ms. El hover eleva 1–2 px o ilumina; nunca rebota.
8. **Nada de grillas de tarjetas idénticas sin jerarquía.** Los KPI usan composición tipo *bento*.
9. **Nunca estética gamer o cyberpunk** (neón, glow saturado), tampoco en tema oscuro.
10. **Prohibido `border-left: 3px solid` (o `border-top`) para indicar estado.** Es el tic visual del dashboard genérico. El semáforo se comunica con **borde completo en los 4 lados + sombra proyectada del mismo color** (sección 2.4).
11. **Nunca inventar un botón, ícono o badge "para esta pantalla".**

### 2.3 El sistema de vidrio en dos capas

| Nivel | Cuándo | Blur | Opacidad (claro) | Ejemplos |
|---|---|---|---|---|
| **`.shell`** | Contenedores grandes, de navegación, poca densidad de texto | 22 px | ~52% | Topbar, sidebar, cada tarjeta KPI, contenedor del Dashboard Visual, panel de detalle, modales |
| **`.content-glass`** | Contenido denso **dentro** de un shell | 7 px | ~68% | Tarjetas de departamento, chips de activos, filas de listado, ítems del panel de detalle, tarjetas de opción |

Reglas no negociables:

- **Respaldo `@supports`:** si el navegador no soporta `backdrop-filter` (ni con prefijo), ambos niveles caen a un fondo casi opaco en vez de mostrar un vidrio roto.
- **Brillo especular:** cada `.shell` lleva un `::before` con un barrido diagonal de luz, para que lea como vidrio real y no como un `blur()` plano.
- **Textura de grano:** una capa fija sobre todo el body con ruido SVG al 3,5% y `mix-blend-mode: overlay`. Es lo que da la sensación táctil; sin ella el fondo se ve como un degradé liso.
- **Fondo atmosférico, nunca color plano:** el body lleva tres manchas radiales de color más un degradé vertical, con `background-attachment: fixed`.
- **Vidrio sobre fondo oscuro necesita otro tratamiento.** Un `.shell` está pensado para apoyarse sobre el fondo claro de la página. Un modal se apoya sobre su propio backdrop oscuro, y ahí ese 52% de blanco se mezcla con el negro de abajo y da un gris lavado "sin los colores de la app". Por eso `.modal` pisa el fondo con la variante casi opaca. **Cualquier componente nuevo que combine vidrio con un fondo oscuro detrás necesita el mismo ajuste.**

### 2.4 El semáforo de 4 estados (es una regla de negocio, no una paleta)

| Estado | Token | Significado | Nunca |
|---|---|---|---|
| Verde | `--ok` | Todo correcto | ...se usa como color decorativo |
| Amarillo | `--warn` | Atención: reclamo leve o medio, deuda de un mes, activo por vencer (≤30 días) | ...se confunde con naranja |
| Naranja | `--pend` | Pendiente: hay una orden de trabajo **en curso** | ...se usa como "advertencia genérica"; es exclusivo de mantenimiento en ejecución |
| Rojo | `--crit` | Crítico: reclamo crítico, deuda de más de un mes, activo vencido | ...se reemplaza por un rojo de librería |

- **Precedencia:** ante varios factores a la vez en una misma unidad, gana el más grave: `ok < warn < pend < crit`.
- Los cuatro valores son **idénticos en tema claro y oscuro**: el significado de un estado no cambia según el tema que el usuario eligió.
- **El cálculo del estado nunca se hace en el frontend con datos reales.** La API lo manda calculado (Documento Técnico, 5.6). El frontend solo pinta.
- **Cómo se aplica visualmente** (el patrón obligatorio): la clase de estado define una variable local de color, y el componente la usa en un **borde completo** teñido y una **sombra proyectada** del mismo color, junto con la sombra de vidrio. Nunca una barra lateral.

### 2.5 Tipografía, radios y espaciado

- **Display, titulares, números de KPI y montos:** `Outfit`, pesos 500–800, `letter-spacing: -0.015em`.
- **Cuerpo, labels, inputs:** `Inter`, pesos 400–700.
- Ambas por Google Fonts con fallback a `ui-sans-serif, system-ui, sans-serif`.
- **Nunca serif.** Es una herramienta de gestión, no una pieza editorial.
- **Un monto siempre va en Outfit**, aunque esté dentro de una fila de texto en Inter: los números son "display".
- **Radios:** tarjetas `--r-card` 20 px · paneles grandes y topbar `--r-lg` 24 px · chips e inputs `--r-sm` 12 px · pills y badges 99 px.
- **Espaciado:** múltiplos de 4 px; gaps de grilla de 8 px (mobile) a 10–12 px (desktop).

---

## 3. Tokens de color — el contrato exacto

Viven en `frontend/assets/css/tokens.css`, que **no dibuja nada**: no tiene una sola clase, solo declara variables. Si mañana se ajusta un matiz, se cambia una vez acá y se actualiza en todo el sistema.

**Regla no negociable:** ningún color, sombra o superficie de vidrio se escribe como valor fijo suelto dentro de una regla. Si un componente nuevo necesita "un blanco" o "un negro tenue", usa un token. Los grupos que más se pasan por alto son justamente los que rompen el tema oscuro: **sombras, vidrio y los literales de mezcla** (`--mix-tint`, `--mix-ink`, `--shadow-rgb`).

### 3.1 Tema claro (`:root`)

```css
/* Neutros y superficies */
--bg-1:#f1f2f3; --bg-2:#e9ebec;
--wash-a:#d6dee3; --wash-b:#e6e2d8;
--ink:#1c2024;    --ink-2:#4b5157;
--ink-3:#7c828a;  --ink-4:#a8adb3;
--line:rgba(28,32,36,.10); --line-2:rgba(28,32,36,.07); --line-strong:rgba(28,32,36,.16);

/* Vidrio — dos niveles + respaldo sin backdrop-filter */
--glass-shell-bg:rgba(255,255,255,.52);   --glass-shell-blur:22px;  --glass-shell-fallback:rgba(255,255,255,.92);
--glass-content-bg:rgba(255,255,255,.68); --glass-content-blur:7px; --glass-content-fallback:rgba(255,255,255,.94);
--glass-in:inset 0 1px 0 rgba(255,255,255,.85),inset 0 0 0 1px rgba(255,255,255,.45);
--glass-sheen:linear-gradient(120deg,rgba(255,255,255,.55),transparent 45%);

--navy:#15181b;

/* Acento de marca — acero/grafito, fuera de la familia del semáforo */
--accent:#57768c; --accent-2:#3e5a6d; --accent-soft:#e2e9ed; --accent-ring:rgba(87,118,140,.28);

/* Semáforo funcional */
--ok:#2e8067; --warn:#ba8c1f; --pend:#bd6c2c; --crit:#b13c47;

/* Mezclas y sombras */
--mix-tint:#fff; --mix-ink:#1c2024;
--shadow-rgb:20,22,25;
--sh-sm:0 1px 2px rgba(var(--shadow-rgb),.06), 0 4px 12px -4px rgba(var(--shadow-rgb),.12);
--sh-md:0 2px 6px rgba(var(--shadow-rgb),.07), 0 16px 34px -16px rgba(var(--shadow-rgb),.22);
--sh-lg:0 4px 16px rgba(var(--shadow-rgb),.09), 0 34px 70px -26px rgba(var(--shadow-rgb),.32);

/* Radios */
--r-card:20px; --r-lg:24px; --r-sm:12px;
```

### 3.2 Tema oscuro (`html[data-theme="dark"]`)

```css
--bg-1:#0c0d0e; --bg-2:#0f1011; --wash-a:#1c2529; --wash-b:#221f18;
--ink:#eef0f1;  --ink-2:#bcc0c4; --ink-3:#868b91; --ink-4:#54585d;
--line:rgba(238,240,241,.10); --line-2:rgba(238,240,241,.06); --line-strong:rgba(238,240,241,.16);

--glass-shell-bg:rgba(22,25,28,.5);    --glass-shell-fallback:rgba(13,15,17,.94);
--glass-content-bg:rgba(22,25,28,.72); --glass-content-fallback:rgba(13,15,17,.96);
--glass-in:inset 0 1px 0 rgba(255,255,255,.07),inset 0 0 0 1px rgba(255,255,255,.05);
--glass-sheen:linear-gradient(120deg,rgba(255,255,255,.07),transparent 45%);

--navy:#050607;
--accent:#7ea3ba; --accent-2:#9bc0d4; --accent-soft:#151e23; --accent-ring:rgba(126,163,186,.3);
--mix-tint:#181b1e; --mix-ink:#f2f4f5;
--shadow-rgb:0,0,0;
--sh-sm:0 1px 2px rgba(0,0,0,.4), 0 4px 14px -4px rgba(0,0,0,.5);
--sh-md:0 2px 8px rgba(0,0,0,.35), 0 18px 38px -16px rgba(0,0,0,.55);
--sh-lg:0 4px 18px rgba(0,0,0,.4), 0 40px 80px -28px rgba(0,0,0,.65);

/* --ok / --warn / --pend / --crit NO se redefinen, a propósito */
```

### 3.3 Tema: comportamiento y persistencia

- **Arranca en claro**, siempre, salvo que el usuario ya haya elegido oscuro. Es deliberado: el residente no es un perfil técnico, y el tema claro se siente más doméstico.
- La preferencia se guarda en `localStorage` y **se reaplica en cada página**. Sin esto, cambiar a oscuro y navegar a otra pantalla volvía a claro (fue un bug real reportado).
- Para que no haya un parpadeo de claro antes de aplicar el oscuro, la reaplicación **no puede esperar al script del final del body**: cada HTML lleva un script mínimo en el `<head>`, antes de cualquier hoja de estilo, que lee `localStorage` y estampa el atributo.
- El botón de tema usa la **View Transitions API** con el cross-fade por defecto del navegador, **sin personalizar**. Se probó un barrido circular desde el punto del clic y **se revirtió a pedido explícito del usuario**: tenía un bug de `z-index` y se percibía lento en Chrome. No se vuelve a intentar sin una decisión nueva.
- Sin soporte de View Transitions, el cambio es instantáneo. Degradación aceptable.

---

## 4. Arquitectura de la aplicación frontend

### 4.1 Multi-página estática, sin framework ni router

Cada **dominio de negocio** es un archivo `.html` independiente que comparte `tokens.css` y `components.css`. La navegación es HTML estándar (`<a href="...">`), sin router de JavaScript. **No hay framework de CSS ni build**: los archivos que se editan son exactamente los que se sirven, y el estilo sale enteramente de esas dos hojas propias.

**Un archivo por dominio, no por rol.** `financiero.html` es una sola pantalla que muestra la gestión completa al administrador y "Mi cuenta" al residente; no hay `financiero_admin.html` y `financiero_residente.html`. El archivo JS de esa pantalla rutea por rol al inicio y muestra la vista que corresponde.

**Sub-vistas dentro de un dominio** (listado, alta, edición, ficha) **no generan archivos nuevos**. Se resuelven dentro de la misma página:
- **Alta y edición** → modal de formulario centrado.
- **Ficha o detalle de solo lectura** → panel `.detail` (hoja inferior en mobile, panel lateral en desktop) o modal de solo lectura.
- **Varias secciones de igual jerarquía** → `.view-switch` (pestañas). Por ejemplo, dentro de `financiero.html`: Gastos / Expensas / Pagos / Deudores / Fondos — y dentro de Fondos, una segunda fila de pestañas para Fondos / Caja chica / Presupuestos / Facturas.

Un archivo nuevo se justifica **solo** cuando es la puerta de entrada a un dominio distinto.

### 4.2 Las dos zonas de la aplicación

**Zona pre-autenticación** — hoy solo el login: tarjeta centrada sobre el fondo atmosférico, sin sidebar ni menú. No hay nada que navegar todavía.

**Zona autenticada** — todo lo demás. Estructura común:

```
.layout-app
 ├─ .sidebar-backdrop        → solo mobile, transparente, cierra al tocar afuera
 ├─ aside.sidebar (shell)
 │   ├─ .sidebar-brand       → marca, enlaza al dashboard
 │   ├─ nav.sidebar-nav      → accesos según el rol (los genera layout.js)
 │   └─ .sidebar-footer      → tarjeta de usuario (nombre + rol) + cerrar sesión
 └─ .main-column
     ├─ header.topbar (shell) → hamburguesa (mobile) + título de pantalla + toggle de tema
     └─ contenido propio de la pantalla
```

- **Desktop (≥1024 px):** sidebar fija de 248 px, siempre visible.
- **Mobile (<1024 px):** sidebar oculta; la hamburguesa la despliega como panel superpuesto, con **el mismo patrón de panel deslizante** que el `.detail` del Dashboard Visual — un solo componente conceptual reutilizado, no dos implementaciones.
- **El backdrop del sidebar y del detalle es transparente**: solo captura el toque para cerrar, no oscurece. El único backdrop que sí oscurece y difumina es el de los modales, porque ahí el usuario tiene que leer algo antes de seguir.

### 4.3 Los accesos del sidebar se definen en un solo lugar

`layout.js` tiene la tabla de qué rol ve qué acceso y la aplica en todas las pantallas. **Nunca se linkea a un archivo que todavía no existe**: un rol sin pantallas ve un mensaje explícito, no un menú roto. Cuando una pantalla suma una audiencia nueva, se agrega ahí y aparece en toda la aplicación de una vez.

---

## 5. Catálogo de componentes

Todos viven en `frontend/assets/css/components.css`. Se listan agrupados por función, con la regla de uso y —donde la hay— la lección que los corrigió.

### 5.1 Estructura y superficies

| Clase | Qué es |
|---|---|
| `.shell` / `.content-glass` | Los dos niveles de vidrio (sección 2.3). |
| `.layout-app`, `.sidebar`, `.main-column`, `.topbar` | El esqueleto de la zona autenticada. |
| `.panel-centrado` | Contenedor de contenido de una pantalla, con ancho máximo. |
| `.detail` + `.backdrop` | Panel de detalle: hoja inferior en mobile (con `.detail-drag`), panel lateral fijo en desktop. Interior: `.detail-head`, `.detail-body`, `.detail-section`, `.detail-item`, `.detail-field`, `.detail-grid`, `.detail-empty`. |

### 5.2 Navegación y acciones

| Clase | Qué es | Notas |
|---|---|---|
| `.icon-btn` | Botón cuadrado de ícono (38 px). | `.icon-btn-sm` (32 px) es la variante para una acción dentro de una fila de listado: el tamaño de topbar ahí es desproporcionado. |
| `.boton-primario` | Acción principal, ancho completo, degradé de acento. | |
| `.boton-chico` | Acción de ancho natural para poner varias en una fila (Confirmar / Rechazar). | `.boton-chico-critico` es la variante negativa, con tratamiento de color sobre `--crit`, nunca un rojo suelto. |
| `.chip-link` | Enlace de navegación con forma de píldora. | **No confundir con `.pill`**, que es exclusiva del semáforo. |
| `.view-switch` | Selector segmentado de pestañas. | Ver 5.6. |
| `.boton-estado-usuario` | Botón que **muestra** un estado binario y lo **alterna** al tocarlo, con efecto *ripple*. | Ver 5.6. |

### 5.3 Listados

| Clase | Qué es |
|---|---|
| `.fila-lista` | Fila de un listado: contenido a la izquierda, acciones a la derecha. El patrón base de cualquier pantalla "lista + alta en modal". |
| `.fila-lista-acciones` | Contenedor de las acciones de la fila. |
| `.fila-lista-estado`, `.fila-lista-botones` | Sub-grupos cuando el badge de estado y los botones tienen que comportarse distinto. |
| `.rol-badge` | Etiqueta neutra de clasificación (un rol, una categoría). No es estado, así que no usa el semáforo. |

> **Tres lecciones acumuladas sobre `.fila-lista`, todas de bugs reales en mobile.** Vale la pena leerlas antes de armar cualquier listado nuevo:
> 1. `flex-wrap: wrap` en las acciones **no alcanza** para que envuelvan: si además tienen `flex: none`, crecen a su ancho de contenido y nunca *necesitan* envolver, así que se salen de la tarjeta. Lo que realmente lo habilita es `min-width: 0` (más el `flex-shrink` por defecto). Se verifica con un texto largo de verdad; con etiquetas cortas el bug no se nota.
> 2. A anchos intermedios (~480–600 px) puede envolver la fila **entera**, dejando las acciones solas en su línea; ahí `justify-content: space-between` no tiene nada que distribuir y quedan pegadas a la izquierda. Se corrige con `margin-left: auto` en las acciones, sin media query: en desktop no tiene nada que empujar, y cubre cualquier ancho donde sí envuelva.
> 3. No todo lo que está en las acciones debe moverse junto. En algunos listados el badge tiene que quedar anclado al nombre y solo los botones ir a la derecha. Se resuelve detectando por contenido (`:has()`) en vez de agregar una clase nueva al HTML.

### 5.4 Estado y datos

| Clase | Qué es |
|---|---|
| `.pill` + `.pill.ok/.warn/.pend/.crit` | **El único componente con licencia para usar los 4 colores del semáforo como fondo de texto.** |
| `.s-ok`, `.s-warn`, `.s-pend`, `.s-crit` | Clases de estado que definen la variable local de color para el patrón borde+sombra (sección 2.4). |
| `.kpi`, `.kpi--hero`, `.kpi-metric`, `.kpi-grid` | Tarjetas de indicador en composición *bento*: 2 tarjetas "hero" grandes + 4 métricas chicas. **Nunca 6 tarjetas idénticas.** |
| `.kpi-label`, `.kpi-num`, `.kpi-sub` | Interior de un KPI. El número va en Outfit. |
| `.status-bar`, `.status-legend`, `.dot` | Barra de composición por estado (cuántas unidades en cada color) con su leyenda. |
| `.fin-row`, `.fin-track`, `.fin-fill`, `.fin-foot` | Barra de progreso financiero (recaudado vs. esperado). |
| `.dato-copiable` | Dato que el usuario necesita copiar (CBU, alias): etiqueta chica, valor destacado, botón de copiar a la derecha. |

### 5.5 Formularios

| Clase | Qué es |
|---|---|
| `.campo` | Bloque label + control. Los inputs llevan `width:100%; min-width:0; box-sizing:border-box` **siempre**. |
| `.form-grid-2` | Dos campos cortos lado a lado: una columna en mobile, dos recién desde 480 px. |
| `.campo-password-wrap` + `.campo-password-toggle` | Campo de contraseña con mostrar/ocultar. **Todo** `input[type=password]` de la aplicación usa esta estructura, sin excepción "porque es modo test". |
| `.campo-select-chico` | Select compacto para filtros en línea (año, mes, estado). Distinto del select de formulario, que es de ancho completo. |
| `.opcion-card` + `.opciones-grid` | Tarjeta seleccionable con descripción, para elegir una entre 2–4 alternativas donde cada una necesita una línea de explicación (prioridad de un reclamo, objetivo de un reclamo). Mismo mecanismo de selección que las tarjetas de unidad. |
| `.mensaje-error` / `.mensaje-exito` | Aviso en línea dentro de un formulario o panel, con ícono. Misma estructura, tono `--crit` o `--ok`. |
| `.modal-backdrop` + `.modal` | Modal centrado sobre backdrop que **sí** oscurece y difumina. `.modal-formulario` para altas y ediciones; `.modal-icono` para el aviso simple. |
| `.mapa-campo`, `.mapa-contenedor`, `.mapa-vacio` | Campo con mapa embebido (geocodificación en el alta de edificio). |

> **Dos correcciones importantes sobre modales:**
> - **`.modal` necesita `max-height` y `overflow-y: auto`.** Faltaba por completo, y con contenido largo de verdad (el detalle de una expensa con muchos rubros, en mobile) el modal se cortaba contra los bordes de la ventana sin forma de desplazarse. El `max-height` tiene que descontar el padding del backdrop.
> - **El modal de formulario nunca se cierra tocando el backdrop**, solo con la X o Cancelar. Perder un alta a medio tipear por un clic afuera es un problema real; cerrar una ficha de solo lectura no pierde nada. Por eso el `.detail` sí cierra al tocar afuera y el modal de formulario no.

### 5.6 Componentes con comportamiento

**`.view-switch` — selector segmentado.** Base de **todo** selector de pestañas del proyecto. El fondo del botón activo no lo pinta cada botón: lo hace **un único indicador que se desliza** entre opciones, moviéndose y cambiando de ancho para calzar exacto. Se engancha solo a cualquier `.view-switch` de la página; ninguna pantalla lo inicializa a mano. La lógica de negocio (qué se muestra al cambiar de pestaña) sigue siendo de cada pantalla: conviven dos listeners, uno mueve el indicador y el otro cambia el dato.

> **Trampa:** si el switch está oculto al cargar (dentro de un panel que todavía no mostró sus datos), medir su posición da todo en cero y el indicador queda mal para siempre. Se resuelve observando el redimensionado del propio switch en vez de calcular una sola vez: se reposiciona solo cuando pasa a tener tamaño real, y de paso cubre gratis el resize de ventana y la rotación del celular.

**`.boton-estado-usuario` — estado + acción en un solo elemento.** Fusiona lo que antes eran dos elementos (un pill de solo lectura y un botón aparte), a pedido explícito para aliviar el mobile. Muestra el estado actual con color y texto, y lo alterna al tocarlo, con un *ripple* que nace del punto exacto del clic.

> **Lección sobre el ripple** (reportado como "no hace el efecto"): la primera versión hacía crecer el círculo y lo desvanecía a la vez, así que para cuando cubría el botón ya era invisible; encima el ripple y el fondo transicionaban al mismo color al mismo tiempo, anulándose. La corrección tiene dos partes: el ripple **se mantiene opaco durante todo el crecimiento** y se desvanece solo al final, y la transición de fondo del botón es **más lenta** que el ripple, para que el ripple "pinte" primero y el fondo lo alcance después. Además, el texto va en un `<span>` interno: escribir directo sobre el botón borraría los ripples en curso.

### 5.7 El Dashboard Visual

Sus clases (`.visual-card`, `.scene`, `.building`, `.roof`, `.floor`, `.floor-row`, `.floor-windows`, `.window`, `.floor-body`, `.units-grid`, `.unit-card`, `.unit-tag`, `.unit-summary`, `.lobby`, `.assets`, `.assets-row`, `.asset-chip`, `.asset-zone`, `.legend`, `.chevron`) se documentan enteras en la sección 6, porque son un sistema, no componentes sueltos.

---

## 6. El Dashboard Visual del Edificio (el diferencial)

Es la funcionalidad que ningún competidor relevado ofrece, y la única parte del frontend cuya arquitectura **no se toca**.

### 6.1 Qué muestra

Una representación gráfica del edificio, piso por piso y departamento por departamento, coloreada según el estado real de cada unidad:

- **Nivel edificio:** fachada con los pisos apilados en franjas horizontales, una franja por piso.
- **Nivel piso (colapsado):** número de piso + una grilla de "ventanas", una por departamento, cada una con el color de su estado.
- **Nivel piso (expandido):** al tocarlo se despliegan las tarjetas completas de sus departamentos.
- **Nivel departamento:** al tocar una tarjeta se abre el panel de detalle con su ficha 360°.
- **Franja de activos:** separada de la fachada, muestra los activos y equipamiento común del edificio (ascensores, matafuegos, bocas de incendio, bombas) con el mismo esquema de colores.

### 6.2 El selector de vista (capa de datos)

El usuario elige qué información determina los colores en cada momento, porque no siempre quiere ver lo mismo:

| Vista | Qué colorea |
|---|---|
| **General** | Todos los factores, aplicando la regla de precedencia |
| **Incidentes** | Solo reclamos abiertos |
| **Deudores** | Solo estado de expensas |
| **Mantenimiento** | Solo órdenes de trabajo en curso |

Al cambiar de vista **se vuelve a renderizar todo**: nunca puede quedar un color "pegado" de la vista anterior.

### 6.3 Jerarquía de contenedores (no se improvisa)

```
.visual-card (shell)
 ├─ .visual-head          → título + .view-switch
 ├─ .legend               → leyenda de los 4 colores
 ├─ .scene
 │   └─ .building (content-glass, con reflejo lateral ::after)
 │       ├─ .roof         → nombre del edificio + indicador "sistema en vivo"
 │       ├─ #floors       → un .floor por piso (generado por JS)
 │       │   └─ .floor
 │       │       ├─ .floor-row   → colapsado: número + .floor-windows (.window por depto)
 │       │       └─ .floor-body  → expandido: .units-grid con una .unit-card por depto
 │       └─ .lobby        → decorativo, planta baja
 └─ .assets               → franja de activos, fuera de la fachada
     └─ .assets-row       → .asset-chip por activo

.backdrop  → capa fija transparente, cierra el panel al tocar afuera
.detail    → panel de detalle (hoja inferior en mobile / lateral en desktop)
```

**Detalles temáticos que no son decorativos:** el `.building` lleva un reflejo lateral simulando luz rebotando en una torre de vidrio real — es la coherencia deliberada entre "edificio de vidrio" y "interfaz de vidrio". El techo (`.roof`) usa el token `--navy` y tiene un indicador de "sistema en vivo".

### 6.4 El panel de detalle: la ficha 360° de la unidad

Al tocar un departamento se abre con:

- Datos de la unidad (propietario, inquilino, m², coeficiente).
- Reclamos abiertos, con su prioridad y el tiempo transcurrido.
- Estado de expensas, **si el rol que consulta tiene permiso para verlo**.
- Órdenes de trabajo activas o recientes.
- Activos ubicados en esa unidad, si aplica.

Es el punto donde confluye toda la información de los módulos de negocio en una sola vista.

### 6.5 Variante "piso completo" (opcional, no por defecto)

Existe documentada una variante donde, además del color por ventana, **todo el piso** se tiñe con el color de su estado más grave, con intensidad progresiva según gravedad. Queda como **variante activable**: el Roadmap decide si se ofrece como preferencia visual del usuario o se descarta. **No se implementa por defecto sin que esa decisión se tome primero.**

---

## 7. Módulos de JavaScript compartidos

Diecisiete archivos en `frontend/assets/js/`, con una división clara: **módulos compartidos** que cualquier pantalla usa, y **un archivo por pantalla** con su lógica propia.

### 7.1 Compartidos

| Módulo | Responsabilidad | Detalle que importa |
|---|---|---|
| `config.js` | Única fuente de la URL del backend, decidida por el hostname. | Se carga **antes** que `api.js` en toda página. |
| `api.js` | Envoltorio único de `fetch`: agrega el token, parsea JSON, estandariza errores. | Un 401 limpia la sesión y vuelve al login — **con una excepción a propósito**: en el propio login, un 401 significa "credenciales incorrectas", no "sesión vencida". Además adjunta el código HTTP al error, para que una pantalla pueda distinguir un 409 ("necesito confirmación") de un 400 cualquiera. |
| `layout.js` | Monta el sidebar: guarda de sesión, pide el usuario actual, arma los accesos por rol, marca el activo, engancha logout y hamburguesa. | Cada pantalla autenticada lo llama una vez y recibe el usuario. Ninguna reescribe esta lógica. |
| `theme.js` | Toggle de tema con View Transitions + persistencia. | El script anti-parpadeo va aparte, inline en el `<head>` de cada HTML. |
| `formularios.js` | Enter se comporta como Tab (avanza de campo) salvo en el último, y el toggle de los campos de contraseña. | Nació de un bug real: se creó un edificio a medio cargar porque Enter en un campo intermedio envió el formulario entero. |
| `view-switch.js` | Crea y mueve el indicador deslizante de todas las pestañas de la página. | Auto-enganche; ninguna pantalla lo inicializa. |
| `cargando.js` | Indicador de carga con dos frases rotando y puntos animados. | Un único intervalo global recorre los indicadores presentes, así funciona también con los que se insertan después al redibujar un listado. |
| `moneda.js` | Formato de moneda argentino para **mostrar** montos. | Centralizado para que ninguna pantalla arme su propio formateador. |
| `monto-input.js` | Formato de miles en vivo para **cargar** montos. | Ver 9.2. |
| `copiar.js` | Copiar al portapapeles con feedback inmediato (el ícono pasa a un check por 1,5 s). | Si el navegador no da permiso, no rompe el flujo. |
| `mapa.js` | Geocodificación (Nominatim) y mapa (Leaflet). | |

### 7.2 Por pantalla

`login.js`, `usuarios.js`, `edificios.js`, `financiero.js`, `reclamos.js`… Un archivo por dominio, que empieza montando el layout y ruteando por rol.

**Convención de tamaño:** cuando un archivo de pantalla supera las ~600 líneas (le pasó a `financiero.js`, que llegó a 1400 con ocho sub-pestañas), es señal de que ese dominio tiene demasiadas sub-vistas en un solo lugar. No es urgente refactorizar, pero sí conviene agrupar por sección con comentarios de bloque y declarar el estado compartido **todo junto arriba** (ver el primer punto de la sección 8).

---

## 8. Catálogo de trampas de frontend

Errores ya cometidos, con su causa y su prevención.

| Síntoma | Causa real | Prevención |
|---|---|---|
| `Cannot access 'X' before initialization` | Variable declarada con `let` más abajo en el archivo de lo que la usa el código de ruteo, que corre al inicio (*temporal dead zone*). **Ocurrió tres veces en tres archivos distintos.** | Declarar **todo** el estado compartido de la pantalla en un bloque arriba de todo, nunca junto a la función que lo usa. |
| Un ícono SVG desaparece al primer clic | Se reemplazó el `innerHTML` de un `<button>` con etiquetas SVG sueltas. Un `<button>` es HTML: su parser no reconoce `<path>` fuera de un `<svg>`, quedan como elementos desconocidos e invisibles. | Apuntar al `<svg>` interno y reemplazar **su** contenido. |
| Una fecha aparece un día antes | `new Date('2026-08-05')` se interpreta como medianoche UTC; en Argentina (UTC-3) retrocede al día anterior. | Nunca pasar una fecha `YYYY-MM-DD` del backend por `new Date()`: separar el texto y reordenarlo. |
| Un formulario no envía y no muestra ningún error | Hay un `<select required>` oculto por `display:none` en un ancestro: Chromium bloquea el envío en silencio porque no puede enfocarlo para mostrar el mensaje. | Los campos mutuamente excluyentes no llevan `required` en HTML; se validan desde el JS del formulario. |
| Un alta se autocompleta con las credenciales del administrador logueado | Chrome detecta el par email + contraseña como un formulario de login. | `autocomplete="off"` en el formulario y en el email, `autocomplete="new-password"` en la contraseña. Aplica a cualquier alta que cree credenciales **para otra persona**. |
| El indicador de pestañas queda mal posicionado | Se midió el switch mientras estaba oculto. | Ver 5.6. |
| Un modal con mucho contenido se corta en mobile | Faltaba `max-height` + `overflow-y` en `.modal`. | Ya resuelto globalmente; no reintroducirlo en un modal nuevo que redefina el fondo. |
| Un modal se ve "gris lavado, sin los colores de la app" | Vidrio translúcido sobre backdrop oscuro. | Ver 2.3, último punto. |

---

## 9. Reglas de interacción transversales

### 9.1 Nunca un diálogo nativo del navegador

Prohibido `alert()`, `confirm()` y `prompt()` en toda la aplicación. Rompen la identidad visual, no son responsive y no permiten explicar consecuencias.

**El patrón de confirmación es este** (implementado y probado con la regeneración de expensas): el usuario ejecuta la acción normalmente → el servidor responde `409` explicando qué se va a sobrescribir → la interfaz muestra ese mensaje y **el botón cambia de texto** a algo explícito como "Confirmar y reemplazar" → el segundo envío incluye el campo de confirmación. Si el usuario cambia algún dato del formulario, el estado de confirmación se reinicia.

### 9.2 Números y fechas en formato argentino

- **Mostrar:** punto de miles, coma decimal, mediante el formateador centralizado. Un monto siempre en Outfit, peso 700.
- **Cargar:** los campos de monto formatean **mientras el usuario tipea**. Un `<input type="number">` no sirve para esto: su modelo de valor nunca agrupa miles. Se usa `type="text"` con `inputmode="decimal"` (mantiene el teclado numérico en mobile) y formateo propio que reposiciona el cursor según cuánto cambió el largo.
- **Fechas:** ver la trampa de la sección 8.

### 9.3 Estados de carga, error y éxito

- Ningún listado muestra un hueco vacío mientras carga: va el indicador rotativo.
- Ningún listado vacío muestra una tabla sin filas: va un texto explicando que todavía no hay nada.
- Los errores se muestran **donde ocurrió la acción** (dentro del modal, arriba del listado), nunca en un lugar genérico lejos del contexto.
- Una acción que salió bien lo dice explícitamente (`.mensaje-exito`) y, si corresponde, limpia el formulario para permitir la siguiente carga.
- Los botones que disparan una llamada se deshabilitan mientras dura, y se rehabilitan pase lo que pase.

### 9.4 Accesibilidad mínima obligatoria

Todo botón de solo ícono lleva `aria-label`. Los formularios usan `<label for>` real. El foco de los campos se marca con el anillo de acento, nunca se elimina el *outline* sin reemplazarlo. Las animaciones respetan `prefers-reduced-motion`.

---

## 10. Responsive: dos quiebres, un solo maquetado

La hoja se escribe **mobile-first**: los estilos base son los de la pantalla angosta y los `@media (min-width: …)` **agregan**, nunca corrigen.

| Quiebre | Qué cambia |
|---|---|
| **Base (<640 px)** | KPIs a 2 columnas (los hero ocupan las 2). Ventanas de piso en grilla de 4 columnas apretada. Departamentos a 2 columnas. Panel de detalle = hoja inferior. Sidebar oculta tras la hamburguesa. Tarjetas de opción en 1 columna. |
| **≥640 px (tablet)** | KPIs a 4 columnas. Más aire en ventanas y tarjetas. Departamentos a 4 columnas. Pares de campos cortos lado a lado (desde 480 px). |
| **≥1024 px (desktop)** | KPIs a 6 columnas (los hero ocupan 3 cada uno). Sidebar fija visible. Panel de detalle pasa de hoja inferior a **panel lateral fijo** a la derecha. |

**No hay dos maquetados distintos**: es el mismo HTML y el mismo CSS reorganizando densidad y reposicionando el panel. Cualquier pantalla nueva se verifica en, al menos, 390 px, 768 px y 1280 px de ancho.

---

## 11. Especificación pantalla por pantalla

Todas las pantallas están **especificadas y ninguna construida**: el código de la primera iteración se eliminó en el reinicio del 2026-09-25. El orden en que se construyen lo fija el [`05_Roadmap.md`](05_Roadmap.md).

| Pantalla | Audiencia | Contenido |
|---|---|---|
| `index.html` — Login | Todos | Tarjeta centrada, email + contraseña con mostrar/ocultar. Redirige siempre al dashboard. |
| `dashboard.html` — Inicio | Todos los autenticados | Grilla de KPIs en composición bento y Dashboard Visual del edificio. Tres ramas por rol en el mismo archivo: gestión, residente y proveedor. |
| `usuarios.html` | Administrador General | Listado con badge de rol, alta en modal, activar/desactivar con el botón de estado. **Nunca permite desactivarse a uno mismo.** |
| `edificios.html` | Admin General / de Consorcio | Listado y alta con geocodificación y mapa. Detalle con pestañas: Datos, Estructura (pisos, departamentos, cocheras, espacios comunes, coeficientes con indicador de suma), Configuración. |
| `financiero.html` | Dos audiencias | **Administrador:** listado de edificios → detalle con pestañas Gastos / Expensas / Pagos / Deudores / Fondos (y dentro: Fondos, Caja chica, Presupuestos, Facturas). **Residente:** "Mi cuenta" — sus unidades, sus expensas con saldo, y carga de pago con el CBU copiable. |
| `reclamos.html` | Residente y gestión | **Residente:** alta de reclamo (objetivo, descripción, prioridad con explicación, fotos) y seguimiento de los propios, con reapertura. **Gestión:** todos los del edificio, filtros, cambio de estado, generar orden de trabajo. |
| `mantenimiento.html` | Administrador / Encargado | Órdenes de trabajo: listado con filtros, alta manual, asignación, cambio de estado, evidencias y costo al cerrar. |
| `activos.html` | Administrador / Encargado | Ficha de activo con QR, estado calculado, historial y próximo mantenimiento. Es también el destino del escaneo del QR físico. |
| `documentos.html` | Según categoría | Repositorio por categoría con visibilidad por rol. |
| `proveedores.html` | Administrador | Directorio con rubros, calificación e historial. |
| `comunicados.html` | Todos | Comunicados segmentados; para quien los emite, quién los leyó. |
| `reservas.html` | Residentes | Calendario por espacio común. |
| `seguridad.html` | Seguridad / Encargado | Incidentes y bitácora. |
| `analitica.html` | Administrador / Auditor | Gráficos con la skill `dataviz`, manteniendo el semáforo como único sistema de color para estado. |
| `configuracion.html` | Administrador General | Parámetros globales, permisos por excepción, auditoría. |

---

## 12. Checklist antes de dar por terminada una pantalla

1. ¿Reutiliza componentes del catálogo, o inventó alguno? Si inventó, ¿quedó documentado acá y en la skill?
2. ¿Se ve bien en 390, 768 y 1280 px de ancho, sin desbordes horizontales?
3. ¿Se ve bien en **tema oscuro**, incluidas sombras y vidrios?
4. ¿Todos los colores salen de tokens? (Buscar valores fijos sueltos.)
5. ¿Los estados de carga, vacío y error están cubiertos?
6. ¿Los botones de ícono tienen `aria-label` y los campos su `<label>`?
7. ¿La consola del navegador está limpia?
8. ¿Cada acción tiene su punto de entrada real, sin depender de escribir una URL a mano?
9. ¿Se probó con **cada rol** que puede entrar, incluido uno que no debería poder?
10. ¿Se probó el caso límite de datos: cero elementos, un elemento, y muchos con textos largos?

---

*Documentos relacionados: [`01_Documento_General.md`](01_Documento_General.md) (qué hace el producto) · [`02_Documento_Tecnico.md`](02_Documento_Tecnico.md) (backend, datos y API) · [`05_Roadmap.md`](05_Roadmap.md) (en qué orden se construye) · `.claude/skills/premium-uiux/` (el contrato visual, en formato ejecutable).*

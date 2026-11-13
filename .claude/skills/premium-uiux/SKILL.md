---
name: premium-uiux
description: Sistema de diseño premium y obligatorio para todo el frontend de SMART Building (ver_4) — paleta, tipografía, vidrio en dos capas, semáforo de 4 estados, arquitectura del Dashboard Visual, dark mode y reglas anti-estética-genérica-de-IA. Cargar SIEMPRE antes de crear, tocar o revisar cualquier pantalla, componente o estilo del frontend.
---

# premium-uiux — Sistema de diseño de SMART Building (ver_4)

Esta skill **es el contrato visual del proyecto** y la fuente de verdad en ejecución. Ninguna pantalla nueva se diseña "a criterio libre": se construye componiendo lo que ya está definido acá. Ante una duda de aspecto, gana la skill.

*(La carpeta `documentacion/mockups/` es exploración visual histórica: su contenido ya fue absorbido por esta skill y no se consulta para construir una pantalla.)*

**Documento hermano, para leer y entender:** [`documentacion/03_Documento_Frontend.md`](../../../documentacion/03_Documento_Frontend.md) es la versión completa y razonada de estas mismas reglas — tokens exactos, catálogo de componentes, arquitectura de pantallas, módulos de JavaScript compartidos, catálogo de trampas conocidas y checklist de pantalla nueva. Esta skill es el formato ejecutable; ese documento es el formato legible. **Si una regla cambia acá, cambia allá, y viceversa: son dos formatos del mismo contrato, no dos fuentes de verdad.**

## Antes que nada: las reglas del proyecto

**Esta skill no reemplaza a `CLAUDE.md`, que está en la raíz del repositorio y manda
sobre todo lo demás.** Dos reglas de ahí se repiten acá porque son las que no se
pueden olvidar ni siquiera en medio de un cambio de estilo:

- **Los datos de producción no se tocan sin avisar.** Antes de ejecutar algo que
  escriba, borre o migre datos de producción —o que pueda hacerlo de rebote— se
  explica qué se toca, qué se puede perder y cómo se vuelve atrás, y se espera
  respuesta. Una pantalla nueva parece inofensiva, pero las migraciones viajan con ella.
- **Nada se sube a Git.** Ni commit ni push: eso lo hace el usuario a mano.

## Misión

Producir una interfaz **premium y profesional** — vidrio auténtico ("Liquid Glass"), acabado de estudio de diseño, nunca "generada" — que funcione igual de bien como herramienta de trabajo densa en datos reales en mobile y en escritorio, sin perder elegancia en ninguno de los dos.

## Antes de escribir una clase en un HTML: leer su regla en el CSS

Tres bugs de la misma pantalla, el mismo día, salieron de **usar una clase por
su nombre sin leer qué hace**. El nombre no alcanza, y los tres se ven mal sin
fallar — que es lo caro.

- **Hay clases que son modificadores y solas no hacen nada.** `.boton-secundario`
  va **encima** de `.boton-primario` (solo cambia fondo y color); `.icon-btn-sm`
  encima de `.icon-btn` (solo cambia el tamaño). Sola, la clase no tiene ningún
  estilo de base y el botón queda sin forma. Se escriben las dos:
  `class="boton-primario boton-secundario"`.
- **Hay clases que necesitan compañera.** `.modal` va con `.shell` — es lo que
  le da la superficie de vidrio— y `.fila-lista` con `.content-glass`.
- **Un `.boton-primario` fuera de un formulario lleva `.boton-chico`.** Nace con
  `width:100%` porque su caso principal es el pie de un formulario; acompañando
  un título hay que encogerlo. `.boton-chico` existe nombrada **justamente para
  eso**, así que no se inventa una regla de contenedor: ya está resuelto.
- **Hay clases que son listas y el nombre no lo dice.** `.bloque-lista` es un
  `<ol>` con contador, no un encabezado: su contenido va en `<li>`.

**La forma corta de no equivocarse:** antes de escribir un componente, buscar
uno igual en `usuarios.html` o `edificios.html` y copiar el `class` entero. Si
no hay ninguno igual, leer la regla en `components.css`.

**Y hay un verificador que atrapa estos cuatro casos:**
`python frontend/verificar_pantallas.py`. Recorre las pantallas, aprende de las
ya aprobadas qué combinaciones de clases son válidas, y avisa. Se corre antes
de dar por terminada una pantalla. Tiene `--probar`, que le inyecta los diez
bugs conocidos en memoria y comprueba que los encuentre.

## Regla de oro: reutilizar, nunca reinventar

Cuando una tarea nueva necesite un botón, un ícono, una tarjeta, un badge, una animación o un patrón de interacción, la pregunta correcta **no es** "¿cómo lo diseño?" sino **"¿cuál de los patrones ya definidos en `references/componentes.md` uso acá?"**. Si de verdad no existe un patrón que sirva, se diseña uno nuevo siguiendo los mismos tokens (color, radio, sombra, tipografía, timing de transición) de esta skill y se agrega a `references/componentes.md` para que la próxima tarea lo reutilice. La consistencia es el producto: un usuario que pasa de Reclamos a Activos a Reservas tiene que sentir que es la misma app, no tres experimentos distintos.

## Anti-patrones estrictamente prohibidos (la estética "por defecto de cualquier LLM")

Un modelo de lenguaje, dejado a su criterio por defecto, converge casi siempre en el mismo puñado de tics visuales. Están **prohibidos sin excepción** en este proyecto:

1. **Ningún morado/lila/violeta**, ni solo ni en degradé (`from-purple-500 to-pink-500`, `indigo-600`, etc.). No forma parte de la identidad de SMART Building.
2. **Ningún color primario genérico de librería** (`bg-blue-500`, `bg-indigo-600`, azules/verdes de manual sin tonalizar). Todo color sale de la paleta acero/grafito de `references/paleta-color.md`.
3. **Ninguna tarjeta "de catálogo"**: `border border-gray-200 rounded-lg shadow-md` repetido en todos lados. Las superficies acá son vidrio translúcido en dos capas (`.shell` / `.content-glass`) con brillo especular + sombra compuesta en capas (`--sh-sm/md/lg`, `--glass-in`).
4. **Cero emojis**, en ninguna parte: ni en la interfaz, ni en textos, ni en comentarios de código. Todo ícono es SVG inline dibujado a mano (trazo, `viewBox 24x24`, `stroke-width ~1.7-1.9`, `stroke-linecap/linejoin round`), nunca una librería de íconos sin adaptar y nunca un emoji Unicode.
5. **Nunca `Inter` (ni `system-ui`) en titulares, números grandes o marca.** Inter se reserva para cuerpo/labels/inputs. Titulares, KPIs y numeración usan siempre **Outfit**.
6. **Nada de hero centrado con texto en degradé sobre un blob difuminado de fondo.** Esta app es una herramienta de trabajo densa en datos reales, no una landing page.
7. **Nada de animaciones "elásticas"/con rebote** (`spring` exagerado, `overshoot`). Toda transición es `ease-out`, sutil, 180-340ms; el hover eleva apenas (`translateY(-1px)` a `-2px`) o ilumina, nunca rebota.
8. **Nada de grillas de tarjetas idénticas sin jerarquía.** Los KPI usan composición tipo *bento* (los 2 "hero" ocupan más columnas que las métricas chicas).
9. **Nunca estética gamer/cyberpunk** (neón real, glow saturado, contraste estridente), tampoco en el tema oscuro.
10. **Prohibido el patrón `border-left: 3px solid var(--color)` (o `border-top`) para indicar estado.** Es un tic visual de dashboard genérico. El semáforo se comunica con **borde completo (4 lados) + sombra proyectada del mismo color** — ver sección siguiente.
11. **Nunca inventar un botón, ícono o badge nuevo "para esta pantalla".** Se reutiliza el vocabulario existente (`references/componentes.md`); si hace falta una variante, se deriva de los mismos tokens.

## Los tres pilares que sí definen esta estética

- **Vidrio auténtico en dos capas, no `backdrop-blur` suelto.** `.shell` (blur 22px, ~52% opacidad clara) para contenedores grandes de baja densidad de texto — topbar, KPIs, contenedor del Dashboard Visual, panel de detalle. `.content-glass` (blur 7px, ~68% opacidad clara) para contenido denso dentro de un shell — tarjetas de departamento, chips de activos, ítems del panel de detalle. Ver `references/paleta-color.md` para el porqué de esta separación (Apple *Liquid Glass*: el vidrio no va debajo de contenido denso).
- **Un acento de marca contenido — acero/grafito (`--accent #487798`) — nunca varios compitiendo, y deliberadamente FUERA de la familia del semáforo.** El único otro sistema de color con licencia para existir es el **semáforo funcional de 4 estados** (sección siguiente), que nunca se usa para decoración, solo para estado real. Si el acento se pareciera a "verde" o "rojo", el usuario confundiría una interacción de marca con un estado real del edificio.
- **El Dashboard Visual del Edificio es intocable en su arquitectura.** Es el diferencial del producto (Documento Técnico, sección 1.2 y 1.3.8). Su jerarquía de contenedores (`references/componentes.md`, "Arquitectura del edificio") no se improvisa nunca: romperla rompe el layout responsive.

## El semáforo de 4 estados (no es una paleta, es una regla de negocio)

| Estado | Variable | Significado | Nunca... |
|---|---|---|---|
| Verde | `--ok` | Todo correcto | ...se usa como color decorativo suelto |
| Amarillo | `--warn` | Atención (reclamo leve/medio, deuda 1 mes, activo por vencer ≤30 días) | ...se confunde con naranja |
| Naranja | `--pend` | Pendiente (ya se está resolviendo — orden de trabajo en curso) | ...se usa como "advertencia genérica"; es EXCLUSIVO de mantenimiento en curso |
| Rojo | `--crit` | Crítico (reclamo crítico, deuda >1 mes, activo vencido) | ...se reemplaza por un rojo de librería |

Regla de precedencia (Documento Técnico 1.2.1): ante varios factores activos a la vez en una misma unidad, gana el **más grave** — verde < amarillo < naranja < rojo. Estos 4 valores se mantienen **idénticos entre tema claro y oscuro** — el significado del estado no cambia según el tema elegido.

**La única excepción al "nunca decorativo", y es una sola (2026-11-13):** el botón de **borrar** de una fila (`.accion.borrar`) usa `--crit` tintado. "Destructivo" es una convención universal y no es un estado del edificio, así que no compite con el semáforo. **Lo que sí se rechazó** fue usar el verde `--ok` para el botón de editar, aunque se pidió: en la misma pantalla el verde pasaría a significar dos cosas —"todo correcto" en el estado de una unidad y "acción de editar"— y esa ambigüedad es exactamente lo que el semáforo existe para evitar. Editar usa el acento. Cualquier otra excepción futura se discute antes y se anota acá: si hay tres, ya no hay regla.

## Tipografía

- **Display / titulares / números de KPI:** `Outfit` (pesos 500-800), `letter-spacing: -0.015em`.
- **Cuerpo / labels / inputs:** `Inter` (pesos 400-700).
- Ambas vía Google Fonts, con fallback `ui-sans-serif, system-ui, sans-serif`.
- Nunca serif en pantallas de gestión.

## Radios y espaciado

- Tarjetas: `--r-card 20px`. Paneles grandes / topbar: `--r-lg 24px`. Elementos chicos (chips, inputs): `--r-sm 12px`. Pills/badges: `border-radius: 99px`.
- Espaciado en múltiplos de 4px; gaps de grilla 8px (mobile) a 10-12px (desktop).

## Responsive: mobile-first real, dos quiebres

- **Base (< 640px, mobile):** KPIs a 2 columnas (los 2 "hero" ocupan las 2 completas). Grilla de ventanas de piso en 4 columnas apretada. Grilla de departamentos a 2 columnas. Panel de detalle = hoja inferior (`bottom sheet`), backdrop transparente (solo cierra al tocar afuera, no oscurece).
- **≥ 640px (tablet):** KPIs a 4 columnas. Ventanas y tarjetas de departamento con más aire. Grilla de departamentos a 4 columnas.
- **≥ 1024px (desktop/web):** KPIs a 6 columnas (los 2 hero ocupan 3 cada uno). Panel de detalle deja de ser hoja inferior y pasa a panel lateral fijo (`right:24px; width:380px`).

No hay dos maquetados distintos: es el mismo HTML/CSS con dos `@media (min-width: …)` que reorganizan densidad y reposicionan el panel de detalle — nunca al revés (los estilos base son siempre los de mobile).

## Dark mode: nunca valores sueltos, siempre tokens

Arranca en tema claro solo cuando no hay una preferencia guardada todavía — el tema elegido persiste en `localStorage` y se reaplica en cada página (ver `references/componentes.md`, sección "Toggle de tema"). El botón de tema (topbar) usa la **View Transitions API** (`document.startViewTransition()`) con el cross-fade default del navegador, sin personalizar — se probó un barrido circular más elaborado y se revirtió a pedido explícito del usuario (bug real de z-index + reportado como lento en Chrome). Si el navegador no soporta View Transitions, el cambio es instantáneo.

Regla no negociable: **ningún color, sombra o superficie de vidrio se escribe como valor fijo suelto en una regla.** Todo pasa por variables CSS en `:root` (claro) redefinidas en `html[data-theme="dark"]` (oscuro) — incluyendo los grupos que se pasan por alto: sombra y vidrio (`--sh-sm/md/lg`, `--glass-in`, `--glass-sheen`) y los literales de mezcla (`--mix-tint`, `--mix-ink`, `--shadow-rgb`). Si una regla nueva necesita "un blanco" o "un negro tenue", nunca escribe `#fff` o `rgba(0,0,0,.1)` directo.

## Como se implementa: CSS propio, sin framework y sin build

- Los tokens de color, sombra y vidrio (variables `:root` / `html[data-theme="dark"]`) viven en `frontend/assets/css/tokens.css`. Esa hoja **no dibuja nada**: solo declara variables, y es la fuente de verdad del color.
- Los patrones compuestos (`.shell`, `.content-glass`, `.unit-card`, `.view-switch`, el toggle de tema) son clases reutilizables en `frontend/assets/css/components.css`.
- Los archivos que se editan son exactamente los que se sirven. No hay paso de compilacion, ni CDN de terceros para el estilo.
- **Se evaluo Tailwind y se descarto** (decision del 2026-09-27): el sistema visual son clases compuestas propias, asi que sus utilidades no se usarian, y agregarlo sumaba una dependencia externa sin resolver ningun problema real.

## Mockups de referencia de la carpeta `mockups/`

Estas son las **pantallas de referencia vigentes** del sistema, hechas con este contrato y nada más que este contrato: mismos tokens, mismo vidrio en dos capas, misma jerarquía del Dashboard Visual, mismo semáforo. A diferencia de `documentacion/mockups/` (exploración histórica, que no manda sobre nada), estas sí se consultan: cuando necesito armar una pantalla nueva, abro la que más se le parezca y copio el patrón.

Son archivos `.dc.html` autocontenidos (cada uno trae los tokens en su `<helmet>`, porque un artboard no puede linkear `tokens.css`). Al portarlos al frontend real, ese bloque se reemplaza por los dos `<link>` de siempre a `tokens.css` y `components.css` — **el CSS del `<helmet>` no se copia al proyecto**, es solo lo que hace que el mockup se vea solo.

| Archivo | Qué resuelve |
|---|---|
| `Mobile-Dashboard.dc.html` | Dashboard Visual en mobile: topbar con hamburguesa, KPIs bento (1 hero + 2 métricas), fachada con selector de 4 vistas, piso expandido, franja de activos. |
| `Mobile-Ficha.dc.html` | La ficha 360° como hoja inferior, con el backdrop transparente y dos acciones ancladas abajo. |
| `Mobile-Reclamo.dc.html` | Alta en modal de formulario: el único backdrop que oscurece y difumina. La prioridad usa `.opcion-card`; la foto es un campo de URL, como corresponde mientras no haya almacenamiento propio. |
| `Mobile-Financiero.dc.html` | "Mi cuenta" del residente: saldo arriba, apertura de la expensa por rubro, CBU y alias copiables. |
| `Mobile-Oscuro.dc.html` | Tema oscuro + el panel de navegación deslizante (mismo componente conceptual que la hoja de detalle). |
| `Desktop-Dashboard.dc.html` | Lo mismo en escritorio: sidebar de 248 px, KPIs a 6 columnas, fachada y panel de detalle lado a lado. |
| `Desktop-General.dc.html` | Dashboard General: bento + recaudación mes a mes + gastos por rubro + "lo que hay que mirar hoy". |
| `Desktop-Financiero.dc.html` | Pantalla financiera: pestañas del dominio en un solo archivo, tabla ancha en caja con scroll propio, columna de resumen. |

### Dos ajustes que salieron de armarlos

1. **Botón de ícono a 42 px en mobile, 38 px en escritorio.** El contrato decía 38 en los dos. A 38 no se llega al mínimo de área táctil que pide cualquier guía de accesibilidad, y en mobile ese botón es la hamburguesa y el cierre de la hoja — los dos toques más frecuentes de la app. En escritorio no hace falta, así que ahí se queda en 38 y no se toca nada más.
2. **El amarillo y el naranja del semáforo son difíciles de distinguir entre sí.** Medido, no estimado: `--warn #bd8b00` contra `--pend #c1691f` quedan a ΔE 8,8 en visión normal y 6,3 simulando deuteranopía. (Ese ΔE es **distancia en OkLab ×100**, que es la métrica con la que se midió toda esta paleta. No confundir con ΔE2000, que para el mismo par da 16,2 — los dos números son correctos y miden cosas distintas, así que al comparar hay que decir cuál se está usando.) La consecuencia: **ninguno de los cuatro estados se comunica nunca solo con color.** Siempre va con texto al lado (una `.pill`, un `.unit-tag`, la leyenda con su etiqueta). Lo mismo vale para `--warn` sobre el fondo claro: queda en 2,73:1, así que nunca lleva texto encima — y eso no se arregla subiendo croma, porque un amarillo oscuro deja de ser amarillo.

3. **La paleta se revisó dos veces para que no se viera apagada**, las dos a pedido del usuario. La segunda, del **2026-11-12**, encontró que el problema ya no era el croma de los colores sino cuánto de ese color se veía: el `saturate()` del backdrop del vidrio subió de 1,15 a 1,35 —el cambio más efectivo de todos y no toca ningún color— y el velo blanco del vidrio bajó de .52 a .46. También destapó **dos errores de contraste que estaban en producción**: `--ink-3` medía 3,68:1 (labels y metadata, por debajo del mínimo) y el botón primario en tema oscuro medía **2,27:1**, porque tenía el texto en blanco fijo "por contraste sobre el acento sólido" — cierto en claro, falso en oscuro. De ahí el token `--sobre-acento`. La regla que queda: **un color que se escribe fijo "porque no depende del tema" se mide en los dos temas antes de afirmarlo.** El detalle está en `references/paleta-color.md`.
4. **La primera revisión, del 2026-11-01**, fue a pedido del usuario. Se multiplicó el croma conservando luminosidad y tono: las manchas del fondo ×2,3 (eran casi grises y son el fondo detrás de todo el vidrio), el acento ×1,45, y el semáforo apenas ×1,08 porque el amarillo ya estaba en el techo del gamut sRGB. El detalle medido, con los contrastes antes y después, está en `references/paleta-color.md`. **Si hay que volver a tocar el color, se lee esa sección primero:** explica por qué el semáforo no se puede subir más y por qué el texto de las pills es un token propio y no un `color-mix`.

## Archivos de referencia

- **`references/paleta-color.md`** — todas las variables CSS (claro + oscuro) con su valor exacto y cuándo usar cada una.
- **`references/componentes.md`** — patrones de interacción con su HTML/CSS/JS de referencia, comentados: topbar, tarjetas KPI, selector de vista segmentado, arquitectura del Dashboard Visual (edificio con pisos/ventanas/departamentos + panel de detalle + franja de activos), pills de estado, botones de ícono, toggle de tema, motor de datos (severidad) independiente de la piel visual.

Antes de escribir la primera línea de una pantalla nueva: leer ambas referencias. Es más rápido copiar y adaptar un patrón ya resuelto que reinventarlo y terminar, sin querer, en la estética genérica que esta skill existe para evitar.

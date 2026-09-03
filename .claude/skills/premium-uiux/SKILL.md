---
name: premium-uiux
description: Sistema de diseño premium y obligatorio para todo el frontend de SMART Building (ver3) — paleta, tipografía, vidrio en dos capas, semáforo de 4 estados, arquitectura del Dashboard Visual, dark mode y reglas anti-estética-genérica-de-IA. Cargar SIEMPRE antes de crear, tocar o revisar cualquier pantalla, componente o estilo del frontend.
---

# premium-uiux — Sistema de diseño de SMART Building (ver3)

Esta skill es la única fuente de verdad visual del proyecto. Ninguna pantalla nueva se diseña "a criterio libre": se construye componiendo lo que ya está definido acá, tomado directamente del mockup aprobado por el cliente — **`documentacion/mockups/Mockup_3D_Vidrio_Grafito.html`**. Ese archivo es el contrato pixel a pixel (también documentado en `documentacion/02_Documento_Tecnico.md`, sección 1.3); esta skill es su documentación reutilizable para construir el resto de las pantallas sin reinventar el lenguaje visual una y otra vez.

## Misión

Producir una interfaz **premium y profesional** — vidrio auténtico ("Liquid Glass"), acabado de estudio de diseño, nunca "generada" — que funcione igual de bien como herramienta de trabajo densa en datos reales en mobile y en escritorio, sin perder elegancia en ninguno de los dos.

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
- **Un acento de marca contenido — acero/grafito (`--accent #57768c`) — nunca varios compitiendo, y deliberadamente FUERA de la familia del semáforo.** El único otro sistema de color con licencia para existir es el **semáforo funcional de 4 estados** (sección siguiente), que nunca se usa para decoración, solo para estado real. Si el acento se pareciera a "verde" o "rojo", el usuario confundiría una interacción de marca con un estado real del edificio.
- **El Dashboard Visual del Edificio es intocable en su arquitectura.** Es el diferencial del producto (Documento Técnico, sección 1.2 y 1.3.8). Su jerarquía de contenedores (`references/componentes.md`, "Arquitectura del edificio") no se improvisa nunca: romperla rompe el layout responsive.

## El semáforo de 4 estados (no es una paleta, es una regla de negocio)

| Estado | Variable | Significado | Nunca... |
|---|---|---|---|
| Verde | `--ok` | Todo correcto | ...se usa como color decorativo suelto |
| Amarillo | `--warn` | Atención (reclamo leve/medio, deuda 1 mes, activo por vencer ≤30 días) | ...se confunde con naranja |
| Naranja | `--pend` | Pendiente (ya se está resolviendo — orden de trabajo en curso) | ...se usa como "advertencia genérica"; es EXCLUSIVO de mantenimiento en curso |
| Rojo | `--crit` | Crítico (reclamo crítico, deuda >1 mes, activo vencido) | ...se reemplaza por un rojo de librería |

Regla de precedencia (Documento Técnico 1.2.1): ante varios factores activos a la vez en una misma unidad, gana el **más grave** — verde < amarillo < naranja < rojo. Estos 4 valores se mantienen **idénticos entre tema claro y oscuro** — el significado del estado no cambia según el tema elegido.

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

Arranca **siempre en tema claro**. El botón de tema (topbar) anima un barrido circular que nace del punto exacto del clic — **View Transitions API** (`document.startViewTransition()`) + `clip-path:circle()` animado con Web Animations API sobre `::view-transition-new(root)` — ver `references/componentes.md`, sección "Toggle de tema"; si el navegador no la soporta, el cambio es instantáneo, sin barrido.

Regla no negociable: **ningún color, sombra o superficie de vidrio se escribe como valor fijo suelto en una regla.** Todo pasa por variables CSS en `:root` (claro) redefinidas en `html[data-theme="dark"]` (oscuro) — incluyendo los grupos que se pasan por alto: sombra y vidrio (`--sh-sm/md/lg`, `--glass-in`, `--glass-sheen`) y los literales de mezcla (`--mix-tint`, `--mix-ink`, `--shadow-rgb`). Si una regla nueva necesita "un blanco" o "un negro tenue", nunca escribe `#fff` o `rgba(0,0,0,.1)` directo.

## Migración a Tailwind (Documento Técnico, sección 1.3.1)

El mockup está resuelto en CSS vanilla a propósito, para iterar rápido en la etapa de diseño. La implementación real:

- Los tokens de color/sombra/vidrio (variables `:root` / `html[data-theme="dark"]`) se mantienen **fuera de Tailwind**, en `frontend/assets/css/tokens.css` — son la fuente de verdad del color.
- `tailwind.config.js` mapea sus utilidades de color a esas mismas variables (`colors: { accent: 'var(--accent)', crit: 'var(--crit)', ... }`), para poder maquetar con clases utilitarias sin perder el theming dinámico.
- Los patrones compuestos (`.shell`, `.content-glass`, `.unit-card`, `.view-switch`, el toggle de tema) se implementan como clases reutilizables vía `@layer components` en `frontend/assets/css/components.css`.
- **Fase CDN → build real:** primeras tareas del Roadmap con `cdn.tailwindcss.com`. Antes de cerrar la etapa de frontend se migra a **Tailwind CLI standalone** (sin Node/npm) para generar `output.css` compilado.

## Archivos de referencia

- **`references/paleta-color.md`** — todas las variables CSS (claro + oscuro) con su valor exacto, tomadas literalmente del mockup, y cuándo usar cada una.
- **`references/componentes.md`** — patrones de interacción con su HTML/CSS/JS de referencia (copiado y comentado desde `Mockup_3D_Vidrio_Grafito.html`): topbar, tarjetas KPI, selector de vista segmentado, arquitectura del Dashboard Visual (edificio con pisos/ventanas/departamentos + panel de detalle + franja de activos), pills de estado, botones de ícono, toggle de tema, motor de datos (severidad) independiente de la piel visual.

Antes de escribir la primera línea de una pantalla nueva: leer ambas referencias. Es más rápido copiar y adaptar un patrón ya resuelto que reinventarlo y terminar, sin querer, en la estética genérica que esta skill existe para evitar.

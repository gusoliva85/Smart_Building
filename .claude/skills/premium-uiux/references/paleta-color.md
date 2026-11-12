# Paleta de color — SMART Building (ver_4)

Valores exactos del contrato visual. Ninguna pantalla nueva inventa un color: si hace falta un matiz que no está acá, se deriva con `color-mix(in srgb, var(--token) N%, ...)` sobre uno de estos tokens, nunca con un valor hexadecimal nuevo suelto.

## Tema claro (`:root`, default)

```css
:root{
  /* Neutros y superficies */
  --bg-1:#f0f2f4; --bg-2:#e8ebed;
  --wash-a:#c6e1f1; --wash-b:#efe2c0;      /* manchas de color radiales detrás del vidrio, ver "Fondo de página" */
  --ink:#1c2024;    --ink-2:#4b5157;
  --ink-3:#6b7280;  --ink-4:#a8adb3;        /* --ink-3 se oscureció el 2026-11-12: antes no llegaba a 4,5:1 */
  --line:rgba(28,32,36,.10); --line-2:rgba(28,32,36,.07); --line-strong:rgba(28,32,36,.16);

  /* Vidrio — dos niveles, ver SKILL.md "Vidrio en dos capas" */
  --glass-shell-bg:rgba(255,255,255,.46);   --glass-shell-blur:22px;  --glass-shell-fallback:rgba(255,255,255,.92);
  --glass-content-bg:rgba(255,255,255,.62); --glass-content-blur:7px; --glass-content-fallback:rgba(255,255,255,.94);
  --glass-in:inset 0 1px 0 rgba(255,255,255,.85),inset 0 0 0 1px rgba(255,255,255,.45);
  --glass-sheen:linear-gradient(120deg,rgba(255,255,255,.55),transparent 45%);

  --navy:#14181d;                            /* techo del edificio (.roof) */

  /* Acento de marca — acero/grafito, FUERA de la familia del semáforo */
  --accent:#3e789f; --accent-2:#265c7d; --accent-soft:#d8ebf7; --accent-ring:rgba(62,120,159,.38);
  --sobre-acento:#ffffff;                    /* texto e iconos ENCIMA del acento sólido; en oscuro NO es blanco */

  /* Semáforo funcional — idéntico en ambos temas */
  --ok:#238166;   /* verde   */
  --warn:#bd8b00; /* amarillo */
  --pend:#c1691f; /* naranja */
  --crit:#b63544; /* rojo    */

  /* Texto de la pill de cada estado. Este SÍ se redefine en oscuro. */
  --ok-ink:#006b51; --warn-ink:#895900; --pend-ink:#9c4700; --crit-ink:#a82739;
  --pill-tinte:26%;                          /* cuánto color lleva el fondo de una pill */

  --mix-tint:#fff; --mix-ink:#1c2024;        /* usados por color-mix() en pills/tags para no repetir "blanco"/"tinta" sueltos */
  --shadow-rgb:16,26,38;                     /* azul muy oscuro, no gris neutro: la sombra lee como profundidad */

  /* Sombras (capas) */
  --sh-sm:0 1px 2px rgba(var(--shadow-rgb),.08), 0 4px 12px -4px rgba(var(--shadow-rgb),.16);
  --sh-md:0 2px 6px rgba(var(--shadow-rgb),.09), 0 16px 34px -16px rgba(var(--shadow-rgb),.26);
  --sh-lg:0 4px 16px rgba(var(--shadow-rgb),.11), 0 34px 70px -26px rgba(var(--shadow-rgb),.36);

  /* Radios */
  --r-card:20px; --r-lg:24px; --r-sm:12px;
}
```

## Tema oscuro (`html[data-theme="dark"]`)

```css
html[data-theme="dark"]{
  --bg-1:#0b0d0f; --bg-2:#0e1012; --wash-a:#002835; --wash-b:#291d03;
  --ink:#eef0f1;  --ink-2:#bcc0c4; --ink-3:#868b91; --ink-4:#54585d;
  --line:rgba(238,240,241,.10); --line-2:rgba(238,240,241,.06); --line-strong:rgba(238,240,241,.16);

  --glass-shell-bg:rgba(22,25,28,.46);   --glass-shell-fallback:rgba(13,15,17,.94);
  --glass-content-bg:rgba(22,25,28,.68); --glass-content-fallback:rgba(13,15,17,.96);
  --glass-in:inset 0 1px 0 rgba(255,255,255,.07),inset 0 0 0 1px rgba(255,255,255,.05);
  --glass-sheen:linear-gradient(120deg,rgba(255,255,255,.07),transparent 45%);

  --navy:#050608;
  --accent:#62a6ce; --accent-2:#81c3e7; --accent-soft:#01202f; --accent-ring:rgba(98,166,206,.40);
  --sobre-acento:#0b0d0f;                /* NO blanco: sobre el acento celeste, el blanco mide 2,27:1 */
  --ok-ink:#54ac8f; --warn-ink:#d19e2b; --pend-ink:#e48945; --crit-ink:#ef6a72;
  --pill-tinte:28%;
  --mix-tint:#181b1e; --mix-ink:#f2f4f5;
  --shadow-rgb:0,0,0;

  --sh-sm:0 1px 2px rgba(0,0,0,.4), 0 4px 14px -4px rgba(0,0,0,.5);
  --sh-md:0 2px 8px rgba(0,0,0,.35), 0 18px 38px -16px rgba(0,0,0,.55);
  --sh-lg:0 4px 18px rgba(0,0,0,.4), 0 40px 80px -28px rgba(0,0,0,.65);

  /* --ok/--warn/--pend/--crit NO se redefinen acá: el significado del estado no depende del tema */
}
```

## Cuándo usar cada token

| Token | Uso |
|---|---|
| `--bg-1` / `--bg-2` | Degradé de fondo de página (`linear-gradient(180deg, var(--bg-1), var(--bg-2))`), nunca un color plano. |
| `--wash-a` / `--wash-b` | Manchas radiales sutiles detrás del vidrio (`radial-gradient(ellipse ... , var(--wash-a), transparent 62%)`), dan profundidad atmosférica al fondo. Nunca como fondo de un componente. |
| `--ink` … `--ink-4` | Texto, de más a menos énfasis. `--ink` para titulares/valores, `--ink-2` cuerpo, `--ink-3` labels/metadata, `--ink-4` iconografía apagada/placeholder. |
| `--line` / `--line-2` / `--line-strong` | Bordes de hairline. `--line-2` para separadores internos sutiles (dentro de un shell), `--line` para el borde del propio shell, `--line-strong` cuando hace falta más contraste puntual. |
| `--glass-shell-*` | Contenedores grandes de navegación: topbar, tarjetas KPI, contenedor del Dashboard Visual, panel de detalle. Clase `.shell`. |
| `--glass-content-*` | Contenido denso dentro de un shell: tarjetas de departamento, chips de activos, campos del panel de detalle. Clase `.content-glass`. |
| `--glass-in` | `box-shadow` inset en TODA superficie de vidrio — la línea de luz interior que la hace leer como vidrio real, no como blur plano. |
| `--glass-sheen` | Fondo del pseudo-elemento `::before` de `.shell` — barrido diagonal de luz especular. |
| `--accent` / `--accent-2` | Marca: CTA, focos, elementos activos (ej. `.view-switch button.active`), gradiente de `.brand-mark`. Nunca para estado. |
| `--accent-soft` / `--accent-ring` | Fondos sutiles de foco/hover ligados a la marca (reservado para estados de foco de inputs). |
| `--ok` / `--warn` / `--pend` / `--crit` | EXCLUSIVO para estado real (semáforo). Nunca decorativo. Se combinan con `color-mix(in srgb, var(--c) N%, ...)` para bordes y washes — nunca un hex nuevo. |
| `--ok-ink` … `--crit-ink` | Color del **texto** de una pill de estado, uno por estado. Derivado bajando (o subiendo, en oscuro) solo la luminosidad del propio color del estado: conserva tono y croma, así que el texto sigue leyéndose como verde o rojo. **No se deriva con `color-mix` contra la tinta neutra** — ver abajo. |
| `--pill-tinte` | Porcentaje del color del estado que lleva el fondo de una pill. 22% en claro, 24% en oscuro. |
| `--mix-tint` / `--mix-ink` | Los dos "extremos" que usa `color-mix()` para derivar el fondo/texto de pills y tags de estado sin escribir blanco/negro sueltos. |
| `--shadow-rgb` | Base RGB de todas las sombras (`--sh-sm/md/lg`) — permite que la sombra cambie de "gris cálido suave" (claro) a "negro profundo" (oscuro) sin tocar cada regla de sombra una por una. |
| `--navy` | Único uso: fondo del techo del edificio (`.roof`) en el Dashboard Visual — el remate oscuro de la fachada. |
| `--r-card` / `--r-lg` / `--r-sm` | Radios estándar: tarjetas, paneles grandes/topbar, elementos chicos (chips/inputs) respectivamente. Pills siempre `border-radius:99px` fijo, no token. |

## La revisión del 2026-11-01: por qué la paleta se veía apagada

El usuario reportó que toda la interfaz se sentía "opaca y apagada, sin brillo". Medido, el diagnóstico fue específico y **no era donde uno esperaría**:

| Grupo | Croma OkLCh antes | Factor aplicado | Por qué |
|---|---|---|---|
| `--wash-a` / `--wash-b` | 0,011 y 0,014 | **×2,3** | Eran prácticamente grises. Son el fondo de página detrás de **todo** el vidrio, así que su falta de color era la causa principal del efecto lavado. |
| `--accent` / `--accent-2` | 0,050 y 0,046 | ×1,45 | Acero muy apagado. Aparece en cada botón, foco y elemento activo. |
| `--accent-soft` | 0,009 | ×2,1 | Fondo del acceso activo del sidebar: era blanco con una idea de azul. |
| `--bg-1` / `--bg-2` / `--navy` | ~0,003 | ×1,6–1,7 | Casi neutros a propósito; se les dio apenas temperatura. |
| **Semáforo** | 0,089 – 0,152 | **×1,08** | **No era el problema.** Ver abajo. |

**El método: se multiplica C y se conservan L y H.** En OkLCh, la luminosidad perceptual y el tono quedan exactamente iguales, así que el color no cambia de identidad ni de claridad — solo deja de estar desteñido. Y como el contraste WCAG depende casi enteramente de la luminancia, los contrastes no se mueven: el texto blanco sobre el botón primario pasó de 4,80:1 a 4,81:1.

**Por qué el semáforo casi no se tocó.** El amarillo `--warn` ya estaba a ×1,08 del techo del gamut sRGB para su tono y su luminosidad: no hay margen. El rojo sí admitía ×1,37, pero subirlo solo a él desbalancea la familia — pasaría a gritar al lado de un amarillo que no se puede mover. **El semáforo es un sistema de cuatro colores, no cuatro colores sueltos: se sube lo que permite el más limitado.** Donde el estado sí se ve más presente es en la pill, subiendo `--pill-tinte` de 15% a 22/24%.

**Y un hallazgo que salió de medir esto: cuatro de los ocho casos de pill no cumplían contraste.** El texto se derivaba con `color-mix(var(--estado) 78%, var(--mix-ink))`, y eso daba 3,72:1 en `.warn` claro, 4,44:1 en `.pend` claro, 4,36:1 en `.ok` oscuro y 3,78:1 en `.crit` oscuro — los cuatro por debajo del mínimo de 4,5:1. La causa es estructural: el amarillo es intrínsecamente claro, así que para oscurecerlo hay que mezclarlo tanto contra el gris que deja de leerse como amarillo. Por eso el texto pasó a ser un token propio por estado (`--warn-ink`…), derivado moviendo **solo la luminosidad** del color del estado. Los ocho casos quedaron entre 4,62:1 y 4,77:1.

**Lo que no cambió, y se verificó que no cambiara:** la separación entre los cuatro estados mejoró en los seis pares (y también simulando deuteranopía); el acento sigue a 67–71° de tono del estado más cercano, así que la regla de oro de abajo se mantiene; y el vidrio no se tocó, porque bajar su opacidad para que pase más color habría costado legibilidad del texto que se apoya encima.

**`--warn` sigue sin poder llevar texto encima:** 2,73:1 sobre el fondo claro. Eso no se arregla subiendo croma, y es la razón por la que ningún estado se comunica nunca solo con color.

## La revisión del 2026-11-12: segunda pasada, y dos errores de contraste que aparecieron midiendo

El usuario volvió a reportar que la interfaz se sentía apagada, con la paleta del 2026-11-01 ya aplicada. El diagnóstico esta vez **no fue el croma de los colores** —ya estaba subido— sino **cuánto de ese color llegaba a verse**:

| Cambio | De → a | Por qué |
|---|---|---|
| `saturate()` del backdrop del vidrio | 1,15 → **1,35** (`.shell`) y 1,0 → 1,2 (`.content-glass`) | **El cambio más efectivo de toda la revisión, y no toca ningún color.** El vidrio satura lo que tiene detrás, así que el fondo atmosférico se ve más vivo *en las superficies*, que es donde se mira. |
| Velo del vidrio | `.52` → `.46` y `.68` → `.62` | El color del fondo llegaba filtrado por un velo casi opaco. Medido: el texto principal pasa de 15,55:1 a 15,41:1 y el cuerpo de 7,62:1 a 7,56:1 — no cuesta legibilidad, porque lo que se asoma es igual de claro. |
| `--wash-a` / `--wash-b` | croma ×1,45 más (0,0254→0,0361 y 0,0321→0,0469) | Siguen siendo el fondo detrás de todo el vidrio. |
| `--accent` / `--accent-2` | croma ×1,18 (0,0729→0,0861) | Aparece en cada botón, foco y elemento activo. El contraste del texto del botón casi no se mueve: 5,89:1 → 5,85:1. |
| `--pill-tinte` | 22% → 26% (claro), 24% → 28% (oscuro) | Es **el único lugar donde el semáforo puede verse más presente**, porque los cuatro colores no se pueden subir. |
| `--shadow-rgb` | `20,22,25` → `16,26,38`, y las opacidades +1/+2 puntos | Una sombra con una pizca del tono de la marca lee como profundidad; una gris pura, como suciedad. |
| Hover de fila | `border-color:--line` → `--line-strong` + `--sh-sm` | El cambio anterior era de .07 a .10 de opacidad: tres centésimas, no se veía. Un hover que no se nota es código que no hace nada. |

**El semáforo se volvió a medir y la conclusión es la misma que en noviembre.** El techo del gamut sRGB conservando L y H es ×1,12 para el verde, **×1,00 para el amarillo**, ×1,09 para el naranja y ×1,28 para el rojo. Es un sistema de cuatro colores y se sube lo que permite el más limitado, así que quedaron como estaban.

### Los dos errores de contraste que esto destapó

**1. `--ink-3` no cumplía: 3,68:1 sobre el vidrio.** Es el color de los labels y de la metadata de cada fila de listado — texto normal, así que el mínimo de WCAG AA es 4,5:1. Se oscureció de `#7c828a` a `#6b7280` y pasa a 4,55:1. En oscuro ya cumplía (5,43:1) y no se tocó.

**2. El botón primario era ilegible en todo el tema oscuro: 2,27:1.** `.boton-primario` tenía `color:#fff` con el comentario *"blanco por contraste sobre el acento sólido, no por tema: no cambia en oscuro"*. Eso es cierto en claro (5,85:1) y falso en oscuro, donde el acento es celeste. Nació el token **`--sobre-acento`** —blanco en claro, `#0b0d0f` en oscuro (8,59:1)— y lo usan el texto del botón y el trazo del ícono de la marca, que tenía el mismo problema.

**La regla que queda de esto:** cualquier color que se escriba "fijo porque no depende del tema" tiene que medirse **en los dos temas** antes de afirmarlo. Los dos errores estuvieron en producción y ninguno de los dos se ve mirando el tema claro.

**Los 24 pares medidos tras la revisión cumplen 4,5:1**, y la verificación se hace **leyendo `tokens.css`**, no la propuesta: un hexadecimal mal tipeado no pasa inadvertido.

## Regla de oro del color

El acento de marca (acero/grafito) **nunca comparte familia de tono con ninguno de los 4 colores del semáforo**. Es intencional: si el acento decorativo se pareciera a "verde" o "rojo", un usuario podría confundir una interacción de marca (un botón activo, un link) con un estado real del edificio. Cualquier paleta futura debe preservar esta separación.

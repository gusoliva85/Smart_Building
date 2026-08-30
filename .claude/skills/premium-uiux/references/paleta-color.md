# Paleta de color — SMART Building (ver3)

Valores exactos tomados de `documentacion/mockups/Mockup_3D_Vidrio_Grafito.html`. Ninguna pantalla nueva inventa un color: si hace falta un matiz que no está acá, se deriva con `color-mix(in srgb, var(--token) N%, ...)` sobre uno de estos tokens, nunca con un valor hexadecimal nuevo suelto.

## Tema claro (`:root`, default)

```css
:root{
  /* Neutros y superficies */
  --bg-1:#f1f2f3; --bg-2:#e9ebec;
  --wash-a:#d6dee3; --wash-b:#e6e2d8;      /* manchas de color radiales detrás del vidrio, ver "Fondo de página" */
  --ink:#1c2024;    --ink-2:#4b5157;
  --ink-3:#7c828a;  --ink-4:#a8adb3;
  --line:rgba(28,32,36,.10); --line-2:rgba(28,32,36,.07); --line-strong:rgba(28,32,36,.16);

  /* Vidrio — dos niveles, ver SKILL.md "Vidrio en dos capas" */
  --glass-shell-bg:rgba(255,255,255,.52);   --glass-shell-blur:22px;  --glass-shell-fallback:rgba(255,255,255,.92);
  --glass-content-bg:rgba(255,255,255,.68); --glass-content-blur:7px; --glass-content-fallback:rgba(255,255,255,.94);
  --glass-in:inset 0 1px 0 rgba(255,255,255,.85),inset 0 0 0 1px rgba(255,255,255,.45);
  --glass-sheen:linear-gradient(120deg,rgba(255,255,255,.55),transparent 45%);

  --navy:#15181b;                            /* techo del edificio (.roof) */

  /* Acento de marca — acero/grafito, FUERA de la familia del semáforo */
  --accent:#57768c; --accent-2:#3e5a6d; --accent-soft:#e2e9ed; --accent-ring:rgba(87,118,140,.28);

  /* Semáforo funcional — idéntico en ambos temas */
  --ok:#2e8067;   /* verde   */
  --warn:#ba8c1f; /* amarillo */
  --pend:#bd6c2c; /* naranja */
  --crit:#b13c47; /* rojo    */

  --mix-tint:#fff; --mix-ink:#1c2024;        /* usados por color-mix() en pills/tags para no repetir "blanco"/"tinta" sueltos */
  --shadow-rgb:20,22,25;

  /* Sombras (capas) */
  --sh-sm:0 1px 2px rgba(var(--shadow-rgb),.06), 0 4px 12px -4px rgba(var(--shadow-rgb),.12);
  --sh-md:0 2px 6px rgba(var(--shadow-rgb),.07), 0 16px 34px -16px rgba(var(--shadow-rgb),.22);
  --sh-lg:0 4px 16px rgba(var(--shadow-rgb),.09), 0 34px 70px -26px rgba(var(--shadow-rgb),.32);

  /* Radios */
  --r-card:20px; --r-lg:24px; --r-sm:12px;
}
```

## Tema oscuro (`html[data-theme="dark"]`)

```css
html[data-theme="dark"]{
  --bg-1:#0c0d0e; --bg-2:#0f1011; --wash-a:#1c2529; --wash-b:#221f18;
  --ink:#eef0f1;  --ink-2:#bcc0c4; --ink-3:#868b91; --ink-4:#54585d;
  --line:rgba(238,240,241,.10); --line-2:rgba(238,240,241,.06); --line-strong:rgba(238,240,241,.16);

  --glass-shell-bg:rgba(22,25,28,.5);   --glass-shell-fallback:rgba(13,15,17,.94);
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
| `--accent-soft` / `--accent-ring` | Fondos sutiles de foco/hover ligados a la marca (poco uso en el mockup base; reservado para estados de foco de inputs). |
| `--ok` / `--warn` / `--pend` / `--crit` | EXCLUSIVO para estado real (semáforo). Nunca decorativo. Se combinan con `color-mix(in srgb, var(--c) N%, ...)` para pills, bordes y washes — nunca un hex nuevo. |
| `--mix-tint` / `--mix-ink` | Los dos "extremos" que usa `color-mix()` para derivar el fondo/texto de pills y tags de estado sin escribir blanco/negro sueltos. |
| `--shadow-rgb` | Base RGB de todas las sombras (`--sh-sm/md/lg`) — permite que la sombra cambie de "gris cálido suave" (claro) a "negro profundo" (oscuro) sin tocar cada regla de sombra una por una. |
| `--navy` | Único uso: fondo del techo del edificio (`.roof`) en el Dashboard Visual — el remate oscuro de la fachada. |
| `--r-card` / `--r-lg` / `--r-sm` | Radios estándar: tarjetas, paneles grandes/topbar, elementos chicos (chips/inputs) respectivamente. Pills siempre `border-radius:99px` fijo, no token. |

## Regla de oro del color

El acento de marca (acero/grafito) **nunca comparte familia de tono con ninguno de los 4 colores del semáforo**. Es intencional: si el acento decorativo se pareciera a "verde" o "rojo", un usuario podría confundir una interacción de marca (un botón activo, un link) con un estado real del edificio. Cualquier paleta futura debe preservar esta separación.

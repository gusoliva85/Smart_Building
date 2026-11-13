# Componentes — SMART Building (ver_4)

Patrones de interacción con su HTML/CSS/JS de referencia. Cada pantalla nueva copia y adapta estos bloques — no los reinventa. Los tokens usados acá están definidos en `paleta-color.md`.

## Fondo de página y textura de grano

Todo el body lleva un fondo atmosférico (nunca un color plano) y una textura de ruido fija en overlay al 3.5% — es lo que le da sensación táctil de vidrio premium:

```css
body{
  margin:0; color:var(--ink); font:15px/1.5 Inter,ui-sans-serif,system-ui,sans-serif;
  background:
    radial-gradient(ellipse 52% 34% at 10% -6%, var(--wash-a), transparent 62%),
    radial-gradient(ellipse 42% 28% at 106% 6%, var(--wash-b), transparent 58%),
    radial-gradient(ellipse 38% 26% at 50% 104%, var(--wash-a), transparent 66%),
    linear-gradient(180deg, var(--bg-1), var(--bg-2));
  background-attachment:fixed;
  -webkit-font-smoothing:antialiased;
}
body::before{
  content:""; position:fixed; inset:0; z-index:999; pointer-events:none;
  opacity:.035; mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
}
h1,h2,h3,.display{ font-family:Outfit,sans-serif; letter-spacing:-.015em; }
.app{ position:relative; max-width:1180px; margin:0 auto; padding:16px 14px 90px; }
```

## Vidrio en dos capas: `.shell` y `.content-glass`

> **Antes que nada, la trampa que estas dos clases esconden.** Declaran **solo la superficie de vidrio** —fondo, blur, borde, sombra, brillo especular— y **ninguna de las dos pone `border-radius` ni `padding`.** Es a propósito: un chip de activo, una fila de listado, un panel de pantalla y un modal necesitan medidas distintas, así que ponerlas en la clase base obligaría a pisarlas en todos los casos menos uno.
>
> La consecuencia es que **todo** lo que se combine con `.shell` o `.content-glass` tiene que declarar su radio y su padding, y si no lo hace **no falla nada**: queda una caja cuadrada con el texto pegado al borde, que se lee como HTML sin estilo. Pasó con el listado de `usuarios.html` —en la fila y en el panel que la contenía— y lo reportó el usuario, no un test. Las medidas de referencia de lo ya construido: `.detail-item` y `.fila-lista` van en `var(--r-sm)` con `padding:11-12px 12-14px`; `.panel-contenido` y las tarjetas grandes en `var(--r-card)`; `.topbar`, `.sidebar` y `.modal` en `var(--r-lg)`.
>
> Y la tipografía va junto con eso: **el dato principal de una pieza de vidrio va en Outfit**, no en Inter (`.detail-field b`, `.fila-lista-dato b`, `.floor-num`, `.kpi-num`). Inter queda para la línea de datos secundarios. La regla general del proyecto —Outfit para titulares y números— se aplica también adentro de una fila: el nombre es el título de ese ítem, no un dato más.

```css
.shell{
  position:relative; overflow:hidden;
  background:var(--glass-shell-bg);
  backdrop-filter:blur(var(--glass-shell-blur)) saturate(1.15);
  -webkit-backdrop-filter:blur(var(--glass-shell-blur)) saturate(1.15);
  border:1px solid var(--line);
  box-shadow:var(--glass-in), var(--sh-md);
}
.shell::before{ content:""; position:absolute; inset:0; background:var(--glass-sheen); pointer-events:none; }
@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){
  .shell{ background:var(--glass-shell-fallback); }
  .content-glass{ background:var(--glass-content-fallback)!important; }
}
.content-glass{
  background:var(--glass-content-bg);
  backdrop-filter:blur(var(--glass-content-blur));
  -webkit-backdrop-filter:blur(var(--glass-content-blur));
  border:1px solid var(--line-2);
  box-shadow:var(--glass-in);
}
```

Regla de aplicación: `.shell` para el contenedor grande (topbar, cada `.kpi`, `.visual-card`, `.detail`). `.content-glass` para lo que va DENTRO con más densidad de texto (`.unit-card`, `.asset-chip`, `.detail-field`, `.detail-item`). Nunca blur fuerte detrás de una grilla de texto chico.

## Topbar

```html
<header class="topbar shell">
  <div class="brand">
    <span class="brand-mark">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8"><path d="M4 21V6l8-3 8 3v15"/><path d="M9 21v-6h6v6"/><path d="M9 10h.01M15 10h.01M9 14h.01M15 14h.01"/></svg>
    </span>
    <div class="brand-text"><b>Torre Central</b><span>SMART Building · Panel administrador</span></div>
  </div>
  <div class="topbar-actions">
    <button class="icon-btn" aria-label="Notificaciones">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M6 8a6 6 0 1112 0c0 5 2 6 2 6H4s2-1 2-6"/><path d="M10 20a2 2 0 004 0"/></svg>
      <span class="badge">6</span>
    </button>
    <button class="icon-btn" aria-label="Cambiar tema" id="theme-toggle">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
    </button>
    <div class="avatar">AC</div>
  </div>
</header>
```

```css
.topbar{ display:flex; align-items:center; justify-content:space-between; gap:12px; padding:12px 16px; border-radius:var(--r-lg); }
.brand{ display:flex; align-items:center; gap:11px; min-width:0; }
.brand-mark{
  width:38px; height:38px; border-radius:13px; flex:none;
  background:linear-gradient(155deg, var(--accent), var(--accent-2));
  display:grid; place-items:center;
  box-shadow:var(--glass-in), 0 6px 16px -4px rgba(var(--shadow-rgb),.35);
  position:relative; overflow:hidden;
}
.brand-mark::after{ content:""; position:absolute; inset:0; background:linear-gradient(125deg, rgba(255,255,255,.55), transparent 50%); }
.brand-mark svg{ width:19px; height:19px; stroke:#fff; position:relative; }
.brand-text b{ display:block; font-family:Outfit; font-size:16.5px; font-weight:700; }
.brand-text span{ display:block; font-size:10.5px; color:var(--ink-3); letter-spacing:.04em; }
.topbar-actions{ display:flex; align-items:center; gap:8px; flex:none; }
.icon-btn{
  position:relative; width:38px; height:38px; border-radius:13px;
  background:var(--glass-content-bg); border:1px solid var(--line); box-shadow:var(--glass-in);
  color:var(--ink-2); display:grid; place-items:center; cursor:pointer; transition:transform .18s ease-out;
}
.icon-btn:hover{ transform:translateY(-1px); }
.icon-btn svg{ width:16px; height:16px; }
.icon-btn .badge{
  position:absolute; top:-3px; right:-3px; min-width:15px; height:15px; padding:0 3px; border-radius:99px;
  background:var(--crit); color:#fff; font-size:9px; font-weight:800; display:grid; place-items:center;
  border:2px solid var(--bg-1);
}
.avatar{
  width:38px; height:38px; border-radius:13px;
  background:linear-gradient(155deg,#5c6469,#33383c);
  display:grid; place-items:center; font-size:12px; font-weight:700; color:#fff; box-shadow:var(--glass-in);
}
```

Íconos: siempre SVG inline con `viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7-1.8"`, nunca librería de íconos ni emoji.

**Favicon:** toda página nueva incluye `<link rel="icon" type="image/svg+xml" href="assets/img/favicon.svg">` en el `<head>` — es el `.brand-mark` de arriba reconstruido como SVG standalone (mismo degradé `155deg` acero/grafito, mismo ícono de edificio en trazo blanco), porque un favicon no puede leer las variables CSS de la página que lo referencia. No se genera un ícono nuevo por pantalla: siempre el mismo archivo, el mismo logo.

Variante chica para una acción de ícono DENTRO de una fila de listado (editar, etc.) — el tamaño de topbar (38px) es desproporcionado ahí:

```css
.icon-btn-sm{ width:32px; height:32px; border-radius:11px; flex:none; }
.icon-btn-sm svg{ width:15px; height:15px; }
```

Uso: `<button class="icon-btn icon-btn-sm" aria-label="Editar">...</button>` — mismo look que `.icon-btn` (fondo, borde, hover), solo más compacto.

## Fila de listado (`.fila-lista`)

Para cualquier pantalla "lista de cosas + alta en modal" (usuarios hoy, después proveedores, reclamos, activos...). Mismo look que `.detail-item.content-glass`.

```css
.fila-lista{ display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; }
.fila-lista-acciones{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; min-width:0; margin-left:auto; }
```

**Lección aprendida (bug real en mobile, feedback del usuario):** con un badge de texto largo (ej. "Administrador de Consorcio") + pill + botón, el conjunto de acciones puede no entrar en una línea en mobile. `flex-wrap:wrap` en `.fila-lista-acciones` es necesario para que sus hijos se acomoden en más de una línea — pero **no alcanza solo con eso**: si además tiene `flex:none` (o cualquier `flex-shrink:0`), el elemento crece a su ancho de contenido completo en vez de respetar el espacio disponible de la fila, y entonces nunca *necesita* wrappear — se sale de la tarjeta igual. `min-width:0` (más el `flex-shrink:1` default, al no poner `flex:none`) es lo que de verdad lo habilita a respetar el ancho disponible. Se verifica con un rol de texto largo específicamente — con roles cortos el bug no se nota.

**Segunda vuelta del mismo bug, un nivel más arriba (verificado en 7 anchos: 360 a 1280px):** a anchos intermedios (~480-600px) puede pasar que `.fila-lista` ENTERA envuelva — un nombre largo se queda sin lugar junto a las acciones — y `.fila-lista-acciones` cae sola a su propia línea. Con un solo elemento en esa línea, el `justify-content:space-between` de `.fila-lista` no tiene nada para distribuir entre dos y lo deja pegado a la izquierda. Por eso `margin-left:auto` va también en `.fila-lista-acciones` (no solo en las variantes internas como `.fila-lista.ocupado .fila-lista-acciones` de edificios.html, donde el badge/texto de estado Y el botón tienen que viajar SIEMPRE juntos hacia la derecha, así se pidió explícitamente) — sin `@media`, a propósito: en desktop no tiene nada que empujar (el contenedor ya mide justo su contenido) así que no cambia nada ahí, pero cubre cualquier ancho donde SÍ envuelva, no solo el que se haya probado a mano.

**Tercera vuelta — no todo lo que está en `.fila-lista-acciones` tiene que moverse junto:** en `usuarios.html` el pedido es distinto al de edificios: el badge de rol (`.fila-lista-estado`) tiene que quedar SIEMPRE a la izquierda (anclado al nombre), mientras que editar + el botón de estado (`.fila-lista-botones`) van SIEMPRE a la derecha — dos grupos independientes, no uno solo viajando junto. El `margin-left:auto` de `.fila-lista-acciones` (arriba) arrastra TODO el contenedor, badge incluido — mal acá. La regla de abajo aplica *solo* cuando el contenedor tiene adentro un `.fila-lista-botones` (o sea, solo en filas de usuario — `edificios.html` nunca tiene esa clase, así que no se pisan):

```css
.fila-lista-acciones:has(.fila-lista-botones){
  flex:1 1 auto; justify-content:space-between; margin-left:0;
}
```

En vez de empujar el contenedor entero, se lo hace crecer para ocupar toda la línea disponible (`flex:1`) y se reparten sus dos hijos con `space-between` — el rol ancla al principio de la línea que le toque (junto al nombre en desktop, solo en su propia línea en mobile angosto), los botones al final, siempre. `:has()` es lo que permite distinguir "esto es una fila de usuario" por su contenido, sin agregar una clase nueva al HTML — moderno pero ya bien soportado (Chrome/Edge/Safari/Firefox, todos desde 2023/2024).

### El resto de la pantalla de listado (construido en `usuarios.html`, F1-T13)

Las filas no van sueltas: hay cuatro piezas más que toda pantalla "lista + alta" necesita, y conviene tomarlas de acá en vez de improvisarlas.

```css
/* El contenedor de las filas. */
.lista-filas{ display:flex; flex-direction:column; gap:8px; }

/* El dato principal: nombre arriba, datos secundarios abajo. El min-width:0 es
   lo que permite que un email largo se recorte en vez de estirar la fila y
   empujar las acciones fuera de la tarjeta. */
.fila-lista-dato{ min-width:0; }
.fila-lista-dato b{ display:block; font-size:13.5px; font-weight:700; margin-bottom:2px; }
.fila-lista-dato span{ display:block; font-size:11.5px; color:var(--ink-3); overflow-wrap:anywhere; }

/* Etiqueta neutra de clasificación: un rol, una categoría, un rubro.
   NO es una .pill — las pills son el semáforo, y el semáforo es estado real
   del edificio, no una paleta para etiquetar cualquier cosa. */
.rol-badge{
  display:inline-flex; align-items:center; padding:3px 10px; border-radius:99px;
  background:var(--glass-content-bg); border:1px solid var(--line);
  color:var(--ink-2); font-size:11px; font-weight:700; white-space:nowrap;
}

/* La ranura de la izquierda del grupo de acciones. Solo posiciona: el aspecto
   lo pone .rol-badge. En la fila de usuarios van las dos juntas. */
.fila-lista-estado{ flex:none; }

/* Un registro dado de baja: atenúa sus datos. La palabra "Inactivo" la dice
   el botón de estado, no un chip aparte — ver su sección más abajo. */
.fila-lista.inactiva .fila-lista-dato{ opacity:.55; }

/* Listado sin elementos, y también el contenedor del indicador de carga. */
.lista-vacia{ padding:26px 20px; text-align:center; font-size:13px; color:var(--ink-3); }
.lista-vacia b{ display:block; margin-bottom:4px; font-size:14px; font-weight:700; color:var(--ink-2); }

/* El panel de vidrio donde vive el contenido de una pantalla de gestión.
   .shell no pone radio ni padding: este los pone. */
.panel-contenido{ padding:18px 16px; border-radius:var(--r-card); }
@media (min-width:640px){ .panel-contenido{ padding:22px 20px; } }

/* El encabezado del contenido: título, bajada y la acción principal. */
.pagina-cabecera{
  display:flex; align-items:center; justify-content:space-between;
  gap:12px; flex-wrap:wrap; margin-bottom:14px;
}
.pagina-cabecera h2{ margin:0; font-size:18px; letter-spacing:-.015em; }
.pagina-cabecera p{ margin:3px 0 0; font-size:12.5px; color:var(--ink-3); }
.pagina-cabecera .boton-primario{ width:auto; padding:10px 16px; }
@media (max-width:519px){ .pagina-cabecera .boton-primario{ width:100%; } }
```

```html
<section class="shell panel-contenido">
<div class="pagina-cabecera">
  <div>
    <h2>Usuarios del sistema</h2>
    <p>Se listan los activos y los inactivos.</p>
  </div>
  <button type="button" class="boton-primario" id="boton-nuevo">Nuevo usuario</button>
</div>

<div class="lista-filas">
  <article class="fila-lista content-glass">
    <div class="fila-lista-dato">
      <b>Ana Suárez</b>
      <span>ana@ejemplo.com · 11 5555 4444</span>
    </div>
    <div class="fila-lista-acciones">
      <span class="fila-lista-estado rol-badge">Administrador de Consorcio</span>
      <div class="fila-lista-botones"><!-- editar + estado --></div>
    </div>
  </article>
</div>
</section>
```

**Tres reglas que no son de aspecto y conviene no perder:**

1. **El badge de rol no usa el semáforo.** Un rol no es un estado. Las cuatro clases `.pill.*` quedan reservadas para severidad real del edificio; para clasificar algo hay `.rol-badge`, con vidrio y tinta neutra.
2. **Un registro inactivo se marca con la palabra "Inactivo" Y con la opacidad, nunca solo con el tono.** Es la misma regla que el semáforo: ningún estado se comunica únicamente con color o intensidad. La baja del sistema es lógica, así que el registro sigue en el listado y hace falta que se vea de un golpe de vista cuál no está activo. La palabra la pone el botón de estado (sección propia más abajo), no un chip aparte: dos elementos diciendo el mismo estado en la misma fila es lo que este componente vino a resolver.
3. **Un listado vacío explica por qué está vacío**, y cuando corresponde dice qué hacer. Nunca una lista en blanco. El mismo contenedor aloja el indicador de carga mientras se espera.

**El botón de la cabecera pasa a ancho completo por debajo de 520 px**, que es donde la cabecera envuelve: un botón angosto perdido a la izquierda de una línea vacía se lee como un error de maquetado.

### De dónde salen las opciones de un formulario de alta

Regla que fijó el alta de `usuarios.html` y que vale para cualquier formulario que ofrezca elegir entre valores que el backend define: **el catálogo lo pide el frontend, no lo escribe.**

El `<select>` de rol necesita los 8 roles con su etiqueta legible, y esas etiquetas viven en la matriz de roles del backend. Escribirlas en el JavaScript sería tener la matriz en dos lugares: el día que la Fase 11 agregue un rol, la pantalla seguiría ofreciendo ocho. Lo mismo con la ayuda de requisitos bajo el campo de contraseña — tiene que decir **lo mismo que el 422 que la rechaza, con las mismas palabras**, y eso solo se cumple si los dos leen la misma lista.

Por eso hay un endpoint que devuelve las dos cosas juntas (`GET /api/usuarios/opciones`), y se piden **al abrir el modal**, no al cargar la pantalla: la mayoría de las visitas a un listado no dan de alta a nadie. Mientras no llegan, el `<select>` y el botón de guardar quedan deshabilitados, así no se puede enviar un alta sin elegir.

```css
/* La lista de requisitos bajo el campo. Los textos NO están acá: llegan del
   backend. La viñeta se dibuja con CSS, nunca con un carácter de lista. */
.campo-requisitos{ list-style:none; margin:2px 0 0; padding:0; display:flex; flex-wrap:wrap; gap:3px 10px; }
.campo-requisitos li{ font-size:11px; color:var(--ink-3); display:flex; align-items:center; gap:4px; }
.campo-requisitos li::before{
  content:""; width:4px; height:4px; border-radius:50%; background:var(--ink-3); flex:none;
}
```

## Secciones dentro de un listado (`.lista-seccion`) y la fila que espera una decisión

Cuando las filas de un listado no son todas de la misma naturaleza, el listado se parte en bloques con su propio encabezado. Primer uso: las cuentas que esperan aprobación contra las que ya tienen rol (`usuarios.html`, `F1-T16B`). Sirve igual para "reclamos abiertos" contra "cerrados", o "activos por vencer" contra el resto.

```html
<section class="lista-seccion" id="seccion-pendientes" hidden>
  <h3 class="lista-seccion-titulo">
    Esperando aprobación
    <span class="contador" data-contador-pendientes></span>
  </h3>
  <p class="lista-seccion-nota">Se registraron desde la pantalla de inicio y todavía no tienen rol.</p>
  <div class="lista-filas" id="lista-pendientes"></div>
</section>

<article class="fila-lista content-glass pendiente">…</article>
```

```css
.lista-seccion{ margin-bottom:18px; }
.lista-seccion-titulo{
  display:flex; align-items:center; gap:8px; margin:0 0 3px;
  font-family:Outfit,ui-sans-serif,system-ui,sans-serif;
  font-size:14.5px; font-weight:700; letter-spacing:-.015em;
}
.lista-seccion-nota{ margin:0 0 10px; font-size:12.5px; line-height:1.5; color:var(--ink-3); }

.contador{
  display:inline-flex; align-items:center; justify-content:center;
  min-width:22px; padding:2px 7px; border-radius:99px;
  background:var(--glass-content-bg); border:1px solid var(--line);
  color:var(--ink-2);
  font-family:Inter,ui-sans-serif,system-ui,sans-serif;
  font-size:11.5px; font-weight:700;
}

.fila-lista.pendiente{
  border-color:var(--accent-ring);
  box-shadow:var(--sh-sm), 0 0 0 1px var(--accent-ring);
}
.fila-lista.pendiente:hover{ border-color:var(--accent); }
```

**El bloque entero se esconde cuando no tiene filas**, en vez de mostrar un `.lista-vacia` adentro. Un encabezado con un "no hay nada" debajo ocupa, todos los días, el lugar de algo que hay que atender; sin pendientes, la pantalla vuelve a ser exactamente la de antes. El título del bloque de abajo ("Con rol asignado") se esconde con él: sin el bloque de arriba, el listado es la pantalla entera y ya lo titula el `<h2>`.

**El `.contador` no es una `.pill`.** Las pills son el semáforo de 4 estados, que es una regla de negocio sobre el estado del edificio; un número de filas no es un estado. Lleva el mismo vidrio y la misma tinta neutra que `.rol-badge`, con ancho mínimo de círculo para que un "1" y un "12" no cambien la altura de la línea.

**`.fila-lista.pendiente` usa el ACENTO, no el naranja del semáforo, y el borde es completo.** Dos reglas del sistema a la vez:

- **Nunca `border-left: 3px solid`.** Es el tic visual de dashboard genérico que esta skill prohíbe. El estado se comunica con borde de 4 lados más sombra proyectada del mismo color.
- **El naranja `--pend` es exclusivo de "mantenimiento en curso"**, no es un "pendiente" genérico. Una cuenta sin aprobar no es un estado del edificio, así que pintarla de naranja la pondría en la misma familia visual que una unidad con una orden de trabajo abierta. El acento vive deliberadamente fuera del semáforo, y por eso acá es el color correcto.
- Y como siempre, **el color no comunica solo**: la fila lleva además la etiqueta del rol con la palabra escrita ("Pendiente de aprobación"), que la calcula el backend.

## Grilla de KPIs (bento, no tarjetas idénticas)

```css
.kpi-grid{ display:grid; grid-template-columns:repeat(2,1fr); gap:10px; margin-top:14px; }
.kpi{ border-radius:var(--r-card); padding:15px; }
.kpi--hero{ grid-column:span 2; padding:18px; }
.kpi-label{ font-size:10.5px; font-weight:600; letter-spacing:.05em; text-transform:uppercase; color:var(--ink-3); }
.kpi-num{ font-family:Outfit; font-size:26px; font-weight:700; margin:5px 0 2px; letter-spacing:-.02em; position:relative; }
.kpi-sub{ font-size:11.5px; color:var(--ink-3); }
.kpi-metric .kpi-num{ font-size:22px; }

@media(min-width:640px){ .kpi-grid{ grid-template-columns:repeat(4,1fr); } .kpi--hero{ grid-column:span 2; } }
@media(min-width:1024px){ .kpi-grid{ grid-template-columns:repeat(6,1fr); } .kpi--hero{ grid-column:span 3; } }
```

Uso: 2 tarjetas `.kpi.kpi--hero.shell` (estado del edificio, estado financiero — con `.status-bar`/`.status-legend` o `.fin-row`/`.fin-track`/`.fin-foot` dentro) + 4 tarjetas `.kpi.kpi-metric.shell` de una sola métrica cada una. Nunca 6 tarjetas idénticas sin jerarquía.

Barra de estado (composición del edificio) y barra financiera:

```css
.status-bar{ display:flex; height:9px; border-radius:99px; overflow:hidden; margin:13px 0 10px; background:rgba(var(--shadow-rgb),.08); box-shadow:inset 0 1px 2px rgba(0,0,0,.08); }
.status-bar i{ display:block; height:100%; }
.status-legend{ display:flex; flex-wrap:wrap; gap:10px 16px; font-size:12px; color:var(--ink-2); }
.status-legend b{ color:var(--ink); }
.dot{ width:8px; height:8px; border-radius:50%; display:inline-block; margin-right:6px; box-shadow:0 0 0 3px color-mix(in srgb, currentColor 15%, transparent); }

.fin-row{ display:flex; align-items:baseline; justify-content:space-between; margin-top:10px; }
.fin-track{ height:8px; border-radius:99px; background:rgba(var(--shadow-rgb),.08); overflow:hidden; margin-top:8px; box-shadow:inset 0 1px 2px rgba(0,0,0,.08); }
.fin-fill{ height:100%; background:linear-gradient(90deg, var(--accent-2), var(--accent)); border-radius:99px; }
.fin-foot{ display:flex; justify-content:space-between; margin-top:9px; font-size:11.5px; color:var(--ink-3); }
```

## Pills de estado

```css
.pill{ display:inline-flex; align-items:center; gap:5px; padding:3px 9px; border-radius:99px; font-size:11px; font-weight:700; }
.pill.crit{ background:color-mix(in srgb, var(--crit) var(--pill-tinte), var(--mix-tint)); color:var(--crit-ink); }
.pill.warn{ background:color-mix(in srgb, var(--warn) var(--pill-tinte), var(--mix-tint)); color:var(--warn-ink); }
.pill.pend{ background:color-mix(in srgb, var(--pend) var(--pill-tinte), var(--mix-tint)); color:var(--pend-ink); }
.pill.ok{ background:color-mix(in srgb, var(--ok) var(--pill-tinte), var(--mix-tint)); color:var(--ok-ink); }
```

Uso: `<span class="pill crit">3 críticos</span>`. Es el único componente con licencia para usar los 4 colores de semáforo como fondo de texto.

**El texto NO se deriva con `color-mix` contra la tinta neutra**, y esa es la corrección del 2026-11-01. Se hacía así, y cuatro de los ocho casos (4 estados × 2 temas) no llegaban al mínimo de 4,5:1 — el peor, `.warn` en claro, quedaba en 3,72:1. La causa es estructural y no se arregla con porcentajes: el amarillo es intrínsecamente claro, así que para oscurecerlo hay que mezclarlo tanto contra el gris que deja de leerse como amarillo. Por eso cada estado tiene su token de texto (`--ok-ink` … `--crit-ink`), derivado moviendo **solo la luminosidad** del color del estado y redefinido en tema oscuro. Los ocho casos quedan entre 4,62:1 y 4,77:1.

**Y el fondo lleva `--pill-tinte`** (22% en claro, 24% en oscuro) y no un 15-16% escrito a mano: con tan poco color la pill se veía apagada incluso con el token del estado bien puesto. Cualquier componente nuevo que ponga texto sobre un fondo teñido de estado usa estas dos piezas, no un `color-mix` propio.

## Selector de vista segmentado (`view-switch`)

Base para **todo** selector de este tipo en el proyecto (a pedido explícito del usuario) — el fondo/sombra del botón activo ya no lo pinta cada botón por separado: un único **indicador que se desliza** entre opciones lo hace, con `assets/js/view-switch.js` (se engancha solo a cualquier `.view-switch` que haya en la página vía `DOMContentLoaded` — ninguna pantalla nueva llama nada a mano). Misma técnica que animaría un switch on/off (un "thumb" moviéndose entre dos posiciones), adaptada a N opciones con texto: el indicador se mueve Y cambia de ancho para calzar exacto con el botón activo, calculado desde `getBoundingClientRect()` — funciona igual con 2 o 6 opciones, de cualquier largo de texto.

```html
<!-- role="tablist" y role="tab" los pone view-switch.js si faltan, y el
     indicador tampoco va en el HTML. Esto es todo lo que escribe la pantalla. -->
<div class="view-switch">
  <button class="activo" data-vista="general">General</button>
  <button data-vista="incidentes">Incidentes</button>
  <button data-vista="deudores">Deudores</button>
  <button data-vista="mantenimiento">Mantenimiento</button>
</div>
```

```css
.view-switch{
  position:relative; display:flex; gap:4px; padding:4px;
  background:rgba(var(--shadow-rgb),.06); border-radius:99px;
  width:max-content; max-width:100%; overflow-x:auto; box-shadow:inset 0 1px 3px rgba(0,0,0,.08);
}
.view-switch-indicador{
  position:absolute; top:4px; left:0; height:calc(100% - 8px);
  background:var(--glass-content-bg); border-radius:99px; box-shadow:var(--glass-in), var(--sh-sm);
  transition:transform .32s cubic-bezier(.32,.72,0,1), width .32s cubic-bezier(.32,.72,0,1);
  pointer-events:none;
}
.view-switch button{
  position:relative; z-index:1; border:0; background:transparent; padding:8px 13px; border-radius:99px;
  font-size:12px; font-weight:600; color:var(--ink-3); cursor:pointer; white-space:nowrap; transition:color .18s;
}
.view-switch button.activo{ color:var(--accent-2); } /* el fondo/sombra ahora los da el indicador, no el botón */
/* Para la primera colocación y para el resize: el indicador aparece donde
   corresponde en vez de deslizarse desde el borde izquierdo. */
.view-switch-indicador.sin-animacion{ transition:none; }
```

**La división de responsabilidades es la clave de que esto no se pise.** `view-switch.js` se ocupa de la **piel**: qué botón se ve activo, dónde está el indicador, el `aria-selected` y el `tabindex`. La pantalla se ocupa del **dato**, con su propio listener de clic sobre los mismos botones:

```js
// La pantalla NO toca la clase .activo ni el indicador: de eso ya se
// encarga view-switch.js. Solo reacciona al cambio de vista.
document.querySelectorAll('.view-switch button').forEach(function (boton) {
  boton.addEventListener('click', function () {
    vistaActual = boton.dataset.vista;
    dibujarPisos();  // se redibuja TODO, nunca queda pegado estado de la vista anterior
  });
});
```

Y si una pantalla cambia el botón activo **por código** —restaurando un estado guardado, por ejemplo—, el indicador la sigue igual: un `MutationObserver` sobre la clase de los botones lo reposiciona sin que nadie tenga que avisar.

**Teclado, que es parte del componente y no un extra:** flechas para moverse entre opciones (circular, del último vuelve al primero), Home y End para los extremos. Solo la opción activa es tabulable (`tabindex="0"`, el resto `-1`), que es el comportamiento estándar de un grupo de pestañas y evita que un selector de seis opciones se coma seis tabs.

**Dos frames, no uno, para la colocación sin animar.** `view-switch.js` pone la clase `sin-animacion`, mide, coloca, y la saca en el frame siguiente. Tiene que ser `requestAnimationFrame` anidado dos veces: con uno solo el navegador puede no haber aplicado todavía el estilo nuevo cuando se saca la clase, y la transición se dispara igual — que es exactamente lo que se quería evitar.

**Y un reposicionamiento fácil de no prever: las fuentes.** Outfit e Inter llegan de Google Fonts *después* del `DOMContentLoaded` y cambian el ancho del texto de los botones. Sin recolocar también en el evento `load`, el indicador queda calzado para la tipografía de respaldo y desfasado para la definitiva.

**Ojo con inicializar el indicador mientras el switch está oculto** (`display:none`, ej. un panel que todavía no terminó de cargar sus datos): `getBoundingClientRect()` da todo en `0` ahí, y el indicador quedaría mal posicionado para siempre. `view-switch.js` resuelve esto con un `ResizeObserver` sobre el propio `.view-switch` en vez de calcular la posición una sola vez al cargar — se reposiciona solo (sin animar) apenas el switch pasa a tener tamaño real, y de paso cubre gratis el resize de ventana y la rotación del celular.

## Arquitectura del Dashboard Visual del edificio

Jerarquía de contenedores — no se improvisa, romperla rompe el layout responsive (Documento de Frontend, sección 6.3):

```
.visual-card (shell)
 ├─ .visual-head           → título + .view-switch
 ├─ .legend                → leyenda de los 4 colores
 ├─ .scene
 │   └─ .building (content-glass, con reflejo lateral ::after)
 │       ├─ .roof           → nombre del edificio + indicador "sistema en vivo"
 │       ├─ #floors         → un .floor por piso (generado por JS)
 │       │   └─ .floor
 │       │       ├─ .floor-row     → colapsado: número de piso + grilla de "ventanas"
 │       │       └─ .floor-body    → expandido: grilla de .unit-card
 │       └─ .lobby          → decorativo, planta baja
 └─ .assets                 → franja "Activos y equipamiento común"
     └─ .assets-row         → .asset-chip por cada activo
```

```css
.visual-card{ margin-top:14px; border-radius:var(--r-lg); overflow:hidden; }
.visual-head{ display:flex; flex-direction:column; gap:12px; padding:19px 19px 0; }
.legend{ display:flex; flex-wrap:wrap; gap:14px; align-items:center; padding:14px 19px; color:var(--ink-3); font-size:11.5px; border-bottom:1px solid var(--line-2); }

.scene{ padding:20px 14px 10px; }
.building{
  position:relative; max-width:760px; margin:0 auto; border-radius:20px 20px 0 0; overflow:hidden;
  background:var(--glass-content-bg); backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);
  border:1px solid var(--line); box-shadow:var(--glass-in);
}
.building::after{ /* reflejo lateral simulando vidrio real */
  content:""; position:absolute; inset:0; pointer-events:none; z-index:2;
  background:linear-gradient(90deg, rgba(255,255,255,.28), transparent 13%, transparent 87%, rgba(255,255,255,.16));
}
html[data-theme="dark"] .building::after{ background:linear-gradient(90deg, rgba(255,255,255,.06), transparent 13%, transparent 87%, rgba(255,255,255,.04)); }

.roof{
  position:relative; height:38px; background:linear-gradient(135deg, var(--navy), color-mix(in srgb, var(--navy) 78%, var(--accent)));
  display:flex; align-items:center; justify-content:space-between; padding:0 16px; color:#eef0f1;
  font-size:9.5px; font-weight:700; letter-spacing:.1em; text-transform:uppercase; overflow:hidden;
}
.roof .live{ color:var(--accent-2); display:flex; align-items:center; gap:5px; }
.roof .live i{ width:6px; height:6px; border-radius:50%; background:var(--accent-2); box-shadow:0 0 8px var(--accent-2); }

.floor{ position:relative; border-top:1px solid var(--line-2); z-index:1; }
.floor-row{ width:100%; border:0; background:transparent; cursor:pointer; color:inherit; text-align:left; display:grid; grid-template-columns:52px 1fr 18px; gap:10px; align-items:center; padding:11px 13px; }
.floor-windows{ display:grid; grid-template-columns:repeat(4,1fr); gap:6px; }
.window{ position:relative; min-height:38px; border-radius:11px 11px 4px 4px; display:grid; place-items:center; font-size:11px; font-weight:700; color:var(--ink); }
.chevron{ color:var(--ink-4); transition:transform .25s; justify-self:end; }
.floor.open .chevron{ transform:rotate(180deg); color:var(--accent); }

.floor-body{ display:grid; grid-template-rows:0fr; transition:grid-template-rows .32s ease; }
.floor.open .floor-body{ grid-template-rows:1fr; }
.floor-body-inner{ min-height:0; overflow:hidden; }
.units-grid{ display:grid; grid-template-columns:repeat(2,1fr); gap:8px; padding:4px 13px 16px; }
.unit-card{ border-radius:14px; padding:11px; text-align:left; cursor:pointer; transition:transform .18s ease-out, box-shadow .18s; }
.unit-card:hover{ transform:translateY(-2px); }
.unit-card.selected{ outline:2px solid var(--accent); outline-offset:1px; }

@media(min-width:640px){
  .floor-row{ grid-template-columns:78px 1fr 22px; padding:13px 22px; }
  .units-grid{ grid-template-columns:repeat(4,1fr); padding:6px 22px 20px; }
}
```

**Clases de estado — el patrón obligatorio (borde completo + sombra de color, NUNCA barra lateral):**

```css
/* Cada clase de estado declara DOS variables: el color del estado y el color
   del texto que va encima de un fondo teñido con él. Van juntas a propósito —
   si --c-ink se derivara con un color-mix sobre --c, volvería el problema de
   contraste que se corrigió en las pills. */
.s-ok{ --c:var(--ok); --c-ink:var(--ok-ink); }
.s-warn{ --c:var(--warn); --c-ink:var(--warn-ink); }
.s-pend{ --c:var(--pend); --c-ink:var(--pend-ink); }
.s-crit{ --c:var(--crit); --c-ink:var(--crit-ink); }

.window.s-ok, .window.s-warn, .window.s-pend, .window.s-crit{
  background:color-mix(in srgb, var(--c) 26%, rgba(255,255,255,.4));
  border:1px solid color-mix(in srgb, var(--c) 45%, transparent);
}
.unit-card.s-ok, .unit-card.s-warn, .unit-card.s-pend, .unit-card.s-crit,
.asset-chip.s-ok, .asset-chip.s-warn, .asset-chip.s-pend, .asset-chip.s-crit{
  border-color:color-mix(in srgb, var(--c) 46%, var(--line-2));
  box-shadow:var(--glass-in), 0 10px 22px -12px color-mix(in srgb, var(--c) 60%, transparent);
}
.unit-tag{ background:color-mix(in srgb, var(--c) var(--pill-tinte), var(--mix-tint)); color:var(--c-ink); }
```

Franja de activos:

```css
.assets{ padding:17px 19px 21px; border-top:1px solid var(--line-2); }
.assets-row{ display:flex; gap:10px; overflow-x:auto; padding-bottom:4px; }
.asset-chip{ flex:none; min-width:170px; border-radius:16px; padding:12px; }
```

## Motor de datos (JS), independiente de la piel visual

```js
const STATE_ORDER = ['ok','warn','pend','crit'];

function reclamoSeverity(u){ if(u.reclamos.some(r=>r.priority==='critico')) return 'crit'; if(u.reclamos.length) return 'warn'; return 'ok'; }
function deudaSeverity(u){ if(!u.deuda) return 'ok'; return u.deuda.months > 1 ? 'crit' : 'warn'; }
function otSeverity(u){ return u.ot ? 'pend' : 'ok'; } // SOLO ok o pend — el naranja es exclusivo de mantenimiento en curso
function maxSeverity(list){ return list.reduce((m,s) => STATE_ORDER.indexOf(s) > STATE_ORDER.indexOf(m) ? s : m, 'ok'); }

function severityForView(u, view){
  if(view === 'incidentes')     return reclamoSeverity(u);
  if(view === 'deudores')       return deudaSeverity(u);
  if(view === 'mantenimiento')  return otSeverity(u);
  return maxSeverity([reclamoSeverity(u), deudaSeverity(u), otSeverity(u)]); // vista "general": regla de precedencia
}
```

Al cambiar de vista se vuelve a ejecutar `renderFloors()` completo — nunca queda un color "pegado" de la vista anterior. En el backend, este mismo cálculo se implementa como servicio puro (`backend/app/services/`) para que el frontend real solo pinte lo que la API ya calculó — nunca se recalcula severidad en JS con datos reales, el motor de arriba es solo la referencia de la REGLA, no el lugar donde vive en producción.

## Panel de detalle (`.detail`) — hoja inferior en mobile, panel lateral en desktop

```html
<div class="backdrop" id="backdrop"></div>
<aside class="detail" id="detail">
  <div class="detail-drag"></div>
  <div class="detail-head">
    <div><h3 id="detail-title">—</h3><span id="detail-sub">—</span></div>
    <button class="detail-close" id="detail-close">✕</button>
  </div>
  <div class="detail-body" id="detail-body"></div>
</aside>
```

```css
.backdrop{ position:fixed; inset:0; z-index:40; background:transparent; pointer-events:none; }
.backdrop.open{ pointer-events:auto; } /* transparente a propósito: solo cierra al tocar afuera, nunca oscurece la pantalla */

.detail{
  position:fixed; left:0; right:0; bottom:0; max-height:85vh;
  background:var(--glass-shell-bg); backdrop-filter:blur(26px) saturate(1.15); -webkit-backdrop-filter:blur(26px) saturate(1.15);
  border-radius:24px 24px 0 0; border:1px solid var(--line); box-shadow:var(--glass-in), var(--sh-lg);
  z-index:50; transform:translateY(105%); transition:transform .34s cubic-bezier(.32,.72,0,1); overflow:auto;
}
.detail.open{ transform:translateY(0); }
.detail-drag{ width:36px; height:4px; border-radius:99px; background:var(--line); margin:10px auto; }

@media(min-width:1024px){
  .detail{ left:auto; right:24px; bottom:24px; top:24px; width:380px; border-radius:24px; transform:translateX(420px); }
  .detail.open{ transform:translateX(0); }
  .detail-drag{ display:none; }
}
```

```js
function closeDetail(){
  detailEl.classList.remove('open');
  backdropEl.classList.remove('open');
  document.querySelectorAll('.unit-card').forEach(c => c.classList.remove('selected'));
}
document.getElementById('detail-close').addEventListener('click', closeDetail);
backdropEl.addEventListener('click', closeDetail);
```

## Toggle de tema (View Transitions API, cross-fade simple + persistencia)

Implementado en `frontend/assets/js/theme.js`. La animación es la que trae el navegador por default con `document.startViewTransition()` (cross-fade) — **sin personalizar**. Se probó un barrido circular más elaborado (nace del punto del clic, con `clip-path` animado vía Web Animations API), pero **se revirtió a pedido explícito del usuario**: tuvo un bug real de `z-index` y, sobre todo, se reportó como lento específicamente en Chrome en producción. Queda anotado en el Roadmap (Fase 13) para retomarse si se decide investigar más adelante — no se vuelve a intentar sin que esa decisión se tome de nuevo explícitamente.

```js
boton.addEventListener('click', () => {
  const siguiente = raiz.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  const aplicar = () => {
    raiz.setAttribute('data-theme', siguiente);
    try { localStorage.setItem('tema', siguiente); } catch (error) { /* modo privado, etc. */ }
  };
  if (document.startViewTransition) { document.startViewTransition(aplicar); } else { aplicar(); }
});
```

**Persistencia (agregada tras un bug real reportado):** el tema se guarda en `localStorage` y se reaplica en cada página — antes se reiniciaba a claro en cada pantalla nueva (bug real: cambiar a oscuro y navegar a Edificios/Usuarios volvía a claro sin querer). Para que no se vea un parpadeo de claro antes de pasar a oscuro, la reaplicación NO puede esperar a `theme.js` (que carga al final del `<body>`) — cada HTML con sidebar tiene este script inline en el `<head>`, antes que cualquier hoja de estilo:

```html
<script>try{if(localStorage.getItem('tema')==='dark')document.documentElement.setAttribute('data-theme','dark');}catch(e){}</script>
```

Si el navegador no soporta View Transitions, el cambio de tema es instantáneo (degradación aceptable).

## Variante "piso completo" (opcional, no default)

Variante documentada: además del color por ventana/departamento, todo el piso se tiñe con el color de su estado más grave (`.floor::before`, `z-index:-1`, `color-mix(in srgb, var(--c) N%, transparent)`, intensidad progresiva 10/20/22/26% según gravedad). Se documenta acá como variante activable — el Roadmap decide si se ofrece como preferencia visual de usuario o se descarta; NO se implementa por default sin que esa decisión quede tomada primero.

## Formularios

El vocabulario base de esta skill nació resolviendo el Dashboard Visual, no un formulario. Este patrón nació en la pantalla de login y ya lo reutiliza cualquier alta (edificios, usuarios...) — se construye con los mismos tokens (`--r-sm`, `--glass-content-bg`, `--line`, `--accent`, `--crit`) para sentirse parte del mismo sistema, nunca un componente "de librería" pegado encima.

```css
.campo{ display:flex; flex-direction:column; gap:6px; margin-bottom:14px; min-width:0; }
.campo label{ font-size:12px; font-weight:600; color:var(--ink-2); }
.campo input, .campo select, .campo textarea{
  width:100%; min-width:0; box-sizing:border-box; font:inherit; padding:10px 13px; border-radius:var(--r-sm);
  background:var(--glass-content-bg); border:1px solid var(--line);
  color:var(--ink); outline:none; transition:border-color .18s, box-shadow .18s;
}
.campo input:focus, .campo select:focus, .campo textarea:focus{
  border-color:var(--accent); box-shadow:0 0 0 3px var(--accent-ring);
}

.boton-primario{
  width:100%; padding:11px; border-radius:var(--r-sm); border:0; cursor:pointer;
  background:linear-gradient(155deg, var(--accent), var(--accent-2)); color:#fff;
  font-family:Outfit; font-weight:700; font-size:14px; transition:transform .18s ease-out, opacity .18s;
}
.boton-primario:hover:not(:disabled){ transform:translateY(-1px); }
.boton-primario:disabled{ opacity:.6; cursor:default; transform:none; }

.mensaje-error{
  display:flex; align-items:center; gap:8px; padding:10px 13px; border-radius:var(--r-sm);
  background:color-mix(in srgb, var(--crit) var(--pill-tinte), var(--mix-tint));
  color:var(--crit-ink);
  font-size:13px; font-weight:600; margin-bottom:14px;
}
```

**Lección aprendida (Fase 1, alta de edificio):** dos columnas de campos lado a lado (`display:grid; grid-template-columns:1fr 1fr`) desbordan si los inputs no tienen `width:100%; min-width:0; box-sizing:border-box` explícito — sin eso, un `<input>` vuelve a su ancho intrínseco (~20 caracteres) y estira la columna más allá de la tarjeta. Ya viene resuelto en las reglas de arriba; cualquier formulario nuevo con columnas hereda el fix gratis.

`.chip-link` — enlace de navegación (no confundir con `.pill`, que es exclusivo del semáforo de estado):

```css
.chip-link{
  display:inline-flex; align-items:center; padding:8px 16px; border-radius:99px;
  font-size:12.5px; font-weight:600; color:var(--ink-2);
  background:var(--glass-content-bg); border:1px solid var(--line);
  text-decoration:none; transition:transform .18s ease-out, color .18s, border-color .18s;
}
.chip-link:hover{ transform:translateY(-1px); color:var(--accent-2); border-color:var(--accent); }
```

## Zona pre-autenticación (las tarjetas de login y registro)

La otra mitad del esqueleto, y la más chica: la única pantalla a la que se entra **sin sesión**, así que no tiene sidebar ni menú — no hay nada que navegar todavía. Es una tarjeta centrada sobre el fondo atmosférico, con la topbar de siempre arriba (marca + indicador de conexión + botón de tema, sin hamburguesa).

```html
<body class="zona-auth">
  <div class="main-column"><div class="page-content">
    <header class="topbar shell">…</header>
    <main class="auth-centro">
      <section class="tarjeta-auth shell">
        <h1>Iniciar sesión</h1>
        <p class="tarjeta-auth-sub">…</p>
        <div class="mensaje-error" role="alert" hidden>…</div>
        <form novalidate>…</form>
      </section>
    </main>
  </div></div>
</body>
```

```css
.zona-auth{ display:flex; flex-direction:column; min-height:100vh; min-height:100dvh; }
.zona-auth > .main-column, .zona-auth .page-content{ display:flex; flex-direction:column; flex:1; min-height:0; }
.auth-centro{ flex:1; display:grid; place-items:center; padding:24px 0 48px; }

.tarjeta-auth{ width:100%; max-width:396px; padding:24px 20px; border-radius:var(--r-lg); }
.tarjeta-auth h1{ font-size:21px; margin-bottom:6px; }
.tarjeta-auth-sub{ margin:0 0 20px; color:var(--ink-2); font-size:13px; line-height:1.55; }
@media (min-width: 640px){ .tarjeta-auth{ padding:30px 28px; } .tarjeta-auth h1{ font-size:24px; } }

/* Bloque de datos de la sesión iniciada: densidad de texto, va en .content-glass */
.auth-sesion{ display:flex; flex-direction:column; gap:2px; padding:13px 15px; margin-bottom:16px; border-radius:var(--r-sm); }
.auth-sesion b{ font-family:Outfit; font-size:15px; }
.auth-sesion span{ font-size:12.5px; color:var(--ink-2); }
```

**`dvh` con `vh` de respaldo, y no `vh` solo.** En mobile `100vh` cuenta también el alto que tapa la barra de direcciones del navegador, así que la tarjeta queda centrada respecto de un área más alta que la visible y se ve corrida hacia abajo. El `vh` va primero para el navegador que no entienda `dvh`.

**El padding de abajo de `.auth-centro` es el doble que el de arriba, a propósito.** Un bloque centrado matemáticamente se percibe bajo, no centrado — es el mismo ajuste óptico de cualquier composición.

**La tarjeta va en `.shell` y el bloque de datos de la sesión en `.content-glass`.** Es la regla de los dos niveles aplicada tal cual: la tarjeta es un contenedor grande de baja densidad de texto, el bloque de datos es contenido denso adentro.

**`max-width: 396px`.** Más ancha, un formulario de dos campos se ve perdido en el medio; más angosta, un email largo no entra de una línea en el input.

**TRES tarjetas excluyentes, nunca una sección vacía.** `index.html` tiene la de login, la de **registro propio** (`F1-T16B`) y la de "sesión iniciada", y `login.js` muestra una sola — nunca dos, nunca una deshabilitada. La de sesión existe porque un rol puede no tener todavía ninguna pantalla construida y la regla del proyecto prohíbe enlazar un archivo que no existe: en vez de un enlace roto, el login cierra el circuito mostrando el resultado real de `GET /auth/me`.

**Se muestran con una sola función**, no con un `hidden` por tarjeta repartido en cada rama:

```js
function mostrarSolo(cual) {
  pantalla.tarjetaLogin.hidden    = cual !== pantalla.tarjetaLogin;
  pantalla.tarjetaRegistro.hidden = cual !== pantalla.tarjetaRegistro;
  pantalla.tarjetaSesion.hidden   = cual !== pantalla.tarjetaSesion;
}
```

Con una función por tarjeta que esconde "la otra", agregar la tercera obliga a revisar que las dos viejas se acuerden de esconderla. Así, una cuarta se suma en un solo lugar. Es la misma lógica del indicador del `view-switch`: un solo elemento decide, en vez de que cada opción se pinte sola.

**El pie de la tarjeta y el enlace a la otra.** La acción secundaria de una pantalla de autenticación —"Crear una cuenta" desde el login, "Iniciar sesión" desde el registro— va en un pie separado por una línea, con aspecto de enlace y no de botón:

```html
  </form>

  <p class="tarjeta-auth-pie">
    ¿No tenés cuenta todavía?
    <button type="button" class="enlace-boton" id="boton-ir-registro">Crear una cuenta</button>
  </p>
</section>
```

```css
.tarjeta-auth-pie{
  margin:16px 0 0; padding-top:14px; border-top:1px solid var(--line);
  text-align:center; font-size:12.5px; color:var(--ink-2);
}
.enlace-boton{
  padding:0; border:0; background:none;
  color:var(--accent);
  font-family:inherit; font-size:inherit; font-weight:700;
  cursor:pointer; text-decoration:none;
  transition:color .18s ease-out;
}
.enlace-boton:hover{ color:var(--accent-2); text-decoration:underline; text-underline-offset:2px; }
.enlace-boton:focus-visible{ outline-offset:3px; border-radius:4px; }
```

Cuatro cosas que no son estéticas:

- **Es un `<button>`, no un `<a href="#">`.** No navega a ninguna URL: cambia lo que se muestra en la misma página. Un ancla agregaría una entrada al historial y ensuciaría la barra de direcciones.
- **Va FUERA del `<form>`.** Un `<button>` dentro de un formulario, sin `type="button"`, lo envía.
- **El acento de marca, nunca un azul de librería**, y el subrayado recién en hover: dentro de una tarjeta de vidrio, un subrayado permanente compite con el botón primario que está justo arriba.
- **El anillo de foco no se redefine**, solo el radio. La regla global `:focus-visible` del comienzo de `components.css` ya lo pone con `--accent`; el primer intento lo sobreescribió con `--accent-ring`, que es más tenue — o sea, empeoró lo único que hace usable este control sin mouse.

**El registro NO tiene campo de rol.** Ni visible, ni oculto, ni deshabilitado. El rol lo escribe el backend como constante y lo asigna después un administrador. Si en una pantalla de registro aparece un `<select>` de rol, no es una mejora de formulario: es un bug de seguridad. Ver el Documento Técnico, sección 4.4.

**El `autocomplete` del login es el caso opuesto al del alta de usuarios.** Acá va activo y nombrado (`username` / `current-password`): es un login de verdad y que el gestor de contraseñas lo complete es lo correcto. En el formulario de **alta** el par email + contraseña es para OTRA persona, y ahí hay que apagarlo (`off` / `new-password`) para que Chrome no lo rellene con las credenciales del administrador logueado — ver la lección del campo de contraseña, más abajo.

## Sidebar de navegación (zona autenticada) — Documento Técnico, sección 4.1

Todas las pantallas detrás de login comparten este layout: sidebar fija a la izquierda (desktop) o panel deslizante (mobile) + columna principal con su propio topbar. Arquitectura de contenedores:

```
.layout-app
 ├─ aside.sidebar (shell)
 │   ├─ .sidebar-brand        → marca, igual a la del topbar del login
 │   ├─ nav.sidebar-nav       → accesos habilitados según el rol (generado por JS)
 │   └─ .sidebar-footer       → tarjeta de usuario (nombre + rol) + botón de logout
 ├─ .sidebar-backdrop         → solo mobile, transparente, cierra el panel al tocar afuera
 └─ .main-column
     ├─ header.topbar (shell)  → botón hamburguesa (mobile) + título de la pantalla + toggle de tema
     └─ main.page-content      → contenido propio de cada pantalla
```

```css
.layout-app{ display:flex; min-height:100vh; }
.sidebar{
  width:248px; flex:none; display:flex; flex-direction:column; padding:18px 14px;
  border-radius:0; position:sticky; top:0; height:100vh; gap:18px;
}
.sidebar-brand{ display:flex; align-items:center; gap:10px; padding:0 6px; }
.sidebar-nav{ display:flex; flex-direction:column; gap:4px; flex:1; }
.sidebar-link{
  display:flex; align-items:center; gap:10px; padding:10px 12px; border-radius:var(--r-sm);
  color:var(--ink-2); font-size:13.5px; font-weight:600; text-decoration:none;
  transition:background .18s, color .18s;
}
.sidebar-link:hover{ background:var(--glass-content-bg); color:var(--ink); }
.sidebar-link.activo{ background:var(--accent-soft); color:var(--accent-2); }
.sidebar-footer{ border-top:1px solid var(--line-2); padding-top:14px; display:flex; flex-direction:column; gap:10px; }

.main-column{ flex:1; min-width:0; padding:16px 20px 60px; }

@media(max-width:1023px){
  .sidebar{
    position:fixed; left:0; top:0; bottom:0; z-index:60; width:82vw; max-width:300px;
    transform:translateX(-105%); transition:transform .3s cubic-bezier(.32,.72,0,1); border-radius:0 20px 20px 0;
  }
  .sidebar.abierta{ transform:translateX(0); }
  .sidebar-backdrop{ position:fixed; inset:0; z-index:55; background:transparent; pointer-events:none; }
  .sidebar-backdrop.abierta{ pointer-events:auto; }
}
/* La hamburguesa es un .icon-btn normal con esta clase, que solo la esconde
   en desktop. No es un botón aparte con estilos propios. */
@media(min-width:1024px){ .hamburguesa{ display:none !important; } }
```

Y las piezas internas, que genera `layout.js`:

```css
.sidebar-brand{ display:flex; align-items:center; gap:10px; padding:0 6px; text-decoration:none; }

.sidebar-link{
  display:flex; align-items:center; gap:10px; padding:10px 12px; border-radius:var(--r-sm);
  color:var(--ink-2); font-size:13.5px; font-weight:600; text-decoration:none;
  transition:background .18s ease-out, color .18s ease-out;
}
.sidebar-link:hover{ background:var(--glass-content-bg); color:var(--ink); }
.sidebar-link.activo{ background:var(--accent-soft); color:var(--accent-2); }
.sidebar-link svg{ width:17px; height:17px; flex:none; }

/* El mensaje de un rol sin pantallas habilitadas: un texto que explica, no
   un menú vacío que parece roto. */
.sidebar-vacio{
  padding:12px; border-radius:var(--r-sm); background:var(--glass-content-bg);
  color:var(--ink-3); font-size:12px; line-height:1.55;
}

/* Quién está logueado. Contenido denso: va en .content-glass. */
.sidebar-usuario{ display:flex; flex-direction:column; gap:1px; padding:10px 12px; border-radius:var(--r-sm); min-width:0; }
.sidebar-usuario b{ font-family:Outfit; font-size:13.5px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.sidebar-usuario span{ font-size:11.5px; color:var(--ink-3); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

/* El título de pantalla, en el topbar. Es un h1 real: la jerarquía de
   encabezados de cada pantalla arranca acá, no en el contenido. */
.topbar-titulo{ flex:1; min-width:0; font-size:16px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
```

El `overflow:hidden; text-overflow:ellipsis; white-space:nowrap` de `.sidebar-usuario` no es decorativo: un nombre largo de verdad empuja el ancho del sidebar y descuadra el layout entero.

`.sidebar-link.activo` usa el acento de marca y **nunca** un color del semáforo: "dónde estoy parado" no es un estado del edificio.

Mismo patrón de panel deslizante que ya usa `.detail` (sección "Panel de detalle" de este documento) — backdrop transparente que solo sirve para cerrar al tocar afuera, nunca oscurece la pantalla. Se cierra de tres formas, y las tres hacen falta: la hamburguesa, el backdrop, y Escape (la tecla que la gente aprieta sin pensar). Al cerrarlo, el foco vuelve al botón que lo abrió: si se quedara dentro de un panel cerrado, el siguiente Tab seguiría recorriendo elementos que ya no se ven.

**Lo que escribe cada pantalla, y es todo lo que escribe:**

```html
<body class="layout-app" data-pantalla="usuarios" data-titulo="Usuarios">
  <div class="main-column">
    <header class="topbar shell" data-topbar></header>
    <main class="page-content"> …contenido propio… </main>
  </div>
</body>
```

El sidebar, el backdrop y el contenido del topbar los genera `assets/js/layout.js`: guarda de sesión, pedido de `/auth/me`, armado de los accesos según el rol, marcado del activo, logout y hamburguesa. Que eso no se repita en catorce HTML es justamente el punto — un acceso nuevo se agrega en un solo lugar y aparece en toda la aplicación.

**La tabla de accesos es la única fuente del menú**, y cada fila lleva una bandera `construida`. Es lo que mantiene la regla de no enlazar nunca un archivo que todavía no existe: la fila se declara igual, con su rol y su ícono, para que la tabla se lea como el plan completo del menú; mientras el archivo no esté, el acceso no se dibuja. Cuando la pantalla se construye, se cambia ese `false` por `true` y nada más.

Ojo con lo que esa tabla **no** es: decide qué se *muestra*, no qué se puede *hacer*. El permiso real lo controla el backend en cada endpoint. Ocultar un acceso es una cortesía para no ofrecer lo que va a ser rechazado, nunca un mecanismo de seguridad — quien escriba la URL a mano llega igual a la pantalla, y ahí lo frena el backend.

**`layout.js` NO se engancha solo**, al contrario de `formularios.js` y `view-switch.js`. Montar el esqueleto implica pedir datos al backend y, si no hay sesión, sacar al usuario de la página: eso no puede pasar por el solo hecho de incluir un `<script>`. La pantalla lo pide, y además necesita el usuario que devuelve para rutear por rol:

```js
window.Layout.montar().then(function (usuario) {
  // acá recién se dibuja el contenido propio de la pantalla
});
```

Cuando no hay sesión, la promesa que devuelve **no se resuelve nunca**, y es deliberado: lo que sigue en la pantalla está encadenado a ese `.then()`, así que no resolver es lo que evita que se dibuje medio contenido mientras el navegador cambia de página.

**El sidebar se inserta ANTES de la columna principal en el DOM**, no solo en el dibujo: el orden del documento es el orden en que se recorre con Tab y el que lee un lector de pantalla. Llegar al menú después del contenido obligaría a recorrer toda la pantalla para volver a navegar.

**El nombre del usuario se escribe con `textContent`, nunca interpolado dentro de un `innerHTML`.** Lo escribió una persona en un formulario, y armar HTML con eso es exactamente cómo se inyecta un script.

## Modal de aviso (primer modal del proyecto)

Usado por primera vez para avisar que una dirección no se pudo geocodificar (alta de edificio) — reutilizable para cualquier aviso bloqueante futuro. Vidrio `.shell` centrado sobre un backdrop que sí oscurece y difumina (a diferencia del backdrop del sidebar/detail, acá es intencional: el usuario tiene que leer el aviso antes de seguir).

```css
.modal-backdrop{
  position:fixed; inset:0; z-index:80; background:rgba(0,0,0,.35);
  backdrop-filter:blur(6px) saturate(1.1); -webkit-backdrop-filter:blur(6px) saturate(1.1);
  display:flex; align-items:center; justify-content:center; padding:20px;
  opacity:0; pointer-events:none; transition:opacity .22s ease;
}
.modal-backdrop.abierto{ opacity:1; pointer-events:auto; }
.modal{
  max-width:360px; width:100%; padding:24px 22px; text-align:center;
  transform:scale(.96); transition:transform .22s ease;
  background:var(--glass-shell-fallback); /* ver "Lección aprendida" abajo — NO usar var(--glass-shell-bg) acá */
  /* Coincide con el padding:20px del backdrop (arriba+abajo=40px) para que
     el modal nunca exceda el alto visible — sin esto, contenido largo de
     verdad (detalle de una expensa con varios rubros/departamentos, en
     mobile) quedaba cortado contra los bordes de la ventana, sin forma de
     scrollear (bug real, encontrado por el usuario). */
  max-height:calc(100vh - 40px);
  overflow-y:auto;
  -webkit-overflow-scrolling:touch;
}
.modal-backdrop.abierto .modal{ transform:scale(1); }
.modal-icono{
  width:44px; height:44px; margin:0 auto 12px; border-radius:50%; display:grid; place-items:center;
  background:color-mix(in srgb, var(--warn) var(--pill-tinte), var(--mix-tint)); color:var(--warn-ink);
}
```

El ícono del modal usa `--warn` (amarillo) por default — es una advertencia recuperable ("no encontramos esa dirección, revisala"), no un error crítico del sistema (`--crit` queda reservado para eso).

**Lección aprendida (feedback real sobre el modal de alta de usuario):** `.modal` se usa siempre junto con `.shell`, que trae `background:var(--glass-shell-bg)` — blanco al 52% de opacidad. Ese valor está pensado para un `.shell` que se apoya sobre el fondo CLARO normal de la página (topbar, sidebar, panel de detalle). Pero un modal se apoya sobre su propio `.modal-backdrop`, que es OSCURO (`rgba(0,0,0,.35)`) — ese 52% blanco se mezcla con el negro de abajo y da un gris lavado, "sin los colores de la app", en vez de un blanco limpio. La regla `.modal{ background:var(--glass-shell-fallback); }` (arriba) pisa ese valor con la versión casi opaca (92%/94% según tema) — border, sombra y blur se siguen heredando de `.shell` sin cambios. Cualquier componente nuevo que combine vidrio translúcido con un backdrop oscuro tiene que aplicar el mismo criterio: el fondo del vidrio necesita ser casi opaco cuando lo que hay detrás no es el fondo claro de siempre.

## Modal de formulario — cuándo usar esto y no `.detail`

Decisión de reutilización que quedó fijada en la Fase 1 (alta de usuarios), a pedido explícito: un formulario de **alta/creación** (crear usuario, crear edificio desde una lista, etc.) usa este modal centrado — nunca el panel `.detail`. `.detail` sigue siendo el patrón correcto para **ver/editar el detalle de algo ya existente** (ficha de una unidad en el Dashboard Visual). La diferencia de fondo: perder los datos de un alta por un clic afuera es un problema real (se pierde trabajo tipeado); cerrar una ficha de solo lectura tocando afuera no pierde nada — por eso el modal de formulario **nunca se cierra tocando el backdrop**, solo con la X, "Cancelar", o completando y aceptando.

```html
<div class="modal-backdrop" id="modal-alta">
  <div class="modal modal-formulario shell">
    <button type="button" class="modal-cerrar" id="boton-cerrar-modal" aria-label="Cerrar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
    </button>
    <h3>Nuevo usuario</h3>
    <span class="modal-formulario-sub">Se crea con la contraseña que definas acá — se la comunicás vos.</span>
    <form id="form-alta">
      <!-- .campo de siempre; .form-grid-2 para pares de campos cortos -->
      <div class="modal-formulario-acciones">
        <button type="button" class="boton-primario" id="boton-cancelar" style="background:var(--glass-content-bg); color:var(--ink-2); box-shadow:inset 0 0 0 1px var(--line);">Cancelar</button>
        <button type="submit" class="boton-primario" id="boton-guardar">Crear usuario</button>
      </div>
    </form>
  </div>
</div>
```

```css
.modal.modal-formulario{ max-width:560px; padding:28px 26px 26px; text-align:left; position:relative; }
.modal-formulario h3{ margin:0 0 4px; padding-right:34px; }
.modal-formulario .modal-formulario-sub{ display:block; margin:0 0 18px; font-size:13px; color:var(--ink-3); }
.modal-cerrar{
  position:absolute; top:18px; right:18px; width:30px; height:30px; border-radius:10px; border:0;
  background:var(--glass-content-bg); box-shadow:var(--glass-in); color:var(--ink-2); font-size:13px;
  display:grid; place-items:center; cursor:pointer; transition:transform .18s ease-out;
}
.modal-cerrar:hover{ transform:translateY(-1px); }
.modal-cerrar svg{ width:14px; height:14px; }
.modal-formulario-acciones{ display:flex; gap:10px; margin-top:6px; }
.modal-formulario-acciones .boton-primario{ width:auto; flex:1; }
```

```js
function abrirModal(){ modalAlta.classList.add('abierto'); primerCampo.focus(); }
function cerrarModal(){ modalAlta.classList.remove('abierto'); formulario.reset(); }
botonNuevo.addEventListener('click', abrirModal);
botonCerrarX.addEventListener('click', cerrarModal);
botonCancelar.addEventListener('click', cerrarModal);
// A propósito: SIN listener de click en el backdrop — este modal no se
// cierra tocando afuera, a diferencia de .detail/.sidebar.
```

> **Las clases de estado van en castellano, igual que el resto del dominio.** `.abierto` / `.abierta`, `.activo`, `.inactiva`, `.selected` no — esa última es la excepción heredada del Dashboard Visual. Esta sección decía `.modal-close` y `.open`, y el CSS real dice `.modal-cerrar` y `.abierto`: se corrigió al construir el alta de `usuarios.html`, donde copiar de acá habría dado un modal que no se abre y un botón sin estilo. **Al tomar un patrón de este documento conviene verificar el nombre contra `frontend/assets/css/components.css`**, que es lo que efectivamente se sirve.

Tres cosas más que fijó el alta de `usuarios.html`:

- **La X del modal es un SVG a trazo**, no el carácter `✕`. Todo ícono del proyecto es SVG dibujado a mano; un carácter tipográfico se ve distinto en cada sistema operativo y no hereda el grosor de trazo del resto.
- **Escape cierra el modal, el backdrop no.** El backdrop no cierra porque perder un alta a medio tipear es un problema real; Escape sí, porque es una acción intencional y es lo que cualquiera espera de un diálogo. Al cerrar, el foco **vuelve al botón que lo abrió** — si no, se va al `<body>` y el siguiente Tab arranca desde el principio de la página.
- **Un error del servidor se muestra DENTRO del modal, que queda abierto con todo lo tipeado en su lugar.** Cerrarlo ante un email repetido obligaría a escribir el alta de nuevo.

Para dos campos "cortos" lado a lado dentro del formulario (Rol + Teléfono, CP + CUIT...), envolverlos en `.form-grid-2` — 1 columna en mobile, 2 columnas recién desde 480px, para que nunca deforme un input angosto en pantallas chicas:

```css
.form-grid-2{ display:grid; grid-template-columns:1fr; gap:0 12px; }
@media(min-width:480px){ .form-grid-2{ grid-template-columns:1fr 1fr; } }
```

## Enter avanza de campo (`assets/js/formularios.js`)

En todo formulario del proyecto, Enter en un campo intermedio **avanza al siguiente** en vez de enviar; solo en el último campo envía, que es el atajo que la gente espera. Nació de un bug real: se creó un edificio a medio cargar porque Enter en un campo intermedio envió el formulario entero. Quien carga datos usa Enter como separador, igual que en una planilla, y la pantalla tiene que acompañar eso.

No hay nada que llamar: el módulo escucha `keydown` **en `document`**, así que cubre igual un formulario que ya venía en el HTML y uno que se inserta después (el modal de alta), sin reinicializar nada al redibujar.

Tres exclusiones, todas necesarias:

- **`<textarea>`**: ahí Enter es un salto de línea y nada más.
- **Con modificador apretado** (Ctrl/Cmd/Alt/Shift): Ctrl+Enter para enviar es una convención extendida, no se intercepta.
- **Inputs que no son para escribir** (`submit`, `button`, `reset`, `image`, `hidden`) y los `disabled`/`readonly`.

**Trampa al armar la lista de campos: `getClientRects().length`, nunca `offsetParent`.** Para descartar los campos invisibles, el reflejo es preguntar por `offsetParent === null`. No sirve acá: un campo dentro de un contenedor con `position: fixed` —o sea, **todo modal del proyecto**— tiene `offsetParent` nulo aunque se vea perfecto, así que con ese criterio la lista de campos de un modal sale vacía y Enter deja de avanzar justo en los formularios donde más se usa.

## Campo de contraseña con mostrar/ocultar

Cualquier `<input type="password">` de la app usa esta estructura — nunca `type="text"` a secas (ni siquiera "porque es modo test", que fue el error real que corrigió este patrón).

**El botón del ojo NO se escribe en el HTML: lo genera `assets/js/formularios.js`** en todo `.campo-password-wrap` que no lo tenga. Alcanza con el envoltorio, que hace falta igual para el CSS:

```html
<div class="campo">
  <label for="campo-password">Contraseña</label>
  <!-- El <button> del ojo lo agrega formularios.js. No hace falta escribirlo. -->
  <div class="campo-password-wrap">
    <input type="password" id="campo-password" required>
  </div>
</div>
```

**Por qué cambió esto (corrección del 2026-11-06, al construir el alta de `usuarios.html`).** Antes el botón se escribía a mano en cada HTML y este documento lo mostraba así. El problema apareció enseguida: la regla "todo campo de contraseña lleva toggle" dependía de que nadie se olvidara de copiar ocho líneas de SVG, y olvidarlas **no falla nada** — deja un campo sin forma de ver lo que se escribe, y no se nota hasta que alguien se queja. Pasó exactamente eso en el primer campo de contraseña nuevo después del login. Generándolo, la regla se cumple por construcción. Es idempotente: si el botón ya está escrito, no se duplica.

Y el `aria-label` lleva eñe. Parece un detalle y no lo es: decía "Mostrar contrasenia", con la convención sin acentos del código, pero un `aria-label` no es código — es la frase que un lector de pantalla dice en voz alta.

```css
.campo-password-wrap{ position:relative; }
.campo-password-wrap input{ padding-right:42px; }
.campo-password-toggle{
  position:absolute; right:5px; top:50%; transform:translateY(-50%);
  width:28px; height:28px; border-radius:8px; border:0; background:transparent;
  color:var(--ink-3); display:grid; place-items:center; cursor:pointer; transition:color .18s;
}
.campo-password-toggle:hover{ color:var(--ink); }
.campo-password-toggle svg{ width:17px; height:17px; }
```

El ícono cambia entre ojo (contraseña oculta, invita a mostrarla) y ojo tachado (contraseña visible, invita a ocultarla) — ambos definidos como constantes `ICONO_OJO`/`ICONO_OJO_TACHADO` en `formularios.js`, expuestas también en `window.Formularios.ICONO_OJO` para quien necesite el mismo SVG fuera de ese archivo.

**Lección aprendida — nunca pisar el `innerHTML` de un elemento HTML con `<path>`/`<circle>` sueltos:** la primera versión hacía `boton.innerHTML = ICONO_OJO` (el botón, no el `<svg>` de adentro). El ícono desaparecía en el primer clic: un `<button>` es HTML, no SVG, y su parser de `innerHTML` no reconoce `<path>`/`<circle>` como elementos SVG reales fuera de un tag `<svg>` — quedan como elementos desconocidos, invisibles. Corregido apuntando al `<svg>` interno: `boton.querySelector('svg').innerHTML = ICONO_OJO`. (Sí funciona, en cambio, pisar el innerHTML con un string que incluye el `<svg>...</svg>` completo — el parser HTML sí reconoce ese tag y cambia a contexto SVG. Preferir siempre apuntar al `<svg>` existente, es más simple y no repite los atributos del tag.)

**Dos formularios de alta se completaban solos con la sesión del admin logueado:** el navegador autocompletaba Email y Contraseña del "Nuevo usuario" con las credenciales guardadas del Administrador General que inició sesión — Chrome detecta el par email+password como un formulario de login. Se corrigió con `autocomplete="off"` en el campo de email y `autocomplete="new-password"` en el de contraseña (el valor semánticamente correcto para "creando una credencial nueva", que Chrome sí respeta) más `autocomplete="off"` en el propio `<form>`. Cualquier formulario de alta que junte un campo de tipo email + uno de tipo password para una persona DISTINTA a quien está logueado necesita este mismo tratamiento.

## Texto de marca animado (`aurora-text`)

Degradé animado para una palabra puntual dentro de un título — hoy la segunda palabra de "SMART Building" en las 4 pantallas donde aparece. Adaptado de un componente de referencia que por default usa una paleta arcoíris (rosa/violeta) — la versión correcta para el proyecto la **reconstruye con únicamente `--accent`/`--accent-2`**, el acento de marca ya licenciado en la skill para esto. Nunca se usa para más de una palabra a la vez ni compite con el semáforo — es decoración de marca, no estado.

> **Estado en el código HOY (pendiente de decisión del usuario):** a pedido explícito, el CSS real en `components.css` tiene puesta la paleta ORIGINAL del componente de referencia (rosa/violeta/azules) "para ver cómo queda" — no la versión de abajo. Viola la regla de "nunca morado/rosa" de esta misma skill a propósito, como experimento visual. Antes de dar por buena esta sección hay que confirmar con el usuario si se queda así (y entonces esta skill se actualiza para reflejarlo como excepción deliberada) o si vuelve a `--accent`/`--accent-2`.

```html
<b>SMART <span class="aurora-text">Building</span></b>
```

```css
span.aurora-text{
  /* "span." explícito: sin el tipo en el selector, pierde por especificidad
     contra cualquier regla tipo ".contenedor span{ display:block }" que ya
     exista para OTRO span hermano (ej. un subtítulo) — un caso real que
     partió "SMART Building" en dos líneas la primera vez. */
  display:inline;
  background-image:linear-gradient(90deg, var(--accent), var(--accent-2), var(--accent), var(--accent-2));
  background-size:300% 100%;
  background-clip:text; -webkit-background-clip:text; color:transparent;
  animation:aurora-desplazamiento 6s ease-in-out infinite;
}
@keyframes aurora-desplazamiento{
  0%{ background-position:0% 50%; } 50%{ background-position:100% 50%; } 100%{ background-position:0% 50%; }
}
@media(prefers-reduced-motion:reduce){ .aurora-text{ animation:none; } }
```

Nunca fija su propio `font-size` — lo hereda siempre del elemento contenedor (`<b>`, `<h1>`...), así el mismo efecto sirve para un título de 14px o de 20px sin tocar la clase.

## Indicador de carga con frases rotando (`assets/js/cargando.js`)

Reemplaza cualquier "Cargando…" estático — dos frases alternando ("Cargando" / "Por favor aguarde") con puntos suspensivos animados (`.` → `..` → `...`). Se engancha solo: un único intervalo global (no un timer por instancia) recorre `document.querySelectorAll('.cargando-rotativo')` en cada tick, así funciona también con instancias insertadas después vía `innerHTML` — el caso normal acá, donde un listado se reemplaza entero al recargar.

```html
<!-- window.Cargando.html() devuelve exactamente esto -->
<span class="cargando-rotativo" role="status" aria-live="polite"><span class="cargando-texto"></span></span>
```

`role="status"` y `aria-live="polite"`: un lector de pantalla tiene que anunciar que se está esperando, si no la pantalla queda en silencio hasta que llegan los datos. `polite` y no `assertive` porque no interrumpe lo que la persona esté escuchando.

**Construido en `F1-T13`.** Dos detalles que no estaban en esta especificación y que importan: el intervalo **se apaga solo** cuando no queda ningún indicador en pantalla y se vuelve a prender con el siguiente —un intervalo vivo para siempre en una pestaña abierta todo el día es exactamente lo que después nadie encuentra—, y el primer pintado se dispara en el `requestAnimationFrame` siguiente a `html()`, porque quien la llamó todavía no insertó el elemento en el DOM; sin eso el indicador aparece vacío casi medio segundo.

```js
listaAlgo.innerHTML = `<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">${window.Cargando.html()}</p>`;
```

No fija tamaño ni color — los hereda del contenedor donde se lo inserte (un `<p>` chico para un listado, directo dentro de un `<h1>` para un título de detalle). Cada 6 ticks (~2,7s) cambia de frase con una transición de desvanecido; los ticks intermedios solo actualizan los puntos, sin transición — un parpadeo constante de "cargando" se sentiría mal si TODO se desvaneciera cada 450ms.

## Confirmación de una acción destructiva (`Confirmar.pedir`)

> **Construido en `F1-T15` (2026-11-07).** Es el único patrón de confirmación para una acción sin formulario. `window.confirm()` está prohibido en todo el proyecto.

**No se escribe el HTML de este modal en ninguna pantalla.** Se pide así, y listo:

```js
window.Confirmar.pedir({
  titulo: 'Desactivar la cuenta',
  mensaje: nombre + ' no va a poder volver a iniciar sesión. Sus datos no se ' +
           'borran y la cuenta se puede reactivar desde este mismo listado ' +
           'cuando haga falta.',
  textoAccion: 'Confirmar y desactivar'
}).then(function (confirmo) {
  if (!confirmo) return;
  // la acción
});
```

La promesa **siempre** se resuelve: cancelar devuelve `false`, no un rechazo. `destructiva: false` deja el botón con el acento en vez de rojo, para una confirmación que no destruye nada.

**Lo que hay que acertar es el texto, no el CSS.** Tres reglas:

1. **Nunca "¿Estás seguro?".** El mensaje dice QUÉ va a pasar, con el nombre de lo afectado adentro.
2. **Si se puede deshacer, decirlo.** Sin esa frase, "desactivar" se lee como "borrar" y la respuesta honesta pasa a ser cancelar siempre.
3. **El botón lleva el verbo**, no "Aceptar": leído solo, tiene que alcanzar para saber lo que hace.

**Y se pregunta solo cuando hace falta.** Desactivar pregunta, reactivar no: no destruye nada y se deshace con otro toque. Un modal que aparece siempre se cierra sin leerlo.

**Lo que ya está resuelto adentro del módulo** y no hay que volver a escribir: el foco arranca en **Cancelar** (no en la acción: un Enter de más confirmaría sin leer), Escape cancela, el velo cancela —a diferencia del modal de formulario, acá no hay nada que perder—, el foco queda atrapado entre los dos botones, y al cerrar vuelve a donde estaba. Cerrado, el modal queda `inert`: escondido con `opacity` seguía siendo alcanzable con Tab.

**`.boton-peligro`** se apoya en `.boton-primario` y solo le cambia el fondo a `var(--crit)`. Es la **segunda** licencia para usar un color del semáforo como fondo de texto (la primera es el botón de estado), y vale por lo mismo: no es decoración, y va siempre con el verbo al lado. Blanco sobre `--crit` da 5,86:1. **Su hover NO oscurece el fondo con `color-mix` contra `--mix-ink`:** ese token se invierte en tema oscuro, así que la misma regla aclararía el botón y bajaría el contraste — es la trampa que ya está anotada en `tokens.css` para el texto de las pills. El hover es el levante de siempre.

## Botón de estado con ripple (`boton-estado-usuario`)

> **Construido en `F1-T14` (2026-11-06), y esta especificación se verificó entera.** Las dos lecciones de abajo —el ripple opaco durante el crecimiento, y la transición del fondo más lenta que el ripple— se implementaron tal cual y hay comprobaciones automáticas que las fijan: una lee los `@keyframes` y verifica que al 70% ya llegó a `scale(1)` y **sigue** en `opacity:.95`; otra compara las dos duraciones como decimales y falla si la del fondo no es mayor. Sin esas guardas, alguien "limpia" el keyframe a un fade normal y el efecto vuelve a desaparecer sin que nada avise.
>
> **Tres cosas que se agregaron y que esta sección no tenía:**
> - **`prefers-reduced-motion`**: quien pide menos animación no ve el ripple. No se pierde información, porque el estado se comunica igual con el color y con la palabra.
> - **El botón se bloquea mientras viaja el pedido.** Dos clics rápidos mandarían dos cambios y el estado final dependería de cuál contestara último.
> - **Al llegar la respuesta se repinta con lo que contestó el backend**, no con lo que se supuso al hacer el cambio optimista. Si otra pestaña cambió algo en el medio, manda el servidor.
>
> Y se quitó el chip punteado de "Inactivo" que tenía la fila: este botón ya dice la palabra, y dos elementos comunicando el mismo estado en la misma fila es justamente lo que este componente vino a resolver.

Fusiona en un solo elemento lo que antes eran DOS (un `.pill` de solo lectura + un botón de acción aparte) — a pedido explícito para aliviar el mobile, donde cuatro elementos sueltos en una fila (badge + pill + ícono + botón) no entraban bien. El mismo botón **muestra** el estado actual (color + texto) Y lo **alterna** al hacer click. Primer uso: activo/inactivo en `usuarios.html` — reutilizable para cualquier estado binario futuro con la misma necesidad (verde/rojo, texto que cambia, acción = toggle).

```html
<button type="button" class="boton-estado-usuario activo boton-alternar-estado" data-id="5" data-activo="true">
  <span class="boton-estado-texto">Activo</span>
</button>
```

```css
.boton-estado-usuario{
  position:relative; overflow:hidden; border:0; cursor:pointer;
  display:inline-flex; align-items:center; justify-content:center;
  padding:8px 16px; border-radius:99px; font-size:12.5px; font-weight:700; color:#fff;
  /* MÁS LENTA que el ripple (700ms vs 550ms) a propósito — ver la
     lección de abajo, sin esto el ripple no se llega a ver */
  transition:background-color .7s ease, transform .18s ease-out;
}
.boton-estado-usuario.activo{ background:var(--ok); }
.boton-estado-usuario.inactivo{ background:var(--crit); }
.boton-estado-texto{ position:relative; z-index:1; } /* por encima del ripple */
.boton-estado-usuario .ripple{
  position:absolute; border-radius:50%; transform:scale(0); opacity:.95;
  animation:ripple-expandir .55s ease-out forwards; pointer-events:none;
}
/* Se mantiene opaco DURANTE el crecimiento, se desvanece recién al
   final (no las dos cosas a la vez) — ver la lección de abajo. */
@keyframes ripple-expandir{
  0%{ transform:scale(0); opacity:.95; }
  70%{ transform:scale(1); opacity:.95; }
  100%{ transform:scale(1); opacity:0; }
}
```

**Lección aprendida — el ripple existía pero era invisible en la práctica (reportado por el usuario: "no hace el efecto"):** la primera versión hacía crecer el círculo Y desvanecerlo a la vez, con la misma curva de tiempo (`opacity:.5→0` mientras `scale:0→1`) — para cuando el círculo llegaba a cubrir el botón, ya casi no tenía opacidad. Encima, el color del ripple es el mismo color EXACTO al que el fondo del botón también está transicionando al mismo tiempo — dos efectos idénticos en color, compitiendo por el mismo resultado final, se anulan visualmente entre sí. La corrección tiene dos partes: (1) el ripple se mantiene bien opaco durante todo el crecimiento y se desvanece solo en el último tramo, cuando ya cubrió el botón entero — así se ve claramente como una ola de color, no un parpadeo; (2) la transición de `background-color` del botón se hizo más LENTA que la del ripple, para que el ripple "pinte" el botón primero y el fondo de base lo alcance después, en vez de llegar los dos juntos y neutralizarse. Se verificó con capturas en primer plano (recorte ajustado al botón) en varios puntos de la animación — no alcanza con confirmar que el elemento `.ripple` existe en el DOM, hay que ver que se note.

El ripple (adaptado de `RippleButton`) nace del punto exacto del clic, coloreado con el estado AL QUE el botón está transicionando — no un color fijo — así el ripple y la transición de `background-color` "aterrizan" juntos en el mismo color nuevo:

```js
function dispararRipple(boton, evento, color) {
  const rect = boton.getBoundingClientRect();
  const tamano = Math.max(rect.width, rect.height) * 2; // cubre el botón desde cualquier esquina
  const ripple = document.createElement('span');
  ripple.className = 'ripple';
  ripple.style.cssText = `width:${tamano}px;height:${tamano}px;left:${evento.clientX - rect.left - tamano/2}px;top:${evento.clientY - rect.top - tamano/2}px;background:${color};`;
  boton.appendChild(ripple);
  ripple.addEventListener('animationend', () => ripple.remove());
}
```

**El texto va en un `<span>` interno, nunca directo en `boton.textContent`** — si no, cada cambio de estado borraría el/los `<span class="ripple">` que estén animando en ese momento (`textContent` reemplaza TODOS los hijos, ripples incluidos). Cambio optimista: el ripple + el color nuevo aparecen al clic, sin esperar la respuesta del servidor — si la llamada falla, se revierte el color/texto (ver la lección de seguridad abajo, la razón de fondo por la que esto importa).

**Lección de seguridad real, encontrada probando este mismo botón — no algo teórico:** el primer intento de esta funcionalidad no tenía ningún resguardo contra que un usuario se desactivara A SÍ MISMO. Al probar el botón sobre la fila del propio Administrador General logueado, la cuenta quedó realmente desactivada — y como el login rechaza usuarios inactivos, y hace falta ser `admin_general` para reactivar a alguien, **la cuenta quedó bloqueada sin ninguna forma de volver a entrar** (se reparó a mano, directo en la base de datos, para poder seguir probando). Corregido en dos capas: el **backend** rechaza con 400 tanto `POST /usuarios/{id}/desactivar` como `PATCH /usuarios/{id}` con `activo:false` cuando `usuario_id` es el mismo que el usuario autenticado; el **frontend** además deshabilita el botón en la propia fila del usuario logueado, con un `title` explicando por qué, para no dejar ni intentarlo. Cualquier acción de "desactivar/eliminar/degradar" sobre uno mismo necesita este mismo resguardo doble — nunca confiar solo en el frontend para una regla de este tipo.

## Formato de moneda (`assets/js/moneda.js`)

`financiero.html` es la primera pantalla que muestra dinero real — se centralizó el formato en vez de dejar que cada pantalla nueva (Expensas, Pagos, Deudores...) arme su propio `Intl.NumberFormat` suelto:

```js
const FORMATEADOR_ARS = new Intl.NumberFormat('es-AR', {
  style: 'currency', currency: 'ARS', minimumFractionDigits: 2, maximumFractionDigits: 2,
});
window.Moneda = { formatear: (valor) => FORMATEADOR_ARS.format(Number(valor) || 0) };
```

Un monto en una fila de listado va en `Outfit` (números, igual que un KPI), nunca en `Inter` — `font-family:Outfit, sans-serif; font-weight:700;` sobre el `<span>` del monto.

**Fechas `YYYY-MM-DD` del backend: nunca pasarlas por `new Date()` directo.** `new Date('2026-08-05')` se interpreta como medianoche UTC — con la zona horaria de Argentina (UTC-3), `toLocaleDateString()` la muestra un día antes de la fecha real. Se resuelve separando el string a mano:

```js
function formatearFecha(fechaISO) {
  const [anio, mes, dia] = fechaISO.split('-');
  return `${dia}/${mes}/${anio}`;
}
```

## Campo de monto editable, con separador de miles en vivo (`assets/js/monto-input.js`)

Para cualquier `<input>` donde el usuario CARGA un monto (a diferencia de `moneda.js`, que es solo para MOSTRAR uno ya guardado) — pedido explícito del usuario tras usar "Nuevo gasto" y ver que el monto se tipeaba sin ningún separador. `<input type="number">` no sirve acá: ese tipo nativo no admite ningún separador de miles mientras se tipea (su value model es siempre un número sin agrupar) — hace falta `type="text"` con formateo propio:

```html
<input type="text" inputmode="decimal" id="campo-gasto-monto" required placeholder="0,00">
```

```js
window.MontoInput.habilitar(document.getElementById('campo-gasto-monto')); // una vez, al configurar el modal
// al leer el valor para mandarlo a la API:
window.MontoInput.aNumero(input.value); // "1.234.567,89" -> 1234567.89
// al precargar el campo (ej. abrir "Editar gasto" con datos ya guardados):
input.value = window.MontoInput.formatearParaInput(gasto.monto); // 1234567.89 -> "1.234.567,89"
```

`inputmode="decimal"` mantiene el teclado numérico en mobile aunque el tipo real sea texto. El formateo reescribe el campo en cada tecleo (separador de miles `.` agregado solo, separador decimal `,` tal como lo escribe el usuario) y reposiciona el cursor según cuánto cambió el largo total — mismo truco que cualquier campo que se reformatea a sí mismo. Con esto ya no hace falta `required`/`min`/`step` de `type="number"`: el `required` sigue funcionando igual en `type="text"`, y un monto inválido (0, vacío) lo rechaza el backend con su mensaje de siempre en `.mensaje-error`.

## Select chico de filtro (`.campo-select-chico`)

Para filtros en línea junto a otros controles (año/mes en un listado, por ejemplo) — mismo peso visual que `.chip-link` (píldora, vidrio, borde fino) pero es un `<select>` real, no un link. Distinto de `.campo select` (esa es de ancho completo, con label, para formularios de alta):

```css
.campo-select-chico{
  font:inherit; font-size:12.5px; font-weight:600; padding:8px 30px 8px 14px; border-radius:99px;
  background:var(--glass-content-bg); border:1px solid var(--line); color:var(--ink-2);
  outline:none; cursor:pointer; appearance:none; -webkit-appearance:none;
  background-image:url("data:image/svg+xml,..."); /* chevron, ver components.css */
  background-repeat:no-repeat; background-position:right 10px center; background-size:13px;
}
```

**Excepción reconocida a la regla de "nunca un color fijo suelto":** el chevron del `<select>` es un SVG embebido como `data:` URI en `background-image` — no puede leer variables CSS (`var(--ink-3)`), así que su `stroke` queda en un gris neutro fijo (`#888`). Es una limitación técnica real de la propiedad `background-image`, no una excepción de comodidad — se probó que ese gris puntual queda legible tanto en tema claro como oscuro (a diferencia de un color con licencia de marca o de semáforo, que si necesitan variar si o si entre temas). Cualquier otro color de la regla — fondo, borde, texto — sigue token normal.

## Botón chico de acción en una fila (`.boton-chico`)

Para una acción que aparece junto a otras dentro de una fila de listado (ej. "Confirmar"/"Rechazar" en la cola de conciliación de pagos) — mismo lenguaje visual que `.boton-primario` pero de ancho natural, para que quepan dos o más en la misma fila sin ocupar todo el ancho:

**Es un MODIFICADOR, no un botón suelto.** Se escribió al construir el primer caso real (aprobar/rechazar una cuenta pendiente, `F1-T16B`) y ahí quedó claro que la forma correcta es acompañar a `.boton-primario`, igual que `.boton-secundario`: solo cambia el ancho, el relleno y un punto de tipografía, y hereda el degradé, la sombra y el hover sin copiarlos.

```html
<button type="button" class="boton-primario boton-chico">Aprobar</button>
<button type="button" class="boton-primario boton-secundario boton-chico">Rechazar</button>
```

```css
.boton-chico{ width:auto; flex:none; padding:8px 14px; font-size:12.5px; }
```

`.boton-primario` nace de ancho completo porque su lugar natural es el pie de un formulario; dentro de una fila tiene que acompañar al dato, no empujarlo. Es la misma excepción que ya hacía `.pagina-cabecera .boton-primario`, ahora nombrada para usarla donde no hay un contenedor que la implique.

**La variante `-critico` sigue especificada y sin escribir, a propósito.** Cuando apareció el primer "Rechazar" real quedó claro que no la necesitaba: el rojo le corresponde al botón del modal de confirmación —que ya lo pone `Confirmar.pedir()`—, no a una fila de listado que no tiene nada mal. Una fila con un botón rojo por cada solicitud pendiente pinta de alarma una lista donde no pasó nada. Se escribe el día que algo la pida de verdad; mientras tanto, la acción negativa va con `.boton-secundario`.

## Dato copiable (`.dato-copiable` + `assets/js/copiar.js`)

Para un dato que el usuario necesita copiar y pegar en otro lado — el caso de origen es el CBU/alias del edificio al cargar un pago (sin QR, decisión final del usuario, ver `Pagos_y_Conciliacion.md`): etiqueta chica arriba, valor destacado abajo, botón de copiar (`.icon-btn.icon-btn-sm`) siempre a la derecha, dentro de un `.detail-item.content-glass`:

```html
<div class="detail-item content-glass">
  <div class="dato-copiable">
    <div>
      <div class="dato-copiable-label">CBU</div>
      <div class="dato-copiable-valor">0170099220000001234567</div>
    </div>
    <button type="button" class="icon-btn icon-btn-sm" aria-label="Copiar CBU">...</button>
  </div>
</div>
```

`assets/js/copiar.js` (`window.Copiar.alPortapapeles(boton, texto)`) hace el `navigator.clipboard.writeText` y da feedback inmediato: el ícono cambia a un check por 1.5s y el `aria-label` pasa a "Copiado" — heurística "visibilidad del estado del sistema", el usuario nunca se queda sin saber si el click copió algo de verdad. Si el navegador no da permiso de portapapeles, el botón simplemente no da feedback — no rompe el resto del flujo.

## Lista numerada dentro de un bloque (`.bloque-lista`)

Para enumerar opciones o pasos dentro de un bloque de formulario. Nació el 2026-11-12 con las tres formas de cargar un coeficiente, que estaban escritas como un párrafo corrido: **una enumeración en prosa obliga a leerla entera para encontrar la opción que se busca.**

```html
<p class="bloque-nota">Los coeficientes se pueden cargar de tres maneras:</p>
<ol class="bloque-lista">
  <li><b>A mano, unidad por unidad.</b> Es la que refleja el reglamento del consorcio.</li>
  <li><b>Con un reparto automático.</b> En partes iguales, o por metro cuadrado — este último necesita las superficies ya cargadas.</li>
  <li><b>Cargando algunas a mano y completando el resto.</b> Reparte lo que falta entre las unidades que quedaron en blanco <i>(no toca ninguna de las que ya cargaste)</i>.</li>
</ol>
```

Es la hermana de `.campo-requisitos` —misma familia, mismo gris— pero en bloque y numerada: ahí los requisitos son equivalentes entre sí y van en línea, acá cada ítem es una alternativa distinta y el número sirve para referenciarla ("la tercera opción"). **El número se dibuja con `counter()`** sobre un círculo de `--accent-soft` con texto `--accent-2` (5,89:1 en claro, 8,72:1 en oscuro), no con el marcador nativo de `<ol>`, que no se puede alinear ni tipografiar.

**Tres niveles de énfasis sin inventar tamaños nuevos:** el título del ítem en `--ink-2` con `<b>`, el cuerpo en `--ink-3`, y la aclaración entre paréntesis **en el mismo `--ink-3`** — no en `--ink-4`. Ese token es para placeholders e iconografía apagada (2,13:1 sobre el vidrio) y una aclaración del tipo "no toca ninguna de las que ya cargaste" es justamente la frase que hay que poder leer. El menor énfasis lo dan los paréntesis, que es tipografía y no color.

## Cómo se muestra un error del backend (`.mensaje-error`) — regla fija

**Hay un solo formato y no se discute por pantalla.** Todo error que devuelve la API se muestra en un `.mensaje-error` (ícono + texto, tono `--crit`), ubicado **donde ocurrió la acción**:

| Dónde falló | Dónde va el aviso |
|---|---|
| Al guardar un formulario en un modal | **Dentro del modal**, arriba del formulario. El modal **no se cierra**: lo tipeado queda en su lugar. |
| Al traer un listado | Arriba de la lista, y la lista se **vacía** — dejar las filas viejas debajo de un error de recarga muestra datos que ya no se sabe si siguen siendo ciertos. |
| Al guardar un bloque de una pantalla con pestañas | Arriba de las pestañas, con `scrollIntoView` si quedó fuera de la vista: un error que no se ve es un error que no existe para quien aprieta el botón por segunda vez. |

**Tres cosas que nunca se hacen:** inventar otro formato de aviso para una pantalla nueva, mandar el error solo a la consola, y usar `alert()` (los diálogos nativos están prohibidos en todo el proyecto).

**El texto es el que mandó el servidor, sin reescribir.** Desde `F1-T29` el backend tiene un catálogo único (`core/errores.py`): los mensajes ya vienen redactados, en castellano y con el nombre legible de cada campo. Una pantalla que redacte su propia versión de un error del backend crea una segunda fuente del mismo texto, que es exactamente lo que ese catálogo vino a eliminar. Lo que sí escribe la pantalla son sus propias validaciones previas ("Completá el nombre y el email"), que existen para no gastar un viaje de red.

**Y la pantalla decide por `error.codigo`, nunca comparando el texto.** `api.js` entrega el código estable del catálogo (`CUENTA_INHABILITADA`, `PISO_CON_UNIDADES`), y es lo que permite reaccionar distinto a dos errores del mismo código HTTP. Comparar el castellano rompe la pantalla el día que alguien corrige una tilde. El primer uso real: el login no borra el campo de contraseña cuando el código es `CUENTA_INHABILITADA`, porque esa contraseña estaba bien.

## Mensaje de éxito (`.mensaje-exito`)

Misma estructura que `.mensaje-error` (ícono + texto en una fila, `border-radius:var(--r-sm)`), tono `--ok` en vez de `--crit` — para confirmar que una acción se hizo bien, no solo para avisar que algo salió mal. Primer uso: "reclamo enviado" (Fase 3).

```html
<div class="mensaje-exito">
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>
  <span>Reclamo enviado — el administrador o encargado del edificio lo va a revisar.</span>
</div>
```

## Tarjeta de opción seleccionable con descripción (`.opcion-card`)

Para elegir UNA entre pocas alternativas (2 a 4) donde cada una necesita una línea de texto explicativo — a diferencia de un `<select>` normal, que no tiene lugar para eso. Primer uso: prioridad de un reclamo (leve/medio/crítico, cada una con su explicación del Documento General 11.3) y el objetivo del reclamo (unidad propia/espacio común/edificio). Mismo mecanismo de selección que `.unit-card` del Dashboard Visual (`.selected` con outline), reutilizado acá fuera de ese contexto porque la mecánica es idéntica — se combina siempre con `.content-glass`, igual que `.unit-card`.

```html
<div class="opciones-grid opciones-grid-3">
  <button type="button" class="opcion-card content-glass" data-valor="leve">
    <span class="pill warn" style="margin-bottom:6px;">Leve</span>
    <p>No compromete a nadie más que a quien reclama, no es urgente.</p>
  </button>
  <!-- ...una .opcion-card más por alternativa... -->
</div>
```

```css
.opcion-card{
  display:block; width:100%; text-align:left; border:1px solid transparent;
  font:inherit; color:inherit; cursor:pointer;
}
.opcion-card b{ display:block; font-size:13px; margin-bottom:3px; }
.opcion-card p{ margin:0; font-size:11.5px; color:var(--ink-3); }
.opcion-card.selected{ outline:2px solid var(--accent); outline-offset:1px; }
.opciones-grid{ display:grid; grid-template-columns:1fr; gap:8px; }
@media(min-width:560px){ .opciones-grid.opciones-grid-3{ grid-template-columns:repeat(3,1fr); } }
```

```js
grid.querySelectorAll('.opcion-card').forEach((boton) => {
  boton.addEventListener('click', () => {
    valorElegido = boton.dataset.valor;
    grid.querySelectorAll('.opcion-card').forEach((b) => b.classList.toggle('selected', b === boton));
  });
});
```

El texto de cada opción (`<b>`/`<p>`, o un `.pill` + `<p>` para agregar color de semáforo cuando corresponde, como en prioridad) queda a criterio de cada uso — la clase solo resuelve la mecánica de selección y el look de tarjeta, no el contenido.

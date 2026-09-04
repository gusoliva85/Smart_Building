# Componentes — SMART Building (ver3)

Patrones de interacción con su HTML/CSS/JS de referencia, extraídos literalmente de `documentacion/mockups/Mockup_3D_Vidrio_Grafito.html`. Cada pantalla nueva copia y adapta estos bloques — no los reinventa. Los tokens usados acá están definidos en `paleta-color.md`.

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
.fila-lista-acciones{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; min-width:0; }
```

**Lección aprendida (bug real en mobile, feedback del usuario):** con un badge de texto largo (ej. "Administrador de Consorcio") + pill + botón, el conjunto de acciones puede no entrar en una línea en mobile. `flex-wrap:wrap` en `.fila-lista-acciones` es necesario para que sus hijos se acomoden en más de una línea — pero **no alcanza solo con eso**: si además tiene `flex:none` (o cualquier `flex-shrink:0`), el elemento crece a su ancho de contenido completo en vez de respetar el espacio disponible de la fila, y entonces nunca *necesita* wrappear — se sale de la tarjeta igual. `min-width:0` (más el `flex-shrink:1` default, al no poner `flex:none`) es lo que de verdad lo habilita a respetar el ancho disponible. Se verifica con un rol de texto largo específicamente — con roles cortos el bug no se nota.

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
.pill.crit{ background:color-mix(in srgb, var(--crit) 15%, var(--mix-tint)); color:color-mix(in srgb, var(--crit) 80%, var(--mix-ink)); }
.pill.warn{ background:color-mix(in srgb, var(--warn) 16%, var(--mix-tint)); color:color-mix(in srgb, var(--warn) 78%, var(--mix-ink)); }
.pill.pend{ background:color-mix(in srgb, var(--pend) 16%, var(--mix-tint)); color:color-mix(in srgb, var(--pend) 78%, var(--mix-ink)); }
.pill.ok{ background:color-mix(in srgb, var(--ok) 15%, var(--mix-tint)); color:color-mix(in srgb, var(--ok) 78%, var(--mix-ink)); }
```

Uso: `<span class="pill crit">3 críticos</span>`. Es el único componente con licencia para usar los 4 colores de semáforo como fondo de texto.

## Selector de vista segmentado (`view-switch`)

Base para **todo** selector de este tipo en el proyecto (a pedido explícito del usuario) — el fondo/sombra del botón activo ya no lo pinta cada botón por separado: un único **indicador que se desliza** entre opciones lo hace, con `assets/js/view-switch.js` (se engancha solo a cualquier `.view-switch` que haya en la página vía `DOMContentLoaded` — ninguna pantalla nueva llama nada a mano). Misma técnica que animaría un switch on/off (un "thumb" moviéndose entre dos posiciones), adaptada a N opciones con texto: el indicador se mueve Y cambia de ancho para calzar exacto con el botón activo, calculado desde `getBoundingClientRect()` — funciona igual con 2 o 6 opciones, de cualquier largo de texto.

```html
<div class="view-switch" role="tablist" id="view-switch">
  <button class="active" data-view="general">General</button>
  <button data-view="incidentes">Incidentes</button>
  <button data-view="deudores">Deudores</button>
  <button data-view="mantenimiento">Mantenimiento</button>
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
.view-switch button.active{ color:var(--accent-2); } /* el fondo/sombra ahora los da el indicador, no el botón */
```

```js
// view-switch.js crea el <span class="view-switch-indicador"> solo — no
// va en el HTML. La lógica de negocio de cada pantalla (marcar .active,
// re-renderizar la vista) sigue siendo responsabilidad de esa pantalla,
// con su propio listener de click en los mismos botones — los dos
// conviven sin pisarse, uno mueve el indicador, el otro cambia el dato.
document.querySelectorAll('#view-switch button').forEach(btn => btn.addEventListener('click', () => {
  document.querySelectorAll('#view-switch button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentView = btn.dataset.view;
  renderFloors(); // se re-renderiza TODO, nunca queda estado de vista anterior pegado
}));
```

**Ojo con inicializar el indicador mientras el switch está oculto** (`display:none`, ej. un panel que todavía no terminó de cargar sus datos): `getBoundingClientRect()` da todo en `0` ahí, y el indicador quedaría mal posicionado para siempre. `view-switch.js` resuelve esto con un `ResizeObserver` sobre el propio `.view-switch` en vez de calcular la posición una sola vez al cargar — se reposiciona solo (sin animar) apenas el switch pasa a tener tamaño real, y de paso cubre gratis el resize de ventana y la rotación del celular.

## Arquitectura del Dashboard Visual del edificio

Jerarquía de contenedores — no se improvisa, romperla rompe el layout responsive (Documento Técnico, sección 1.3.8):

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
.s-ok{ --c:var(--ok); } .s-warn{ --c:var(--warn); } .s-pend{ --c:var(--pend); } .s-crit{ --c:var(--crit); }

.window.s-ok, .window.s-warn, .window.s-pend, .window.s-crit{
  background:color-mix(in srgb, var(--c) 26%, rgba(255,255,255,.4));
  border:1px solid color-mix(in srgb, var(--c) 45%, transparent);
}
.unit-card.s-ok, .unit-card.s-warn, .unit-card.s-pend, .unit-card.s-crit,
.asset-chip.s-ok, .asset-chip.s-warn, .asset-chip.s-pend, .asset-chip.s-crit{
  border-color:color-mix(in srgb, var(--c) 46%, var(--line-2));
  box-shadow:var(--glass-in), 0 10px 22px -12px color-mix(in srgb, var(--c) 60%, transparent);
}
.unit-tag{ background:color-mix(in srgb, var(--c) 18%, var(--mix-tint)); color:color-mix(in srgb, var(--c) 78%, var(--mix-ink)); }
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

Implementado en `frontend/assets/js/theme.js`. La animación es la que trae el navegador por default con `document.startViewTransition()` (cross-fade) — **sin personalizar**. Se probó un barrido circular más elaborado (nace del punto del clic, con `clip-path` animado vía Web Animations API — documentado en `que_hice.html`, slide `f12-t2`), pero **se revirtió a pedido explícito del usuario**: tuvo un bug real de `z-index` y, sobre todo, se reportó como lento específicamente en Chrome en producción. Queda anotado en el Roadmap (Fase 13) para retomarse si se decide investigar más adelante — no se vuelve a intentar sin que esa decisión se tome de nuevo explícitamente.

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

Existe `documentacion/mockups/Mockup_3D_Vidrio_Grafito_PisoCompleto.html`, donde además del color por ventana/departamento, todo el piso se tiñe con el color de su estado más grave (`.floor::before`, `z-index:-1`, `color-mix(in srgb, var(--c) N%, transparent)`, intensidad progresiva 10/20/22/26% según gravedad). Se documenta acá como variante activable — el Roadmap decide si se ofrece como preferencia visual de usuario o se descarta; NO se implementa por default sin que esa decisión quede tomada primero.

## Formularios (no viene del mockup — primer patrón agregado en la Fase 1)

El mockup base solo resolvía el Dashboard Visual, nunca un formulario. Este patrón nació en la pantalla de login y ya lo reutiliza cualquier alta (edificios, usuarios...) — se construye con los mismos tokens (`--r-sm`, `--glass-content-bg`, `--line`, `--accent`, `--crit`) para sentirse parte del mismo sistema, nunca un componente "de librería" pegado encima.

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
  background:color-mix(in srgb, var(--crit) 15%, var(--mix-tint));
  color:color-mix(in srgb, var(--crit) 80%, var(--mix-ink));
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
  .sidebar.open{ transform:translateX(0); }
  .sidebar-backdrop{ position:fixed; inset:0; z-index:55; background:transparent; pointer-events:none; }
  .sidebar-backdrop.open{ pointer-events:auto; }
  .hamburger-btn{ display:grid; }
}
@media(min-width:1024px){ .hamburger-btn{ display:none; } }
```

Mismo patrón de panel deslizante que ya usa `.detail` (sección "Panel de detalle" de este documento) — backdrop transparente que solo sirve para cerrar al tocar afuera, nunca oscurece la pantalla. Se monta con `assets/js/layout.js`, que hace la guarda de sesión, pide `/auth/me`, arma los accesos según el rol y engancha el logout — cada pantalla nueva lo importa, ninguna reescribe esta lógica.

## Modal de aviso (primer modal del proyecto)

Usado por primera vez para avisar que una dirección no se pudo geocodificar (alta de edificio) — reutilizable para cualquier aviso bloqueante futuro. Vidrio `.shell` centrado sobre un backdrop que sí oscurece y difumina (a diferencia del backdrop del sidebar/detail, acá es intencional: el usuario tiene que leer el aviso antes de seguir).

```css
.modal-backdrop{
  position:fixed; inset:0; z-index:80; background:rgba(0,0,0,.35);
  backdrop-filter:blur(6px) saturate(1.1); -webkit-backdrop-filter:blur(6px) saturate(1.1);
  display:flex; align-items:center; justify-content:center; padding:20px;
  opacity:0; pointer-events:none; transition:opacity .22s ease;
}
.modal-backdrop.open{ opacity:1; pointer-events:auto; }
.modal{
  max-width:360px; width:100%; padding:24px 22px; text-align:center;
  transform:scale(.96); transition:transform .22s ease;
  background:var(--glass-shell-fallback); /* ver "Lección aprendida" abajo — NO usar var(--glass-shell-bg) acá */
}
.modal-backdrop.open .modal{ transform:scale(1); }
.modal-icono{
  width:44px; height:44px; margin:0 auto 12px; border-radius:50%; display:grid; place-items:center;
  background:color-mix(in srgb, var(--warn) 16%, var(--mix-tint)); color:color-mix(in srgb, var(--warn) 75%, var(--mix-ink));
}
```

El ícono del modal usa `--warn` (amarillo) por default — es una advertencia recuperable ("no encontramos esa dirección, revisala"), no un error crítico del sistema (`--crit` queda reservado para eso).

**Lección aprendida (feedback real sobre el modal de alta de usuario):** `.modal` se usa siempre junto con `.shell`, que trae `background:var(--glass-shell-bg)` — blanco al 52% de opacidad. Ese valor está pensado para un `.shell` que se apoya sobre el fondo CLARO normal de la página (topbar, sidebar, panel de detalle). Pero un modal se apoya sobre su propio `.modal-backdrop`, que es OSCURO (`rgba(0,0,0,.35)`) — ese 52% blanco se mezcla con el negro de abajo y da un gris lavado, "sin los colores de la app", en vez de un blanco limpio. La regla `.modal{ background:var(--glass-shell-fallback); }` (arriba) pisa ese valor con la versión casi opaca (92%/94% según tema) — border, sombra y blur se siguen heredando de `.shell` sin cambios. Cualquier componente nuevo que combine vidrio translúcido con un backdrop oscuro tiene que aplicar el mismo criterio: el fondo del vidrio necesita ser casi opaco cuando lo que hay detrás no es el fondo claro de siempre.

## Modal de formulario — cuándo usar esto y no `.detail`

Decisión de reutilización que quedó fijada en la Fase 1 (alta de usuarios), a pedido explícito: un formulario de **alta/creación** (crear usuario, crear edificio desde una lista, etc.) usa este modal centrado — nunca el panel `.detail`. `.detail` sigue siendo el patrón correcto para **ver/editar el detalle de algo ya existente** (ficha de una unidad en el Dashboard Visual). La diferencia de fondo: perder los datos de un alta por un clic afuera es un problema real (se pierde trabajo tipeado); cerrar una ficha de solo lectura tocando afuera no pierde nada — por eso el modal de formulario **nunca se cierra tocando el backdrop**, solo con la X, "Cancelar", o completando y aceptando.

```html
<div class="modal-backdrop" id="modal-alta">
  <div class="modal modal-formulario shell">
    <button type="button" class="modal-close" id="modal-alta-cerrar" aria-label="Cerrar">✕</button>
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
.modal-close{
  position:absolute; top:18px; right:18px; width:30px; height:30px; border-radius:10px; border:0;
  background:var(--glass-content-bg); box-shadow:var(--glass-in); color:var(--ink-2); font-size:13px;
  display:grid; place-items:center; cursor:pointer; transition:transform .18s ease-out;
}
.modal-close:hover{ transform:translateY(-1px); }
.modal-formulario-acciones{ display:flex; gap:10px; margin-top:6px; }
.modal-formulario-acciones .boton-primario{ width:auto; flex:1; }
```

```js
function abrirModal(){ modalAlta.classList.add('open'); primerCampo.focus(); }
function cerrarModal(){ modalAlta.classList.remove('open'); formulario.reset(); }
botonNuevo.addEventListener('click', abrirModal);
botonCerrarX.addEventListener('click', cerrarModal);
botonCancelar.addEventListener('click', cerrarModal);
// A propósito: SIN listener de click en el backdrop — este modal no se
// cierra tocando afuera, a diferencia de .detail/.sidebar.
```

Para dos campos "cortos" lado a lado dentro del formulario (Rol + Teléfono, CP + CUIT...), envolverlos en `.form-grid-2` — 1 columna en mobile, 2 columnas recién desde 480px, para que nunca deforme un input angosto en pantallas chicas:

```css
.form-grid-2{ display:grid; grid-template-columns:1fr; gap:0 12px; }
@media(min-width:480px){ .form-grid-2{ grid-template-columns:1fr 1fr; } }
```

## Campo de contraseña con mostrar/ocultar

Cualquier `<input type="password">` de la app usa esta estructura — nunca `type="text"` a secas (ni siquiera "porque es modo test", que fue el error real que corrigió este patrón). Se auto-conecta solo: `assets/js/formularios.js` engancha el ícono y el toggle a cualquier `.campo-password-toggle` que encuentre en la página, sin que la pantalla llame nada.

```html
<div class="campo">
  <label for="campo-password">Contraseña</label>
  <div class="campo-password-wrap">
    <input type="password" id="campo-password" required>
    <button type="button" class="campo-password-toggle" aria-label="Mostrar contraseña">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>
    </button>
  </div>
</div>
```

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

Degradé animado para una palabra puntual dentro de un título — hoy la segunda palabra de "SMART Building" en las 4 pantallas donde aparece. Adaptado de un componente de referencia que por default usa una paleta arcoíris (rosa/violeta) — **reconstruido con únicamente `--accent`/`--accent-2`**, el acento de marca ya licenciado en la skill para esto. Nunca se usa para más de una palabra a la vez ni compite con el semáforo — es decoración de marca, no estado.

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
<span class="cargando-rotativo"><span class="cargando-texto"></span></span>
```

```js
listaAlgo.innerHTML = `<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">${window.Cargando.html()}</p>`;
```

No fija tamaño ni color — los hereda del contenedor donde se lo inserte (un `<p>` chico para un listado, directo dentro de un `<h1>` para un título de detalle). Cada 6 ticks (~2,7s) cambia de frase con una transición de desvanecido; los ticks intermedios solo actualizan los puntos, sin transición — un parpadeo constante de "cargando" se sentiría mal si TODO se desvaneciera cada 450ms.

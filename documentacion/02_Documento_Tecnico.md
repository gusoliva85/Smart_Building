# Documento Técnico — SMART Building

> Estado del documento: **Completo.** Arquitectura, sistema de diseño, modelo de datos y especificación técnica de los 19 módulos funcionales descriptos en el Documento General. La ejecución paso a paso de todo esto vive en `03_Roadmap.md` — este documento es la referencia; el roadmap es la lista de tareas.

---

## 1. Dashboard Inteligente

Es la pantalla de entrada al sistema para los roles de administración (Administrador General, Administrador de Consorcio, Encargado). Tiene dos partes bien diferenciadas: un **Dashboard General** (métricas y números) y el **Dashboard Visual del Edificio** (la funcionalidad diferencial del proyecto, descripta en el Documento General, sección 4).

### 1.1 Dashboard General

Conjunto de widgets que dan una foto del estado del edificio (o de toda la cartera, si el rol es Administrador General) sin tener que entrar a ningún módulo en particular.

| Widget | Qué muestra | De dónde sale el dato |
|---|---|---|
| **Estado del edificio** | Resumen en un número: cantidad de departamentos en verde / amarillo / naranja / rojo. | Cálculo agregado del Dashboard Visual (sección 1.2). |
| **Estado financiero** | Total recaudado del mes vs. total esperado, morosidad (%), próximos vencimientos de expensas. | Módulo financiero (Documento General, sección 6). |
| **Reclamos** | Reclamos abiertos por prioridad (leve/medio/crítico), y cuántos se abrieron/cerraron en los últimos 30 días. | Módulo de reclamos (Documento General, sección 11). |
| **Deudas** | Ranking de unidades con mayor deuda acumulada y antigüedad. | Módulo financiero, sub-sección deudores (sección 6.3). |
| **Mantenimientos** | Órdenes de trabajo abiertas, en curso y programadas para los próximos 15 días. | Módulo de mantenimiento (Documento General, sección 10). |
| **Riesgos** | Activos de seguridad vencidos o próximos a vencer (matafuegos, ascensores, bocas de incendio). | Módulo de activos (Documento General, sección 9). |
| **KPIs** | Indicadores de gestión: tiempo promedio de resolución de reclamos, costo de mantenimiento acumulado del mes, tasa de morosidad. | Cálculo agregado sobre reclamos, mantenimiento y finanzas. |

**Nota de diseño:** cada widget respeta el permiso del rol que lo ve. Un Encargado, por ejemplo, ve Reclamos y Mantenimientos con el mismo detalle que un Administrador, pero no ve el detalle de Estado financiero (solo un semáforo general, sin montos) — el detalle de permisos fino se termina de definir en la sección 6 de este documento (Autenticación, roles y permisos).

### 1.2 Dashboard Visual del Edificio

Esta es, según el análisis competitivo del Documento General, la funcionalidad que ningún competidor relevado ofrece. Es una representación gráfica del edificio, piso por piso y departamento por departamento, coloreada según el estado real de cada unidad.

#### 1.2.1 Modelo de estados (semáforo de 4 colores)

El pedido original definía 3 colores (verde/amarillo/rojo) en la introducción del proyecto y 4 en el detalle técnico (verde/amarillo/naranja/rojo). Se adopta el modelo de **4 estados**, porque permite distinguir "hay algo para mirar" (amarillo) de "ya se está actuando, pero todavía no está resuelto" (naranja) — una distinción que aporta valor real y que el modelo de 3 colores no permitía expresar.

| Color | Significado | Ejemplos que lo disparan |
|---|---|---|
| 🟢 **Verde** | Todo correcto | Sin reclamos abiertos, sin deuda, activos vigentes. |
| 🟡 **Amarillo** | Atención | Reclamo leve o medio abierto · deuda de expensas de un mes · activo por vencer dentro de 30 días. |
| 🟠 **Naranja** | Pendiente | Orden de trabajo ya asignada y en curso (se está resolviendo, pero aún no cerrada) · mantenimiento programado próximo a su fecha límite. |
| 🔴 **Rojo** | Crítico | Reclamo crítico · deuda de expensas de más de un mes · activo de seguridad vencido o inhabilitado. |

**Regla de precedencia:** un departamento puede tener simultáneamente más de un factor (por ejemplo, un reclamo leve y una deuda de dos meses). En ese caso, el color mostrado es siempre el del **estado más grave** entre todos los factores aplicables (deuda, reclamos, mantenimiento asociado a su unidad), con el orden de gravedad verde < amarillo < naranja < rojo. El detalle de qué factores están activos se ve al expandir el panel lateral (sección 1.2.3).

#### 1.2.2 Estructura de la vista

- **Nivel edificio:** vista general con todos los pisos apilados en franjas horizontales — el edificio se dibuja como una fachada con ventanas, una franja por piso.
- **Nivel piso:** al tocar un piso, se despliegan sus departamentos individuales, cada uno como una tarjeta coloreada según su estado.
- **Nivel departamento:** al tocar un departamento se abre su detalle completo (sección 1.2.3).
- **Selector de "vista" (capa de datos):** el usuario elige qué información determina los colores en un momento dado — no siempre se quiere ver lo mismo:
  - **General** (combinada, aplica la regla de precedencia de todos los factores).
  - **Incidentes / reclamos** (colorea solo según reclamos abiertos).
  - **Deudores** (colorea solo según estado de expensas).
  - **Mantenimiento** (colorea solo según órdenes de trabajo activas).
- **Apartado de mobiliario y activos:** una franja separada (no asociada a un departamento puntual) que muestra los activos de seguridad y equipamiento común del edificio (matafuegos, ascensores, bocas de incendio, bombas), con el mismo esquema de colores. Corresponde a lo pedido explícitamente en la introducción del proyecto ("un apartado para ver los mobiliarios que tienen que estar habilitados").

#### 1.2.3 Panel lateral de detalle

Tal como se describe en la introducción del proyecto, la vista tiene "un pequeño detalle en su lateral" que se expande al hacer clic. Se define así:

- **Estado colapsado (mobile / tablet):** no hay franja lateral fija — el panel vive oculto como una hoja inferior (*bottom sheet*) que sube desde abajo al tocar un departamento.
- **Estado colapsado (desktop ≥1024px):** panel fijo anclado al costado derecho del Dashboard Visual, con posición `fixed`.
- **Estado expandido (al tocar un departamento):** panel completo con:
  - Datos de la unidad (propietario, inquilino, m²).
  - Reclamos abiertos, con prioridad y tiempo transcurrido.
  - Estado de expensas (si el rol que consulta tiene permiso para verlo).
  - Órdenes de mantenimiento activas o recientes.
  - Activos ubicados en esa unidad, si aplica.

Este panel es el punto donde confluye toda la información de los módulos de negocio (Documento General, secciones 5 a 11) en una sola vista — es, en la práctica, la "ficha 360°" del departamento.

### 1.3 Arquitectura de implementación del frontend (plantilla base validada)

La plantilla visual validada con el cliente, tras un proceso de exploración de 5 direcciones distintas y su posterior refinamiento con investigación de referencias externas (Apple *Liquid Glass*, patrones de *bento grid*, mejores prácticas de *glassmorphism* en dashboards premium 2026), es **`documentacion/mockups/Mockup_3D_Vidrio_Grafito.html`**. Ese archivo es el contrato pixel a pixel de esta sección; lo que sigue es su documentación reutilizable para que cualquier pantalla nueva se construya con el mismo lenguaje visual, sin reinventarlo pantalla por pantalla.

#### 1.3.1 Aclaración sobre el stack de la plantilla

El mockup está resuelto en **HTML + CSS + JavaScript vanilla**, sin frameworks ni build tools, para poder iterarlo rápido durante la etapa de diseño. La implementación real (a partir del Roadmap) migra ese mismo CSS a **Tailwind CSS**, de la siguiente forma:

- Los **tokens de color, sombra y vidrio** (variables CSS `:root` / `html[data-theme="dark"]`) se mantienen tal cual, fuera de Tailwind, en una hoja `frontend/assets/css/tokens.css` — Tailwind no maneja bien el intercambio dinámico claro/oscuro de valores arbitrarios, así que las variables CSS siguen siendo la fuente de verdad del color.
- Tailwind se configura (`tailwind.config.js`) para que sus utilidades de color (`bg-accent`, `text-ink-3`, `border-crit`, etc.) **lean esas mismas variables CSS** (`colors: { accent: 'var(--accent)', crit: 'var(--crit)', ... }`), de forma que se pueda maquetar con clases utilitarias (`class="p-4 rounded-2xl"`) sin perder el sistema de theming.
- Los patrones que no son solo utilidades sueltas (la tarjeta de vidrio en dos capas, el semáforo, el toggle de tema) se documentan como **componentes** (sección 1.3.3) y se implementan como clases reutilizables vía `@layer components` de Tailwind, para no repetir 15 utilidades idénticas en cada pantalla.
- **Fase de CDN → build real:** las primeras tareas del Roadmap usan el CDN de Tailwind (`cdn.tailwindcss.com`) para poder maquetar sin instalar nada. Antes de dar por cerrada la etapa de frontend (ver Roadmap, fase de pulido) se migra al **Tailwind CLI standalone** (binario ejecutable, sin depender de Node/npm — coherente con que el resto del stack es Python) para generar un `output.css` compilado y optimizado.

#### 1.3.2 Sistema de temas: claro por defecto, oscuro opcional

La plataforma arranca **siempre en tema claro**, pensado para que cualquier residente —no solo un perfil técnico— lo sienta cómodo y hogareño. Un botón en la barra superior (patrón `AnimatedThemeToggler`) permite alternar a un tema oscuro como preferencia personal; esa preferencia nunca es el estado inicial.

El cambio de tema no es un corte instantáneo ni un fundido plano: usa la **View Transitions API** del navegador para animar un barrido circular que nace en el punto exacto donde el usuario tocó el botón y cubre toda la pantalla. Técnicamente, esto implica:
- Todos los colores que cambian entre temas están declarados como variables CSS en `:root` (claro) y redefinidos en un bloque `html[data-theme="dark"]` (oscuro) — nunca como valores fijos sueltos en una regla, porque entonces esa regla puntual queda "pegada" al tema anterior.
- Además de los colores de marca, hay un segundo grupo de variables que muchas veces se pasa por alto: los tokens de **sombra y vidrio** (`--sh-sm/md/lg`, `--glass-shell-bg`, `--glass-content-bg`, `--glass-in`). Si estos quedan con valores fijos pensados solo para el tema claro, el tema oscuro se ve con sombras invisibles o vidrios que no cambian de opacidad.
- El navegador, si no soporta la View Transitions API, hace el cambio de forma instantánea — sigue siendo funcional, solo pierde la animación.
- **Nota de implementación:** el mockup base dispara `document.startViewTransition()` con el barrido *default* del navegador (un cross-fade). El barrido circular que nace del punto exacto del clic (`clip-path` animado con `circle()` calculado desde las coordenadas del botón) es un refinamiento pendiente, documentado como tarea específica del Roadmap — no viene resuelto en el mockup.

#### 1.3.3 Sistema de vidrio en dos capas (glassmorphism selectivo)

La lección de diseño más importante detrás de esta plantilla, tomada de las guías de Apple *Liquid Glass* (2025-26): **el vidrio no va debajo de contenido denso.** Un fondo con blur fuerte se ve espectacular detrás de un titular o un ícono, pero vuelve ilegible una grilla de texto chico. Por eso el sistema define **dos niveles de vidrio**, no uno:

| Nivel | Uso | Blur | Opacidad de fondo (claro) | Ejemplos |
|---|---|---|---|---|
| **`.shell`** | Contenedores grandes, "de navegación" — poca densidad de texto | 22px | ~52% | Topbar, tarjetas KPI, contenedor del Dashboard Visual, panel de detalle |
| **`.content-glass`** | Contenido denso dentro de un shell — mucho texto chico junto | 7px | ~68% | Tarjetas de departamento, chips de activos, ítems del panel de detalle |

Reglas no negociables de este sistema:
- **`@supports` de respaldo:** si el navegador no soporta `backdrop-filter` (ni con prefijo `-webkit-`), ambos niveles caen a un fondo casi sólido (`--glass-shell-fallback` / `--glass-content-fallback`) en vez de mostrar un vidrio roto o ilegible.
- **Brillo especular:** cada `.shell` lleva un pseudo-elemento `::before` con un barrido diagonal de luz (`--glass-sheen`) para que la superficie lea como vidrio real y no como un simple `blur()` plano.
- **Textura de grano:** una capa fija (`body::before`) con una textura SVG de ruido (`feTurbulence`) al 3.5% de opacidad y `mix-blend-mode: overlay` evita que el fondo se vea como un degradé liso — es lo que le da la sensación táctil de vidrio premium, no cosmética.
- **Reflejo del edificio:** el contenedor `.building` del Dashboard Visual lleva su propio reflejo lateral (`::after` con gradiente horizontal) simulando luz rebotando en una torre de vidrio real — una coherencia temática deliberada entre "edificio de vidrio" y "UI de vidrio".
- **Estado semáforo: nunca con borde de acento de un solo lado.** Está prohibido en este proyecto el patrón `border-left: 3px solid var(--color)` (o `border-top`) para indicar el estado de una tarjeta — es un tic visual demasiado asociado a dashboards genéricos. El estado de una tarjeta (`.unit-card`, `.asset-chip`) se comunica con:
  1. Un **borde completo** (los 4 lados, 1px) teñido con el color de estado: `border-color: color-mix(in srgb, var(--c) 46%, var(--line-2))`.
  2. Una **sombra proyectada** del mismo color, en capas junto con la sombra de vidrio: `box-shadow: var(--glass-in), 0 10px 22px -12px color-mix(in srgb, var(--c) 60%, transparent)`.

  Este patrón (borde parejo + sombra de color, nunca una barra de acento) es el estándar para **cualquier** componente futuro que necesite comunicar el semáforo de 4 estados.

#### 1.3.4 Paleta de color — variables exactas

```css
/* Neutros y superficies — tema claro (default) */
--bg-1: #f1f2f3;  --bg-2: #e9ebec;           /* fondo de página, degradé sutil */
--wash-a: #d6dee3; --wash-b: #e6e2d8;        /* manchas de color detrás del vidrio */
--ink: #1c2024;    --ink-2: #4b5157;
--ink-3: #7c828a;  --ink-4: #a8adb3;
--line: rgba(28,32,36,.10); --line-2: rgba(28,32,36,.07); --line-strong: rgba(28,32,36,.16);

/* Vidrio */
--glass-shell-bg: rgba(255,255,255,.52);   --glass-shell-blur: 22px;
--glass-content-bg: rgba(255,255,255,.68); --glass-content-blur: 7px;
--glass-in: inset 0 1px 0 rgba(255,255,255,.85), inset 0 0 0 1px rgba(255,255,255,.45);
--glass-sheen: linear-gradient(120deg, rgba(255,255,255,.55), transparent 45%);

/* Acento de marca — acero/grafito, deliberadamente FUERA de la familia del semáforo */
--accent: #57768c; --accent-2: #3e5a6d; --accent-soft: #e2e9ed; --accent-ring: rgba(87,118,140,.28);

/* Semáforo funcional — idéntico en ambos temas, nunca decorativo */
--ok: #2e8067;   /* verde */
--warn: #ba8c1f; /* amarillo */
--pend: #bd6c2c; /* naranja */
--crit: #b13c47; /* rojo */

/* Sombras (capas) */
--sh-sm: 0 1px 2px rgba(var(--shadow-rgb),.06), 0 4px 12px -4px rgba(var(--shadow-rgb),.12);
--sh-md: 0 2px 6px rgba(var(--shadow-rgb),.07), 0 16px 34px -16px rgba(var(--shadow-rgb),.22);
--sh-lg: 0 4px 16px rgba(var(--shadow-rgb),.09), 0 34px 70px -26px rgba(var(--shadow-rgb),.32);
```

```css
/* Tema oscuro — html[data-theme="dark"] */
--bg-1: #0c0d0e; --bg-2: #0f1011;
--ink: #eef0f1;  --ink-2: #bcc0c4; --ink-3: #868b91; --ink-4: #54585d;
--glass-shell-bg: rgba(22,25,28,.5); --glass-content-bg: rgba(22,25,28,.72);
--accent: #7ea3ba; --accent-2: #9bc0d4;
/* --ok/--warn/--pend/--crit NO cambian entre temas: el significado del estado no depende del tema elegido */
```

**Regla de oro del color:** el acento de marca (acero/grafito) nunca comparte familia de tono con ninguno de los 4 colores del semáforo (verde/amarillo/naranja/rojo). Esto es intencional: si el acento decorativo se pareciera a "verde" o "rojo", un usuario podría confundir una interacción de marca (un botón activo, un link) con un estado real del edificio. Cualquier paleta futura (si se rediseña la marca) debe preservar esta separación.

#### 1.3.5 Tipografía

- **Display / titulares / números de KPI:** `Outfit` (pesos 500–800), `letter-spacing: -0.015em`.
- **Cuerpo / labels / inputs:** `Inter` (pesos 400–700).
- Ambas se cargan vía Google Fonts (`<link>` en el `<head>`) con fallback a `ui-sans-serif, system-ui, sans-serif` por si no hay conexión.
- Nunca serif en pantallas de gestión — esta plataforma es una herramienta de trabajo densa en datos reales, no una pieza editorial.

#### 1.3.6 Radios y espaciado

- Tarjetas: `--r-card: 20px`. Paneles grandes / topbar: `--r-lg: 24px`. Elementos chicos (chips, inputs): `--r-sm: 12px`. Pills/badges de estado: `border-radius: 99px`.
- Espaciado en múltiplos de 4px, gaps de grilla entre 8px (mobile) y 10-12px (desktop).

#### 1.3.7 Responsive: mobile-first real, un quiebre intermedio y uno de escritorio

La hoja de estilos se escribe **mobile-first** (los estilos base son los de la pantalla angosta; los `@media (min-width: …)` agregan comportamiento, nunca lo corrigen). Dos quiebres:

| Quiebre | Qué cambia |
|---|---|
| **Base (< 640px, mobile)** | Grilla de KPIs a 2 columnas (los 2 widgets "hero" ocupan las 2 columnas completas). Fachada del edificio angosta, ventanas de piso en grilla de 4 columnas apretada. Grilla de departamentos expandida a 2 columnas. Panel de detalle = **hoja inferior** (`position: fixed; bottom: 0`, con `transform: translateY(105%)` oculto y `translateY(0)` visible), con *backdrop* transparente (solo captura el toque afuera para cerrar, sin oscurecer la pantalla). |
| **≥ 640px (tablet)** | Grilla de KPIs a 4 columnas. Ventanas y tarjetas de departamento con más aire (paddings y gaps mayores). Grilla de departamentos a 4 columnas. |
| **≥ 1024px (desktop / web)** | Grilla de KPIs a 6 columnas (los 2 "hero" ocupan 3 columnas cada uno). El panel de detalle deja de ser hoja inferior y se convierte en **panel lateral fijo** (`position: fixed; right: 24px; top/bottom: 24px; width: 380px`), con `transform: translateX(420px)` oculto y `translateX(0)` visible. |

Este es el único mecanismo de adaptación mobile → web que pide el Documento General (sección 1.4: "toda la aplicación se hace mobile first y web"): **no hay dos maquetados distintos**, es el mismo HTML/CSS con dos quiebres que reorganizan densidad y reposicionan el panel de detalle.

#### 1.3.8 Arquitectura del componente "Edificio" (Dashboard Visual)

Jerarquía de contenedores, de afuera hacia adentro — **no se improvisa**, romperla rompe el layout responsive:

```
.visual-card (shell)
 ├─ .visual-head           → título + selector de vista (general/incidentes/deudores/mantenimiento)
 ├─ .legend                → leyenda de los 4 colores
 ├─ .scene
 │   └─ .building (content-glass, con reflejo lateral ::after)
 │       ├─ .roof           → nombre del edificio + indicador "sistema en vivo"
 │       ├─ #floors         → un .floor por piso (generado por JS)
 │       │   └─ .floor (position:relative, contiene el wash de color si aplica variante)
 │       │       ├─ .floor-row     → colapsado: número de piso + grilla de "ventanas" (una por depto)
 │       │       └─ .floor-body    → expandido: grilla de .unit-card (una tarjeta completa por depto)
 │       └─ .lobby          → decorativo, planta baja
 └─ .assets                 → franja "Activos y equipamiento común", fuera de la fachada
     └─ .assets-row         → .asset-chip por cada activo (ascensores, matafuegos, BIE, bombas)

.backdrop                    → capa fija, transparente, cierra el panel al tocar afuera
.detail (shell)               → panel de detalle (hoja inferior en mobile / lateral en desktop)
```

**Motor de datos (JS), independiente de la piel visual:**
- Cada departamento tiene tres posibles "factores" de estado: `reclamos[]`, `deuda{months, amount}`, `ot{title, state}` (orden de trabajo).
- Tres funciones puras calculan la severidad de cada factor: `reclamoSeverity()`, `deudaSeverity()`, `otSeverity()` (esta última solo puede devolver `ok` o `pend`, nunca `warn`/`crit` — el "naranja" es exclusivo del mantenimiento en curso).
- `severityForView(unidad, vista)` decide qué severidad mostrar según la vista activa: si la vista es "general", aplica `maxSeverity()` (la regla de precedencia de la sección 1.2.1) sobre los tres factores; si es una vista específica, devuelve solo la severidad de ese factor.
- Al cambiar de vista, se vuelve a ejecutar `renderFloors()` completo — no hay estado oculto entre vistas, así que nunca puede quedar un color "pegado" de la vista anterior.

#### 1.3.9 Variante "piso completo"

Existe una variante documentada del componente (`Mockup_3D_Vidrio_Grafito_PisoCompleto.html`) donde, además del color por ventana/departamento, **todo el piso** se tiñe con el color de su estado más grave — inspirado en el mockup de referencia entregado al inicio (`Edificio_Solid.html`). Se logra con un wash translúcido detrás de todo el contenido del piso (`.floor::before`, `z-index: -1`, `color-mix(in srgb, var(--c) N%, transparent)`), con intensidad progresiva según gravedad (10% verde, 20% amarillo, 22% naranja, 26% rojo) para no caer en bloques de color planos ni saturados. Queda como **variante activable**, no como comportamiento por defecto — se decide en el Roadmap si se adopta como configuración de usuario ("preferencia visual") o se descarta.

---

## 2. Arquitectura general del sistema

### 2.1 Principios

- **Backend y frontend separados desde el día uno** (Documento General, sección 1.3): son dos carpetas, dos procesos, dos responsabilidades. El frontend nunca renderiza HTML del lado del servidor ni depende de un motor de templates de Python — es HTML/CSS/JS estático que consume una API JSON.
- **Simplicidad antes que arquitectura de manual:** no se introduce una capa (microservicios, colas, cache distribuida) hasta que haya una razón real de negocio para hacerlo. Un solo proceso de backend, una sola base SQLite, mientras el proyecto sea de un tamaño manejable.
- **Escalable sin sobre-ingeniería:** la organización interna del backend (routers/modelos/schemas por dominio) y del frontend (una pantalla = un HTML + su JS) permite agregar módulos nuevos sin tocar los existentes, y migrar de SQLite a Postgres el día que haga falta sin rehacer la capa de negocio (gracias a usar un ORM).
- **Todo lo construido se prueba de punta a punta** antes de pasar a la siguiente tarea — ver Roadmap.

### 2.2 Stack tecnológico

| Capa | Tecnología | Por qué |
|---|---|---|
| Backend — framework | **FastAPI** | Documentación interactiva automática (`/docs`) — clave para probar cada endpoint antes de que exista la pantalla que lo consuma, que es exactamente el flujo incremental que pide este proyecto. Validación de datos automática con Pydantic. Rendimiento y curva de aprendizaje razonables. |
| Backend — ORM | **SQLAlchemy** | Estándar de facto en Python, permite migrar de SQLite a otro motor el día de mañana sin reescribir queries. |
| Backend — validación | **Pydantic** | Ya viene integrado con FastAPI; separa el "modelo de base de datos" del "modelo de entrada/salida de la API" (buena práctica, evita filtrar campos internos). |
| Backend — servidor | **Uvicorn** | Servidor ASGI liviano, el estándar para correr FastAPI. |
| Base de datos | **SQLite** | Pedido explícito del proyecto. Un solo archivo `.db`, cero infraestructura para levantar en desarrollo. |
| Autenticación | **Passlib** (hash de contraseñas) + **JWT** (python-jose) | Sesión simple basada en token, sin estado en servidor. |
| Frontend — maquetado | **HTML + CSS + Tailwind CSS** | Pedido explícito. Tailwind vía CDN en las primeras tareas, migrando a Tailwind CLI standalone (sin Node) antes de cerrar la etapa de frontend. |
| Frontend — interactividad | **JavaScript vanilla (ES2020+)** | Sin framework de frontend (React/Vue/etc.) — no hace falta para el tamaño de este proyecto y mantiene la promesa de "arquitectura simple". Se reevalúa solo si el proyecto crece mucho más allá del alcance actual. |
| Frontend — mapas y geocodificación | **Leaflet.js + tiles de OpenStreetMap + geocodificación Nominatim** | Pedido explícito ("mapa gratuito"). Sin API key ni facturación, a diferencia de Google Maps/Mapbox — coherente con el resto del stack, que no depende de credenciales externas. Se usa primero en la Fase 1 (validación visual de dirección al dar de alta un edificio) y queda disponible para cualquier pantalla futura que necesite mostrar una ubicación. |
| Servidor de archivos estáticos (desarrollo) | **`python -m http.server`** | Cero dependencias nuevas — ya usamos Python en el backend. |

### 2.3 Estructura de carpetas

```
Smart_Building_ver3/
├── backend/
│   ├── app/
│   │   ├── main.py                 # Entry point FastAPI, CORS, incluye routers
│   │   ├── database.py             # Engine SQLAlchemy + sesión + Base declarativa
│   │   ├── core/
│   │   │   ├── config.py           # Configuración (rutas, secretos, orígenes CORS)
│   │   │   └── security.py         # Hash de contraseñas, JWT, dependencias de auth
│   │   ├── models/                 # Un archivo por dominio (SQLAlchemy)
│   │   │   ├── usuario.py
│   │   │   ├── edificio.py
│   │   │   ├── reclamo.py
│   │   │   ├── mantenimiento.py
│   │   │   ├── activo.py
│   │   │   ├── financiero.py
│   │   │   ├── documento.py
│   │   │   ├── proveedor.py
│   │   │   ├── comunicado.py
│   │   │   ├── reserva.py
│   │   │   └── seguridad.py
│   │   ├── schemas/                # Un archivo por dominio (Pydantic), mismo criterio que models/
│   │   ├── routers/                # Un archivo por dominio, define los endpoints HTTP
│   │   ├── services/               # Lógica de negocio reutilizable (ej: cálculo de severidad/semáforo)
│   │   └── seed.py                 # Script que crea usuarios y edificio de prueba
│   ├── requirements.txt
│   └── smart_building.db           # Generado en runtime, no se versiona a mano
│
├── frontend/
│   ├── index.html                  # Login
│   ├── dashboard.html               # Dashboard General (KPIs) + Dashboard Visual del edificio — sección 1
│   ├── usuarios.html                # Gestión de usuarios y roles — sección 6
│   ├── edificios.html               # Alta, configuración y estructura (pisos/deptos/cocheras/espacios) — sección 7
│   ├── financiero.html              # Gastos/Expensas/Pagos/Deudores/Fondos/Caja/Presupuestos/Facturas (sub-vistas por pestaña) — sección 8
│   ├── documentacion.html
│   ├── proveedores.html
│   ├── activos.html
│   ├── mantenimiento.html
│   ├── reclamos.html
│   ├── comunicados.html
│   ├── reservas.html
│   ├── seguridad.html
│   ├── analitica.html               # Gráficos de Analítica — sección 17
│   ├── configuracion.html           # Roles/excepciones, parámetros generales, auditoría — sección 6.1 (solo Administrador General)
│   ├── assets/
│   │   ├── css/
│   │   │   ├── tokens.css          # Variables CSS (paleta, vidrio, sombras) — sección 1.3.4
│   │   │   ├── components.css      # Clases reutilizables (.shell, .content-glass, .unit-card, etc.)
│   │   │   └── output.css          # Generado por Tailwind CLI (no se edita a mano)
│   │   ├── js/
│   │   │   ├── api.js              # Wrapper fetch() con manejo de token/errores
│   │   │   ├── auth.js             # Login/logout, guardado de sesión
│   │   │   ├── theme.js            # Toggle de tema + View Transitions API
│   │   │   ├── layout.js           # Sidebar de navegación (autenticado) — sección 4.1
│   │   │   ├── mapa.js             # Geocodificación (Nominatim) + mapa (Leaflet) — sección 7
│   │   │   ├── edificio.js         # Motor del Dashboard Visual (sección 1.3.8)
│   │   │   └── ... un archivo por pantalla
│   │   └── img/
│   └── tailwind.config.js
│
├── documentacion/
│   ├── 01_Documento_General.md
│   ├── 02_Documento_Tecnico.md
│   ├── 03_Roadmap.md
│   └── mockups/
│
├── .gitignore
├── README.md                   # cómo levantar backend y frontend a mano
└── que_hice.html
```

**Nota de arranque:** el proyecto se versiona en GitHub y se levanta a mano (backend y frontend en dos terminales separadas) — no hay un script de un solo clic. El detalle paso a paso vive en `README.md`, en la raíz del proyecto.

---

## 3. Arquitectura del Backend

### 3.1 Convenciones de la API

- Prefijo común `/api/`, versionado implícito por ahora (se agrega `/api/v1/` recién si en el futuro conviven dos versiones).
- Un router por dominio, montado en `main.py`: `/api/auth`, `/api/usuarios`, `/api/edificios`, `/api/reclamos`, `/api/mantenimiento`, `/api/activos`, `/api/financiero`, `/api/documentos`, `/api/proveedores`, `/api/comunicados`, `/api/reservas`, `/api/seguridad`, `/api/dashboard`, `/api/analitica`, `/api/configuracion`.
- Respuestas siempre en JSON, códigos HTTP semánticos (200/201/204/400/401/403/404/422).
- Todo endpoint que devuelve datos de un edificio recibe `edificio_id` (path o query param) y valida que el usuario autenticado tenga acceso a ese edificio.
- Documentación automática siempre activa en `/docs` (Swagger) y `/redoc` — se usa activamente durante el desarrollo para probar cada endpoint antes de conectarlo al frontend.

### 3.2 Autenticación y sesión

- Login: `POST /api/auth/login` con `email` + `password` → devuelve un JWT de corta duración.
- El frontend guarda el token en `localStorage` y lo manda en el header `Authorization: Bearer <token>` en cada request.
- Cada endpoint protegido usa una dependencia de FastAPI (`get_current_user`) que decodifica el token, busca el usuario y expone su rol — de ahí se deriva el control de permisos.
- **Nota de simplicidad para esta etapa:** contraseñas de prueba en texto simple documentadas en `que_hice.html` (sección "Credenciales de prueba"), pero **siempre hasheadas en la base** (`passlib`, algoritmo `bcrypt`) — nunca se guarda una contraseña en texto plano, ni siquiera en modo test.

---

## 4. Arquitectura del Frontend

### 4.1 Modelo de navegación

Aplicación **multi-página estática** (no SPA): cada **dominio/módulo de negocio** (sección 2.3) es un archivo `.html` independiente en `frontend/`, que comparte los mismos `tokens.css`/`components.css`. La navegación entre dominios es HTML estándar (`<a href="reclamos.html">`), sin router de JavaScript — más simple de mantener y de razonar para el tamaño de este proyecto.

**Dos zonas de la aplicación, con chrome distinto:**

- **Zona pre-autenticación** (hoy, solo `index.html`, el login): tarjeta centrada sobre el fondo atmosférico, sin sidebar ni menú — no hay nada que navegar todavía porque no hay sesión.
- **Zona autenticada** (`dashboard.html` en adelante — cualquier pantalla detrás de login): **sidebar de navegación fija a la izquierda** con todos los accesos a acciones de la aplicación (Edificios, Usuarios, y cada dominio que se vaya sumando), más un topbar arriba del contenido principal (título de la pantalla + toggle de tema). El login, al autenticar, redirige siempre a `dashboard.html` — el "home" de la zona autenticada, que la Fase 6 termina de llenar con KPIs reales; hasta entonces es un cascarón mínimo de bienvenida que ya trae el sidebar funcionando.

**Sidebar — estructura y responsive:**
- Contenido: marca arriba, lista de accesos habilitados **según el rol logueado** en el medio (un mismo patrón de datos — qué rol ve qué acceso — que ya se usaba de forma provisoria en la vista de sesión del login, ahora promovido a componente compartido), y abajo una tarjeta con nombre/rol del usuario + botón de cerrar sesión.
- Se monta con un script común (`assets/js/layout.js`) que cada pantalla autenticada importa — hace la guarda de acceso (sin token → redirige a `index.html`), pide `/auth/me`, arma los accesos según el rol, y expone el mismo botón de logout en todas las pantallas. Ninguna pantalla nueva vuelve a escribir esta lógica a mano.
- **Desktop (≥1024px):** sidebar fija de 248px, siempre visible.
- **Mobile (< 1024px):** sidebar oculta por default; un botón hamburguesa en el topbar la despliega como panel superpuesto (mismo patrón `translateX` + backdrop transparente-al-tacto ya usado en el panel de detalle del Dashboard Visual, sección 1.2.3) — un único componente de "panel deslizante" reutilizado, no dos implementaciones distintas.
- Documentado con su HTML/CSS/JS de referencia en la skill `premium-uiux` (`references/componentes.md`).

**Convención para sub-vistas dentro de un mismo dominio** (listado, alta, edición, detalle/ficha): no generan un archivo `.html` nuevo cada una. Se resuelven dentro de la misma página con JavaScript, reutilizando el patrón `.detail` ya validado en el Dashboard Visual (sección 1.2.3) — hoja inferior en mobile, panel lateral fijo en desktop — para altas/ediciones/fichas puntuales, y el patrón `.view-switch` (sección 1.3.3) para alternar entre varias sub-vistas de igual jerarquía dentro de un dominio (por ejemplo, dentro de `financiero.html`: Gastos/Expensas/Pagos/Deudores/Fondos/Caja/Presupuestos/Facturas como pestañas de un mismo `.view-switch`, no como 8 archivos separados). Un archivo `.html` nuevo se justifica únicamente cuando la pantalla es la puerta de entrada a un dominio de negocio distinto, no cuando es un paso más de un mismo flujo.

### 4.2 Comunicación con el backend

- `assets/js/api.js` centraliza todas las llamadas `fetch()`: agrega el header de autenticación, castea la respuesta a JSON, y estandariza el manejo de errores (401 → redirige a `index.html`).
- Cada pantalla tiene su propio archivo JS que llama a `api.js`, arma el HTML dinámico (igual que ya hace el mockup con `buildingData`) y engancha los eventos de interacción.
- CORS: en desarrollo, backend (`localhost:8000`) y frontend (`localhost:5500`) corren en puertos distintos → `CORSMiddleware` en FastAPI habilita explícitamente el origen del frontend.

### 4.3 Componentes reutilizables (resumen — detalle completo en sección 1.3)

Topbar, tarjeta KPI (`.kpi`, `.kpi--hero`, `.kpi-metric`), selector segmentado (`.view-switch`), tarjeta de estado (`.unit-card`, `.asset-chip`), panel de detalle (`.detail`), pill de prioridad/estado (`.pill`), botón de ícono (`.icon-btn`), toggle de tema. Documentados con su HTML/CSS de referencia en `frontend/assets/css/components.css` a medida que se implementan (Roadmap, fase 1).

---

## 5. Modelo de datos

Resumen de las tablas principales por dominio. El detalle exacto de columnas, tipos e índices vive en el código (`backend/app/models/`) — acá se documenta el propósito y las relaciones clave para que cualquier tarea nueva sepa dónde entra.

### 5.1 Usuarios y estructura

- **`usuarios`**: id, nombre, email, password_hash, rol, activo, creado_en. Rol ∈ {admin_general, admin_consorcio, encargado, propietario, inquilino, proveedor, auditor, seguridad}.
- **`edificios`**: id, nombre, dirección, CP, CUIT, admin_consorcio_id, días de vencimiento de expensas, política de recargos, contacto de emergencia, roles habilitados, latitud/longitud (nullable — geocodificados al dar de alta, sección 7).
- **`usuario_edificio`**: tabla puente — un usuario puede estar vinculado a más de un edificio (Administrador General con cartera, propietario con unidades en dos edificios distintos), con un rol efectivo por vínculo.
- **`pisos`**: id, edificio_id, número/nombre.
- **`departamentos`**: id, piso_id, identificador (ej. "6A"), m², propietario_id, inquilino_id (nullable), estado ocupacional.
- **`cocheras`**: id, edificio_id, número, departamento_id (nullable, fija o rotativa).
- **`espacios_comunes`**: id, edificio_id, nombre, capacidad, reglas de uso.

### 5.2 Financiero

`expensas`, `expensa_detalle` (rubro + monto), `pagos` (con comprobante y conciliación), `gastos` (rubro, proveedor_id opcional, activo_id opcional), `fondos`, `movimientos_fondo`, `caja`, `presupuestos`, `facturas`. Los "deudores" son una **vista calculada** sobre `expensas` + `pagos`, no una tabla propia.

### 5.3 Documental

`documentos`: id, edificio_id, categoría (reglamento/contrato/acta/seguro/garantía/manual/certificado/legal), nombre, archivo, fecha de vencimiento (nullable — dispara el estado de activos cuando aplica), subido_por, visibilidad (qué roles lo ven).

### 5.4 Proveedores

`proveedores` (exclusivo_edificio: bool), `rubros`, `proveedor_rubro` (puente N:N), `evaluaciones_proveedor` (vinculada a una orden de trabajo cerrada).

### 5.5 Activos y mantenimiento

- **`activos`**: id, edificio_id, código único, tipo, ubicación (piso_id o espacio_id), estado (calculado, no se guarda a mano), QR, proveedor_id responsable, próximo mantenimiento, garantía_hasta, manual_documento_id, costos_acumulados (calculado).
- **`activo_fotos`**: registro fotográfico.
- **`ordenes_trabajo`**: id, edificio_id, activo_id (nullable), espacio_id (nullable), reclamo_id (nullable — trazabilidad reclamo → OT), tipo (preventivo/correctivo/programado/emergencia), proveedor_id, prioridad, estado, fechas de creación/inicio/cierre, costo.
- **`ot_evidencias`**: fotos antes/después.

### 5.6 Reclamos

`reclamos` (edificio_id, departamento_id o espacio_id, creado_por, título, descripción, prioridad, estado, fechas), `reclamo_adjuntos`, `reclamo_comentarios`.

### 5.7 Comunicación, reservas y seguridad

`comunicados` (segmento: todos/piso/unidad, con tabla de lectura por usuario), `reservas` (espacio_id, usuario_id, fecha, horario, estado — con validación de solapamiento), `incidentes_seguridad`, `bitacora` (registro diario de encargado/seguridad).

---

## 6. Autenticación, roles y permisos

### 6.1 Modelo elegido para esta etapa: RBAC simple

Se implementa **control de acceso basado en rol** (un rol = un conjunto fijo de permisos), no un motor de permisos granulares por usuario. Es la opción correcta para el tamaño actual del proyecto: simple de razonar, simple de auditar, simple de extender.

El Documento General (sección 3, nota de diseño) deja abierta la puerta a "excepciones caso por caso" (ej. un inquilino al que el propietario le habilita ver expensas) — **queda documentado como extensión futura**, no como parte del alcance inicial: se resolvería agregando una tabla de permisos-por-excepción que se consulta *antes* de la regla de rol, sin tener que rediseñar el sistema de roles.

### 6.2 Matriz de roles (resumen operativo)

| Rol | Alcance | Ve financiero de la unidad | Ve financiero del edificio | Gestiona | Solo lectura |
|---|---|---|---|---|---|
| Administrador General | Toda la cartera | — | ✅ (todos sus edificios) | Alta de edificios, usuarios, configuración global | — |
| Administrador de Consorcio | Un edificio | — | ✅ | Expensas, gastos, reclamos, proveedores, documentación, comunicados de su edificio | — |
| Encargado | Un edificio | — | ❌ (solo semáforo, sin montos) | Incidentes, mantenimiento, bitácora | — |
| Propietario | Su(s) unidad(es) | ✅ | ❌ | Reclamos, reservas | — |
| Inquilino | Su unidad | ❌ (por defecto) | ❌ | Reclamos, reservas | — |
| Proveedor / Técnico | Sus OTs asignadas | — | — | Evidencia y estado de sus OTs | Ficha de sus OTs |
| Auditor | Un edificio o cartera (definido) | ✅ | ✅ | — | Financiero, documental, trazabilidad completa |
| Personal de seguridad | Un edificio | — | — | Incidentes, bitácora, botón de emergencia | — |

---

## 7. Gestión de edificios

- **Alta de edificio** (Administrador General): `POST /api/edificios` — crea el edificio y su estructura vacía (pisos/departamentos se generan a partir de la cantidad indicada en el alta). El formulario pide CP en vez de ciudad (más preciso para geocodificar y suficiente para lo que hoy usa la plataforma).
- **Geocodificación en el alta (frontend):** al completar Dirección y CP, se geocodifica con Nominatim (OpenStreetMap) y se muestra un mapa (Leaflet) con el resultado dentro del propio formulario — sin bloquear el resto de la carga mientras alguno de los dos campos esté vacío. Si la dirección no se encuentra, se avisa con un modal en vez de fallar en silencio o rechazar el alta (una dirección nueva puede no estar todavía indexada en OpenStreetMap). Las coordenadas encontradas viajan con el alta y quedan guardadas en `latitud`/`longitud` — insumo para una futura ubicación real del edificio en el Dashboard Visual u otros reportes, sin tener que re-geocodificar después.
- **Configuración** (Administrador de Consorcio): `PATCH /api/edificios/{id}` — contacto de emergencia, días de vencimiento de expensas, roles habilitados para ese edificio, reglas de reserva.
- **Estructura** (pisos/departamentos/cocheras/espacios comunes): CRUD estándar bajo `/api/edificios/{id}/pisos`, `/departamentos`, `/cocheras`, `/espacios-comunes`. Esta estructura es la base de la que depende el Dashboard Visual (sección 1) y todos los módulos que ubican algo "en un piso" o "en una unidad".
- **Planos**: carga de archivos (imagen/PDF) vinculados al edificio o a un piso puntual — módulo documental (sección 10) con categoría "planos".

---

## 8. Gestión financiera

Módulo más sensible: de él depende directamente el color amarillo/rojo por deuda en el Dashboard Visual.

- **Expensas:** `POST /api/edificios/{id}/expensas` genera la liquidación periódica con detalle abierto por rubro (`expensa_detalle`). Notificación automática (vía módulo de comunicados) cuando está disponible.
- **Pagos:** `POST /api/departamentos/{id}/pagos` con comprobante adjunto; estado de conciliación entre lo liquidado y lo cobrado.
- **Deudores:** endpoint calculado `GET /api/edificios/{id}/deudores` — antigüedad de la deuda en meses, alimenta directamente `deudaSeverity()` del Dashboard Visual (sección 1.3.8): 1 mes → amarillo, más de 1 mes → rojo.
- **Gastos / Fondos / Caja / Presupuestos / Facturas:** CRUD estándar, con trazabilidad completa gasto → presupuesto → factura → pago cuando corresponde.
- **Reportes:** `GET /api/edificios/{id}/reportes/financiero` — recaudado vs. esperado, morosidad, evolución de gastos por rubro. Alimenta el widget "Estado financiero" del Dashboard General (sección 1.1).

---

## 9. Gestión documental

- Repositorio por categoría (reglamento, contrato, acta, seguro, garantía, manual, certificado, legal), con visibilidad por rol definida en el Documento General (sección 7, tabla de categorías).
- Endpoint clave: `GET /api/edificios/{id}/documentos?categoria=certificado` — cada certificado con fecha de vencimiento dispara, vía el `service` de cálculo de estado, el semáforo del activo correspondiente (sección 11).

---

## 10. Gestión de proveedores

- Directorio con distinción explícita "exclusivo del edificio" vs. "también atiende particulares" (el diferencial competitivo mencionado en el Documento General, sección 8).
- `proveedores` con N rubros (`proveedor_rubro`), historial de presupuestos, historial de intervenciones (derivado de `ordenes_trabajo` donde `proveedor_id` coincide), calificación promedio calculada sobre `evaluaciones_proveedor`.
- La ficha de proveedor (`GET /api/proveedores/{id}`) agrega: datos de contacto/disponibilidad, contratos vigentes (módulo documental), historial completo, calificación.

---

## 11. Gestión de activos del edificio

Junto con el Dashboard Visual, es el otro pilar del diferencial (Documento General, sección 4 y 9).

- Ficha de activo (`GET /api/activos/{id}`): identificación, QR, fotos, estado (calculado), ubicación, historial (de `ordenes_trabajo`), garantía, manual (vínculo documental), proveedor responsable, próximo mantenimiento, costos acumulados (suma de `ordenes_trabajo.costo` + `gastos` asociados).
- **Cálculo de estado** (`services/activos.py`): verde si vigente, amarillo si el próximo mantenimiento está a ≤30 días, rojo si está vencido sin registrar la intervención. Misma función que alimenta la franja "Activos y equipamiento común" del Dashboard Visual (sección 1.2.2).
- **QR:** se genera en el momento del alta del activo (librería `qrcode` de Python) y el PNG resultante se guarda junto a la ficha; al escanearlo, abre `frontend/activos.html?id={activo_id}` directamente.

---

## 12. Gestión de mantenimiento

- **Órdenes de trabajo**: unidad central del módulo. Se originan de 3 formas — manual (admin/encargado), automática (vencimiento de un activo), o desde un reclamo (quedan vinculados vía `reclamo_id` para no perder la trazabilidad "quién lo pidió" → "qué se hizo").
- Tipos: preventivo, correctivo, programado, emergencia (Documento General, sección 10.1).
- Estados: pendiente → en curso (dispara **naranja** en el Dashboard Visual) → resuelta.
- Evidencias fotográficas antes/después (`ot_evidencias`).
- Costos: se acumulan tanto en la OT como en el activo afectado y en el gasto general del edificio.
- **Tiempo de resolución**: campo calculado (fecha_cierre − fecha_creación), alimenta el widget de KPIs del Dashboard General.

---

## 13. Gestión de reclamos

- **Creación** (propietario/inquilino): unidad, espacio común o edificio en general + prioridad percibida (leve/medio/crítico).
- **Adjuntos**: fotos/documentos de respaldo.
- **Flujo de estados**: recibido → asignado → en curso → resuelto → cerrado, visible en todo momento para quien lo cargó.
- **Comentarios**: hilo dentro del propio reclamo entre quien reclama y quien gestiona.
- **Prioridad → color**: leve/medio = amarillo, crítico = rojo, en el Dashboard Visual (vía `reclamoSeverity()`).
- **Historial**: reclamos cerrados quedan archivados y visibles como antecedente (detección de recurrencia en una misma unidad/activo).

---

## 14. Comunicación interna

- `comunicados`: título, cuerpo, segmento de audiencia (todo el edificio / un piso / una unidad puntual), creado por Administrador de Consorcio o Encargado (según configuración del edificio).
- Registro de lectura por usuario (`comunicado_lectura`) — resuelve el problema identificado en el Documento General (sección 2.1) de "no hay forma de saber si un aviso llegó a todos".

---

## 15. Reservas de espacios comunes

- `reservas`: espacio_id, usuario_id, fecha, horario, estado. Validación de solapamiento contra las reglas de reserva configuradas por edificio (sección 5.2 del Documento General).
- Pantalla tipo calendario/agenda por espacio común (SUM, parrilla, gimnasio, etc.).

---

## 16. Módulo de seguridad

- **Alcance de esta etapa**: gestión y registro de información, no integración de hardware de cámaras (fuera de alcance según Documento General, sección 1.4).
- `incidentes_seguridad`: tipo, descripción, fecha, registrado por.
- `bitacora`: registro diario operativo del encargado/personal de seguridad.
- **Botón de emergencia**: por ahora, un registro de evento de alta prioridad (`incidentes_seguridad` con tipo="emergencia") que dispara una notificación inmediata — no hay integración con servicios externos (policía/bomberos) en esta etapa.

---

## 17. Analítica y reportes

Endpoints agregados (`/api/edificios/{id}/reportes/*`) sobre los datos ya existentes de reclamos, mantenimiento y finanzas: tiempo promedio de resolución, morosidad, costo de mantenimiento acumulado, desempeño de proveedores. Los gráficos de estas pantallas, cuando se implementen, siguen las reglas de la skill `dataviz` (paleta accesible, formas de gráfico apropiadas al dato) manteniendo el semáforo funcional como el único sistema de color con licencia para representar estado.

---

## 18. Capa de Inteligencia Artificial

Definido en el Documento General como diferencial competitivo (sección 4.3) pero **fuera del alcance de las primeras fases** del Roadmap — se implementa una vez que los módulos base (reclamos, comunicados, documentación) ya existen y tienen datos reales sobre los cuales operar. Alcance funcional previsto:
- Clasificación y priorización automática de reclamos nuevos.
- Generación asistida de comunicados a partir de una idea en lenguaje natural.
- Búsqueda inteligente sobre la documentación cargada.

El proveedor/modelo de IA a integrar se define en el momento de abordar esa fase del Roadmap, no antes — evita atarse a una decisión técnica prematura.

---

## 19. Seguridad de la aplicación

- Contraseñas siempre hasheadas (`bcrypt`), nunca en texto plano en base de datos (aunque el valor de prueba sea trivial en modo test).
- Tokens JWT de corta duración; sin refresh token en esta etapa (se re-loguea) — se revisita si la fricción de uso lo justifica.
- Validación de entrada en el borde de la API vía Pydantic (nunca se confía en datos del frontend).
- CORS restringido explícitamente al origen del frontend, nunca `*` en producción.
- Todo endpoint que devuelve datos de un edificio valida pertenencia del usuario a ese edificio antes de responder (evita fuga de datos entre consorcios distintos).
- Archivos subidos (comprobantes, fotos, documentos) validados por tipo/tamaño antes de guardarse.

---

## 20. Estrategia de pruebas

Dado el enfoque incremental del proyecto (una tarea chica del Roadmap por vez, probada por el usuario antes de avanzar), la estrategia formal de tests automatizados (pytest para backend) se incorpora **a partir de que exista lógica de negocio no trivial** (cálculo de severidad del semáforo, conciliación de pagos, validación de solapamiento de reservas) — no se escriben tests de CRUDs triviales antes de que el proyecto los necesite, en línea con el principio de simplicidad de la sección 2.1. Cada módulo con lógica de cálculo (activos, financiero, reclamos → semáforo) suma su suite de tests como parte de la tarea del Roadmap que lo implementa, no como una fase separada al final.

---

## 21. Roadmap de implementación

El detalle fase por fase, con tareas chicas, verificables y aprobables una por una, vive en **`documentacion/03_Roadmap.md`**. Este documento técnico es la referencia de arquitectura; el roadmap es la ejecución.

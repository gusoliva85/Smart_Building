# Roadmap de ejecución — SMART Building


## 1. Cómo se usa este documento

### 1.1 El ciclo de una tarea

Cada `- [ ]` es un entregable chico, verificable y **aprobable por separado**. El ciclo es siempre el mismo:

1. Se implementa **una sola tarea**, la siguiente sin tildar.
2. Se explica en palabras qué se hizo, por qué, y qué hay que mirar para probarlo.
3. **El usuario la prueba y la aprueba.** Sin esa aprobación explícita no se avanza a la siguiente, bajo ninguna circunstancia.
4. Recién ahí se tilda `- [x]` y se agrega —si hizo falta— una nota corta con lo que apareció al construirla.
5. Si el usuario no la aprueba, la tarea **se revisa y se corrige en el mismo lugar**. Nunca se duplica una tarea ni se abre una nueva para arreglar la anterior.

### 1.2 El orden dentro de cada bloque: lógica → backend → frontend

Dentro de cada tema, las tareas van siempre en ese orden y se aprueban en ese orden:

| Etapa | Qué es | Cómo la prueba el usuario |
|---|---|---|
| **Lógica** | Reglas de negocio puras en `services/`, sin HTTP ni ORM. Con sus tests de pytest en la misma tarea. | Corriendo `pytest` y leyendo qué reglas quedaron fijadas. |
| **Backend** | Modelos, esquemas y endpoints que exponen esa lógica. | Desde `/docs` (Swagger), endpoint por endpoint, antes de que exista la pantalla. |
| **Frontend** | La pantalla que la consume. | En el navegador real, con cada rol que puede entrar. |

**Ejemplo concreto del criterio, tal como lo pidió el usuario:** se arranca por Usuarios. Se hace la **lógica solo de usuarios y roles**, después el **backend solo de usuarios y roles**, y recién después el **frontend solo de usuarios** — la pantalla en ese momento muestra únicamente usuarios, nada más, porque nada más existe todavía. Cuando llega el turno de Edificios, la aplicación pasa a mostrar Usuarios **y** Edificios. Y así sucesivamente: la interfaz crece de a una pantalla, nunca aparece completa de entrada.

### 1.3 Reglas duras de alcance

- **Prohibido implementar dos bloques temáticos en simultáneo.** Mientras "Usuarios" esté abierto no se toca "Edificios", aunque la tentación de "ya que estoy" exista. Es la causa más común de que algo quede a medio probar.
- **Prohibido adelantar pantallas o endpoints** de un módulo cuyo turno no llegó.
- **Prohibida una pantalla con secciones vacías o deshabilitadas** de funcionalidad futura. Si el módulo no existe, no existe su acceso en el menú (`layout.js` no linkea nunca a un archivo que no está).
- **Prohibido dar por terminada una tarea "que anda pero no se probó".** Lo no probado no está hecho.
- Si hay una razón real para alterar el orden del documento, **esa razón se escribe acá antes de saltear nada**.

### 1.4 Definición de "listo" por tipo de tarea

| Tipo | Está lista cuando… |
|---|---|
| **Lógica** | Las funciones puras existen en `services/`, tienen tests de pytest que cubren el caso feliz **y** los bordes, y la suite completa pasa en verde. |
| **Backend** | El endpoint responde correcto en `/docs`, tiene test de integración del caso permitido **y del prohibido** (un endpoint sin test de 403 es un endpoint sin control de acceso probado), y la suite completa pasa. |
| **Frontend** | Se abrió en el navegador con **cada rol** que puede entrar y con uno que no debería; se verificó en 390 px, 768 px y 1280 px; en tema claro y oscuro; con la consola limpia; con cero, uno y muchos elementos (textos largos incluidos). Checklist completo: `03_Documento_Frontend.md`, sección 12. |
| **Prueba de punta a punta** | El flujo completo del tema se recorrió con datos reales cargados a mano, no con un fixture. |
| **Documentación de fase** | Existe `documentacion/fases/Fase_N_<nombre>.md` con el contenido que define la sección 1.6. |

### 1.5 Convenciones que valen para todas las fases

- **Nomenclatura:** carpetas técnicas en inglés (`models/`, `schemas/`, `routers/`, `services/`, `core/`, `tests/`); **todo el dominio de negocio en español** (`Usuario`, `Edificio`, `calcular_prorrateo_periodo`, `transicion_valida`). El código habla el mismo idioma que esta documentación y que la interfaz.
- **Tests progresivos, no una fase aparte.** No se escriben tests de CRUD trivial. Sí se testea, siempre y en la misma tarea que la crea: toda lógica de servicio, toda regla de autorización, todo flujo de estados y todo cálculo financiero.
- **Antes de dar una tarea por terminada se corre la suite completa, no solo el archivo nuevo.** Dos regresiones reales de la iteración anterior pasaron los tests del archivo nuevo y rompieron archivos ajenos.
- **Usuarios y contraseñas de prueba se anotan en `README.md` en el momento de crearlos.** Quedó un usuario de prueba cuya contraseña nunca se documentó y, como no hay endpoint de reseteo, su login quedó inutilizable.
- **Antes de depurar algo raro, leer los dos catálogos de trampas conocidas:** `02_Documento_Tecnico.md` sección 9 (backend) y `03_Documento_Frontend.md` sección 8 (frontend). Son errores ya cometidos, con su causa exacta.
- **Toda acción destructiva se explica antes de ejecutarse** y ningún diálogo nativo del navegador (`alert`, `confirm`, `prompt`) se usa jamás.
- **Todo mensaje de error que vea un usuario entra en `core/errores.py`, y ningún endpoint escribe un texto suelto.** Es la regla que deja `F1-T29` y vale para todas las fases que siguen: cuando una tarea necesita un error que no existe, **primero** lo agrega al catálogo —con su código estable, su código HTTP y su texto en castellano— y después lo levanta por código. Un `detail=` escrito a mano en un endpoint es un error de revisión, no una variante aceptable. El motivo medido: antes del catálogo había 27 mensajes repartidos en seis archivos y el mismo fallo de guardado estaba redactado de cuatro formas distintas.
- **Y del lado de la pantalla, un error del backend se muestra siempre igual:** en un `.mensaje-error` ubicado **donde ocurrió la acción** —dentro del modal si el error fue al guardar un formulario, arriba de la lista si fue al traerla—, con el texto que mandó el servidor y sin reescribirlo. La pantalla **decide por `error.codigo`** y nunca comparando el texto, que se puede corregir en cualquier momento. Ninguna pantalla inventa su propio formato de aviso, ninguna manda un error solo a la consola, y ninguna usa un diálogo nativo. El detalle visual está en `03_Documento_Frontend.md` sección 5.4 y en la skill.

### 1.6 La tarea de documentación de cierre de fase

**Cada fase termina con una tarea `FN-DOC`.** Se ejecuta únicamente cuando **todas** las demás tareas de esa fase están tildadas y aprobadas. Produce `documentacion/fases/Fase_N_<nombre>.md`, con esta estructura fija:

1. **Qué resuelve esta fase**, en lenguaje natural, para alguien que no vio el código.
2. **Qué puede hacer cada rol** ahora que no podía antes, con un cuadro rol × capacidad.
3. **Recorrido de uso**, paso a paso, de al menos un flujo completo — con capturas o descripciones de pantalla.
4. **Las reglas de negocio que quedaron fijadas**, en castellano, con ejemplos numéricos donde aplique (ej. cómo se reparte una expensa de $4.849.900 entre 32 unidades).
5. **La parte técnica**: modelos creados (con sus campos), endpoints expuestos (con un ejemplo de request y response reales), servicios y sus funciones puras, y cuántos tests sumó la fase.
6. **Decisiones tomadas y por qué**, incluidas las que se descartaron.
7. **Deuda asumida y qué fase la salda.**

> **Por qué esta vez no se desactualiza.** En la iteración anterior existieron dos bitácoras paralelas (`que_hice.html` y una carpeta `documentacion/fases/`) que se contradecían entre sí porque se mantenían **en paralelo** al desarrollo. Acá el documento de fase se escribe **una sola vez, al cierre**, cuando ya nada de esa fase va a cambiar; el Roadmap sigue siendo el único lugar vivo. Si una fase posterior modifica algo de una anterior, se agrega una línea al final del documento de la fase vieja — no se lo reescribe.

---

## 2. Arquitectura de referencia

El detalle completo vive en `02_Documento_Tecnico.md`. Resumen operativo para no saltar de documento en cada tarea:

- **Backend:** Python 3.12 + FastAPI + SQLAlchemy + Pydantic v2 + Uvicorn. Un router por dominio bajo `/api/`. JWT (`PyJWT`, HS256) + hash con `bcrypt` usado directo. `/docs` siempre activo **en desarrollo**, apagado en producción.
- **Base de datos:** SQLite en desarrollo, PostgreSQL (Supabase, vía *connection pooler*) en producción. El entorno serverless **no tiene disco persistente, ni procesos de fondo, ni estado en memoria entre requests**: todo lo que suene a *cron* (avisar vencimientos, recordar deudas) se calcula al momento de la consulta.
- **Frontend:** multi-página estática, sin framework, sin router y **sin build**. Un `.html` por dominio, CSS propio (una hoja de tokens y un catálogo de componentes) + JavaScript vanilla ES2020+. Se evaluó Tailwind y se descartó el 2026-09-27: el sistema visual son clases compuestas propias, sus utilidades no se usarían, y sumaba una dependencia externa sin resolver nada.
- **Sistema de diseño obligatorio:** **el contrato visual del proyecto es la skill `.claude/skills/premium-uiux/`** — se carga antes de crear o tocar cualquier pantalla, y ante una duda de aspecto, gana la skill. `03_Documento_Frontend.md` es la misma especificación en versión legible y razonada. **La carpeta `documentacion/mockups/` es exploración visual histórica y no manda sobre nada.** Si una regla cambia, cambia en los dos lugares: son dos formatos del mismo contrato, no dos fuentes de verdad.
- **La lógica de negocio va antes que la base.** Toda regla no trivial se escribe y se prueba como función pura en `services/` antes de modelar la tabla que la usa. Un servicio **nunca importa un modelo** (los modelos importan constantes de los servicios; la dependencia inversa crearía un ciclo) — recibe lo que necesita por *duck typing*.
- **⚠️ La infraestructura de producción sobrevivió al reinicio.** La base de Supabase conserva el esquema y los datos del código eliminado, y Vercel quedó huérfano al borrarse el repositorio. **Antes de desplegar cualquier cosa, leer `04_Infraestructura.md`**: el mecanismo de arranque es puramente aditivo, así que un esquema viejo desalineado **falla en silencio** en vez de dar error.

---

## 3. Mapa de fases

| Fase | Tema | Qué habilita | Depende de |
|---|---|---|---|
| **0** | Fundación | Esqueleto backend + frontend comunicándose, sistema de diseño aplicado | — |
| **1** | Usuarios, roles y estructura del edificio | La base de datos de la que depende todo lo demás | 0 |
| **2** | Gestión financiera | Expensas, pagos, deudores — el color amarillo/rojo del dashboard | 1 |
| **3** | Reclamos y mantenimiento | Reclamos y órdenes de trabajo — el resto de los colores | 1 |
| **4** | Activos y seguridad normativa | Uno de los dos pilares del diferencial | 1, 3 |
| **5** | **Dashboard Visual del edificio** | El diferencial del producto | 2, 3, 4 |
| **6** | Dashboard General y Analítica | La lectura agregada para el administrador | 2, 3, 4, 5 |
| **7** | Gestión documental y proveedores | Almacenamiento real de archivos; cierra las FK diferidas | 2, 3, 4 |
| **8** | Comunicación interna y reservas | Los dos módulos de comunidad | 1, 7 |
| **9** | Módulo de seguridad | Incidentes y bitácora | 1, 8 |
| **10** | Inteligencia artificial | La capa de asistencia, con datos reales debajo | 3, 7, 8 |
| **11** | Configuración avanzada, permisos por excepción y auditoría | Cierra las decisiones postergadas de roles | todas |
| **12** | Pulido de frontend, build y PWA | Calidad de interfaz y heurísticas de UX | todas |
| **13** | Cierre y puesta en producción | Piloto con un edificio real | todas |
| **X** | Verificación de requisitos de facultad | Checklist externo, verificado contra lo construido | 13 |

**Sobre el orden.** Las Fases 2 y 3 son independientes entre sí (ambas solo dependen de la 1) y podrían intercambiarse; se deja financiero primero porque es el módulo más sensible y conviene atacarlo con la cabeza fresca. La Fase 5 no puede adelantarse: sin las tres fuentes de severidad (deuda, reclamos, órdenes) el Dashboard Visual pintaría todo verde. La Fase 7 llega antes que la 8 a propósito: es la que resuelve el almacenamiento real de archivos, del que dependen los adjuntos de todo el sistema.

---

## 4. Deuda conocida y dónde se salda

Cinco cosas que el proyecto arrastra deliberadamente. Están acá juntas para que ninguna se pierda de vista.

| Deuda | Qué significa hoy | Dónde se salda |
|---|---|---|
| **Sin carga de archivos** | Toda foto, comprobante o adjunto es un campo de URL a un archivo alojado afuera. | **Fase 7** (`F7-T01` a `F7-T04`) |
| **Claves foráneas diferidas** | `activo_id` y `proveedor_id` son enteros sueltos sin FK real en `Gasto`, `Presupuesto`, `Factura` y `OrdenTrabajo`. | `activo_id` en **Fase 4** (`F4-T03`); `proveedor_id` en **Fase 7** (`F7-T10`) |
| **Alcance del rol Auditor** | No hay mecanismo que defina a qué edificios accede un Auditor puntual. | **Fase 1** decide el mecanismo (`F1-T02`), **Fase 11** lo expone (`F11-T05`) |
| **Inquilino y el financiero de su unidad** | Propietario e Inquilino tienen el mismo acceso financiero a su unidad, por decisión adoptada (`01`, 3.1). | Se mantiene. La **Fase 11** agrega la excepción puntual para el edificio que quiera lo contrario |
| **Criterio de prorrateo por rubro** | Todos los rubros se reparten con el mismo coeficiente; no existe "planta baja exenta de ascensor". | Fuera de alcance. Se evalúa después de la **Fase 13** |

---

## 5. Cambios respecto de la versión anterior de este Roadmap

Para que quede registro de qué se corrigió y por qué:

1. **Enlaces entre documentos corregidos.** La versión anterior referenciaba `03_Roadmap.md`, `04_Documento_Frontend.md` y `05_Infraestructura.md`; los archivos reales son `03_Documento_Frontend.md`, `04_Infraestructura.md` y `05_Roadmap.md`. **Los documentos 01 y 02 todavía tienen los enlaces viejos** — se corrigen en la tarea `F0-T01`.
2. **La Fase X dejó de estar escrita en pasado.** Decía "Ya cumplido" en 15 de sus puntos, describiendo código que ya no existe. Ahora es lo que debe ser: un checklist de **verificación final**, y los 7 puntos que sí eran trabajo real se movieron a la fase donde corresponden (contraseñas robustas → Fase 1; `/docs` apagado en producción → Fase 0; rol de mínimo privilegio en la base → Fase 13; deshacer, confirmación destructiva, ayuda contextual, protección del trabajo → Fase 12).
3. **Las notas históricas se convirtieron en especificación.** Donde antes decía "se corrigió así", ahora dice "hacelo así, porque si no pasa esto". Se eliminó el ruido de bookkeeping ("el checkbox había quedado sin tildar por error").
4. **Tareas con identificador.** Cada tarea tiene un ID estable (`F2-T07`) para poder referenciarla desde otra tarea, desde un commit o desde una conversación.
5. **Cada fase se dividió en temas.** Antes había fases con 20 tareas corridas sin agrupar; ahora cada fase declara sus temas y cada tema recorre lógica → backend → frontend → prueba.
6. **Tareas nuevas que faltaban por completo:** `core/migraciones.py` en la Fase 0 (antes aparecía recién como corrección en la Fase 2), la suite base de pytest en la Fase 0, `layout.js` como tarea propia en la Fase 1, la decisión sobre `usuario_edificio` en la Fase 1, el patrón de confirmación destructiva en la Fase 1, y la tarea de documentación al cierre de cada fase.
7. **Tareas eliminadas:** `iniciar.bat` y su prueba asociada (el propio documento las daba por removidas), y el barrido circular del toggle de tema (revertido a pedido explícito y con instrucción de no reintentarlo).

---

# Fase 0 — Fundación del proyecto

**Objetivo.** Dejar el esqueleto de backend y frontend funcionando y comunicándose entre sí, con el sistema de diseño ya aplicado y sin un solo dato de negocio. Al cerrar esta fase se puede levantar el proyecto en dos terminales, abrir una página con la identidad visual definitiva y ver que el backend responde.

**Respaldo documental:** `02_Documento_Tecnico.md` (1.2, 1.3, 1.4, 6, 8) · `03_Documento_Frontend.md` (2, 3, 4) · `04_Infraestructura.md`.

**Ninguna funcionalidad de negocio en esta fase.** Ni login, ni usuarios, ni edificios.

## Tema 0.1 — Documentación y repositorio

- [x] **F0-T01 · Verificación cruzada de la documentación.**
  **Qué se hace:** lectura completa de los documentos 01 a 04 confirmando que no se contradicen entre sí, y corrección de los enlaces rotos: los documentos 01 y 02 referencian `04_Documento_Frontend.md`, `03_Roadmap.md` y `05_Infraestructura.md`, cuando los archivos reales son `03_Documento_Frontend.md`, `05_Roadmap.md` y `04_Infraestructura.md`.
  **Listo cuando:** ningún enlace interno de la carpeta `documentacion/` apunta a un archivo inexistente.

- [x] **F0-T02 · Repositorio y `.gitignore`.**
  **Qué se hace:** repositorio Git inicializado, `.gitignore` cubriendo `backend/venv/`, `backend/smart_building.db`, `__pycache__/`, `.env` y `.pytest_cache/`.
  **Cuidado con:** el `.db` de desarrollo **nunca** se versiona; el despliegue de Vercel quedó huérfano al borrarse el repositorio anterior y se revincula recién en la Fase 13.

## Tema 0.2 — Esqueleto del backend

- [x] **F0-T03 · Estructura de carpetas y entorno.**
  **Qué se construye:** `backend/app/{core,models,schemas,routers,services}/`, `backend/tests/`, entorno virtual y `requirements.txt` con `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `PyJWT`, `bcrypt`, `python-multipart`, `qrcode[pil]`, `psycopg2-binary`, `pytest`, `httpx`.
  **Listo cuando:** `pip install -r requirements.txt` corre limpio en un entorno nuevo.

- [x] **F0-T04 · `core/config.py` — configuración y variables de entorno.**
  **Qué se construye:** lectura de `DATABASE_URL`, `JWT_SECRETO`, `CORS_ORIGENES_EXTRA` y `VERCEL`, con valores por defecto que hacen que en local no haga falta configurar nada. Bandera `ES_PRODUCCION`. `verificar_configuracion_produccion()`, que **falla fuerte al arrancar** si detecta producción con el secreto JWT de desarrollo puesto.
  **Listo cuando:** el arranque local funciona sin ninguna variable definida, y forzar producción con el secreto de desarrollo impide arrancar.
  **Cuidado con:** es preferible que el despliegue no arranque a que arranque inseguro sin que nadie lo note.

- [x] **F0-T05 · `database.py` — engine, sesión y base declarativa.**
  **Qué se construye:** engine de SQLAlchemy apuntando a `DATABASE_URL` (SQLite local por defecto), `SessionLocal`, `Base` declarativa y la dependencia `obtener_db`.
  **Cuidado con:** en PostgreSQL la conexión va **por el pooler**, nunca directa: cada invocación serverless abre su propia conexión y sin pooler se agota el límite de la base con muy poco tráfico.

- [x] **F0-T06 · `core/migraciones.py` — evolución aditiva del esquema.**
  **Qué se construye:** el mecanismo que corre al arrancar la aplicación: (1) `create_all` de las tablas faltantes, (2) comparación de las columnas declaradas en los modelos contra las reales de cada tabla, emitiendo `ALTER TABLE ... ADD COLUMN` para las que falten. Más un módulo agregador que importa todos los modelos **antes** de esa línea.
  **Por qué está en la Fase 0 y no más adelante:** en la iteración anterior se construyó recién en la Fase 2, como corrección de urgencia. Sin él, cualquier campo nuevo en un modelo existente obliga a borrar la base.
  **Listo cuando:** agregar una columna anulable a un modelo y reiniciar la aplicación la crea sola, sin perder datos.
  **Cuidado con:** el mecanismo **solo agrega columnas**. No modifica tipos, no agrega restricciones ni claves foráneas sobre columnas existentes, y no borra nada. Todo lo que caiga fuera de eso necesita una migración escrita a mano — y esto es exactamente lo que hace que desplegar contra el esquema viejo de Supabase falle en silencio (ver `04_Infraestructura.md`).

- [x] **F0-T07 · `main.py` — aplicación FastAPI mínima.**
  **Qué se construye:** instancia de FastAPI, `CORSMiddleware` con whitelist explícita de orígenes (**jamás** `["*"]`), arranque del esquema (F0-T06), y `GET /api/salud` devolviendo estado y versión.
  **Incluye:** la documentación interactiva apagada en producción (`docs_url`, `redoc_url` y `openapi_url` en `None` cuando corre en Vercel). Hoy `/docs` abierto en producción deja el esquema completo de la API a la vista de cualquier visitante anónimo; en desarrollo es la herramienta con la que se aprueba cada tarea de backend, así que ahí queda activo.
  **Listo cuando:** `uvicorn` levanta, `/api/salud` responde 200 y `/docs` abre en local.

- [x] **F0-T08 · Suite base de pytest.**
  **Qué se construye:** `backend/tests/conftest.py` con el patrón de test de integración que se va a copiar tal cual en toda la vida del proyecto: motor SQLite **en memoria** con `StaticPool`, `create_all` con **lista explícita de tablas**, sobrescritura de la dependencia de sesión con `dependency_overrides` y su limpieza al final del fixture, más un helper de login que devuelve el header de autorización. Un primer test sobre `/api/salud` que confirme que el andamio funciona.
  **Cuidado con:** sin `StaticPool` cada conexión ve una base distinta y los tests fallan de forma incomprensible. La lista explícita de tablas es deliberada: hace visible qué depende de qué y falla ruidosamente si falta una.

## Tema 0.3 — Esqueleto del frontend

- [x] **F0-T09 · `assets/css/tokens.css`.**
  **Qué se construye:** la hoja de tokens exacta de `03_Documento_Frontend.md` sección 3 — tema claro en `:root` y oscuro en `html[data-theme="dark"]`. La fuente es `references/paleta-color.md` de la skill, que trae cada token con su valor exacto y con cuándo usarlo.
  **Cuidado con:** esta hoja **no dibuja nada**, no tiene una sola clase. Y los cuatro colores del semáforo no se redefinen en oscuro, a propósito: el significado de un estado no cambia según el tema.

- [x] **F0-T10 · `assets/css/components.css` — catálogo base.**
  **Qué se construye:** el fondo atmosférico con las tres manchas radiales y la textura de grano, los dos niveles de vidrio (`.shell` / `.content-glass` con su respaldo `@supports`), el esqueleto de la zona autenticada (`.layout-app`, `.sidebar`, `.main-column`, `.topbar`) y los componentes transversales (`.icon-btn`, `.pill`, `.campo`, `.boton-primario`, `.modal`, `.view-switch`). La fuente es `references/componentes.md` de la skill, que trae el HTML y el CSS de referencia de cada patrón.
  **Cuidado con:** ningún color, sombra o superficie de vidrio se escribe como valor fijo suelto. Los grupos que más se pasan por alto son justamente los que rompen el tema oscuro: sombras, vidrio y los literales de mezcla.
  **Cuidado también con `.modal`:** necesita `max-height` y `overflow-y: auto` desde el primer día. Sin eso, contenido largo de verdad se corta contra los bordes de la ventana en mobile sin forma de desplazarse. Y un modal se apoya sobre un backdrop oscuro, así que su fondo tiene que ser la variante **casi opaca** del vidrio: el 52% de blanco pensado para el fondo claro de la página se mezcla con el negro de abajo y da un gris lavado "sin los colores de la app".

- [x] **F0-T11 · Tipografía, favicon y script anti-parpadeo.**
  **Qué se construye:** carga de Outfit e Inter por Google Fonts con fallback; `assets/img/favicon.svg` (la marca reconstruida como SVG independiente, porque un favicon no puede leer las variables CSS de la página que lo referencia); y el script mínimo inline en el `<head>` de **cada** HTML, antes de cualquier hoja de estilo, que lee `localStorage` y estampa el atributo de tema.
  **Cuidado con:** si esa reaplicación espera al script del final del `<body>`, se ve un parpadeo de tema claro antes de pasar a oscuro. Es un bug ya reportado.

- [x] **F0-T12 · `index.html` — el cascarón.**
  **Qué se construye:** la primera página real del proyecto: fondo atmosférico, topbar con marca y botón de tema, y nada más. Es el "HTML básico con el estilo implementado" que pide la metodología: sin login, sin KPIs, sin edificio.
  **Listo cuando:** se ve igual de bien en 390 px y 1280 px, y la marca y el boton de tema estan en su lugar.
  **Ajuste de orden (2026-09-27):** el comportamiento del toggle se verifica en `F0-T13`, que es la tarea que lo engancha. Esta tarea entrega la pagina y el boton; la que sigue le da vida.

- [x] **F0-T13 · `assets/js/theme.js`.**
  **Qué se construye:** el toggle con la View Transitions API usando el **cross-fade por defecto del navegador, sin personalizar**, más la persistencia en `localStorage`. Sin soporte de View Transitions, el cambio es instantáneo.
  **Cuidado con:** el barrido circular desde el punto del clic ya se implementó una vez y **se revirtió a pedido explícito del usuario** (bug de z-index y lentitud reportada en Chrome). No se reintenta sin una decisión nueva.

- [x] **F0-T14 · `assets/js/config.js` y `assets/js/api.js`.**
  **Qué se construye:** `config.js` como única fuente de la URL del backend, decidida por hostname. `api.js` como envoltorio único de `fetch`: agrega el token, parsea JSON y estandariza errores.
  **Incluye desde ahora:** el código HTTP adjunto al objeto de error (para que una pantalla pueda distinguir un `409` "necesito confirmación" de un `400` cualquiera), y el manejo del `401` → limpiar sesión y volver al login, **con la excepción deliberada del propio login**, donde un 401 significa "credenciales incorrectas" y no "sesión vencida".
  **Cuidado con:** `config.js` se carga **siempre antes** que `api.js`.

- [x] **F0-T15 · `frontend/servidor_dev.py`.**
  **Qué se construye:** servidor estático de desarrollo con caché desactivada, en su propio puerto.
  **Por qué importa la caché:** sin desactivarla, media hora de depuración se va en mirar un CSS viejo.

## Tema 0.4 — Integración y arranque

- [x] **F0-T16 · Primera conexión real frontend ↔ backend.**
  **Qué se construye:** el cascarón llama a `GET /api/salud` al cargar y refleja el resultado en un indicador visual chico — el mismo punto "sistema en vivo" del techo del edificio, reutilizado como indicador de conexión.
  **Listo cuando:** con el backend apagado el indicador lo refleja, sin romper la página ni ensuciar la consola con un error no manejado.

- [x] **F0-T17 · `README.md` de arranque.**
  **Qué se construye:** cómo levantar backend y frontend a mano en dos terminales, requisitos previos, y la tabla de usuarios y contraseñas de prueba, vacía por ahora y que se completa desde la Fase 1.
  **Nota:** no se crea ningún script de arranque automático. El proyecto se versiona en GitHub y cada quien levanta los dos procesos a mano.

- [x] **F0-T18 · Prueba manual de punta a punta.**
  **Qué se prueba:** clonar en una carpeta limpia, seguir el README paso a paso, levantar los dos procesos, abrir el cascarón, ver el indicador de conexión, cambiar de tema, recargar y confirmar que el tema persistió. En mobile y en escritorio.

- [x] **F0-DOC · Documentación de la Fase 0.**
  Con todo lo anterior aprobado, redactar `documentacion/fases/Fase_0_Fundacion.md` siguiendo la estructura de la sección 1.6. Foco particular: por qué el proyecto no usa framework de frontend ni build, qué hace exactamente el mecanismo de migraciones y cuáles son sus límites.

---

# Fase 0.5 — Despliegue temprano

**Por que existe esta fase, fuera del orden original.** El plan ponia todo el
despliegue en la Fase 13. El usuario pidio adelantarlo para poder ver cada
tarea aprobada funcionando en produccion, y hay una razon tecnica que lo hace
todavia mas conveniente: **hoy no existe ni un solo modelo**, asi que vaciar el
esquema viejo de Supabase no cuesta nada. Cuando la Fase 1 cree la tabla
`usuarios`, el mecanismo aditivo se va a encontrar con una `usuarios` vieja de
otra forma, no la va a corregir y **tampoco va a dar error**. Resolverlo ahora
es gratis; resolverlo mas adelante es una migracion escrita a mano.

**Decision de arquitectura tomada aca (2026-09-27):** un solo proyecto de
Vercel, no dos. El despliegue anterior eran dos proyectos separados, lo que
obligaba al frontend a conocer el dominio del backend y a mantener CORS entre
dominios. Con un unico proyecto y una regla de reescritura, `/api/*` va a la
funcion Python y todo lo demas al frontend estatico: **mismo origen, sin CORS
en produccion**, y `config.js` funciona sin cambios.

**Esta fase no tiene documento propio.** Es un bloque de tareas adelantadas, no
una etapa funcional: quedo documentada en el **anexo (seccion 9) de
`documentacion/fases/Fase_0_Fundacion.md`**, porque lo que se desplego es
exactamente lo que construyo esa fase. Es una excepcion deliberada a la regla
de la seccion 1.6, no un olvido.

- [x] **F05-T01 · Vaciar el esquema de produccion de Supabase.**
  **Que se hace:** eliminar el esquema `public` de la base de Supabase y
  volverlo a crear vacio, para que el codigo nuevo lo construya desde cero en
  vez de arrastrar la forma del codigo eliminado.
  **Quien:** el usuario, desde el editor SQL de Supabase. No hay acceso a esa
  cuenta desde el proyecto.
  **Por que se puede hacer sin riesgo hoy:** lo que hay son datos de prueba del
  codigo eliminado, y no existe todavia ningun modelo que dependa de ellos.
  **Cuidado con:** es destructivo e irreversible. Adelanta `F13-T01`.
  **Listo cuando:** el esquema `public` existe y esta vacio, verificado con una
  consulta al catalogo de tablas.

- [x] **F05-T02 · Punto de entrada serverless y `vercel.json`.**
  **Que se construye:** `api/index.py` (el adaptador que expone la aplicacion
  de FastAPI a la funcion serverless), `requirements.txt` en la raiz (es donde
  lo busca el runtime de Python de Vercel) y `vercel.json` con la region
  `gru1` y la reescritura de `/api/*` hacia la funcion.
  **Por que la region importa:** se midio en produccion un costo fijo de
  500-600 ms por request sin ninguna consulta de por medio, porque backend y
  base podian estar en continentes distintos. `gru1` coincide con la region
  `sa-east-1` de Supabase. **Si se cambia la region de la base, se cambia esta.**
  **Listo cuando:** los tres archivos existen y la suite completa sigue en verde.

- [x] **F05-T03 · Ajustar la guarda de produccion al despliegue de dominio unico.**
  **Que se cambia:** hoy `verificar_configuracion_produccion()` se niega a
  arrancar si `CORS_ORIGENES_EXTRA` esta vacio. Con frontend y backend en el
  mismo origen, el navegador no dispara CORS, asi que exigir ese valor seria
  pedir configuracion que no hace falta. Pasa de error a advertencia registrada
  en el log; las otras dos verificaciones (secreto y SQLite) siguen siendo
  bloqueantes.
  **Listo cuando:** el test de esa guarda refleja el comportamiento nuevo y la
  suite completa sigue en verde.

- [x] **F05-T04 · Primer despliegue y verificacion en produccion.**
  **Quien hace que:** el usuario conecta el repositorio de GitHub al proyecto
  de Vercel y carga las variables de entorno (`DATABASE_URL`, `JWT_SECRETO`)
  desde el panel. **Ningun secreto entra al repositorio ni pasa por la
  conversacion.**
  **Listo cuando:** `https://<dominio>/api/salud` responde 200; la pagina abre
  con el indicador de conexion en verde; `/docs` responde **404** (la
  documentacion interactiva esta apagada en produccion); y el despliegue se
  dispara solo con cada push a `main`.
  **Sustituye a** `F13-T02`, que queda como verificacion final.

- [x] **F05-T05 · Detectar la cadena de conexion equivocada al arrancar.**
  **Por que existe esta tarea:** no estaba planificada. La agregue despues de
  perder un ciclo de despliegue completo con la cadena de conexion directa de
  Supabase en lugar de la del pooler: el host directo resuelve a IPv6, una
  funcion serverless no puede usarlo, y el error llega como un
  `Cannot assign requested address` dentro de un traceback de ochenta lineas
  que no menciona el verdadero problema.
  **Que se construye:** una verificacion en
  `verificar_configuracion_produccion()` que reconoce la cadena directa y
  responde con el mensaje exacto de que cambiar — host terminado en
  `pooler.supabase.com`, puerto 6543, usuario `postgres.<proyecto>`.
  **Listo cuando:** hay tres tests — que la directa bloquee el arranque, que la
  del pooler lo permita, y que una base que no sea de Supabase no dispare la
  regla — y la suite completa sigue en verde.

---

# Fase 1 — Usuarios, roles y estructura del edificio

**Objetivo.** Construir la base de la que depende absolutamente todo lo demás: quién entra al sistema, con qué permisos, y cómo está organizado un edificio por dentro.

**Respaldo documental:** `01_Documento_General.md` (3, 5) · `02_Documento_Tecnico.md` (3.1, 4, 5.1) · `03_Documento_Frontend.md` (4.2, 4.3, 11).

**Temas:** 1.1 Autorización · 1.2 Usuarios y autenticación · 1.3 Esqueleto de la zona autenticada · 1.4 Pantalla de usuarios · 1.5 Estructura del edificio · 1.6 Pantalla de edificios.

## Tema 1.1 — Autorización (la lógica antes que todo)

- [x] **F1-T01 · Lógica — `services/autorizacion.py`, la matriz de roles.**
  **Qué se construye:** la matriz completa de `02_Documento_Tecnico.md` sección 4.2 como **estructura de datos, no como condicionales repartidos**: los 8 roles (`admin_general`, `admin_consorcio`, `encargado`, `propietario`, `inquilino`, `proveedor`, `auditor`, `seguridad`), su alcance (cartera / edificio / unidad / órdenes asignadas), si ve el financiero de la unidad, si ve el financiero del edificio, y si es de solo lectura.
  **Reglas que quedan fijadas acá:** Propietario e Inquilino tienen **exactamente el mismo acceso financiero a nivel de su propia unidad** (decisión adoptada, `01` sección 3.1); el Encargado ve el semáforo del edificio pero **nunca los montos**; el Auditor ve todo y **no puede editar nada**.
  **Listo cuando:** hay tests que recorren los 8 roles y sus atributos, y la lista de roles válidos es la única fuente que después consumen los `CheckConstraint` de los modelos.

- [x] **F1-T02 · Decisión — cómo se resuelve el alcance de un usuario sobre un edificio.**
  **Qué se decide:** `02_Documento_Tecnico.md` sección 3.1 deja abierta una contradicción heredada: existe la tabla `usuario_edificio` pero **nunca se pobló**, y la autorización real termina consultando la base (¿es el admin de este edificio? ¿tiene una unidad acá?). Tener las dos cosas a medias fue lo que generó confusión.
  **Las dos salidas posibles:** (a) poblar `usuario_edificio` de verdad y convertirla en la única fuente de alcance; (b) eliminarla y dejar los vínculos donde efectivamente están (`edificios.admin_consorcio_id`, `edificios.encargado_id`, `departamentos.propietario_id` / `inquilino_id`), agregando en la Fase 11 un vínculo explícito para el Auditor.
  **DECISIÓN TOMADA (2026-09-27): ninguna de las dos como estaban planteadas.** Al escribir la matriz de roles (`F1-T01`) me di cuenta de que las dos opciones originales fallaban por el mismo lado: trataban a los ocho roles como si su vínculo con el edificio fuera de la misma naturaleza, y no lo es. Hay tres naturalezas distintas, y cada una tiene su lugar correcto:

  | Naturaleza del vínculo | Roles | Dónde vive |
  |---|---|---|
  | **Derivado** de un dato que ya existe | propietario, inquilino, proveedor | `departamentos.propietario_id` / `inquilino_id`; las órdenes asignadas |
  | **Responsabilidad única** por edificio (1:1) | admin_consorcio, encargado | Columnas de `edificios` |
  | **Asignación** de varios a varios (N:M) | seguridad, auditor | Tabla `asignacion_edificio` |
  | Sin vínculo | admin_general | Alcanza toda la cartera |

  **Por qué descarté la tabla puente única.** Duplicaría la verdad. El vínculo real de un propietario con un edificio es su unidad; si además hubiera que insertar una fila en una tabla puente, asignar una unidad y olvidarse de esa fila dejaría al usuario con departamento y sin acceso, sin que nada avise. Un dato que se guarda en dos lugares termina divergiendo.

  **Por qué descarté usar solo columnas.** Obligaría a una columna `seguridad_id` en `edificios`, y eso limita a **un** agente de seguridad por edificio, cuando en la realidad hay turnos. Y dejaría al Auditor sin resolver hasta la Fase 11.

  **Un hueco real que esta decisión cierra.** El rol `seguridad` tiene alcance de edificio desde el primer día y **no tenía ningún vínculo** que lo atara a uno: `edificios` solo tiene `admin_consorcio_id` y `encargado_id`. Es exactamente el mismo error que ya pasó una vez con `encargado_id`, que faltaba y se descubrió recién en la Fase 3, cuando "gestión de reclamos por Encargado" no tenía forma de resolverse. Esta vez lo encontré antes de escribir la primera tabla.

  **Consecuencias para las tareas siguientes:**
  - `usuario_edificio` **no se crea**. Sale del esquema y del Documento Técnico.
  - Se crea `asignacion_edificio` (`usuario_id`, `edificio_id`) en `F1-T03`, usada **solo** por seguridad y auditor.
  - `F11-T05` ya no tiene que inventar el vínculo del Auditor: solo expone la pantalla para asignarlo.

## Tema 1.2 — Usuarios y autenticación

- [x] **F1-T03 · Backend — modelo `Usuario`.**
  **Qué se construye:** `models/usuario.py` con `id`, `nombre`, `email` (único), `password_hash`, `rol`, `telefono`, `activo`, `creado_en`. El `rol` se valida dos veces: en Pydantic (para el mensaje de error claro) y con un `CheckConstraint` contra la lista de `services/autorizacion.py` (para que la base sea la última línea de defensa). Más `AsignacionEdificio` (`usuario_id`, `edificio_id`), la tabla de asignación N:M que decidió `F1-T02`, usada **solo** por los roles `seguridad` y `auditor`. Con una restricción de unicidad sobre el par, para que no se pueda asignar dos veces al mismo usuario en el mismo edificio.
  **Cuidado con:** la baja es siempre **lógica** (`activo = false`), nunca borrado físico, para no perder trazabilidad.

- [x] **F1-T04 · Backend — `core/security.py`.**
  **Qué se construye:** hash y verificación de contraseñas con `bcrypt`; emisión y decodificación de JWT de 60 minutos con `PyJWT`.
  **Cuidado con:** ninguna contraseña se guarda ni se loguea en texto plano en ningún punto, **ni siquiera en modo test**.

- [x] **F1-T05 · Backend — validador de contraseña robusta.**
  **Qué se construye:** validador en el esquema de alta de usuario exigiendo mínimo 8 caracteres con mayúscula, minúscula, número y carácter especial, con un mensaje que diga exactamente qué falta. El reflejo en el frontend (texto de ayuda bajo el campo) se agrega en `F1-T13`.
  **Por qué acá y no al final:** es el requisito 4 de los lineamientos de seguridad de la facultad, y agregarlo cuando ya existan usuarios creados obliga a migrar contraseñas. Nace con el modelo.
  **Máximo que me deja `F1-T04`, además del mínimo:** bcrypt no acepta más de **72 bytes**, y el límite es en bytes y no en caracteres. En castellano eso importa de verdad: con UTF-8 cada letra acentuada y la eñe ocupan 2 bytes, así que 37 caracteres acentuados ya son 74 bytes. `core/security.py` levanta `PasswordDemasiadoLarga` con el conteo de bytes y de caracteres por separado, justamente para que el validador pueda explicar la diferencia — quien escribió la contraseña cuenta letras, y un "máximo 72" a secas parece arbitrario cuando le rechaza una de 40. El validador tiene que atajarlo antes, con un 422 claro, en vez de dejar que explote en el hasheo.

- [x] **F1-T06 · Backend — `app/seed.py`, primer Administrador General.**
  **Qué se construye:** script idempotente que crea, si no existe, el Administrador General inicial con credenciales de prueba conocidas. Sin esto no hay forma de loguearse la primera vez.
  **Listo cuando:** las credenciales quedan anotadas en `README.md` **en el momento**, no después.

- [x] **F1-T07 · Backend — `routers/auth.py`.**
  **Qué se construye:** `POST /api/auth/login` (email + contraseña → JWT) y `GET /api/auth/me` (el usuario de la sesión, que es lo que el frontend usa para armar la navegación).
  **Cuidado con:** un usuario inactivo no puede iniciar sesión **y su token deja de valer aunque no haya expirado** — el estado del usuario se verifica en cada request, no solo la firma del token.
  **Lo que queda deliberadamente para `F1-T30`:** hoy los tres motivos de rechazo del login —el email no existe, la contraseña es incorrecta, el usuario está inhabilitado— devuelven el **mismo** 401 con el mismo texto, y eso deja al usuario inhabilitado reintentando su contraseña correcta sin entender nunca qué pasa. Decidí no diferenciarlos acá porque hacerlo mal abre enumeración de cuentas; la forma de diferenciarlos sin abrirla está especificada en `F1-T30`.
  **Normalización del email, que viene de `F1-T05`:** el esquema de login tiene que pasar el email por `schemas/usuario.normalizar_email`, la misma función que usa el alta. Pydantic baja a minúsculas el dominio pero **no la parte local**, así que sin eso el alta guarda `ana@...` y el login busca `Ana@...`: el usuario existe, la consulta no lo encuentra, y lo que ve la persona es "credenciales inválidas" sin ninguna pista de qué pasó.

- [x] **F1-T08 · Backend — `core/dependencies.py`, `obtener_usuario_actual`.**
  **Lo que ya quedó hecho en `F1-T07`:** `core/dependencies.py` existe con `obtener_usuario_actual`, porque `GET /api/auth/me` no podía funcionar sin él — la tarea anterior pedía que el estado del usuario se verifique en cada request, y eso es esta dependencia. Decodifica el token, busca al usuario y valida que esté activo, con tests de token vencido, token de usuario desactivado y token de usuario borrado. Escribir una versión descartable dentro del router y rehacerla acá habría sido duplicarla.
  **Lo que también quedó hecho, antes de `F1-T09`:** las dependencias de autorización que consultan la matriz — `exigir_roles(...)`, `exigir_que_pueda_escribir`, y los atajos `SoloAdminGeneral`, `SoloAdministradores` y `UsuarioQuePuedeEscribir`. Las adelanté porque el CRUD de usuarios no se puede escribir sin ellas y la alternativa era que cada endpoint resolviera los permisos por su cuenta, que es justamente lo que la matriz existe para evitar. Con tests propios en `tests/test_dependencias.py`, sobre una aplicación de juguete: así la dependencia queda probada por sí misma y no mezclada con las reglas del primer endpoint que la use.
  **Tres cosas que se fijaron ahí y valen para todo el proyecto:** el rechazo por permisos es **403 y nunca 401** (el envoltorio de `fetch` trata el 401 limpiando la sesión, así que un 403 mal devuelto como 401 desloguea a alguien que estaba perfectamente logueado); el 403 **no lleva** `WWW-Authenticate`, porque volver a autenticarse no da permisos; y la guarda de escritura es **independiente** de la lista de roles, porque el Auditor ve lo mismo que un administrador y una lista de roles amplia lo dejaría escribir.
  **Y una que evita un agujero silencioso:** los nombres de rol se validan **al declarar** la dependencia, no al atender el request. Si se validaran al atender, `exigir_roles("encargdo")` dejaría ese endpoint rechazando a todos para siempre sin un solo error en los logs — un rol que no existe no coincide con nadie — y se descubriría meses después, cuando alguien reporte que no puede entrar a una pantalla.
  **Lo que faltaba y mantuvo esta tarea abierta hasta el final de la fase:** exponer el **alcance** — sobre qué edificios o unidades opera el usuario —, que necesita los modelos `Edificio` y `Departamento` y por lo tanto no se podía construir antes de `F1-T18` y `F1-T19`.
  **Aprobada el 2026-11-12.** El alcance quedó construido en **`F1-T23`**, en un archivo propio: `core/alcance.py`, con `limitar_a_los_que_administra()` —el `WHERE` de los listados y de los endpoints de escritura— y `puede_ver()` —si una persona tiene algo que hacer en un edificio: lo administra, trabaja ahí, vive ahí o lo tiene asignado—. Está separado de `services/autorizacion.py` porque son **dos preguntas distintas**: la matriz dice *qué puede hacer un rol* y es lógica pura sin base de datos; el alcance dice *sobre qué edificios* y no se puede responder sin consultar. Se pudo cerrar recién ahí porque `F1-T23` fue la primera tarea con un endpoint que no era admin-only.
  **Lo que esta tarea desbloqueó y NO se hizo en la Fase 1: la ampliación del CRUD de usuarios al Administrador de Consorcio.** Pasa a **`F11-T07`**, y el motivo de moverla en vez de hacerla acá es que necesita una regla que es de la Fase 11 y no de esta: *nadie puede crear ni asignar un rol de más permisos que el propio*. Sin esa regla, darle el alta al Administrador de Consorcio es darle la forma de hacerse Administrador General, así que las dos cosas van juntas o no van.
  **Cuidado con:** ninguna regla de permiso se escribe dentro del cuerpo de un endpoint. Y ojo con el tipo que devuelve cada dependencia: declarar mal el tipo en la firma no falla al importar, falla en ejecución cuando alguien usa un atributo que ese objeto no tiene.

- [x] **F1-T09 · Backend — CRUD de usuarios.**
  **Qué se construye:** `routers/usuarios.py` con alta, edición parcial, listado filtrado según el rol de quien consulta, y desactivación.
  **Regla no negociable:** un usuario **no puede desactivarse a sí mismo**. Lo rechaza el backend con 400 tanto en el endpoint de desactivar como en el `PATCH` con `activo:false`. Esto no es teórico: un Administrador General se desactivó a sí mismo probando el botón, el login rechaza usuarios inactivos, hace falta ser admin para reactivar a alguien, y la cuenta quedó irrecuperable — hubo que reparar la base a mano.
  **Semántica de PATCH, válida para todo el sistema:** no mandar un campo lo deja como está; mandarlo en `null` lo borra de verdad.
  **Cómo quedó el alcance, que es lo único que no se pudo hacer como estaba escrito:** el listado filtrado según el rol de quien consulta no se puede construir todavía, porque filtrar por rol es filtrar por **alcance** y el alcance necesita `Edificio` y `Departamento` (`F1-T18`, `F1-T19`). La elección real era entre dejar el módulo solo para el Administrador General o darle el acceso al Administrador de Consorcio **sin poder limitarlo** — que no es un filtro parcial, es que vea y edite los usuarios de todos los consorcios de la plataforma, incluidos los administradores de los otros. Entre un permiso que falta y un permiso de más, falta. Queda anotado en `F1-T08` dónde se amplía.
  **Y una precondición que la ampliación tiene que traer:** sin una regla que impida crear un rol de más permisos que el propio, el alta es una escalada de privilegios — un Administrador de Consorcio que pudiera dar de alta usuarios se daría de alta a sí mismo un Administrador General.
  **Segunda regla de la misma familia que la auto-desactivación, que agregué porque deja el mismo estado irrecuperable:** un usuario **no puede cambiarse el rol a sí mismo**. Un Administrador General que se pone rol `propietario` pierde en ese instante el permiso para volver a cambiárselo, y no hace falta ni que sea un error de dedo: "me bajo el rol para ver cómo queda la pantalla" alcanza. Con las dos reglas juntas queda cerrado el último camino al sistema sin ningún administrador activo, porque toda baja y toda degradación se la aplica **otro** usuario, que por definición sigue activo.
  **El email repetido devuelve 400 y no 409**, aunque 409 sea el código semánticamente correcto: en este proyecto el `409` ya tiene significado reservado — `api.js` lo traduce a `error.necesitaConfirmacion` —, así que devolverlo haría que la pantalla ofrezca confirmar y repetir una operación que va a fallar igual. Es una limitación de usar el código HTTP como significado, y es exactamente lo que resuelve el catálogo de `F1-T29`.
  **Los esquemas de entrada rechazan los campos desconocidos** (`extra="forbid"`). Por defecto Pydantic los descarta en silencio, y en un formulario eso significa que un `nombres` por `nombre` devuelve 200 sin haber guardado nada: la persona ve que se guardó bien y no se guardó.
  **El cambio de estado va por `POST /{id}/estado` con el estado deseado en el cuerpo**, no por `/activar` y `/desactivar`: el botón de `F1-T14` es uno que alterna, y dos endpoints lo obligarían a elegir a cuál pegarle según un estado actual que puede haber cambiado en otra pestaña. Así el pedido es idempotente. Y va en el cuerpo y no como `?activo=false`, porque una URL se copia, se comparte y se llama por accidente desde la barra de direcciones, y esto cambia quién puede entrar al sistema.
  **Listo cuando:** hay test del caso permitido, del prohibido (403) y del intento de auto-desactivación (400).

## Tema 1.3 — Esqueleto de la zona autenticada

- [x] **F1-T10 · Frontend — pantalla de login.**
  **Qué se construye:** `index.html` pasa de cascarón a login real: tarjeta centrada sobre el fondo atmosférico, email y contraseña con mostrar/ocultar, mensaje de error claro ante credenciales inválidas, token en `localStorage` y redirección.
  **Incluye:** `assets/js/formularios.js`, con el toggle de contraseña que se auto-engancha y con Enter comportándose como Tab salvo en el último campo.
  **Cuidado con:** **todo** campo de contraseña del proyecto usa la estructura con toggle, sin excepción "porque es modo test". Y nunca se pisa el contenido de un `<button>` con etiquetas `<path>` sueltas: el parser de HTML no las reconoce fuera de un `<svg>` y el ícono desaparece al primer clic — se apunta al `<svg>` interno.
  **Por qué Enter como Tab:** se creó un edificio a medio cargar porque Enter en un campo intermedio envió el formulario entero.
  **Qué mensaje muestra, mientras `F1-T30` no esté hecha:** el texto que manda el backend, que en esta etapa es uno solo para los tres motivos de rechazo. La pantalla **no** interpreta el motivo ni lo adivina por su cuenta: cuando `F1-T30` agregue los códigos de error, lo único que cambia acá es de dónde sale el texto, no la lógica.

- [x] **F1-T11 · Frontend — `assets/js/layout.js`, el esqueleto por rol.**
  **Qué se construye:** el módulo que monta el sidebar y el topbar en **toda** pantalla autenticada: guarda de sesión, pedido de `/auth/me`, armado de los accesos según el rol desde **una única tabla declarada en un solo lugar**, marcado del acceso activo, hamburguesa en mobile y cierre de sesión.
  **Regla:** nunca se linkea a un archivo que todavía no existe. Un rol sin pantallas habilitadas ve un mensaje explícito, no un menú roto. En esta fase la tabla tiene una sola entrada — Usuarios — y crece una línea por fase.
  **Cuidado con:** el sidebar de mobile usa **el mismo patrón de panel deslizante** que el panel de detalle del Dashboard Visual: un componente conceptual reutilizado, no dos implementaciones. Su backdrop es transparente y solo sirve para cerrar al tocar afuera; el único backdrop que oscurece es el de los modales.

- [x] **F1-T12 · Frontend — `assets/js/view-switch.js`.**
  **Qué se construye:** el indicador deslizante de todo selector segmentado del proyecto. El fondo del botón activo no lo pinta cada botón: lo hace un único indicador que se mueve **y cambia de ancho** para calzar exacto. Se auto-engancha a cualquier `.view-switch` de la página; ninguna pantalla lo inicializa a mano.
  **Cuidado con:** si el switch está oculto al cargar, medirlo da todo en cero y el indicador queda mal para siempre. Se resuelve observando el redimensionado del propio switch en vez de medir una sola vez — y de paso cubre gratis el resize de ventana y la rotación del celular.

## Tema 1.4 — Pantalla de usuarios

- [x] **F1-T13 · Frontend — `usuarios.html`, listado y alta.**
  **Qué se construye:** listado con el patrón de fila (badge de rol anclado al nombre, acciones a la derecha) y alta en modal de formulario, con el texto de ayuda de los requisitos de contraseña de `F1-T05`.
  **Cuidado con:** el modal de formulario **nunca se cierra tocando el backdrop**, solo con la X o Cancelar — perder un alta a medio tipear es un problema real; cerrar una ficha de solo lectura no pierde nada, por eso ahí sí cierra. Y el formulario lleva `autocomplete="off"` en el email y `autocomplete="new-password"` en la contraseña: Chrome detecta el par email + contraseña como un login y autocompleta con las credenciales del administrador logueado.
  **Cuidado también con** el envoltorio de acciones de la fila: `flex-wrap` no alcanza para que envuelvan en mobile si además llevan `flex: none`; lo que realmente lo habilita es `min-width: 0`. Se verifica con un rol de texto largo de verdad ("Administrador de Consorcio"), porque con etiquetas cortas el bug no se nota.

  **Desviación del orden, anotada acá como pide la sección 1.3: esta tarea agregó un endpoint de backend.** `GET /api/usuarios/opciones`, que devuelve el catálogo de los 8 roles con su etiqueta legible y la política de contraseña. La razón es que el `<select>` de rol necesita las etiquetas ("Administrador de Consorcio", no `admin_consorcio`) y esas etiquetas viven en la matriz de `services/autorizacion.py` y no salían del backend. La alternativa era escribirlas a mano en el JavaScript, o sea tener la matriz de roles en dos lugares, que es justamente lo que `F1-T01` existe para evitar: el día que la Fase 11 agregue un rol, la pantalla seguiría ofreciendo ocho. Lo mismo con el texto de ayuda de los requisitos de contraseña, que tiene que decir **lo mismo que el 422 que la rechaza, con las mismas palabras**. Van los dos juntos en un endpoint y no en dos porque el formulario los necesita al mismo tiempo, al abrir el modal. Con sus 7 tests, incluido el de que la ruta literal no la capture `GET /{usuario_id}`.

  **Lo que quedó construido:** `usuarios.html`, `assets/js/usuarios.js`, `assets/js/cargando.js` (el indicador de espera, que nace acá porque esta es la primera pantalla con un listado), las clases de listado en `components.css`, y en `layout.js` el acceso ya construido más dos agregados: `montar({ roles: [...] })`, que declara quién puede ver la pantalla, y `paginaInicialDe(rol)`, de donde el login saca a dónde redirigir.

  **La redirección del login, que venía pendiente de `F1-T10`, entró acá.** El destino no es una constante: es la primera pantalla construida que el rol puede ver, leída de la tabla de accesos. Dos razones — no hay una pantalla de inicio única todavía (el dashboard llega en la Fase 5), y un rol puede no tener **ninguna** pantalla construida, que hoy les pasa a siete de los ocho. A esos no se los manda a `usuarios.html` para que lean que no es su pantalla: ven la tarjeta de sesión, que ahora explica que entraron bien y que todavía no hay nada para su rol.

  **Y se eliminó `frontend/verificacion-esqueleto.html`**, que existía solo mientras `layout.js` y `view-switch.js` no tuvieran una pantalla real que los consumiera.

  **Tres cosas que aparecieron al construirla y que no estaban previstas:**
  - **El botón de mostrar/ocultar contraseña no existía en el campo nuevo, y nada falló.** Estaba escrito a mano en el HTML del login, así que la regla "todo campo de contraseña lleva toggle" dependía de acordarse de copiar ocho líneas de SVG. Ahora lo genera `formularios.js` en todo `.campo-password-wrap` que no lo tenga, y la regla se cumple por construcción. Se sacó el duplicado del login para que haya una sola forma de hacerlo.
  - **Los textos que lee la persona estaban sin acentos.** El login mostraba "Email o contrasenia incorrectos." y el `aria-label` del ojo hacía que un lector de pantalla dijera "Mostrar contrasenia". El código del backend se escribe sin acentos a propósito, pero el contenido de un `detail` no es código. Se corrigieron los 15 textos que llegan al frontend, y los tests de contraseña ahora fijan los acentos para que no se "corrijan" al estilo del resto del archivo. **Esto no reemplaza a `F1-T29`**, que es otra cosa: un catálogo con códigos de error, no la ortografía.
  - **La skill y el CSS real tenían nombres de clase distintos** para el modal (`.modal-close` / `.open` contra `.modal-cerrar` / `.abierto`). Copiar del documento que manda habría dado un modal que no se abre. Corregido en la skill, con la convención escrita: las clases de estado van en castellano.

  **Cómo se verificó:** 287 tests de backend en verde (13 nuevos), más dos arneses headless sobre las páginas reales contra el backend real — 89 comprobaciones de `usuarios.html` (el listado, el alta, el email repetido que deja el modal abierto con lo tipeado, la contraseña débil, Escape, el rol ajeno que lee una explicación en vez de un 403, y que ninguna clase del DOM falte en el CSS) y 23 de `index.html` (el toggle generado, la redirección del administrador, la tarjeta explicada del rol sin pantallas). Más la revisión en navegador, que es la que cerró la tarea.

  **Lo que salió de esa revisión, y es la lección más útil de toda la tarea.** El alta estaba bien, pero las filas del listado se veían cuadradas, sin márgenes y "genéricas" — lo reportó el usuario, no un test. La causa: **`.shell` y `.content-glass` declaran solo la superficie de vidrio y ninguna de las dos pone `border-radius` ni `padding`.** Es deliberado, porque un chip, una fila, un panel y un modal necesitan medidas distintas; pero significa que todo lo que se apoya en ellas tiene que poner las suyas, y no ponerlas **no falla nada**: queda una caja cuadrada con el texto pegado al borde. Me pasó en dos lugares a la vez, la fila y el panel que la contiene.

  Se corrigió dando a `.fila-lista` las mismas medidas que `.detail-item` del panel de detalle —es el mismo nivel de vidrio y el mismo tipo de contenido, así que tienen que leerse como el mismo componente—, creando `.panel-contenido` para el panel de la pantalla (que además saca un `style="padding:…"` en línea que no debería haber estado), y pasando el nombre del usuario a **Outfit**: el dato principal de una pieza de vidrio va en Outfit igual que `.detail-field b` o `.kpi-num`, e Inter queda para la línea de datos secundarios. El usuario notó incluso eso, que la fuente no era la del resto.

  Quedó anotada como trampa en `03_Documento_Frontend.md` sección 8 y, sobre todo, **arriba de la sección del vidrio en la skill**, que es de donde se copia para armar las trece pantallas que faltan. Y hay un chequeo automático que recorre todo lo que se combina con `.shell` o `.content-glass` y avisa si alguna clase quedó sin radio.

- [x] **F1-T14 · Frontend — edición y botón de estado con ripple.**
  **Qué se construye:** ícono de editar en cada fila que abre el mismo modal en modo edición (nombre, rol y teléfono; email y contraseña quedan fuera porque el backend no los acepta por esa vía), y el botón que **muestra** el estado activo/inactivo **y lo alterna** al tocarlo, con un ripple que nace del punto del clic.
  **Cuidado con el ripple:** la primera versión hacía crecer el círculo y lo desvanecía a la vez, así que para cuando cubría el botón ya era invisible. Tiene que mantenerse **opaco durante todo el crecimiento** y desvanecerse solo al final, y la transición de fondo del botón tiene que ser **más lenta** que el ripple para que el ripple pinte primero. El texto va en un `<span>` interno: escribir directo sobre el botón borraría los ripples en curso.
  **Cuidado con:** el botón está **deshabilitado** en la fila del usuario logueado, con un texto que explica por qué. Doble resguardo con el backend de `F1-T09`.

  **Corrección de esta misma tarea, anotada acá como pide la sección 1.3: el email SÍ se puede editar.** La tarea decía que "email y contraseña quedan fuera porque el backend no los acepta por esa vía", y eso es cierto de la contraseña pero **falso del email**: `UsuarioEditar` lo declara, el router verifica que no esté tomado por otro y lo normaliza con la misma función que el alta. Lo comprobé en vivo con un PATCH antes de escribir la pantalla.

  Así que lo incluí, y la razón de fondo no es que el backend lo permita, es lo que pasa si no está: un email cargado con un error de tipeo es una cuenta que **nunca va a poder iniciar sesión y no se puede arreglar desde la interfaz**. No hay endpoint de recuperación de contraseña ni de corrección de email, así que la única salida sería editar la base a mano. Es exactamente la misma forma del problema que ya dejó una cuenta inutilizable en la iteración anterior (la contraseña de prueba que nunca se documentó, sección 1.5). Entre ofrecer un campo de más y dejar un estado sin salida, el campo. La contraseña sí queda afuera de verdad: no está en el esquema de edición y, con `extra="forbid"`, mandarla devuelve un 422.

  **Lo que quedó construido:** el ícono de editar y el botón de estado en cada fila, el modal reutilizado en modo edición, y en `components.css` el botón con su ripple. **Es UN solo modal, no dos**: dos serían el mismo formulario escrito dos veces y el día que se agregue un campo habría que acordarse de los dos. Lo que cambia es el título, la bajada, el texto del botón y si el bloque de contraseña está — se **esconde** al editar, no se deshabilita, porque un campo gris que no se puede usar invita a preguntarse por qué.

  **Las acciones de fila van por delegación en el contenedor del listado**, no un listener por fila. El listado se reemplaza entero con `innerHTML` en cada recarga, así que los listeners fila por fila se perderían y habría que volver a engancharlos; delegando, las filas nuevas funcionan solas. El botón se busca con `closest()` y no comparando contra `event.target`, porque el clic puede caer en el `<svg>` o en el `<span>` de adentro.

  **El ripple quedó como lo pedía la especificación, y con guardas automáticas.** Las dos lecciones —opaco durante todo el crecimiento, y la transición del fondo más lenta que el ripple (700 ms contra 550)— están implementadas, y hay dos comprobaciones que las fijan: una lee los `@keyframes` y verifica que al 70% ya esté en `scale(1)` y **siga** en `opacity:.95`, otra compara las duraciones y falla si la del fondo no es la mayor. Sin esas guardas, alguien "limpia" el keyframe a un fade normal y el efecto desaparece de nuevo sin que nada avise.

  **Tres cosas que agregué y que la tarea no pedía:** el botón se bloquea mientras viaja el pedido (dos clics rápidos mandarían dos cambios y ganaría el que contestara último); al llegar la respuesta se repinta con **lo que contestó el backend** y no con lo que se supuso, por si otra pestaña cambió algo en el medio; y `prefers-reduced-motion` esconde el ripple, sin perder información porque el estado se sigue comunicando con el color y con la palabra.

  **Y se quitó el chip punteado de "Inactivo"** que la fila tenía desde `F1-T13`: este botón ya dice la palabra, y dos elementos comunicando el mismo estado en la misma fila es lo que este componente vino a resolver.

  **Lo que NO hace, a propósito:** el botón alterna directo, sin preguntar. La confirmación de acción destructiva es `F1-T15`, la tarea siguiente, y ahí se intercala el componente de confirmación delante de la desactivación.

  **Cómo se verificó:** 287 tests de backend en verde (sin cambios de backend en esta tarea) y un arnés headless de 54 comprobaciones sobre la pantalla real contra el backend real — la precarga del formulario (incluido que el rol sea el del usuario y no el primero de la lista), que el PATCH no pise la contraseña (se comprueba iniciando sesión después de editar), que el email se pueda corregir, que el mismo modal vuelva a modo alta y arranque vacío, que el ripple nazca del punto del clic y no del centro, que el cambio sea optimista, que un rechazo del servidor **revierta** el color, que un usuario desactivado ya no pueda entrar, y que el backend rechace con 400 que uno se desactive a sí mismo tanto por `/estado` como por `PATCH`. **Falta tu revisión en navegador**, que es la que cierra la tarea: hay que *ver* que el ripple se note, que es justamente lo que la primera versión no cumplía.

- [x] **F1-T15 · Frontend — patrón de confirmación de acción destructiva.**
  **Qué se construye:** el componente reutilizable de confirmación, estrenado acá con la desactivación de un usuario, que se usa en **todo el resto del proyecto**: el mensaje dice exactamente qué se va a perder o reescribir, no "¿estás seguro?", y el botón de acción cambia su texto a algo explícito ("Confirmar y desactivar").
  **Cuidado con:** prohibido `alert()`, `confirm()` y `prompt()` en toda la aplicación. Rompen la identidad visual, no son responsive y no permiten explicar consecuencias.

  **Lo primero que encontré es que el proyecto ya tenía un patrón de confirmación documentado, y no servía para esto.** La sección 9.1 del Documento Frontend describe uno solo: el usuario manda la acción, el servidor contesta `409` explicando qué se va a sobrescribir, y el botón del formulario cambia de texto. Eso funciona para la regeneración de expensas, donde el mensaje necesita un dato que solo el backend conoce (cuántas expensas ya emitidas se reescriben). Para un botón de una fila no sirve: no hay formulario donde poner un segundo envío, y pedirle un `409` al backend sería agregar un ida y vuelta —y un endpoint que falla a propósito— para preguntar algo que el frontend ya sabe.

  Así que ahora hay **dos** formas de confirmar, con un criterio de corte escrito para no volver a dudar: ¿hace falta un dato del servidor para redactar el mensaje? Entonces el `409`. ¿Ya se sabe lo que va a pasar? Entonces el modal. Quedó en 9.1, con las dos.

  **Lo que quedó construido:** `frontend/assets/js/confirmar.js`, que se pide con `Confirmar.pedir({titulo, mensaje, textoAccion})` y devuelve una promesa con `true` o `false`, más `.modal-confirmar` y `.boton-peligro` en `components.css`. **El HTML del modal no lo escribe ninguna pantalla:** lo arma el módulo una sola vez y lo cuelga del `<body>`. Catorce pantallas copiando el mismo bloque serían catorce lugares para arreglar el día que cambie el componente — la misma razón por la que en `F1-T13` el botón del ojo pasó a generarlo `formularios.js`.

  **La promesa nunca se rechaza.** Cancelar no es un error, es una respuesta: un `reject` obligaría a cada pantalla a poner un `catch` que no distinguiría "dijo que no" de "se rompió algo".

  **Y se pregunta solo al desactivar, no al reactivar.** Reactivar no destruye nada y se deshace con otro toque, así que preguntar ahí solo agrega un paso — y un modal que aparece siempre se cierra sin leerlo, que es exactamente como se arruina el único momento en que el mensaje importa.

  **El texto del modal me llevó más tiempo que el componente, y creo que es lo que de verdad hace el trabajo.** Dice qué pasa y, sobre todo, qué NO pasa: "no va a poder volver a iniciar sesión. Sus datos no se borran y la cuenta se puede reactivar desde este mismo listado cuando haga falta". Sin la segunda frase, "desactivar" se lee como "borrar" y la respuesta honesta pasa a ser cancelar siempre. Las tres reglas de redacción (nunca "¿estás seguro?", aclarar si se deshace, el verbo en el botón) quedaron en la skill, que es de donde se va a copiar para el resto del proyecto.

  **Dos decisiones de teclado que no son de gusto.** El foco arranca en **Cancelar** y no en el botón de acción: con el foco en la acción, un Enter de más —el mismo que venía de enviar un formulario— confirma sin que nadie lea el mensaje. Y en mobile los botones se apilan con la acción **abajo** (`column-reverse`), aunque en el HTML Cancelar vaya primero: el orden del HTML es el correcto para el teclado, el visual es el correcto para el pulgar.

  **Y este modal SÍ se cierra tocando el velo**, al contrario del modal de formulario de `F1-T13`. No es una inconsistencia: en un alta a medio tipear un toque al costado pierde trabajo, y acá tocar afuera es exactamente lo mismo que cancelar.

  **Tres defectos que encontré construyéndolo, los tres de accesibilidad y los tres invisibles mirando la pantalla:**

  1. **El modal cerrado seguía siendo alcanzable con Tab.** Se esconde con `opacity` y `pointer-events`, que lo saca del mouse pero no del teclado ni del lector de pantalla: un Tab desde el listado se metía en los dos botones de una pregunta que no estaba abierta. Se resuelve con `inert` más `aria-hidden`, y el orden importa — se quita antes de pedir el foco al abrir, y se pone después de devolverlo al cerrar.
  2. **Devolver el foco "a donde estaba" falla cuando no estaba en ninguna parte.** `document.activeElement` devuelve el `<body>`, y pedirle `focus()` no mueve nada, así que el foco se quedaba dentro del modal recién escondido. Hay que tratar al `<body>` —y a cualquier elemento que ya no esté en el documento— como "sin foco previo" y soltarlo explícitamente.
  3. **Mi primera versión deshabilitaba el botón de estado mientras el modal estaba abierto**, que parecía lo prudente. Es justo lo contrario: al cerrar, el modal devuelve el foco a quien lo abrió, y el foco no entra en un botón deshabilitado — se iba al `<body>` y el teclado quedaba recorriendo la página desde el principio. Tampoco hacía falta: el modal tapa la fila, así que un segundo clic cae en el velo.

  **Y una cosa que ya estaba y había que no romper:** el ripple del botón de estado nace del punto del clic, y ahora entre el clic y el ripple hay un modal. Las coordenadas se copian al hacer clic, porque para cuando se contesta la pregunta el evento original ya no sirve. Además, si la fila se movió mientras el modal estaba abierto (porque apareció o se fue el aviso de éxito de arriba) el punto guardado puede caer fuera del botón; en ese caso el ripple nace del centro, que siempre está bien.

  **Cómo se verificó:** 287 tests de backend en verde (esta tarea no toca el backend) y un arnés headless de 68 comprobaciones sobre la pantalla real contra el backend real — que desactivar pregunte y no cambie nada hasta confirmar (verificado también contra el backend, no solo en la pantalla), que Escape, el velo y Cancelar cancelen y no desactiven, que un clic sobre el texto del mensaje NO cierre, que confirmar sí desactive y que el desactivado ya no pueda entrar, que reactivar no pregunte, que el foco arranque en Cancelar y vuelva al botón que abrió la pregunta, que el Tab quede atrapado en los dos sentidos, que una segunda pregunta no tape la abierta, que un nombre con `<b>` no se interprete como HTML, y un barrido sobre todos los `.js` y `.html` del frontend confirmando que **nadie** llama a `alert()`, `confirm()` ni `prompt()`. El arnés de `F1-T14` se actualizó para contestar el modal: lo que verifica es lo mismo, lo que cambió es que ahora hay un paso antes.

  **Falta tu revisión en navegador**, que es la que cierra la tarea. Lo que conviene mirar: que el mensaje se entienda leído rápido (es lo único que de verdad previene el error), que el rojo del botón no quede estridente al lado del resto, y que en el celular los dos botones apilados queden cómodos.

- [x] **F1-T16 · Prueba de punta a punta — usuarios.**
  **Qué se prueba:** correr el seed, loguearse con el Administrador General, dar de alta un usuario de cada rol que vaya a hacer falta más adelante, confirmar que cada uno entra y ve únicamente lo que le corresponde (en esta fase: sidebar acotado y pantallas ajenas bloqueadas), intentar desactivarse a uno mismo y confirmar que no se puede ni desde la interfaz ni por API, probar una contraseña débil y confirmar que el backend la rechaza, y verificar que todas las credenciales quedaron en `README.md`.

  **Lo primero que decidí es que esta prueba no podía quedar solo en mi máquina.** Las otras tareas las verifiqué con arneses que viven en la carpeta temporal de la sesión: sirven para cerrar la tarea y después se van. Pero esta tarea *es* la prueba, así que si se va con la sesión, el tema queda sin forma de volver a verificarse. Lo dividí en dos según dónde puede correr cada mitad:

  - **`backend/tests/test_e2e_usuarios.py`, en el repositorio** (20 tests). Todo el recorrido por HTTP, con el login real. Es la mitad que importa para la seguridad: lo que se **puede** hacer. Corre con el resto de la suite, así que de acá en adelante cualquier cambio que rompa el recorrido completo se nota sin que nadie se acuerde de correr nada aparte.
  - **La mitad de navegador, en un arnés de la sesión** (103 comprobaciones). El sidebar acotado y el bloqueo de la pantalla ajena viven en `layout.js`, que es JavaScript de navegador: pytest no puede verlo.

  **Por qué la mitad de navegador no quedó en el repositorio, y es una decisión tuya.** Necesita `jsdom`, o sea `package.json` y `node_modules` en un frontend que hoy, a propósito, no tiene ni framework ni paso de compilación (sección 4.1 del Documento Frontend). No me pareció que pudiera meter esa dependencia por mi cuenta como efecto secundario de una tarea de pruebas. **Las dos opciones son razonables:** o se asume `node_modules` solo para pruebas —el frontend que se sirve sigue sin build— o se acepta que la capa de navegador se verifica a mano en cada tarea. Si decidís la primera, lo paso al repositorio y queda corriendo siempre.

  **Qué encontró el e2e de backend, probándolo contra el código roto a propósito.** Un test que nació en verde y nunca falló no prueba nada, así que saqué la guarda de auto-desactivación del PATCH y lo corrí: falló, y de la forma reveladora: `/estado` siguió devolviendo 400 y PATCH devolvió 200. Es exactamente el agujero para el que escribí el test — hay **dos** endpoints que pueden desactivar una cuenta, y cubrir solo el que usa el botón deja abierta la vía de la API, que es la que usaría cualquiera con `curl` en la mano. El resultado de equivocarse ahí no es un error cualquiera: es un sistema sin ningún administrador que pueda entrar y sin forma de arreglarlo desde la aplicación.

  **Y un defecto en mi propia prueba de navegador, que es el hallazgo más útil de la tarea.** Mi primera versión daba 71 de 71 en verde. Para comprobar que medía algo, saqué la guarda de rol de `usuarios.js` y la volví a correr: **siguió en 71 de 71.** Pasaba por dos motivos equivocados a la vez:

  1. Buscaba un texto suelto en todo el `<body>`, y el sidebar de un rol sin pantallas ya dice "Todavía no hay pantallas habilitadas para tu rol" — en los dos casos.
  2. Verificaba que no hubiera filas en el listado, y sin la guarda las filas quedaban en cero igual: las dejaba vacías el 403 del backend.

  O sea que estaba midiendo el **resultado** y no el **mecanismo**, y el resultado lo lograba el backend solo. Ahora comprueba tres cosas que únicamente pueden pasar si la guarda corrió: el `<h1>` exacto que escribe `mostrarSinAcceso()`, que el contenido propio de la pantalla haya sido reemplazado y no tapado, y que **no** aparezca el cartel del 403 — porque si aparece significa que la pantalla alcanzó a pedir el listado, o sea que la guarda no la frenó. Con eso, el mismo mutante produce 21 fallas en los siete roles. Y queda a la vista lo que la guarda aporta de verdad: sin ella, la persona ve "Esta acción es solo para: Administrador General" en vez de una explicación.

  **El último punto del checklist quedó automatizado**, y creo que es el que más vale: el arnés **lee `README.md`**, saca las ocho filas de la tabla de credenciales e intenta entrar con cada una, verificando además que el rol anotado sea el real. Lo probé cambiándole la contraseña del Auditor en el README: falla. Es lo único que protege contra la deriva de la que el propio README se advierte, y contra el error concreto que en la iteración anterior dejó una cuenta inutilizable para siempre.

  **Los ocho usuarios quedaron creados y anotados.** Uno por rol, los siete nuevos dados de alta por la API real y no insertados en la base, para que si el alta tuviera un problema esto fallara. Todos con la misma contraseña a propósito: ocho distintas no prueban nada que esta no pruebe y multiplican por ocho la chance de anotar una mal. Hoy siete de los ocho entran y no ven ninguna pantalla, y está bien — la única construida es Usuarios. Sirven desde ahora, en cada fase, para verificar que cada rol vea solo lo suyo.

  **Algo que encontré de paso y arreglé: la base de desarrollo tenía veinticinco usuarios de basura** dejados por mis propios arneses de `F1-T13`, `F1-T14` y `F1-T15`, mezclados con el administrador. No molestaban a las pruebas, pero el listado de la pantalla era ilegible y la verificación de "cada rol ve lo que le toca" no se podía hacer sobre esa base. Respaldé el `.db` antes de tocar nada y establecí la convención que lo hace mecánico de acá en adelante: **todo usuario que crea una prueba usa `@ejemplo.com`, y los ocho documentados usan `@test.com`.** Quedó escrito en el README, con un limpiador que borra por dominio. El borrado va por la base porque no hay endpoint de borrado — y es correcto que no lo haya: el sistema desactiva, no borra.

  **Cómo se verificó:** **307 tests de backend** en verde (20 nuevos), **103 comprobaciones** del arnés de navegador sobre los ocho roles, y los arneses anteriores siguen en verde — 89 de `F1-T13`, 57 de `F1-T14`, 68 de `F1-T15` y 23 del login. Los dos mutantes que probé (la guarda de PATCH y la guarda de rol) fallan como deben.

  **Revisado y aprobado en navegador.** Entré con el Administrador General y con tres roles sin pantallas: el mensaje de "no hay pantallas habilitadas para tu rol" se entiende y no parece un error roto, ni entrando normal ni escribiendo `usuarios.html` a mano en la barra de direcciones.

  **La decisión sobre `jsdom` quedó sin tomar, y es deuda consciente.** Mientras no se tome, la capa de navegador se verifica a mano en cada tarea de frontend. No bloquea nada, pero cada tarea que pasa es una verificación más que no queda corriendo sola.

  **Y una cosa que encontré después de darla por cerrada, que vale anotar.** El arnés de `F1-T14` fallaba dos de cada tres corridas en "el PATCH no tocó la contraseña". No era el producto: el arnés editaba el primer usuario del listado y **daba por sentado** que su contraseña era la que esperaba, sin crearlo nunca — funcionaba de casualidad porque otro arnés dejaba usuarios con esa contraseña. Peor: una corrida vieja le cambió el email a `adminconsorcio@test.com`, uno de los ocho documentados, y el limpiador después lo borró porque ya no parecía documentado. Lo recreé y arreglé las dos puntas: el arnés crea y edita **su** usuario, y el limpiador borra solo por la convención `@ejemplo.com` y **reporta** lo que no encaja en vez de adivinar. **La lección es la misma que la del mutante de arriba:** una prueba que depende del estado en que quedó la base no está midiendo el producto. El 57 de 57 reportado en su momento era cierto sobre una base limpia, pero el arnés era frágil y no lo había corrido dos veces seguidas.

- [x] **F1-T16A · Backend — registro público y rol `pendiente`.**
  **De dónde sale esta tarea:** no estaba en el plan. Salió de una pregunta al terminar `F1-T16` — si el único que puede dar de alta usuarios es el Administrador General, cada persona del consorcio tiene que pedirle el alta por fuera del sistema y dictarle sus datos. Para un edificio de cuarenta unidades eso no escala, y además el administrador termina cargando datos que no son suyos. La solución es que cada uno se registre y el administrador solo **apruebe**.

  **Qué se construye:** un `POST /api/auth/registro` **público** — el primer endpoint de escritura sin autenticación del sistema — que crea un usuario con nombre, email, teléfono y contraseña, y lo deja con `rol = 'pendiente'`.

  **Por qué `pendiente` es un valor del rol y no un campo nuevo.** Evalué tres formas y las otras dos son peores:
  - **`rol` nulo:** hoy todo el sistema asume que `rol` es un valor válido de la matriz — el `CheckConstraint` del modelo, los validadores de Pydantic, `autorizacion.obtener()` que falla ruidosamente ante un rol desconocido. Un nulo obliga a agregar una rama "¿y si no tiene rol?" en cada uno de esos lugares, y alcanza con que falte una para tener un agujero.
  - **`activo = False`:** confunde dos hechos distintos — "lo desactivó un administrador" y "nunca fue aprobado" —, que son cosas diferentes en la pantalla, en el mensaje que lee la persona y en la trazabilidad. Y bloquea el login, cuando lo que se quiere es que la persona entre y lea que su cuenta está esperando aprobación.
  - **`rol = 'pendiente'`, un noveno valor en la matriz:** cada pantalla ya declara su `ROLES_HABILITADOS` y `pendiente` no está en ninguna, así que queda afuera de todo **sin escribir una sola línea de autorización nueva**. El login funciona y el `CheckConstraint` sigue siendo exacto. Es la que se implementa.

  **Cambio obligatorio que lo acompaña: `ROLES` se parte en dos.** Hoy es una sola tupla que responde dos preguntas distintas — "¿este valor es válido en la base?" y "¿qué roles puede elegir un administrador?" —. `pendiente` es sí a la primera y **no** a la segunda: nadie se lo puede asignar a nadie, lo pone únicamente el registro. Quedan `ROLES` (válidos, los 9) y `ROLES_ASIGNABLES` (elegibles, los 8), y el endpoint de opciones y la validación del alta pasan a consumir la segunda.

  **El único lugar donde un error acá es una escalada de privilegios:** el schema del registro **no tiene** el campo `rol`, y lleva `extra="forbid"` para que mandarlo sea un 422 y no un silencio. Si ese campo entra, cualquiera en internet se da de alta como `admin_general`.

  **Y una consecuencia que hoy no existe:** el alta actual devuelve **400 cuando el email ya existe**, y eso está bien en un endpoint que solo usa el administrador. En uno público es un oráculo de enumeración — cualquiera prueba emails y averigua quién está registrado. El registro responde **siempre lo mismo**, exista o no el email. El aviso de "ya tenés cuenta" se manda por mail cuando haya mail; mientras no haya, no se avisa.

  **Qué queda explícitamente afuera:** el edificio. `Edificio` no existe como modelo hasta `F1-T18`, y un usuario pendiente no tiene rol, así que no puede ver datos de ningún edificio igual. El edificio se asigna **en el mismo momento en que se le da el rol**, que es cuando empieza a importar.

  **Listo cuando:** hay tests de que el registro crea con `rol = 'pendiente'`, de que mandar `rol` da 422, de que un email repetido responde igual que uno nuevo, de que un pendiente puede loguearse pero recibe 403 en todos los endpoints de las pantallas, y de que `pendiente` no aparece en `/usuarios/opciones`.

  **Cómo quedó.** `POST /api/auth/registro` responde **202** y siempre lo mismo: un único campo `mensaje`, sin id ni datos. El rol se escribe como constante en el endpoint y `RegistroPublico` no declara el campo `rol`, con `extra="forbid"` para que mandarlo sea un 422 y no un descarte silencioso. `ROLES` se partió en `ROLES` (los 9 que acepta la columna) y `ROLES_ASIGNABLES` (los 8 que alguien puede elegir), con `es_asignable()` al lado de `es_rol_valido()`; los validadores de alta y edición preguntan por la primera. `pendiente` entró a la matriz con alcance `ninguno` y `solo_lectura=True`, que es un resguardo y no una descripción — está explicado en la matriz y fijado por un test para que nadie lo "corrija" más adelante.

  **El corte de `ROLES` rompió ocho tests, y ninguno era un bug.** Eran tests que preguntaban por `ROLES` cuando lo que querían saber era `ROLES_ASIGNABLES`: hasta que existió `pendiente` las dos preguntas daban la misma respuesta, así que no había forma de notar que eran dos. Es la señal de que el corte hacía falta.

  ### Y acá está lo que de verdad dejó esta tarea

  **El bug que los tests no podían encontrar.** Con los 46 tests nuevos en verde, probé el recorrido contra el backend de desarrollo. El registro devolvió **`202 Accepted` sin crear el usuario.** La tabla `usuarios` de esa base se había creado antes de que existiera `pendiente`, así que su `CheckConstraint` listaba ocho roles y rechazaba el INSERT.

  Hubo **dos defectos, no uno**, y conviene separarlos porque las lecciones son distintas:

  1. **Mi `except IntegrityError` era demasiado ancho.** Estaba ahí para responder igual ante un email repetido —la defensa contra la enumeración— y sin que yo lo pensara convertía **cualquier** falla de integridad en un éxito silencioso. Es el peor tipo de bug que se puede escribir: no hay log, no hay error, y la persona cree que se registró. Corregido: solo se traga el choque si el email **está** en la tabla; si no está, el INSERT falló por otra razón y se vuelve a lanzar. Se pregunta por el estado de la base y no por el código de error del driver, porque ese código es distinto en SQLite y en PostgreSQL y el proyecto corre contra los dos.

  2. **El esquema real no coincidía con el declarado, y nada avisaba.** `core/migraciones.py` es aditivo a propósito y lo documenta, pero la consecuencia es que un CHECK nuevo sobre una columna existente no se aplica **y tampoco da error**. Así que la aplicación arrancó informando "sin cambios" y trabajó contra una tabla que no era la que el código declaraba. Esto no se arregla con un `except`: necesita una migración escrita a mano.

  **Por qué pytest no lo encontraba, y por qué no es un descuido del andamio.** El `conftest.py` crea las tablas desde los modelos actuales, así que su CHECK sí incluía `pendiente` y el INSERT nunca fallaba. Es correcto que las pruebas corran contra el esquema declarado. Lo que falta —y es la lección general— es que **un esquema declarado y una base real no son lo mismo, y ninguna prueba de integración contra una base recién creada va a notar la diferencia.** Queda un test que reproduce la *clase* de problema: fuerza un INSERT que la tabla rechaza por un motivo que no es el email y fija lo único que importa, que el endpoint **no** conteste que todo salió bien.

  **Lo que salió de ahí: `app/migraciones_manuales/`.** Una carpeta nueva con la convención escrita —un archivo numerado por migración, idempotente, que funciona en SQLite y en PostgreSQL, y que nunca se cuelga del arranque— más `m001_rol_pendiente.py`, que ensancha el CHECK. En PostgreSQL son dos sentencias; en SQLite hay que reconstruir la tabla, y el DDL de la nueva se genera **desde el modelo** para que no haya que actualizar la migración cada vez que cambie una columna. Copia nombrando las columnas y no con `SELECT *` —si el orden difiere, un `SELECT *` las mete corridas y el dato queda en la columna equivocada sin que falle nada—, verifica las claves foráneas antes de confirmar, y al final inserta una fila con el rol nuevo y la borra, porque que el DDL diga lo correcto y que la base acepte el INSERT son dos cosas distintas.

  **Esto es un paso de despliegue, no un detalle interno.** La base de Supabase existe desde antes del rol `pendiente`, así que **el registro va a fallar en producción aunque funcione en desarrollo** hasta que se corra la migración allá. Quedó anotado en el README, antes del bloque del seed y en el mismo orden en que hay que correrlo.

  **Cómo se verificó:** **382 tests** en verde (46 nuevos). Siete mutantes probados uno por uno: el esquema aceptando el rol, el email repetido devolviendo 400, el registrado quedando inactivo, `validar_rol` volviendo a `es_rol_valido`, el formulario ofreciendo `ROLES`, `pendiente` entrando en los asignables, y el `except` ancho — los siete se detectan. Un octavo **no** se detecta y está bien que no: romper *solo* el endpoint —hacerle leer un `rol` del pedido en vez de usar la constante— no cambia nada, porque sin el campo en el esquema no hay nada que leer. Es un mutante equivalente, y es literalmente lo que significa tener dos barreras; rotas las dos juntas, fallan 9 tests. **La lección: al probar defensa en profundidad hay que romper las dos a la vez, y que una sola no haga fallar nada no significa que sobre.** La migración se probó primero contra una copia de la base de desarrollo, comparando las ocho filas campo por campo —incluido el hash—, los índices, la unicidad del email, `foreign_key_check` e `integrity_check`, y corriéndola dos veces para la idempotencia. Después, el recorrido completo a mano contra el backend real: registro sin credenciales, el pendiente entrando y viendo su estado, el 403 en la pantalla, el administrador aprobándolo, la persona entrando ya como propietario **con su propia contraseña**, y el 422 al intentar desaprobarla.

  **Un hueco de la convención de dominios, encontrado de paso.** El limpiador de usuarios de prueba no reconoció el que creó esta verificación: comparaba con `@ejemplo.com` exacto y el email era `@ejemplo.com.ar`, que es la grafía que hay que usar cuando el esquema valida el email, porque `email-validator` rechaza los dominios de uso reservado. **El limpiador se portó bien** —no borró lo que no encajaba, lo reportó, que es exactamente para lo que se endureció en `F1-T16`— pero dos grafías para una sola convención es una convención que no se puede aplicar mecánicamente, que era el punto de tenerla. Ahora el criterio es que el dominio **empiece** con `ejemplo.`, y quedó corregido en el README.

  **Dos cosas más que aparecieron y arreglé:** había **dos procesos de uvicorn** peleando por el puerto 8000 —uno con el intérprete del venv y otro con el Python del sistema—, así que quedó uno solo y con `--reload`, que es lo que hacía falta para que el endpoint nuevo apareciera sin reiniciar a mano. Y un script mío de verificación, por un escape mal escrito, **truncó `app/schemas/usuario.py` a cero bytes**; lo recuperé del último commit y volví a aplicar la edición, con la suite en verde como comprobación. Es el argumento más concreto a favor de commitear seguido.

  **Aprobada el 2026-11-07**, junto con `F1-T16B`: las revisó a las dos de una vez desde el navegador, que era la única forma de ver esta funcionando — no tiene pantalla propia.

- [x] **F1-T16B · Frontend — registro desde el login y aprobación de pendientes.**
  **Qué se construye:** dos mitades. En `index.html`, un botón de "Crear cuenta" que abre el formulario de registro — sin selector de rol, porque el rol no es del que se registra. Y en `usuarios.html`, la lista de los pendientes con la acción de asignarles el rol.

  **Quién aprueba, y acá hay una restricción heredada.** Lo natural sería que aprobaran el Administrador General **y** el Administrador de Consorcio — el Encargado no, eso está claro —. Pero el de consorcio **todavía no puede**, por la misma razón anotada en `F1-T08`: no hay forma de limitarlo a *su* consorcio hasta que existan `Edificio` y `Departamento` (`F1-T18`, `F1-T19`), y darle hoy la pantalla no es dárselo a medias, es que vea y apruebe los usuarios de **todos** los consorcios de la plataforma, incluidos los administradores de los otros. Así que el aprobador es `admin_general`, y se amplía a `admin_consorcio` en la misma tarea donde se resuelve el alcance. El atajo `SoloAdministradores` ya existe esperando eso.

  **Decisión de pantalla:** los pendientes van **en `usuarios.html`**, no en una pantalla nueva. Son usuarios; separarlos duplicaría el listado, el buscador y las acciones.

  **Qué ve el pendiente cuando entra:** su cuenta funciona, no tiene ninguna pantalla, y el mensaje que lee tiene que decir **que está esperando aprobación** — no el "todavía no hay pantallas habilitadas para tu rol" genérico, que es verdadero pero no explica nada ni dice qué hacer.

  **Reutiliza, no reinventa:** el modal de formulario de `F1-T13`, el modal de confirmación de `F1-T15` para el rechazo, y la pintura optimista con reversión de `F1-T14`. Y el rechazo **desactiva, no borra**, como todo en este sistema.

  **Listo cuando:** se puede registrar una cuenta desde el login, el administrador la ve en los pendientes, le asigna el rol, y la persona entra y ve lo que le corresponde — todo sin tocar la base de datos en ningún paso.

  **Cómo quedó.** `index.html` pasó a tener **tres tarjetas** excluyentes —login, registro y sesión-sin-destino— y una sola función decide cuál se ve. El registro no tiene campo de rol, ni visible ni oculto. Al crear la cuenta se vuelve al login con el email ya puesto y el mensaje del backend arriba; ese texto no se escribe en el frontend, porque es el mismo para un email nuevo que para uno repetido y esa indistinguibilidad es una defensa de `F1-T16A` que redactarlo acá sería la forma más fácil de arruinar sin darse cuenta.

  En `usuarios.html`, el bloque de pendientes va **arriba del listado**, con contador, la fecha en que se registraron y dos acciones. **Aprobar es el PATCH que ya existía** —no hay endpoint, permiso ni modal nuevo: es la edición de siempre, en un modo que el modal deduce del rol que tiene cargado en vez de guardarlo en una variable aparte que pueda quedar en desacuerdo—. **Rechazar desactiva**, con el mismo endpoint que el botón de estado, y la fila baja al listado de abajo marcada como inactiva; si se la reactiva, vuelve a la cola para decidir, que es lo correcto.

  **Un agujero que no era de esta tarea y había que tapar igual.** El `<select>` de rol arrancaba en la primera opción, y la matriz está ordenada de más permisos a menos: **enviar el formulario de alta sin tocar el rol creaba un Administrador General.** En el alta ya era un riesgo tonto; con la aprobación de pendientes pasaba a ser el camino más probable de todos, porque se aprueba de a varios y el campo que no se toca es justo el que importa. Ahora la primera opción no es un rol ("Elegí un rol…", con valor vacío) y está seleccionada por defecto, así que hay que elegirlo a mano en el alta y en la aprobación. Esto **cambia el comportamiento de `F1-T13`** y quedó anotado en el Documento Técnico 4.4 y en el de Frontend.

  **Un endpoint nuevo, chico y público:** `GET /api/auth/politica-password`. El formulario de registro necesita los requisitos de la contraseña y lo usa, por definición, alguien que todavía no tiene cuenta, así que `/usuarios/opciones` no servía — pide sesión de administrador porque además entrega el catálogo de roles. Las alternativas eran escribir los requisitos en el HTML (la política en dos lugares, que es exactamente lo que `textos_de_requisitos()` existe para evitar) o no mostrar nada y dejar que se entere por el 422 (adivinar la contraseña sin tener a quién preguntarle). Es seguro que sea público: no revela nada que el 422 no diga ya, solo lo dice antes. Y al escribirlo aparecieron **las mismas tres líneas duplicadas** en los dos endpoints, así que la lectura se centralizó en `PoliticaDePassword.vigente()`.

  **Dos desajustes entre la documentación y el código, encontrados al tocarlos:**

  1. **`.boton-chico` estaba especificado en el Documento de Frontend y en la skill de diseño, y no existía en el CSS.** Se escribió ahora, con el primer caso real que lo necesitaba. Y la forma que estaba documentada —una clase suelta— era la equivocada: corresponde que sea un **modificador** de `.boton-primario`, igual que `.boton-secundario`, para heredar el degradé, la sombra y el hover en vez de copiarlos. La referencia de la skill quedó corregida. Su variante `-critico` sigue especificada y sin escribir, también a propósito: el rojo le corresponde al botón del modal de confirmación, no a una fila que no tiene nada mal — una lista con un botón rojo por solicitud pinta de alarma algo donde no pasó nada.
  2. **Un `:focus-visible` propio que empeoraba el anillo global.** Mi primera versión del enlace lo sobreescribía con `--accent-ring`, que es más tenue que el `--accent` de la regla global: o sea, debilitaba lo único que hace usable ese control sin mouse. Quedó solo el radio.

  **Por qué la fila de un pendiente usa el acento y no el naranja.** Porque el semáforo de 4 estados es una regla de negocio sobre el estado del **edificio**, y `--pend` significa "mantenimiento en curso", no "pendiente" en general. Una cuenta sin aprobar no es un estado del edificio; pintarla de naranja la pondría en la misma familia visual que una unidad con una orden de trabajo abierta. El acento vive deliberadamente fuera del semáforo. Y el borde es de los **cuatro lados** más sombra del mismo color, nunca el `border-left: 3px` que el sistema de diseño prohíbe.

  **Cómo se verificó:** **385 tests** en verde (3 nuevos, sobre el endpoint de la política: que no pida sesión, que diga exactamente lo mismo que el de administrador, y que un rechazo real nombre uno de los requisitos publicados — que es lo único que garantiza que la ayuda y el error no sean dos redacciones distintas de la misma regla). Después, **26 comprobaciones contra el backend real**, en el orden en que las hace el navegador: la política sin token, dos registros, el pendiente entrando y recibiendo 403 en la pantalla, el administrador viéndolos con su fecha, la aprobación devolviendo el rol y la etiqueta para el aviso, la persona entrando ya con rol **y con su propia contraseña**, un rol vacío dando 422, el rechazo desactivando sin borrar, el rechazado sin poder entrar, la reactivación devolviéndolo a la cola, y el pendiente sin poder ascenderse a sí mismo.

  **Y una verificación nueva, que vale para todas las pantallas que vienen.** Lo que no se puede probar sin navegador es si el JavaScript y el HTML hablan del mismo DOM: un `getElementById()` con un id que no existe devuelve `null` sin avisar, y la pantalla deja de funcionar tres líneas después. Escribí un chequeo que compara los dos lados —cada id y cada atributo `data-` que el JS busca contra lo que el HTML declara, y cada clase que el JS escribe contra las reglas de `components.css`— y da 0 faltantes en las dos pantallas. **No reemplaza abrir el navegador**, pero cubre la clase de error que más veces me hizo perder tiempo, y es barato al lado de montar jsdom (que sigue siendo la deuda anotada en `F1-T16`).

  **Lo que rompí yo, otra vez por un escape.** El script que escribió ese chequeo convirtió un `\b` en un carácter de retroceso real, así que el patrón nunca podía coincidir con nada y el verificador reportaba dos faltantes que no existían. Es **el mismo tipo de error** que en `F1-T16A` truncó `app/schemas/usuario.py` a cero bytes: una secuencia de escape interpretada por el intérprete que escribe el archivo en vez de quedar literal. La conclusión práctica: en un script que genera código, las expresiones regulares y los saltos de línea van en cadenas crudas o directamente no van.

  **Aprobada el 2026-11-07.** La probó en el navegador con las cuentas de prueba que dejé cargadas (`carla.t16b@` y `diego.t16b@` pendientes, `bruno.t16b@` ya aprobada como Propietario, todas con `Registro123!`): registró una cuenta, aprobó una pendiente y rechazó la otra. Quedan en la base de desarrollo hasta que corra el limpiador de usuarios de prueba.

  **Con esto cierra el Tema 1.4 completo**, que era lo que faltaba de usuarios. La única tarea del tema que sigue abierta es `F1-T08`, y es a propósito: le falta el **alcance**, que no se puede hacer hasta que existan `Edificio` (`F1-T17`/`F1-T18`) y `Departamento` (`F1-T19`). No es trabajo pendiente de usuarios, es una pieza que depende del tema siguiente.

  **Y una corrección sobre cómo informo.** Al cerrar esta tarea me marcó que mis informes se volvieron confusos: usé palabras mías —"arnés", "mutante"— sin explicarlas, mezclé en la misma lista los fallos de mis propios scripts de verificación con el estado del producto, y nombré usuarios de prueba (Bruno, Carla, Diego) como si él supiera de dónde salieron. Lo anoté como regla de trabajo: **primero qué puede hacer él ahora, después qué cambió, y nada de vocabulario interno.** Si una verificación mía falla, eso no se cuenta junto con el resultado de la tarea.

> **Por qué estas dos tareas son `F1-T16A` y `F1-T16B` y no `F1-T17` y `F1-T18`.** Corresponden al Tema 1.4, así que van acá y no al final de la fase. Renumerar de `F1-T17` en adelante para insertarlas en orden invalidaría las referencias cruzadas que ya existen en este archivo y en los documentos Técnico y de Frontend — docenas de menciones a tareas por número —, y una referencia que apunta a la tarea equivocada es peor que una numeración con un sufijo.

## Tema 1.5 — Estructura del edificio

- [x] **F1-T17 · Lógica — generación automática de estructura y atajos de coeficiente.**
  **Qué se construye:** en `services/finanzas.py`, la regla de generación de la estructura vacía a partir de cantidad de pisos y unidades por piso, y los dos atajos para completar coeficientes por primera vez: **partes iguales** y **por m²**.
  **Regla que queda fijada:** el coeficiente es **el dato, no el criterio**. Cada unidad tiene un porcentual fijo registrado en el reglamento de propiedad horizontal y los de un edificio suman 100%. "Partes iguales" y "por m²" no son criterios de prorrateo: son atajos para completar el campo la primera vez, editable después unidad por unidad. Fundamento normativo completo en `investigaciones/Prorrateo.md`.
  **Cuidado con la precisión:** `Departamento.coeficiente` se guarda como `Numeric(6,3)` — **tres decimales**. Redondear a más decimales que los que la columna guarda hace que la suma deje de dar 100% al persistir. Es un error real, detectado en un edificio de 28 unidades donde daba 99,989%. La precisión es una constante del servicio, no un número mágico repetido.
  **Listo cuando:** hay tests de los dos atajos, del redondeo a 3 decimales y del caso de 28 unidades que reproduce el error histórico.
  **Aprobada el 2026-11-08.** Quedó `services/finanzas.py` con `generar_estructura()`, `calcular_partes_iguales()`, `calcular_por_metros_cuadrados()` y `validar_coeficientes()`, más 56 tests en `tests/test_servicio_finanzas.py` (suite completa: 441). La primera pantalla que la usa es `F1-T27`.
  **Dos decisiones que tomé acá y aprobó:** el reparto cuenta pasos enteros de 0,001 en vez de dividir decimales, así la suma da 100% por construcción y no por tener el redondeo bien calibrado; y el sobrante de los pasos **se reparte entre varias unidades en vez de apilarse en la última**, porque un coeficiente es permanente y dejar a un propietario 0,012 puntos arriba de sus vecinos se lo cobra todos los meses. En el prorrateo de un monto (Fase 2) se sigue haciendo al revés, y está bien: el resto de un monto es de un mes. Las dos están escritas en `investigaciones/Prorrateo.md`, sección 9.

- [x] **F1-T18 · Backend — modelo `Edificio`.**
  **Qué se construye:** `id`, `nombre`, `direccion`, `cp`, `cuit`, `latitud`, `longitud`, **`admin_consorcio_id`**, **`encargado_id`**, `dias_vencimiento_expensas`, `recargo_mora_porcentual`, `contacto_emergencia_nombre`, `contacto_emergencia_telefono`, `roles_habilitados`, `cbu`, `alias_cbu`, `activo`, `creado_en`.
  **Cuidado con `encargado_id`:** en la iteración anterior **faltaba**. El rol Encargado existía con alcance de edificio desde el primer día pero no había nada que lo vinculara a un edificio concreto, lo que hacía imposible resolver "los reclamos que este encargado puede gestionar". Se detectó recién en la Fase 3. **Un rol con alcance de edificio necesita su vínculo desde el modelo, no después.**
  **Por qué CP y no ciudad:** es más preciso para geocodificar y suficiente para lo que usa la plataforma.
  **Pendiente que me deja `F1-T03`:** `asignacion_edificio.edificio_id` quedó como entero sin clave foránea, porque cuando creé esa tabla `edificios` todavía no existía y una FK contra una tabla ausente hace fallar la creación del esquema entero al arrancar. Acá se formaliza. **No es una migración:** la tabla está vacía durante toda la ventana —lo primero que escribe una asignación es la pantalla de `F11-T05`—, así que alcanza con borrarla y dejar que se vuelva a crear con la FK declarada. Esto no es la deuda de claves foráneas de la sección 4: esas quedaron sin FK con datos ya cargados encima, y eso sí necesita una migración escrita a mano.
  **Aprobada el 2026-11-08.** Quedó `models/edificio.py` con las 18 columnas, las dos relaciones a `usuarios` y seis CHECK; `models/__init__.py` y `tests/conftest.py` actualizados con la tabla nueva; 43 tests en `tests/test_edificio.py`. El alta por API es `F1-T20`.
  **La migración que hay que correr una vez por base:** `m002_fk_asignacion_edificio` borra y recrea `asignacion_edificio` con la clave foránea declarada, y **se niega a hacerlo si la tabla tiene filas**. Corrida contra la base de desarrollo; **falta contra Supabase**, y está anotada en el README junto a `m001`. Se puede correr antes o después de desplegar: la propia migración crea `edificios` si todavía no existe.
  **Dos decisiones que tomé acá y aprobó:** `roles_habilitados` es una columna `JSON` cuya lista válida es `autorizacion.ROLES_HABILITABLES` —una tercera lista de roles que agregué a la matriz, los asignables menos `admin_general`, porque su alcance es la cartera entera y no se habilita por edificio— y un edificio nuevo nace con **todos** habilitados, no con ninguno; y `cuit` quedó **sin restricción de unicidad**, porque un mismo consorcio puede administrar dos torres cargadas como dos edificios. El detalle de tipos está en `02_Documento_Tecnico.md`, sección 3.1.

- [x] **F1-T19 · Backend — modelos `Piso`, `Departamento`, `Cochera`, `EspacioComun`.**
  **Qué se construye:** `Piso` (edificio, número, orden de apilado); `Departamento` (piso, identificador, m², `propietario_id`, `inquilino_id`, `ocupado`, `coeficiente` `Numeric(6,3)`); `Cochera` (edificio, número, tipo fija/rotativa con CHECK, departamento opcional); `EspacioComun` (edificio, nombre, capacidad, reglas de uso).
  **Regla:** el estado ocupacional del departamento **no se carga a mano**: se deriva de si tiene propietario o inquilino asignado.
  **Regla de estructura:** un propietario puede tener varias unidades, incluso en edificios distintos; **un inquilino tiene una sola**. Esto simplifica toda la interfaz del residente: donde el propietario a veces necesita elegir de cuál de sus unidades habla, el inquilino nunca.
  **Aprobada el 2026-11-08.** Las cuatro tablas quedaron en `models/edificio.py`, que es el archivo del dominio del edificio (igual que `Usuario` y `AsignacionEdificio` comparten `usuario.py`). 49 tests en `tests/test_estructura.py`, suite completa: 533. No hay endpoint todavía: el alta con estructura automática es `F1-T20`.
  **Las dos reglas del enunciado, resueltas por la base y no por código:** "un inquilino, una sola unidad" es una restricción de unicidad sobre `inquilino_id` —anulable, así que no obliga a que toda unidad tenga inquilino, solo impide que la misma persona figure en dos—; y `ocupado` **no es una columna**: es una `hybrid_property` que devuelve "hay propietario o hay inquilino", así que no se puede cargar a mano ni quedar desactualizada, y además filtra en SQL.
  **Tres decisiones que tomé acá y aprobó:** la cochera cuelga del **edificio** y no del piso (está en un subsuelo que no es un piso de departamentos) y su `numero` es texto, porque el rótulo real dice "S2-14" tan seguido como dice "12"; y las relaciones del edificio a su estructura **no llevan borrado en cascada**, así que intentar borrar un piso con departamentos falla ruidosamente en vez de arrastrarse las unidades y su historial.
  **Una limitación que dejo anotada:** `Departamento` no tiene columna de orden, porque el enunciado no le declara una, así que las unidades de un piso se ordenan por `identificador`. Con más de 26 unidades en un mismo piso eso pone "1AA" antes de "1B". Con 26 o menos —todos los casos reales— el orden es el correcto. Si aparece un piso así, la columna se agrega sin migración: es el caso aditivo que `core/migraciones.py` resuelve solo.

- [x] **F1-T20 · Backend — alta de edificio con estructura automática.**
  **Qué se construye:** `POST /api/edificios` (solo Administrador General): crea el edificio y, en la **misma transacción**, sus pisos y departamentos vacíos según la cantidad indicada.
  **Cuidado con:** si algo falla a mitad de camino se hace rollback y no queda nada a medio crear.
  **Aprobada el 2026-11-08.** `schemas/edificio.py`, `routers/edificios.py` y el router montado en `main.py`. 42 tests en `tests/test_edificios.py`, suite completa: 575. Se prueba desde `/docs`: `POST /api/edificios` con `nombre`, `direccion`, `cp`, `cantidad_pisos` y `unidades_por_piso`. Lo probé también contra el servidor real: un edificio de 3 pisos por 2 unidades devolvió los seis identificadores (`1A`, `1B`, `2A`, `2B`, `3A`, `3B`) y después borré esa fila para no dejarte basura en la base de desarrollo.
  **Cómo quedó la atomicidad, que es lo que da sentido a la tarea.** No se guarda de a tandas: se arma el grafo completo en memoria —el edificio con sus pisos, y cada piso con sus departamentos— y se hace **un solo** `commit`, dejando que SQLAlchemy resuelva el orden de los INSERT por las relaciones. Hay un test que lo verifica provocando la falla a propósito: fuerza una estructura con dos unidades del mismo identificador, y comprueba que no queda ni el edificio. Si el alta no fuera una sola transacción, quedaría un edificio sin estructura y la persona —que vio un error— lo cargaría de nuevo y tendría dos.
  **Qué pide el alta y qué no, a propósito.** Pide identidad y ubicación (`nombre`, `direccion`, `cp`, `cuit` opcional, coordenadas opcionales) más los dos números de tamaño. **No** pide responsables, vencimientos, mora, CBU ni roles habilitados: eso es `F1-T22`, nace con su valor por defecto, y un formulario de alta de dieciocho campos es un formulario que nadie completa. Los dos números de tamaño **no se guardan en ninguna columna**: son los argumentos de `generar_estructura()`, y "cuántos pisos tiene" se responde contando pisos — un número guardado aparte dejaría de coincidir en cuanto `F1-T23` agregue uno.
  **Y una decisión que conviene tener a la vista:** los topes de tamaño los valida el esquema de entrada **contra las constantes de `services/finanzas.py`**, no contra números escritos de nuevo. Así el error es un 422 que explica el límite en vez de un 500 por un `ValueError` que se escapó del servicio, y el día que se suba el tope no quedan dos lugares que lo digan distinto.
  **Topes bajados dos veces, las dos a pedido mío: a 40 y 15 el 2026-11-09, y a 20 pisos y 10 unidades por piso el 2026-11-12** (eran 60 y 40). El motivo es el mismo las dos veces: un tope holgado no ataja el error que tiene que atajar — con 40 unidades por piso permitidas, escribir 14 en vez de 4 generaba 140 unidades sin que nada avisara. Se cambió la constante en un solo lugar y el esquema, el servicio y el mensaje del 422 quedaron alineados solos, que es justamente para lo que estaba centralizada.
  **Los dos valores son el tope de la generación automática, no un límite del dominio.** Un edificio más grande se carga igual: se genera hasta el tope y se agregan los pisos o las unidades que falten de a uno con el CRUD de `F1-T23`. La carga masiva queda anotada como pedido para más adelante.
  **Una consecuencia del segundo tope, anotada para que no sorprenda:** con 15 unidades por piso como máximo, la numeración nunca pasa de la letra O, así que la continuación `1AA`, `1AB` de `_letra()` **dejó de ser alcanzable desde la API**. El código se deja —es correcto y tiene que seguir funcionando el día que el tope se suba— pero su test ya no puede generar un piso de 28 unidades, así que ahora prueba el nombrador directamente. Y quedó un test nuevo que falla si alguien sube el tope por encima de 26, para avisar que esa numeración vuelve a ser real y hay que revisar las pantallas que muestran identificadores, no solo la constante.

- [x] **F1-T21 · Backend — listado y detalle de edificios, sin N+1.**
  **Qué se construye:** `GET /api/edificios` (listado) y `GET /api/edificios/{id}` (detalle).
  **Se construye bien desde el principio, no se optimiza después:** el listado usa un esquema de **resumen** con un `COUNT` agregado y **nunca** trae pisos y departamentos completos; el detalle usa `selectinload`, quedando fijo en 2 consultas extra sin importar cuántos pisos tenga el edificio.
  **Por qué:** en la iteración anterior el listado disparaba 29 consultas para 7 edificios de prueba y el detalle 6 para un edificio de 3 pisos — imperceptible en SQLite local (2-12 ms), pero ~1,5 segundos contra Supabase, porque cada consulta extra paga el costo de red real.
  **Listo cuando:** hay tests que **cuentan las consultas SQL disparadas** (no tiempos, poco confiables en CI) y confirman que quedan fijas sin importar cuántos edificios, pisos o departamentos haya.
  **Aprobada el 2026-11-08.** Los dos endpoints en `routers/edificios.py` y los esquemas de lectura en `schemas/edificio.py`. 43 tests nuevos en `tests/test_edificios_lectura.py`, suite completa: 618. Se prueba desde `/docs`: `GET /api/edificios` y `GET /api/edificios/{id}`.
  **Las consultas quedaron contadas, no estimadas.** El listado dispara **una sola** consulta: no devuelve ninguna colección —así que no hay nada que Pydantic pueda leer y disparar una consulta por edificio— y los dos números que muestra la pantalla los cuenta la base con subconsultas correlacionadas. Verificado con 1 edificio, con 7 (los mismos 7 que en la iteración anterior costaban 29 consultas) y con uno de 20 pisos por 8 unidades: una, siempre. El detalle dispara **cinco fijas** —el edificio y una por colección, con `selectinload`—, iguales para un edificio de 3 pisos y para uno de 20 pisos con 160 unidades.
  **Una corrección al número que anoté acá.** Esta tarea decía "2 consultas extra" en el detalle, contando pisos y departamentos. El detalle también trae cocheras y espacios comunes, así que son 4 extra: 5 en total. Lo que importa es que el número sea **fijo**, y lo es; dejo el número real escrito para que el día que alguien cuente no parezca que algo se rompió.
  **El contador de consultas está probado a sí mismo.** Un contador que no registre nada, o que filtre mal, haría pasar los cinco tests de rendimiento sin verificar absolutamente nada. Así que hay un test que provoca a mano el N+1 que los endpoints evitan —traer los edificios y pedirle los pisos a cada uno— y verifica que el contador lo ve: 1 + 3 consultas para tres edificios.
  **Y una decisión de alcance que quiero que mires, porque no estaba escrita en la tarea.** El listado no podía devolverle la cartera entera a cualquier administrador: el Administrador General ve todo —es quien da de alta los edificios—, y el Administrador de Consorcio ve solo los edificios donde figura como tal, por la columna `admin_consorcio_id` que ya existe. El filtro va en el `WHERE` y no en la pantalla, porque un filtro que vive en el frontend no es un permiso. Y un edificio fuera del alcance responde **igual** que uno inexistente, para no ir contando qué edificios hay probando ids. Los demás roles no entran a estos dos endpoints todavía: el residente ve su edificio por el dashboard de `F3`, que es otro endpoint con otras reglas.

- [x] **F1-T22 · Backend — configuración del edificio.**
  **Qué se construye:** `PATCH /api/edificios/{id}` con responsables (validando que `admin_consorcio_id` apunte a un usuario con ese rol real, ídem `encargado_id`), contacto de emergencia, días de vencimiento, recargo por mora, **CBU y alias** de la cuenta del consorcio, y roles habilitados para ese edificio.
  **Aprobada el 2026-11-08.** `EdificioConfigurar` en `schemas/edificio.py` y el `PATCH` en `routers/edificios.py`. 54 tests nuevos en `tests/test_edificios_configuracion.py`, suite completa: 672. Se prueba desde `/docs`.
  **Es un PATCH de verdad, y eso es lo que hace que la pantalla pueda guardar por bloques.** Un campo que no viaja no se toca; uno que viaja en `null` se vacía. La diferencia la resuelve `model_fields_set` de Pydantic y no un valor centinela, que es lo que permite **borrar** el teléfono de emergencia: con una cadena vacía como centinela, "borralo" sería indistinguible de "no lo toques". Los campos que la columna declara NOT NULL no se pueden vaciar, y eso lo rechaza el esquema con un 422 antes de llegar a la base.
  **Los responsables se validan contra la matriz de roles**, que es lo que la tarea pide: el usuario tiene que existir, estar activo y tener ese rol. Los tres motivos de rechazo dan mensajes distintos a propósito, porque quien configura es un administrador eligiendo entre usuarios que él mismo dio de alta, y "esa persona está desactivada" le ahorra adivinar.
  **El permiso está partido en dos y quiero que lo mires.** Quién administra el edificio lo decide **solo el Administrador General**: si un Administrador de Consorcio pudiera tocar esos dos campos, podría sacarse a sí mismo —perdiendo el acceso al edificio sin forma de recuperarlo— o asignarse un edificio ajeno. Todo el resto —cobranza, contacto de emergencia, roles habilitados— lo configura el Administrador de Consorcio sobre su propio edificio, porque pedirle al Administrador General que cargue el CBU de cada consorcio sería convertir un dato operativo en un trámite.
  **Lo que validé de la cobranza, y lo que deliberadamente no.** Al CBU se le sacan espacios y guiones antes de medirlo —se copia y se pega de un resumen bancario, casi siempre en bloques— y se exigen 22 dígitos exactos, que ataja el error de tipeo que corta un dígito; **el dígito verificador no se valida**, igual que el del CUIT. El alias se mide contra los límites reales del alias bancario argentino. Y el recargo por mora **rechaza más de dos decimales en vez de redondearlos en silencio**: la columna es `Numeric(5,2)`, así que un 1,555 se guardaría como 1,56 y quien lo escribió nunca se enteraría de que el recargo que se cobra no es el que puso.
  **Una cosa que descubrí construyendo esto y dejo anotada.** El CHECK `ck_edificios_responsables_distintos` es **inalcanzable** desde la API: un usuario tiene un solo rol y cada puesto exige el suyo, así que la misma persona nunca puede quedar en los dos. Lo frena antes la validación de rol, con un mensaje más útil. Dejé igual el chequeo en el endpoint, como respaldo del CHECK, y lo escribí donde está para que no parezca la defensa principal.

- [x] **F1-T23 · Backend — CRUD anidado de la estructura.**
  **Qué se construye:** alta, edición y baja de pisos, departamentos, cocheras y espacios comunes bajo `/api/edificios/{id}/...`, más la asignación y desvinculación de propietario o inquilino a un departamento existente.
  **Cuidado con:** el listado de espacios comunes **no puede ser admin-only**. En la iteración anterior lo fue por error y bloqueó sin querer a Propietario, Inquilino y Encargado, que sí lo necesitan para reportar un reclamo sobre un espacio común (se descubrió recién en la Fase 3). Crear un espacio común sí es exclusivo del administrador; verlo, no.
  **Aprobada el 2026-11-09.** Trece endpoints en `routers/estructura.py`, los esquemas de entrada en `schemas/estructura.py` y el alcance en `core/alcance.py` (archivo nuevo). 90 tests nuevos —70 en `tests/test_estructura_api.py` y 20 en `tests/test_alcance.py`—, suite completa: 762. Se prueba desde `/docs`, bajo la etiqueta "Estructura del edificio".
  **El error de la iteración anterior, resuelto y con un test por rol.** `GET /api/edificios/{id}/espacios-comunes` no es admin-only: lo ve cualquiera que tenga algo que hacer en el edificio, y eso lo decide `core/alcance.puede_ver()` — lo administra, trabaja ahí, vive ahí (tiene una unidad como propietario o inquilino) o lo tiene asignado en `asignacion_edificio`. **Crear**, editar y borrar siguen siendo exclusivos del administrador, y hay un test que verifica las dos mitades de la frase: que el encargado, el propietario, el inquilino y el agente de seguridad lo vean, y que ninguno de los cuatro pueda crear uno.
  **Nació `core/alcance.py`, y es la deuda de `F1-T08` que quedaba abierta.** La matriz de `services/autorizacion.py` responde **qué puede hacer un rol**; faltaba la otra mitad, **sobre qué edificios**, que no se puede responder sin consultar la base. Esta es la primera tarea que la necesita de verdad, porque es la primera con un endpoint que no es admin-only. Dejé el alcance del Proveedor explícitamente afuera: su alcance en la matriz es `ots_asignadas`, así que llega a un edificio por una orden de trabajo, y ese permiso sale de la orden cuando exista (Fase 5).
  **Todo está anidado bajo el edificio porque eso ES el permiso.** El orden en los trece endpoints es el mismo: buscar el edificio dentro del alcance de quien pide, buscar la fila hija dentro de ese edificio, validar la regla, guardar. Pedir el piso de un edificio ajeno pasando el id del propio da 404, y hay un test de eso para cada una de las cuatro entidades — es el agujero que no se ve leyendo un endpoint, sino comparándolo con los otros doce.
  **Dos decisiones que quiero que mires.** La primera: la asignación y desvinculación de propietario o inquilino va en el **PATCH del departamento** (`null` desvincula) y no en cuatro endpoints propios, porque la operación es la misma —cambiar una columna de la unidad— y partirla obligaría a la pantalla a elegir a cuál de cuatro URLs pegarle según qué tocó el usuario. La segunda: asignar un residente exige que **ese rol esté habilitado en ese edificio**, que es lo que le da sentido a `roles_habilitados` de `F1-T22` — sin eso, la columna no tendría ningún efecto. Desvincular funciona siempre, igual: si no, deshabilitar un rol dejaría a esas personas pegadas a sus unidades para siempre.
  **Y una limitación a la vista:** los pisos y las unidades se agregan de a uno. No hay alta masiva ("agregame 4 unidades a este piso") porque el alta masiva ya existe y es el alta del edificio (`F1-T20`); esto es para corregir y completar. Si al usar la pantalla de `F1-T25` resulta incómodo, se agrega.

- [x] **F1-T24 · Backend — carga de coeficientes.**
  **Qué se construye:** `PATCH` de coeficiente unidad por unidad (carga manual, la que refleja el reglamento real) y un endpoint que aplica los atajos de `F1-T17` a todo el edificio de una vez.
  **Cuidado con:** en la iteración anterior esto quedó pendiente **en silencio** — nunca existió endpoint para cargar el coeficiente, solo se podía a mano en la base, y se descubrió recién al intentar generar una expensa ("Hay departamentos sin coeficiente cargado"). Sin coeficientes cargados no hay expensa posible: esta tarea es prerrequisito real de toda la Fase 2.
  **Aprobada el 2026-11-09.** Tres endpoints en `routers/coeficientes.py` y los esquemas en `schemas/coeficientes.py`. 38 tests nuevos en `tests/test_coeficientes.py`, suite completa: 800. Se prueba desde `/docs`, bajo la etiqueta "Coeficientes".
  **Lo que hice para que esto no vuelva a quedar pendiente en silencio:** las tres respuestas traen el estado completo del edificio — la suma, si es 100%, cuántas unidades faltan y los identificadores de las primeras cinco. No hace falta pedir nada aparte para saber si el edificio puede emitir una expensa, y el mensaje dice "Faltan 3 unidades sin coeficiente: 1A, 1B, 2C" en vez de "hay departamentos sin coeficiente". Con 40 unidades sin cargar no las nombra todas: dice las primeras cinco y "y 35 más".
  **La suma no se bloquea mientras se carga, se informa.** Cargar treinta coeficientes a mano pasa por estados donde la suma no es 100 —con el primero cargado suma 3,5—, y rechazarlos obligaría a cargar todo en un solo pedido o a bajar uno antes de poder subir otro. La suma exacta la impone la generación de la expensa, que es donde importa.
  **El atajo se niega a pisar lo cargado a mano, y devuelve 409.** Los coeficientes salen del reglamento de propiedad horizontal: no se calculan, se copian, así que pisarlos con un cálculo automático es destruir el dato verdadero y dejar uno plausible. El 409 es el código de "necesito que confirmes" en este proyecto —`api.js` lo convierte en `error.necesitaConfirmacion`— y este es el único lugar de la Fase 1 donde corresponde. Con `sobrescribir: true` reemplaza todo.
  **Las cuentas siguen siendo del servicio, no del endpoint.** `services/finanzas.py` reparte 100.000 pasos de 0,001 por resto mayor, así que la suma da 100,000% por construcción. Verificado con el caso histórico: 28 unidades, que daba 99,989%, ahora da 100,000% y los coeficientes quedan en 3,571 y 3,572 — el sobrante repartido, no apilado en la última. El endpoint solo ordena las unidades (posición del piso, después identificador) y guarda, en una sola transacción. Hay un test de que aplicarlo dos veces da exactamente lo mismo: si el orden no fuera estable, dos llamadas darían coeficientes distintos y nadie entendería por qué cambió su expensa.
  **Dos cosas que agregué y una que dejé afuera.** Agregué el `GET /coeficientes` —no estaba pedido, pero es la pantalla de carga y el lugar donde se ve el estado— y acepté el **0** como coeficiente válido, porque una unidad puede estar exenta (el departamento del encargado suele estarlo) y eso es un cero cargado a propósito, no un dato faltante. Lo que dejé afuera: el coeficiente **no** entra por el PATCH de la estructura, y hay un test de que da 422 — separado, el permiso y la validación se leen de un vistazo, y corregir los metros cuadrados nunca puede tocar un coeficiente por accidente.

## Tema 1.6 — Pantalla de edificios

- [x] **F1-T25 · Frontend — `edificios.html`, listado y alta con geocodificación.**
  **Qué se construye:** listado (mismo patrón que usuarios) y alta en modal con `assets/js/mapa.js`: al completar dirección y CP se geocodifica con Nominatim (OpenStreetMap, sin API key ni facturación) y se muestra el resultado en un mapa Leaflet dentro del propio formulario.
  **Regla:** si la dirección no se encuentra **se avisa pero no se bloquea el alta** — una dirección nueva puede no estar indexada todavía y no tiene sentido impedir cargar un edificio real por eso.
  **Cuidado con:** el listado es imprescindible, no un extra. En la iteración anterior `edificios.html` tenía solo el formulario de alta y **no había forma de llegar a un edificio ya creado**.
  **Aprobada el 2026-11-12.** `edificios.html`, `assets/js/edificios.js` y `assets/js/mapa.js` (archivo nuevo), más las tres clases del mapa en `components.css` y el acceso "Edificios" en la tabla de `layout.js`. Se prueba en `http://127.0.0.1:8090/edificios.html`, con el backend levantado en 8000.
  **El error de la iteración anterior, resuelto.** El listado es lo primero que se ve y trae lo que hace falta para reconocer un edificio sin abrirlo: nombre, dirección, CP, CUIT si tiene, y la cantidad de pisos y unidades. Los dos conteos los calcula la base en la misma consulta (`F1-T21`), así que el listado es **una sola consulta** haya 1 edificio o 300. Los inactivos se listan igual que los activos, atenuados: la baja de este sistema es lógica y un edificio que no aparece es un edificio que nadie puede reactivar.
  **El permiso está partido, y por eso el botón de alta no es parte del permiso de la pantalla.** El listado lo ven el Administrador General y el de Consorcio —cada uno con su alcance, que lo filtra el backend— y crear un edificio es exclusivo del Administrador General. El botón "Nuevo edificio" nace oculto y se muestra solo a quien puede crear: mostrárselo al otro sería invitarlo a un 403. Por lo mismo, el estado vacío tiene dos textos distintos, porque "no hay edificios" significa dos cosas: no creaste ninguno todavía, o no tenés ninguno asignado — y lo segundo no se resuelve apretando un botón.
  **La geocodificación avisa y no bloquea, y está escrita para que no haya forma de que bloquee.** `mapa.js` no rechaza nunca: una dirección que no se encuentra, el servicio que no contesta, el CDN de Leaflet que no carga y la falta de red son todos el mismo resultado —no hay coordenadas— y cada uno tiene su propia frase, que termina diciendo que el edificio se puede guardar igual. Es verdad: la columna de coordenadas es anulable justamente para esto. Una cosa que sí decidí: **si se corrige la dirección y la nueva no se encuentra, las coordenadas viejas se descartan.** Dejar el pin anterior guardaría la ubicación de la dirección equivocada, y un dato ausente se ve mientras uno incorrecto no.
  **La búsqueda se dispara al salir del campo, no mientras se tipea.** Nominatim es un servicio público y gratuito que pide un máximo de un pedido por segundo; buscar "A", "Av", "Av.", "Av. R"… es exactamente lo que no hay que hacer. Además, al salir del campo es cuando la dirección está completa, que es cuando el resultado sirve. Hay un botón para buscar a mano, que existe para el reintento, y dos cosas más por el mismo motivo: dos pedidos seguidos se separan 1,1 s como mínimo, y no se repite una búsqueda idéntica por entrar y salir del campo sin cambiar nada.
  **Leaflet se carga tarde y con la versión clavada.** Son unos 160 KB que el listado —que es lo que se mira casi siempre— no necesita, así que se piden la primera vez que se abre el mapa y una sola vez por página. Las dos URLs llevan `integrity`, o sea que el navegador verifica el archivo antes de ejecutarlo, y la versión está escrita (`1.9.4`) y no es "la última": si no, el día que publiquen una versión nueva cambiaría el código que corre en producción sin que nadie haya tocado el proyecto. **Si alguna vez se sube la versión hay que recalcular las dos huellas**, porque con la vieja el navegador rechaza el archivo nuevo y el mapa desaparece sin dar un error que lo explique.
  **Dos cosas que agregué.** La primera: el formulario dice **antes de guardar** cuánto se va a generar ("se van a generar 7 pisos con 28 unidades en total"), porque la estructura es la única parte del alta que crea filas que después hay que corregir de a una. La segunda: la rueda del mouse **no hace zoom** en el mapa. El mapa vive dentro de un modal con scroll propio, y con el zoom por rueda prendido alguien que baja la página con el puntero encima termina mirando Sudamérica en vez de llegar al botón de guardar; se hace zoom con los botones y, en mobile, pellizcando.
  **Y una limitación a la vista:** los topes de pisos (20) y de unidades por piso (10, ver `F1-T20`) **no están escritos en el frontend**. Salen de `services/finanzas.py` y escribirlos acá sería tener el mismo número en dos lugares, así que un 70 se manda y lo rechaza el backend con un 422 que dice el tope. Si al usarlo resulta molesto, la solución correcta es un `GET /api/edificios/opciones` que los publique —como ya hace `/usuarios/opciones` con los roles—, y eso no está en el Roadmap: lo agrego si me lo pedís.

- [x] **F1-T26 · Frontend — detalle del edificio con pestañas.**
  **Qué se construye:** selector segmentado con tres pestañas dentro del mismo archivo: **Datos** (responsables, contacto de emergencia), **Estructura** (pisos, departamentos, cocheras, espacios comunes, con alta y asignación de propietario/inquilino) y **Configuración** (vencimientos, mora, CBU y alias con botón de copiar, roles habilitados).
  **Incluye:** `assets/js/copiar.js`, con feedback inmediato — el ícono pasa a un check por 1,5 s. Si el navegador no da permiso de portapapeles, no rompe el flujo.
  **Nota de alcance:** la vista de estructura es **en lista**, no gráfica. La versión gráfica coloreada es el Dashboard Visual de la Fase 5 y no se adelanta acá ni parcialmente.
  **Aprobada el 2026-11-12.** `assets/js/edificio-detalle.js` y `assets/js/copiar.js` (archivos nuevos), la vista de detalle dentro de `edificios.html`, el ruteo en `edificios.js` y once clases nuevas en `components.css`. Del lado del backend, dos endpoints (abajo) con **33 tests** en `tests/test_edificios_opciones.py`; suite completa: **834**. Se prueba abriendo un edificio del listado con el botón "Abrir".
  **Las dos vistas viven en el mismo archivo y la URL decide cuál.** Con `?id=7` se muestra el detalle; sin nada, el listado. El id va en la URL y no en una variable de JavaScript por tres razones concretas: F5 no te saca del edificio en el que estabas, el botón de atrás del navegador vuelve al listado sin que haya que programar nada, y el enlace de un edificio se puede mandar por mensaje. Por lo mismo la fila del listado abre con un enlace de verdad y no con un botón: así funcionan el clic del medio, el "abrir en pestaña nueva" y el arrastre al marcador.
  **Desviación del orden, anotada acá como pide la sección 1.3: esta tarea agregó dos endpoints de backend, y los aprobaste antes de que los escribiera.** `GET /api/edificios/opciones` (tipos de cochera, roles habilitables y los dos topes de la estructura) y `GET /api/edificios/{id}/asignables` (los candidatos de cada puesto y de cada unidad). Sin el primero, los tres catálogos quedaban escritos a mano en el JavaScript, o sea las reglas del backend en dos lugares: el día que se agregue un tipo de cochera, la pantalla seguiría ofreciendo dos. Sin el segundo, el desplegable de personas solo se podía armar con `GET /api/usuarios`, que es **exclusivo del Administrador General**: el de Consorcio puede asignar un propietario a una unidad de su edificio (`F1-T23`) y no tenía de dónde sacar la lista, así que la pantalla terminaba pidiéndole que escribiera un número que no podía averiguar. Es la misma situación que `F1-T13` con `/usuarios/opciones`.
  **`asignables` devuelve solo lo que se puede asignar, y eso es la mitad de su valor.** Únicamente usuarios activos, con el rol que el puesto exige, y los residentes solo si ese rol está habilitado en ese edificio. Un desplegable armado así **no puede ofrecer una opción que el backend vaya a rechazar**, que es la clase de error que convierte un formulario en una adivinanza. Cuando el rol no está habilitado, la lista vuelve vacía y la pantalla lo dice con palabras: "el rol Propietario no está habilitado en este edificio, se habilita en la pestaña Configuración" — no un desplegable vacío sin explicación.
  **Un solo modal para las cuatro entidades de la estructura**, en alta y en edición: piso, unidad, cochera y espacio común. El título, la bajada y los campos los arma el JavaScript desde una descripción de campos. Cuatro modales escritos a mano serían el mismo formulario cuatro veces —ocho contando alta y edición— y el día que se agregue un campo habría que acordarse de los ocho.
  **Dos detalles que son bugs evitados, no preferencias.** El primero: si el responsable asignado tiene la cuenta desactivada, se le agrega una opción propia al desplegable ("Usuario #7, cuenta desactivada"). Sin eso el navegador ignora el valor desconocido, el desplegable muestra "Sin asignar", y guardar ese bloque por cualquier otro motivo **desvincula a esa persona sin que nadie lo haya pedido**. El segundo: los decimales viajan al backend como texto y no como número de JavaScript, porque `Number` puede llegar como `1.5500000000000002` y el esquema rechaza más de dos decimales — un error de validación imposible de entender mirando el campo.
  **El coeficiente se muestra y no se edita acá**, a propósito: es `F1-T27`, y el backend además lo rechaza por el PATCH de la unidad (422) para que corregir una superficie no pueda tocar un coeficiente por accidente.
  **Y dos limitaciones a la vista.** La primera: **no se editan los datos de identidad** del edificio —nombre, dirección, CP, CUIT— porque no hay endpoint; `PATCH /api/edificios/{id}` es de configuración. Si cargás un nombre mal, hoy se corrige en la base. La segunda: **un Administrador de Consorcio ve en `asignables` el nombre y el email de todos los propietarios e inquilinos activos del sistema**, no solo de su edificio, porque la misma persona puede ser propietaria en dos consorcios y filtrar por edificio haría imposible asignarle su unidad en el segundo. Si eso te parece demasiado, la forma de acotarlo es que el endpoint busque por email en vez de listar, y ahí el desplegable pasa a ser un campo de búsqueda.

- [x] **F1-T27 · Frontend — carga de coeficientes con indicador de suma.**
  **Qué se construye:** dentro de la pestaña Estructura, la edición de coeficiente por unidad y los dos atajos, con un **resumen en vivo de la suma** que avisa en rojo si no da 100% exacto.
  **Incluye:** `assets/js/cargando.js` (indicador con dos frases rotando y puntos animados, con un único intervalo global que recorre los indicadores presentes, así funciona también con los que se insertan al redibujar un listado).
  **Aprobada el 2026-11-12.** El bloque de coeficientes dentro de la pestaña Estructura de `edificios.html`, con su lógica en `edificio-detalle.js` y tres clases nuevas en `components.css`. `cargando.js` **ya existía** desde `F1-T13` y se reusa tal cual: no hizo falta escribirlo de nuevo.
  **El bloque va primero en la pestaña, arriba de los pisos.** Sin coeficientes cargados no se puede emitir una sola expensa, y en la iteración anterior eso se descubrió tres fases después: lo primero que se ve al entrar a la estructura de un edificio tiene que ser si está en condiciones de liquidar. La suma vive en una pill al lado del título del bloque, verde si da 100,000% exacto y roja si no, y **nunca comunica con el color solo**: el texto dice el porcentaje, porque la diferencia entre 99,999% y 100,000% no se ve en un color.
  **La suma no se calcula en el navegador, y eso es lo importante de cómo quedó.** Las tres operaciones del backend devuelven el estado completo del edificio, así que la pantalla muestra lo que el servidor calculó con `Decimal`. Sumar los valores en JavaScript daría `99.99999999999999` para un edificio que suma 100 exacto, y la pantalla diría que no se puede liquidar un edificio que sí se puede. El mensaje también es del backend: nombra las primeras unidades que faltan ("Faltan 3 unidades sin coeficiente: 1A, 1B, 2C") y escribirlo acá sería una segunda versión de la frase que valida la expensa.
  **El coeficiente salió de la fila de la unidad en la lista de pisos.** Lo había puesto en `F1-T26` y lo saqué al hacer esto: un dato que se muestra en dos lugares de la misma pantalla es un dato que en algún momento se muestra distinto en los dos, porque basta con que una de las dos listas no se redibuje después de un cambio.
  **Tres decisiones de interacción que vienen de cómo se carga esto de verdad** —veinte unidades, de a una, con Tab—. Se guarda en `change` y no en `input`: un pedido por tecla mandaría "3", "3,", "3,5", que son valores que nadie quiso guardar. Al guardar se repinta **solo** la pill y el valor de esa fila, no la lista entera, porque `innerHTML` se lleva puesto el foco y perderlo en cada guardado haría la carga inviable. Y Enter se intercepta en este bloque, porque `formularios.js` mueve el foco al campo siguiente —correcto en un formulario— y estos campos **no** están en un `<form>`: son veinte guardados independientes.
  **Vaciar el campo no borra el coeficiente, y la pantalla lo explica.** El endpoint no acepta `null`: "dejarlo sin cargar" no es una operación que exista. Si quedó cargado por error, el valor es **0**, que es una unidad exenta —el departamento del encargado suele estarlo— y es un caso real, distinto de un dato que falta.

  **Tus tres observaciones del 2026-11-11, aplicadas.**
  **1. Una sola lista, no dos.** Tenías razón y era un error claro: el bloque de coeficientes listaba todas las unidades y abajo "Pisos y unidades" las listaba otra vez, así que la misma unidad aparecía dos veces en la misma pantalla. Ahora el coeficiente se edita **en la fila de la unidad**, junto con su superficie y sus ocupantes. Lo que quedó arriba del listado no es la lista repetida: es el estado del edificio —la suma y si se puede liquidar— y los botones que se aplican a todas las unidades juntas.
  **2. El mapa en la pestaña Datos**, debajo de la ficha de identidad y arriba de los responsables. Es el mismo módulo del alta y no geocodifica nada: muestra el punto guardado. Si el edificio no tiene coordenadas no dibuja un mapa vacío, explica que la dirección no se encontró al darlo de alta y que eso no impide operar.
  **Rehecha visualmente el 2026-11-13, después de que la vieras en producción.** Tu diagnóstico fue preciso: el campo del coeficiente "no respetaba la estética", los botones de ícono "no tenían identidad" al lado de "Agregar piso", y todo el bloque de pisos era "blanco y negro, sin sombras ni detalles". Lo trabajé como mockup antes de tocar el código —dos propuestas en un canvas, revisadas en dos rondas— y la aprobada fue la **Opción A: lista con jerarquía**. Lo que cambió: el campo del coeficiente y su `%` son **una sola pieza** con los tokens del sistema y el valor **con coma** (lo que obligó a `type="text"`, porque un `type="number"` rechaza la coma y ahí estaba el origen del punto); los botones de acción pasaron a compartir el vocabulario del primario —degradé, línea de luz, sombra, 2 px de elevación— con el color diciendo qué hacen (`sumar` relleno con el acento, `editar` en acento, `borrar` en rojo suave); el piso ganó una cabecera en banda teñida con el número en un círculo con relieve; y la suma de coeficientes se muestra además como **barra de progreso**. En teléfono, los botones llevan texto y la unidad se apila: tres íconos de 42 px al lado de un campo en 390 px no entraban bien y no se entendían. Los cuatro componentes nuevos (`.accion`, `.chip`, `.panel-total`/`.barra-total` y el campo del coeficiente) quedaron en los dos catálogos.
  **Y una excepción de color que quedó anotada en la skill:** el botón de borrar usa el rojo del semáforo. Es la única excepción a que el semáforo no decore —"destructivo" es una convención universal y no es un estado del edificio—. El verde para editar, en cambio, se rechazó: en la misma pantalla el verde pasaría a significar "todo correcto" y "editar" a la vez.

  **3. El reparto automático del resto, que es lo que pediste y quedó mejor de lo que yo había propuesto.** Mi primera idea era guardar en una columna nueva el origen de cada coeficiente —tuyo o calculado— para poder redistribuir solo los automáticos. Tu forma no la necesita: **se reparte lo que falta entre las unidades que están en blanco**, y "en blanco" ya es un estado real de la base (la columna es anulable), así que sobrevive a recargar la página, a cerrar el navegador y a que lo siga otra persona mañana. Una marca de "esto lo toqué yo" guardada en la pantalla se pierde con la pestaña, y guardada en la base es una columna más para mantener para siempre. **Sin columna nueva y sin migración.**
  **Cómo quedó el tercer criterio.** `completar_el_resto` en el endpoint de atajos, con las cuentas en `services/finanzas.py` (`resto_por_repartir` y `completar_el_resto`), por el mismo método del resto mayor que los otros dos: tu caso da 20% y 20%, y uno que no divide exacto —40% entre tres— da 13,334 y dos de 13,333, **sumando 100,000% exacto**. No pide confirmación, al contrario de los otros dos: no puede pisar nada, y una pregunta que siempre se contesta igual se deja de leer. Se niega en tres casos con tres mensajes distintos, porque se resuelven distinto: no quedan unidades en blanco; lo cargado ya suma 100% y entonces a las que faltan les tocaría 0%, que es un dato inventado (si son exentas, se les carga 0 a mano); o lo cargado ya pasa de 100% y hay que corregir alguna. **20 tests nuevos** —10 del servicio y 10 del endpoint—, suite completa: **853**. Verificado además contra el servidor real con 16 comprobaciones, incluido tu ejemplo textual.
  **Lo que NO hice, y te lo marco porque lo mencionaste:** que el edificio nazca con todos los coeficientes repartidos por igual. Un edificio recién creado se vería listo para liquidar con porcentajes que nadie confirmó, y eso es exactamente el problema de la iteración anterior al revés: antes faltaba el dato y se descubría tarde; así el dato está pero es inventado, y eso no se descubre nunca. Las unidades siguen naciendo en blanco y el reparto en partes iguales está a un botón de distancia. Si lo querés igual, lo cambio: es una línea en el alta.

- [x] **F1-T28 · Prueba de punta a punta — estructura del edificio.**
  **Qué se prueba:** dar de alta un edificio real con varios pisos, confirmar que la estructura se generó sola, completar coeficientes con un atajo y verificar que suman 100,000% exacto, corregir uno a mano, asignar un propietario y un inquilino a departamentos distintos, y confirmar que al loguearse como cada uno solo alcanza lo suyo. Repetir con un edificio de 28 unidades o más para verificar el redondeo.
  **Aprobada el 2026-11-12, después de tu recorrido por la pantalla en producción. Corrida completa contra el backend real: 57 comprobaciones, las 57 bien.** El recorrido entero de arriba, en una sola pasada: un edificio de 5x4 con su estructura generada sola y sus identificadores correctos (`1A`…`5D`), las 20 unidades naciendo sin coeficiente y sin ocupantes, el atajo dando **100,000% exacto** —verificado sumando los veinte valores con `Decimal`, no leyendo el total que informa el servidor—, una corrección a mano bajando la suma a 99,500% con el aviso correspondiente, cuatro decimales rechazados, y el atajo negándose a pisar lo cargado con un 409.
  **El reparto del edificio de 28 unidades, que es el caso que fallaba:** suma 100,000% exacta, dos valores distintos (3,571 y 3,572) y **doce** unidades con el paso de más — los doce pasos de 0,001 que faltaban, repartidos y no apilados en la última, que quedó en 3,571. También el atajo por metro cuadrado: rechazado con un 400 que nombra las unidades sin superficie, y después, con las 28 superficies cargadas, sumando 100,000% con la unidad de 70 m² pagando 4,546% contra el 2,597% de la de 40 m².
  **Y el alcance, que es la otra mitad de la prueba.** Una propietaria en la 1A y un inquilino en la 2A: el mismo inquilino en una segunda unidad se rechaza con un 400 que nombra la unidad donde ya figura. Logueados, cada uno ve los espacios comunes de **su** edificio (200) y recibe **404 —no 403— en el edificio ajeno**, así que no puede ni averiguar que existe; y recibe 403 en listar la cartera, ver el detalle, tocar la configuración, cargar un coeficiente, crear un espacio común y dar de alta un edificio. Un propietario sin ninguna unidad no ve ningún edificio.
  **Lo que falta y es tuyo:** el mismo recorrido por la pantalla, con el navegador. Lo que verifiqué es que el backend responde lo que tiene que responder en cada paso y que la pantalla le pide exactamente eso; que lo que se dibuja se vea y se use bien, lo tenés que ver vos.

## Tema 1.7 — Mensajes de error

- [ ] **F1-T29 · Backend — `core/errores.py`, catálogo único de mensajes de error.** *(construida, falta tu revisión)*
  **Por qué existe esta tarea.** Hasta acá cada mensaje de error está escrito a mano dentro del endpoint que lo levanta, como un `detail=` suelto. Mientras hay dos endpoints eso no molesta; con cuarenta se convierte en tres problemas concretos: el mismo error se redacta distinto en dos lugares, el frontend no tiene nada estable contra lo que decidir (tiene que comparar el texto castellano, que cambia en cuanto alguien corrige una tilde), y cambiar un mensaje obliga a buscarlo por todo el proyecto. Es el mismo razonamiento que llevó a poner los permisos en una matriz en vez de repartirlos en condicionales: **si es una regla del sistema, es una estructura de datos, no texto suelto.**
  **Qué se construye:** `core/errores.py` con un catálogo de errores de negocio, cada uno con **código estable** (`CREDENCIALES_INVALIDAS`, `CUENTA_INHABILITADA`, `SIN_PERMISO`, `NO_ENCONTRADO`, …), su código HTTP y su texto en castellano; una excepción propia que se levanta por código y no por texto; y un manejador único registrado en `main.py` que la convierte en respuesta JSON con la **misma forma siempre** — código, mensaje, y los campos involucrados cuando sean de un formulario.
  **Regla:** ningún endpoint vuelve a escribir un `detail=` literal. El texto vive en el catálogo y en ningún otro lado.
  **Cuidado con no romper lo que ya anda:** `api.js` (`F05-T03`) ya estandariza errores del lado del frontend. Esta tarea le da una forma estable que consumir, **no** una segunda capa de traducción en paralelo; si al terminar hay dos lugares que deciden qué texto ve el usuario, la tarea salió mal.
  **Corrección del 2026-11-09: acá decía que `api.js` "ya traduce el 422 de Pydantic", y es falso.** `api.js` lo **formatea** —toma la lista de problemas por campo y la convierte en un texto legible tipo "campo: mensaje"— pero el mensaje de cada problema lo escribe Pydantic **en inglés**, y eso es lo que se ve en pantalla: al cargar un edificio con 70 pisos, el aviso dice *"cantidad_pisos: Input should be less than or equal to 40"*. Lo detecté construyendo `F1-T25`. Dejo la frase corregida porque si esta tarea se empieza creyéndola, el 422 se va a dar por resuelto y el texto va a quedar en inglés para siempre.
  **Cómo se traduce el 422, entonces, y por qué va acá y no en cada esquema.** El manejador único que esta tarea registra en `main.py` atiende también `RequestValidationError`, y traduce **por el tipo de error** que informa Pydantic (`missing`, `less_than_equal`, `greater_than_equal`, `string_too_short`, `string_too_long`, `decimal_max_places`, `extra_forbidden`…), usando el contexto que viene en cada problema para armar la frase con el número real. Son unas pocas entradas y cubren todos los formularios del sistema, presentes y futuros. La alternativa —un mensaje escrito a mano por campo en cada esquema— sería el mismo texto repetido en cuarenta lugares, que es exactamente lo que esta tarea existe para eliminar. El tipo que no esté traducido cae en un texto genérico que nombra el campo: es mejor que un `KeyError`, y el tipo sin traducir se agrega cuando aparece.
  **Y el nombre del campo también hay que traducirlo.** De nada sirve "El valor tiene que ser menor o igual a 40" si el campo se llama `cantidad_pisos`: el catálogo lleva, al lado de los mensajes, el nombre legible de los campos que puede nombrar un 422 ("cantidad de pisos", "unidades por piso", "código postal"). Es el mismo criterio que las etiquetas de los roles, que ya salen del backend por `GET /api/usuarios/opciones` y no están escritas en el JavaScript.
  **Cuidado con lo que el catálogo no puede filtrar:** el texto de un error de negocio se le muestra a cualquiera, así que ninguna entrada menciona tablas, columnas, consultas ni nombres de archivo. Eso ya es regla del proyecto (`FX-T11`) y el catálogo la vuelve verificable: alcanza con leer un archivo para auditarla entera.
  **Listo cuando:** hay test de que el manejador devuelve la misma forma para un error de negocio y para un `422` de validación, de que ningún código del catálogo está duplicado, y **de que ningún mensaje que llega al usuario está en inglés** — concretamente, que un pedido con un número arriba del tope y uno con un campo faltante devuelven las dos frases en castellano y nombrando el campo como lo nombra la pantalla.
  **Construida, falta tu revisión.** `core/errores.py` (archivo nuevo) con **44 entradas**, los tres manejadores registrados en `main.py`, los **27 mensajes migrados** desde seis archivos, `api.js` exponiendo el código, y **22 tests** en `tests/test_errores.py`. Suite completa: **876**. No quedó un solo `detail=` escrito a mano en el backend.
  **Qué se ve distinto.** Lo que antes decía *"cantidad_pisos: Input should be less than or equal to 40"* ahora dice **"La cantidad de pisos no puede ser mayor que 40."**, y un formulario incompleto contesta campo por campo: "Completá el nombre.", "Completá el código postal." El 422 se traduce **por tipo de problema** —23 plantillas que cubren todos los formularios del sistema, presentes y futuros— y el nombre del campo también se traduce, porque "El valor no puede ser mayor que 40" no dice nada si no se sabe de qué valor habla.
  **Los mensajes de los validadores propios se respetan tal cual.** "El coeficiente admite hasta 3 decimales" sabe cosas que el tipo de error no, así que el traductor no lo pisa con una frase genérica. Llegan como `value_error` con la excepción en el contexto; el único `value_error` que no es propio es el del validador de email, que viene en inglés y se reconoce por su contexto.
  **La forma de la respuesta es la misma siempre**, venga de un endpoint, de una dependencia, de la validación o del ruteo de FastAPI: `codigo` (estable, para que decida el cliente), `mensaje` (castellano, para que lea la persona) y `campos` (por campo, cuando es un formulario). Una ruta inexistente dejó de contestar `{"detail":"Not Found"}` en inglés. `campos` viaja siempre, vacío cuando no corresponde: una forma que cambia según el caso obliga a preguntar antes de leer.
  **Y la regla `FX-T11` pasó de revisable a verificada.** Hay un test que recorre el catálogo entero buscando nombres de tabla, de columna, de archivo e ids internos. Al migrar apareció un caso real: el 404 de usuario decía "No existe un usuario con id 37", y ese id es interno y no le sirve a nadie del otro lado de la pantalla.
  **Una consecuencia de levantar una excepción propia, anotada porque costó un rato de diagnóstico:** `ErrorDeNegocio` se convierte en respuesta HTTP **solo si la aplicación registró el manejador**. La aplicación real lo hace en `main.py`; la app de juguete que usan los tests de dependencias en aislamiento también tuvo que hacerlo, y hasta que se agregó esa línea los rechazos de permiso no eran un 403 sino una excepción sin atender, con un error que no mencionaba lo que faltaba.
  **El primer consumidor real de `campos` llegó enseguida, el 2026-11-12: la marca de error por campo.** El aviso del backend se mostraba arriba del formulario y, en un formulario largo en teléfono, **no se veía** — se apretaba "Crear edificio" y no pasaba nada visible. Ahora cada campo rechazado se marca en rojo con su frase debajo, y la pantalla lleva el foco al primero. Eso solo es posible porque el catálogo manda el problema **por campo**: con un único texto arriba no había forma de saber a qué campo correspondía. Está en `formularios.js` —la estructura se genera, no la escribe cada HTML— y enganchado en los cinco formularios que existen. Aprobado el 2026-11-13.
  **Lo que no cambió, a propósito:** los textos. Esta tarea centraliza los mensajes, no los reescribe — salvo los cuatro del fallo de guardado, que eran cuatro redacciones del mismo error y ahora son uno con un parámetro, y el 404 de usuario, que perdió el id.

- [ ] **F1-T30 · Backend + Frontend — mensajes diferenciados del login, sin abrir enumeración de cuentas.** *(construida, falta tu revisión)*
  **El problema que resuelve.** `F1-T07` dejó un solo 401 para los tres motivos de rechazo. Eso es correcto como defensa y malo como experiencia: el usuario inhabilitado por un administrador recibe "email o contraseña incorrectos", así que reintenta su contraseña —que es la correcta—, prueba otra, y termina pidiendo ayuda por algo que el sistema sabía desde el primer intento.
  **La regla de seguridad que no se negocia, y por qué.** Mientras no se haya verificado la contraseña, el sistema **no puede** decir nada que dependa de si la cuenta existe. "Ese email no está registrado" y "la contraseña es incorrecta" tienen que seguir siendo la misma respuesta. Si no lo fueran, el login se convierte en un verificador de direcciones: se le pasa una lista de emails, se queda con los que existen y recién ahí se atacan solo esos. Es la recomendación explícita de OWASP y la razón por la que `F1-T07` está hecha así. Lo mismo vale para el tiempo de respuesta, que ya está igualado con un hash descartable.
  **Lo que sí se puede diferenciar, que es justamente lo que falta.** Una vez que la contraseña **se verificó y es correcta**, quien está del otro lado ya demostró que la cuenta es suya, y contarle su situación no le informa nada a un atacante que no tenga ya la contraseña. Ahí sí van mensajes propios:
  - cuenta inhabilitada → "Tu cuenta está inhabilitada. Contactá al administrador del consorcio." (código `CUENTA_INHABILITADA`)
  - y queda el lugar listo para lo que venga después de la misma forma: contraseña vencida, segundo factor pendiente, cuenta bloqueada por intentos.
  **El orden importa y es el contenido real de la tarea:** primero se busca el usuario, siempre se verifica la contraseña (exista o no), y **solo si la verificación dio bien** se evalúa el estado de la cuenta. Invertir esos dos pasos —chequear `activo` antes de la contraseña— vuelve a abrir la enumeración completa, porque responder "inhabilitada" sin contraseña correcta confirma que el email existe.
  **Dónde vive el texto:** en el catálogo de `F1-T29`. Esta tarea no agrega mensajes sueltos al router; agrega entradas al catálogo y la decisión de cuál corresponde.
  **Frontend:** la pantalla de login decide qué mostrar por el **código**, nunca comparando el texto. Y el caso "no sé si mi email está registrado" no se responde con un mensaje: se responde con el enlace de recuperación de contraseña, que también contesta siempre lo mismo exista o no la cuenta, y manda el correo solo si existe.
  **Listo cuando:** hay test de que el email inexistente y la contraseña incorrecta siguen devolviendo respuestas **idénticas** —el test de `F1-T07` no se toca ni se debilita—, de que la cuenta inhabilitada con la contraseña correcta devuelve `CUENTA_INHABILITADA`, y de que la cuenta inhabilitada con la contraseña **incorrecta** devuelve el error genérico y no revela nada.
  **Construida, falta tu revisión.** Tres líneas en el endpoint de login, la entrada `CUENTA_INHABILITADA` en el catálogo de `F1-T29`, y la decisión por código en `login.js`. Verificado contra el servidor real: con la contraseña correcta, una cuenta inhabilitada contesta **403 `CUENTA_INHABILITADA`** y *"Tu cuenta está inhabilitada. Contactá al administrador del consorcio."*; con la contraseña incorrecta contesta **exactamente lo mismo** que un email que no existe, comparado campo por campo.
  **Los tres tests existían y encodeaban la regla vieja.** Decían "el usuario inactivo da el mismo error que la contraseña mala", que era correcto antes de esta tarea. Los reemplacé por los dos que pide el Roadmap y dejé escrito en cada uno por qué cambió: el que verifica que **con la contraseña mal no se revela nada** es el que sostiene la defensa, y es el que falla si alguien invierte el orden de las dos verificaciones en el endpoint.
  **El orden quedó documentado donde se lee.** El comentario del endpoint dice que el orden de esas dos verificaciones **es** la defensa, no un detalle de implementación: responder "inhabilitada" sin contraseña correcta convierte al login en un verificador de direcciones de correo.
  **Y la pantalla decide por el código, no por el texto.** Con `CREDENCIALES_INVALIDAS` se borra el campo de contraseña y el foco vuelve ahí, que es lo único que hay para reintentar. Con `CUENTA_INHABILITADA` **no se borra**: la contraseña estaba bien, borrarla haría pensar que el problema es esa, y no hay nada que reintentar hasta que un administrador habilite la cuenta.

- [ ] **F1-DOC · Documentación de la Fase 1.** *(redactada, falta tu revisión)*
  Redactar `documentacion/fases/Fase_1_Usuarios_y_Estructura.md` según la sección 1.6. Foco particular: el cuadro completo de los 8 roles con lo que puede cada uno, cómo se decidió resolver el alcance (`F1-T02`) y por qué, y un ejemplo numérico de reparto de coeficientes en un edificio de 28 unidades.
  **Redactada el 2026-11-12**, con las siete secciones que pide la sección 1.6 y los tres focos pedidos: el cuadro de los nueve roles con lo que puede cada uno hoy, la decisión del alcance de `F1-T02` con las dos opciones que descarté y por qué, y el reparto de las 28 unidades con la cuenta completa (100÷28 = 3,571428…, veintiocho veces 3,571 dan 99,988, los 12 pasos faltantes se reparten y 12 unidades quedan en 3,572). Lleva además los endpoints con un ejemplo real de pedido y respuesta, la deuda asumida con quién la salda, y el detalle de que la suite pasó de 27 tests al cierre de la Fase 0 a 876.
  **El documento queda escrito pero la fase se cierra con tu aprobación de `F1-T29` y `F1-T30`**, que son las dos únicas tareas que todavía no revisaste. La cabecera del documento lo dice así, en vez de declarar una fase cerrada que no lo está.

---

# Fase 2 — Gestión financiera

**Objetivo.** El módulo más sensible del sistema: de él sale el dato de morosidad que después colorea de amarillo o rojo un departamento en el Dashboard Visual, y un error acá afecta a todos los propietarios a la vez.

**Respaldo documental:** `01_Documento_General.md` (6) · `02_Documento_Tecnico.md` (3.2, 5.1, 5.2) · `investigaciones/Prorrateo.md`, `Pagos_y_Conciliacion.md`, `Caja_chica.md`, `Presupuestos_y_Facturas.md`.

**Precondición:** Fase 1 cerrada. En particular `F1-T24`: sin coeficientes cargados no se puede generar una sola expensa.

**Temas:** 2.1 Gastos · 2.2 Prorrateo y expensas · 2.3 Pagos y conciliación · 2.4 Deudores · 2.5 Fondos, caja chica, presupuestos y facturas · 2.6 Reportes · 2.7 Pantalla financiera.

## Tema 2.1 — Gastos

- [ ] **F2-T01 · Backend — modelo `Gasto`.**
  **Qué se construye:** `edificio_id`, `rubro`, `monto` (`Numeric(12,2)`, nunca `float`, que pierde centavos), `fecha`, `descripcion`, `proveedor_id`*, `activo_id`*, `creado_en`. CHECK de monto mayor a cero.
  **Sobre los campos marcados con asterisco:** son **enteros sueltos sin clave foránea real**, deliberadamente. Una columna sin FK no depende de que la tabla destino exista, así que se puede crear desde el primer día; lo que sí necesita la tabla destino es la restricción. `activo_id` se formaliza en la Fase 4 y `proveedor_id` en la Fase 7. **Cada columna diferida se documenta en el modelo con un comentario que diga en qué fase se formaliza.**
  **Regla:** un gasto es editable (se carga mal un monto y se corrige), pero esa edición **no reescribe una expensa ya liquidada**.

- [ ] **F2-T02 · Backend — CRUD de gastos con filtro por período.**
  **Qué se construye:** alta, edición, baja y listado bajo `/api/edificios/{id}/gastos`, con filtro por año y mes.
  **Cuidado con:** la edición es obligatoria desde el principio, no un agregado posterior. Sin ella, un gasto mal cargado obliga a recargar el edificio entero a mano — pasó.

## Tema 2.2 — Prorrateo y expensas

- [ ] **F2-T03 · Lógica — `services/finanzas.py`, reparto de un monto entre unidades.**
  **Qué se construye:** la función pura que, dado un total y la lista de coeficientes de las unidades, devuelve cuánto le toca a cada una.
  **Regla de precisión no negociable:** al repartir un monto entre N unidades **nunca se redondea cada parte por separado** — eso deja centavos sin asignar. La última unidad recibe el **resto exacto**, de modo que la suma de lo repartido siempre iguala el total.
  **Listo cuando:** hay tests con montos que no dividen exacto (por ejemplo, $4.849.900 entre 32 unidades con coeficientes desiguales) verificando que la suma de las partes da **exactamente** el total, al centavo.

- [ ] **F2-T04 · Backend — modelos `Expensa`, `ExpensaDetalle` y `ExpensaDepartamento`.**
  **Qué se construye:** `Expensa` (edificio, año, mes, total, creado_en; CHECK de mes entre 1 y 12 y total mayor a cero); `ExpensaDetalle` (la apertura por rubro de esa liquidación — la transparencia que pide `01` sección 6.1, no solo un total); `ExpensaDepartamento` (lo que le toca a cada unidad).

- [ ] **F2-T05 · Backend — generación de la expensa del período.**
  **Qué se construye:** `POST /api/edificios/{id}/expensas`: toma los gastos reales del período, los agrupa por rubro, aplica el prorrateo de `F2-T03` y genera la expensa completa en una transacción.
  **Regla de inmutabilidad:** una expensa liquidada es un documento contable y **no se edita**. Editar un gasto viejo no la altera retroactivamente.
  **La única excepción, deliberada y acotada:** regenerar **la última** expensa del edificio, para el caso real de haber liquidado con un gasto mal cargado. Regenerar un período que no sea el último está **prohibido**: rompería la cadena contable de los meses posteriores.
  **Cómo se implementa la confirmación:** el servidor responde `409` explicando exactamente qué se va a reemplazar, y el cliente reenvía la misma petición con un campo booleano de confirmación. **Este es el mecanismo que permite no usar nunca un `confirm()` del navegador**, y se reutiliza en todo el sistema.
  **Cuidado con:** al regenerar se **conserva la identidad de la expensa** (se reemplazan su detalle y su reparto, no se la borra y recrea) para que los pagos ya registrados contra ella sigan siendo válidos.

- [ ] **F2-T06 · Backend — consulta de expensas y su detalle.**
  **Qué se construye:** listado de expensas del edificio, detalle con su apertura por rubro, y la expensa de una unidad puntual con su apertura — que es lo que después consume "Mi cuenta" del residente.

## Tema 2.3 — Pagos y conciliación

- [ ] **F2-T07 · Lógica — ciclo de vida del pago.**
  **Qué se construye:** las reglas puras de `pendiente → confirmado` y `pendiente → rechazado`, con sus tests.
  **Regla fundamental:** **solo un pago confirmado reduce la deuda.** Si el sistema diera por saldado un pago apenas el residente lo carga, cualquiera podría subir un comprobante falso y aparecer sin deuda sin que la plata haya entrado. La conciliación es un paso humano, no automático.
  **Segunda regla:** el propio residente **nunca** puede confirmar su pago, aunque tenga permisos sobre su unidad.
  **Tercera regla:** un pago pendiente no baja el saldo, **pero sí se le muestra al residente** como "ya lo cargaste, está esperando confirmación". Sin ese aviso, el residente ve su saldo intacto y vuelve a pagar.

- [ ] **F2-T08 · Backend — modelo `Pago` y carga por el residente.**
  **Qué se construye:** el modelo (`departamento_id`, `expensa_id`, `monto`, `fecha`, `medio_pago`, `comprobante_url`, `estado` con CHECK y por defecto `pendiente`, `creado_en`), el endpoint con el que **el propio usuario logueado** carga su pago sin tener que elegir edificio ni piso (el backend resuelve sus departamentos solo), y el endpoint que le devuelve sus unidades con su estado de cuenta.
  **Regla:** los **pagos parciales están permitidos** y el sistema los muestra como tales, con el saldo restante calculado — son habituales en la realidad del rubro.

- [ ] **F2-T09 · Backend — conciliación y listado de pagos.**
  **Qué se construye:** el cambio de estado (solo administración) y el listado de pagos del edificio con filtro por estado.
  **Cuidado con:** el listado es parte de esta tarea, no un agregado posterior. Sin él, la cola de conciliación no existe como pantalla.

- [ ] **F2-T10 · Decisión ya tomada — cómo se muestran los datos de cobro.**
  **Qué queda fijado (no se rediscute, se implementa):** se muestran **el CBU y el alias como texto, cada uno con su botón de copiar**, para pegarlos en la app del banco. **No hay QR de ningún tipo.**
  **Por qué:** el QR interoperable de Argentina ("Transferencias 3.0", regulado por el BCRA) **solo lo pueden emitir entidades financieras y proveedores de servicios de pago registrados** — una aplicación de terceros no puede generar un QR de pago real y válido. La alternativa de un "QR de conveniencia" que al escanearlo solo muestra el CBU se descartó por innecesaria: copiar un texto es un toque, y escanear un QR para volver a copiar el texto que tenía adentro es un paso de más. Fundamento completo en `investigaciones/Pagos_y_Conciliacion.md`.
  **Consecuencia legal, que conviene tener escrita:** mostrar el CBU del consorcio **no convierte a SMART Building en un procesador de pagos**. La plata nunca pasa por la plataforma.

## Tema 2.4 — Deudores

- [ ] **F2-T11 · Backend — cálculo de deudores.**
  **Qué se construye:** `GET /api/edificios/{id}/deudores` como **vista calculada, no como tabla propia**: se arma sobre `ExpensaDepartamento` menos los pagos **confirmados**, devolviendo por unidad el saldo y la antigüedad de la deuda en meses, ordenado de más a menos atrasada.
  **Regla:** la deuda del mes corriente **no cuenta como atraso** hasta pasado el vencimiento configurado del edificio.
  **Regla:** es **siempre de solo lectura**. La única forma de saldar una deuda es conciliar el pago correspondiente.
  **Este es el dato que alimenta el amarillo y el rojo del Dashboard Visual:** un mes de deuda pinta amarillo, más de un mes pinta rojo.

## Tema 2.5 — Fondos, caja chica, presupuestos y facturas

- [ ] **F2-T12 · Backend — `Fondo` y `MovimientoFondo`.**
  **Qué se construye:** fondo de reserva y otros fondos especiales, cada uno con sus movimientos de ingreso y egreso (CHECK de tipo). **El saldo se calcula, no se guarda.**

- [ ] **F2-T13 · Backend — `Caja` y `MovimientoCaja` (sistema de fondo fijo).**
  **Qué se construye:** caja chica con `monto_fijo` (CHECK mayor a cero) y `responsable_id`, con sus movimientos.
  **Regla contable:** es un **sistema de fondo fijo**, que es como funciona en la práctica en las administraciones: la caja tiene un monto fijo definido, se gasta contra ella durante el mes y se **repone hasta ese monto** cada vez que se rinde. **No es una cuenta de saldo libre**: el disponible y lo pendiente de reposición se derivan del monto fijo y los movimientos. Fundamento en `investigaciones/Caja_chica.md`.
  **Cuidado con:** el primer diseño no tenía movimientos propios y quedó incompleto; el modelo correcto es este.

- [ ] **F2-T14 · Backend — `Presupuesto` y `Factura`.**
  **Qué se construye:** `Presupuesto` (edificio, proveedor_id*, descripción, monto, fecha, estado con CHECK `pendiente`/`aprobado`/`rechazado`, `gasto_id` para vincularlo al gasto real cuando se aprueba) y `Factura` (siempre vinculada a un gasto real).
  **Regla:** completan la cadena de trazabilidad **presupuesto → gasto → factura → pago**. Un presupuesto nace pendiente; al aprobarse se lo puede vincular al gasto que generó, cerrando la comparación entre "lo que se presupuestó" y "lo que finalmente se pagó".

- [ ] **F2-T15 · Backend — CRUD de fondos, caja, presupuestos y facturas.**
  **Qué se construye:** los cuatro conjuntos de endpoints, todos anidados bajo edificio.

## Tema 2.6 — Reportes

- [ ] **F2-T16 · Backend — endpoint consolidado de reportes financieros.**
  **Qué se construye:** un endpoint que devuelve, por período: recaudado contra esperado, morosidad, y gastos agrupados por rubro con su evolución.
  **Cuidado con:** **consolida, no recalcula de cero.** La morosidad ya sale de `F2-T11`, la evolución de gastos por rubro de `F2-T02`, y el recaudado contra esperado del total de la expensa contra la suma de pagos confirmados de `F2-T09`. Es la data cruda de la Analítica de la Fase 6.

## Tema 2.7 — Pantalla financiera

> `financiero.html` es **un solo archivo para dos audiencias**, no dos pantallas. El JS rutea por rol al inicio: gestión ve el módulo completo con pestañas; residente ve "Mi cuenta".

- [ ] **F2-T17 · Frontend — cascarón con pestañas y pestaña Gastos.**
  **Qué se construye:** la página con el selector segmentado que organiza todo el módulo (Gastos / Expensas / Pagos / Deudores / Fondos), con la primera pestaña funcional: carga, edición y listado de gastos con filtro por rubro y período.
  **Incluye:** `assets/js/moneda.js` (formato argentino para **mostrar** montos, centralizado para que ninguna pantalla arme su propio formateador) y `assets/js/monto-input.js` (formato de miles **mientras el usuario tipea**).
  **Cuidado con el campo de monto:** un `<input type="number">` **no sirve**: su modelo de valor nunca agrupa miles. Se usa `type="text"` con `inputmode="decimal"` (que mantiene el teclado numérico en mobile) y formateo propio que reposiciona el cursor según cuánto cambió el largo.
  **Cuidado con las fechas:** nunca pasar una fecha `YYYY-MM-DD` del backend por `new Date()` — se interpreta como medianoche UTC y en Argentina (UTC-3) se muestra un día antes. Se separa el texto y se reordena a mano.

- [ ] **F2-T18 · Frontend — pestaña Expensas (gestión).**
  **Qué se construye:** generación de la expensa del período, listado de liquidaciones, y detalle con la apertura por rubro. El botón de regenerar aparece **solo en la última** y usa el patrón de confirmación de `F2-T05`: el formulario pasa a modo confirmación con el texto explícito de qué se reemplaza.
  **Cuidado con:** si el usuario cambia algún dato del formulario, el estado de confirmación **se reinicia**.

- [ ] **F2-T19 · Frontend — pestaña Pagos, vista de gestión.**
  **Qué se construye:** la cola de pagos pendientes con sus botones de confirmar y rechazar en la misma fila, y el listado histórico con su estado.

- [ ] **F2-T20 · Frontend — pestaña Deudores.**
  **Qué se construye:** listado ordenado por antigüedad con el detalle de las expensas impagas de cada unidad. Consume tal cual `F2-T11`, sin cambios de backend.
  **Nota de alcance:** el acceso del rol Auditor a esta pestaña depende de cómo se haya resuelto `F1-T02`. Si quedó pendiente, se habilita en `F11-T05` y **no antes** — darle acceso a toda la cartera sin un vínculo real sería un sobre-permiso.

- [ ] **F2-T21 · Frontend — pestaña Fondos, con su sub-navegación.**
  **Qué se construye:** una única pestaña principal con **cuatro secciones internas** (Fondos / Caja chica / Presupuestos / Facturas) mediante una segunda fila de pestañas.
  **Por qué agrupadas:** sumar las cuatro como botones del selector principal daba ocho pestañas en una sola fila, demasiado para el flujo principal.
  **Cuidado con:** al cargar un movimiento hay que **volver a pedir el listado** antes de refrescar el saldo; refrescarlo desde el caché muestra el valor viejo (bug real). Y ningún `<select required>` puede quedar oculto por `display:none` en un ancestro: Chromium bloquea el envío del formulario **en silencio** porque no puede enfocarlo para mostrar el mensaje — los campos mutuamente excluyentes se validan desde el JS, no con `required` en HTML.

- [ ] **F2-T22 · Frontend — "Mi cuenta" del residente.**
  **Qué se construye:** la rama de rol para Propietario e Inquilino dentro del mismo archivo: sus unidades, la expensa del período **con su apertura por rubro** (no solo el total), el saldo, el CBU y el alias con botón de copiar, y el formulario de carga de pago.
  **Regla visible en pantalla:** un pago cargado aparece como pendiente con el texto que explica que el saldo se actualiza recién cuando la administración lo concilia.
  **Cuidado con:** el Propietario a veces necesita elegir de cuál de sus unidades habla; el Inquilino **nunca** — con una sola unidad, el selector ni se muestra.

- [ ] **F2-T23 · Prueba de punta a punta — financiero.**
  **Qué se prueba, con datos cargados a mano y en el frontend real:** cargar los gastos de un mes; generar la expensa; verificar que la suma de lo repartido da exactamente el total; corregir un gasto y regenerar la última expensa confirmando el reemplazo; cargar pagos desde la sesión del residente y dejarlos pendientes; confirmar uno, rechazar otro; verificar que solo el confirmado bajó el saldo; dejar unidades con uno, dos y cuatro meses de deuda y confirmar que Deudores calcula bien meses y monto en cada caso. Repetir con el edificio de 28 unidades.

- [ ] **F2-DOC · Documentación de la Fase 2.**
  Redactar `documentacion/fases/Fase_2_Gestion_Financiera.md` según la sección 1.6. Foco particular: el ejemplo numérico completo de una liquidación (gastos por rubro → total → reparto por coeficiente → lo que ve cada unidad), el circuito de conciliación explicado como se le explicaría a un administrador, y por qué no hay QR.

---

# Fase 3 — Reclamos y mantenimiento

**Objetivo.** La puerta de entrada más habitual para el residente y el circuito de trabajo que responde. Se implementan juntos porque un reclamo puede dar origen a una orden de trabajo, pero **son dos flujos de estado distintos** y confundirlos es un error fácil de cometer.

**Respaldo documental:** `01_Documento_General.md` (10, 11) · `02_Documento_Tecnico.md` (3.3, 3.4, 5.3, 5.4, 5.5, 5.6, 5.7).

**Precondición:** Fase 1 cerrada. En particular `Edificio.encargado_id` (`F1-T18`), sin el cual no hay forma de resolver qué reclamos puede gestionar un encargado.

**Temas:** 3.1 Flujos de estado · 3.2 Reclamos · 3.3 Órdenes de trabajo · 3.4 Tiempos y severidad · 3.5 Pantallas.

## Tema 3.1 — Los dos flujos de estado

- [ ] **F3-T01 · Lógica — flujo del reclamo y niveles de prioridad.**
  **Qué se construye:** en `services/reclamos.py`, la tabla de transiciones válidas del reclamo (`recibido → asignado → en_curso → resuelto → cerrado`) y una **única** función que la valida, más las tres prioridades con su significado exacto.
  **Las tres prioridades, con el texto que ve el residente al elegir** (para que la elección signifique lo mismo para todos): **leve**, no compromete a nadie más que a quien reclama, no es urgente; **medio**, empieza a afectar o podría afectar a otras unidades o al funcionamiento del edificio; **crítico**, compromete la seguridad de los residentes o del edificio, requiere atención inmediata.
  **Regla de color:** leve y medio pintan **amarillo**; crítico pinta **rojo**. Leve y medio nunca se distinguen por color.
  **La excepción de reapertura:** `resuelto → en_curso` es la **única** excepción al flujo lineal, y la única transición que puede disparar quien creó el reclamo además de la gestión. Sin esto, corregir un cierre prematuro obligaría a cargar un reclamo nuevo, perdiendo el historial de comentarios y fotos.
  **`cerrado` es terminal, siempre y a propósito:** un problema que reaparece es un reclamo **nuevo**. El antecedente tiene que quedar archivado tal como se cerró.
  **Listo cuando:** hay tests de cada transición válida, de cada inválida, y de la reapertura.

- [ ] **F3-T02 · Lógica — flujo de la orden de trabajo.**
  **Qué se construye:** en el mismo archivo, las constantes y la función de transición **propias** de la orden: `pendiente → en_curso → resuelta`, estrictamente lineal y **sin reapertura**.
  **Por qué comparte archivo pero no lógica:** los dominios se implementan juntos, **no porque sean el mismo flujo**. Una orden de trabajo es un **registro de ejecución**, no un hilo de seguimiento: si el trabajo resulta incompleto se genera una orden nueva y la vieja queda archivada tal como se cerró. Confundir los dos flujos es un error que ya se cometió una vez.
  **Cuatro tipos:** preventivo, correctivo, programado, emergencia.

## Tema 3.2 — Reclamos

- [ ] **F3-T03 · Backend — modelos `Reclamo`, `ReclamoFoto` y `ReclamoComentario`.**
  **Qué se construye:** `Reclamo` con `edificio_id` siempre, más el objetivo puntual: `departamento_id` opcional **o** `espacio_comun_id` opcional **o** ninguno de los dos (el edificio en general). Descripción, prioridad, estado (nace en `recibido`), `creado_por_id`, `creado_en`, `cerrado_en`.
  **Los tres CHECK:** prioridad válida, estado válido, y **`departamento_id IS NULL OR espacio_comun_id IS NULL`** — la restricción que hace imposible un reclamo que sea sobre una unidad *y* un espacio común a la vez. Los tres objetivos posibles se codifican con esas dos columnas, sin una tercera columna de "tipo".
  **Convención de adjuntos, para todo el sistema:** una foto es **una fila en una tabla hija con una URL**, nunca una lista de URLs aplastada en un campo de texto.
  **`cerrado_en` se completa solo al llegar a `cerrado`**, y es lo que permite calcular el tiempo de resolución.

- [ ] **F3-T04 · Backend — dependencias de autorización de reclamos.**
  **Qué se construye:** en `core/dependencies.py`, dos dependencias nuevas: la que responde "¿gestionás reclamos y órdenes en este edificio?" (admin general siempre; admin de consorcio o encargado solo si son los de **ese** edificio) y la que responde "¿podés cargar un reclamo acá?" (lo anterior **o** cualquiera con una unidad propia en el edificio).
  **Cuidado con:** una dependencia se reutiliza si la regla coincide, aunque el nombre suene a otro dominio. La segunda de estas dos resultó ser también la regla correcta para "ver los espacios comunes de un edificio": el conjunto de gente es idéntico. Se reutiliza y se documenta por qué, en vez de escribir una quinta dependencia igual.

- [ ] **F3-T05 · Backend — ciclo de vida del reclamo.**
  **Qué se construye:** `routers/reclamos.py` con creación (fotos como lista de URL que se convierten en filas), listado del edificio para gestión con filtros de estado y prioridad, listado de los propios para cualquier rol, detalle con fotos y comentarios anidados, alta de comentario, y cambio de estado.
  **Regla:** el cambio de estado usa **siempre** la función de `F3-T01`. Ningún endpoint valida una transición a mano.
  **Quién puede qué:** administración y encargado del edificio mueven el flujo completo; **quien lo creó puede comentar en cualquier estado** pero no mover el flujo, salvo la reapertura. Siempre consultable por quien lo creó.
  **Listo cuando:** hay tests de los tres objetivos posibles, del control de acceso de listado, detalle y comentario, y de las cuatro variantes de cambio de estado incluida la reapertura.

## Tema 3.3 — Órdenes de trabajo

- [ ] **F3-T06 · Backend — modelos `OrdenTrabajo` y `OtEvidencia`.**
  **Qué se construye:** `OrdenTrabajo` con edificio, espacio común opcional, `activo_id`* (entero suelto, se formaliza en la Fase 4), `reclamo_id` opcional, tipo, prioridad, estado, descripción, costo, **`encargado_id`** (FK real a un usuario con rol encargado) y/o `proveedor_id`* (entero suelto hasta la Fase 7), `creado_en`, `fecha_inicio`, `fecha_cierre`. CHECK de tipo, estado, prioridad y costo nulo o mayor o igual a cero. `OtEvidencia` con URL, momento (antes/después con CHECK), subido_por y fecha.
  **Regla de asignación:** una orden puede nacer sin asignar, pero **no puede pasar a `en_curso` sin alguien asignado** — un encargado o un proveedor, cualquiera de los dos alcanza. Nunca una orden en curso sin nadie real haciéndola.

- [ ] **F3-T07 · Backend — generación de orden desde un reclamo.**
  **Qué se construye:** el endpoint que crea la orden vinculada al reclamo, heredando edificio, ubicación, prioridad y descripción si no se especifican explícitas.
  **Reglas:** bloqueada para un reclamo ya resuelto o cerrado, y bloqueada si ya existe una orden **activa** vinculada a ese reclamo — pero una orden ya resuelta nunca bloquea generar una nueva (caso de reapertura). **Generar la orden es, en los hechos, el acto de asignar el reclamo:** si estaba en `recibido`, pasa a `asignado` acá mismo, siempre a través de la función de transición, nunca a mano.

- [ ] **F3-T08 · Backend — gestión de órdenes y sincronización con el reclamo.**
  **Qué se construye:** alta manual sin reclamo previo, listado con filtros y detalle (**gestión únicamente** — nunca el propietario o inquilino directo: su ventana sigue siendo el reclamo), asignación y reasignación con semántica de `exclude_unset`, cambio de estado, y alta de evidencia.
  **Reglas del cambio de estado:** pasar a `en_curso` exige tener alguien asignado y registra `fecha_inicio`; pasar a `resuelta` registra `fecha_cierre` y admite cargar el costo en la misma operación; una orden resuelta **ya no se reasigna**.
  **La sincronización con el reclamo de origen, paso a paso:** generar la orden lleva el reclamo a `asignado`; pasarla a `en_curso` lo lleva a `en_curso`; pasarla a `resuelta` lo lleva a `resuelto`. Siempre a través de la misma función de validación: si el reclamo ya llegó a un estado terminal por otra vía, **no se fuerza nada**.
  **⚠️ Trampa real, la más importante de esta fase:** la sincronización del cierre **no funciona si no existe también la del inicio**. Pasar la orden a `resuelta` intenta llevar el reclamo a `resuelto`, pero `asignado → resuelto` **no es una transición válida** (hay que pasar por `en_curso`). Sin el paso intermedio, la automatización **parece funcionar y silenciosamente no hace nada**. Los dos flujos tienen que caminar en paralelo, paso a paso.

## Tema 3.4 — Tiempos y severidad

- [ ] **F3-T09 · Lógica — tiempos de resolución.**
  **Qué se construye:** las funciones puras que calculan el tiempo de resolución, por separado para reclamos y para órdenes, expuestas por la API en segundos y en `null` mientras el elemento sigue abierto.
  **Regla:** el reclamo se mide desde su creación **hasta el cierre**, no hasta "resuelto" — que todavía puede revertirse. La orden se mide hasta `fecha_cierre`.
  **Cuidado con:** son campos **calculados del esquema de salida**, no se recalculan en JavaScript. El frontend pinta lo que la API ya calculó. Y el servicio no importa modelos: recibe los objetos por *duck typing*, lo que además hace los tests triviales.

- [ ] **F3-T10 · Lógica — `services/severidad.py`, el semáforo por unidad.**
  **Qué se construye:** las funciones puras de severidad por factor, cada una devolviendo uno de los cuatro valores.
  **Reclamos:** algún reclamo abierto crítico → `crit`; algún reclamo abierto de cualquier otra prioridad → `warn`; ninguno → `ok`.
  **Órdenes:** alguna **en curso** → `pend`; en cualquier otro caso → `ok`. **Nunca devuelve `warn` ni `crit`**: el naranja es exclusivo de mantenimiento en ejecución. Y ojo: una orden todavía `pendiente`, sin arrancar, **no** dispara el naranja.
  **Alcance acotado a esta fase:** la severidad por deuda y la combinación con precedencia quedan para la Fase 5, cuando el Dashboard Visual arma la respuesta completa.
  **Listo cuando:** hay tests de cada rama de cada función, incluido el caso de la orden pendiente que no pinta naranja.

## Tema 3.5 — Pantallas

- [ ] **F3-T11 · Frontend — alta de reclamo (residente).**
  **Qué se construye:** `reclamos.html` con la rama del residente: objetivo (unidad propia / espacio común / edificio en general) y prioridad como **tarjetas seleccionables con su explicación** (un `<select>` no tiene lugar para esa línea de texto), descripción, y fotos como lista dinámica de URLs.
  **Regla de velocidad, que es un requisito funcional y no una mejora de UX:** un formulario de reclamo que tarde más que mandar un mensaje de texto ya fracasó, por prolijo que sea el registro que genere. Con una sola unidad propia el selector de unidad **ni se muestra**.
  **Cuidado con:** el envío exitoso se confirma con un mensaje en línea explícito, no con un cambio de pantalla silencioso.

- [ ] **F3-T12 · Frontend — seguimiento del propio reclamo.**
  **Qué se construye:** la vista de quien lo creó: el flujo de estados visible en todo momento, el hilo de comentarios, y el botón de reabrir cuando está en `resuelto` y el problema sigue.
  **Por qué importa:** es la funcionalidad que el relevamiento identificó como la más valorada por el residente — poder mostrar que un problema ya se reclamó antes y la reparación no funcionó.

- [ ] **F3-T13 · Frontend — gestión de reclamos.**
  **Qué se construye:** en el **mismo archivo**, la rama de administración y encargado: todos los reclamos del edificio, filtros por estado y prioridad, cambio de estado y botón de generar orden de trabajo.

- [ ] **F3-T14 · Frontend — `mantenimiento.html`, órdenes de trabajo.**
  **Qué se construye:** listado con filtros, alta manual, asignación de un encargado real desde un selector (y del proveedor como campo numérico simple hasta la Fase 7), cambio de estado, y cierre con evidencia y costo.
  **Nota de alcance:** la vista de autogestión del rol Proveedor (ver "sus" órdenes) **queda para la Fase 7**: recién ahí existe un proveedor real vinculado a un login.

- [ ] **F3-T15 · Prueba de punta a punta — reclamos y mantenimiento.**
  **Qué se prueba:** crear un reclamo crítico desde la sesión de un residente; generar su orden de trabajo; confirmar que el reclamo pasó a `asignado` solo; asignar un encargado real; pasar la orden a `en_curso` y confirmar que el reclamo la siguió; cerrarla con evidencia y costo y confirmar que el reclamo quedó en `resuelto` y el tiempo calculado; reabrir el reclamo y confirmar que vuelve al listado de gestión; cerrarlo definitivamente y confirmar que ya no se puede reabrir. Probar además el reclamo sobre un espacio común y sobre el edificio en general.

- [ ] **F3-DOC · Documentación de la Fase 3.**
  Redactar `documentacion/fases/Fase_3_Reclamos_y_Mantenimiento.md` según la sección 1.6. Foco particular: los dos diagramas de estado lado a lado con la explicación de por qué son distintos, la tabla de sincronización paso a paso, y el cuadro de quién puede mover qué.

---

# Fase 4 — Activos y seguridad normativa

**Objetivo.** El primero de los dos pilares del diferencial competitivo: control de los elementos físicos que requieren seguimiento normativo — matafuegos, ascensores, bocas de incendio, bombas, portones, luces de emergencia — con vencimientos, QR e historial.

**Respaldo documental:** `01_Documento_General.md` (9) · `02_Documento_Tecnico.md` (3.6, 10).

**Por qué importa de verdad:** en Argentina el vencimiento de la habilitación de matafuegos, ascensores o bocas de incendio no es un tema estético — es una obligación normativa que, si no se cumple, puede dejar al edificio inhabilitado y al administrador expuesto a responsabilidad civil ante un siniestro. El relevamiento lo confirmó textualmente: *"lo llevo con recordatorios en el celular o memoria, y ahí me la juego, porque la responsabilidad legal es mía"*.

**Temas:** 4.1 Estado calculado · 4.2 Modelo y QR · 4.3 Historial · 4.4 Pantallas.

## Tema 4.1 — El estado calculado

- [ ] **F4-T01 · Lógica — `services/activos.py`, estado por vencimiento.**
  **Qué se construye:** la función pura que, dada la fecha del próximo mantenimiento y la fecha de hoy, devuelve el estado del activo: **verde** vigente, **amarillo** si vence en 30 días o menos, **rojo** si ya venció o está fuera de servicio.
  **Regla:** el estado del activo **nunca se carga a mano**, siempre se calcula.
  **Cuidado con el entorno serverless:** no hay tareas programadas. Este cálculo ocurre **al momento de la consulta**, no en un job nocturno. Cualquier funcionalidad futura que suene a *cron* se resuelve igual.
  **Listo cuando:** hay tests del borde exacto de los 30 días, del vencimiento del mismo día, y del activo sin fecha de próximo mantenimiento cargada.

## Tema 4.2 — Modelo, QR y formalización de la FK diferida

- [ ] **F4-T02 · Backend — modelos `Activo` y `ActivoFoto`.**
  **Qué se construye:** `Activo` con código único interno (por ejemplo `MAT-P3-01`, tipo + ubicación), tipo, ubicación (piso, espacio común o zona), `proveedor_id`* (entero suelto hasta la Fase 7), garantía, manual (se vincula a `Documento` en la Fase 7), próximo mantenimiento y fecha de vencimiento. `ActivoFoto` como tabla hija con URL, misma convención que `ReclamoFoto`.
  **Los costos acumulados no son una columna:** se derivan de las órdenes de trabajo y gastos asociados.

- [ ] **F4-T03 · Backend — formalizar `OrdenTrabajo.activo_id` como clave foránea real.**
  **Qué se construye:** ahora que `Activo` existe, la columna entera suelta de `F3-T06` pasa a ser una FK real con su relación.
  **Cuidado con:** la columna ya existe con datos, así que **el mecanismo de migraciones aditivas no alcanza** — solo agrega columnas, nunca restricciones sobre columnas existentes. Si la tabla ya tiene filas en la base de desarrollo, la migración se escribe a mano para este caso puntual. Es exactamente el escenario que `02_Documento_Tecnico.md` sección 6 marca como "No lo resuelve solo".

- [ ] **F4-T04 · Backend — generación del código QR al dar de alta.**
  **Qué se construye:** con la librería `qrcode`, el QR que apunta a la ficha del activo (`activos.html?id={activo_id}`), generado en el alta y recuperable desde la ficha para imprimirlo y pegarlo en el activo físico.
  **Para qué sirve de verdad:** el encargado, el inspector o el proveedor lo escanean desde el celular y abren la ficha completa sin buscar nada.

- [ ] **F4-T05 · Backend — CRUD de activos.**
  **Qué se construye:** alta, edición, listado filtrable por tipo y ubicación, y detalle — siempre con el estado **ya calculado** por `F4-T01`, nunca dejando que el frontend lo derive.

## Tema 4.3 — Historial y costos

- [ ] **F4-T06 · Backend — historial y costos acumulados de un activo.**
  **Qué se construye:** el endpoint que arma el historial consultando las órdenes de trabajo que tienen ese activo como afectado, y suma sus costos.
  **Regla:** **no es una tabla nueva.** El historial no se carga aparte: se deriva de las órdenes de trabajo.

## Tema 4.4 — Pantallas

- [ ] **F4-T07 · Frontend — `activos.html`, listado con semáforo.**
  **Qué se construye:** todos los activos del edificio con su estado visible de un vistazo y filtros por tipo y por "requieren atención". Es el anticipo, en chico, de la franja del Dashboard Visual.
  **Incluye:** un aviso destacado arriba cuando hay activos vencidos, con el detalle de cuáles — es el dato que puede dejar al edificio inhabilitado.

- [ ] **F4-T08 · Frontend — alta y edición de activo.**
  **Qué se construye:** el modal con tipo, código, ubicación, proveedor responsable, próximo mantenimiento, vencimiento y fotos.

- [ ] **F4-T09 · Frontend — ficha del activo.**
  **Qué se construye:** el panel de detalle con la ficha completa, el QR para imprimir, las fotos, el historial de intervenciones derivado de las órdenes, los costos acumulados, y el botón de generar una orden de trabajo sobre ese activo.
  **Es también el destino del escaneo del QR físico**, así que tiene que funcionar bien abierta directo desde una URL con el id en la query.

- [ ] **F4-T10 · Prueba de punta a punta — activos.**
  **Qué se prueba:** dar de alta un matafuego con vencimiento en 20 días y confirmar que queda amarillo; dar de alta un ascensor ya vencido y confirmar que queda rojo; generar desde la ficha una orden de recarga para el vencido; cerrarla cargando la nueva fecha de vencimiento; confirmar que el activo vuelve a verde solo y que la orden quedó en su historial con su costo. Escanear o abrir el QR y confirmar que lleva a la ficha correcta.

- [ ] **F4-DOC · Documentación de la Fase 4.**
  Redactar `documentacion/fases/Fase_4_Activos.md` según la sección 1.6. Foco particular: por qué el control normativo es el diferencial (con el dato de contexto del relevamiento), la regla de estado con ejemplos de fechas concretas, y cómo se usa el QR en la práctica.

---

# Fase 5 — Dashboard Visual del Edificio

**Objetivo.** La funcionalidad que ningún competidor relevado ofrece: el edificio dibujado piso por piso y departamento por departamento, coloreado según su estado real. **No se rediseña nada** — el diseño y la interacción ya están validados en el mockup aprobado y documentados en la skill. Esta fase **conecta esa plantilla a datos reales** de las Fases 2, 3 y 4.

**Respaldo documental:** `01_Documento_General.md` (4.3) · `02_Documento_Tecnico.md` (5.6, 10) · `03_Documento_Frontend.md` (6, la sección entera).

**Precondición:** Fases 2, 3 y 4 cerradas. Sin las tres fuentes de severidad, el dashboard pintaría todo verde.

**Temas:** 5.1 Severidad completa · 5.2 Endpoints · 5.3 Pantalla.

## Tema 5.1 — Severidad completa

- [ ] **F5-T01 · Lógica — severidad por deuda y regla de precedencia.**
  **Qué se construye:** en `services/severidad.py`, las dos piezas que faltaban de la Fase 3: la severidad por deuda (**más de un mes → `crit`; un mes → `warn`; sin deuda → `ok`**) y la combinación de los tres factores con la regla de precedencia — **gana el más grave: `ok` < `warn` < `pend` < `crit`**.
  **Más la "severidad según la vista":** en la vista general se combinan los tres factores; en una vista filtrada se muestra **solo** el factor de esa vista.
  **Regla que no se negocia:** el cálculo vive en el backend y viaja **ya calculado** al frontend. **Nunca se recalcula severidad en JavaScript con datos reales.** El frontend solo pinta.
  **Listo cuando:** hay tests de la precedencia con las combinaciones de dos y tres factores simultáneos, y de cada vista filtrada por separado.

## Tema 5.2 — Endpoints

- [ ] **F5-T02 · Backend — estado agregado del edificio.**
  **Qué se construye:** el endpoint que devuelve, para un edificio, la estructura completa con el estado de cada departamento bajo **cada una de las cuatro vistas** (general, incidentes, deudores, mantenimiento), más los datos mínimos que necesita cada tarjeta (identificador, resumen de qué le pasa).
  **Cuidado con el rendimiento:** es el endpoint más pesado del sistema y se consulta al abrir la pantalla principal. Se arma con consultas agregadas, no recorriendo departamento por departamento y preguntando por cada uno — el mismo criterio de `F1-T21`. Con test que cuente las consultas.

- [ ] **F5-T03 · Backend — resumen por piso.**
  **Qué se construye:** el estado dominante de cada piso (el peor entre sus departamentos), que es lo que colorea la franja del piso antes de expandirla.

- [ ] **F5-T04 · Backend — activos del edificio para la franja.**
  **Qué se construye:** la lista de activos con su estado ya calculado (Fase 4), en el formato que espera la franja de equipamiento común.

- [ ] **F5-T05 · Backend — ficha 360° de una unidad.**
  **Qué se construye:** el endpoint de detalle que confluye todos los módulos en una sola respuesta: datos de la unidad (propietario, inquilino, m², coeficiente), reclamos abiertos con su prioridad y tiempo transcurrido, órdenes de trabajo activas o recientes, activos ubicados ahí, y **el estado de expensas solo si el rol que consulta tiene permiso para verlo**.
  **Cuidado con:** el filtrado por rol se hace **acá, en el backend**, no ocultando datos en el frontend. Si el Encargado no ve montos, la respuesta no los trae.

## Tema 5.3 — La pantalla

- [ ] **F5-T06 · Frontend — `dashboard.html`, la fachada con datos reales.**
  **Qué se construye:** la jerarquía de contenedores documentada, portada tal cual, reemplazando los datos de ejemplo por las respuestas de los endpoints anteriores: contenedor del dashboard → escena → edificio (con su reflejo lateral) → techo con el nombre real y el indicador de sistema en vivo → pisos generados por JS → planta baja → franja de activos.
  **Regla:** **la arquitectura de contenedores no se improvisa.** Romperla rompe el layout responsive. Y tiene que funcionar con **cualquier** cantidad de pisos, no solo con los del mockup.
  **Detalle que no es decorativo:** el reflejo lateral del edificio simula luz rebotando en una torre de vidrio real — es la coherencia deliberada entre "edificio de vidrio" e "interfaz de vidrio".

- [ ] **F5-T07 · Frontend — selector de vista conectado.**
  **Qué se construye:** el selector segmentado General / Incidentes / Deudores / Mantenimiento conectado al endpoint de estado agregado.
  **Regla:** al cambiar de vista **se vuelve a renderizar todo**. Nunca puede quedar un color pegado de la vista anterior.

- [ ] **F5-T08 · Frontend — expansión de piso con departamentos reales.**
  **Qué se construye:** al tocar la franja de un piso se despliegan las tarjetas completas de sus departamentos, con el mismo mecanismo de acordeón ya validado.

- [ ] **F5-T09 · Frontend — panel de detalle, la ficha 360°.**
  **Qué se construye:** al seleccionar un departamento se abre el panel con la respuesta de `F5-T05`: hoja inferior en mobile, panel lateral fijo a la derecha en escritorio.
  **Regla:** es **el mismo componente conceptual** que el sidebar deslizante de `F1-T11`, no una segunda implementación. Su backdrop es transparente: solo captura el toque para cerrar, no oscurece.

- [ ] **F5-T10 · Frontend — franja de activos con datos reales.**
  **Qué se construye:** los chips de activos reales con su color, y el clic que lleva a su ficha.

- [ ] **F5-T11 · Decisión — la variante "piso completo".**
  **Qué se decide:** existe documentada una variante donde, además del color por ventana, **todo el piso** se tiñe con el color de su estado más grave, con intensidad progresiva según gravedad. Con datos reales ya conectados, se decide si se ofrece como preferencia visual configurable por el usuario o se descarta.
  **Regla:** **no se implementa por defecto sin que esta decisión se tome primero.**

- [ ] **F5-T12 · Frontend — verificación con datos variables.**
  **Qué se prueba:** que la pantalla sigue funcionando igual de bien con un edificio de 3 pisos y con uno de 12; con identificadores de departamento largos; con un edificio sin ningún activo cargado; con todas las unidades en verde y con todas en rojo. En mobile, tablet y escritorio, en ambos temas.

- [ ] **F5-T13 · Prueba de punta a punta — Dashboard Visual.**
  **Qué se prueba:** con el edificio de prueba ya cargado con deudas, reclamos y activos reales, verificar que cada departamento se pinta según la regla de precedencia; que una unidad con deuda de un mes **y** un reclamo crítico se pinta roja y no amarilla; que en la vista Deudores esa misma unidad se pinta según su deuda y nada más; que la ficha 360° trae información real y coherente con las otras pantallas; y que el Encargado no ve montos en ningún lado de esta pantalla.

- [ ] **F5-DOC · Documentación de la Fase 5.**
  Redactar `documentacion/fases/Fase_5_Dashboard_Visual.md` según la sección 1.6. Foco particular: por qué esta pantalla es el diferencial del producto, la regla de precedencia explicada con un ejemplo de una unidad que tiene tres cosas a la vez, y capturas de las cuatro vistas sobre los mismos datos.

---

# Fase 6 — Dashboard General y Analítica

**Objetivo.** La lectura agregada: los KPIs que responden "¿cómo está el edificio?" de un vistazo, y los gráficos que responden "¿cómo viene evolucionando?".

**Respaldo documental:** `01_Documento_General.md` (6.9) · `02_Documento_Tecnico.md` (10) · `03_Documento_Frontend.md` (5.4, 11) · skill `dataviz`.

**Temas:** 6.1 KPIs · 6.2 Analítica.

## Tema 6.1 — Dashboard General

- [ ] **F6-T01 · Backend — endpoint único de KPIs.**
  **Qué se construye:** un solo endpoint con todos los widgets: estado del edificio (la composición por color), estado financiero (porcentaje recaudado y morosidad), reclamos abiertos por prioridad, ranking de deudas, órdenes abiertas / en curso / programadas, riesgos normativos (activos vencidos y por vencer) y KPIs de gestión (tiempo medio de resolución, costo acumulado del mes).
  **Cuidado con:** **un solo endpoint, no ocho.** La pantalla principal no puede disparar ocho requests en serie contra una base remota.

- [ ] **F6-T02 · Backend — filtrado de detalle por rol dentro del mismo endpoint.**
  **Qué se construye:** el Encargado recibe Reclamos y Mantenimiento con el mismo detalle que un Administrador, pero el estado financiero **le llega como semáforo sin montos**.
  **Regla:** se resuelve en el backend, **no ocultando campos en el frontend**. Si el rol no puede verlo, la respuesta no lo trae.

- [ ] **F6-T03 · Frontend — grilla de KPIs en el dashboard.**
  **Qué se construye:** la composición **bento** ya documentada — 2 tarjetas grandes (estado del edificio con su barra de composición, estado financiero con su barra de progreso) más 4 métricas chicas — reemplazando los valores de ejemplo por los reales, con el layout responsive de 2 / 4 / 6 columnas.
  **Regla:** **nunca 6 tarjetas idénticas sin jerarquía.**

- [ ] **F6-T04 · Frontend — vistas del dashboard por rol.**
  **Qué se construye:** en el **mismo archivo**, las tres ramas: gestión (KPIs + Dashboard Visual), residente (su unidad, su saldo, sus reclamos, sus comunicados sin leer) y proveedor (sus órdenes asignadas).
  **Cuidado con:** el residente ve el Dashboard Visual también, pero **sin la vista Deudores** — el estado financiero de las unidades ajenas no es asunto suyo.

## Tema 6.2 — Analítica

- [ ] **F6-T05 · Backend — endpoints de series agregadas.**
  **Qué se construye:** una serie por gráfico, sobre datos ya existentes: gastos mensuales por rubro, evolución de la morosidad, recaudado contra esperado, reclamos por prioridad y mes, tiempo medio de resolución, y (cuando existan, Fase 7) ranking de proveedores y costos por activo.
  **Regla:** la agregación es responsabilidad de este módulo, no del cálculo por elemento de `F3-T09`.

- [ ] **F6-T06 · Frontend — `analitica.html`.**
  **Qué se construye:** la pantalla de gráficos, con filtro por rango de fechas y, para el Administrador General, por edificio.
  **Reglas de color, que salen de la skill `dataviz` y del sistema de diseño del proyecto:** cada gráfico de **una sola serie** usa el acento de marca — no hace falta paleta categórica. **Un eje por gráfico: nunca dos escalas superpuestas.** El semáforo se usa **únicamente** donde lo graficado *es* un estado, y siempre acompañado de etiqueta, nunca color solo. Todo gráfico tiene su vista alternativa en tabla, para que la información no dependa del color.
  **Se define acá** qué librería de gráficos liviana se adopta, y esa decisión queda como estándar del proyecto.

- [ ] **F6-T07 · Prueba de punta a punta — dashboard y analítica.**
  **Qué se prueba:** que los KPIs del Dashboard General coinciden exactamente con los números del Dashboard Visual (mismos reclamos, mismos deudores, mismos activos por vencer) y con los de la pantalla financiera; que los gráficos reflejan el historial cargado; que el Encargado no ve un solo monto; y que el residente ve su propia vista y no la de gestión.

- [ ] **F6-DOC · Documentación de la Fase 6.**
  Redactar `documentacion/fases/Fase_6_Dashboard_y_Analitica.md` según la sección 1.6. Foco particular: qué responde cada KPI y de dónde sale su número, y las reglas de color de los gráficos con el porqué.

---

# Fase 7 — Gestión documental y proveedores

**Objetivo.** Dos módulos que comparten terreno (los contratos y garantías de un proveedor viven en documental, y su historial se arma con las órdenes de trabajo ya existentes) y, sobre todo, **la fase que salda la deuda más visible del producto**: el almacenamiento real de archivos.

**Respaldo documental:** `01_Documento_General.md` (7, 8) · `02_Documento_Tecnico.md` (3.6, 10).

**Temas:** 7.1 Almacenamiento de archivos · 7.2 Documental · 7.3 Proveedores · 7.4 Cierre de las FK diferidas.

## Tema 7.1 — Almacenamiento real de archivos (la decisión postergada)

- [ ] **F7-T01 · Decisión — dónde y cómo se guardan los archivos.**
  **Qué se decide:** hasta acá toda foto, comprobante o adjunto del sistema es **un campo de URL a un archivo alojado afuera**. Es la restricción más visible del producto y este es el punto del roadmap donde deja de ser tolerable.
  **La restricción que condiciona la decisión:** el entorno serverless **no tiene disco persistente**. Guardar archivos en el filesystem de la función no es una opción: se pierden al terminar la invocación.
  **Alternativas a evaluar:** almacenamiento de objetos del propio Supabase (coherente con que la base ya está ahí, mismo proveedor, misma región), un servicio de objetos externo, o seguir con URLs externas indefinidamente.
  **Recomendación:** el almacenamiento de Supabase, por cercanía de red con la base y por no sumar un proveedor más.
  **Listo cuando:** la decisión está tomada por el usuario y escrita acá. Nada de este tema se implementa antes.

- [ ] **F7-T02 · Backend — subida de archivos.**
  **Qué se construye:** el endpoint de carga con **validación de tipo y tamaño antes de guardar**, y la devolución de la URL resultante.
  **Cuidado con:** nunca se confía en el nombre ni en el tipo declarado por el cliente.

- [ ] **F7-T03 · Backend — migrar los campos de URL existentes.**
  **Qué se construye:** los campos de URL de `ReclamoFoto`, `OtEvidencia`, `ActivoFoto` y el comprobante de `Pago` pasan a apuntar al almacenamiento propio.
  **Regla:** las URLs externas ya cargadas **siguen funcionando**. No se migran datos viejos a la fuerza; conviven.

- [ ] **F7-T04 · Frontend — componente de subida reutilizable.**
  **Qué se construye:** el componente único de carga de archivo, que reemplaza los campos de "pegá acá la URL" en las cuatro pantallas que hoy los tienen (reclamos, órdenes, activos, pagos).
  **Cuidado con:** se agrega al catálogo de componentes y a la skill, para que ninguna pantalla futura invente el suyo.

## Tema 7.2 — Gestión documental

- [ ] **F7-T05 · Lógica — tabla de visibilidad por categoría.**
  **Qué se construye:** la regla única y reutilizable de quién sube y quién ve cada categoría, tal como la fija `01_Documento_General.md` sección 7: reglamentos, actas, seguros y certificados los ven todos los residentes; contratos y documentación legal, solo Administrador General y Auditor; garantías y manuales, administración y encargado.
  **Regla:** **no se repite el chequeo a mano por categoría.** Una tabla, una función.

- [ ] **F7-T06 · Backend — modelo `Documento`.**
  **Qué se construye:** edificio, categoría (con CHECK), archivo, subido_por, fecha, y **fecha de vencimiento anulable**.
  **Por qué importa el vencimiento:** es lo que dispara el estado de atención o crítico del activo correspondiente (Fase 4). Un certificado vencido es un activo vencido.

- [ ] **F7-T07 · Backend — endpoints de carga, listado y descarga.**
  **Qué se construye:** los tres, aplicando la regla de visibilidad de `F7-T05` en una dependencia, nunca en el cuerpo del endpoint.

- [ ] **F7-T08 · Backend — vínculo de documentos con activos.**
  **Qué se construye:** el manual y el certificado de un activo pasan de ser campos sueltos a apuntar a un `Documento` real, y el vencimiento del certificado alimenta el estado del activo.

- [ ] **F7-T09 · Frontend — `documentos.html`.**
  **Qué se construye:** listado filtrable por categoría con la visibilidad real según el rol, subida si corresponde, y descarga. Los documentos con vencimiento muestran su estado con el semáforo.

## Tema 7.3 — Proveedores

- [ ] **F7-T10 · Backend — modelo `Proveedor` y formalización de las FK diferidas.**
  **Qué se construye:** nombre o razón social, contacto, horarios y **disponibilidad de emergencia**, y el campo diferencial: **exclusivo del consorcio o también atiende trabajos particulares** — algo que ningún competidor relevado ofrece de forma completa, y que le sirve directamente al vecino para contratar por su cuenta al plomero que ya conoce el edificio.
  **⚠️ Acá se cierran las claves foráneas diferidas** de `Gasto`, `Presupuesto`, `Factura` (Fase 2) y `OrdenTrabajo` (Fase 3): los cuatro `proveedor_id` sueltos pasan a FK real. **Igual que en `F4-T03`, el mecanismo de migraciones aditivas no alcanza** para agregar una restricción sobre una columna que ya tiene datos.
  **Y hay que volver a las pantallas ya construidas:** los campos de "ID de proveedor" numéricos de Gastos, Presupuestos y Órdenes pasan a ser selectores reales. No alcanza con hacerlo en las pantallas nuevas de esta fase.

- [ ] **F7-T11 · Backend — `Rubro` y la relación N:N.**
  **Qué se construye:** el catálogo de rubros (plomería, electricidad, gas, ascensores, matafuegos, jardinería, limpieza, seguridad, obras) con su tabla puente. Un proveedor puede tener varios.

- [ ] **F7-T12 · Backend — `EvaluacionProveedor`.**
  **Qué se construye:** la evaluación formal posterior a cada orden cerrada (cumplimiento de plazo, calidad, prolijidad) que alimenta la calificación general.
  **Por qué formal y no una opinión suelta:** queda como antecedente objetivo para decidir si se lo vuelve a contratar.

- [ ] **F7-T13 · Backend — CRUD, historial y calificación.**
  **Qué se construye:** alta y edición, listado filtrable por rubro y por exclusivo/particular, el historial de intervenciones (**armado sobre las órdenes de trabajo y los presupuestos, no es tabla nueva**) y el recálculo del promedio al registrar una evaluación.

- [ ] **F7-T14 · Backend — vista de autogestión del rol Proveedor.**
  **Qué se construye:** ahora que existe un proveedor real vinculable a un login, el endpoint que le devuelve **sus** órdenes asignadas — la deuda que quedó abierta en `F3-T14`.

- [ ] **F7-T15 · Frontend — `proveedores.html`.**
  **Qué se construye:** listado con filtros, ficha con contacto, calificación, historial y presupuestos, y alta y edición incluyendo el campo diferencial.

- [ ] **F7-T16 · Frontend — vista del proveedor en Mantenimiento.**
  **Qué se construye:** la rama del rol Proveedor en `mantenimiento.html`: sus órdenes, con carga de evidencia y cambio de estado. Su alcance es **solo eso**; no accede a nada más del edificio.

- [ ] **F7-T17 · Prueba de punta a punta — documental y proveedores.**
  **Qué se prueba:** subir un archivo real (no una URL) y confirmar que se guarda y se descarga; subir un reglamento y confirmar que lo ven todos, y un contrato y confirmar que solo lo ven Administrador General y Auditor; cargar un certificado con vencimiento próximo y confirmar que el activo vinculado pasa a amarillo; dar de alta un proveedor "también atiende particulares", vincularlo a una orden cerrada, evaluarlo y confirmar que su calificación e historial se actualizan; entrar con el login del proveedor y confirmar que ve sus órdenes y nada más.

- [ ] **F7-DOC · Documentación de la Fase 7.**
  Redactar `documentacion/fases/Fase_7_Documental_y_Proveedores.md` según la sección 1.6. Foco particular: cómo quedó resuelto el almacenamiento de archivos y por qué se eligió esa opción, la tabla de visibilidad documental completa, y el listado de las claves foráneas que esta fase formalizó.

---

# Fase 8 — Comunicación interna y reservas

**Objetivo.** Los dos módulos de comunidad: el que resuelve "no hay forma de saber si el aviso llegó a todos" y el que ordena el uso de los espacios comunes.

**Respaldo documental:** `01_Documento_General.md` (1.4, 2.1) · `02_Documento_Tecnico.md` (3.6, 10).

**Temas:** 8.1 Reservas · 8.2 Comunicados.

## Tema 8.1 — Reservas de espacios comunes

- [ ] **F8-T01 · Lógica — validación de solapamiento.**
  **Qué se construye:** la función pura que, dado un espacio, una fecha y un rango horario, determina si se superpone con una reserva existente, contemplando las reglas del edificio (turnos mínimos y máximos, horario permitido, anticipación mínima para cancelar).
  **Cuidado con los bordes:** una reserva que termina a las 16:00 y otra que empieza a las 16:00 **no** se solapan. El test tiene que cubrir ese caso exacto, más el de una reserva que contiene a otra por completo.

- [ ] **F8-T02 · Backend — modelo `Reserva` y endpoints.**
  **Qué se construye:** espacio común (Fase 1), usuario, fecha, horario, estado; alta validando el solapamiento, consulta de disponibilidad en un rango, y cancelación respetando el tiempo mínimo configurado.

- [ ] **F8-T03 · Frontend — `reservas.html`.**
  **Qué se construye:** selección de espacio, vista de disponibilidad de la semana, formulario de reserva, y listado de las reservas propias con opción de cancelar. Las reglas de uso de cada espacio quedan visibles al elegirlo.

## Tema 8.2 — Comunicados

- [ ] **F8-T04 · Backend — modelo `Comunicado` y su segmentación.**
  **Qué se construye:** título, cuerpo, autor, fecha, prioridad y **alcance**: todo el edificio, un piso, o una unidad.
  **Por qué segmentar importa:** evita el ruido. Un aviso de obra en el piso 1 no tiene por qué llegarle a los 32 departamentos, y el aviso que le llega a todo el mundo sin distinción termina siendo el que nadie lee.

- [ ] **F8-T05 · Backend — registro de lectura por usuario.**
  **Qué se construye:** la tabla que registra quién abrió cada comunicado.
  **Qué problema resuelve:** el más votado del relevamiento — no había forma de saber si un aviso importante realmente llegó a todos los vecinos. Ahora el emisor ve la cobertura real.

- [ ] **F8-T06 · Backend — endpoints de comunicados.**
  **Qué se construye:** publicar con alcance, listar según a quién le corresponde verlo, marcar como leído, y la cobertura de lectura para quien lo emitió.

- [ ] **F8-T07 · Frontend — `comunicados.html`.**
  **Qué se construye:** en el mismo archivo, las dos vistas: la del residente (feed cronológico con indicador de sin leer) y la de quien emite (alta con selector de alcance, más la barra de cobertura de lectura por comunicado).

- [ ] **F8-T08 · Prueba de punta a punta — reservas y comunicados.**
  **Qué se prueba:** reservar un espacio y después intentar reservar el mismo horario desde otra unidad, confirmando que se rechaza por solapamiento; reservar el turno contiguo exacto y confirmar que **sí** se permite; publicar un comunicado segmentado a un piso puntual y confirmar que solo los usuarios de ese piso lo reciben; abrirlo desde una de esas cuentas y confirmar que la cobertura de lectura se actualiza.

- [ ] **F8-DOC · Documentación de la Fase 8.**
  Redactar `documentacion/fases/Fase_8_Comunicacion_y_Reservas.md` según la sección 1.6. Foco particular: la regla de solapamiento con ejemplos horarios, y cómo se lee la cobertura de un comunicado.

---

# Fase 9 — Módulo de seguridad

**Objetivo.** Registro de incidentes y bitácora operativa. **Gestión de información, no integración de hardware** — cámaras y control de accesos están explícitamente fuera de alcance.

**Respaldo documental:** `01_Documento_General.md` (1.4) · `02_Documento_Tecnico.md` (3.6, 10).

- [ ] **F9-T01 · Backend — modelo `IncidenteSeguridad`.**
  **Qué se construye:** tipo, descripción, fecha, registrado_por, ubicación y gravedad con **el mismo esquema leve / medio / crítico que los reclamos** — no se inventa una escala nueva.

- [ ] **F9-T02 · Backend — modelo `Bitacora`.**
  **Qué se construye:** el registro diario operativo del encargado y del personal de seguridad: hora, entrada de texto, autor, turno.

- [ ] **F9-T03 · Backend — endpoints de incidentes y bitácora.**
  **Qué se construye:** alta, listado por rango de fechas y detalle, con el control de acceso correspondiente (seguridad y encargado cargan; administración y auditor leen).

- [ ] **F9-T04 · Backend — botón de emergencia.**
  **Qué se construye:** el endpoint que genera automáticamente un incidente de gravedad crítica y dispara el aviso reutilizando el mecanismo de comunicados de la Fase 8.
  **Regla de alcance:** **es un registro de alta prioridad, sin integración con servicios externos.** No llama a nadie, no manda SMS: deja constancia inmediata con hora, responsable y ubicación, y avisa dentro de la plataforma.

- [ ] **F9-T05 · Frontend — `seguridad.html`, incidentes y bitácora.**
  **Qué se construye:** en el mismo archivo, las dos pestañas: carga y listado de incidentes, y la bitácora del turno en vista cronológica.

- [ ] **F9-T06 · Frontend — botón de emergencia.**
  **Qué se construye:** el botón, con **confirmación explícita antes de activarse** usando el patrón de `F1-T15`, para evitar toques accidentales. El mensaje dice exactamente qué va a pasar al activarlo.

- [ ] **F9-T07 · Prueba de punta a punta — seguridad.**
  **Qué se prueba:** activar el botón de emergencia desde una cuenta de personal de seguridad y confirmar que se generó el incidente crítico con su hora exacta, que aparece en la bitácora del turno, y que el aviso llegó a quien corresponde. Cargar un incidente común y confirmar que un residente no puede verlo.

- [ ] **F9-DOC · Documentación de la Fase 9.**
  Redactar `documentacion/fases/Fase_9_Seguridad.md` según la sección 1.6. Foco particular: qué hace y qué **no** hace el botón de emergencia, para que no se espere de él algo que está fuera de alcance.

---

# Fase 10 — Inteligencia artificial

**Objetivo.** La capa de asistencia. **Se ubica al final a propósito:** recién ahora los módulos base tienen datos reales sobre los que operar. Una IA sin datos es una demo.

**Respaldo documental:** `01_Documento_General.md` (1.4, 4.3) · `02_Documento_Tecnico.md` (10).

- [ ] **F10-T01 · Decisión — proveedor de modelo de lenguaje.**
  **Qué se decide:** cuál se usa, evaluando costo, límites de uso y facilidad de integración. **La decisión se toma en esta fase, no antes.**
  **Regla de diseño:** se aísla en `services/ia.py` para poder cambiar de proveedor sin tocar el resto del sistema.

- [ ] **F10-T02 · Backend — reglas de negocio y validación de seguridad del asistente.**
  **Qué se construye, antes que cualquier funcionalidad de IA:** la traducción al asistente de las mismas reglas de negocio del resto del sistema (qué es "deuda vencida", la precedencia de colores, qué significa cada prioridad) y la validación de que **toda consulta generada sea de solo lectura y respete el alcance y los permisos de quien pregunta**.
  **Regla dura:** un propietario **no puede** obtener por esta vía datos de otro departamento. Esta tarea va primero, no última: es la que evita que la capa de IA se convierta en una puerta trasera que saltea toda la autorización construida en nueve fases.
  **Listo cuando:** hay tests que intentan, desde cada rol, obtener datos fuera de su alcance y confirman que el asistente los rechaza.

- [ ] **F10-T03 · Backend — clasificación y priorización de reclamos.**
  **Qué se construye:** al crear un reclamo, sugiere rubro y prioridad.
  **Regla:** **sugiere, nunca decide.** El administrador confirma o corrige, y lo que queda guardado es lo que él eligió.

- [ ] **F10-T04 · Backend — generación asistida de comunicados.**
  **Qué se construye:** a partir de una idea breve en lenguaje natural, redacta un borrador de comunicado que **siempre** se revisa antes de publicar.

- [ ] **F10-T05 · Backend — búsqueda inteligente sobre la documentación.**
  **Qué se construye:** preguntas en lenguaje natural sobre los documentos cargados en la Fase 7, respetando la tabla de visibilidad por categoría.
  **Cuidado con:** si un usuario no puede ver un contrato, el asistente tampoco puede citárselo ni resumírselo.

- [ ] **F10-T06 · Frontend — sugerencia en el formulario de reclamo.**
  **Qué se construye:** integrada en la pantalla existente, como sugerencia **editable** y claramente marcada como sugerencia.

- [ ] **F10-T07 · Frontend — borrador asistido en Comunicados.**
  **Qué se construye:** integrado en la pantalla existente, con el borrador cargado en el formulario para editarlo antes de publicar.

- [ ] **F10-T08 · Frontend — búsqueda en Documentación.**
  **Qué se construye:** integrada en la pantalla existente, con las fuentes citadas — nunca una respuesta sin decir de qué documento salió.

- [ ] **F10-T09 · Prueba de punta a punta — IA.**
  **Qué se prueba:** crear un reclamo típico de plomería y confirmar que la sugerencia de rubro y prioridad es razonable y editable; generar un comunicado a partir de una idea breve; y, lo más importante, **pedir desde una cuenta de propietario un dato de otro departamento y confirmar que el asistente lo rechaza en vez de responder**.

- [ ] **F10-DOC · Documentación de la Fase 10.**
  Redactar `documentacion/fases/Fase_10_Inteligencia_Artificial.md` según la sección 1.6. Foco particular: qué decide la IA y qué no, y cómo se garantiza que no puede saltear los permisos.

---

# Fase 11 — Configuración avanzada, permisos por excepción y auditoría

**Objetivo.** Cerrar las decisiones que se postergaron deliberadamente durante todo el proyecto.

**Respaldo documental:** `01_Documento_General.md` (3.2, 12) · `02_Documento_Tecnico.md` (4.2, 7).

- [ ] **F11-T01 · Backend — permisos por excepción sobre el RBAC.**
  **Qué se construye:** la tabla de excepciones que se consulta **antes** de la regla de rol, sin rediseñar el sistema de permisos.
  **El caso de uso concreto que la motiva:** un edificio donde el propietario decide que su inquilino **no** vea nada financiero, cuando el comportamiento por defecto del sistema es que sí lo vea. Es la excepción, no la regla: la decisión adoptada de `01` sección 3.1 se mantiene como comportamiento por defecto.
  **Cuidado con:** la consulta de excepciones se resuelve en la dependencia de autorización, no repartida por los endpoints.

- [ ] **F11-T02 · Backend — parámetros generales de la plataforma.**
  **Qué se construye:** los valores por defecto para edificios nuevos (días de vencimiento, recargo por mora, umbral de aviso de vencimiento de activos), configurables por el Administrador General.

- [ ] **F11-T03 · Backend — registro de auditoría.**
  **Qué se construye:** el registro de quién y cuándo, para las operaciones sensibles ya construidas: regenerar una expensa, confirmar o rechazar un pago, cambiar el estado de un reclamo, dar de alta o desactivar un usuario, modificar coeficientes.
  **Regla:** es material de trabajo del rol Auditor, y es de **solo lectura para todos**, incluido el Administrador General. Un registro de auditoría editable no sirve como registro.

- [ ] **F11-T04 · Frontend — `configuracion.html`, pestañas Parámetros y Roles.**
  **Qué se construye:** los parámetros generales y la pantalla de excepciones por usuario, ambas solo para Administrador General.

- [ ] **F11-T05 · Frontend — pestaña Auditoría y cierre del alcance del Auditor.**
  **Qué se construye:** la vista de auditoría de solo lectura, y **la resolución definitiva del vínculo Auditor ↔ edificio** según lo que se haya decidido en `F1-T02`.
  **⚠️ Y hay que volver atrás:** una vez resuelto, revisar las dependencias de autorización de todo el módulo financiero para que acepten al Auditor de solo lectura, y habilitar su acceso a las pantallas ya construidas — empezando por Deudores (`F2-T20`).

- [ ] **F11-T07 · Backend — ampliar el módulo de usuarios al Administrador de Consorcio.**
  **De dónde viene:** es la deuda que dejó abierta `F1-T08` al cerrar la Fase 1. El módulo de usuarios quedó **solo para el Administrador General**, y no por olvido: cuando se construyó (`F1-T09`) el alcance todavía no existía, y la elección real era dejarlo así o darle el acceso al Administrador de Consorcio **sin poder limitarlo** — que no es un filtro parcial, es que vea y edite los usuarios de todos los consorcios de la plataforma, incluidos los administradores de los otros. Entre un permiso que falta y un permiso de más, falta.
  **Qué se construye:** el listado, el alta y la edición de usuarios filtrados por el alcance de quien consulta. Un Administrador de Consorcio ve y da de alta a las personas **de sus edificios**: los propietarios e inquilinos de sus unidades, su encargado, su personal de seguridad.
  **La regla que hace falta primero, y es la razón por la que esta tarea está en esta fase y no en la 1:** *nadie puede crear ni asignar un rol de más permisos que el propio.* Sin eso, el alta es una **escalada de privilegios**: un Administrador de Consorcio que puede dar de alta usuarios se da de alta a sí mismo un Administrador General. La regla es del mismo tipo que las dos de `F1-T09` —nadie se desactiva a sí mismo, nadie se cambia el rol a sí mismo— y cierra la familia: con las tres juntas, ningún camino lleva a un sistema sin administrador ni a un usuario con más permisos de los que le dieron.
  **Lo que ya está y no hay que rehacer:** `core/alcance.py` (`F1-T23`) con las dos funciones del alcance, y `GET /api/edificios/{id}/asignables` (`F1-T26`), que ya resuelve "qué personas puede asignar este administrador en este edificio" y es la mitad de esta consulta vista desde el otro lado.
  **Cuidado con:** el listado filtrado tiene que seguir mostrando a los **inactivos** —reactivar a alguien de baja es parte del trabajo del administrador— y un usuario fuera del alcance tiene que contestar **404 y no 403**, igual que un edificio ajeno: con un 403 se puede tantear qué ids existen.
  **Listo cuando:** hay test de que un Administrador de Consorcio ve a las personas de sus edificios y **no** a las de un edificio ajeno; de que no puede crear ni asignar `admin_general` (ni ningún rol de más permisos que el propio); de que un id fuera de su alcance da 404; y de que el Administrador General sigue viendo todo como hasta ahora.

- [ ] **F11-T06 · Prueba de punta a punta — permisos y auditoría.**
  **Qué se prueba:** crear una excepción que le quite a un inquilino puntual el acceso financiero de su unidad y confirmar que la pierde, mientras otro inquilino sin la excepción la conserva; ejecutar una acción sensible y confirmar que aparece en la auditoría con el usuario y la hora correctos; entrar como Auditor y confirmar que ve el financiero del edificio y **no puede editar nada en ninguna pantalla**. Y, por `F11-T07`: entrar como Administrador de Consorcio, dar de alta un propietario de su edificio, confirmar que **no puede** crear un Administrador General, y confirmar que no ve a las personas de un edificio ajeno.

- [ ] **F11-DOC · Documentación de la Fase 11.**
  Redactar `documentacion/fases/Fase_11_Permisos_y_Auditoria.md` según la sección 1.6. Foco particular: el modelo de permisos completo y final (rol + excepción), y qué operaciones quedan auditadas.

---

# Fase 12 — Pulido de frontend, build de producción y heurísticas de UX

**Objetivo.** Cerrar la calidad de la interfaz: build real, accesibilidad, PWA, y las heurísticas de usabilidad que quedaron identificadas como faltantes.

**Respaldo documental:** `03_Documento_Frontend.md` (9, 12) · `02_Documento_Tecnico.md` (1.2).

**Temas:** 12.1 Build y rendimiento · 12.2 Heurísticas de UX pendientes · 12.3 Accesibilidad y PWA.

## Tema 12.1 — Build y rendimiento

- [ ] **F12-T01 · Frontend — revisión de peso y carga de los assets.**
  **Qué se revisa:** que las dos hojas propias sigan siendo chicas y sin reglas muertas después de doce fases, y el costo de la única dependencia externa que queda en el frontend — las fuentes de Google. Se evalúa servirlas desde el propio proyecto para no depender de un CDN en un entorno sin conexión.
  **Nota:** esta tarea reemplaza a la migración de Tailwind CDN a CLI que estaba planificada acá. Al sacarse Tailwind del proyecto (decisión del 2026-09-27) dejó de existir el paso de compilación que había que migrar.
  **Listo cuando:** no hay parpadeo de estilos sin aplicar al cargar ninguna pantalla, y el peso total de CSS está medido y anotado.

- [ ] **F12-T02 · Frontend — revisión de rendimiento percibido.**
  **Qué se revisa:** el costo de composición de varias capas de vidrio apiladas. Hubo un reporte real de animaciones lentas en Chrome y fluidas en Firefox; el disparador puntual (el barrido circular del toggle de tema) ya está descartado desde `F0-T13`, así que acá se confirma si el síntoma persiste sin esa animación de por medio y, si persiste, se reduce la cantidad de capas simultáneas.

## Tema 12.2 — Heurísticas de UX pendientes

> Estas seis salen del análisis de heurísticas de usabilidad y son trabajo real, no verificación. Las otras diez ya quedan cubiertas por decisiones de diseño tomadas en fases anteriores; el detalle está en la Fase X.

- [ ] **F12-T03 · Deshacer para acciones reversibles.**
  **Qué se construye:** un aviso temporal con botón de "Deshacer" (unos segundos) para las acciones reversibles más comunes, empezando por activar/desactivar un usuario y asignar o desvincular un departamento.
  **Por qué esas primero:** la desactivación de usuario ya provocó un incidente real. Es la acción que más resguardo necesita, no menos.

- [ ] **F12-T04 · Protección del trabajo del usuario.**
  **Qué se construye:** aviso de confirmación al intentar cerrar un modal con campos ya completados, y reintento automático en el envoltorio de `fetch` ante una falla de red puntual, antes de mostrarle el error al usuario.

- [ ] **F12-T05 · Ayuda contextual.**
  **Qué se construye:** un acceso de ayuda en el topbar que abre los pasos concretos de la tarea de **esa** pantalla ("cómo generar una expensa", "cómo cargar un pago"). Una lista corta de pasos, nunca un manual extenso.

- [ ] **F12-T06 · Flexibilidad para el usuario frecuente.**
  **Qué se construye:** recordar el último filtro usado al volver a una pantalla (período en Gastos, estado en Reclamos) mediante `localStorage`, y accesos rápidos de teclado en las pantallas de mayor uso.

- [ ] **F12-T07 · Anticipación.**
  **Qué se construye:** sugerir el próximo período a liquidar en Generar expensa (**el mes siguiente al de la última expensa generada**, no siempre el mes calendario actual) y avisar proactivamente de vencimientos próximos en el dashboard del rol correspondiente.

- [ ] **F12-T08 · Registro del estado de sesión.**
  **Qué se construye:** recordar la última pantalla visitada para volver ahí al iniciar sesión, en vez de mandar siempre al dashboard, y distinguir el primer ingreso de un usuario para darle una bienvenida distinta.

## Tema 12.3 — Accesibilidad, PWA y cierre visual

- [ ] **F12-T09 · Auditoría de consistencia con el sistema de diseño.**
  **Qué se revisa, pantalla por pantalla:** que ningún color, sombra o vidrio tenga un valor fijo suelto; que no haya aparecido ningún componente inventado fuera del catálogo; que las dos hojas y la skill sigan diciendo lo mismo.
  **Regla de sincronización:** si una regla cambió en el código, cambia también en `03_Documento_Frontend.md` y en la skill. Son dos formatos del mismo contrato, no dos fuentes de verdad.

- [ ] **F12-T10 · Auditoría de accesibilidad.**
  **Qué se revisa:** contraste de texto suficiente en ambos temas (verificación formal, no a ojo); `aria-label` en todo botón de solo ícono; `<label for>` real en todo campo; foco visible siempre, nunca un `outline` eliminado sin reemplazo; navegación completa por teclado en los componentes interactivos; y que las animaciones respeten la preferencia de movimiento reducido del sistema.

- [ ] **F12-T11 · Decisión pendiente — el texto de marca animado.**
  **Qué se decide:** el degradé animado sobre la segunda palabra de la marca quedó, en la iteración anterior, con la paleta original del componente de referencia — que incluye rosa y violeta, **prohibidos por el sistema de diseño**. Se dejó así a pedido explícito, "para ver cómo queda".
  **Hay que cerrarlo:** o se confirma como excepción deliberada y se documenta como tal en la skill, o vuelve al acento de marca. No puede quedar como una violación silenciosa de la regla.

- [ ] **F12-T12 · PWA — manifiesto y Service Worker básico.**
  **Qué se construye:** el manifiesto (nombre, íconos, colores de tema y fondo tomados de los tokens) y un Service Worker mínimo de cacheo de assets estáticos, para poder instalar la aplicación en el celular.
  **Alcance:** primera capa de uso offline. **La sincronización offline de datos queda fuera de alcance.**

- [ ] **F12-T13 · Prueba de punta a punta — pulido.**
  **Qué se prueba:** que el sitio se ve y funciona igual tras la migración del CSS, sin parpadeo; que el tema persiste al navegar entre todas las pantallas; que la aplicación se instala desde el navegador mobile; que deshacer funciona en las acciones donde se implementó; y un recorrido completo por todas las pantallas con teclado solamente.

- [ ] **F12-DOC · Documentación de la Fase 12.**
  Redactar `documentacion/fases/Fase_12_Pulido_y_PWA.md` según la sección 1.6. Foco particular: qué cambió para el usuario final y el estado final de la auditoría de accesibilidad.

---

# Fase 13 — Cierre y puesta en producción

**Objetivo.** No agrega funcionalidad: deja el proyecto listo para un primer edificio real.

**Respaldo documental:** `02_Documento_Tecnico.md` (7) · `04_Infraestructura.md` (entero).

- [ ] **F13-T01 · Verificar el estado del esquema de produccion.**
  **Nota (2026-09-27):** la decision y el vaciado se adelantaron a `F05-T01`. Esta tarea queda como la verificacion final de que el esquema de produccion coincide con los modelos despues de trece fases.
  **Contenido original, que se conserva como referencia:**
  **⚠️ Esta tarea va primero de la fase y bloquea a las demás.** La base de producción **conserva el esquema y los datos del código eliminado**. Como los dos mecanismos de evolución del esquema son **puramente aditivos**, desplegar la reimplementación contra esa base **no va a corregir ninguna diferencia**: una tabla modelada distinto queda con su forma vieja, **sin error visible**.
  **Qué se decide:** vaciar el esquema y dejar que la aplicación lo recree desde cero (recomendado, y es lo que sugiere `04_Infraestructura.md` sección 3), o auditar tabla por tabla las diferencias.
  **Listo cuando:** la decisión está tomada, ejecutada y verificada contra la base real.

- [ ] **F13-T02 · Infraestructura — revision final del despliegue.**
  **Nota (2026-09-27):** el vinculo con el repositorio y las variables de entorno se adelantaron a `F05-T04`. Aca se revisa que todo siga correcto antes del cierre.
  **Qué se hace:** recrear el vínculo entre el repositorio nuevo y el proyecto de Vercel (quedó huérfano al borrarse el repositorio anterior), verificar las variables de entorno que siguen vivas, y **confirmar que la región del backend coincide con la de la base** — si están en continentes distintos se paga un costo fijo de cientos de milisegundos por request, incluso sin ninguna consulta de por medio.

- [ ] **F13-T03 · Seguridad — rol de base de datos de mínimo privilegio.**
  **Qué se construye:** un rol dedicado en Supabase con permiso de lectura y escritura **solo** sobre las tablas de la aplicación, y la cadena de conexión de producción apuntando a él en vez de al rol por defecto del proyecto.

- [ ] **F13-T04 · Revisión de seguridad general.**
  **Qué se revisa:** autorización por rol de **todos** los endpoints construidos; validación de entrada en el borde; que ningún dato sensible quede expuesto; que la documentación interactiva esté efectivamente apagada en producción; que CORS no tenga comodín; que el secreto de producción no sea el de desarrollo.
  **Incluye una pasada formal contra OWASP Top 10** y una revisión explícita de las decisiones de arquitectura que sostienen la seguridad (JWT sin estado, whitelist de CORS, secretos por variable de entorno), en vez de darlas por buenas porque se tomaron sobre la marcha.

- [ ] **F13-T05 · Evaluación de amenazas y riesgo.**
  **Qué se hace:** el assessment básico de amenazas — qué pasaría si se filtrara un token, si un administrador consultara el edificio de otro, si alguien cargara un archivo malicioso. La fuga de datos más probable de este sistema es **un administrador viendo el edificio de otro**, y por eso la validación de pertenencia es una dependencia obligatoria en todo endpoint que devuelve datos de un edificio.

- [ ] **F13-T06 · Pruebas de carga básicas.**
  **Qué se prueba:** que la plataforma responde bien con varios edificios y usuarios simultáneos, no solo con el edificio de prueba usado durante todo el desarrollo. Con atención particular a los endpoints agregados (Dashboard Visual, KPIs), que son los más pesados.

- [ ] **F13-T07 · Documentación de despliegue.**
  **Qué se escribe:** el paso a paso completo, **completando y manteniendo actualizado `04_Infraestructura.md`**, que ya documenta los recursos existentes y el checklist del primer despliegue. Esta tarea lo completa, no lo reemplaza.

- [ ] **F13-T08 · Manual de uso para el Administrador de Consorcio.**
  **Qué se escribe:** la guía breve de las tareas del día a día — generar expensas, conciliar pagos, gestionar reclamos, dar de alta activos. **Se construye reutilizando los documentos de fase** ya escritos en cada `FN-DOC`, que están redactados justamente en lenguaje natural con ejemplos.

- [ ] **F13-T09 · Piloto con un edificio real.**
  **Qué se hace:** antes de escalar, probar la plataforma completa con un edificio real y su administrador, para levantar ajustes finales con feedback real.
  **Qué mirar de cerca:** las dos advertencias del relevamiento — que la plataforma **reemplace el circuito informal en vez de duplicarlo** (si cargar un gasto cuesta más tiempo del que ahorra, se abandona al mes) y que el registro sirva efectivamente como antecedente.

- [ ] **F13-DOC · Documentación de cierre del proyecto.**
  Redactar `documentacion/fases/Fase_13_Cierre.md` según la sección 1.6, más un índice que enlace los trece documentos de fase anteriores como recorrido completo del sistema.

---

# Fase X — Verificación de requisitos de facultad

**No es una fase de desarrollo.** No sigue el orden lógica → backend → frontend ni agrega funcionalidad: es el **checklist de los requisitos que pide la facultad**, verificado uno por uno contra lo efectivamente construido.

**Estado al 2026-09-27, con las Fases 0 y 0.5 cerradas: 6 de 19 requisitos cumplidos y verificados**, 3 parciales y 10 pendientes. Los cumplidos llevan su evidencia concreta escrita abajo, con la fecha de verificación.

**Cómo se reparte el trabajo que falta.** La mayoría de estos requisitos no son tareas separadas: son **propiedades del código** que cada fase tiene que construir bien desde el principio (el control de acceso, las contraseñas robustas, la validación de entrada). Esos ya están dentro de las tareas de sus fases y no se pueden dejar para el final sin reescribir. Lo que sí corresponde al final es la **verificación formal** — el barrido de OWASP, el assessment de amenazas, la auditoría de contraste, el recorrido responsive completo — porque necesita el sistema terminado para tener sentido.

> **Cómo cambió respecto de la versión anterior de este documento.** Antes, 15 de estos puntos estaban escritos como "Ya cumplido", describiendo código de la iteración eliminada. Ahora cada punto dice **dónde** se cumple en este Roadmap, y se verifica contra el código real en el momento de ejecutarlo. Los siete puntos que eran trabajo real ya no viven acá: se movieron a la fase donde corresponden, y esta fase solo los verifica.

## Requisitos generales

- [ ] **FX-T01 · Sistema transaccional sobre base relacional.**
  **Dónde se cumple:** backend completo con transacciones explícitas — por ejemplo, la generación de una expensa (`F2-T05`): si el prorrateo falla a mitad de camino se hace rollback y no queda nada a medio crear. SQLite en desarrollo, PostgreSQL en producción.
  **Qué se verifica:** que existe al menos un caso documentado de rollback real, probado.
  **Estado al 2026-09-27: parcial.** La base relacional ya esta en los dos entornos (SQLite y PostgreSQL) y las sesiones se abren sin autocommit, asi que toda operacion es transaccional por defecto. Lo que falta es el **caso de rollback documentado**, y llega con la generacion de expensas (`F2-T05`): es la primera operacion del sistema que escribe varias tablas en una sola transaccion.

- [x] **FX-T02 · Herramienta de mapeo objeto-relacional.**
  **Dónde se cumple:** SQLAlchemy en el 100% de los modelos y consultas, desde `F0-T05`.
  **Qué se verifica:** que no hay SQL crudo armado a mano en ninguna parte, con la única excepción del mecanismo de migraciones, que compone DDL a partir de la metadata de los propios modelos.
  **Evidencia (2026-09-27):** en todo `backend/app/` hay **una sola** llamada a `execute()` con SQL en texto, en `core/migraciones.py`, y su sentencia se compone a partir de la metadata de los propios modelos y del escapador de identificadores del motor — nunca de un dato de usuario. Todo lo demas pasa por SQLAlchemy.
  **Verificado el 2026-09-27**, con la Fase 0.5 cerrada. Se re-verifica en `FX-DOC` al cierre del proyecto, porque es una propiedad que hay que mantener a lo largo de todas las fases.

- [ ] **FX-T03 · Diseño web adaptable.**
  **Dónde se cumple:** mobile-first real en todo el sistema de diseño, con dos quiebres y **un solo maquetado**.
  **Qué se verifica:** un recorrido por todas las pantallas construidas en 390, 768 y 1280 px, sin desborde horizontal en ninguna.
  **Estado al 2026-09-27: parcial.** El sistema ya esta: hoja mobile-first con dos quiebres (480 px para pares de campos, 1024 px para el salto a escritorio) y un solo maquetado. Pero hay **una sola pantalla construida**, asi que el recorrido completo solo se puede hacer al final. Cada tarea de frontend lo verifica en su momento, y `FX-T03` consolida.

- [ ] **FX-T04 · API de autenticación.**
  **Dónde se cumple:** `F1-T07` (login y sesión) y `F1-T08` (la dependencia que valida el token en cada request).
  **Qué se verifica:** que las contraseñas están hasheadas en la base, que un token expirado se rechaza, y que un usuario desactivado no puede seguir operando con un token todavía vigente.

- [ ] **FX-T05 · Otra API externa (geolocalización).**
  **Dónde se cumple:** `F1-T25` — geocodificación con Nominatim (OpenStreetMap) y mapa con Leaflet, sin API key ni facturación.
  **Qué se verifica:** que funciona con una dirección real y que, si no la encuentra, avisa sin bloquear el alta.

## Lineamientos de seguridad informática

- [ ] **FX-T06 · Control de acceso basado en permisos.**
  **Dónde se cumple:** `F1-T01` (la matriz), `F1-T08` y `F3-T04` (las dependencias).
  **Qué se verifica:** que **ningún** endpoint queda sin dependencia de autorización, y que la decisión se toma siempre por rol y relación real con el edificio, nunca por lo que el frontend decide mostrar u ocultar.

- [ ] **FX-T07 · Autenticación contra un dominio de base de datos.**
  **Dónde se cumple:** `F1-T07`. No hay usuarios ni contraseñas escritas en el código.
  **El matiz a documentar, no a corregir:** el enunciado sugiere "preferentemente separado del dominio de la aplicación" (un directorio tipo LDAP aparte). Acá la autenticación vive en la misma base. Para el tamaño y alcance de este proyecto no se justifica separarlos — **se documenta como decisión consciente**, no como una carencia.

- [ ] **FX-T08 · Accesos otorgados por rol.**
  **Dónde se cumple:** `F1-T01`. Ningún permiso se asigna a un usuario puntual; todo pasa por su rol, más su vínculo real con el edificio o la unidad. La única excepción es el mecanismo de `F11-T01`, que es deliberado y auditable.

- [ ] **FX-T09 · Contraseñas robustas.**
  **Dónde se cumple:** `F1-T05` (backend, la garantía real) y `F1-T13` (el reflejo en el frontend).
  **Qué se verifica:** que el backend rechaza una contraseña débil aunque el frontend la deje pasar.

- [x] **FX-T10 · Rutas sin extensión de script expuesta.**
  **Dónde se cumple:** por diseño de FastAPI, todas las rutas son limpias. No hay forma de inferir el lenguaje o el framework desde una URL.
  **Evidencia (2026-09-27):** la unica ruta publicada es `/api/salud`. No hay extension de archivo en ninguna URL del sistema, asi que no se puede inferir el lenguaje ni el framework.
  **Verificado el 2026-09-27**, con la Fase 0.5 cerrada. Se re-verifica en `FX-DOC` al cierre del proyecto, porque es una propiedad que hay que mantener a lo largo de todas las fases.

- [x] **FX-T11 · Errores no visibles por pantalla.**
  **Dónde se cumple:** la aplicación nunca se instancia en modo depuración; un error no manejado devuelve un 500 genérico, jamás el traceback.
  **Qué se verifica:** revisar uno por uno los mensajes de error que sí muestran texto y confirmar que **todos** son mensajes de negocio redactados a mano, nunca el texto crudo de una excepción que pueda filtrar estructura interna.
  **Cómo se vuelve verificable de una sola lectura:** `F1-T29` junta todos esos textos en `core/errores.py`, así que auditar esta regla pasa de recorrer cuarenta endpoints a leer un archivo.
  **Evidencia (2026-09-27):** no existe ni una aparicion de `debug=True` en el codigo. Probado contra produccion: una ruta inexistente devuelve `{"detail":"Not Found"}`, sin traceback ni estructura interna.
  **Verificado el 2026-09-27**, con la Fase 0.5 cerrada. Se re-verifica en `FX-DOC` al cierre del proyecto, porque es una propiedad que hay que mantener a lo largo de todas las fases.

- [x] **FX-T12 · Solo lo que debe verse, publicado.**
  **Dónde se cumple:** `F0-T07` — documentación interactiva apagada en producción.
  **Qué se verifica:** que `/docs`, `/redoc` y el esquema OpenAPI efectivamente **no responden** en producción, probándolo contra la URL real desplegada.
  **Evidencia (2026-09-27), probada contra la URL real desplegada:** `/docs`, `/redoc`, `/openapi.json` y `/api/openapi.json` devuelven **404 los cuatro**. En desarrollo siguen disponibles, que es donde hacen falta.
  **Verificado el 2026-09-27**, con la Fase 0.5 cerrada. Se re-verifica en `FX-DOC` al cierre del proyecto, porque es una propiedad que hay que mantener a lo largo de todas las fases.

- [x] **FX-T13 · Validación de entrada en cliente y servidor.**
  **Dónde se cumple:** Pydantic en el 100% de las entradas del backend; tipos y validación HTML5 en cada formulario.
  **Qué se verifica:** que no existe **ni una sola** consulta armada por concatenación de strings a partir de un dato del request — todo pasa por el ORM, así que no hay superficie de inyección SQL.
  **Evidencia (2026-09-27):** cero consultas armadas por concatenacion, interpolacion o `format()` en todo el backend — verificado con una busqueda por patron. No hay superficie de inyeccion SQL. La validacion de entrada con Pydantic se prueba de verdad cuando existan los primeros esquemas de entrada, en la Fase 1.
  **Verificado el 2026-09-27**, con la Fase 0.5 cerrada. Se re-verifica en `FX-DOC` al cierre del proyecto, porque es una propiedad que hay que mantener a lo largo de todas las fases.

- [ ] **FX-T14 · Mínimo privilegio en la base de datos.**
  **Dónde se cumple:** `F13-T03`.
  **Estado al 2026-09-27: no hecho, y conviene adelantarlo.** La conexion de produccion usa hoy el rol por defecto del proyecto de Supabase, que puede borrar tablas. Crear el rol restringido ahora, con la base vacia y sin datos que migrar, es mas simple que hacerlo con trece fases encima.
  **Qué se verifica:** que la cadena de conexión de producción apunta al rol restringido y que ese rol **no** puede, por ejemplo, borrar tablas.

- [x] **FX-T15 · Sin acceso a carpetas privadas.**
  **Dónde se cumple:** `F0-T02` (el `.gitignore`) y la naturaleza del hosting: ni el estático del frontend ni las funciones serverless exponen listado de directorios.
  **Qué se verifica:** intentar acceder a rutas del filesystem del proyecto desde la URL pública y confirmar que no responden.
  **Evidencia (2026-09-27), probada contra produccion:** nueve rutas de archivos privados devuelven 404 — `/backend/app/main.py`, `/backend/app/core/config.py`, `/api/index.py`, `/vercel.json`, `/.gitignore`, `/requirements.txt`, `/backend/`, `/documentacion/05_Roadmap.md` y `/.git/config`. No hay listado de directorios ni acceso al filesystem del proyecto.
  **Verificado el 2026-09-27**, con la Fase 0.5 cerrada. Se re-verifica en `FX-DOC` al cierre del proyecto, porque es una propiedad que hay que mantener a lo largo de todas las fases.

- [ ] **FX-T16 · Análisis contra vulnerabilidades conocidas (OWASP).**
  **Dónde se cumple:** `F13-T04`.

- [ ] **FX-T17 · Revisión de la seguridad que depende de la arquitectura.**
  **Dónde se cumple:** `F13-T04`.

- [ ] **FX-T18 · Assessment de amenazas y riesgo.**
  **Dónde se cumple:** `F13-T05` más las pruebas de carga de `F13-T06`.

## Heurísticas de usabilidad

- [ ] **FX-T19 · Verificación de las 16 heurísticas.**
  **Qué se verifica, una por una, contra la aplicación terminada:**

  Estado al 2026-09-27: **5 cumplidas, 4 parciales, 7 pendientes.**

  | # | Heurística | Dónde se resuelve | Estado |
  |---|---|---|---|
  | 1 | Visibilidad del estado del sistema | `F1-T27` (indicador de carga), mensajes de error y éxito en cada formulario | Parcial — el indicador de conexión ya avisa si el backend responde |
  | 2 | Correspondencia con el mundo real | Nomenclatura de dominio en español con los términos reales del rubro | **Cumplida** — convención fijada y aplicada |
  | 3 | Control y libertad del usuario | `F12-T03` (deshacer) | Pendiente |
  | 4 | Consistencia y estándares | El catálogo de componentes y su regla de oro: reutilizar, nunca reinventar | **Cumplida** — el catálogo existe y ya rechazó una clase inventada |
  | 5 | Prevención de errores | `F1-T15` (confirmación de acción destructiva) + validación en las dos puntas | Pendiente |
  | 6 | Reconocer antes que recordar | Ningún formulario pide escribir un ID de memoria; los selectores vienen poblados con datos reales | Pendiente — no hay formularios todavía |
  | 7 | Flexibilidad y eficiencia | `F12-T06` | Pendiente |
  | 8 | Diseño minimalista | El sistema de diseño completo: densidad deliberada, composición bento, nada que compita con el dato | **Cumplida** — el sistema está aplicado |
  | 9 | Reconocer y recuperarse de errores | Los mensajes muestran el texto real del backend en lenguaje llano, nunca un código ni un stack trace | Parcial — `api.js` ya traduce el 422 de Pydantic y da un mensaje accionable si el backend no responde; el catálogo único de mensajes es `F1-T29` |
  | 10 | Ayuda y documentación | `F12-T05` (en la app) + los documentos de fase | Parcial — los documentos de fase existen; la ayuda dentro de la app, no |
  | 11 | Anticipación | `F12-T07` | Pendiente |
  | 12 | Autonomía | Usuario y rol siempre visibles en el sidebar; contexto y vuelta atrás en cada pantalla de detalle | Pendiente — no hay sidebar todavía |
  | 13 | Legibilidad | Jerarquía tipográfica del sistema de diseño + verificación formal de contraste en `F12-T10` | Parcial — la jerarquía está; el contraste sin verificar formalmente |
  | 14 | Registro del estado | `F0-T13` (tema persistente) + `F12-T08` (última pantalla y primer ingreso) | Parcial — el tema ya persiste entre páginas y sesiones |
  | 15 | Simplificación de tareas | La metodología misma: una tarea a la vez, modales de un solo paso, nunca un asistente de varios pasos para un alta simple | **Cumplida** — es la metodología del proyecto |
  | 16 | Protección del trabajo | `F12-T04` | Pendiente |

- [ ] **FX-DOC · Informe de cumplimiento.**
  Redactar `documentacion/fases/Fase_X_Cumplimiento.md` con el resultado de cada verificación, la evidencia concreta de cada una (captura, salida de consola, fragmento de código) y la justificación escrita de las decisiones conscientes que se apartan del enunciado (`FX-T07`).

---

*Fin del Roadmap. 14 fases de desarrollo (0 a 13) más la Fase X de verificación externa, con su tarea de documentación al cierre de cada una. Cada `- [ ]` se implementa de a una, en el orden lógica → backend → frontend, y se tilda únicamente después de la aprobación explícita del usuario. Si aparece una razón real para alterar el orden, esa razón se escribe en este documento antes de saltear nada.*

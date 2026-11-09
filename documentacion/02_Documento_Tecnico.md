# Documento Técnico — SMART Building

> **Estado del documento:** completo y **reescrito el 2026-09-25** sobre la experiencia de haber construido el sistema hasta la Fase 3 (usuarios y estructura, gestión financiera, reclamos y mantenimiento) y haberlo eliminado para rehacerlo. Todo lo que dice este documento fue ejecutado y probado al menos una vez, salvo las secciones explícitamente marcadas como "sin implementar".
>
> **Qué es este documento.** El "cómo": arquitectura, stack, modelo de datos exacto, convenciones de API, reglas de negocio implementadas, estrategia de pruebas y despliegue. **Todo lo relativo a la interfaz de usuario y al sistema de diseño se movió a [`03_Documento_Frontend.md`](03_Documento_Frontend.md)** — antes vivía acá, mezclado con la arquitectura, y creció hasta merecer documento propio.
>
> **Cambio estructural respecto de la versión anterior:** la sección 1 ya no es el Dashboard (eso es producto e interfaz: ver 01 y 04). Este documento arranca por la arquitectura, que es lo que efectivamente condiciona todo lo demás.

---

## 1. Arquitectura general

### 1.1 Principios

- **Backend y frontend separados desde el día uno.** Dos carpetas, dos procesos, dos responsabilidades. El frontend nunca renderiza HTML del lado del servidor ni usa un motor de templates: es HTML/CSS/JS estático que consume una API JSON.
- **Simplicidad antes que arquitectura de manual.** No se introduce una capa (microservicios, colas, cache distribuida) hasta que haya una razón real de negocio. Un proceso de backend, una base.
- **La lógica de negocio va antes que la base de datos.** Cada regla no trivial (prorrateo, transiciones de estado, severidad del semáforo, matriz de roles) se escribe y se prueba como **función pura de Python**, sin HTTP ni ORM, *antes* de modelar la tabla que la usa. Es la convención más importante de este proyecto y la que más errores evitó: una regla de negocio probada en aislamiento no se puede "romper sin querer" al cambiar un endpoint.
- **Escalable sin sobre-ingeniería.** La organización por dominio (un archivo de modelo, esquema, router y servicio por dominio) permite sumar módulos sin tocar los existentes.
- **Nada se da por terminado sin probarse de punta a punta**, con la interfaz real, antes de pasar a lo siguiente.

### 1.2 Stack tecnológico

| Capa | Tecnología | Por qué |
|---|---|---|
| Backend — framework | **FastAPI** | Documentación interactiva automática en `/docs`: permite probar cada endpoint antes de que exista la pantalla que lo consume, que es exactamente el flujo incremental de este proyecto. Validación automática con Pydantic. |
| Backend — ORM | **SQLAlchemy** | Permite desarrollar sobre SQLite y desplegar sobre PostgreSQL sin reescribir queries. Esa portabilidad dejó de ser hipotética: es exactamente lo que pasa hoy (ver 1.4). |
| Backend — validación | **Pydantic v2** | Separa el modelo de base de datos del modelo de entrada/salida de la API. Los validadores de campo son donde viven las reglas de forma (un estado válido, una prioridad válida). |
| Backend — servidor | **Uvicorn** | Servidor ASGI estándar para FastAPI. |
| Base de datos — desarrollo | **SQLite** | Un archivo, cero infraestructura. |
| Base de datos — producción | **PostgreSQL** (Supabase, vía *connection pooler*) | Requisito del entorno serverless: no hay disco persistente donde vivir un archivo SQLite. |
| Autenticación | **bcrypt** (hash, usado directo) + **PyJWT** (JWT HS256) | Sesión sin estado en el servidor — necesario en serverless, donde no hay proceso de larga vida que sostenga una sesión. |

> **Por qué no `python-jose` ni `passlib`, que es lo que decía la versión anterior de este documento (cambio del 2026-10-28).** Al implementar `core/security.py` revisé el estado de las dos librerías y ninguna se sostenía. `python-jose` 3.3.0 arrastra CVE-2024-33663 (confusión de algoritmo) y CVE-2024-33664 (denegación de servicio por JWE comprimido); el primero sigue reportado como arreglo incompleto hasta 3.5.0, y la librería está prácticamente sin mantenimiento. `passlib` tiene su última release en enero de 2020, y era la única razón por la que `bcrypt` estaba clavado en 4.0.1: passlib lee `bcrypt.__about__.__version__`, atributo que bcrypt eliminó en 4.1. Sacándola, bcrypt queda al día. El formato del hash es el mismo (`$2b$`), así que no hubo nada que migrar, y `cryptography` salió del proyecto de paso: entraba como extra de python-jose y HS256 no la necesita, así que son varios MB menos en el bundle de la función serverless.

> **La defensa concreta contra la confusión de algoritmo.** No alcanza con cambiar de librería: `decodificar_token` pasa `algorithms=["HS256"]` de forma explícita. Sin esa lista, quien valida el token acepta el algoritmo que el **propio token** declara en su encabezado, y entonces basta con mandar uno firmado con `alg: none` para fabricarse una sesión sin conocer el secreto. Hay un test que lo intenta y espera el rechazo, para que no se pueda reintroducir a mano.
| Frontend — maquetado | **HTML + CSS propio**: una hoja de tokens y un catalogo de componentes | Ver `03_Documento_Frontend.md`. **Sin framework de CSS y sin build.** Se evaluo Tailwind y se descarto: el sistema visual son clases compuestas propias (vidrio en dos capas, semaforo, dashboard visual), asi que sus utilidades no se usarian, y agregarlo sumaba un CDN o un binario de build sin resolver ningun problema real. Decision del 2026-09-27. |
| Frontend — interactividad | **JavaScript vanilla (ES2020+)** | Sin framework. Para el tamaño de este proyecto no aporta, y mantiene la promesa de arquitectura simple y sin build. |
| Frontend — mapas | **Leaflet.js + OpenStreetMap + Nominatim** | Sin API key ni facturación, a diferencia de Google Maps/Mapbox. Coherente con un stack que no depende de credenciales externas. |
| Testing | **pytest** + `TestClient` de FastAPI | Ver sección 8. |
| Despliegue | **Vercel** (backend serverless + frontend estático) | Ver 1.4. |

### 1.3 Estructura de carpetas

```
Smart_Building_ver_4/
├── backend/
│   ├── app/
│   │   ├── main.py                 # Instancia FastAPI, CORS, include_router, arranque del esquema
│   │   ├── database.py             # Engine, SessionLocal, Base declarativa, dependencia obtener_db
│   │   ├── core/
│   │   │   ├── config.py           # Variables de entorno, CORS, JWT, verificación de producción
│   │   │   ├── security.py         # Hash de contraseñas, emisión y decodificación de JWT
│   │   │   ├── dependencies.py     # Dependencias de autenticación y autorización (sección 4.3)
│   │   │   └── migraciones.py      # Evolución del esquema en arranque (sección 6)
│   │   ├── models/                 # SQLAlchemy — un archivo por dominio
│   │   ├── schemas/                # Pydantic — un archivo por dominio, mismo nombre que el modelo
│   │   ├── routers/                # Endpoints HTTP — un archivo por dominio
│   │   ├── services/               # Lógica de negocio pura (sección 2.3)
│   │   └── seed.py                 # Datos iniciales de desarrollo
│   ├── tests/                      # pytest — un archivo por router o por servicio
│   ├── pytest.ini
│   ├── requirements.txt            # Solo referencia a ../requirements.txt
│   └── smart_building.db           # Solo en desarrollo; no se versiona
│
├── frontend/                       # Ver 03_Documento_Frontend.md para el detalle
│   ├── index.html                  # Login (zona pre-autenticación)
│   ├── dashboard.html, edificios.html, usuarios.html, financiero.html,
│   │   reclamos.html, mantenimiento.html, activos.html, documentos.html,
│   │   proveedores.html, comunicados.html, reservas.html, seguridad.html,
│   │   analitica.html, configuracion.html
│   ├── assets/{css,js,img}/
│   └── servidor_dev.py             # Servidor estático con caché desactivada
│
├── documentacion/
│   ├── 01_Documento_General.md     # Producto y negocio
│   ├── 02_Documento_Tecnico.md     # Este documento
│   ├── 03_Documento_Frontend.md    # Sistema de diseño e interfaz
│   ├── 04_Infraestructura.md       # Recursos vivos fuera del repositorio
│   ├── 05_Roadmap.md               # Ejecución, tarea por tarea
│   ├── entrevistas.md              # Relevamiento de necesidad
│   ├── investigaciones/            # Decisiones con respaldo normativo
│   └── mockups/                    # Exploración visual histórica (no es contrato)
│
├── api/
│   └── index.py                    # Punto de entrada serverless de Vercel (ver 1.5)
│
├── .claude/skills/premium-uiux/    # Sistema de diseño ejecutable (ver 03, sección 1)
├── vercel.json                     # Región, builds y ruteo del despliegue (ver 1.5)
├── requirements.txt                # Lista canónica de dependencias (ver 1.5)
├── .vercelignore
├── .gitignore
└── README.md
```

**Nomenclatura (regla firme):** carpetas técnicas en inglés (`models/`, `schemas/`, `routers/`, `services/`, `core/`, `tests/`), porque es la convención del stack; **todo el dominio de negocio en español** (`Usuario`, `Edificio`, `Departamento`, `calcular_prorrateo_periodo`, `transicion_valida`). El código habla el mismo idioma que esta documentación y que la interfaz.

### 1.4 Entornos: desarrollo y producción

> **⚠️ Los recursos de producción siguen vivos.** La base de Supabase no se eliminó en el reinicio del proyecto y conserva el esquema y los datos del código anterior. **Antes de desplegar, leer [`04_Infraestructura.md`](04_Infraestructura.md)**, que documenta dónde está cada recurso, qué variables de entorno existen y por qué desplegar contra ese esquema viejo puede fallar en silencio (ver también la sección 6 de este documento).

Éste es el punto donde la arquitectura real difiere más de lo que preveía la versión anterior de este documento, que asumía SQLite en todos lados.

| | Desarrollo | Producción |
|---|---|---|
| Backend | Uvicorn local, puerto 8000 | Vercel, función serverless |
| Base de datos | SQLite (`smart_building.db`) | PostgreSQL gestionado (Supabase), **a través del connection pooler** |
| Frontend | `servidor_dev.py`, puerto 8090 | Vercel, estático |
| Configuración | Valores por defecto en código | Variables de entorno |

**Lo que impone el entorno serverless** (no son detalles de despliegue, condicionan el diseño):

1. **No hay disco persistente.** SQLite queda descartado en producción: cualquier escritura se pierde al terminar la invocación. De ahí PostgreSQL.
2. **Hay que conectarse por el *pooler*, no directo.** Cada invocación serverless abre su propia conexión; sin pooler se agota el límite de conexiones de la base con muy poco tráfico.
3. **No hay procesos de fondo ni tareas programadas.** Todo lo que el sistema haga tiene que ocurrir dentro del ciclo de un request. Funcionalidades futuras que suenan a *cron* (avisar vencimientos de activos, recordatorios de deuda) se resuelven calculando al momento de la consulta, no con un job.
4. **No hay estado en memoria entre requests.** De ahí JWT sin sesión de servidor.

**Variables de entorno** (definidas en `core/config.py`, con valores por defecto que hacen que en local no haga falta configurar nada):

| Variable | Para qué | Ausente en local |
|---|---|---|
| `DATABASE_URL` | Cadena de conexión a PostgreSQL | Cae a SQLite local |
| `JWT_SECRETO` | Secreto de firma de los tokens | Cae a un valor de desarrollo |
| `CORS_ORIGENES_EXTRA` | Dominios adicionales permitidos (coma-separado) | Solo se permiten los puertos locales |
| `VERCEL` | Marca que se está en producción | Ausente |

**Guarda de arranque:** `verificar_configuracion_produccion()` se ejecuta al iniciar la aplicación y **falla fuerte** si detecta que está en producción con el secreto JWT de desarrollo todavía puesto. Es preferible que el despliegue no arranque a que arranque inseguro sin que nadie lo note.

### 1.5 Los cuatro archivos del despliegue

Hay cuatro archivos en la raíz que existen únicamente porque Vercel los espera
ahí. Ninguno tiene lógica de negocio, y conviene entender qué hace cada uno
antes de tocarlos.

| Archivo | Para qué |
|---|---|
| `api/index.py` | Vercel busca las funciones serverless en una carpeta `api/` de la raíz, no dentro de `backend/`. Este archivo pone `backend/` en el path de importación y expone la aplicación que ya existe. **No debe tener lógica propia nunca.** |
| `vercel.json` | Declara la región (`gru1`, para que coincida con la de Supabase), las dos construcciones —la función Python y el frontend estático— y el ruteo: `/api/*` a la función, el resto al frontend. |
| `requirements.txt` (raíz) | Es la **lista canónica** de dependencias. Está en la raíz porque es donde la lee el runtime de Python de Vercel, y `backend/requirements.txt` la referencia con `-r ../requirements.txt`. |
| `.vercelignore` | Recorta lo que no participa del despliegue (documentación, skill, tests). No cambia el resultado, solo lo hace más liviano. |

**Frontend y backend se despliegan como un solo proyecto**, con `/api/*`
reescrito hacia la función. Comparten dominio, así que en producción el
navegador no dispara CORS.

**Dos trampas que ya costaron un ciclo de despliegue cada una:**

1. **El parser de `requirements.txt` de Vercel no admite `-r`.** Si el archivo
   de la raíz intenta incluir otro, el build falla con
   `could not parse requirements.txt`. Por eso la lista real está en la raíz y
   la referencia está en `backend/`, y no al revés.
2. **La cadena de conexión tiene que ser la del *Transaction pooler*, no la
   directa.** El host directo (`db.<proyecto>.supabase.co`, puerto 5432)
   resuelve a IPv6, y una función serverless no puede abrir conexiones IPv6
   salientes: falla con `Cannot assign requested address`. Desde la Fase 0.5,
   `verificar_configuracion_produccion()` detecta ese caso y lo dice en una
   línea, en lugar de dejar un traceback de ochenta.

---

## 2. Arquitectura del backend

### 2.1 Convenciones de la API

- Prefijo común `/api/`. Sin versionado explícito por ahora (se agregaría `/api/v1/` recién si conviven dos versiones).
- **Un router por dominio**, montado en `main.py`. Un mismo dominio puede exponer **dos routers** cuando tiene endpoints con prefijos distintos: uno anidado bajo el edificio (`/api/edificios/{edificio_id}/reclamos`) y otro sobre el recurso ya identificado (`/api/reclamos/{reclamo_id}/estado`). Es lo normal, no una excepción.
- Respuestas siempre JSON. Códigos: `200` lectura y actualización, `201` creación, `400` regla de negocio violada, `401` sin sesión válida, `403` sin permiso, `404` no existe, `409` requiere confirmación explícita, `422` datos mal formados (lo produce Pydantic solo).
- **`400` vs `422`:** si el valor es sintácticamente inválido (un estado que no existe en el enum), lo rechaza Pydantic con 422 sin llegar al router. Si el valor es válido pero la operación no se puede hacer en ese contexto (una transición de estado no permitida, un departamento de otro edificio), es un 400 del router con un mensaje explicativo en español.
- **`409` significa "necesito que confirmes"**, no "error". Se usa en las operaciones que van a sobrescribir algo: el servidor responde 409 con la explicación de qué va a pasar, y el cliente reenvía la misma petición con un campo booleano de confirmación (`confirmar_reemplazo: true`). Este mecanismo es el que permite no usar nunca un `confirm()` del navegador.
- Todo endpoint que opera sobre un edificio recibe `edificio_id` y **resuelve el permiso con una dependencia**, nunca con un `if` escrito a mano en el cuerpo del endpoint (sección 4.3).
- **Una ruta literal se declara siempre ANTES que una con parámetro, dentro del mismo router.** FastAPI resuelve en orden de declaración, así que `GET /usuarios/opciones` declarado después de `GET /usuarios/{usuario_id}` entra por el segundo con `usuario_id="opciones"` y devuelve un 422 de tipo inválido — un error que no menciona en ningún momento el problema real, que es el orden de dos decoradores. Cada ruta literal nueva lleva su test de que responde lo que corresponde, que es la única guarda contra reordenar el archivo.
- **Todo texto que una persona lee va acentuado y con eñes.** El código del backend se escribe sin acentos a propósito —nombres, docstrings, comentarios—, pero el contenido de un `detail` o de un `ValueError` no es código: es lo que aparece en la pantalla. El login mostraba "Email o contrasenia incorrectos." Se corrigió en `F1-T13`, en los quince textos que llegan al frontend, y los tests de contraseña fijan los acentos para que no se "corrijan" al estilo del resto del archivo.
- `/docs` (Swagger) siempre activo: es la herramienta con la que se prueba y se aprueba cada tarea de backend antes de que exista su pantalla.

### 2.2 Organización por dominio

Cada dominio tiene, como máximo, cuatro archivos con el mismo nombre en carpetas distintas:

```
models/reclamo.py     → tablas (SQLAlchemy)
schemas/reclamo.py    → entrada y salida de la API (Pydantic)
routers/reclamo(s).py → endpoints
services/reclamos.py  → reglas de negocio puras
```

Un dominio no importa el router de otro. Sí puede importar sus modelos y sus servicios.

### 2.3 La capa de servicios: reglas puras, sin base de datos

Es la convención central del proyecto. Un servicio contiene la regla de negocio **sin tocar la base de datos ni HTTP**, de modo que se puede probar con pytest en milisegundos y sin fixtures.

| Servicio | Responsabilidad |
|---|---|
| `services/autorizacion.py` | Matriz de roles: alcance de cada rol, qué información financiera ve, si es de solo lectura. Fuente única de verdad de los permisos. |
| `services/finanzas.py` | Estructura vacía del edificio (pisos por unidades) y coeficientes: los dos atajos de carga inicial (partes iguales, por m²) y la validación de que el edificio sume 100% exacto. El reparto de un monto real entre unidades es de la Fase 2 y todavía no está. |
| `services/reclamos.py` | Flujos de estado de `Reclamo` y de `OrdenTrabajo` (son dos flujos distintos), prioridades, colores de prioridad, tiempos de resolución. |
| `services/severidad.py` | Cálculo del semáforo por departamento a partir de sus reclamos y órdenes de trabajo. |
| `services/activos.py` | *(sin implementar)* Estado de un activo según su próximo mantenimiento. |

**Endpoints construidos hasta acá:** `routers/auth.py` (login, registro público, política de contraseña), `routers/usuarios.py` (CRUD de usuarios), `routers/edificios.py` (`POST /api/edificios` el alta con estructura automática de `F1-T20`, `GET /api/edificios` y `GET /api/edificios/{id}` de `F1-T21`, y `PATCH /api/edificios/{id}` la configuración de `F1-T22`) `routers/estructura.py` (los trece endpoints anidados de `F1-T23`: pisos, departamentos, cocheras y espacios comunes bajo `/api/edificios/{id}/...`) y `routers/coeficientes.py` (los tres de `F1-T24`). Con eso el backend de la Fase 1 queda completo: lo que sigue son las pantallas.

> **La carga de coeficientes tiene endpoints propios, y la razón es la de la iteración anterior.** El coeficiente es el porcentaje de la expensa que paga cada unidad: sin coeficientes cargados no hay expensa posible — no es que salga mal, es que no se puede emitir. En la iteración anterior esto quedó pendiente **en silencio**: nunca existió endpoint para cargarlo, solo se podía escribiendo en la base, y el problema apareció recién al intentar generar la primera expensa con un "Hay departamentos sin coeficiente cargado" que no decía cuáles ni cuántos. Así que la decisión central de este módulo es que **cada respuesta trae el estado completo del edificio**: cuánto suma hoy, si eso es 100%, cuántas unidades siguen sin coeficiente y cuáles son las primeras. La pantalla puede mostrar "suman 99,988% y faltan 3 unidades" en el mismo momento en que se carga una, y el problema se ve mientras se trabaja.

> **La suma no se bloquea mientras se carga: se informa.** Cargar treinta coeficientes a mano pasa por estados intermedios donde la suma no es 100 —cuando se cargó el primero suma 3,5—, y rechazar esos estados obligaría a cargar todo en un solo pedido o a bajar un coeficiente antes de poder subir otro. Lo que sí impone la suma exacta es la generación de la expensa (Fase 2), que es donde importa, y para entonces la pantalla ya venía avisando.

> **El atajo no pisa lo cargado a mano sin confirmación, y ese es el único 409 de la Fase 1.** Los coeficientes de un consorcio real están escritos en el reglamento de propiedad horizontal: no se calculan, se copian. El atajo —partes iguales o por metro cuadrado— es para el edificio que todavía no tiene el reglamento cargado. Si alguna unidad ya tiene coeficiente, el atajo responde **409** con el texto de la pregunta, que es exactamente lo que el envoltorio de `fetch` del frontend convierte en `error.necesitaConfirmacion` para abrir el diálogo de "¿seguro?". Con `sobrescribir: true` reemplaza todo. Las cuentas las hace `services/finanzas.py` y no el endpoint, así que la suma da 100,000% por construcción; el endpoint solo arma la lista de unidades en un orden estable (posición del piso, después identificador) y guarda lo que el servicio devuelve, **en una sola transacción**: la mitad de un edificio con coeficientes nuevos y la otra con los viejos no suma 100% y nadie se daría cuenta hasta la expensa.

> **Toda la estructura está anidada bajo el edificio, y eso es un permiso.** Un piso no existe por sí solo: existe en un edificio. Que eso se vea en la URL tiene una consecuencia práctica — el permiso se verifica una sola vez, sobre el edificio, y al principio. Si las rutas fueran `/api/pisos/{id}`, cada endpoint tendría que subir del piso al edificio para saber si quien pide tiene algo que ver con él, y el día que uno se olvide, el agujero no se ve leyendo ese endpoint: se ve comparándolo con los otros doce. El orden es siempre el mismo: buscar el edificio **dentro del alcance** de quien pide (404 si no), buscar la fila hija **dentro de ese edificio** (404 si no), validar la regla de negocio (400 si no), guardar. El segundo paso también es un permiso: pedir el piso de un edificio ajeno pasando el id del edificio propio da 404, y por eso la búsqueda del hijo lleva siempre la condición del padre. Hay un test de eso por cada una de las cuatro entidades.

> **Lo que cuelga se desarma antes de borrar.** No hay borrado en cascada en ninguna de las cuatro relaciones (decisión de `F1-T19`): un piso con unidades no se borra, una unidad con propietario o inquilino asignado no se borra, y una unidad con cocheras apuntándole tampoco — una cochera fija apuntando a una unidad que ya no existe queda apuntando a la nada. Las cocheras y los espacios comunes sí se borran sin condiciones **por ahora**: el día que haya reservas (Fase 7), borrar un espacio con reservas futuras dejaría a varias personas con una reserva de un lugar que no existe, y ahí gana la misma verificación.

> **La asignación de un residente valida cuatro cosas, y la cuarta es la que le da sentido a `roles_habilitados`.** La persona tiene que existir, estar activa, tener ese rol en la matriz **y** que ese rol esté habilitado en ese edificio. Sin la cuarta, la columna que `F1-T22` configura no tendría ningún efecto: un consorcio podría decidir no habilitar inquilinos y el sistema aceptaría uno igual. Desvincular, en cambio, funciona siempre: si no fuera así, deshabilitar un rol dejaría a esas personas pegadas a sus unidades para siempre.

> **La configuración es un PATCH, y la diferencia con un PUT no es de estilo.** La pantalla de configuración tiene varios bloques —responsables, cobranza, contacto de emergencia, roles habilitados— y se guardan por separado. Con un PUT, guardar el bloque de cobranza obligaría a mandar también los responsables y el contacto, y el día que un campo nuevo no viaje en ese formulario, guardar la cobranza lo borraría sin que nadie lo pida. La diferencia entre "no mandé este campo" y "mandé este campo en `null`" la resuelve `model_fields_set` de Pydantic: el endpoint arma el UPDATE con `model_dump(exclude_unset=True)`, así que un campo ausente no se toca y un campo en `null` se vacía de verdad. Eso es lo que permite **borrar** el teléfono de emergencia, que con un centinela tipo cadena vacía sería indistinguible de "no lo toques". Los campos que la columna declara NOT NULL no se pueden vaciar, y eso lo rechaza el esquema con un 422 antes de llegar a la base.

> **Dos clases de campo, dos permisos.** Quién administra el edificio (`admin_consorcio_id`, `encargado_id`) es una decisión de la plataforma: solo el Administrador General. Si un Administrador de Consorcio pudiera cambiarlos, podría sacarse a sí mismo —perdiendo el acceso al edificio sin forma de recuperarlo— o asignarse un edificio ajeno. Cómo cobra y a quién llamar (días de vencimiento, recargo por mora, CBU, alias, contacto de emergencia, roles habilitados) es el trabajo diario del Administrador de Consorcio sobre su edificio: pedirle al Administrador General que cargue el CBU de cada consorcio sería convertir un dato operativo en un trámite. El alcance es el mismo que el de la lectura, y un edificio ajeno responde 404 igual que uno inexistente.

> **Un responsable se valida contra la matriz de roles, no solo contra la tabla de usuarios.** `admin_consorcio_id` tiene que apuntar a un usuario con rol `admin_consorcio` real y activo, ídem `encargado_id` con `encargado`. Sin esa validación, un "encargado" que en la matriz es Proveedor no tendría ninguno de los permisos que la pantalla del encargado necesita, y la falla aparecería recién cuando esa persona intente entrar. Los tres motivos de rechazo —no existe, está desactivado, tiene otro rol— dan mensajes distintos a propósito: quien configura es un administrador eligiendo entre usuarios que él mismo dio de alta.

> **Una consecuencia de lo anterior que conviene tener escrita:** como un usuario tiene un solo rol y cada puesto exige el suyo, el CHECK `ck_edificios_responsables_distintos` es hoy **inalcanzable** desde la API — el cruce lo rechaza antes la validación de rol, con un mensaje más útil. El chequeo del endpoint queda igual como respaldo, porque el día que un puesto admita más de un rol sería la única red: un CHECK que salta devuelve un 500 sin explicación.

> **El CBU y el alias se validan en el esquema, y lo que NO se valida está escrito.** Al CBU se le sacan espacios y guiones antes de medirlo, porque se copia y se pega de un resumen bancario y casi siempre viene en bloques; se exigen 22 dígitos exactos, que es lo que ataja el error de tipeo que corta un dígito. **No se valida el dígito verificador**, igual que no se valida el del CUIT. El alias se mide contra los límites del alias bancario argentino (6 a 20 caracteres, letras, números, puntos y guiones): sin eso, un alias de 30 caracteres lo rechazaría la columna `String(20)` y la persona vería un 500 sin explicación. Y el recargo por mora **rechaza más de dos decimales en vez de redondearlos**: la columna es `Numeric(5,2)`, así que un 1,555 se guardaría como 1,56 y quien lo escribió nunca se enteraría de que el recargo que se aplica no es el que puso. Es plata ajena.

> **Cómo se evita el N+1 en este proyecto, porque la regla vale para todo lo que venga.** "N+1" es una consulta para traer la lista y una más por cada elemento de esa lista. Nadie lo escribe a propósito: aparece solo, en cuanto el esquema de respuesta de un listado incluye una colección y Pydantic sale a leerla fila por fila. En la iteración anterior el listado de edificios disparaba 29 consultas para 7 edificios de prueba y el detalle 6 para uno de 3 pisos: en SQLite local eso son 2 a 12 milisegundos y no se nota, pero contra Supabase cada consulta paga ida y vuelta de red y el mismo listado tardaba alrededor de un segundo y medio. Las dos defensas son distintas y las dos quedan escritas en `routers/edificios.py`: **el listado no trae colecciones** y cuenta con subconsultas correlacionadas —una sola consulta, haya 1 edificio o 300—, y **el detalle usa `selectinload`**, que agrega una consulta por colección con todos los ids juntos en un `IN`: cinco consultas fijas, sin importar que el edificio tenga 3 pisos o 20. Se usa `selectinload` y no `joinedload` porque unir dos colecciones hermanas en una sola consulta hace su producto cartesiano (7 pisos por 10 cocheras son 70 filas que después hay que deduplicar en memoria).

> **Los tests cuentan consultas, no miden tiempos.** Un tiempo en CI depende de la máquina y de la carga del momento, así que un N+1 que vuelva a aparecer pasaría un test de tiempo en silencio. `tests/test_edificios_lectura.py` engancha un oyente al motor de SQLAlchemy y cuenta las sentencias que tocan las tablas de la estructura, y además **prueba el contador**: provoca a mano el N+1 que los endpoints evitan y verifica que lo ve. Un contador roto haría pasar los demás sin verificar nada.

> **El alcance del listado lo decide la consulta.** El Administrador General ve la cartera entera —es quien da de alta los edificios—; el Administrador de Consorcio ve solo los edificios donde figura como tal, por `admin_consorcio_id`. El filtro va en el `WHERE` y no en la pantalla: un filtro que vive en el frontend no es un permiso, porque la respuesta ya trajo los datos y cualquiera los lee en la pestaña de red del navegador. Y un edificio que existe pero está fuera del alcance responde **lo mismo** que uno inexistente: un 403 distinguible le iría contando a un Administrador de Consorcio qué edificios hay en la cartera probando ids.

**Dos reglas que hacen que esto funcione:**

1. **Un servicio no importa modelos.** Los modelos importan constantes de los servicios (para declarar sus `CheckConstraint` contra la misma lista de valores válidos), así que la dependencia inversa crearía un ciclo de imports. Cuando una función de servicio necesita leer atributos de una entidad, los recibe por *duck typing*: la función pide "algo que tenga `.prioridad`", no un `Reclamo`. Esto además hace los tests triviales — se prueban con objetos de juguete.
2. **La única excepción son las funciones que, por su naturaleza, necesitan consultar.** Por ejemplo, prorratear el período real de un edificio requiere ir a buscar sus gastos y sus coeficientes. Esas funciones —una o dos por servicio, no más— sí importan modelos y reciben una `Session` como parámetro. Se documentan explícitamente como la excepción dentro del propio archivo.

### 2.4 Esquemas de entrada y salida

- **Entrada y salida son esquemas distintos**, siempre. Nunca se expone un modelo de SQLAlchemy directamente.
- Los esquemas de salida usan `from_attributes=True` y se construyen desde el objeto ORM.
- **PATCH parcial:** los esquemas de edición declaran todos los campos opcionales y el router aplica `model_dump(exclude_unset=True)`. La semántica resultante, que es la correcta y hay que respetar en todo el sistema: **no mandar un campo lo deja como está; mandarlo en `null` lo borra de verdad.**
- Los campos calculados que el frontend necesita pero no son columnas (por ejemplo, el tiempo de resolución en segundos) se exponen como **campo calculado del esquema de salida**, no se recalculan en JavaScript. El frontend pinta lo que la API ya calculó.
- Las validaciones de forma (un estado que existe, una prioridad válida, dos campos mutuamente excluyentes) se hacen con validadores de Pydantic, **siempre contra las constantes del servicio correspondiente** — nunca repitiendo la lista de valores válidos en un segundo lugar.

---

## 3. Modelo de datos

23 tablas, agrupadas por dominio. Convenciones generales: clave primaria `id` autoincremental; marca temporal `creado_en` en UTC en toda entidad que sea un hecho registrado; montos en `Numeric(12,2)` (nunca `float`, que pierde centavos); los valores de enumeración se validan **dos veces**, en Pydantic (para el mensaje de error claro) y con un `CheckConstraint` en la tabla (para que la base sea la última línea de defensa).

### 3.1 Usuarios y estructura del edificio

**`usuarios`** — `id`, `nombre`, `email`, `password_hash`, `rol`, `telefono`, `activo`, `creado_en`.
`rol` ∈ {admin_general, admin_consorcio, encargado, propietario, inquilino, proveedor, auditor, seguridad}, validado por CHECK.

**`edificios`** — `id`, `nombre`, `direccion`, `cp`, `cuit`, `latitud`, `longitud`, **`admin_consorcio_id`**, **`encargado_id`**, `dias_vencimiento_expensas`, `recargo_mora_porcentual`, `contacto_emergencia_nombre`, `contacto_emergencia_telefono`, `roles_habilitados`, `cbu`, `alias_cbu`, `activo`, `creado_en`.

> **Los dos vínculos de responsabilidad son columnas del edificio, no una tabla de asignación.** `admin_consorcio_id` y `encargado_id` apuntan a `usuarios` y son los que responden la pregunta "¿quién gestiona este edificio?". `encargado_id` **faltaba** en el diseño original: el rol Encargado existía con alcance de edificio desde el primer día, pero no había ningún mecanismo que lo vinculara a un edificio concreto, lo que hacía imposible resolver "los reclamos que este encargado puede gestionar". Se detectó recién al implementar reclamos. No repetir el error: **un rol con alcance de edificio necesita su vínculo desde el modelo, no después.**

> **Las decisiones de tipo que tomé al construir la tabla (`F1-T18`).** Ninguna es obvia leyendo la lista de columnas:
>
> | Columna | Cómo quedó | Por qué |
> |---|---|---|
> | `cp` | Obligatoria, texto | Es lo que `F1-T25` le pasa a Nominatim junto con la dirección. No guardo ciudad ni provincia: el CP ya las determina, y guardarlas sería tener el mismo dato tres veces. |
> | `latitud` / `longitud` | `Numeric(9,6)`, anulables | Anulables porque una dirección que no se geocodifica **avisa pero no bloquea el alta** — una calle nueva puede no estar indexada. `Numeric` y no `Float` porque seis decimales de grado son 11 cm y un decimal exacto se compara sin la sorpresa de que 0,1 no exista en binario. Con CHECK de rango: una latitud de 200 es un error de geocodificación, no una ubicación rara. |
> | `cuit` | Anulable, **sin unicidad** | Un mismo consorcio puede administrar dos torres cargadas como dos edificios, así que una restricción de unicidad bloquearía un caso real. |
> | `admin_consorcio_id` / `encargado_id` | FK a `usuarios`, anulables | Que apunten a un usuario **con el rol correcto** no lo puede garantizar la base: sería un CHECK que consulta otra tabla, y eso ningún motor lo permite. Lo valida `F1-T22` al grabar, y es una de las poquísimas reglas de esta tabla sin red abajo. Sí hay CHECK de que las dos no apunten a la misma persona: un usuario tiene un solo rol. |
> | `dias_vencimiento_expensas` | Obligatoria, por defecto 10 | Con CHECK de 1 a 31. Un 0 silencioso rompe el cálculo de la primera expensa que se genere. |
> | `recargo_mora_porcentual` | `Numeric(5,2)`, por defecto 0 | Multiplica deuda real, así que nunca `float`. CHECK de 0 a 100: negativo sería un descuento por pagar tarde. |
> | `roles_habilitados` | `JSON`, obligatoria, por defecto **todos** | Qué roles tienen sentido en *este* edificio. El default es "todos" y no "ninguno" a propósito: una lista vacía bloquearía en silencio toda asignación de un edificio recién creado. La lista válida es `autorizacion.ROLES_HABILITABLES` (los asignables menos `admin_general`, cuyo alcance es la cartera entera y no se habilita por edificio). |
> | `cbu` | Texto de 22, anulable | Texto y no número porque un CBU puede arrancar con cero y como entero lo perdería. CHECK de largo exacto 22: uno de 21 dígitos es un CBU mal copiado, y el error tiene que aparecer al guardarlo, no cuando un propietario intente transferir. |
>
> **Un cuidado con `roles_habilitados` que no se ve en la tabla:** SQLAlchemy **no detecta una modificación en el lugar** de una columna JSON. `edificio.roles_habilitados.remove("encargado")` no se guarda nunca y tampoco da error — hay que asignar una lista nueva. Y lo que la lista contiene no lo valida la base, porque un CHECK no puede leer adentro de un JSON de forma portable entre SQLite y PostgreSQL: lo valida el esquema Pydantic de `F1-T22`.

**`asignacion_edificio`** — `id`, `usuario_id`, `edificio_id`, `creado_en`. Restricción de unicidad sobre el par (`usuario_id`, `edificio_id`).

> **`edificio_id` ya tiene su clave foránea (`F1-T18`).** Nació sin ella en `F1-T03`, y no por olvido: `edificios` no existía como modelo todavía, y declarar una FK contra una tabla ausente hace fallar la creación del esquema entero al arrancar. Se cerró sin migrar datos porque la tabla estuvo **vacía** durante toda la ventana —lo primero que escribe una asignación es la pantalla de `F11-T05`—, así que alcanzó con borrarla y dejar que se vuelva a crear ya con la FK declarada. Eso lo hace `m002_fk_asignacion_edificio`, que se corre a mano una vez por base y **se niega a tocar la tabla si tiene filas**. Esto no era la deuda de `activo_id` y `proveedor_id` (sección 4): esas quedaron sin FK con datos ya cargados encima, y eso sí necesita una migración que preserve las filas.

> **Cómo se resuelve el alcance de un usuario sobre un edificio (decisión del 2026-09-27).** Los ocho roles no tienen todos la misma clase de vínculo con un edificio, así que no se resuelven todos con el mismo mecanismo. Cada vínculo vive en **un solo lugar**, y esa es la regla:
>
> | Naturaleza | Roles | Dónde vive |
> |---|---|---|
> | **Derivado** de un dato que ya existe | propietario, inquilino, proveedor | `departamentos.propietario_id` / `inquilino_id`; `ordenes_trabajo` asignadas |
> | **Responsabilidad única** por edificio (1:1) | admin_consorcio, encargado | `edificios.admin_consorcio_id`, `edificios.encargado_id` |
> | **Asignación** de varios a varios (N:M) | seguridad, auditor | `asignacion_edificio` |
> | Sin vínculo | admin_general | Alcanza toda la cartera |
>
> `asignacion_edificio` existe **solo** para los dos roles N:M, y es deliberado que no sea una tabla puente genérica para los ocho. Una tabla así duplicaría la verdad: el vínculo real de un propietario es su unidad, y guardar además una fila que diga "alcanza el edificio X" crea dos fuentes del mismo hecho que pueden divergir — asignar una unidad y olvidar la fila dejaría al usuario con departamento y sin acceso, sin que nada avise.
>
> **Por qué hacen falta los dos roles N:M y no una columna más.** Un edificio tiene un solo administrador y un solo encargado, pero puede tener **varios** agentes de seguridad (turnos), y un auditor puede auditar **varios** edificios. Eso no entra en una columna.
>
> **La versión anterior de este documento describía una tabla `usuario_edificio` que nunca se pobló**, mientras la autorización real terminaba consultando la base. Tener las dos cosas a medias fue lo que generó confusión. Esa tabla no existe más: el reemplazo es la tabla de arriba, con un propósito acotado y documentado.
>
> **El hueco que esto cierra.** El rol `seguridad` tiene alcance de edificio desde el primer día y no tenía ningún vínculo que lo atara a uno. Es el mismo error que ya ocurrió con `encargado_id`, que faltaba y se descubrió recién al implementar reclamos. **Un rol con alcance de edificio necesita su vínculo desde el modelo, no después.**

**`pisos`** — `id`, `edificio_id`, `numero`, `orden`. Unicidad de (`edificio_id`, `numero`) y de (`edificio_id`, `orden`).
**`departamentos`** — `id`, `piso_id`, `identificador`, `m2`, `propietario_id`, `inquilino_id`, **`coeficiente`** `Numeric(6,3)`. Unicidad de (`piso_id`, `identificador`) y de `inquilino_id`.
**`cocheras`** — `id`, `edificio_id`, `numero`, `tipo` (CHECK: fija/rotativa), `departamento_id`. Unicidad de (`edificio_id`, `numero`).
**`espacios_comunes`** — `id`, `edificio_id`, `nombre`, `capacidad`, `reglas_uso`. Unicidad de (`edificio_id`, `nombre`).

> **`numero` y `orden` del piso son dos columnas porque son dos cosas.** El nombre de un piso y su lugar en la pila no siempre coinciden: una planta baja es el piso de más abajo y se llama 0, un entrepiso va entre el 0 y el 1, y hay edificios que saltean el 13. Con una sola columna habría que elegir entre dibujar el edificio en el orden correcto o llamar a cada piso como lo llaman sus vecinos. `generar_estructura()` los crea con `numero == orden`, que es lo único que se puede saber sin preguntar.

> **`ocupado` NO es una columna: se deriva.** Es `hybrid_property` de `Departamento` y devuelve "hay propietario o hay inquilino". El Roadmap lo pide explícitamente y vale escribir por qué: una columna booleana que hay que mantener al día es una columna que algún día dice que la unidad está vacía mientras tiene un inquilino con contrato firmado. El dato ya está, así que guardarlo aparte es guardar dos veces el mismo hecho — y cuando un hecho está guardado dos veces, es cuestión de tiempo que las dos copias no coincidan. Es `hybrid_property` y no una `property` común para que también se pueda filtrar en SQL (`where(Departamento.ocupado)`) sin traer filas a Python para descartarlas.

> **"Un propietario, varias unidades; un inquilino, una sola" lo garantiza la base.** `propietario_id` no lleva restricción de unicidad —un propietario puede tener varias unidades, incluso en edificios distintos— e `inquilino_id` sí. La unicidad sobre una columna anulable permite muchos `NULL`, tanto en SQLite como en PostgreSQL, así que no obliga a que toda unidad tenga inquilino: solo impide que la misma persona figure en dos. No es una limitación arbitraria: es lo que permite que la interfaz del residente nunca le pregunte a un inquilino de cuál de sus unidades está hablando.

> **Las otras garantías de la estructura, todas con CHECK.** `coeficiente` entre 0 y 100; `m2 > 0` (un 0 silencioso rompe el atajo de coeficientes por superficie); propietario e inquilino no pueden ser la misma persona; el aforo de un espacio común es mayor que cero o es `NULL` (un laundry con dos lavarropas no tiene aforo, y un 0 como "sin dato" sería un espacio que no admite a nadie); y **una cochera rotativa no puede tener un departamento asignado**, porque rotativa significa justamente que no es de nadie en particular.

> **Las relaciones del edificio a su estructura no llevan borrado en cascada**, a propósito. Suena cómodo —sacar un piso de la lista lo borraría— y es justo lo que no conviene: un departamento puede tener expensas y pagos apuntándole, así que darlo de baja es una decisión con consecuencias y la toma `F1-T23`. Con el comportamiento por defecto, intentar borrar un piso que todavía tiene departamentos falla ruidosamente, que es lo que corresponde.

> **El `numero` de la cochera es texto.** En la práctica están rotuladas, y el rótulo dice "S2-14" o "12 bis" tan seguido como dice "12". La cochera cuelga del edificio y no del piso: está en un subsuelo que no es un piso de departamentos, y colgarla de un piso obligaría a inventar pisos sin unidades.

> **Ver los espacios comunes no puede ser admin-only.** En la iteración anterior el listado lo fue por error y dejó sin poder reportar un reclamo sobre un espacio común a Propietario, Inquilino y Encargado, que son justamente los que están ahí. Se descubrió recién en la Fase 3. **Crear** un espacio común sí es exclusivo del administrador; verlo, no. **Resuelto en `F1-T23`:** `GET /api/edificios/{id}/espacios-comunes` pide sesión y resuelve el alcance con `core/alcance.puede_ver()`, así que lo ve cualquiera que tenga algo que hacer en el edificio — quien lo administra, quien trabaja ahí, quien vive ahí y quien lo tiene asignado. El Proveedor queda afuera a propósito: su alcance en la matriz es `ots_asignadas`, o sea que llega a un edificio por una orden de trabajo y no por el edificio en sí. Hay un test por rol, y uno que verifica las dos mitades de la frase: que lo vea y que no pueda crearlo.

### 3.2 Financiero

**`gastos`** — `id`, `edificio_id`, `rubro`, `monto`, `fecha`, `descripcion`, `proveedor_id`*, `activo_id`*, `creado_en`. CHECK: monto > 0.
**`expensas`** — `id`, `edificio_id`, `anio`, `mes`, `total`, `creado_en`. CHECK: mes entre 1 y 12, total > 0.
**`expensa_detalle`** — `id`, `expensa_id`, `rubro`, `monto`. La apertura por rubro de esa liquidación.
**`expensa_departamento`** — `id`, `expensa_id`, `departamento_id`, `monto`. Lo que le toca a cada unidad.
**`pagos`** — `id`, `departamento_id`, `expensa_id`, `monto`, `fecha`, `medio_pago`, `comprobante_url`, `estado` (pendiente/confirmado/rechazado, por defecto pendiente), `creado_en`.
**`fondos`** / **`movimientos_fondo`** — fondo con nombre; movimientos con tipo (CHECK ingreso/egreso), monto, fecha, descripción. El saldo se calcula, no se guarda.
**`cajas`** / **`movimientos_caja`** — caja chica con `responsable_id` y `monto_fijo` (CHECK > 0); movimientos igual que los de fondo.
**`presupuestos`** — `id`, `edificio_id`, `proveedor_id`*, `descripcion`, `monto`, `fecha`, `estado` (CHECK pendiente/aprobado/rechazado), `gasto_id` (vínculo al gasto real cuando se aprueba), `creado_en`.
**`facturas`** — `id`, `gasto_id`, `proveedor_id`*, `numero`, `monto`, `fecha`, `archivo_url`, `creado_en`.

Los **deudores** no son una tabla: son una consulta calculada sobre `expensa_departamento` menos los `pagos` confirmados.

### 3.3 Reclamos

**`reclamos`** — `id`, `edificio_id`, `departamento_id`, `espacio_comun_id`, `descripcion`, `prioridad`, `estado`, `creado_por_id`, `creado_en`, `cerrado_en`.
Tres CHECK: prioridad válida, estado válido, y **`departamento_id IS NULL OR espacio_comun_id IS NULL`** — la restricción que hace imposible un reclamo que sea sobre una unidad *y* un espacio común a la vez. Los tres objetivos posibles (unidad / espacio común / edificio en general) se codifican con esas dos columnas, sin una tercera columna de "tipo".
`cerrado_en` se completa **solo** al llegar al estado terminal `cerrado`, y es lo que permite calcular el tiempo de resolución.

**`reclamo_fotos`** — `id`, `reclamo_id`, `url`, `creado_en`. Una fila por foto.
**`reclamo_comentarios`** — `id`, `reclamo_id`, `autor_id`, `texto`, `creado_en`.

> **Convención de adjuntos, para todo el sistema:** una foto o evidencia es **una fila en una tabla hija con una URL**, nunca una lista de URLs aplastada en un campo de texto. Aplica a `reclamo_fotos`, `ot_evidencias` y al futuro `activo_fotos`.

### 3.4 Mantenimiento

**`ordenes_trabajo`** — `id`, `edificio_id`, `espacio_comun_id`, `activo_id`*, `reclamo_id`, `tipo`, `prioridad`, `estado` (por defecto pendiente), `descripcion`, `costo`, **`encargado_id`**, `proveedor_id`*, `creado_en`, `fecha_inicio`, `fecha_cierre`.
CHECK: tipo ∈ {preventivo, correctivo, programado, emergencia}; estado ∈ {pendiente, en_curso, resuelta}; prioridad válida; costo nulo o ≥ 0.

**`ot_evidencias`** — `id`, `orden_trabajo_id`, `url`, `momento` (CHECK antes/despues), `subido_por_id`, `creado_en`.

### 3.5 (*) El patrón de clave foránea diferida

Las columnas marcadas con `*` arriba (`activo_id`, `proveedor_id`) son **enteros sueltos sin clave foránea real**. Es deliberado y es un patrón que conviene entender bien porque se repite:

- Un módulo necesita referenciar una entidad cuyo módulo llega varias fases después (Gastos necesita Proveedor; Órdenes de trabajo necesitan Activo).
- Una **columna sin FK no depende de que la tabla destino exista**: se puede crear desde el primer día. Lo que sí necesita que exista la tabla destino es la restricción de clave foránea.
- Cuando el módulo destino se construye, la columna se convierte en FK real agregando la restricción en el modelo. Ese cambio **sí** requiere tocar el esquema de una tabla que ya tiene datos (ver sección 6), a diferencia de agregar una columna nueva.

La alternativa —bloquear tres módulos esperando a un cuarto, o crear tablas vacías anticipadas— es peor. Pero el patrón exige disciplina: cada columna diferida se documenta en el modelo con un comentario que diga en qué fase se formaliza.

### 3.6 Tablas de módulos aún no implementados

Especificadas, no construidas: `activos` y `activo_fotos`; `documentos`; `proveedores`, `rubros`, `proveedor_rubro`, `evaluaciones_proveedor`; `comunicados` y `comunicado_lectura`; `reservas`; `incidentes_seguridad` y `bitacora`. El detalle funcional de cada una está en el Documento General, secciones 7 a 9 y 14 a 16.

---

## 4. Autenticación, roles y permisos

### 4.1 Autenticación

- `POST /api/auth/registro` crea una cuenta propia, **sin autenticación**, y la deja con rol `pendiente` hasta que un administrador la apruebe (sección 4.4).
- `POST /api/auth/login` con email y contraseña → JWT de 60 minutos.
- `GET /api/auth/me` devuelve el usuario de la sesión: es lo que usa el frontend para armar la navegación según el rol.
- `GET /api/auth/politica-password` devuelve los requisitos de la contraseña, **sin autenticación**. Existe porque el formulario de registro los necesita y lo usa, por definición, alguien que todavía no tiene cuenta: `/usuarios/opciones` ya los devolvía, pero pide sesión de Administrador General porque además entrega el catálogo de roles. Es seguro que sea público — no revela nada que no se pueda averiguar mandando una contraseña mala al registro, que ya responde con la lista completa de lo que falta; esto solo la dice antes. La estructura la arma `PoliticaDePassword.vigente()`, así que los dos endpoints no pueden desacoplarse.
- El frontend guarda el token en `localStorage` y lo manda en `Authorization: Bearer <token>`.
- Contraseñas **siempre** hasheadas con bcrypt, incluso las triviales de prueba. Nunca texto plano en la base, ni siquiera en modo test.
- Un usuario inactivo no puede iniciar sesión, y su token deja de valer aunque no haya expirado (se verifica el estado del usuario en cada request, no solo la firma del token).

### 4.2 Matriz de roles

Definida una sola vez en `services/autorizacion.py` como estructura de datos, no repartida en `if`s por los routers:

| Rol | Alcance | Ve financiero de la unidad | Ve financiero del edificio | Solo lectura |
|---|---|---|---|---|
| admin_general | cartera completa | — | ✅ | no |
| admin_consorcio | su edificio | — | ✅ | no |
| encargado | su edificio | — | ❌ (solo semáforo, sin montos) | no |
| propietario | su(s) unidad(es) | ✅ | ❌ | no |
| inquilino | su unidad | ✅ *(corregido, ver Documento General 3.1)* | ❌ | no |
| proveedor | sus órdenes de trabajo | — | ❌ | no |
| auditor | edificio o cartera | ✅ | ✅ | **sí** |
| seguridad | su edificio | — | ❌ | no |
| `pendiente` | **ninguno** | ❌ | ❌ | sí *(resguardo, ver 4.4)* |

Las ocho primeras filas son los roles del negocio, y son las que la aplicación ofrece para elegir. `pendiente` está en la matriz porque la columna `rol` lo acepta, no porque sea un rol que alguien asigne: lo escribe el registro propio y se explica en la sección 4.4.

### 4.3 Autorización: dependencias, no condicionales sueltos

El control de acceso vive en `core/dependencies.py` como dependencias de FastAPI que los endpoints declaran. Ninguna regla de permiso se escribe dentro del cuerpo de un endpoint.

**Cómo quedó esto en esta iteración (`F1-T23`).** La tabla de abajo es el diseño completo de la capa, con los nombres de la iteración anterior. Las dependencias se construyen a medida que hay pantallas que las necesiten, y la pregunta del alcance —"¿sobre qué edificios?"— quedó resuelta en un archivo propio, **`core/alcance.py`**, con dos funciones: `limitar_a_los_que_administra(consulta, usuario)`, que es el `WHERE` de los endpoints de escritura y del listado de la cartera, y `puede_ver(db, usuario, edificio)`, que responde si esa persona tiene algo que hacer en ese edificio (lo administra, trabaja ahí, vive ahí o lo tiene asignado) y cubre lo que la tabla llama `requerir_acceso_edificio`. Está separado de `services/autorizacion.py` porque son dos preguntas distintas: la matriz dice **qué puede hacer un rol** y es lógica pura sin base de datos; el alcance dice **sobre qué edificios** y no se puede responder sin consultar. Es la deuda que `core/dependencies.py` anotó en `F1-T07` ("lo que queda para F1-T08 es exponer el alcance, que necesita los modelos `Edificio` y `Departamento`"), y se pudo cerrar recién acá porque `F1-T23` es la primera tarea con un endpoint que no es admin-only.

| Dependencia | Responde a | Quién pasa |
|---|---|---|
| `obtener_usuario_actual` | ¿Quién sos? | Cualquier sesión válida y activa |
| `requerir_acceso_edificio` | ¿Podés operar sobre este edificio? | Según la matriz de alcance |
| `requerir_acceso_financiero_edificio` | ¿Podés ver lo financiero de tu unidad acá? | admin_general; admin_consorcio del edificio; propietario/inquilino con unidad en él |
| `requerir_gestion_reclamos_edificio` | ¿Gestionás reclamos y órdenes de trabajo acá? | admin_general; admin_consorcio **o encargado** de ese edificio |
| `requerir_acceso_para_crear_reclamo` | ¿Podés cargar un reclamo o ver datos básicos del edificio? | Lo anterior **o** cualquiera con unidad propia en el edificio |

**Lecciones de diseño que dejó esta capa:**

1. **El token no lleva el alcance: la autorización lo resuelve consultando la base en cada dependencia.** Es correcto y es lo que hay que hacer. Un alcance guardado dentro del token quedaría congelado en el momento de emitirlo: si a un usuario se le quita un edificio, seguiría entrando hasta que el token expire. Lo que no hay que hacer es escribir código que *asuma* que el token trae el alcance. Cada dependencia pregunta por el vínculo real, según la tabla de la sección 3.1.
2. **Una dependencia se reutiliza si la regla coincide, aunque el nombre suene a otro dominio.** `requerir_acceso_para_crear_reclamo` terminó siendo también la regla correcta para "ver los espacios comunes de un edificio": el conjunto de gente es idéntico. Se reutiliza y se documenta el porqué, en vez de escribir una quinta dependencia igual.
3. **Cuidado con el tipo que devuelve la dependencia.** Algunas devuelven el usuario autenticado y otras la entidad ya cargada. Declarar mal el tipo en la firma del endpoint no falla al importar: falla en tiempo de ejecución, cuando alguien usa un atributo que ese objeto no tiene. Ver sección 9.

### 4.4 El registro propio y el rol `pendiente`

Hasta `F1-T16` el único que podía dar de alta usuarios era el Administrador General. Para un edificio de cuarenta unidades eso son cuarenta altas dictadas por teléfono y cargadas por alguien que no es el dueño del dato. Así que cada persona se registra sola y el administrador **solo aprueba**, que es la decisión que sí le corresponde.

`POST /api/auth/registro` es el **único endpoint de escritura sin autenticación de todo el sistema**, y eso cambia su superficie de ataque respecto de cualquier otro: lo puede llamar cualquiera, desde cualquier parte, sin credenciales. Las cuatro defensas que lo hacen aceptable no son opcionales:

1. **El rol no viene en el pedido.** `RegistroPublico` no declara el campo `rol` y rechaza los campos que no conoce (`extra="forbid"`), así que mandarlo es un 422. Y el endpoint escribe el rol como constante, sin leer nada del cuerpo. Son dos barreras para lo mismo a propósito: el costo de equivocarse acá es que cualquiera se dé de alta como Administrador General con un `curl`.
2. **Una cuenta pendiente es inerte.** Queda activa —entra y puede leer en qué estado está— pero `pendiente` no figura en la lista de roles habilitados de ninguna pantalla, así que no alcanza nada. **Eso es lo que hace que un registro abierto no sea un problema de seguridad:** lo peor que logra un abuso es crear filas que no pueden nada.
3. **La respuesta es la misma exista o no el email.** El alta del administrador devuelve 400 ante un email repetido, y ahí está bien: la usa una persona de confianza y el mensaje le ahorra una consulta. En un endpoint público esa misma distinción es un oráculo: cualquiera prueba direcciones de a una y averigua quién vive en el edificio. El duplicado no se consulta antes — se intenta el INSERT, el índice único lo rechaza, se traga el `IntegrityError` y se responde exactamente lo mismo. **Y el tiempo también tiene que parecerse:** el hash de la contraseña, que es lo más caro de la operación, se calcula antes del INSERT, así que los dos caminos lo pagan igual. Es el mismo criterio que el hash descartable del login.
4. **`pendiente` es un valor válido que nadie puede asignar.** Ver abajo.

**Por qué `pendiente` es un valor del rol y no un campo nuevo.** Se evaluaron tres formas:

| Forma | Por qué no / sí |
|---|---|
| `rol` nulo | Todo el sistema asume que `rol` es un valor válido de la matriz — el `CheckConstraint`, los validadores de Pydantic, `autorizacion.obtener()` que falla ruidosamente ante un rol desconocido. Un nulo obliga a agregar una rama "¿y si no tiene rol?" en cada uno de esos lugares, y alcanza con que falte una para tener un agujero. |
| `activo = False` | Confunde dos hechos distintos: "lo desactivó un administrador" y "nunca fue aprobado". Son cosas diferentes en la pantalla, en el mensaje que lee la persona y en la trazabilidad. Y bloquea el login, cuando lo que se quiere es que la persona entre y lea que está esperando aprobación. |
| **`rol = 'pendiente'`** | **La elegida.** Cada pantalla ya declara su lista de roles habilitados y `pendiente` no está en ninguna, así que queda afuera de todo **sin escribir una sola línea de autorización nueva**. El login funciona y el `CheckConstraint` sigue siendo exacto. |

**Consecuencia obligatoria: `ROLES` se partió en dos.** Era una sola tupla que respondía dos preguntas distintas sin que se notara que eran dos, porque daban la misma respuesta:

| Lista | Pregunta que responde | Contenido |
|---|---|---|
| `ROLES` | ¿La columna `rol` puede guardar este valor? | Los 8 + `pendiente` |
| `ROLES_ASIGNABLES` | ¿Un administrador puede elegir este rol? | Los 8 |

`pendiente` es sí a la primera y **no** a la segunda. Con una sola lista, el `<select>` del formulario de alta ofrecería "Pendiente de aprobación" como si fuera un rol del consorcio, y el `PATCH` permitiría devolver a alguien al estado de no aprobado — una operación que no existe. Para quitarle el acceso a una persona está la baja lógica, que es reversible y queda registrada.

La regla para cualquier consumidor nuevo: **el `CheckConstraint` de la tabla usa `ROLES`; todo lo demás usa `ROLES_ASIGNABLES`.** Los esquemas de alta y de edición preguntan por `es_asignable()`, no por `es_rol_valido()`.

**Un detalle de la matriz que es un resguardo y no una descripción:** `pendiente` tiene `solo_lectura = True`. Un pendiente tampoco puede *leer* nada, así que ninguno de los dos valores lo describe bien; se eligió `True` porque falla del lado seguro — el día que exista un endpoint protegido únicamente por `exigir_que_pueda_escribir`, sin lista de roles, un pendiente queda afuera igual. El costo conocido es que el mensaje de ese rechazo diría "es un rol de consulta", que para un pendiente no es la explicación correcta. Es barato al lado de un permiso de escritura concedido por omisión.

**Quién aprueba, y por qué todavía es uno solo.** Lo natural sería que aprobaran el Administrador General y el Administrador de Consorcio. El segundo **todavía no puede**, por la misma razón por la que toda la gestión de usuarios es solo del Administrador General en esta fase: no hay forma de limitarlo a *su* consorcio hasta que existan `Edificio` y `Departamento`. Se amplía en la misma tarea que resuelve el alcance.

#### El circuito completo, con pantallas (`F1-T16B`)

El backend quedó en `F1-T16A`; esto es lo que lo hace usable. Vale leer las cuatro decisiones de diseño porque ninguna agregó código de autorización nuevo:

| Decisión | Por qué |
|---|---|
| El registro es **una tarjeta más de `index.html`**, no un archivo ni un modal | Comparte todo con el login —topbar, indicador de conexión, centrado, componentes de campo—, así que un `registro.html` sería la cabecera canónica repetida una vez más. Y no interrumpe nada que haya que preservar atrás, así que tampoco es un modal. |
| Aprobar es **el PATCH que ya existía** | Aprobar es asignarle un rol a quien tiene `pendiente`. No hay endpoint nuevo, no hay permiso nuevo, no hay modal nuevo: es la edición de siempre, con el formulario en un modo que obliga a elegir el rol. |
| Rechazar es **desactivar**, no borrar | La baja del sistema es lógica en todas partes, y acá además resuelve un caso concreto: si se borrara, la persona podría volver a registrarse con el mismo email a los cinco minutos y habría que rechazarla de nuevo, sin ninguna constancia de que ya se lo había hecho. Desactivada, el email sigue ocupado, la solicitud baja al listado marcada como inactiva, y se puede reactivar y aprobar si fue un error. |
| Los pendientes van **arriba del listado de usuarios**, no en una pantalla propia | No son una entidad distinta: son los mismos usuarios en un estado que pide una decisión. Una pantalla aparte significaría que el administrador tiene que acordarse de entrar a mirarla, y una solicitud que nadie mira es una persona esperando. |

**Un hallazgo que no era parte de la tarea y había que arreglar igual.** El `<select>` de rol del formulario de alta arrancaba en la primera opción, y la matriz está ordenada de más permisos a menos: enviar el formulario sin tocar el rol creaba un **Administrador General**. En el alta ya era un riesgo tonto; con la aprobación de pendientes pasaba a ser el camino más probable de todos, porque el administrador va a aprobar de a varios y el campo que no se toca es justo el que importa. Ahora la primera opción es una que **no es un rol** ("Elegí un rol…", con valor vacío) y está seleccionada por defecto, así que el rol hay que elegirlo a mano en el alta y en la aprobación. El backend ya rechazaba el valor vacío con un 422; esto evita llegar a pedírselo.

**El texto que lee quien se registra no se escribe en el frontend.** Lo manda el backend en la respuesta del registro, y es el mismo para un email nuevo que para uno que ya existía. Esa indistinguibilidad es la defensa número 3 de arriba, y redactar el mensaje en la pantalla sería la forma más fácil de arruinarla sin darse cuenta: alcanzaría con un "te creamos la cuenta" que no aplica al caso del email repetido.

**Lo que esta sección dejó aprendido sobre probar dos barreras.** Al verificar las defensas rompiendo el código a propósito apareció algo que conviene tener anotado: romper **solo** la segunda barrera —hacer que el endpoint lea un `rol` del pedido en vez de usar la constante— no hizo fallar ningún test. No es falta de cobertura: sin el campo en el esquema no hay nada que leer, así que el comportamiento es idéntico. Es un *mutante equivalente*, y es literalmente lo que significa tener defensa en profundidad. Pero deja a la vista cuál de las dos sostiene todo —la ausencia del campo— y por eso hay un test que la fija directamente, además del que la verifica por su consecuencia. **La lección general: al probar dos barreras para lo mismo, hay que romper las dos juntas; si se rompe una sola y nada falla, eso no dice que los tests sean malos ni que la barrera sobre.**

---

## 5. Reglas de negocio implementadas

### 5.1 Prorrateo de expensas

- `Departamento.coeficiente` es `Numeric(6,3)`: **tres decimales**. Cualquier cálculo que produzca coeficientes debe redondear con esa misma precisión. Redondear a más decimales que los que la columna guarda hace que la suma deje de dar 100% al persistir — error real, detectado con 28 unidades, donde daba 99,989%. La precisión de la columna es una constante del servicio, no un número mágico repetido.
- Repartir un monto entre N unidades **no redondea cada parte por separado**: la última unidad recibe el resto exacto, para que la suma dé siempre igual al total.
- Editar un gasto no altera una expensa ya generada. La regeneración de la **última** expensa es la única excepción: responde `409` pidiendo confirmación, y al confirmarse **conserva la identidad de la expensa** (reemplaza su detalle y su reparto, no la borra) para que los pagos ya registrados contra ella sigan siendo válidos.

### 5.2 Ciclo de vida del pago

`pendiente → confirmado` o `pendiente → rechazado`, y solo lo mueve un administrador. Solo `confirmado` descuenta deuda. El monto pendiente de confirmación se le informa al residente por separado del saldo, para que no pague dos veces.

### 5.3 Flujo de estados del reclamo

```
recibido → asignado → en_curso → resuelto → cerrado
                          ↑          │
                          └──────────┘   (reapertura: única excepción)
```

- Transiciones definidas como un diccionario en `services/reclamos.py` y validadas con una única función. Ningún endpoint valida una transición a mano.
- `resuelto → en_curso` es la única excepción al flujo lineal, y la única transición que puede disparar **quien creó el reclamo** además de la gestión.
- `cerrado` es terminal, siempre. Un problema que reaparece es un reclamo nuevo.
- Una transición inválida devuelve `400` con el mensaje exacto de qué a qué no se puede pasar.

### 5.4 Flujo de estados de la orden de trabajo

```
pendiente → en_curso → resuelta
```

Flujo **propio y distinto** del reclamo: tres estados, estrictamente lineal, sin reapertura. Comparte archivo de servicio con el flujo de reclamos porque los dominios se implementan juntos, **no porque sean el mismo flujo** — confundirlos es un error fácil de cometer y que efectivamente se cometió durante el diseño.

Reglas asociadas:
- Pasar a `en_curso` exige tener asignado un encargado o un proveedor, y registra `fecha_inicio`.
- Pasar a `resuelta` registra `fecha_cierre` y admite cargar el costo en la misma operación.
- Una orden `resuelta` ya no se reasigna.

### 5.5 Sincronización reclamo ↔ orden de trabajo

Cuando una orden nace de un reclamo, los estados del reclamo siguen a los de la orden:

| Al hacer esto con la orden | El reclamo pasa a |
|---|---|
| Generarla desde el reclamo | `asignado` |
| Pasarla a `en_curso` | `en_curso` |
| Pasarla a `resuelta` | `resuelto` |

Siempre a través de la misma función de validación de transiciones: si la transición no es válida (porque el reclamo ya está cerrado por otra vía), **no se fuerza nada**, simplemente no ocurre.

> **Trampa real:** la sincronización del cierre no funciona si no existe también la del inicio. Pasar la orden a `resuelta` intenta llevar el reclamo a `resuelto`, pero `asignado → resuelto` **no es una transición válida** (hay que pasar por `en_curso`). Sin el paso intermedio, la automatización parecía funcionar y silenciosamente no hacía nada. Los dos flujos tienen que caminar en paralelo, paso a paso.

### 5.6 Severidad (semáforo del dashboard)

Funciones puras, una por factor, que devuelven uno de cuatro valores (`ok`, `warn`, `pend`, `crit`):

- **Reclamos:** algún reclamo abierto crítico → `crit`; algún reclamo abierto de cualquier otra prioridad → `warn`; ninguno → `ok`.
- **Órdenes de trabajo:** alguna **en curso** → `pend`; en cualquier otro caso → `ok`. Nunca devuelve `warn` ni `crit`: el naranja es exclusivo de mantenimiento en ejecución. Ojo: una orden todavía `pendiente` (sin arrancar) **no** dispara el naranja.
- **Deuda:** más de un mes → `crit`; un mes → `warn`; sin deuda → `ok`.
- **Combinación:** en la vista general gana el estado más grave (`ok` < `warn` < `pend` < `crit`). En una vista filtrada se muestra solo el factor de esa vista.

El cálculo vive en el backend y viaja calculado al frontend. **Nunca se recalcula severidad en JavaScript con datos reales.**

### 5.7 Tiempos de resolución

Campo calculado, expuesto por la API en segundos, `null` mientras el elemento sigue abierto:
- **Reclamo:** desde `creado_en` hasta `cerrado_en` (el cierre, no el "resuelto", que todavía puede revertirse).
- **Orden de trabajo:** desde `creado_en` hasta `fecha_cierre`.

La agregación (promedios, series por mes) es responsabilidad del módulo de Analítica, no de este cálculo.

---

## 6. Evolución del esquema de base de datos

No se usa Alembic. El esquema evoluciona con dos mecanismos que corren al arrancar la aplicación:

1. **Creación de tablas faltantes.** SQLAlchemy crea las tablas que todavía no existen. Es idempotente y no toca las existentes. Para que funcione, **todo modelo nuevo tiene que estar importado antes de esa línea** — se garantiza importándolos en un módulo agregador.
2. **Agregado de columnas faltantes** (`core/migraciones.py`). Compara las columnas declaradas en los modelos contra las columnas reales de cada tabla y emite `ALTER TABLE ... ADD COLUMN` para las que falten.

**Los límites exactos del segundo mecanismo** (entenderlos evita corromper datos):

| Cambio en el modelo | ¿Lo resuelve solo? |
|---|---|
| Agregar una columna nueva anulable | **Sí** |
| Agregar una columna nueva obligatoria a una tabla con filas | No (no hay valor para las filas existentes) |
| Agregar una clave foránea o un CHECK a una columna que ya existe | **No** — solo agrega columnas, nunca modifica restricciones |
| Cambiar el tipo de una columna | **No** |
| Renombrar o eliminar una columna | **No**, y tampoco lo intenta (una columna sobrante en la base se ignora) |

Todo lo que cae en "No" requiere una migración pensada y escrita a mano para ese caso. En particular, **convertir una columna diferida en clave foránea real** (sección 3.5) cae acá: no alcanza con agregar `ForeignKey` al modelo si la tabla ya tiene filas.

**Cuándo conviene revisar esta decisión:** este esquema funciona bien mientras el proyecto sea de un solo desarrollador y la base de producción se pueda recrear. En cuanto haya datos reales de clientes que no se puedan perder, conviene migrar a Alembic. No antes: sería infraestructura sin uso.

> **⚠️ Aplicación inmediata de todo esto.** La base de producción de Supabase **conserva hoy el esquema completo del código eliminado** (23 tablas con datos de prueba). Como los dos mecanismos de arriba son puramente aditivos, desplegar la reimplementación contra esa base **no va a corregir ninguna diferencia**: una tabla modelada distinto queda con su forma vieja, sin error visible. La decisión a tomar antes del primer despliegue —y la recomendación de vaciar el esquema, con su fundamento— está en [`04_Infraestructura.md`](04_Infraestructura.md), sección 3.

---

## 7. Seguridad de la aplicación

- Contraseñas con bcrypt, nunca en texto plano en la base.
- JWT de corta duración, sin refresh token por ahora (se vuelve a iniciar sesión). Se revisita si la fricción lo justifica.
- Validación de toda entrada en el borde de la API con Pydantic. Nunca se confía en datos del frontend.
- CORS restringido a orígenes explícitos, jamás `*` en producción.
- **Aislamiento entre consorcios:** todo endpoint que devuelve datos de un edificio valida pertenencia antes de responder. Es la fuga de datos más probable de este sistema (un administrador viendo el edificio de otro) y por eso la validación es una dependencia obligatoria, no un chequeo opcional.
- **Doble resguardo en las acciones auto-destructivas.** Un usuario no puede desactivarse a sí mismo: lo rechaza el backend **y** la interfaz no lo ofrece. Esto no es teórico: durante el desarrollo un Administrador General se desactivó a sí mismo probando el botón y, como el login rechaza usuarios inactivos y hace falta ser admin para reactivar a alguien, la cuenta quedó irrecuperable y hubo que reparar la base a mano. Cualquier acción de "desactivar / eliminar / degradar" sobre uno mismo necesita el mismo tratamiento.
- El secreto de producción se verifica al arrancar (sección 1.4).
- Los archivos subidos —cuando exista carga real— se validarán por tipo y tamaño antes de guardarse.

---

## 8. Estrategia de pruebas

**Qué se prueba y qué no.** No se escriben tests de CRUD trivial. Se prueba: toda lógica de servicio (siempre, en la misma tarea que la crea), toda regla de autorización, todo flujo de estados, y todo cálculo financiero. La referencia alcanzada en la primera construcción fue de **356 tests** al cierre de la Fase 3.

**Tres niveles:**

1. **Tests de servicio** — lógica pura, sin base ni HTTP. Milisegundos. Se prueban con objetos de juguete (`@dataclass`) gracias al *duck typing* de la sección 2.3.
2. **Tests de integración** — router completo contra base real en memoria.
3. **Prueba de punta a punta, una por tema** (`tests/test_e2e_*.py`) — el recorrido completo en el orden en que lo hace una persona el primer día. La primera es `test_e2e_usuarios.py`, de `F1-T16`.

**Por qué hace falta el tercer nivel si cada pieza ya está probada aparte:** porque los errores de integración no viven dentro de una pieza, viven en las juntas. Dos casos reales que ningún test de unidad vio:

- `/usuarios/opciones` devolvía 422 porque la ruta parametrizada `/usuarios/{usuario_id}` estaba declarada antes y se comía la literal. Los dos endpoints funcionaban; lo que estaba mal era el orden **entre** ellos.
- El primer usuario creado en la iteración anterior quedó inutilizable porque su contraseña nunca se anotó. Cada pieza funcionaba; lo que faltaba era el recorrido.

**Dos reglas del e2e que lo diferencian de un test de integración:**

- **Todo pasa por HTTP, con el login real.** El e2e **no** usa el fixture `como`: ese atajo inserta el usuario en la base y después se loguea, lo cual es perfecto para probar un endpoint pero acortaría justamente el camino que la prueba viene a recorrer. La única excepción es el administrador inicial, que se crea llamando a `sembrar()` porque es exactamente lo que hace el sistema real.
- **Las listas salen de la fuente de verdad, no copiadas.** Los roles que recorre vienen de `autorizacion.ROLES`, así que el día que se agregue uno la prueba lo incluye sola y falla si el alta no lo soporta. Una lista escrita a mano envejecería en silencio.

**Y una regla que vale para los tres niveles: un test que nació en verde y nunca falló no prueba nada.** Antes de dar por bueno un test que importa, se rompe a propósito el código que vigila y se confirma que falla. En `F1-T16` eso encontró dos cosas: que cubrir solo `/estado` dejaba abierta la vía de `PATCH` para desactivarse a uno mismo, y que una prueba de interfaz propia estaba midiendo el resultado (listado vacío) en vez del mecanismo (la guarda de rol) — el resultado lo lograba el 403 del backend, así que la prueba pasaba igual con la guarda desactivada.

**Patrón del test de integración** (mismo en todos los archivos, conviene copiarlo tal cual):

- Motor SQLite **en memoria** con `StaticPool` (sin él, cada conexión ve una base distinta).
- `create_all` con **lista explícita de tablas**, no todas: hace visible qué depende de qué, y falla ruidosamente si falta una.
- Se sobrescribe la dependencia de sesión de la app (`dependency_overrides`) y se limpia al final del fixture.
- Usuarios de cada rol relevante creados en el fixture, y un helper que hace login y devuelve el header de autorización.
- Se prueba siempre el caso permitido **y** el prohibido. Un endpoint sin test de 403 es un endpoint sin control de acceso probado.

**Regla de oro aprendida:** correr solo el archivo de test que se está escribiendo **no alcanza**. Dos regresiones reales (un campo que quedó obligatorio sin querer en un esquema, una consulta con columnas explícitas que no incluía una columna nueva) pasaron los tests del archivo nuevo y rompieron archivos ajenos. **Antes de dar una tarea por terminada se corre la suite completa.**

---

## 9. Catálogo de trampas conocidas

Errores que ya se cometieron una vez, con su síntoma y su causa. Leer antes de depurar algo raro.

**Backend**

| Síntoma | Causa | Prevención |
|---|---|---|
| `AttributeError` sobre el objeto que devolvió una dependencia | La firma del endpoint declara un tipo (`Edificio`) pero la dependencia devuelve otro (`UsuarioAutenticado`). FastAPI no valida esa anotación. | Usar el parámetro de ruta (`edificio_id`) directamente y tratar la dependencia solo como guardia de permiso. |
| Un endpoint ajeno empieza a fallar con "campo requerido" tras agregar un campo | Se quitó sin querer el valor por defecto de un campo opcional de un esquema de entrada. | Correr la suite completa, no solo el archivo nuevo. |
| Error de validación de respuesta al agregar una columna | Hay consultas optimizadas que seleccionan **columnas explícitas** en vez de la entidad completa; agregar un campo al esquema de salida exige agregarlo también a esa lista. | Buscar consultas con columnas explícitas cada vez que se suma un campo a un esquema de salida. |
| Import circular al escribir un servicio | El servicio importó un modelo, y el modelo ya importaba constantes del servicio. | Duck typing en los servicios (sección 2.3). |
| La sincronización automática entre dos entidades "no hace nada" | La transición intermedia faltaba y la validación la rechazaba en silencio. | Sección 5.5. |
| Suma de porcentajes que no da 100 | Redondeo con más decimales que los que guarda la columna. | Sección 5.1. |
| En los tests, una tabla "no existe" | Falta en la lista explícita de `create_all`. | Agregarla al fixture. |
| Una ruta literal nueva devuelve 422 de "tipo inválido" | Se declaró **después** de una ruta con parámetro del mismo router (`/usuarios/{usuario_id}`), y FastAPI resuelve en orden de declaración: el texto de la ruta entra como valor del parámetro. El mensaje de error no menciona nada de esto. | Las rutas literales van arriba de las que tienen parámetro, y cada una con su test de que responde lo que corresponde. |
| Un mensaje de la interfaz aparece sin acentos ("contrasenia") | Se escribió con la convención del código, que es sin acentos. Pero un `detail` no es código: es lo que lee la persona. | Ver 2.1, penúltimo punto. |

**Frontend** *(el catálogo completo está en `03_Documento_Frontend.md`, sección 8)*

| Síntoma | Causa |
|---|---|
| `Cannot access 'X' before initialization` | Variable declarada con `let` más abajo de donde la usa el código de ruteo (*temporal dead zone*). Ocurrió tres veces. |
| Un ícono SVG desaparece al primer clic | Se reemplazó el `innerHTML` del `<button>` con etiquetas SVG sueltas, en vez del `innerHTML` del `<svg>` interno. |
| Una fecha se muestra un día antes | `new Date('2026-08-05')` se interpreta como medianoche UTC y en Argentina (UTC-3) retrocede un día. |
| Un formulario no envía y no muestra ningún error | Hay un `<select required>` oculto por `display:none`: Chromium bloquea el envío sin poder enfocarlo. |
| Un alta se autocompleta con las credenciales del admin logueado | Chrome detecta el par email+contraseña como un login. |

---

## 10. Módulos especificados sin implementar

Resumen técnico de lo que falta construir. El detalle funcional está en el Documento General.

- **Dashboard General** — un único endpoint con todos los widgets, filtrando el detalle por rol en el backend (el Encargado recibe el estado financiero como semáforo sin montos, no se le oculta en el frontend).
- **Dashboard Visual** — endpoint por edificio que devuelve la estructura completa con la severidad **ya calculada** por unidad (sección 5.6) y los activos comunes. El frontend solo pinta.
- **Activos** — ficha, estado calculado por vencimiento, QR generado al dar de alta (librería `qrcode`), historial derivado de órdenes de trabajo, costos acumulados.
- **Gestión documental** — categorías con visibilidad por rol, fechas de vencimiento que alimentan el estado de activos, y **la decisión pendiente de almacenamiento real de archivos** que destraba los adjuntos de todo el sistema.
- **Proveedores** — directorio con rubros N:N, evaluaciones, historial derivado de órdenes de trabajo. Al construirse, formaliza las claves foráneas diferidas (sección 3.5).
- **Comunicación interna** — comunicados segmentados con registro de lectura por usuario.
- **Reservas** — validación de solapamiento contra las reglas del edificio.
- **Seguridad** — incidentes y bitácora; el botón de emergencia es un registro de alta prioridad, sin integración externa.
- **Analítica** — endpoints de series agregadas sobre datos ya existentes.
- **Capa de IA** — clasificación y priorización de reclamos, generación asistida de comunicados, búsqueda sobre documentación. Deliberadamente al final: necesita datos reales. El proveedor de modelo se elige al abordar la fase, no antes.

---

*Documentos relacionados: [`01_Documento_General.md`](01_Documento_General.md) (producto) · [`03_Documento_Frontend.md`](03_Documento_Frontend.md) (interfaz y diseño) · [`05_Roadmap.md`](05_Roadmap.md) (ejecución) · [`investigaciones/`](investigaciones/) (fundamento normativo de las reglas financieras).*

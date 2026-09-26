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
| Autenticación | **passlib/bcrypt** (hash) + **python-jose** (JWT) | Sesión sin estado en el servidor — necesario en serverless, donde no hay proceso de larga vida que sostenga una sesión. |
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
│   ├── requirements.txt
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
├── .claude/skills/premium-uiux/    # Sistema de diseño ejecutable (ver 04, sección 1)
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

---

## 2. Arquitectura del backend

### 2.1 Convenciones de la API

- Prefijo común `/api/`. Sin versionado explícito por ahora (se agregaría `/api/v1/` recién si conviven dos versiones).
- **Un router por dominio**, montado en `main.py`. Un mismo dominio puede exponer **dos routers** cuando tiene endpoints con prefijos distintos: uno anidado bajo el edificio (`/api/edificios/{edificio_id}/reclamos`) y otro sobre el recurso ya identificado (`/api/reclamos/{reclamo_id}/estado`). Es lo normal, no una excepción.
- Respuestas siempre JSON. Códigos: `200` lectura y actualización, `201` creación, `400` regla de negocio violada, `401` sin sesión válida, `403` sin permiso, `404` no existe, `409` requiere confirmación explícita, `422` datos mal formados (lo produce Pydantic solo).
- **`400` vs `422`:** si el valor es sintácticamente inválido (un estado que no existe en el enum), lo rechaza Pydantic con 422 sin llegar al router. Si el valor es válido pero la operación no se puede hacer en ese contexto (una transición de estado no permitida, un departamento de otro edificio), es un 400 del router con un mensaje explicativo en español.
- **`409` significa "necesito que confirmes"**, no "error". Se usa en las operaciones que van a sobrescribir algo: el servidor responde 409 con la explicación de qué va a pasar, y el cliente reenvía la misma petición con un campo booleano de confirmación (`confirmar_reemplazo: true`). Este mecanismo es el que permite no usar nunca un `confirm()` del navegador.
- Todo endpoint que opera sobre un edificio recibe `edificio_id` y **resuelve el permiso con una dependencia**, nunca con un `if` escrito a mano en el cuerpo del endpoint (sección 4.3).
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
| `services/finanzas.py` | Prorrateo: cálculo de coeficientes (partes iguales, por m²) y reparto de un monto entre unidades respetando el coeficiente y el redondeo exacto. |
| `services/reclamos.py` | Flujos de estado de `Reclamo` y de `OrdenTrabajo` (son dos flujos distintos), prioridades, colores de prioridad, tiempos de resolución. |
| `services/severidad.py` | Cálculo del semáforo por departamento a partir de sus reclamos y órdenes de trabajo. |
| `services/activos.py` | *(sin implementar)* Estado de un activo según su próximo mantenimiento. |

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

**`usuario_edificio`** — `id`, `usuario_id`, `edificio_id`, `rol_efectivo` (CHECK contra los 8 roles). Tabla puente para vínculos múltiples.

> **Advertencia sobre esta tabla:** existe en el esquema pero **la autorización real no se resuelve con ella**. El JWT lleva una lista de edificios que en la práctica siempre viaja vacía, así que toda dependencia de autorización termina consultando la base (¿es el admin de este edificio? ¿tiene una unidad acá?). Antes de volver a implementarla, decidir: o se la puebla y se la usa de verdad como fuente de alcance, o se la elimina y los vínculos quedan donde efectivamente están (`edificios.admin_consorcio_id`, `edificios.encargado_id`, `departamentos.propietario_id`/`inquilino_id`). Tener las dos cosas a medias es lo que generó confusión.

**`pisos`** — `id`, `edificio_id`, `numero`, `orden`.
**`departamentos`** — `id`, `piso_id`, `identificador`, `m2`, `propietario_id`, `inquilino_id`, `ocupado`, **`coeficiente`** `Numeric(6,3)`.
**`cocheras`** — `id`, `edificio_id`, `numero`, `tipo` (CHECK: fija/rotativa), `departamento_id`.
**`espacios_comunes`** — `id`, `edificio_id`, `nombre`, `capacidad`, `reglas_uso`.

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

- `POST /api/auth/login` con email y contraseña → JWT de 60 minutos.
- `GET /api/auth/me` devuelve el usuario de la sesión: es lo que usa el frontend para armar la navegación según el rol.
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

### 4.3 Autorización: dependencias, no condicionales sueltos

El control de acceso vive en `core/dependencies.py` como dependencias de FastAPI que los endpoints declaran. Ninguna regla de permiso se escribe dentro del cuerpo de un endpoint.

| Dependencia | Responde a | Quién pasa |
|---|---|---|
| `obtener_usuario_actual` | ¿Quién sos? | Cualquier sesión válida y activa |
| `requerir_acceso_edificio` | ¿Podés operar sobre este edificio? | Según la matriz de alcance |
| `requerir_acceso_financiero_edificio` | ¿Podés ver lo financiero de tu unidad acá? | admin_general; admin_consorcio del edificio; propietario/inquilino con unidad en él |
| `requerir_gestion_reclamos_edificio` | ¿Gestionás reclamos y órdenes de trabajo acá? | admin_general; admin_consorcio **o encargado** de ese edificio |
| `requerir_acceso_para_crear_reclamo` | ¿Podés cargar un reclamo o ver datos básicos del edificio? | Lo anterior **o** cualquiera con unidad propia en el edificio |

**Lecciones de diseño que dejó esta capa:**

1. **La lista de edificios del JWT nunca se pobló**, así que la autorización real se resuelve consultando la base en cada dependencia. Funciona y es correcto; lo que no hay que hacer es escribir código que *asuma* que el token trae el alcance. Ver la advertencia de `usuario_edificio` en 3.1.
2. **Una dependencia se reutiliza si la regla coincide, aunque el nombre suene a otro dominio.** `requerir_acceso_para_crear_reclamo` terminó siendo también la regla correcta para "ver los espacios comunes de un edificio": el conjunto de gente es idéntico. Se reutiliza y se documenta el porqué, en vez de escribir una quinta dependencia igual.
3. **Cuidado con el tipo que devuelve la dependencia.** Algunas devuelven el usuario autenticado y otras la entidad ya cargada. Declarar mal el tipo en la firma del endpoint no falla al importar: falla en tiempo de ejecución, cuando alguien usa un atributo que ese objeto no tiene. Ver sección 9.

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

**Dos niveles:**

1. **Tests de servicio** — lógica pura, sin base ni HTTP. Milisegundos. Se prueban con objetos de juguete (`@dataclass`) gracias al *duck typing* de la sección 2.3.
2. **Tests de integración** — router completo contra base real en memoria.

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

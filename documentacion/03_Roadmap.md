# Roadmap del Proyecto — SMART Building (ver3)

> Este es el documento de trabajo del día a día: la bitácora que se sigue tarea por tarea. Toma todo lo definido en el [Documento General](01_Documento_General.md) y el [Documento Técnico](02_Documento_Tecnico.md) y lo organiza en fases, con checklists concretos de tareas chicas.
>
> **Cómo se usa:** cada tarea (`- [ ]`) es un entregable chico y verificable. Se implementa una sola a la vez, en el orden **lógica → backend → frontend** dentro de cada bloque funcional, y se marca como hecha (`- [x]`) recién cuando el usuario la prueba y da luz verde. No se avanza a la tarea siguiente sin esa aprobación. Si al revisar una tarea aprobada aparece un ajuste, se corrige esa misma línea acá — nunca se duplica la tarea. *(`que_hice.html` se usó como bitácora visual tarea por tarea hasta el cierre de la Fase 2 — se eliminó a pedido del usuario el 2026-09-06. De ahora en más, la documentación de lo hecho vive en `documentacion/fases/`: un archivo por fase terminada — ver [`documentacion/fases/Index.md`](fases/Index.md) — en vez de un slide por tarea.)*
>
> **Regla dura de alcance:** dentro de un mismo bloque temático (ejemplo: "Usuarios") no se toca ningún otro dominio (ejemplo: "Edificios") hasta que el bloque activo esté aprobado. El frontend de una tarea muestra únicamente lo ya construido hasta ese punto — nunca una pantalla con secciones de funcionalidades futuras vacías o deshabilitadas.
>
> Estado del documento: **Completo — 14 fases (Fase 0 a Fase 13), cubriendo los 19 módulos del Documento General y las 21 secciones del Documento Técnico.**

---

## Metodología de trabajo

- **Una tarea a la vez, en orden lógica → backend → frontend.** Para cada bloque funcional (ej. "Usuarios y roles") primero se define el modelo de datos y las reglas de negocio (lógica pura, sin HTTP todavía), después los endpoints que la exponen (backend), y recién al final la pantalla que la consume (frontend). El usuario prueba y aprueba en ese mismo orden — puede probar un endpoint desde `/docs` (Swagger) antes de que exista la pantalla.
- **Nunca se implementa más de un bloque funcional en simultáneo.** Está prohibido adelantar pantallas o endpoints de un módulo que todavía no llegó su turno en este Roadmap, aunque la tentación de "ya que estoy" exista — es la causa más común de que algo quede a medio probar.
- **El frontend crece de a una pantalla por vez.** Se arranca con el HTML/CSS del sistema de diseño ya validado (skill `premium-uiux`) sin datos reales, y recién después se conecta a la API real, tarea por tarea. Nunca se construye toda la interfaz de una sola vez ni se deja una pantalla "a medio cablear".
- **Nomenclatura: carpetas en inglés, dominio de negocio en español.** Se respeta tal cual la estructura ya fijada en el Documento Técnico, sección 2.3: carpetas técnicas (`models/`, `schemas/`, `routers/`, `services/`, `core/`) en inglés porque es la convención del stack (FastAPI/SQLAlchemy), pero los archivos, clases, variables y funciones de dominio van en español (`Usuario`, `Edificio`, `Departamento`, `calcular_severidad`, `crear_reclamo`) — el código habla el mismo idioma que esta documentación.
- **Explicación después de cada tarea.** Al terminar una tarea se actualiza `que_hice.html` con un resumen en palabras de qué se hizo y por qué, más el código relevante, antes de pedir la aprobación para seguir.
- **Testing progresivo, no una fase aparte.** Tal como define el Documento Técnico (sección 20), no se escriben tests de CRUDs triviales antes de que el proyecto los necesite. Cada módulo con lógica de cálculo real (severidad del semáforo, prorrateo, conciliación de pagos, solapamiento de reservas, cálculo de estado de activos) suma su suite de tests con pytest como parte de la misma tarea que lo implementa.
- **Usuarios y contraseñas de prueba.** Cada vez que una tarea da de alta un usuario de prueba nuevo (vía seed o a mano durante la validación), sus credenciales quedan documentadas en las primeras diapositivas de `que_hice.html` — son deliberadamente triviales porque el proyecto está en modo test (Documento Técnico, sección 3.2).

---

## Arquitectura técnica (referencia — el detalle completo vive en 02_Documento_Tecnico.md)

No se redefine acá: el Documento Técnico ya la deja cerrada y aprobada. Resumen operativo para no tener que saltar de documento en documento en cada tarea:

- **Backend:** Python 3.12 + FastAPI + SQLAlchemy (ORM) + Pydantic + Uvicorn + SQLite. Un router por dominio, montado en `main.py` bajo el prefijo `/api/`. Autenticación JWT (`python-jose`) + contraseñas hasheadas (`passlib`/bcrypt). Documentación interactiva siempre activa en `/docs`.
- **Frontend:** multi-página estática (sin SPA ni router de JS) — un `.html` por pantalla en `frontend/`, HTML + Tailwind CSS (CDN al inicio, migrado a Tailwind CLI standalone antes de cerrar la etapa de frontend, ver Fase 12) + JavaScript vanilla ES2020+. Sistema de diseño obligatorio: skill `premium-uiux` (`.claude/skills/premium-uiux/`), basada pixel a pixel en `documentacion/mockups/Mockup_3D_Vidrio_Grafito.html`.
- **Estructura de carpetas:** la definida en el Documento Técnico, sección 2.3 — `backend/app/{core,models,schemas,routers,services}` + `frontend/{*.html, assets/{css,js,img}, tailwind.config.js}`.
- **Mobile-first con salto a web:** un único HTML/CSS por pantalla, con los quiebres `640px` y `1024px` ya documentados en la skill — nunca dos maquetados separados.

---

## Fase 0 — Fundación del proyecto

Objetivo: dejar el esqueleto de backend y frontend funcionando y comunicándose entre sí, con el sistema de diseño ya aplicado (sin datos reales todavía), y las herramientas de trabajo del proyecto (arranque, bitácora) operativas. Ninguna funcionalidad de negocio en esta fase.

- [x] **Documentación base del proyecto.**
  Lectura completa de `01_Documento_General.md` y `02_Documento_Tecnico.md`, confirmando que el segundo queda completo y coherente con el mockup aprobado (`Mockup_3D_Vidrio_Grafito.html`) antes de planificar la ejecución.

- [x] **Skill de diseño `premium-uiux`.**
  Creada en `.claude/skills/premium-uiux/` (`SKILL.md` + `references/paleta-color.md` + `references/componentes.md`), documentando token por token y componente por componente el mockup aprobado — paleta acero/grafito, vidrio en dos capas, semáforo de 4 estados, tipografía Outfit/Inter, arquitectura del Dashboard Visual y motor de severidad. Es la fuente de verdad visual obligatoria para toda pantalla nueva de acá en adelante.

- [x] **Backend: estructura de carpetas y entorno virtual.**
  Crear `backend/app/{core,models,schemas,routers,services}/`, entorno virtual de Python y `requirements.txt` (`fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `python-jose[cryptography]`, `passlib[bcrypt]`, `python-multipart`, `qrcode[pil]`).

- [x] **Backend: aplicación FastAPI mínima.**
  `main.py` con la instancia de FastAPI, `CORSMiddleware` habilitando el origen del frontend de desarrollo, y un endpoint de salud (`GET /api/salud`) que confirme que el servidor está activo. `core/config.py` con las rutas y variables de configuración (nombre de la base, orígenes CORS, secreto JWT).

- [x] **Backend: conexión a base de datos.**
  `database.py` con el engine de SQLAlchemy apuntando a `smart_building.db`, la sesión y la `Base` declarativa que van a heredar todos los modelos de las fases siguientes.

- [x] **Frontend: extracción de tokens y componentes del mockup a archivos reales.**
  `frontend/assets/css/tokens.css` con las variables CSS exactas de `references/paleta-color.md` (tema claro + `html[data-theme="dark"]`), y `frontend/assets/css/components.css` con las clases documentadas en `references/componentes.md` (`.shell`, `.content-glass`, `.topbar`, `.kpi*`, `.pill`, `.view-switch`, arquitectura del Dashboard Visual, `.detail`) traducidas a `@layer components` de Tailwind. Se incorpora el CDN de Tailwind (`cdn.tailwindcss.com`) con la configuración inline mínima para que sus utilidades de color lean las variables CSS (`colors: { accent: 'var(--accent)', ok: 'var(--ok)', warn: 'var(--warn)', pend: 'var(--pend)', crit: 'var(--crit)', ... }`).

- [x] **Frontend: "cascarón" base (`frontend/index.html`).**
  Primera página HTML real del proyecto: topbar con marca, botón de tema y avatar (sin backend detrás todavía), fondo atmosférico con textura de grano, toggle de tema funcionando con la View Transitions API — es el "HTML básico con el estilo implementado" que pide la metodología del proyecto, sin ninguna sección de negocio todavía (ni login funcional, ni KPIs, ni edificio).

- [x] **Frontend: `assets/js/api.js`.**
  Wrapper de `fetch()` que centraliza la URL base de la API, agrega el header `Authorization` cuando hay token en `localStorage`, castea la respuesta a JSON y estandariza el manejo de errores (incluyendo el 401 → redirección a `index.html`, aunque el login recién se construye en la Fase 1).

- [x] **Verificación: primera conexión real frontend ↔ backend.**
  El cascarón llama a `GET /api/salud` al cargar y muestra en un indicador visual chico (ej. el punto "sistema en vivo" del techo del edificio, reutilizado como indicador de conexión) si el backend respondió.

- [x] **`iniciar.bat`.** *(Removido más adelante — ver nota de actualización.)*
  Script que levantaba el backend (activaba el entorno virtual e iniciaba Uvicorn), después el frontend (servidor estático de Python en otro puerto) y por último abría el navegador en la URL del frontend. Probado contra el esqueleto de esta misma fase.
  **Actualización (fuera de fase, a pedido del usuario):** se eliminó el archivo. El proyecto pasa a versionarse en GitHub y cada quien levanta backend y frontend a mano en dos terminales — el paso a paso queda en `README.md (raíz del proyecto)`. `frontend/servidor_dev.py` (el servidor sin caché) se sigue usando igual, solo que se ejecuta directo en vez de que lo dispare el script.

- [x] **`que_hice.html`.**
  Bitácora visual del proyecto, con la primera diapositiva documentando esta Fase 0 (arquitectura elegida, skill de diseño, esqueleto backend/frontend) y una tabla de usuarios/contraseñas de prueba que se va completando desde la Fase 1 en adelante.

- [x] **Prueba manual de punta a punta.**
  En su momento: ejecutar `iniciar.bat` desde cero en una máquina limpia y confirmar que backend, frontend y navegador arrancaban solos, con el cascarón mostrando la conexión a `/api/salud` — en mobile y desktop, con el toggle de tema funcionando en ambos. Quedó superado por la actualización de arriba; el arranque manual documentado en `README.md (raíz del proyecto)` cumple el mismo rol.

---

## Fase 1 — Usuarios, autenticación y estructura del edificio

Corresponde al Documento General, secciones 3 (Actores del sistema) y 5 (Gestión de edificios); Documento Técnico, secciones 6 y 7. Es la base de datos de la que depende absolutamente todo lo demás.

### Usuarios y autenticación

- [x] **Lógica: modelo de roles y reglas de acceso (RBAC simple).**
  Se define, antes de escribir código de infraestructura, la matriz de roles completa del Documento Técnico (sección 6.2): `admin_general`, `admin_consorcio`, `encargado`, `propietario`, `inquilino`, `proveedor`, `auditor`, `seguridad`, con su alcance (toda la cartera / un edificio / su unidad) y qué puede gestionar cada uno. Se documenta como la función de autorización que va a reutilizar cada endpoint futuro, sin repetir el chequeo a mano módulo por módulo.

- [x] **Backend: modelo `Usuario` y `UsuarioEdificio`.**
  `backend/app/models/usuario.py`: id, nombre, email (único), password_hash, rol, teléfono, activo, creado_en. `usuario_edificio.py`: tabla puente para que un mismo usuario esté vinculado a más de un edificio con un rol efectivo por vínculo (ej. Administrador General con cartera, propietario con unidades en dos edificios).

- [x] **Backend: hashing de contraseñas y utilidades JWT.**
  `core/security.py`: hash/verificación con `passlib`(bcrypt), generación y decodificación de JWT de corta duración. Ninguna contraseña se guarda ni se loguea en texto plano en ningún punto del código, ni siquiera en modo test.

- [x] **Backend: script de seed del primer Administrador General.**
  `app/seed.py`: crea, si no existe, un usuario Administrador General inicial con credenciales de prueba conocidas — sin esto no hay forma de loguearse la primera vez. Las credenciales generadas quedan documentadas en `que_hice.html` en cuanto esta tarea se aprueba.

- [x] **Backend: endpoint de login.**
  `routers/auth.py`: `POST /api/auth/login` (email + password) → JWT con id, rol y edificios asociados. `GET /api/auth/me` para que el frontend recupere los datos del usuario logueado a partir del token.

- [x] **Backend: dependencia de autorización (`get_current_user`).**
  Dependencia de FastAPI que decodifica el JWT, busca el usuario, valida que esté activo, y expone su rol/edificios — aplicando la matriz de la primera tarea de este bloque. La reutiliza cada endpoint protegido de acá en adelante.

- [x] **Backend: CRUD de usuarios.**
  `routers/usuarios.py`: alta (asociando rol y, si corresponde, edificio/departamento), edición, listado filtrado por edificio según el rol de quien consulta, y baja lógica (`activo=false`, nunca borrado físico, para no perder trazabilidad histórica).

- [x] **Frontend: pantalla de login (`index.html` pasa a ser la pantalla de login real).**
  Formulario con email y contraseña sobre el cascarón ya construido en la Fase 0, mensaje de error claro ante credenciales inválidas, guardado del token en `localStorage` y redirección post-login. Sin selector de rol visible: el rol lo determina el backend.

- [x] **Frontend: pantalla de gestión de usuarios (`usuarios.html`).**
  Listado de usuarios (filtrado por edificio si corresponde al rol), con alta de usuario nuevo (nombre, email, rol, edificio/departamento si aplica) y acción de desactivar. Visible en el menú únicamente para los roles con permiso de gestionar usuarios (Administrador General/Consorcio).

- [x] **Frontend: edición de usuario (`usuarios.html`).**
  Agregada a pedido explícito tras aprobar la tarea anterior — no estaba en el alcance original (solo alta + desactivar). Ícono de editar en cada fila del listado, que abre el mismo modal de alta pero en modo edición, con los datos del usuario cargados. Edita nombre, rol y teléfono vía `PATCH /api/usuarios/{id}` (ya soportado por el backend desde la Tarea 7) — email y contraseña quedan fuera, porque el backend no los acepta por esa vía.

- [x] **Prueba manual de punta a punta.**
  Ejecutar el seed, loguearse con el Administrador General, dar de alta un usuario de cada rol relevante para las pruebas iniciales (un Administrador de Consorcio y un Propietario), confirmar que cada uno ve únicamente lo que le corresponde al loguearse, y que las credenciales de todos quedaron en `que_hice.html`.

### Estructura del edificio

- [x] **Lógica: reglas de alta y estructura vacía automática.**
  Se define cómo, al dar de alta un edificio indicando cantidad de pisos y unidades por piso, se genera automáticamente su estructura vacía (`Piso` + `Departamento` sin propietario todavía) — tal como pide el Documento General, sección 5.1, en vez de cargarla a mano piso por piso.

- [x] **Backend: modelo `Edificio`.**
  `models/edificio.py`: nombre, dirección, ciudad, CUIT/razón social, administrador de consorcio a cargo, días de vencimiento de expensas, política de recargos por mora, activo, creado_en.

- [x] **Backend: modelos `Piso`, `Departamento`, `Cochera`, `EspacioComun`.**
  Tal como los define el Documento Técnico, sección 5.1: `Piso` (edificio, número/orden), `Departamento` (piso, identificador, m², propietario_id/inquilino_id opcionales, estado ocupacional), `Cochera` (edificio, número, fija/rotativa, departamento_id opcional), `EspacioComun` (edificio, nombre, capacidad, reglas de uso).

- [x] **Backend: endpoint de alta de edificio con generación automática de estructura.**
  `routers/edificios.py`: `POST /api/edificios` (solo Administrador General) — crea el edificio y, en la misma operación, sus pisos y departamentos vacíos según la cantidad indicada.

- [x] **Backend: endpoints de configuración y estructura.**
  `PATCH /api/edificios/{id}` (contacto de emergencia, vencimientos, roles habilitados para ese edificio); CRUD anidado de pisos/departamentos/cocheras/espacios comunes bajo `/api/edificios/{id}/...`; endpoint para asignar/desvincular propietario o inquilino a un departamento ya existente.

- [x] **Frontend: pantalla de alta de edificio (`edificios.html`).**
  Formulario con los datos mínimos del Documento General 5.1, visible solo para Administrador General.

- [x] **Frontend: pantalla de estructura del edificio (`edificios.html`, pestaña "Estructura" vía `.view-switch`).**
  Vista en lista (no gráfica todavía — la versión gráfica coloreada es el Dashboard Visual de la Fase 5) de pisos, departamentos, cocheras y espacios comunes de un edificio, con alta de piso/departamento nuevo y asignación de propietario/inquilino. *(Actualización: no existía forma de LLEGAR a un edificio existente — `edificios.html` solo tenía el formulario de alta, sin listado. Se agregó un listado de edificios (mismo patrón que `usuarios.html`) más `GET /api/edificios` y `GET /api/edificios/{id}` en el backend, no itemizados antes como tarea aparte — decisión consultada y confirmada con el usuario antes de implementar.)*

- [x] **Prueba manual de punta a punta.**
  Dar de alta un edificio de prueba ("Torre Central", igual que en el mockup) con estructura de varios pisos, confirmar que se generó automáticamente, asignar el usuario Propietario ya creado a un departamento puntual, y validar que al loguearse como ese propietario solo ve su propia unidad. *(El Dashboard Visual que muestra la unidad propia recién llega en la Fase 5 — hoy "solo ve lo que le corresponde" se verificó como sidebar vacío + bloqueo de pantallas ajenas, mismo criterio que la Tarea 16.)*

---

## Fase 2 — Gestión financiera básica

Corresponde al Documento General, sección 6; Documento Técnico, sección 8. De acá sale directamente el dato de morosidad que después colorea de amarillo/rojo un departamento en el Dashboard Visual (Fase 5).

- [x] **Lógica: criterio de prorrateo.**
  Se define el cálculo antes de tocar modelos — es la pieza más delicada del módulo porque un error afecta a todos los propietarios a la vez. *(Actualización: validado contra la normativa argentina real antes de implementar, a pedido del usuario — Ley 13.512 / Código Civil y Comercial, arts. 2037 y ss. El criterio real es un **coeficiente (%) fijo por departamento** — no "partes iguales o por m²" como criterio global. "Partes iguales" y "por m²" quedan como atajos para completar el coeficiente la primera vez, editables después desde una pantalla de Configuración. `services/finanzas.py` implementado y probado — 18 tests nuevos. Investigación legal completa en `documentacion/investigaciones/Prorrateo.md`.)* *(Corrección 2026-09-08: la "pantalla de Configuración" quedó pendiente en silencio — nunca existió ningún endpoint para cargar `coeficiente`, solo se podía a mano en la base. Se encontró recién al intentar generar una expensa para un edificio de prueba distinto ("Hay departamentos sin coeficiente cargado"). Se construyó `PATCH /api/edificios/departamentos/{id}/coeficiente` (manual) + `POST /api/edificios/{id}/coeficientes/auto` (partes iguales/por m², reutilizando `services/finanzas.py`) y su UI en `edificios.html` → Estructura, con un resumen en vivo de la suma. De paso se corrigió un bug real de precisión: los atajos redondeaban a 4 decimales pero `Departamento.coeficiente` solo guarda 3 (`Numeric(6,3)`), así que la suma dejaba de dar 100% recién al persistir en edificios con muchas unidades (28, en el caso real que lo disparó) — corregido a 3 decimales en `services/finanzas.py`, con test de regresión. Detalle completo en `Prorrateo.md`, sección 7.)*

- [x] **Backend: modelo `Gasto`.**
  Rubro, monto, fecha, descripción, proveedor asociado (opcional, se conecta de verdad recién en la Fase 7), activo asociado (opcional, se conecta en la Fase 4). *(Corrección de bookkeeping: esta tarea ya estaba hecha y aprobada desde la Tarea 2 — el checkbox había quedado sin tildar por error, detectado en la revisión completa de la Fase 2.)*

- [x] **Backend: modelos `Expensa` y `ExpensaDetalle`.**
  `Expensa`: liquidación de un edificio para un período, con total. `ExpensaDetalle`: apertura por rubro dentro de esa expensa — la transparencia de gasto que pide explícitamente el Documento General 6.1.

- [x] **Backend: modelo `Pago`.**
  Departamento, expensa correspondiente, monto, fecha, medio de pago, comprobante adjunto — soporta pago parcial o total.

- [x] **Backend: modelos `Fondo`, `MovimientoFondo`, `Caja`.**
  Fondo de reserva y otros fondos especiales con sus movimientos, separados del flujo corriente; caja chica del edificio con responsable. *(Corrección: el primer diseño de `Caja` no tenía movimientos propios — investigado en `documentacion/investigaciones/Caja_chica.md` tras la duda del usuario, se agregó `monto_fijo` y el modelo `MovimientoCaja`, siguiendo el sistema real de "fondo fijo" de una caja chica.)*

- [x] **Backend: modelos `Presupuesto` y `Factura`.**
  Para sostener la trazabilidad completa gasto → presupuesto → factura → pago (Documento General 6.7-6.8).

- [x] **Backend: servicio de prorrateo automático.**
  `services/finanzas.py`: dado un período y el criterio configurado del edificio, calcula cuánto le corresponde a cada departamento.

- [x] **Backend: generación de expensa mensual.**
  `POST /api/edificios/{id}/expensas`: toma los gastos del período, aplica el prorrateo, genera `Expensa` + `ExpensaDetalle` por departamento. *(Ampliación 2026-09-09, a pedido explícito del usuario: se permite regenerar la ÚLTIMA expensa de un edificio (nunca una anterior) para corregir un gasto o coeficiente cargado mal después de emitirla — excepción deliberada y acotada a la inmutabilidad de `Prorrateo.md` sección 6, con confirmación obligatoria (`409` primero, `confirmar_reemplazo: true` para ejecutar) y sin un `confirm()` del navegador — el propio formulario de "Generar expensa" pasa a modo confirmación. Detalle completo en `Prorrateo.md`, sección 8.)*

- [x] **Backend: registro de pagos y conciliación.**
  `POST /api/departamentos/{id}/pagos`: registra el pago, actualiza si la expensa queda saldada o parcial. *(Ampliada a pedido explícito del usuario: medio de pago del edificio (CBU/alias — investigado en `documentacion/investigaciones/Pagos_y_Conciliacion.md`; un QR de pago instantáneo real requiere ser/integrar un PSP registrado y queda fuera de alcance, y el propio usuario terminó prefiriendo directamente copiar CBU/alias por separado, sin QR de ningún tipo) y carga de pago por el propio usuario logueado (`POST /api/pagos`, sin elegir edificio/piso — resuelve sus propios departamentos), naciendo en estado `pendiente` hasta que un Administrador lo concilie (`PATCH /api/pagos/{id}/estado`). `GET /api/mis-departamentos` cubre de paso el "estado de cuenta por unidad" del Documento General 6.2.)*

- [x] **Backend: cálculo de deudores.**
  `GET /api/edificios/{id}/deudores` (vista calculada, no tabla propia — Documento Técnico 5.2): antigüedad de deuda en meses por departamento. Este es el dato que va a alimentar `deudaSeverity()` en la Fase 5.

- [x] **Backend: endpoints CRUD de Gastos, Fondos, Caja, Presupuestos, Facturas.**
  Todos anidados bajo edificio.

- [x] **Backend: endpoint de reportes financieros.**
  `GET /api/edificios/{id}/reportes/financiero`: recaudado vs. esperado, morosidad, evolución de gastos por rubro — la data cruda para Analítica (Fase 6). *(Ajuste tras revisar toda la Fase 2 ya construida: gran parte de esta data ya existe, esta tarea consolida en un solo endpoint, no recalcula de cero — morosidad sale de `/deudores` (Tarea 10), evolución de gastos por rubro de `/gastos` con el filtro de período ya soportado (Tarea 11), y recaudado vs. esperado de `Expensa.total` contra la suma de `Pago` `confirmado` por período (Tareas 8-9).)*

- [x] **Frontend: `financiero.html` — cascarón con pestañas (`.view-switch`) y pestaña "Gastos".**
  Se crea la página con el selector segmentado que va a organizar todo el módulo (Gastos/Expensas/Pagos/Deudores/Fondos·Caja·Presupuestos·Facturas — Documento Técnico, sección 4.1), con la primera pestaña funcional: carga y listado de gastos, filtro por rubro y rango de fechas. *(Nota: es una pantalla de gestión — Administrador General/de Consorcio — ya con el endpoint real detrás desde la Tarea 11, `GET/POST /api/edificios/{id}/gastos` con filtro `?anio=&mes=`.)* *(Corrección 2026-09-09, a pedido del usuario tras usar la app de verdad: (1) se sumó `PATCH /api/edificios/{id}/gastos/{id}` + botón de editar en cada fila — antes un gasto mal cargado no se podía corregir, había que borrar y recargar todo el edificio a mano. Editar un gasto nunca reabre una expensa ya generada (foto fija, `Prorrateo.md` sección 6), solo afecta a la próxima que se genere. (2) Bug real de UI, reportado desde el celular: el modal de detalle de expensa (con muchos rubros/departamentos) no entraba en la pantalla y no se podía scrollear — `.modal` (componente compartido de toda la skill, `componentes.md`) nunca tuvo `max-height`/`overflow-y`. Corregido en un solo lugar, arregla todos los modales del proyecto por igual.)* *(Corrección 2026-09-09, a pedido del usuario: el campo Monto de "Nuevo/Editar gasto" pasó de `<input type="number">` a un campo de texto con separador de miles en vivo (`.` cada 3 dígitos, `,` decimal — mismo formato que ya usa `assets/js/moneda.js` para mostrar montos, ahora también para cargarlos) — `assets/js/monto-input.js`, nuevo y reutilizable, documentado en `componentes.md`.)*

- [x] **Frontend: pestaña "Expensas".**
  Vista de generación/detalle (Administrador) y "Mi cuenta" (Propietario/Inquilino — mismo archivo, rama de rol distinta). *(Corrección de bookkeeping: esta tarea ya estaba hecha y aprobada desde la Tarea 14 (`que_hice.html`, slide `f2-t14`) — el checkbox había quedado sin tildar por error. La decisión sobre Inquilino se resolvió con el usuario y quedó registrada más abajo: se le muestra igual que al Propietario, a propósito, hasta la Fase 11 — no es una inconsistencia heredada sin resolver.)*

- [x] **Frontend: pestaña "Pagos".**
  Carga de pago contra una expensa, con confirmación de saldo pendiente si es parcial. Son dos vistas distintas sobre el mismo backend de la Tarea 9, no una sola pantalla — (1) la del Administrador, una cola de `Pago` en estado `pendiente` para conciliar (`PATCH /api/pagos/{id}/estado`); (2) la del propio Propietario/Inquilino, que carga SU pago sin elegir edificio ni piso (`POST /api/pagos`, resuelve sus departamentos solo) — Inquilino ve esta segunda vista igual que el Propietario, misma decisión ya registrada abajo. *(Se sumó `GET /api/edificios/{id}/pagos`, nuevo — la Tarea 9 nunca había construido un listado, solo alta y cambio de estado puntual. El "confirmación de saldo pendiente si es parcial" se resuelve con un aviso in-line al cargar un monto menor al saldo, no con un `confirm()` del navegador. Detalle completo, con evidencia de Playwright, en `Pagos_y_Conciliacion.md` sección 7 y `que_hice.html`, slide `f2-t15`.)*

- [x] **Frontend: pestaña "Deudores".**
  Listado ordenado por antigüedad, con detalle de las expensas impagas de cada departamento — usa tal cual `GET /api/edificios/{id}/deudores` (Tarea 10), sin cambios de backend. *(⚠️ Auditor queda afuera por ahora, a propósito: la matriz de roles (`services/autorizacion.py`) le da `ve_financiero_edificio: True` de solo lectura, pero hoy no existe ningún mecanismo real que defina A QUÉ edificios tiene acceso un Auditor puntual — la tabla `UsuarioEdificio` (pensada para esto desde la Fase 1) nunca se llegó a poblar, y darle acceso a toda la cartera sin ese vínculo sería el mismo tipo de sobre-permiso que ya se dejó registrado para Inquilino más arriba. La Fase 11 ya tiene las tareas "registro de auditoría" y "pantalla de auditoría" pensadas exactamente para esto — ahí se resuelve el vínculo Auditor↔edificio y se habilita esta pestaña para ese rol, no antes.)*

- [x] **Frontend: pestaña "Fondos, Caja, Presupuestos y Facturas".**
  Resuelto como una única pestaña principal ("Fondos") con su propia sub-navegación de 4 secciones — con datos reales, sumar los 4 como botones del `.view-switch` principal (junto a Gastos/Expensas/Pagos/Deudores) daba 8 pestañas en la misma fila, demasiado para el flujo principal; agruparlas mantiene la jerarquía clara. Sin cambios de backend, los 4 CRUD ya estaban probados desde la Tarea 11. *(Dos bugs reales encontrados y corregidos con Playwright antes de aprobar: (1) el saldo de un fondo mostraba el valor viejo tras cargar un movimiento — el modal se refrescaba con el caché sin haber vuelto a pedir el listado primero; (2) el `<select>` de responsable de la caja chica, oculto vía `display:none` cuando el rol logueado no puede ver `/usuarios` (admin_consorcio), bloqueaba el submit del formulario EN SILENCIO — Chromium no puede enfocar un campo `required` no renderizado para rechazarlo, así que el evento `submit` nunca llegaba a dispararse. Se sacó el `required` nativo de ese campo, la validación real quedó a cargo del JS del formulario. Responsable de la caja: admin_general elige de un `<select>` real (`GET /api/usuarios`); admin_consorcio, que no tiene ese endpoint disponible, cae a un campo de ID numérico — no existe hoy ningún directorio de usuarios accesible para ese rol.)*

- [x] **Prueba manual de punta a punta.**
  Cargar gastos de un mes de prueba, generar la expensa del edificio de prueba, pagar completo en algunos departamentos y dejar otros en deuda de distinta antigüedad, y confirmar que el endpoint de deudores calcula bien meses y monto en cada caso. Hecha de punta a punta con el frontend real (no solo backend) a lo largo de las Tareas 14-16 y las correcciones posteriores: **Torre Cierre Fase 1** — Ago/Sep confirmadas (Al día), Octubre con pagos en los 3 estados (confirmado/pendiente/rechazado) dejándola en deuda; **Torres Independencia 3252** (28 unidades) — coeficientes autocompletados, expensa generada y regenerada tras corregir un gasto, Deudores mostrando 12 departamentos con `meses_atraso` y `deuda_total` correctos. En el camino se encontraron y corrigieron con datos reales (no hipotéticos) tres huecos genuinos que un ejercicio de punta a punta real tenía que encontrar: la pantalla de Configuración de coeficientes (nunca se había construido), la edición de un gasto ya cargado, y el modal de detalle de expensa sin scroll en mobile — exactamente el propósito de esta tarea.

**⚠️ Decisión registrada (Fase 2 completa, 2026-09-05): Inquilino sigue viendo/pagando financiero de su unidad, a propósito, hasta la Fase 11.** La matriz de roles (`services/autorizacion.py`, Fase 1) fija `ve_financiero_unidad: False` para Inquilino por defecto, "habilitable por excepción recién en la Fase 11" — pero esa bandera nunca se llegó a *aplicar* en ningún endpoint (verificado: cero referencias fuera de la matriz y sus tests), y el backend de la Tarea 9 (`GET /api/mis-departamentos`, `POST /api/pagos`) trata a Propietario e Inquilino exactamente igual. Consultado con el usuario: se **deja así deliberadamente** — más práctico para probar la app mientras el sistema de excepciones de la Fase 11 no existe todavía. Cuando esa fase llegue, este es el punto exacto a revisar: restringir el default a `False` para Inquilino y exponer la excepción puntual por unidad que la matriz ya anticipa.

---

## Fase 3 — Reclamos y mantenimiento

Corresponde al Documento General, secciones 10 y 11; Documento Técnico, secciones 12 y 13. Se implementan juntas: un reclamo puede dar origen a una orden de trabajo.

- [x] **Lógica: flujo de estados de reclamo y niveles de prioridad.**
  Se fija el flujo (recibido → asignado → en curso → resuelto → cerrado) y el significado exacto de leve/medio/crítico (Documento General 11.3) antes de modelar — es lo que después determina amarillo vs. rojo en el Dashboard Visual. `services/reclamos.py`: `transicion_valida()` (tabla de transiciones válidas) y `color_por_prioridad()` (leve/medio → `warn`, crítico → `crit`, tal como fija Documento Técnico sección 13) — 10 tests nuevos. *(Decisión de diseño, no fijada explícitamente por el enunciado: se permite `resuelto → en_curso` como única excepción al flujo lineal — si quien reclamó confirma que el problema sigue, se reabre el mismo reclamo en vez de perder su historial de comentarios/fotos cargando uno nuevo. `cerrado` queda siempre terminal a propósito: la recurrencia ya la resuelve el Documento General 11.5 con un reclamo NUEVO, no reabriendo uno viejo.)*

- [x] **Backend: modelos `Reclamo`, `ReclamoFoto` y `ReclamoComentario`.**
  `edificio_id` (siempre), y el objetivo puntual — `departamento_id` opcional, `espacio_comun_id` opcional, o ninguno de los dos si es sobre el edificio en general (Documento General 11.1: "su unidad, un espacio común, o el edificio en general" son las 3 opciones reales, no solo unidad/espacio; `CheckConstraint` impide cargar los dos a la vez). Descripción, prioridad (`leve`/`medio`/`critico`, validada contra `services/reclamos.py::PRIORIDADES`), estado (`services/reclamos.py::ESTADOS`, nace en `recibido`), `creado_por_id`/`creado_en`. *(Ajuste sobre lo escrito en la revisión de fase: `fotos` termina siendo su propia tabla, `ReclamoFoto` (reclamo_id + url), no una lista de URLs aplastada en un campo de texto — mismo criterio que `OtEvidencia`/`ActivoFoto`, planeadas como tablas propias más abajo en esta misma fase y en la Fase 4; sigue sin haber upload real de archivos en ningún lado del proyecto, solo la URL.)* Hilo de comentarios (`ReclamoComentario`) entre quien reclama y quien gestiona. 9 tests nuevos.

- [x] **Backend: modelos `OrdenTrabajo` y `OtEvidencia`.** `services/reclamos.py` sumó `TIPOS_OT`/`ESTADOS_OT`/`transicion_valida_ot()` (16 tests en total del servicio). 8 tests nuevos de modelo.
  Tipo (preventivo/correctivo/programado/emergencia), espacio común afectado (`espacio_comun_id`, opcional — ya existe desde la Fase 1), prioridad, estado (`pendiente`/`en_curso`/`resuelta` — **flujo propio, distinto del de `Reclamo`**: Documento Técnico sección 12 fija solo estos 3 para la orden de trabajo, sin "asignado" ni "cerrado"; conviene sumar sus propias `ESTADOS_OT`/`transicion_valida_ot()` en `services/reclamos.py` junto a las de Reclamo, no reinterpretar las de Reclamo para esto), fechas de creación/inicio/cierre, costo, reclamo_id opcional (trazabilidad "quién lo pidió" → "qué se hizo"). **`activo_id`** queda como entero suelto sin `ForeignKey` real — mismo criterio ya usado por `Gasto.activo_id`/`Gasto.proveedor_id` (Fase 2): no hace falta esperar a `core/migraciones.py` para esto, un `Column(Integer, nullable=True)` sin FK no depende de que la tabla destino ya exista, solo la FK real sí. Se conecta de verdad recién cuando la Fase 4 cree `Activo` — ver la nota en esa fase (ahí si hace falta `core/migraciones.py`, para agregar la `ForeignKey` sobre una tabla que ya tiene filas). Asignación (decisión consultada con el usuario, 2026-09-09): `encargado_id` (FK real a `Usuario` con rol `encargado` — ese rol ya existe con login desde la Fase 1, se puede asignar de verdad) **y/o** `proveedor_id` (entero suelto, sin FK real — mismo criterio que `Gasto.proveedor_id`/`Presupuesto.proveedor_id` de la Fase 2, se conecta de verdad recién cuando exista el modelo `Proveedor` real de la Fase 7). `OtEvidencia`: URL de la foto (mismo criterio que arriba, sin upload real todavía), antes/después, subido_por, fecha.

- [x] **Backend: ciclo de vida del reclamo.**
  `routers/reclamos.py`: crear (`POST /api/edificios/{id}/reclamos`, con `fotos` como lista de URL → filas `ReclamoFoto`), listar del edificio para gestión (`GET /api/edificios/{id}/reclamos`, filtros `estado`/`prioridad`), `GET /api/mis-reclamos` (los propios, cualquier rol), detalle (`GET /api/reclamos/{id}`, con `fotos`/`comentarios` anidados), comentar (`POST .../comentarios`) y cambiar de estado (`PATCH .../estado`) usando `services/reclamos.py::transicion_valida()` — nunca una validación de transición repetida a mano acá. Reglas de quién puede qué: Administrador/Encargado del edificio mueven el flujo normal (recibido→asignado→en_curso→resuelto→cerrado); quien lo creó puede comentar en cualquier estado y es el único, además de Administrador/Encargado, habilitado para la excepción `resuelto→en_curso` (confirma que el problema sigue). Siempre consultable por quien lo creó, en cualquier estado.
  **Gap real encontrado y corregido al empezar esta tarea**: el rol `encargado` existe con `alcance: ALCANCE_EDIFICIO` desde la Fase 1, pero nunca existió un vínculo real Encargado↔Edificio (a diferencia de `admin_consorcio_id`) — sin esto, "gestión de reclamos por Encargado" no tenía forma de resolverse. Se agregó `Edificio.encargado_id` (mismo patrón que `admin_consorcio_id`: campo del modelo, de `EdificioConfiguracion`/`EdificioResumenSalida`/`EdificioSalida`, validado en `configurar_edificio()` contra un Usuario real con `rol == "encargado"`). Dos dependencias nuevas en `core/dependencies.py`: `requerir_gestion_reclamos_edificio` (admin_general siempre; admin_consorcio/encargado solo si son los de ESE edificio) y `requerir_acceso_para_crear_reclamo` (superset: además, cualquiera con una unidad propia en el edificio). 21 tests nuevos en `test_reclamos.py` (creación con los 3 objetivos posibles, RBAC de listado/detalle/comentario, las 4 variantes de `cambiar_estado_reclamo` incluida la reapertura).

- [x] **Backend: generación de orden de trabajo desde un reclamo.**
  `routers/ordentrabajo.py`, `POST /api/reclamos/{id}/orden-trabajo` (gestión del edificio): crea la `OrdenTrabajo` vinculada (`reclamo_id`, `edificio_id`/`espacio_comun_id` heredados del reclamo), con `tipo` obligatorio y `prioridad`/`descripcion` heredadas del reclamo si no se especifican explícitas. Bloqueada para un reclamo ya `resuelto`/`cerrado`, y si ya existe una OT activa (no `resuelta`) vinculada a ese mismo reclamo — pero una OT ya `resuelta` nunca bloquea generar una nueva (reapertura del reclamo). Generar la OT es, en los hechos, el acto de asignar el reclamo: si estaba `recibido`, pasa a `asignado` acá mismo (vía `transicion_valida()`, nunca a mano). `sincronizar_reclamo_al_resolver_ot()` queda lista en el mismo archivo — cuando esa orden pasa a `resuelta` (su propio estado final, distinto del "cerrado" de `Reclamo` — ver nota de la Tarea 3), el reclamo pasa automáticamente a "resuelto" (vía `transicion_valida()`, mismo mecanismo que un cambio de estado manual — si el reclamo ya estaba en otro estado terminal por otra vía, no se fuerza la transición) — pero el único disparador real (el endpoint que cambia el estado de una OT) es la próxima tarea, así que acá se prueba llamándola directo. 14 tests nuevos en `test_ordenes_trabajo.py`.

- [ ] **Backend: gestión de órdenes de trabajo (incluidas las manuales).**
  Crear sin reclamo previo, asignar/reasignar un Encargado real o un `proveedor_id` suelto (ver nota de la tarea de modelos), cambiar estado (`pendiente`/`en_curso`/`resuelta`, propio de OT — ver nota de la tarea de modelos), cargar evidencia y costo al cerrar. Pasar a `en_curso` exige tener alguien asignado (Encargado o `proveedor_id` cargado) — nunca una orden "en curso" sin nadie real haciéndola.

- [ ] **Backend: cálculo de tiempo de resolución.**
  Para reclamos y para órdenes de trabajo, por separado — alimenta el Dashboard General (Fase 6).

- [ ] **Backend: servicio de "peor estado" por departamento.**
  `services/severidad.py`: `reclamoSeverity()` y `otSeverity()` tal como quedaron documentados en la skill `premium-uiux` (`otSeverity()` solo puede devolver `ok` o `pend`, nunca `warn`/`crit`) — el dato exacto que va a consumir el Dashboard Visual en la Fase 5. Primer módulo con lógica de cálculo no trivial: suma su test con pytest en esta misma tarea (Documento Técnico, sección 20).

- [ ] **Frontend: pantalla de creación de reclamo.**
  Para Propietario/Inquilino: elegir el objetivo (su propia unidad — auto-seleccionada si tiene una sola, mismo criterio que Pagos en la Fase 2 —, un espacio común del edificio, o "todo el edificio"), descripción, foto (campo de URL/link por ahora, sin carga de archivo real — mismo criterio que el comprobante de un Pago), prioridad percibida con explicación breve de qué significa cada nivel (Documento General 11.3, texto ya definido en la Tarea 1).

- [ ] **Frontend: pantalla de seguimiento de reclamos.**
  Vista de quien lo creó (estado + comentarios + botón de reabrir si está "resuelto" y el problema sigue) y vista de Administrador/Encargado (todos los reclamos del edificio, filtro por estado/prioridad, cambio de estado, generar la orden de trabajo).

- [ ] **Frontend: pantalla de órdenes de trabajo.**
  Para Administrador/Encargado por ahora: listado, asignar un Encargado real (selector) o anotar un `proveedor_id` (campo numérico simple, sin selector — mismo criterio que otros campos "sin FK real hasta la Fase 7"), cambiar estado, cerrar con evidencia y costo. La vista de autogestión para el rol Proveedor (ver "sus" OT asignadas, `ALCANCE_OTS_ASIGNADAS` de la matriz de roles de la Fase 1) queda pendiente de la Fase 7: recién ahí existe un `Proveedor` real vinculado a un login, no antes.

- [ ] **Prueba manual de punta a punta.**
  Crear un reclamo crítico, generar su orden de trabajo, asignarle un Encargado de prueba real, cerrarla con evidencia y costo, confirmar que el reclamo pasa a "resuelto" solo y que el tiempo de resolución quedó calculado. Probar además la excepción `resuelto → en_curso`: reabrir el reclamo ya resuelto y confirmar que vuelve a aparecer en el listado de gestión.

---

## Fase 4 — Activos y seguridad normativa

Corresponde al Documento General, sección 9; Documento Técnico, sección 11. Junto con el Dashboard Visual, es uno de los dos pilares del diferencial competitivo (Documento General, sección 4).

- [ ] **Lógica: regla de estado del activo por vencimiento.**
  Verde si falta bastante para el próximo mantenimiento, amarillo si vence en ≤30 días, rojo si ya venció sin registrarse — se define antes de modelar porque el estado nunca se guarda a mano, siempre se calcula.

- [ ] **Backend: modelo `Activo`.**
  Tipo, código único (ej. `MAT-P3-01`), ubicación (piso o espacio común), fotos (URL suelta, mismo criterio que el resto del proyecto — sin upload real todavía), proveedor responsable (`proveedor_id` suelto, sin FK real hasta la Fase 7 — igual que en `OrdenTrabajo`), garantía, manual (vínculo documental, se conecta en la Fase 7), próximo mantenimiento, costos acumulados (calculado). *(⚠️ Con `Activo` ya existiendo, conectar acá `OrdenTrabajo.activo_id` (Fase 3) de verdad: ya es una columna entera real desde que se creó, así que no hace falta `core/migraciones.py` para esto — alcanza con agregarle `ForeignKey("activos.id")` y su `relationship()` en el modelo, en el código Python, nada que tocar en la base ya existente.)*

- [ ] **Backend: modelo `ActivoFoto`.**
  Registro fotográfico de estado actual/instalación.

- [ ] **Backend: servicio de cálculo de estado del activo.**
  `services/activos.py`, aplicando la regla de la primera tarea — mismo servicio que va a alimentar la franja "Activos y equipamiento común" del Dashboard Visual (Fase 5). Suma test con pytest.

- [ ] **Backend: generación de código QR al alta.**
  Librería `qrcode` de Python: genera el PNG apuntando a `frontend/activos.html?id={activo_id}` y lo guarda junto a la ficha.

- [ ] **Backend: endpoints CRUD de `Activo`.**
  Alta, listado filtrable por tipo/ubicación, detalle, edición.

- [ ] **Backend: endpoint de historial y costos acumulados de un activo.**
  Se arma consultando las `OrdenTrabajo` (Fase 3) que lo tienen como afectado — no es una tabla nueva.

- [ ] **Frontend: pantalla de alta de activo.**
  Tipo, ubicación, proveedor responsable, próximo mantenimiento, fotos.

- [ ] **Frontend: pantalla de listado de activos.**
  Todos los activos con su semáforo visible de un vistazo, filtro por tipo/ubicación — anticipo, en chico, de la franja del Dashboard Visual.

- [ ] **Frontend: pantalla de ficha de activo.**
  QR para imprimir, fotos, historial, costos acumulados, documentos vinculados.

- [ ] **Prueba manual de punta a punta.**
  Dar de alta un matafuego con vencimiento en 20 días (debe quedar amarillo) y un ascensor ya vencido (debe quedar rojo); generar desde la Fase 3 una orden de recarga para el vencido, cerrarla con nueva fecha, y confirmar que vuelve a verde solo.

---

## Fase 5 — Dashboard Visual del Edificio (la funcionalidad diferencial)

Corresponde al Documento Técnico, sección 1.2 y 1.3. El diseño y la interacción ya están validados pixel a pixel en `Mockup_3D_Vidrio_Grafito.html` y documentados en la skill `premium-uiux` — esta fase **conecta esa plantilla a datos reales** de las Fases 1 a 4. No se rediseña nada.

- [ ] **Backend: endpoint de estado agregado del edificio.**
  Para un edificio, el estado (verde/amarillo/naranja/rojo) de cada departamento bajo cada una de las 4 vistas (general/incidentes/deudores/mantenimiento), aplicando la regla de precedencia (Documento Técnico 1.2.1: gana el más grave entre `reclamoSeverity()`, `deudaSeverity()`, `otSeverity()`). Combina Fase 2 (deudores), Fase 3 (peor reclamo/OT por departamento) y Fase 4 (activos ubicados en la unidad, si aplica).

- [ ] **Backend: endpoint de resumen por piso.**
  Estado dominante de cada piso (el peor entre sus departamentos) — el dato que colorea cada `.floor`/`.floor-row` antes de expandirlo.

- [ ] **Backend: endpoint de activos para la franja de mobiliario.**
  Lista los activos del edificio (Fase 4) con su estado ya calculado, en el formato que espera `.assets-row`.

- [ ] **Frontend: `dashboard.html` — cascarón del Dashboard Visual con datos reales.**
  Se porta la arquitectura de contenedores documentada en `references/componentes.md` (`.visual-card` → `.scene` → `.building` → `#floors`/`.lobby` → `.assets`) tal cual, reemplazando `buildingData`/`assetsData` de ejemplo por las respuestas de los tres endpoints anteriores. Techo con nombre/dirección real del edificio; funciona con cualquier cantidad de pisos, no solo los 7 del mockup.

- [ ] **Frontend: selector de vista conectado a datos reales.**
  El `.view-switch` (General/Incidentes/Deudores/Mantenimiento) ya resuelto visualmente se conecta al endpoint de estado agregado — cambiar de vista vuelve a pedir/recolorear sin dejar estado pegado de la vista anterior.

- [ ] **Frontend: expansión de piso con departamentos reales.**
  Al tocar un `.floor-row`, se muestran los `.unit-card` reales de ese piso con su severidad — mismo mecanismo de acordeón `grid-template-rows` ya validado.

- [ ] **Frontend: panel de detalle (`.detail`) con datos reales — "ficha 360°".**
  Al seleccionar un departamento se pide su detalle completo (propietario/inquilino, m², reclamos abiertos, estado de expensas si el rol tiene permiso, OT activas, activos ubicados ahí) y se muestra en la hoja inferior (mobile) o panel lateral fijo (desktop, ≥1024px) — ambos ya construidos en la skill, solo se reemplazan los datos de ejemplo.

- [ ] **Frontend: franja de mobiliario y activos con datos reales.**
  Reemplaza los `.asset-chip` de ejemplo por los activos reales, con el mismo clic hacia el panel de detalle.

- [ ] **Frontend: verificación de responsive y tema sobre datos variables.**
  Se reutiliza tal cual la arquitectura de layout — esta tarea solo confirma que sigue funcionando igual de bien con un edificio de más/menos pisos que el mockup, nombres de departamento más largos, y que el toggle de tema (con View Transitions) sigue andando sobre datos reales.

- [ ] **Decisión: variante "piso completo".**
  Con datos reales ya conectados, se decide si la variante documentada en la skill (`references/componentes.md`, "piso completo") se ofrece como preferencia visual configurable por usuario o se descarta — no se implementa sin que esta decisión quede tomada primero.

- [ ] **Prueba manual de punta a punta.**
  Con el edificio de prueba ya cargado (reclamos, deudas, activos reales de fases anteriores), verificar que el Dashboard Visual pinta cada departamento según la regla de precedencia, que las 4 vistas cambian el color correctamente, que el panel de detalle trae información real, y que se ve y funciona igual en mobile y en desktop.

---

## Fase 6 — Dashboard General y Analítica

Corresponde al Documento Técnico, secciones 1.1 y 17. El diseño de las tarjetas KPI ya está validado en la skill — se conectan a datos reales y se suma Analítica, que todavía no tiene pantalla propia.

- [ ] **Backend: endpoint de KPIs del Dashboard General.**
  Un solo endpoint con los widgets del Documento Técnico 1.1: estado del edificio (verde/amarillo/naranja/rojo agregado), estado financiero (% recaudado, morosidad), reclamos abiertos por prioridad, ranking de deudas, mantenimientos abiertos/en curso/programados, riesgos normativos (activos vencidos/por vencer), KPIs de gestión (tiempo de resolución, costo acumulado del mes).

- [ ] **Backend: control de detalle por rol en los KPIs.**
  Un Encargado ve Reclamos y Mantenimientos con el mismo detalle que un Administrador, pero Estado financiero le llega solo como semáforo general sin montos (Documento Técnico 1.1, nota de diseño) — se resuelve en el mismo endpoint, no filtrando después en el frontend.

- [ ] **Frontend: `dashboard.html` — grilla de KPIs con datos reales.**
  Se porta el patrón bento ya documentado (2 `.kpi--hero` + 4 `.kpi-metric`, `references/componentes.md`) reemplazando los valores de ejemplo del mockup, con el layout responsive ya validado (2/4/6 columnas).

- [ ] **Backend: endpoints de series para Analítica.**
  Uno por gráfico (Documento Técnico, sección 17): gastos mensuales por rubro, evolución de morosidad, evolución financiera, reclamos por prioridad/mes, tiempo de resolución, ranking de proveedores, costos por activo, historial de fallas por tipo de activo.

- [ ] **Frontend: pantalla de Analítica (`analitica.html`).**
  Primera pantalla nueva de esta sección. Se define acá qué librería de gráficos liviana se usa (queda como estándar del proyecto de acá en más) y se aplican las reglas de la skill `dataviz` (paleta accesible, forma de gráfico apropiada al dato), manteniendo el semáforo funcional como el único sistema de color con licencia para representar estado. Filtro por rango de fechas y, si el rol es Administrador General, por edificio.

- [ ] **Prueba manual de punta a punta.**
  Confirmar que los KPIs del Dashboard General coinciden con los mismos números que muestra el Dashboard Visual de la Fase 5 (mismos reclamos, deudores, activos por vencer), y que los gráficos de Analítica reflejan el historial cargado.

---

## Fase 7 — Gestión documental y proveedores

Corresponde al Documento General, secciones 7 y 8; Documento Técnico, secciones 9 y 10. Comparten terreno: contratos/garantías de un proveedor viven en documental, y su historial se arma con las `OrdenTrabajo` ya existentes de la Fase 3.

### Gestión documental

- [ ] **Lógica: tabla de visibilidad por categoría.**
  Se traslada la tabla del Documento General, sección 7 (reglamento visible para todos, contrato solo para Administrador General/Auditor, etc.) a una regla única y reutilizable — no se repite el chequeo a mano por categoría.

- [ ] **Backend: modelo `Documento`.**
  Edificio, categoría (reglamento/contrato/acta/seguro/garantía/manual/certificado/legal), archivo, subido_por, fecha, fecha de vencimiento (nullable — dispara el estado de activos cuando aplica).

- [ ] **Backend: endpoints de carga, listado y descarga.**
  Aplicando la regla de visibilidad de la tarea anterior.

- [ ] **Backend: vínculo de documentos con activos.**
  El "manual" y "certificado" de un `Activo` (Fase 4) pasan a apuntar a `Documento` en vez de ser campos sueltos.

- [ ] **Frontend: pantalla de gestión documental.**
  Listado filtrable por categoría, subida (si el rol tiene permiso) y descarga.

### Proveedores

- [ ] **Backend: modelo `Proveedor`.**
  Nombre/razón social, contacto, exclusivo del consorcio vs. también atiende trabajos particulares — el dato diferencial del Documento General 8.1. *(⚠️ Acá se conectan de verdad los `proveedor_id` sueltos que quedaron sin FK real en fases anteriores: `Gasto`/`Presupuesto` (Fase 2) y `OrdenTrabajo` (Fase 3) — revisar esos tres puntos y sumar la FK real + los selectores en sus pantallas ya construidas, no solo en las nuevas de esta fase.)*

- [ ] **Backend: modelos `Rubro` y `ProveedorRubro`.**
  Catálogo de rubros con relación N:N a proveedores.

- [ ] **Backend: modelo `EvaluacionProveedor`.**
  Evaluación posterior a una OT cerrada, alimenta la calificación general.

- [ ] **Backend: endpoints CRUD de `Proveedor`/`Rubro`.**
  Alta, edición, listado filtrable por rubro y por exclusivo/particular.

- [ ] **Backend: endpoint de historial de proveedor.**
  Se arma sobre `OrdenTrabajo` (Fase 3) + `Presupuesto` (Fase 2), no es tabla nueva.

- [ ] **Backend: endpoint de calificación/evaluación.**
  Registra la evaluación y recalcula el promedio.

- [ ] **Frontend: pantalla de listado y ficha de proveedor.**
  Filtro por rubro; ficha con contacto, calificación, historial, presupuestos.

- [ ] **Frontend: pantalla de alta/edición de proveedor.**
  Incluye el campo diferencial "exclusivo / también atiende particulares".

- [ ] **Prueba manual de punta a punta.**
  Subir un reglamento (todos lo ven) y un contrato (solo Admin General/Auditor); dar de alta un proveedor marcado "también atiende particulares", vincularlo a una OT cerrada de una fase anterior, evaluarlo, y confirmar que calificación e historial se actualizan.

---

## Fase 8 — Comunicación interna y reservas de espacios comunes

Corresponde al Documento General ("Comunicación interna" y "Reservas" dentro del alcance de la sección 1.4); Documento Técnico, secciones 14 y 15.

- [ ] **Backend: modelo `Reserva`.**
  Espacio común (Fase 1), usuario, fecha, horario, estado.

- [ ] **Backend: servicio de validación de solapamiento.**
  Antes de confirmar una reserva, valida que no se superponga con otra del mismo espacio — segundo módulo con lógica de cálculo no trivial, suma test con pytest.

- [ ] **Backend: endpoints de reserva.**
  Crear, consultar disponibilidad en un rango, cancelar (respetando el tiempo mínimo configurado por edificio).

- [ ] **Frontend: pantalla de reserva de espacios comunes.**
  Selección de espacio, calendario de disponibilidad, confirmar turno.

- [ ] **Backend: modelo `Comunicado`.**
  Título, cuerpo, autor, fecha, alcance (todo el edificio / un piso / una unidad) — Documento General, sección 1.3.

- [ ] **Backend: registro de lectura por usuario.**
  `comunicado_lectura`: resuelve el problema de "no hay forma de saber si un aviso llegó a todos" (Documento General, sección 2.1).

- [ ] **Backend: endpoints de comunicados.**
  Publicar (con alcance), listar según a quién le corresponde verlo, marcar como leído.

- [ ] **Frontend: pantalla de comunicados.**
  Feed cronológico, publicar si el rol tiene permiso, indicador de leído/no leído.

- [ ] **Prueba manual de punta a punta.**
  Reservar un espacio común dos veces en el mismo horario y confirmar que la segunda se rechaza por solapamiento; publicar un comunicado segmentado a un piso puntual y confirmar que solo ese piso lo recibe.

---

## Fase 9 — Módulo de seguridad

Corresponde al Documento General, sección 1.4 (alcance: gestión y registro, sin integración de hardware); Documento Técnico, sección 16.

- [ ] **Backend: modelo `IncidenteSeguridad`.**
  Tipo, descripción, fecha, registrado_por, prioridad (mismo esquema leve/medio/crítico que reclamos).

- [ ] **Backend: modelo `Bitacora`.**
  Registro diario operativo de encargado/personal de seguridad.

- [ ] **Backend: endpoint de botón de emergencia.**
  Genera automáticamente un `IncidenteSeguridad` de prioridad crítica y dispara notificación inmediata (reutilizando el mecanismo de comunicados/lectura de la Fase 8) — sin integración con servicios externos en esta etapa, tal como fija el alcance.

- [ ] **Backend: endpoints CRUD de incidentes y bitácora.**

- [ ] **Frontend: pantalla de carga de eventos/incidentes.**
  Para personal de seguridad/encargado.

- [ ] **Frontend: botón de emergencia.**
  Con confirmación antes de activar (evita toques accidentales).

- [ ] **Frontend: pantalla de bitácora.**
  Vista cronológica para Administrador, Encargado y personal de seguridad.

- [ ] **Prueba manual de punta a punta.**
  Activar el botón de emergencia desde un usuario de prueba y confirmar que se generó el incidente crítico, que aparece en la bitácora, y que disparó la notificación esperada.

---

## Fase 10 — Inteligencia Artificial

Corresponde al Documento General, sección 4.3 (diferencial competitivo) y 1.4 (dentro del alcance, en la etapa final); Documento Técnico, sección 18. Se ubica acá a propósito: recién ahora los módulos base tienen datos reales sobre los que operar.

- [ ] **Backend: elegir e integrar el proveedor de modelo de lenguaje.**
  Decisión que se toma en esta fase, no antes, evaluando costo/límites/facilidad de integración. Se aísla en `services/ia.py` para poder cambiar de proveedor sin tocar el resto del sistema.

- [ ] **Backend: clasificación y priorización automática de reclamos.**
  Sugiere rubro y prioridad al crear un reclamo (Fase 3); el administrador confirma o corrige — nunca decide sola.

- [ ] **Backend: generación asistida de comunicados.**
  A partir de una idea breve en lenguaje natural, redacta un borrador de comunicado (Fase 8) que se revisa antes de publicar.

- [ ] **Backend: búsqueda inteligente sobre documentación.**
  Preguntas en lenguaje natural sobre los documentos cargados (Fase 7).

- [ ] **Backend: reglas de negocio del asistente y validación de seguridad de consultas.**
  Traduce al asistente las mismas reglas de negocio del resto del sistema (qué es "deuda vencida", la precedencia de colores de la Fase 5); valida que toda consulta generada sea de solo lectura y respete el alcance/permisos de quien pregunta — un propietario no puede obtener por esta vía datos de otro departamento.

- [ ] **Frontend: sugerencias de clasificación en el formulario de reclamo.**
  Integradas en la pantalla ya existente (Fase 3), como sugerencia editable.

- [ ] **Frontend: botón "generar borrador con IA" en Comunicados.**
  Integrado en la pantalla existente (Fase 8).

- [ ] **Frontend: búsqueda inteligente en Gestión documental.**
  Integrada en la pantalla existente (Fase 7).

- [ ] **Prueba manual de punta a punta.**
  Crear un reclamo típico de plomería y confirmar que la sugerencia de rubro/prioridad es razonable. Generar un comunicado a partir de una idea breve. Pedir un dato fuera del alcance de permisos de un usuario de prueba y confirmar que el asistente lo rechaza en vez de responder.

---

## Fase 11 — Configuración avanzada, permisos por excepción y auditoría

Corresponde al Documento Técnico, sección 6.1 (extensión futura documentada desde la Fase 1) y al cierre de la sección 19 (seguridad de la aplicación).

- [ ] **Backend: permisos granulares por excepción.**
  Sobre el RBAC de la Fase 1, se agrega la posibilidad de habilitar excepciones puntuales — el ejemplo ya documentado: un propietario habilita a su inquilino a ver el estado de expensas de la unidad, aunque por defecto no la vea. **Punto exacto a resolver acá** (decisión registrada en el cierre de la Fase 2): hoy `GET /api/mis-departamentos` y `POST /api/pagos` le dan este acceso a TODO Inquilino, sin excepción — al construir esta tarea, restringir el default a `False` (como ya fija la matriz de roles) y exponer la excepción puntual por unidad en su lugar.

- [ ] **Backend: parámetros generales de la plataforma.**
  Valores por defecto para edificios nuevos (Fase 1), configurables por Administrador General.

- [ ] **Backend: registro de auditoría.**
  Para operaciones sensibles ya construidas (aprobar un gasto, modificar una expensa, cambiar estado de un reclamo): quién y cuándo. Material de trabajo del rol Auditor.

- [ ] **Frontend: pantalla de roles y permisos (`configuracion.html`, pestaña "Roles y permisos").**
  Para Administrador General: ajustar excepciones por usuario.

- [ ] **Frontend: pantalla de parámetros generales (`configuracion.html`, pestaña "Parámetros").**

- [ ] **Frontend: pantalla de auditoría (`configuracion.html`, pestaña "Auditoría").**
  Para el rol Auditor, solo lectura. *(⚠️ Acá se resuelve también el vínculo Auditor↔edificio que quedó pendiente desde la Fase 2 (pestaña Deudores, `- [x]` con nota): la tabla `UsuarioEdificio` nunca se pobló, y sin eso no hay forma de saber a qué edificios puede entrar un Auditor puntual. Una vez resuelto acá, revisar `requerir_admin_del_edificio` y equivalentes en `financiero.py` para que también acepten Auditor de solo lectura, y habilitar su acceso a las pestañas ya construidas — Deudores primero, el resto de Financiero después.)*

- [ ] **Prueba manual de punta a punta.**
  Habilitar la excepción de un inquilino puntual para ver expensas y confirmar que puede verlas (y que otro inquilino sin la excepción no puede); confirmar que una acción sensible reciente aparece en la auditoría.

---

## Fase 12 — Pulido de frontend, build de producción y PWA

Corresponde al Documento Técnico, sección 1.3.1 (migración Tailwind CDN → CLI) y al alcance de PWA fijado en el Documento General, sección 1.4 ("en un futuro se hará una versión PWA").

- [ ] **Frontend: migración de Tailwind CDN a Tailwind CLI standalone.**
  Se instala el binario ejecutable (sin Node/npm, coherente con que el resto del stack es Python) y se genera `frontend/assets/css/output.css` compilado y optimizado a partir de `tailwind.config.js` — deja de depender del CDN en cualquier entorno, incluido uno sin conexión a internet.

- [ ] **Frontend: barrido circular del toggle de tema.**
  Refinamiento documentado como pendiente desde el mockup base (skill `premium-uiux`): el barrido de la View Transitions API nace en el punto exacto del clic (`clip-path` con `circle()` calculado desde las coordenadas del botón), en vez del cross-fade por defecto. *(Actualización: se implementó, se aprobó, y se revirtió después a pedido explícito del usuario — tuvo un bug real de z-index y se reportó como lento específicamente en Chrome en producción. `theme.js` volvió al cross-fade default sin personalizar. Ver `que_hice.html`, slide `f12-t2`, para el detalle completo. No se reintenta sin que el usuario lo pida de nuevo explícitamente.)*

- [ ] **Frontend: indicador deslizante del `.view-switch`.**
  Adelantada a pedido explícito del usuario (fuera de orden, como el toggle de tema): el selector segmentado (hoy "Datos generales"/"Estructura" en `edificios.html`, la base para cualquier `.view-switch` futuro) pasa de pintar el fondo del botón activo de golpe a un indicador que se desliza entre opciones — `assets/js/view-switch.js`, se engancha solo a cualquier `.view-switch` de la página. Documentado en `que_hice.html`, slide `f12-t3`.

- [ ] **Frontend: texto de marca animado ("Building") e indicador de carga con dos frases rotando.**
  Adelantadas a pedido explícito del usuario. `.aurora-text` (`components.css`): degradé animado sobre la segunda palabra de "SMART Building". `assets/js/cargando.js`: reemplaza el "Cargando…" estático de `usuarios.html`/`edificios.html` por dos frases rotando ("Cargando" / "Por favor aguarde") con puntos suspensivos animados, reutilizable en cualquier pantalla nueva con carga de datos. Documentado en `que_hice.html`, slide `f12-t4`. *(Actualización: la paleta de `.aurora-text` está temporalmente puesta en los colores originales del componente de referencia — incluye rosa/violeta, prohibidos por la skill — a pedido explícito del usuario, "para ver cómo queda". Pendiente de que confirme si se queda así o vuelve a `--accent`/`--accent-2`.)*

- [x] **Frontend: botón de estado con ripple (`usuarios.html`).**
  Adelantada a pedido explícito del usuario, resolviendo de paso el problema de mobile con demasiados elementos en una fila: se saca el `.pill` de solo lectura "Activo"/"Inactivo" y se fusiona con el botón de acción — un solo botón que muestra el estado (verde "Activo" / rojo "Inactivo") y lo alterna al click, con un ripple del color de destino (adaptado de `RippleButton`) sincronizado con la transición de fondo. **Bug de seguridad real encontrado y corregido en el proceso:** nada impedía que un `admin_general` se desactivara a sí mismo, lo que lo dejaba bloqueado del sistema sin ninguna forma de volver a entrar (los usuarios inactivos no pueden loguearse). Corregido con un guard en el backend (`POST /desactivar` y `PATCH` con `activo:false` rechazan con 400 si es la propia cuenta) y deshabilitando el botón en el frontend para la fila del usuario logueado. Documentado en `que_hice.html`, slide `f12-t5`.

- [x] **Backend: optimización N+1 en `GET /api/edificios` y `GET /api/edificios/{id}` (rendimiento).**
  Adelantada a pedido explícito del usuario, tras reportar lentitud navegando la app en mobile y desktop con solo datos de prueba. Se midió el problema antes de tocar código: el listado disparaba **29 consultas SQL** para 7 edificios de prueba (una consulta extra por cada piso, otra por cada departamento de cada piso — un N+1 real), y el detalle de un edificio de 3 pisos disparaba **6 consultas**. Confirmado en producción (Vercel + Supabase): ~1.5 segundos para listar un solo edificio de prueba, contra 2-12ms en SQLite local — la diferencia es el costo de red real de cada consulta extra contra una base remota. Corregido con `selectinload` en el detalle (fijo en 2 consultas extra, sin importar cuántos pisos tenga el edificio) y reemplazando el listado por una consulta agregada (`COUNT`) que nunca trae pisos/departamentos completos — el listado ahora usa un schema de resumen (`EdificioResumenSalida`) en vez de reutilizar el schema completo del detalle. Se agrega además `backend/vercel.json` fijando la región del backend (`gru1`, São Paulo) para que coincida con la de Supabase (`sa-east-1`) — hoy podrían estar en continentes distintos, lo que explicaría el costo fijo de ~500-600ms por request incluso sin ninguna consulta de por medio. 3 tests nuevos que cuentan las consultas SQL reales disparadas (no tiempos, poco confiables en CI) y confirman que quedan fijas sin importar cuántos edificios/pisos/departamentos haya. Documentado en `que_hice.html`, slide `f12-t7`.

- [ ] **Frontend: auditoría de accesibilidad y de consistencia con la skill.**
  Repaso pantalla por pantalla contra `references/componentes.md` y `references/paleta-color.md` — ningún color/sombra/vidrio con valor suelto, contraste de texto suficiente, navegación por teclado en los componentes interactivos (`.view-switch`, `.unit-card`, `.detail-close`).

- [ ] **Frontend: manifiesto y Service Worker básico (PWA).**
  `manifest.json` (nombre, ícono, colores de tema/fondo tomados de los tokens) y un Service Worker mínimo de cacheo de assets estáticos, para instalar la app en el celular y tener una primera capa de uso offline — sin llegar a sincronización offline de datos, que queda fuera de alcance en esta etapa.

- [ ] **Prueba manual de punta a punta.**
  Confirmar que el sitio sigue viéndose y funcionando igual tras la migración a `output.css` (sin parpadeo de estilos sin aplicar), que el toggle de tema conserva la preferencia elegida al navegar entre pantallas, y que la app se puede "instalar" desde el navegador mobile como PWA.

---

## Fase 13 — Cierre y puesta en producción

Última fase: no agrega funcionalidad nueva, deja el proyecto listo para un primer edificio real.

- [ ] **Revisión de seguridad general.**
  Repaso de autorización por rol de todos los endpoints construidos (Documento Técnico, sección 19), validación de entrada, y que ningún dato sensible (contraseñas, tokens) quede expuesto donde no corresponde.
  *(Ampliada con los puntos 11, 12 y 13 de la Fase X — Requerimientos de seguridad informática: repaso explícito contra el checklist de **OWASP Top 10**, revisión formal de las decisiones de arquitectura ya tomadas — JWT sin estado, CORS con whitelist, secretos por variable de entorno — y un assessment de amenazas/riesgo básico antes del cierre. Incluye además ejecutar los puntos ya identificados como pendientes: deshabilitar `/docs`/`/redoc`/`/openapi.json` en producción, exigir contraseñas robustas, y crear un rol de base de datos de mínimo privilegio en Supabase.)*

- [ ] **Pruebas de carga básicas.**
  Confirmar que la plataforma responde bien con varios edificios y usuarios simultáneos, no solo con el edificio de prueba usado durante todo el desarrollo.

- [ ] **Evaluar la migración de SQLite a PostgreSQL.**
  Prevista desde el día uno por usar SQLAlchemy (Documento Técnico, sección 2.1) — se decide en esta fase si hace falta antes de salir a producción, según la escala esperada. *(Actualización: esto ya pasó antes de lo previsto — la base de producción en Vercel corre sobre PostgreSQL/Supabase desde el despliegue inicial, porque el filesystem de Vercel es efímero y SQLite no persiste ahí. Queda para esta fase evaluar si conviene seguir en el plan free de Supabase o migrar de proveedor según la escala real.)*

- [ ] **Investigar transiciones lentas/trabadas en Chrome (reportado en producción, no se reproduce en Firefox).**
  Reportado por el usuario probando en producción: animaciones con `backdrop-filter` se veían lentas en Chrome, fluidas en Firefox. El disparador puntual (el barrido circular del toggle de tema) ya se revirtió a pedido del usuario, así que el síntoma original puede haber desaparecido con él — falta confirmar si sigue habiendo lentitud en Chrome sin esa animación de por medio. Si persiste, candidatos: costo de composición de múltiples capas `backdrop-filter` apiladas, o el script `cdn.tailwindcss.com` (ya señalado como no apto para producción por el propio Tailwind — ver la tarea de migración a Tailwind CLI de la Fase 12).

- [ ] **Documentación de despliegue.**
  Cómo llevar backend y frontend a un servidor real, paso a paso.

- [ ] **Manual de uso para el Administrador de Consorcio.**
  Guía breve de las tareas del día a día (generar expensas, gestionar reclamos, dar de alta activos).

- [ ] **Piloto con un edificio real.**
  Antes de escalar a más edificios, se prueba la plataforma completa con un edificio real y su administrador, para levantar ajustes finales con feedback real.

---

## Fase X — Solicitud de Facultad

No es una fase de desarrollo más (no sigue el orden lógica → backend → frontend, ni se hace tarea por tarea en secuencia): es el **checklist de los requisitos mínimos que pide la facultad** para el proyecto, verificado contra todo lo ya construido. Se agrega tal cual la pidió el usuario, con el nombre literal — no "Fase 14", a propósito, para que quede claro que es un requisito externo al diseño del producto, no una etapa funcional.

- [x] **1. Sistema de procesamiento transaccional + repositorio de información en una base de datos relacional.**
  **Ya cumplido.** El backend completo (FastAPI + SQLAlchemy) opera con transacciones reales — `db.commit()` / `db.rollback()` explícitos, por ejemplo en `generar_expensa_mensual` (Fase 2, Tarea 8): si el prorrateo falla a mitad de camino, se hace rollback y no queda nada a medio crear. Repositorio: SQLite en desarrollo, **PostgreSQL (Supabase) en producción** — ambas relacionales, PostgreSQL es la que normalmente se trabaja en la carrera.

- [x] **2. Herramienta de mapeo objeto-relacional (ORM).**
  **Ya cumplido.** SQLAlchemy, usado en el 100% de los modelos y consultas del proyecto desde la Fase 0 — nunca SQL crudo salvo la migración puntual de `core/migraciones.py` (Fase 2, Tarea 7), y ahí también se usa el compilador de DDL de SQLAlchemy, no strings armados a mano.

- [x] **3. Diseño web adaptable (RWD) — tablets, smartphones, portátiles.**
  **Ya cumplido.** Mobile-first real en toda la skill `premium-uiux` (dos quiebres: 640px y 1024px, nunca dos maquetados separados) — verificado con Playwright en cada pantalla nueva a lo largo de todo el proyecto (sin overflow horizontal en 360-390px, layout reorganizado en tablet/desktop). No es una promesa de diseño: cada tarea de frontend de este Roadmap lo comprobó antes de darse por terminada.

- [x] **4. API de autenticación.**
  **Ya cumplido.** `POST /api/auth/login` (Fase 1, Tarea 5) — JWT de corta duración (`python-jose`), contraseñas hasheadas con `bcrypt` (`passlib`), nunca texto plano ni en la base ni en logs. `GET /api/auth/me` para que el frontend recupere la sesión. Cada endpoint protegido depende de `obtener_usuario_actual`, que decodifica el token en cada request.

- [x] **5. Otras APIs (se sugiere geolocalización).**
  **Ya cumplido.** `assets/js/mapa.js` (Fase 1, Tarea 14 — alta de edificio): geocodifica dirección + CP contra la **API de Nominatim** (OpenStreetMap, gratuita, sin API key) y muestra el resultado en un mapa real con **Leaflet**. Se usa hoy en `edificios.html` al dar de alta un edificio nuevo.

### Requerimientos de seguridad informática (13 lineamientos pedidos por la facultad)

El punto 6 original ("cumplimiento de lineamientos de seguridad... a definir oportunamente") se reemplaza por esta lista concreta que el usuario acercó. Mismo criterio de siempre: se verificó cada uno contra el código real (grep de validaciones existentes, lectura de `main.py`/`config.py`/`core/security.py`), no de memoria — 6 de los 13 ya están cumplidos, 7 quedan como tareas concretas a construir antes del cierre del proyecto.

- [x] **1. Seguridad y control de acceso basado en permisos.**
  **Ya cumplido.** Ningún endpoint del backend queda sin una dependencia de autorización — `core/dependencies.py` (`requerir_admin_del_edificio`, `requerir_acceso_financiero_edificio`, etc.) decide siempre en base al rol y la relación real del usuario con el edificio/departamento, nunca en base a lo que el frontend decide mostrar u ocultar.

- [x] **2. Autenticar y autorizar contra un dominio de base de datos.**
  **Cumplido, con un matiz a documentar.** El login (`POST /api/auth/login`) valida siempre contra la tabla `Usuario` real (password hasheada con `bcrypt`, nunca en texto plano) — no hay usuarios ni contraseñas hardcodeadas en el código. El matiz: el enunciado dice "preferentemente separado del de la aplicación" (ej. un directorio tipo LDAP/Active Directory aparte), y acá el dominio de autenticación vive en la misma base que el resto de la app. Para el tamaño y alcance de este proyecto (una sola base, sin necesidad de SSO corporativo) no se justifica separar ambos dominios — se documenta como decisión consciente, no como algo que falte.

- [x] **3. Accesos otorgados por rol (RBAC), nunca directo a la aplicación.**
  **Ya cumplido.** `Usuario.rol` es siempre uno de los 8 roles fijos de `services/autorizacion.py` (`ROLES`) — ningún permiso se asigna a un usuario puntual, todo pasa por su rol (y, en Financiero, además por su vínculo real con un departamento).

- [ ] **4. Contraseñas robustas (mínimo 8 caracteres, mayúsculas + minúsculas + números + especiales).**
  **No implementado — a construir.** Se verificó `schemas/usuario.py` y `schemas/auth.py`: hoy no existe ninguna validación de fortaleza, un usuario puede darse de alta con una contraseña de un solo carácter. Falta un `field_validator` en `UsuarioEntrada` (backend, la garantía real) que exija los 4 requisitos, más el reflejo en el frontend (`pattern`/mensaje de ayuda en el input de alta de usuario) para que el error se vea antes de mandar el formulario.

- [x] **5. Ocultar la extensión de los scripts públicos.**
  **Ya cumplido.** Todas las rutas del backend son limpias por diseño de FastAPI (`/api/edificios/7/gastos`, nunca `/servicio.py`) — no hay forma de inferir el lenguaje/framework desde una URL del sistema.

- [x] **6. Deshabilitar la visualización de errores por pantalla.**
  **Ya cumplido.** `FastAPI()` nunca se instanció con `debug=True` — un error no manejado devuelve siempre un 500 genérico, nunca el traceback real. Los únicos errores que sí muestran texto (`HTTPException` con `detail`) fueron revisados uno por uno: siempre son mensajes de negocio redactados a mano (ej. "Faltan coeficientes para prorratear", `financiero.py`), nunca el texto crudo de una excepción de SQLAlchemy o de Python que pueda filtrar estructura interna.

- [ ] **7. Solo los archivos que deben verse desde afuera, en directorios publicados.**
  **Hallazgo concreto — a construir.** `/docs`, `/redoc` y `/openapi.json` (documentación interactiva automática de FastAPI) quedan activos tal cual en producción — no hay ningún `docs_url=None`/`openapi_url=None` en `main.py`. Hoy cualquier visitante anónimo puede ver el esquema completo de la API (todas las rutas, todos los campos de cada modelo) sin loguearse. Falta deshabilitarlos en producción (`docs_url=None if ES_PRODUCCION else "/docs"`, mismo patrón ya usado por `ES_PRODUCCION` en `config.py`).

- [x] **8. Validar los parámetros de entrada, cliente y servidor.**
  **Ya cumplido.** El 100% de los `Entrada` del backend pasan por Pydantic (tipos, campos obligatorios, `field_validator` donde aplica) y el frontend usa `required`/tipos HTML5 en cada formulario. Se verificó además que no existe ni una sola consulta armada con string/f-string a partir de un dato del request — todo pasa por el ORM de SQLAlchemy (la única excepción, `core/migraciones.py`, arma DDL a partir de metadata de los propios modelos, nunca de un dato de usuario), así que no hay superficie de inyección SQL.

- [ ] **9. Mínimo privilegio en los permisos de base de datos.**
  **No implementado — a construir.** La conexión a Supabase/Postgres en producción usa hoy el rol de conexión por defecto del proyecto, no un rol dedicado creado a mano con el mínimo permiso necesario (lectura/escritura solo de las tablas de la app). Falta crear ese rol en Supabase y apuntar `DATABASE_URL` de producción a él, antes del cierre del proyecto.

- [x] **10. Evitar accesos a carpetas privadas — directorios específicos, no los default.**
  **Ya cumplido.** `backend/venv/` y `smart_building.db` nunca se versionan ni se despliegan (`.gitignore`); ni el hosting estático del frontend ni las funciones serverless del backend en Vercel exponen listado de directorios ni el filesystem del proyecto — cada uno sirve únicamente lo que expone explícitamente (rutas `/api/*` uno, los archivos de `frontend/` el otro).

- [ ] **11. Análisis preliminar de código contra vulnerabilidades conocidas (OWASP).**
  **Ya contemplado en el Roadmap — se amplía, no se duplica.** No se hizo todavía un repaso explícito contra el checklist de OWASP Top 10. En vez de una tarea nueva y aislada, se suma como parte concreta de la tarea ya existente **"Revisión de seguridad general"** (Fase 13) — ver nota agregada ahí mismo.

- [ ] **12. Revisar las cuestiones de seguridad que dependen solo de la arquitectura.**
  **Parcialmente cubierto por decisiones ya tomadas — falta la revisión formal.** Varias ya están de base: JWT sin estado (nada de sesiones en el servidor), CORS con whitelist explícita de orígenes (nunca `allow_origins=["*"]`, `core/config.py`), secretos solo por variable de entorno y `verificar_configuracion_produccion()` que no deja arrancar en Vercel con el secreto de desarrollo puesto. Falta una revisión formal dedicada, no solo decisiones tomadas sobre la marcha — se suma también a la tarea de la Fase 13.

- [ ] **13. Assessment completo de seguridad (amenazas y riesgo).**
  **No hecho — ya contemplado en el Roadmap.** Se cubre con el alcance ampliado de "Revisión de seguridad general" (Fase 13) más "Pruebas de carga básicas" (misma fase). La herramienta que cita el enunciado (subgraph.com) es una referencia de la cátedra, no necesariamente la que se termine usando — se evalúa cuando llegue el turno de esa tarea.

### Requerimientos de UX (16 heurísticas pedidas por la facultad)

Mismo criterio que los 6 puntos de arriba: se revisó cada heurística contra el código y el resto del Roadmap antes de responder — 9 de las 16 ya están cubiertas (algunas realizadas, una ya tiene su propia tarea en la Fase 12), las 7 restantes se detallan como tareas concretas a futuro, no como ítems vacíos.

- [x] **1. Visibilidad del estado del sistema.**
  **Ya realizado.** `assets/js/cargando.js` (indicador de carga con frases rotando, reutilizado en toda pantalla que pide datos), `.mensaje-error` en cada formulario, y el patrón de cambio optimista con reversión visible si falla (`usuarios.js`, botón de estado; `financiero.js`, alta de gasto/expensa) — el usuario nunca se queda sin saber si algo está pasando o si algo salió mal.

- [x] **2. Consistencia entre el sistema y el mundo real.**
  **Ya realizado.** Regla de nomenclatura del proyecto desde el Documento Técnico, sección 2.3: "el código habla el mismo idioma que esta documentación" — dominio siempre en español y con los términos reales del rubro (`Expensa`, `Propietario`, `Inquilino`, `CBU`, `Alias`, `Coeficiente`), nunca traducciones literales de un genérico en inglés.

- [ ] **3. Control y libertad de usuario (deshacer/rehacer).**
  **No contemplado todavía — nueva tarea.** Hoy los modales tienen "Cancelar" (antes de confirmar), pero ninguna acción ya confirmada se puede deshacer — ej. desactivar un usuario, asignar un departamento. Agregar un patrón de **"Deshacer" tipo toast** (aviso temporal con un botón "Deshacer" de unos segundos) para las acciones reversibles más comunes, empezando por las que ya tuvieron un incidente real: activar/desactivar usuario (Fase 12, `f12-t5` — el bug de seguridad de autodesactivación ya mostró que esta acción necesita más resguardo, no menos) y asignar/desvincular un departamento.

- [x] **4. Consistencia y estándares.**
  **Ya realizado.** Es la razón de ser de la skill `premium-uiux` completa ("Regla de oro: reutilizar, nunca reinventar") — cada botón, ícono, badge y patrón de interacción nuevo se compara primero contra `references/componentes.md` antes de diseñarse desde cero.

- [ ] **5. Prevención de errores.**
  **Parcialmente cubierto — falta una pieza concreta.** La validación de entrada sí está resuelta en las dos puntas (Pydantic en el backend, HTML5 `required`/tipos en el frontend), pero **falta confirmación explícita antes de acciones destructivas o irreversibles** — hoy "Desactivar" un usuario o rechazar un pago ejecutan directo, sin un "¿estás seguro?". Nueva tarea: modal de confirmación reutilizable (`.modal` chico, ya existe el patrón visual en `modal-direccion`) para toda acción marcada como destructiva, empezando por desactivar usuario y rechazar un pago.

- [x] **6. Reconocer antes que recordar.**
  **Ya realizado.** Ningún formulario pide escribir un ID de memoria — los `<select>` de propietario/inquilino/piso/departamento siempre vienen poblados con los datos reales ya cargados, y el panel de detalle (`.detail`, edificios/departamentos) muestra toda la información relevante junta, no repartida en pantallas que haya que recordar.

- [ ] **7. Flexibilidad y eficiencia de uso (novato y experto).**
  **No contemplado todavía — nueva tarea.** Hoy no hay nada pensado para acelerar el uso frecuente de un usuario experto: sin atajos de teclado más allá de "Enter avanza al siguiente campo" (`formularios.js`), sin recordar el último filtro usado al volver a una pantalla (ej. año/mes en Gastos), sin acciones en lote. Nueva tarea, a definir con más detalle cuando le toque el turno: al menos "recordar el último filtro" (via `localStorage`, mismo mecanismo ya usado para el tema) y accesos rápidos de teclado en las pantallas de mayor uso (Usuarios, Financiero).

- [x] **8. Estética y diseño minimalista.**
  **Ya realizado.** Es el otro pilar de `premium-uiux` — vidrio en dos capas con densidad de información deliberada (`.shell` para contenedores grandes, `.content-glass` para contenido denso), composición *bento* para KPIs (nunca grillas idénticas sin jerarquía), nada que compita visualmente con el dato real.

- [x] **9. Ayudar a reconocer, diagnosticar y recuperarse de errores.**
  **Ya realizado.** El patrón `.mensaje-error` (repetido en cada formulario del proyecto, desde el login hasta el alta de gasto) muestra el mensaje real que devuelve el backend, siempre en lenguaje llano ("Ya existe un usuario con ese email", "Ese departamento no es tuyo") — nunca un código de error crudo ni un stack trace.

- [ ] **10. Ayuda y documentación.**
  **No contemplado todavía — nueva tarea.** `que_hice.html` es una bitácora técnica para el equipo de desarrollo, no ayuda para el usuario final — hoy no existe ninguna sección de ayuda dentro de la aplicación. Nueva tarea: una pantalla o panel de ayuda contextual (por ejemplo, un ícono "?" en el topbar que abra pasos concretos de la tarea de esa pantalla puntual — "cómo generar una expensa", "cómo cargar un pago" — nunca un manual extenso, sí una lista corta de pasos como pide el propio enunciado).

- [ ] **11. Anticipación.**
  **Parcialmente cubierto — falta sistematizarlo.** Hay anticipación puntual (la fecha de hoy precargada en Gasto/Expensa, la unidad propia auto-seleccionada si el usuario tiene una sola — Tarea 9), pero no es una política deliberada del proyecto. Nueva tarea, a definir con más detalle cuando le toque el turno: por ejemplo, sugerir el próximo período a liquidar en "Generar expensa" (el mes siguiente al de la última expensa generada, no siempre el mes calendario actual) y avisar proactivamente de vencimientos próximos en el dashboard del rol correspondiente.

- [x] **12. Autonomía.**
  **Ya realizado.** El sidebar muestra siempre el usuario y rol logueado, cada pantalla de detalle tiene su `chip-link` de "‹ Volver" (edificios.html, financiero.html) y el título de contexto (nombre del edificio) queda visible en todo momento — el usuario nunca pierde de vista dónde está ni cómo volver atrás sin que el sistema le imponga un único camino.

- [x] **13. Legibilidad.**
  **Ya contemplado en el Roadmap — no hace falta una tarea nueva.** La jerarquía tipográfica (Outfit para titulares/KPIs/montos, Inter para cuerpo, tokens `--ink`/`--ink-2`/`--ink-3` para dar más peso al dato que a la etiqueta — ya aplicado en `financiero.html`: el monto en negrita, el rubro en texto plano) está resuelta por diseño desde la skill. La verificación formal de contraste (WCAG) ya es parte de la tarea "Frontend: auditoría de accesibilidad y de consistencia con la skill" (Fase 12) — se marca ahí, no hace falta duplicarla acá.

- [ ] **14. Registro del estado.**
  **Parcialmente cubierto — falta la parte de sesión/navegación.** El tema (claro/oscuro) ya persiste entre páginas y sesiones (`localStorage`, Fase 12). Lo que falta: recordar dónde estaba el usuario la última vez (hoy, todo login redirige siempre a `dashboard.html`, nunca a la última pantalla visitada) y si es la primera vez que usa el sistema (para poder mostrar una bienvenida distinta). Nueva tarea, a definir con más detalle cuando le toque el turno.

- [x] **15. Simplificación de la estructura de las tareas.**
  **Ya realizado.** Es la metodología misma del proyecto ("una tarea a la vez", nunca una pantalla con secciones de funcionalidades futuras) trasladada al diseño de cada pantalla: modales de un solo paso (nunca un wizard de varios pasos para un alta simple), formularios cortos, cada pantalla resuelve un propósito concreto.

- [ ] **16. Protección del trabajo del usuario.**
  **No contemplado todavía — nueva tarea.** Hoy cerrar cualquier modal (backdrop, ✕, o navegar afuera) descarta lo escrito sin avisar — no hay "tenés cambios sin guardar, ¿seguro que querés salir?", ni reintento automático si falla la conexión a mitad de un guardado. Nueva tarea, a definir con más detalle cuando le toque el turno: al menos un aviso de confirmación al cerrar un modal con campos ya completados, y (más adelante) reintento automático en el `Api` wrapper (`api.js`) ante una falla de red puntual, antes de mostrarle el error al usuario.

---

*Fin del Roadmap (14 fases de desarrollo, Fase 0 a Fase 13, más la Fase X de requisitos de facultad). Cada tarea marcada `- [ ]` se implementa una por vez, en el orden lógica → backend → frontend, siguiendo el orden de este documento salvo que surja una razón puntual para alterarlo — en cuyo caso esa razón se documenta acá mismo antes de saltear el orden.*

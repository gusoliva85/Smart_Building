# Roadmap del Proyecto — SMART Building (ver3)

> Este es el documento de trabajo del día a día: la bitácora que se sigue tarea por tarea. Toma todo lo definido en el [Documento General](01_Documento_General.md) y el [Documento Técnico](02_Documento_Tecnico.md) y lo organiza en fases, con checklists concretos de tareas chicas.
>
> **Cómo se usa:** cada tarea (`- [ ]`) es un entregable chico y verificable. Se implementa una sola a la vez, en el orden **lógica → backend → frontend** dentro de cada bloque funcional, se explica qué se hizo y por qué en [`que_hice.html`](../que_hice.html), y se marca como hecha (`- [x]`) recién cuando el usuario la prueba y da luz verde. No se avanza a la tarea siguiente sin esa aprobación. Si al revisar una tarea aprobada aparece un ajuste, se corrige esa misma tarea y se actualiza su slide en `que_hice.html` — nunca se crea un slide nuevo para una corrección.
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

- [ ] **Frontend: pantalla de estructura del edificio (`edificios.html`, pestaña "Estructura" vía `.view-switch`).**
  Vista en lista (no gráfica todavía — la versión gráfica coloreada es el Dashboard Visual de la Fase 5) de pisos, departamentos, cocheras y espacios comunes de un edificio, con alta de piso/departamento nuevo y asignación de propietario/inquilino. *(Actualización: no existía forma de LLEGAR a un edificio existente — `edificios.html` solo tenía el formulario de alta, sin listado. Se agregó un listado de edificios (mismo patrón que `usuarios.html`) más `GET /api/edificios` y `GET /api/edificios/{id}` en el backend, no itemizados antes como tarea aparte — decisión consultada y confirmada con el usuario antes de implementar.)*

- [ ] **Prueba manual de punta a punta.**
  Dar de alta un edificio de prueba ("Torre Central", igual que en el mockup) con estructura de varios pisos, confirmar que se generó automáticamente, asignar el usuario Propietario ya creado a un departamento puntual, y validar que al loguearse como ese propietario solo ve su propia unidad.

---

## Fase 2 — Gestión financiera básica

Corresponde al Documento General, sección 6; Documento Técnico, sección 8. De acá sale directamente el dato de morosidad que después colorea de amarillo/rojo un departamento en el Dashboard Visual (Fase 5).

- [ ] **Lógica: criterio de prorrateo.**
  Se define el cálculo (partes iguales o por m², configurable por edificio) antes de tocar modelos — es la pieza más delicada del módulo porque un error afecta a todos los propietarios a la vez.

- [ ] **Backend: modelo `Gasto`.**
  Rubro, monto, fecha, descripción, proveedor asociado (opcional, se conecta de verdad recién en la Fase 7), activo asociado (opcional, se conecta en la Fase 4).

- [ ] **Backend: modelos `Expensa` y `ExpensaDetalle`.**
  `Expensa`: liquidación de un edificio para un período, con total. `ExpensaDetalle`: apertura por rubro dentro de esa expensa — la transparencia de gasto que pide explícitamente el Documento General 6.1.

- [ ] **Backend: modelo `Pago`.**
  Departamento, expensa correspondiente, monto, fecha, medio de pago, comprobante adjunto — soporta pago parcial o total.

- [ ] **Backend: modelos `Fondo`, `MovimientoFondo`, `Caja`.**
  Fondo de reserva y otros fondos especiales con sus movimientos, separados del flujo corriente; caja chica del edificio con responsable.

- [ ] **Backend: modelos `Presupuesto` y `Factura`.**
  Para sostener la trazabilidad completa gasto → presupuesto → factura → pago (Documento General 6.7-6.8).

- [ ] **Backend: servicio de prorrateo automático.**
  `services/finanzas.py`: dado un período y el criterio configurado del edificio, calcula cuánto le corresponde a cada departamento.

- [ ] **Backend: generación de expensa mensual.**
  `POST /api/edificios/{id}/expensas`: toma los gastos del período, aplica el prorrateo, genera `Expensa` + `ExpensaDetalle` por departamento.

- [ ] **Backend: registro de pagos y conciliación.**
  `POST /api/departamentos/{id}/pagos`: registra el pago, actualiza si la expensa queda saldada o parcial.

- [ ] **Backend: cálculo de deudores.**
  `GET /api/edificios/{id}/deudores` (vista calculada, no tabla propia — Documento Técnico 5.2): antigüedad de deuda en meses por departamento. Este es el dato que va a alimentar `deudaSeverity()` en la Fase 5.

- [ ] **Backend: endpoints CRUD de Gastos, Fondos, Caja, Presupuestos, Facturas.**
  Todos anidados bajo edificio.

- [ ] **Backend: endpoint de reportes financieros.**
  `GET /api/edificios/{id}/reportes/financiero`: recaudado vs. esperado, morosidad, evolución de gastos por rubro — la data cruda para Analítica (Fase 6).

- [ ] **Frontend: `financiero.html` — cascarón con pestañas (`.view-switch`) y pestaña "Gastos".**
  Se crea la página con el selector segmentado que va a organizar todo el módulo (Gastos/Expensas/Pagos/Deudores/Fondos·Caja·Presupuestos·Facturas — Documento Técnico, sección 4.1), con la primera pestaña funcional: carga y listado de gastos, filtro por rubro y rango de fechas.

- [ ] **Frontend: pestaña "Expensas".**
  Vista de generación/detalle (Administrador) y vista de solo la propia expensa (Propietario — nunca el Inquilino, salvo excepción futura de la Fase 11).

- [ ] **Frontend: pestaña "Pagos".**
  Carga de pago contra una expensa, con confirmación de saldo pendiente si es parcial.

- [ ] **Frontend: pestaña "Deudores".**
  Listado ordenado por antigüedad, visible para Administrador y Auditor.

- [ ] **Frontend: pestaña "Fondos, Caja, Presupuestos y Facturas".**
  Puede resolverse como una única pestaña con sub-secciones si el volumen de datos de prueba lo permite, o como pestañas propias dentro del mismo `.view-switch` si se necesita más espacio — se decide al llegar a esta tarea, según cómo se vea con datos reales.

- [ ] **Prueba manual de punta a punta.**
  Cargar gastos de un mes de prueba, generar la expensa del edificio de prueba, pagar completo en algunos departamentos y dejar otros en deuda de distinta antigüedad, y confirmar que el endpoint de deudores calcula bien meses y monto en cada caso.

---

## Fase 3 — Reclamos y mantenimiento

Corresponde al Documento General, secciones 10 y 11; Documento Técnico, secciones 12 y 13. Se implementan juntas: un reclamo puede dar origen a una orden de trabajo.

- [ ] **Lógica: flujo de estados de reclamo y niveles de prioridad.**
  Se fija el flujo (recibido → asignado → en curso → resuelto → cerrado) y el significado exacto de leve/medio/crítico (Documento General 11.3) antes de modelar — es lo que después determina amarillo vs. rojo en el Dashboard Visual.

- [ ] **Backend: modelos `Reclamo` y `ReclamoComentario`.**
  Unidad/espacio afectado, descripción, fotos, prioridad, estado, creado_por/cuándo; hilo de comentarios entre quien reclama y quien gestiona.

- [ ] **Backend: modelos `OrdenTrabajo` y `OtEvidencia`.**
  Tipo (preventivo/correctivo/programado/emergencia), activo o espacio afectado, proveedor asignado, prioridad, estado, fechas de creación/inicio/cierre, costo, reclamo_id opcional (trazabilidad "quién lo pidió" → "qué se hizo"); evidencias fotográficas antes/después.

- [ ] **Backend: ciclo de vida del reclamo.**
  Crear, comentar, cambiar de estado — siempre consultable por quien lo creó.

- [ ] **Backend: generación de orden de trabajo desde un reclamo.**
  Endpoint que, dado un reclamo, genera su `OrdenTrabajo` vinculada; al cerrarse la orden, el reclamo pasa automáticamente a "resuelto".

- [ ] **Backend: gestión de órdenes de trabajo (incluidas las manuales).**
  Crear sin reclamo previo, asignar/reasignar proveedor, cambiar estado, cargar evidencia y costo al cerrar.

- [ ] **Backend: cálculo de tiempo de resolución.**
  Para reclamos y para órdenes de trabajo, por separado — alimenta el Dashboard General (Fase 6).

- [ ] **Backend: servicio de "peor estado" por departamento.**
  `services/severidad.py`: `reclamoSeverity()` y `otSeverity()` tal como quedaron documentados en la skill `premium-uiux` (`otSeverity()` solo puede devolver `ok` o `pend`, nunca `warn`/`crit`) — el dato exacto que va a consumir el Dashboard Visual en la Fase 5. Primer módulo con lógica de cálculo no trivial: suma su test con pytest en esta misma tarea (Documento Técnico, sección 20).

- [ ] **Frontend: pantalla de creación de reclamo.**
  Para Propietario/Inquilino: descripción, fotos, prioridad percibida con explicación breve de qué significa cada nivel.

- [ ] **Frontend: pantalla de seguimiento de reclamos.**
  Vista de quien lo creó (estado + comentarios) y vista de Administrador/Encargado (todos los reclamos del edificio, filtro por estado/prioridad, asignación).

- [ ] **Frontend: pantalla de órdenes de trabajo.**
  Para Administrador/Encargado/Proveedor: listado, asignar proveedor, cambiar estado, cerrar con evidencia y costo.

- [ ] **Prueba manual de punta a punta.**
  Crear un reclamo crítico, generar su orden de trabajo, asignar un proveedor de prueba, cerrarla con evidencia y costo, confirmar que el reclamo pasa a "resuelto" solo y que el tiempo de resolución quedó calculado.

---

## Fase 4 — Activos y seguridad normativa

Corresponde al Documento General, sección 9; Documento Técnico, sección 11. Junto con el Dashboard Visual, es uno de los dos pilares del diferencial competitivo (Documento General, sección 4).

- [ ] **Lógica: regla de estado del activo por vencimiento.**
  Verde si falta bastante para el próximo mantenimiento, amarillo si vence en ≤30 días, rojo si ya venció sin registrarse — se define antes de modelar porque el estado nunca se guarda a mano, siempre se calcula.

- [ ] **Backend: modelo `Activo`.**
  Tipo, código único (ej. `MAT-P3-01`), ubicación (piso o espacio común), fotos, proveedor responsable, garantía, manual (vínculo documental, se conecta en la Fase 7), próximo mantenimiento, costos acumulados (calculado).

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
  Nombre/razón social, contacto, exclusivo del consorcio vs. también atiende trabajos particulares — el dato diferencial del Documento General 8.1.

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
  Sobre el RBAC de la Fase 1, se agrega la posibilidad de habilitar excepciones puntuales — el ejemplo ya documentado: un propietario habilita a su inquilino a ver el estado de expensas de la unidad, aunque por defecto no la vea.

- [ ] **Backend: parámetros generales de la plataforma.**
  Valores por defecto para edificios nuevos (Fase 1), configurables por Administrador General.

- [ ] **Backend: registro de auditoría.**
  Para operaciones sensibles ya construidas (aprobar un gasto, modificar una expensa, cambiar estado de un reclamo): quién y cuándo. Material de trabajo del rol Auditor.

- [ ] **Frontend: pantalla de roles y permisos (`configuracion.html`, pestaña "Roles y permisos").**
  Para Administrador General: ajustar excepciones por usuario.

- [ ] **Frontend: pantalla de parámetros generales (`configuracion.html`, pestaña "Parámetros").**

- [ ] **Frontend: pantalla de auditoría (`configuracion.html`, pestaña "Auditoría").**
  Para el rol Auditor, solo lectura.

- [ ] **Prueba manual de punta a punta.**
  Habilitar la excepción de un inquilino puntual para ver expensas y confirmar que puede verlas (y que otro inquilino sin la excepción no puede); confirmar que una acción sensible reciente aparece en la auditoría.

---

## Fase 12 — Pulido de frontend, build de producción y PWA

Corresponde al Documento Técnico, sección 1.3.1 (migración Tailwind CDN → CLI) y al alcance de PWA fijado en el Documento General, sección 1.4 ("en un futuro se hará una versión PWA").

- [ ] **Frontend: migración de Tailwind CDN a Tailwind CLI standalone.**
  Se instala el binario ejecutable (sin Node/npm, coherente con que el resto del stack es Python) y se genera `frontend/assets/css/output.css` compilado y optimizado a partir de `tailwind.config.js` — deja de depender del CDN en cualquier entorno, incluido uno sin conexión a internet.

- [ ] **Frontend: barrido circular del toggle de tema.**
  Refinamiento documentado como pendiente desde el mockup base (skill `premium-uiux`): el barrido de la View Transitions API nace en el punto exacto del clic (`clip-path` con `circle()` calculado desde las coordenadas del botón), en vez del cross-fade por defecto. *(Actualización: se implementó, se aprobó, y se revirtió después a pedido explícito del usuario — tuvo un bug real de z-index y se reportó como lento específicamente en Chrome en producción. `theme.js` volvió al cross-fade default sin personalizar. Ver `que_hice.html`, slide `f12-t2`, para el detalle completo. No se reintenta sin que el usuario lo pida de nuevo explícitamente.)*

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

*Fin del Roadmap (14 fases, Fase 0 a Fase 13). Cada tarea marcada `- [ ]` se implementa una por vez, en el orden lógica → backend → frontend, siguiendo el orden de este documento salvo que surja una razón puntual para alterarlo — en cuyo caso esa razón se documenta acá mismo antes de saltear el orden.*

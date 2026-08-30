# Documento General del Proyecto — SMART Building

> Estado del documento: **Completo (11 secciones).** 1. Introducción, 2. Análisis del negocio, 3. Actores del sistema, 4. Análisis competitivo y diferencial, 5. Gestión de edificios, 6. Gestión financiera, 7. Gestión documental, 8. Gestión de proveedores, 9. Gestión de activos del edificio, 10. Gestión de mantenimiento, 11. Gestión de reclamos.

---

## 1. Introducción

### 1.1 Problema actual

La administración de consorcios y edificios hoy se resuelve, en la gran mayoría de los casos, con herramientas que no fueron pensadas para esto: planillas de Excel, grupos de WhatsApp, carpetas físicas, avisos en papel pegados en el palier y llamados telefónicos. Esto genera una serie de problemas estructurales:

- El propietario o inquilino no tiene forma de saber en tiempo real el estado de un reclamo que hizo, ni cuánto falta para que se resuelva.
- El administrador no tiene visibilidad centralizada del estado general del edificio (deudas, incidentes, mantenimientos) sin tener que cruzar información de varias fuentes.
- No queda registro histórico ordenado de reparaciones, incidentes o intervenciones de proveedores, lo que dificulta auditar qué se hizo, cuándo y a qué costo.
- Los certificados de seguridad obligatorios (matafuegos, ascensores, bocas de incendio) se controlan manualmente, con riesgo real de que venzan sin que nadie lo note a tiempo.
- La comunicación es unidireccional y desordenada: no hay forma de saber si un aviso importante realmente llegó a todos los vecinos.

En síntesis: **falta un sistema único que centralice información, dé trazabilidad y sea visual**, en un rubro donde hoy todo está fragmentado.

### 1.2 Objetivos generales

Desarrollar una plataforma digital de gestión y visualización integral de edificios/consorcios que centralice la comunicación, la administración financiera, el mantenimiento, los reclamos y la seguridad edilicia, con una experiencia visual diferencial que permita entender el estado del edificio de un solo vistazo.

### 1.3 Objetivos específicos

- Permitir que cada persona vinculada al edificio (administrador, propietario, inquilino, encargado, proveedor) tenga su propio usuario con permisos acordes a su rol.
- Digitalizar la gestión de expensas: emisión, visualización y control de pagos.
- Habilitar la carga y seguimiento de reclamos de mantenimiento con niveles de prioridad (leve, medio, crítico).
- Mantener un historial completo de mantenimientos y reparaciones realizadas, además de un plan de acciones futuras.
- Centralizar avisos, comunicados y alertas dirigidas a todo el edificio o a segmentos específicos (por ejemplo, solo un piso).
- Disponer de un directorio de contactos de confianza del consorcio (plomero, electricista, gasista, etc.), diferenciando quiénes trabajan exclusivamente para el edificio de quienes aceptan trabajos particulares.
- Gestionar los activos de seguridad del edificio (matafuegos, ascensores, bocas de incendio) con control de vencimientos y habilitaciones normativas.
- Ofrecer un dashboard visual del edificio, piso por piso y departamento por departamento, con código de colores según el estado de cada unidad.
- Sentar las bases de una arquitectura simple, prolija y escalable, separando backend y frontend desde el día uno.

### 1.4 Alcance

**Incluido en el proyecto (todas las fases del roadmap):**

- Gestión multi-edificio, con estructura de pisos, departamentos, cocheras y espacios comunes.
- Gestión financiera (expensas, pagos, deudores, gastos, fondos, reportes).
- Gestión documental (reglamentos, contratos, actas, seguros, certificados).
- Gestión de proveedores y técnicos de confianza.
- Gestión de activos de seguridad y mantenimiento (con QR, historial, vencimientos).
- Gestión de reclamos e incidentes, con prioridad y seguimiento.
- Dashboard general y dashboard visual del edificio (la funcionalidad diferencial del producto).
- Comunicación interna (avisos, comunicados, notificaciones).
- Reservas de espacios comunes (SUM, parrilla, gimnasio, etc.) y agenda de eventos.
- Módulo de seguridad (cámaras, incidentes, botón de emergencia, bitácora) — a nivel de gestión de información, no de integración de hardware en una primera etapa.
- Capa de inteligencia artificial como asistente (clasificación de reclamos, generación de comunicados, búsqueda inteligente).
- En paralelo toda la aplicacion se hace mobile first y web, para poder visualizarlo desde un celular (uso mas comun) y en una web para major visualizacion y analisis. En un futuro se hara una version PWA.

**Fuera de alcance por ahora** (se podrán evaluar en un futuro, pero no forman parte de las fases iniciales):

- Integración real con hardware de cámaras de seguridad o control de accesos (el módulo de seguridad, en esta primera versión, es de gestión y registro de eventos/incidentes, no de video en vivo).
- Medios de pago propios / pasarela de cobro integrada (se contempla el registro y control de pagos, no el procesamiento de transacciones bancarias).
- Soporte para edificios de uso comercial u oficinas (el foco es el consorcio residencial).

### 1.5 Público objetivo

- **Administradores de consorcio** (estudios de administración o administradores independientes) que gestionan uno o varios edificios.
- **Propietarios e inquilinos** que viven o poseen una unidad dentro de un edificio gestionado con la plataforma.
- **Encargados / porteros** que trabajan operativamente dentro del edificio.
- **Proveedores y técnicos** vinculados al mantenimiento del consorcio.

### 1.6 Beneficios esperados

- **Transparencia:** propietarios e inquilinos ven el estado real de sus reclamos, pagos y del edificio en general, sin depender de terceros para esa información.
- **Reducción de tiempos de respuesta:** los reclamos se priorizan y siguen un flujo claro, evitando que se pierdan en un chat o un llamado telefónico.
- **Trazabilidad total:** cada reparación, pago, incidente o intervención de proveedor queda registrada con fecha, responsable y costo.
- **Prevención normativa:** los vencimientos de certificados de seguridad (matafuegos, ascensores, etc.) se controlan de forma proactiva, reduciendo el riesgo de incumplimientos.
- **Diferencial visual:** el dashboard visual del edificio permite, de un solo vistazo, entender qué pisos o departamentos requieren atención — algo que ninguna planilla puede ofrecer.
- **Escalabilidad:** al estar pensado desde el inicio para múltiples edificios y roles, el sistema puede crecer de un solo consorcio a una cartera completa de edificios administrados.

---

## 2. Análisis del negocio

### 2.1 Problemas actuales de los consorcios

| Problema | Descripción | Consecuencia |
|---|---|---|
| **Comunicación deficiente** | Los avisos se transmiten por carteleras físicas, grupos de WhatsApp o de boca en boca. | No hay certeza de que la información llegue a todos; se generan malentendidos y reclamos duplicados. |
| **Reclamos sin seguimiento** | Un reclamo se hace por teléfono o mensaje y queda "en el aire" hasta que alguien se acuerda de resolverlo. | Frustración del vecino, pérdida de reclamos, sin registro de tiempos de resolución. |
| **Información dispersa** | Expensas en un sistema, documentación en carpetas físicas, reclamos en WhatsApp, mantenimiento en la memoria del encargado. | Nadie tiene una visión completa del edificio; decisiones basadas en información incompleta. |
| **Falta de trazabilidad** | No queda un historial claro de qué se reparó, cuándo, quién lo hizo y a qué costo. | Imposible auditar gastos o detectar patrones de fallas recurrentes. |
| **Poco control sobre proveedores** | No hay un registro formal de qué proveedores son de confianza, su historial de trabajos o su desempeño. | Se repiten errores con proveedores que ya habían dado problemas antes. |
| **Gestión documental deficiente** | Reglamentos, actas, seguros y certificados se guardan en papel o carpetas dispersas de difícil acceso. | Documentos que se pierden, vencimientos que pasan desapercibidos, dificultad para auditorías. |

### 2.2 Oportunidades

| Oportunidad | Cómo la aborda SMART Building |
|---|---|
| **Digitalización** | Toda la información del consorcio (expensas, documentos, reclamos, activos) pasa a vivir en un solo sistema accesible desde cualquier dispositivo. |
| **Automatización** | Notificaciones automáticas de vencimientos, alertas de deudas, recordatorios de mantenimiento preventivo. |
| **Centralización** | Un único punto de verdad para todos los actores del edificio, con permisos diferenciados según el rol. |
| **Visualización** | El dashboard visual del edificio traduce datos crudos (reclamos, deudas, estado de activos) en una representación gráfica inmediata y comprensible. |
| **Analítica** | Métricas y gráficos sobre gastos, morosidad, tiempos de resolución y desempeño de proveedores, que hoy no existen o se arman manualmente. |

---

## 3. Actores del sistema

Cada actor tiene un nivel de acceso distinto. La lógica general es: cuanto más "operativo" es el rol, más acotado es su alcance (su propio edificio, su propia unidad); cuanto más "administrativo", más amplio.

| Actor | Descripción | Alcance típico | Qué puede hacer (resumen) |
|---|---|---|---|
| **Administrador General** | Rol de máximo nivel dentro de la plataforma. Suele corresponder al estudio de administración que gestiona varios edificios. | Multi-edificio (toda la cartera) | Alta de edificios, gestión de usuarios y roles, configuración global, visión consolidada de todos los consorcios que administra. |
| **Administrador de Consorcio** | Responsable operativo y financiero de un edificio puntual. | Un edificio | Gestión de expensas, aprobación de gastos, gestión de reclamos, proveedores, documentación y comunicados de su edificio. |
| **Encargado** | Personal que trabaja físicamente en el edificio (portero, encargado de mantenimiento). | Un edificio, con foco operativo | Carga de incidentes, actualización de estado de reclamos, registro de tareas de mantenimiento realizadas, bitácora diaria. |
| **Propietario** | Dueño de una o más unidades dentro de uno o varios edificios. | Su(s) unidad(es) | Ver expensas y pagos, cargar reclamos, ver historial de mantenimiento, reservar espacios comunes, recibir comunicados. |
| **Inquilino** | Persona que habita una unidad sin ser el propietario. | Su unidad | Mismas funciones que el propietario a nivel operativo (reclamos, reservas, comunicados), sin acceso a información financiera de propiedad (como el estado de deuda de expensas, que es responsabilidad del propietario). |
| **Proveedor / Técnico** | Persona o empresa externa que presta servicios al consorcio (plomero, electricista, gasista, ascensores, etc.). | Las órdenes de trabajo asignadas | Ver órdenes de trabajo asignadas, cargar evidencia de la intervención realizada (fotos, informe), actualizar estado del trabajo. |
| **Auditor** | Rol de solo lectura para revisión externa (contable, legal o de la propia administración). | Definido por edificio o cartera | Acceso de consulta a información financiera, documental y de trazabilidad, sin permisos de edición. |
| **Personal de seguridad** | Encargado del módulo de seguridad del edificio (vigilancia, control de incidentes). | Un edificio | Registro de incidentes de seguridad, gestión de la bitácora, activación de alertas/botón de emergencia. |

**Nota de diseño:** el sistema de permisos se define en detalle en el módulo de *Configuración* (roles y permisos), dentro de la documentación técnica. Esta tabla describe el rol funcional; la implementación real usará un esquema de permisos granular para poder ajustar excepciones caso por caso (por ejemplo, un inquilino al que el propietario sí le habilita ver el estado de expensas).

---

## 4. Análisis competitivo y diferencial

### 4.1 Panorama competitivo

El rubro de administración de consorcios ya tiene jugadores consolidados, tanto a nivel local (Argentina) como regional e internacional. Ninguno de ellos nació como una plataforma "visual" — todos parten de la misma base (liquidar expensas y ordenar reclamos) y fueron sumando módulos alrededor de esa base. Se relevaron seis productos representativos:

| Producto | Mercado | Posicionamiento |
|---|---|---|
| **Kavanagh Cloud** | Argentina | Líder local en liquidación de expensas online, integración con AFIP y facturación electrónica. Fuerte en la parte contable/impositiva. |
| **Mis Expensas** | Argentina | Foco en automatizar la liquidación de expensas y reducir morosidad; acceso web y app. |
| **SiDomus** | Argentina | App para vecinos + panel para administradores; fuerte en reclamos con foto y liquidación digital de expensas. |
| **ConsorcioAbierto** | Argentina | Conecta expensas, proveedores, documentación, mantenimiento y comunicación en un mismo sistema; cobranza con impacto en tiempo real. |
| **ComunidadFeliz** | Chile / México / LatAm | El más completo de la región: libro de banco, control de accesos de visitas/proveedores, reservas, encuestas/votaciones y videoconferencia con el comité. |
| **Buildium / AppFolio** | EE.UU. (referencia internacional) | Suites de "property management" de nivel empresarial: contabilidad avanzada, portal de inquilinos, mantenimiento y reporting. Pensadas para administradoras profesionales con muchas unidades, no para el vecino final. |

*Relevamiento basado en información pública (sitios oficiales, fichas de tiendas de aplicaciones y comparativas de terceros) a julio de 2026. No implica una prueba exhaustiva de cada producto; donde no hay evidencia pública de una función, se marca como "No consta" en lugar de asumir directamente que no existe.*

### 4.2 Cuadro comparativo de funcionalidades

Leyenda: ✅ = funcionalidad confirmada públicamente · ⚠️ = existe una versión acotada o distinta al alcance que planteamos · ❌ = no se encontró evidencia pública, probablemente no la tenga o no la publicita.

| Funcionalidad | Kavanagh Cloud | Mis Expensas | SiDomus | ConsorcioAbierto | ComunidadFeliz | Buildium/AppFolio | **SMART Building** |
|---|---|---|---|---|---|---|---|
| Liquidación y pago de expensas online | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **✅** |
| Reclamos con foto y prioridad (leve/medio/crítico) | ❌ | ❌ | ⚠️ (con foto, sin niveles de prioridad) | ⚠️ | ⚠️ | ⚠️ | **✅** |
| Historial de mantenimiento por activo (no solo por reclamo) | ❌ | ❌ | ❌ | ⚠️ | ❌ | ⚠️ | **✅** |
| Gestión de activos de seguridad con vencimientos normativos (matafuegos, ascensores, bocas de incendio) e identificación por QR | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| Directorio de proveedores de confianza, con distinción entre "exclusivo del edificio" y "también atiende particulares" | ❌ | ❌ | ❌ | ⚠️ (directorio simple) | ❌ | ❌ | **✅** |
| Reserva de espacios comunes (SUM, parrilla, gimnasio, etc.) | ❌ | ❌ | ❌ | ⚠️ | ✅ | ⚠️ | **✅** |
| Encuestas / votaciones digitales | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | **✅** |
| Control de accesos / registro de visitas y proveedores | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | Fuera de alcance inicial (ver sección 1.4) |
| Gestión documental centralizada (reglamentos, actas, seguros, certificados) | ⚠️ | ❌ | ❌ | ✅ | ⚠️ | ✅ | **✅** |
| Multi-rol con permisos diferenciados (admin, propietario, inquilino, proveedor, auditor, seguridad) | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | **✅** |
| **Dashboard visual del edificio** (planta/piso/departamento coloreado según estado: incidente, deuda, avería) | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ (planos de ocupación en real estate comercial, no pensado para consorcios) | **✅ — funcionalidad diferencial** |
| Asistente con Inteligencia Artificial (clasificación, priorización, generación de comunicados, búsqueda inteligente) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| Predicción de mantenimientos (mantenimiento predictivo) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |

### 4.3 Conclusión: cuál es el diferencial de SMART Building

Del relevamiento surgen dos lecturas:

1. **La liquidación de expensas ya está resuelta en el mercado.** Todos los competidores locales compiten en ese terreno (Kavanagh Cloud y Mis Expensas incluso lo tienen como su producto central). Competir solamente ahí no aporta una ventaja real — es una funcionalidad de base, no un diferencial.
2. **Nadie combina, en un mismo producto, tres cosas que SMART Building sí plantea desde el diseño:**
   - Un **dashboard visual del edificio** piso por piso y departamento por departamento, con semáforo de estado (verde/amarillo/rojo) para incidentes, averías y deudas — lo más cercano que existe son herramientas de *stacking plan* de real estate comercial (tipo Yardi Floorplan Manager), pensadas para oficinas en alquiler, no para consorcios residenciales.
   - Un **módulo de activos de seguridad normativa** (matafuegos, ascensores, bocas de incendio) con QR, vencimientos y habilitación — hoy este control lo hace cada administrador "a mano", sin ningún competidor relevado que lo digitalice.
   - Una **capa de Inteligencia Artificial** como asistente real del administrador (clasificar y priorizar reclamos automáticamente, generar comunicados, buscar en la documentación) en lugar de un simple formulario digital.

El diferencial de SMART Building, entonces, no es "otra app de expensas": es la combinación de **visualización premium + control normativo de seguridad + asistencia por IA**, sobre una base funcional (expensas, reclamos, mantenimiento, comunicación) que iguala lo que el mercado ya validó como necesario.

---

## 5. Gestión de edificios

Este módulo es la base estructural de todo el sistema: define cómo se organiza un edificio internamente, y de esa estructura dependen todos los demás módulos (una expensa se prorratea por departamento, un reclamo se ubica en un piso, un activo se asigna a un espacio común, etc.).

### 5.1 Alta de edificio

Proceso que realiza el **Administrador General** al incorporar un nuevo edificio a la plataforma. Datos mínimos requeridos:

- Nombre, dirección y datos catastrales del edificio.
- Datos de la administración a cargo (Administrador de Consorcio asignado).
- Cantidad de pisos y unidades funcionales.
- CUIT/razón social del consorcio (a efectos de facturación y AFIP, ver sección 6).

A partir del alta se genera automáticamente la estructura vacía del edificio (pisos, departamentos) que luego se completa en la configuración.

### 5.2 Configuración

Parámetros propios de cada edificio, editables por el Administrador de Consorcio:

- Datos de contacto de emergencia y de la administración.
- Días de vencimiento de expensas y política de recargos por mora.
- Definición de qué roles existen habilitados para ese edificio en particular (por ejemplo, un edificio sin personal de seguridad propio no activa ese rol).
- Reglas de reserva de espacios comunes (ver módulo de Reservas, en la documentación técnica).

### 5.3 Pisos / Departamentos / Cocheras / Espacios comunes

Es el corazón estructural del edificio y la base sobre la que se construye el **dashboard visual** (la funcionalidad diferencial descripta en sección 4). Cada unidad se modela como una entidad con:

| Entidad | Atributos clave | Vínculo con otros módulos |
|---|---|---|
| **Piso** | Número/nombre de piso, cantidad de departamentos | Agrupa departamentos; nivel de agregación del dashboard visual |
| **Departamento** | Número/letra, propietario(s), inquilino (si aplica), m², estado ocupacional | Recibe expensas, reclamos, y el color de estado en el dashboard (verde/amarillo/rojo, ver sección 1) |
| **Cochera** | Número, unidad funcional asociada, fija o rotativa | Puede o no estar vinculada a un departamento |
| **Espacio común** | Nombre (SUM, parrilla, gimnasio, pileta, etc.), capacidad, reglas de uso | Base del módulo de Reservas y también sujeto a activos de seguridad (ver sección 9) |

Un mismo departamento puede tener un propietario y, simultáneamente, un inquilino habitando la unidad — ambos con su propio usuario, con el matiz de permisos financieros descripto en sección 3.

### 5.4 Planos

Carga de planos del edificio (plano general, por piso, de evacuación) en formato imagen o PDF. Estos planos son la referencia visual sobre la que, en una etapa posterior del roadmap, se podrá construir la representación gráfica interactiva del edificio (más allá de la vista esquemática por pisos).

### 5.5 Documentación

Punto de enlace con el módulo de **Gestión documental** (sección 7): cada edificio tiene su propio espacio documental (reglamento interno, planos, habilitaciones), heredando la estructura general pero acotado a ese edificio puntual.

---

## 6. Gestión financiera

El módulo más sensible del sistema, ya que de él depende directamente uno de los tres colores del dashboard visual (rojo/amarillo por deuda de expensas).

### 6.1 Expensas

- Generación periódica (mensual) de la liquidación de expensas por edificio, prorrateada según el criterio configurado (partes iguales, por m², u otro coeficiente definido en el reglamento del consorcio).
- Detalle abierto por rubro (sueldos de personal, mantenimiento, seguros, servicios, etc.), no solo un monto total — esto es lo que hoy más reclaman los propietarios en los consorcios tradicionales (transparencia del gasto).
- Notificación automática al propietario/inquilino cuando la expensa está disponible.

### 6.2 Pagos

- Registro de pagos realizados (transferencia, efectivo, débito), con comprobante adjunto.
- Conciliación entre lo liquidado y lo efectivamente cobrado.
- Estado de cuenta por unidad, visible para el propietario correspondiente.

### 6.3 Deudores

- Listado de unidades con expensas impagas, con antigüedad de la deuda.
- Este dato alimenta directamente el color del departamento en el dashboard visual: **amarillo** con un mes de deuda, **rojo** con más de un mes (según la regla definida en la Introducción, sección 1).
- Posibilidad de generar recordatorios automáticos de pago.

### 6.4 Gastos

- Carga de gastos del edificio (proveedores, sueldos, servicios, insumos), cada uno asociado a un rubro y, cuando corresponda, a un activo específico (por ejemplo, el gasto de recarga de un matafuego se asocia a ese matafuego puntual — ver sección 9).

### 6.5 Fondos

- Fondo de reserva y otros fondos especiales (por ejemplo, fondo de obras). Registro de aportes, usos y saldo disponible, separado del flujo corriente de gastos e ingresos.

### 6.6 Caja

- Movimientos de caja chica del edificio (si el encargado maneja efectivo para gastos menores), con su propio registro de ingresos/egresos y responsable.

### 6.7 Presupuestos

- Carga de presupuestos recibidos de proveedores para un trabajo o compra determinada, para comparar antes de aprobar un gasto. Se vincula con el módulo de Gestión de proveedores (sección 8).

### 6.8 Facturas

- Carga y archivo de las facturas de gastos y de servicios, vinculadas a su gasto correspondiente para mantener la trazabilidad completa (gasto → presupuesto → factura → pago).

### 6.9 Reportes

- Reportes financieros mensuales/anuales: total recaudado, total gastado, morosidad, evolución de gastos por rubro. Es la base de los gráficos financieros descriptos en la Analítica (documentación técnica, punto 2).

---

## 7. Gestión documental

Repositorio central de todo documento relevante para el consorcio, con control de quién puede ver o subir cada tipo de documento.

| Categoría | Descripción | Quién sube | Quién ve |
|---|---|---|---|
| **Reglamentos** | Reglamento de copropiedad y reglamento interno del edificio | Administrador de Consorcio | Todos los residentes |
| **Contratos** | Contratos con proveedores, personal o servicios | Administrador de Consorcio | Administrador General, Auditor |
| **Actas** | Actas de asamblea y reuniones de consorcio | Administrador de Consorcio | Todos los residentes |
| **Seguros** | Pólizas vigentes del edificio (incendio, responsabilidad civil, ascensores) | Administrador de Consorcio | Todos los residentes (consulta), Auditor |
| **Garantías** | Garantías de equipamiento y obras realizadas | Administrador de Consorcio / Proveedor | Administrador de Consorcio |
| **Manuales** | Manuales de uso de equipos (ascensor, bombas, portón) | Proveedor / Administrador | Encargado, Administrador |
| **Certificados** | Certificados de habilitación de activos de seguridad (matafuegos, ascensores, etc.) | Proveedor / Administrador | Todos los residentes (consulta), Auditor |
| **Documentación legal** | Habilitaciones municipales, documentación de AFIP, documentación laboral del personal | Administrador de Consorcio | Administrador General, Auditor |

Este módulo es también el que sostiene, en la práctica, el control de vencimientos de habilitaciones que se explota visualmente en el módulo de **Gestión de activos** (sección 9): cada certificado cargado aquí tiene una fecha de vencimiento que dispara el estado de "atención" o "crítico" del activo correspondiente.

---

## 8. Gestión de proveedores

Este es uno de los puntos que releva explícitamente el pedido original del proyecto: un directorio de contactos de confianza del consorcio (plomero, electricista, gasista, etc.), diferenciando quiénes trabajan en exclusiva para el edificio de quienes también aceptan trabajos particulares — algo que, según el análisis competitivo (sección 4), ningún competidor relevado ofrece de forma completa.

### 8.1 Alta

Registro de un proveedor con: nombre/razón social, contacto, rubro(s) en los que trabaja, y si es exclusivo del consorcio o también realiza trabajos particulares para propietarios/inquilinos (en cuyo caso queda visible ese dato en su ficha, para que cada vecino pueda contratarlo por su cuenta si lo desea).

### 8.2 Rubros

Clasificación por especialidad: plomería, electricidad, gas, ascensores, matafuegos, jardinería, limpieza, seguridad, obras, etc. Un mismo proveedor puede tener más de un rubro.

### 8.3 Calificaciones

Puntuación del proveedor en base a los trabajos realizados, cargada por el Administrador de Consorcio (y, en una fase posterior, con opinión agregada de propietarios/inquilinos sobre trabajos que los afectaron directamente).

### 8.4 Contratos

Vínculo con el módulo documental (sección 7): contratos formales vigentes con el proveedor, con fecha de inicio/fin y condiciones.

### 8.5 Presupuestos

Historial de presupuestos que el proveedor presentó para distintos trabajos, se hayan aprobado o no — permite comparar precios entre proveedores del mismo rubro a lo largo del tiempo.

### 8.6 Historial

Registro completo de todas las intervenciones del proveedor en el edificio: qué trabajo hizo, cuándo, en qué activo o espacio, y a qué costo. Es el historial que después se expone, resumido, en la ficha de cada activo (sección 9).

### 8.7 Disponibilidad

Datos de contacto y disponibilidad horaria/de emergencia del proveedor — relevante para los rubros críticos (plomero, electricista, gasista) donde la urgencia define a quién se llama primero.

### 8.8 Evaluaciones

Evaluación formal posterior a cada trabajo (cumplimiento de plazo, calidad, prolijidad), que alimenta la calificación general del proveedor (sección 8.3) y queda como antecedente objetivo para decidir si se lo vuelve a contratar.

---

## 9. Gestión de activos del edificio

Este módulo es, junto con el dashboard visual, uno de los pilares del diferencial detectado en el análisis competitivo (sección 4): ningún competidor relevado digitaliza el control normativo de seguridad del edificio. Un "activo" es cualquier elemento físico del edificio que requiere seguimiento: matafuegos, ascensores, bocas de incendio, bombas de agua, portones, luces de emergencia, etc.

Cada activo tendrá la siguiente ficha:

| Atributo | Descripción |
|---|---|
| **Identificación** | Código único interno del activo (tipo + ubicación, ej. "MAT-P3-01" para el matafuego 01 del piso 3). |
| **QR** | Código QR físico adherido al activo, que al escanearlo abre su ficha completa desde el celular (útil tanto para el encargado como para el inspector/proveedor). |
| **Fotos** | Registro fotográfico del estado actual y de instalación. |
| **Estado** | Verde (habilitado y vigente), Amarillo (próximo a vencer / requiere atención), Rojo (vencido o fuera de servicio). Mismo criterio de color que el resto de la plataforma (ver sección 1). |
| **Ubicación** | Piso, espacio común o zona común donde está instalado. |
| **Historial** | Todas las intervenciones realizadas sobre el activo (inspecciones, recargas, reparaciones), heredado del historial de proveedores (sección 8.6) y de las órdenes de trabajo (sección 10). |
| **Garantía** | Vigencia de garantía del fabricante o instalador, si corresponde. |
| **Manual** | Manual de uso/mantenimiento del activo (vínculo con Gestión documental, sección 7). |
| **Proveedor** | Proveedor/técnico responsable de su mantenimiento habitual. |
| **Próximo mantenimiento** | Fecha programada de la próxima inspección o recarga obligatoria. Dispara el cambio a amarillo cuando se acerca y a rojo si se vence sin registrarse. |
| **Costos acumulados** | Suma histórica de lo gastado en el activo (recargas, reparaciones, reemplazos), vinculado a Gestión financiera (sección 6.4). |

**Por qué importa este módulo:** en Argentina, el vencimiento de la habilitación de matafuegos, ascensores o bocas de incendio no es un tema estético — es una obligación normativa que, si no se cumple, puede dejar al edificio inhabilitado o al administrador expuesto a responsabilidad civil ante un siniestro. Hoy este control se hace "a mano" (agenda, memoria del encargado); automatizarlo con vencimientos y alertas es una mejora concreta y de alto impacto, no cosmética.

---

## 10. Gestión de mantenimiento

Mientras que Gestión de activos (sección 9) es la ficha de "qué es y en qué estado está" cada elemento, Gestión de mantenimiento es el flujo de trabajo de "qué se hizo o se va a hacer" sobre ese activo o sobre el edificio en general.

### 10.1 Tipos de mantenimiento

- **Preventivo:** tareas programadas para evitar fallas (ej. recarga anual de matafuegos, service de ascensor).
- **Correctivo:** reparación de una falla ya detectada (ej. arreglar una pérdida de agua reportada).
- **Programado:** trabajos planificados que no son estrictamente preventivos ni urgentes (ej. pintura de palier, impermeabilización de azotea) — este es el "plan de acciones futuras" mencionado en la introducción del proyecto.
- **Emergencias:** intervenciones inmediatas ante una situación crítica (ej. corte de suministro, ascensor atascado con gente adentro).

### 10.2 Órdenes de trabajo

Unidad central del módulo: cada intervención (preventiva, correctiva, programada o de emergencia) genera una **orden de trabajo**, con:

- Activo o espacio afectado.
- Proveedor/técnico asignado.
- Prioridad y estado (pendiente, en curso, resuelta).
- Fecha de creación, de inicio y de cierre.

Una orden de trabajo puede originarse de tres formas: manualmente por el administrador o encargado, automáticamente por vencimiento de un activo (sección 9), o a partir de un reclamo cargado por un propietario/inquilino (sección 11) — quedando ambos vinculados para no perder la trazabilidad de "quién lo pidió" y "qué se hizo al respecto".

### 10.3 Evidencias fotográficas

Fotos de antes/después de cada intervención, adjuntas a la orden de trabajo correspondiente — respaldo tanto para el administrador como para eventuales reclamos de garantía al proveedor.

### 10.4 Costos

Costo real de cada orden de trabajo (mano de obra + materiales), que se acumula en el activo afectado (sección 9) y en el gasto general del edificio (sección 6.4).

### 10.5 Tiempo de resolución

Tiempo transcurrido entre la apertura y el cierre de la orden de trabajo. Es un indicador clave de gestión: permite detectar si cierto tipo de trabajo o cierto proveedor demora sistemáticamente más de lo esperado, y alimenta los gráficos de Analítica descriptos en la documentación técnica.

---

## 11. Gestión de reclamos

Es la puerta de entrada más habitual para el propietario o inquilino: el módulo por el cual reporta un problema y hace seguimiento hasta su resolución. Es también, junto con la morosidad, uno de los dos factores que determinan el color de un departamento en el dashboard visual (ver sección 1 y sección 5.3).

### 11.1 Creación

El propietario o inquilino carga el reclamo indicando qué pasa, dónde (su unidad, un espacio común, o el edificio en general) y con qué prioridad lo percibe.

### 11.2 Adjuntos y fotos

El reclamo admite adjuntar fotos o documentos que respalden el problema reportado — esencial para que el administrador o el proveedor entiendan la magnitud sin tener que ir a ver en persona antes de actuar.

### 11.3 Prioridad

Se define en tres niveles, consistentes con el resto de la plataforma:

- **Leve:** no compromete a nadie más que a quien reclama, no es urgente.
- **Medio:** empieza a afectar o podría afectar a otras unidades o al funcionamiento normal del edificio.
- **Crítico:** compromete la seguridad de los residentes o del edificio, requiere atención inmediata.

Esta prioridad es la que define si el departamento se pinta de amarillo (leve/medio) o rojo (crítico) en el dashboard visual.

### 11.4 Seguimiento y estados

El reclamo recorre un flujo de estados claro (por ejemplo: recibido → asignado → en curso → resuelto → cerrado), visible en todo momento para quien lo cargó — resolviendo directamente el problema de "reclamos sin seguimiento" identificado en el análisis del negocio (sección 2.1).

### 11.5 Historial

Todo reclamo queda archivado con su resolución, sirviendo como antecedente para detectar problemas recurrentes en una misma unidad o activo (por ejemplo, la misma pérdida de agua reportada tres veces en un año es una señal de que la reparación anterior no fue efectiva).

### 11.6 Comentarios

Intercambio de comentarios entre quien reclama y quien gestiona el reclamo (administrador, encargado o proveedor asignado), dentro del propio reclamo — evitando que la conversación se disperse en WhatsApp o llamados telefónicos, tal como se identificó en el análisis del negocio.

### 11.7 Tiempo de resolución

Igual que en Gestión de mantenimiento (sección 10.5), se mide el tiempo entre la creación del reclamo y su cierre — indicador central del dashboard general (documentación técnica, punto 1) y de la calidad de gestión del consorcio.

---

*Fin del Documento General (Bloques 1, 2 y 3 completos). Próximo documento: Roadmap del proyecto, dividiendo la "Documentación técnica — cosas a implementar" en fases de trabajo.*

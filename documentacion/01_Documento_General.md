# Documento General del Proyecto — SMART Building

> **Estado del documento:** completo y **revisado a fondo el 2026-09-25**, tras una primera construcción real del sistema (Fases 0 a 3 del Roadmap: usuarios y estructura, gestión financiera, reclamos y mantenimiento). Ese código se construyó, se probó de punta a punta y se eliminó deliberadamente para rehacer el proyecto sobre una documentación ya corregida — ver "Sobre esta revisión", más abajo.
>
> **Qué es este documento.** La visión de producto y de negocio: qué problema resuelve SMART Building, para quién, con qué alcance y con qué reglas de negocio. Es el "qué" y el "por qué". El "cómo" técnico vive en [`02_Documento_Tecnico.md`](02_Documento_Tecnico.md), la interfaz en [`03_Documento_Frontend.md`](03_Documento_Frontend.md), y la ejecución paso a paso en [`05_Roadmap.md`](05_Roadmap.md).
>
> **Orden de lectura sugerido:** 01 (este) → 02 (técnico) → 04 (frontend) → 03 (roadmap, el documento de trabajo diario).

---

## Sobre esta revisión (leer antes que el resto)

La primera versión de este documento se escribió **antes** de tener una sola línea de código. Después se construyó el sistema hasta la Fase 3 y, al hacerlo, aparecieron decisiones, restricciones y hallazgos que ningún documento previo podía anticipar: normativa real de propiedad horizontal que cambió el criterio de prorrateo, un límite legal concreto en el cobro por QR, un flujo de estados que necesitaba una excepción que el diseño original no contemplaba, roles declarados en la matriz que en la práctica necesitaban lo contrario.

El proyecto se reinicia desde cero con el código borrado, pero **nada de ese aprendizaje se pierde**: está incorporado acá. Cuando una sección dice "decisión adoptada" o "hallazgo", no es una hipótesis de diseño — es algo que ya se implementó, se probó contra usuarios y datos reales, y se corrigió al menos una vez.

Tres documentos de apoyo sostienen esta revisión:

- **`entrevistas.md`** — relevamiento de necesidad con dos inquilinos y un administrador de consorcio, contrastado con datos reales del mercado argentino 2024-2025.
- **`investigaciones/`** — cuatro investigaciones previas a implementar (`Prorrateo.md`, `Pagos_y_Conciliacion.md`, `Caja_chica.md`, `Presupuestos_y_Facturas.md`), cada una con normativa consultada y la decisión de diseño que se tomó en consecuencia.
- **`.claude/skills/premium-uiux/`** — el sistema de diseño en formato ejecutable: el contrato visual del frontend. *(La carpeta `mockups/` es exploración histórica y no manda sobre nada.)*

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

**Validación del problema (2026-09):** el relevamiento documentado en `entrevistas.md` confirma cada uno de estos cinco puntos desde las dos puntas de la relación. Un inquilino lo resumió en una palabra: *"incertidumbre — no poder saber, en un momento dado, qué pasó con esto que reclamé"*. Un administrador con 15 edificios a cargo lo dijo desde el otro lado: *"si un consorcista me pregunta en la asamblea qué pasó con el reclamo que hizo hace ocho meses, tengo que ponerme a buscar en mensajes viejos de WhatsApp"*. El dato de contexto que enmarca todo esto: en 2024 los residentes de la Ciudad de Buenos Aires presentaron 2943 quejas formales contra administradores de consorcio, y **una cuarta parte de ellas fue por incumplimiento del mantenimiento de espacios comunes** — no por mala fe, en muchos casos, sino por falta de un registro que permita demostrar qué se hizo.

### 1.2 Objetivos generales

Desarrollar una plataforma digital de gestión y visualización integral de edificios/consorcios que centralice la comunicación, la administración financiera, el mantenimiento, los reclamos y la seguridad edilicia, con una experiencia visual diferencial que permita entender el estado del edificio de un solo vistazo.

### 1.3 Objetivos específicos

- Permitir que cada persona vinculada al edificio (administrador, propietario, inquilino, encargado, proveedor) tenga su propio usuario con permisos acordes a su rol.
- Digitalizar la gestión de expensas: emisión prorrateada por coeficiente, visualización con apertura por rubro y control de pagos con conciliación.
- Habilitar la carga y seguimiento de reclamos de mantenimiento con niveles de prioridad (leve, medio, crítico) y un flujo de estados visible en todo momento para quien lo cargó.
- Mantener un historial completo de mantenimientos y reparaciones realizadas, además de un plan de acciones futuras.
- Centralizar avisos, comunicados y alertas dirigidas a todo el edificio o a segmentos específicos (por ejemplo, solo un piso).
- Disponer de un directorio de contactos de confianza del consorcio (plomero, electricista, gasista, etc.), diferenciando quiénes trabajan exclusivamente para el edificio de quienes aceptan trabajos particulares.
- Gestionar los activos de seguridad del edificio (matafuegos, ascensores, bocas de incendio) con control de vencimientos y habilitaciones normativas.
- Ofrecer un dashboard visual del edificio, piso por piso y departamento por departamento, con código de colores según el estado de cada unidad.
- Sentar las bases de una arquitectura simple, prolija y escalable, separando backend y frontend desde el día uno.

### 1.4 Alcance

**Incluido en el proyecto (todas las fases del roadmap):**

- Gestión multi-edificio, con estructura de pisos, departamentos, cocheras y espacios comunes.
- Gestión financiera (expensas, pagos y conciliación, deudores, gastos, fondos, caja chica, presupuestos, facturas, reportes).
- Gestión documental (reglamentos, contratos, actas, seguros, certificados).
- Gestión de proveedores y técnicos de confianza.
- Gestión de activos de seguridad y mantenimiento (con QR, historial, vencimientos).
- Gestión de reclamos e incidentes, con prioridad y seguimiento.
- Dashboard general y dashboard visual del edificio (la funcionalidad diferencial del producto).
- Comunicación interna (avisos, comunicados, notificaciones).
- Reservas de espacios comunes (SUM, parrilla, gimnasio, etc.) y agenda de eventos.
- Módulo de seguridad (incidentes, botón de emergencia, bitácora) — a nivel de gestión de información, no de integración de hardware.
- Capa de inteligencia artificial como asistente (clasificación de reclamos, generación de comunicados, búsqueda inteligente).
- Toda la aplicación es **mobile-first y web a la vez**: un único maquetado responsive, pensado primero para el celular (el uso más común del residente) y que se expande a escritorio para el análisis del administrador. La versión PWA queda para una fase posterior.

**Fuera de alcance por ahora** (se podrán evaluar en el futuro, pero no forman parte de las fases iniciales):

- Integración real con hardware de cámaras de seguridad o control de accesos.
- **Procesamiento de pagos.** La plataforma registra y concilia pagos; la plata nunca pasa por el sistema. Ver la restricción legal concreta en la sección 6.2 — no es una simplificación de alcance, es un límite regulatorio real.
- **Carga de archivos al servidor.** Hoy toda "foto", "comprobante" o "adjunto" es un **campo de URL/link** a un archivo alojado afuera. Un almacenamiento propio de archivos es una decisión de infraestructura que se toma cuando el módulo de Gestión documental (Fase 7) lo exija de verdad, no antes. Es la restricción más visible del producto actual y está documentada en cada módulo que la sufre.
- Soporte para edificios de uso comercial u oficinas (el foco es el consorcio residencial).

### 1.5 Público objetivo

- **Administradores de consorcio** (estudios de administración o administradores independientes) que gestionan uno o varios edificios.
- **Propietarios e inquilinos** que viven o poseen una unidad dentro de un edificio gestionado con la plataforma.
- **Encargados / porteros** que trabajan operativamente dentro del edificio.
- **Proveedores y técnicos** vinculados al mantenimiento del consorcio.

### 1.6 Beneficios esperados

- **Transparencia:** propietarios e inquilinos ven el estado real de sus reclamos, pagos y del edificio en general, sin depender de terceros para esa información.
- **Reducción de tiempos de respuesta:** los reclamos se priorizan y siguen un flujo claro, evitando que se pierdan en un chat o un llamado telefónico.
- **Trazabilidad total:** cada reparación, pago, incidente o intervención de proveedor queda registrada con fecha, responsable y costo. Es, según el relevamiento, el beneficio que más valoran las dos puntas: el residente lo quiere como prueba, el administrador como defensa.
- **Prevención normativa:** los vencimientos de certificados de seguridad se controlan de forma proactiva, reduciendo el riesgo de incumplimientos.
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
| **Falta de trazabilidad** | No queda un historial claro de qué se reparó, cuándo, quién lo hizo y a qué costo. | Imposible auditar gastos, detectar fallas recurrentes, o defenderse de una denuncia infundada. |
| **Poco control sobre proveedores** | No hay un registro formal de qué proveedores son de confianza, su historial de trabajos o su desempeño. | Se repiten errores con proveedores que ya habían dado problemas antes. |
| **Gestión documental deficiente** | Reglamentos, actas, seguros y certificados se guardan en papel o carpetas dispersas. | Documentos que se pierden, vencimientos que pasan desapercibidos, dificultad para auditorías. |
| **Opacidad del gasto** | La expensa llega como un total, sin apertura de en qué se gastó cada peso ni por qué subió. | Desconfianza del propietario, discusiones en asamblea, denuncias por "falta de transparencia" que muchas veces son solo falta de registro presentable. |

### 2.2 Oportunidades

| Oportunidad | Cómo la aborda SMART Building |
|---|---|
| **Digitalización** | Toda la información del consorcio (expensas, documentos, reclamos, activos) pasa a vivir en un solo sistema accesible desde cualquier dispositivo. |
| **Automatización** | Notificaciones de vencimientos, alertas de deudas, recordatorios de mantenimiento preventivo, generación de órdenes de trabajo a partir de un reclamo. |
| **Centralización** | Un único punto de verdad para todos los actores del edificio, con permisos diferenciados según el rol. |
| **Visualización** | El dashboard visual del edificio traduce datos crudos (reclamos, deudas, estado de activos) en una representación gráfica inmediata y comprensible. |
| **Analítica** | Métricas y gráficos sobre gastos, morosidad, tiempos de resolución y desempeño de proveedores, que hoy no existen o se arman manualmente. |

### 2.3 Dos advertencias del relevamiento (restricciones de diseño, no funcionalidades)

Estas dos salieron de las entrevistas y condicionan el producto entero, así que se documentan acá y no en un módulo puntual:

1. **La plataforma tiene que reemplazar el circuito informal, no duplicarlo.** *"Que no sea otra cosa más para revisar además del WhatsApp del edificio"* (inquilina) y *"si me saca más tiempo cargar un gasto del que me ahorra, la voy a dejar de usar al mes"* (administrador). Consecuencia concreta de diseño: **la velocidad de carga es un requisito funcional, no una mejora de UX.** Un formulario de reclamo que tarde más que mandar un mensaje de texto ya fracasó, por prolijo que sea el registro que genere.
2. **El registro solo vale si ninguna de las partes puede reescribirlo unilateralmente.** *"Si el historial lo puede editar solo una de las dos partes, no sirve como prueba de nada"* (inquilino). Consecuencia concreta: los registros que funcionan como antecedente (reclamos cerrados, expensas liquidadas, órdenes de trabajo resueltas) **son inmutables por diseño**, y donde existe una excepción es deliberada, acotada y está documentada (ver sección 6.1 y sección 12).

---

## 3. Actores del sistema

Cada actor tiene un nivel de acceso distinto. La lógica general: cuanto más "operativo" es el rol, más acotado es su alcance (su propio edificio, su propia unidad); cuanto más "administrativo", más amplio.

| Actor | Descripción | Alcance | Qué puede hacer |
|---|---|---|---|
| **Administrador General** | Máximo nivel de la plataforma. Suele ser el estudio de administración que gestiona varios edificios. | Toda la cartera | Alta de edificios, gestión de usuarios y roles, configuración global, visión consolidada de todos los consorcios. |
| **Administrador de Consorcio** | Responsable operativo y financiero de un edificio puntual. | Su edificio | Expensas, gastos, aprobación de presupuestos, conciliación de pagos, gestión de reclamos y órdenes de trabajo, proveedores, documentación y comunicados. |
| **Encargado** | Personal que trabaja físicamente en el edificio (portero, encargado de mantenimiento). | Su edificio, con foco operativo | Carga de incidentes, gestión de reclamos y órdenes de trabajo, registro de tareas realizadas, bitácora diaria. **No ve montos financieros** — solo el semáforo general. |
| **Propietario** | Dueño de una o más unidades, en uno o varios edificios. | Su(s) unidad(es) | Ver expensas con su apertura por rubro, registrar pagos, cargar y seguir reclamos, ver historial de mantenimiento, reservar espacios comunes, recibir comunicados. |
| **Inquilino** | Persona que habita una unidad sin ser el propietario. | Su unidad (una sola) | Lo mismo que el propietario a nivel operativo y financiero **de su propia unidad** (ver la corrección de abajo). |
| **Proveedor / Técnico** | Persona o empresa externa que presta servicios al consorcio. | Las órdenes de trabajo asignadas | Ver sus órdenes de trabajo, cargar evidencia de la intervención, actualizar estado del trabajo. |
| **Auditor** | Solo lectura, para revisión externa (contable, legal o de la propia administración). | Definido por edificio o cartera | Consulta de información financiera, documental y de trazabilidad, sin ningún permiso de edición. |
| **Personal de seguridad** | Encargado del módulo de seguridad del edificio. | Su edificio | Registro de incidentes, bitácora, botón de emergencia. |

### 3.1 Corrección adoptada: el Inquilino sí ve el financiero de su unidad

La primera versión de este documento decía que el Inquilino **no** accede a información financiera, "porque la deuda de expensas es responsabilidad del propietario". Al implementar el módulo de pagos apareció la contradicción: en la enorme mayoría de los alquileres de Argentina **las expensas ordinarias las paga de hecho el inquilino**, y el relevamiento lo confirma de las dos puntas. Un inquilino que no puede ver su propia expensa ni registrar su propio pago no puede usar el módulo que más va a usar.

**Decisión adoptada:** Propietario e Inquilino tienen exactamente el mismo acceso financiero **a nivel de su propia unidad** (ver expensa, ver apertura por rubro, ver saldo, registrar un pago, ver el CBU del consorcio). Ninguno de los dos ve el financiero del edificio (eso es del Administrador y del Auditor). Un mismo departamento puede tener propietario e inquilino simultáneamente, cada uno con su usuario y ambos con acceso a la misma unidad.

**Regla de estructura asociada:** un propietario puede tener varias unidades (incluso en edificios distintos); **un inquilino tiene una sola**. Esto simplifica toda la interfaz del residente: donde el propietario a veces necesita elegir de cuál de sus unidades está hablando, el inquilino nunca.

### 3.2 Permisos por excepción

El modelo de permisos es **RBAC simple**: un rol equivale a un conjunto fijo de permisos. Las excepciones caso por caso (por ejemplo, un edificio donde el propietario decide que su inquilino no vea nada financiero) quedan como extensión futura: se resuelven agregando una tabla de excepciones que se consulta *antes* de la regla de rol, sin rediseñar el sistema. No forman parte del alcance inicial.

---

## 4. Análisis competitivo y diferencial

### 4.1 Panorama competitivo

El rubro ya tiene jugadores consolidados, locales y regionales. Ninguno nació como una plataforma "visual" — todos parten de la misma base (liquidar expensas y ordenar reclamos) y fueron sumando módulos alrededor.

| Producto | Mercado | Posicionamiento |
|---|---|---|
| **Kavanagh Cloud** | Argentina | Líder local en liquidación de expensas online, integración con AFIP y facturación electrónica. Fuerte en lo contable/impositivo. |
| **Mis Expensas** | Argentina | Automatizar la liquidación y reducir morosidad; acceso web y app. |
| **SiDomus** | Argentina | App para vecinos + panel para administradores; fuerte en reclamos con foto. |
| **ConsorcioAbierto** | Argentina | Conecta expensas, proveedores, documentación, mantenimiento y comunicación; cobranza con impacto en tiempo real. |
| **ComunidadFeliz** | Chile / México / LatAm | El más completo de la región: libro de banco, control de accesos, reservas, encuestas y videoconferencia con el comité. |
| **Buildium / AppFolio** | EE.UU. (referencia) | Suites de *property management* empresariales: contabilidad avanzada, portal de inquilinos, mantenimiento y reporting. Pensadas para administradoras grandes, no para el vecino final. |

*Relevamiento basado en información pública (sitios oficiales, fichas de tiendas de aplicaciones y comparativas de terceros) a julio de 2026. Donde no hay evidencia pública de una función, se marca "no consta" en lugar de asumir que no existe.*

### 4.2 Cuadro comparativo

Leyenda: ✅ confirmada públicamente · ⚠️ versión acotada o distinta a nuestro alcance · ❌ sin evidencia pública.

| Funcionalidad | Kavanagh | Mis Expensas | SiDomus | ConsorcioAbierto | ComunidadFeliz | Buildium/AppFolio | **SMART Building** |
|---|---|---|---|---|---|---|---|
| Liquidación y pago de expensas online | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **✅** |
| Reclamos con foto y prioridad (leve/medio/crítico) | ❌ | ❌ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | **✅** |
| Historial de mantenimiento por activo (no solo por reclamo) | ❌ | ❌ | ❌ | ⚠️ | ❌ | ⚠️ | **✅** |
| Activos de seguridad con vencimientos normativos y QR | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| Directorio de proveedores con distinción "exclusivo / también particulares" | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | **✅** |
| Reserva de espacios comunes | ❌ | ❌ | ❌ | ⚠️ | ✅ | ⚠️ | **✅** |
| Encuestas / votaciones digitales | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | **✅** |
| Control de accesos / registro de visitas | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | Fuera de alcance (1.4) |
| Gestión documental centralizada | ⚠️ | ❌ | ❌ | ✅ | ⚠️ | ✅ | **✅** |
| Multi-rol con permisos diferenciados (8 roles) | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | **✅** |
| **Dashboard visual del edificio** (piso/departamento coloreado por estado) | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ | **✅ — diferencial** |
| Asistente con Inteligencia Artificial | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| Mantenimiento predictivo | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |

### 4.3 Conclusión: cuál es el diferencial

1. **La liquidación de expensas ya está resuelta en el mercado.** Competir solo ahí no aporta ventaja: es una funcionalidad de base, no un diferencial. Tiene que estar, y tiene que estar bien hecha, pero no es el argumento.
2. **Nadie combina, en un mismo producto, estas tres cosas:**
   - Un **dashboard visual del edificio** piso por piso y departamento por departamento, con semáforo de 4 estados. Lo más cercano que existe son los *stacking plans* de real estate comercial, pensados para oficinas en alquiler, no para consorcios residenciales.
   - Un **módulo de activos de seguridad normativa** (matafuegos, ascensores, bocas de incendio) con QR, vencimientos y habilitación — hoy ese control lo hace cada administrador a mano.
   - Una **capa de IA** como asistente real (clasificar y priorizar reclamos, generar comunicados, buscar en la documentación).

El diferencial no es "otra app de expensas": es la combinación de **visualización premium + control normativo de seguridad + asistencia por IA**, sobre una base funcional que iguala lo que el mercado ya validó como necesario.

---

## 5. Gestión de edificios

Módulo base de todo el sistema: define cómo se organiza un edificio internamente, y de esa estructura dependen todos los demás módulos (una expensa se prorratea por departamento, un reclamo se ubica en un piso o espacio común, un activo se asigna a una ubicación).

### 5.1 Alta de edificio

La realiza el **Administrador General**. Datos del alta:

- Nombre, dirección y CP (se pide CP en vez de ciudad: es más preciso para geocodificar y suficiente para lo que usa la plataforma).
- CUIT del consorcio.
- Administrador de Consorcio asignado (opcional en el alta, asignable después).
- Cantidad de pisos y unidades por piso → **la estructura se genera automáticamente** (pisos y departamentos vacíos) y luego se completa y corrige desde Configuración.

**Geocodificación en el alta:** al completar Dirección + CP, el formulario geocodifica con Nominatim (OpenStreetMap) y muestra el resultado en un mapa dentro del propio formulario. Si la dirección no se encuentra, **se avisa pero no se bloquea el alta** — una dirección nueva puede no estar todavía indexada, y no tiene sentido impedir cargar un edificio real por eso. Las coordenadas quedan guardadas para usos futuros (ubicación del edificio en reportes o en el dashboard).

### 5.2 Configuración del edificio

Parámetros propios de cada edificio, editables por el Administrador General o el Administrador de Consorcio de ese edificio:

- **Responsables:** Administrador de Consorcio y **Encargado** asignados. Ambos son vínculos reales a un usuario del sistema, y son los que determinan quién gestiona los reclamos y las órdenes de trabajo de ese edificio.
- Contacto de emergencia (nombre y teléfono).
- Días de vencimiento de expensas y porcentaje de recargo por mora.
- **CBU y alias** de la cuenta del consorcio (los datos que el residente necesita para transferir — ver 6.2).
- Roles habilitados para ese edificio en particular (un edificio sin personal de seguridad propio no activa ese rol).
- Reglas de reserva de espacios comunes.
- **Coeficientes de las unidades** (ver 6.1) — la pantalla de configuración es donde se completan y corrigen.

### 5.3 Pisos, departamentos, cocheras y espacios comunes

Es el corazón estructural del edificio y la base sobre la que se construye el dashboard visual.

| Entidad | Atributos clave | Vínculo con otros módulos |
|---|---|---|
| **Piso** | Número/nombre, orden de apilado | Agrupa departamentos; es la franja horizontal de la fachada en el dashboard visual |
| **Departamento** | Identificador (ej. "6A"), m², **coeficiente (%)**, propietario, inquilino, estado ocupacional | Recibe expensas y reclamos; es la unidad que se colorea en el dashboard |
| **Cochera** | Número, tipo (fija o rotativa), departamento asociado (opcional) | Puede o no estar vinculada a un departamento |
| **Espacio común** | Nombre (SUM, parrilla, gimnasio…), capacidad, reglas de uso | Base del módulo de Reservas; puede ser objetivo de un reclamo o de una orden de trabajo; aloja activos |

El **estado ocupacional** de un departamento no se carga a mano: se deriva de si tiene propietario o inquilino asignado.

### 5.4 Planos

Carga de planos del edificio (general, por piso, de evacuación). Son la referencia visual sobre la que, en una etapa posterior, se podrá construir una representación gráfica más fiel que la vista esquemática por pisos.

### 5.5 Documentación del edificio

Punto de enlace con Gestión documental (sección 7): cada edificio tiene su propio espacio documental, heredando la estructura general pero acotado a ese edificio.

---

## 6. Gestión financiera

El módulo más sensible del sistema: de él depende directamente uno de los colores del dashboard visual (amarillo/rojo por deuda), y un error acá afecta a todos los propietarios a la vez.

### 6.1 Expensas

> Investigación legal completa y fundamento de la decisión: **`investigaciones/Prorrateo.md`**.

**El coeficiente es el dato, no el criterio.** Se investigó la normativa real de propiedad horizontal en Argentina (Ley 13.512 y su continuación en el Código Civil y Comercial, arts. 2037 y siguientes) antes de escribir una línea: cada unidad funcional tiene un **porcentual fijo registrado en el reglamento de propiedad horizontal**, y los coeficientes de todas las unidades de un edificio suman 100%. No es un criterio global que se recalcula en cada liquidación.

- "Partes iguales" y "por m²" **no son criterios de prorrateo**: son dos atajos para completar el coeficiente la primera vez, al dar de alta la estructura. Una vez completados, el coeficiente queda como dato editable unidad por unidad, para que coincida con el reglamento real del edificio si difiere.
- La liquidación mensual toma los **gastos reales cargados de ese período**, los agrupa por rubro (apertura visible para el residente, no solo un total) y reparte el total según el coeficiente de cada unidad.
- **Precisión:** al repartir un monto entre N unidades, nunca se redondea cada parte por separado — eso deja centavos sin asignar. La última unidad recibe el resto exacto, de modo que la suma de lo repartido siempre iguala el total. El mismo cuidado aplica al completar coeficientes: el redondeo tiene que coincidir con la precisión real con que se guarda el dato, o la suma deja de dar 100% al persistirse (error real detectado en un edificio de 28 unidades, donde daba 99,989%).

**Inmutabilidad y su única excepción.** Una expensa liquidada es un documento contable: no se edita. Editar un gasto viejo **no** altera retroactivamente una expensa ya generada. La única excepción, deliberada y acotada: **regenerar la última expensa del edificio**, para el caso real de haber liquidado con un gasto mal cargado. Al regenerar se avisa explícitamente que se va a reemplazar, se pide confirmación, y se conserva la identidad de la expensa (los pagos ya registrados contra ella siguen siendo válidos). Regenerar un período que no sea el último está prohibido: rompería la cadena contable de los meses posteriores.

**Fuera de alcance por ahora:** un criterio de distribución distinto por rubro dentro del mismo edificio (ej. planta baja exenta del gasto de ascensor). Es real y contemplado por la ley vía el reglamento, pero se resuelve en una tarea aparte que no rompa esta base.

### 6.2 Pagos y conciliación

> Investigación completa (incluido el límite legal del QR y por qué la conciliación no puede ser automática): **`investigaciones/Pagos_y_Conciliacion.md`**.

**Hallazgo legal sobre el QR.** El QR interoperable de Argentina ("Transferencias 3.0", regulado por el BCRA) **solo lo pueden emitir entidades financieras y proveedores de servicios de pago registrados**. Una aplicación de terceros no puede generar un QR de pago real y válido. La opción intermedia era un "QR de conveniencia" (que al escanearlo solo muestra el CBU como texto), pero se descartó por innecesaria: **se muestran el CBU y el alias como texto, cada uno con su botón de copiar**, para pegarlos en la app del banco. Copiar un texto es un toque; escanear un QR para volver a copiar el texto que tenía adentro es un paso de más — y elimina cualquier ambigüedad sobre si "hay un QR" significa que el pago se dispara solo.

**La conciliación es un paso humano, no automático.** Si el residente carga un pago y el sistema lo da por saldado al instante, cualquiera podría cargar un comprobante falso y aparecer sin deuda sin que la plata haya entrado. Por eso:

- Un pago cargado por el residente nace en estado **pendiente**.
- El Administrador lo contrasta con el movimiento bancario real y lo pasa a **confirmado** o **rechazado**.
- **Solo un pago confirmado reduce la deuda.** Un pago pendiente no baja el saldo, pero sí se le muestra al residente como "ya lo cargaste, está esperando confirmación" — sin ese aviso, el residente ve su saldo intacto y vuelve a pagar.
- El propio residente nunca puede confirmar su pago, aunque tenga permisos sobre su unidad.

Esto también deja en claro un punto legal: mostrar el CBU del consorcio no convierte a SMART Building en un procesador de pagos. La plata nunca pasa por la plataforma; el comprobante se carga después para que el administrador lo audite. Es exactamente lo que hoy hace cualquier administración que manda el CBU por WhatsApp, pero con registro.

**Pagos parciales:** están permitidos y el sistema los muestra como tales (saldo restante calculado), porque son habituales en la realidad del rubro.

### 6.3 Deudores

- Vista **calculada** (no una tabla propia) sobre expensas y pagos confirmados: unidades con saldo impago y antigüedad de la deuda en meses, ordenadas de más a menos atrasada.
- La deuda del mes corriente **no cuenta como atraso** hasta pasado el vencimiento configurado del edificio.
- Alimenta directamente el color del departamento en el dashboard: **amarillo** con un mes de deuda, **rojo** con más de un mes.
- Siempre es solo lectura: la única forma de saldar una deuda es conciliar el pago correspondiente.

### 6.4 Gastos

Carga de los gastos reales del edificio (proveedores, sueldos, servicios, insumos), cada uno con rubro, monto, fecha y descripción, y opcionalmente asociado a un proveedor y/o a un activo puntual (ej. la recarga de un matafuego se asocia a ese matafuego). Los gastos de un período son el insumo de la liquidación de expensas de ese período.

Un gasto es editable (se carga mal un monto y se corrige), pero esa edición **no reescribe una expensa ya liquidada** — ver 6.1.

### 6.5 Fondos

Fondo de reserva y otros fondos especiales (fondo de obras, etc.), cada uno con su registro de movimientos de ingreso y egreso y su saldo calculado, separado del flujo corriente de gastos.

### 6.6 Caja chica

> Investigación del criterio contable adoptado: **`investigaciones/Caja_chica.md`**.

Se implementa como **sistema de fondo fijo**, que es como funciona en la práctica en las administraciones: la caja tiene un **monto fijo** definido y un **responsable** (habitualmente el encargado), se gasta contra ella durante el mes y se **repone hasta el monto fijo** cada vez que se rinde. No es una cuenta de saldo libre: el saldo disponible y lo pendiente de reposición se derivan del monto fijo y los movimientos cargados.

### 6.7 Presupuestos

> Investigación del circuito y su relación con el gasto real: **`investigaciones/Presupuestos_y_Facturas.md`**.

Presupuestos recibidos de proveedores para un trabajo determinado, para comparar antes de aprobar. Cada uno nace **pendiente** y pasa a **aprobado** o **rechazado**. Al aprobarse se lo puede vincular al **gasto real** que generó, cerrando la trazabilidad de "lo que se presupuestó" contra "lo que finalmente se pagó".

### 6.8 Facturas

Facturas de gastos y servicios, siempre vinculadas a un gasto real del edificio. Completan la cadena de trazabilidad **presupuesto → gasto → factura → pago**.

### 6.9 Reportes

Reportes financieros por período: recaudado vs. esperado, morosidad, gastos agrupados por rubro y su evolución. Es la base de los gráficos de Analítica y del widget financiero del Dashboard General.

---

## 7. Gestión documental

Repositorio central de todo documento relevante del consorcio, con control de quién puede ver o subir cada tipo.

| Categoría | Descripción | Quién sube | Quién ve |
|---|---|---|---|
| **Reglamentos** | Reglamento de copropiedad y reglamento interno | Administrador de Consorcio | Todos los residentes |
| **Contratos** | Contratos con proveedores, personal o servicios | Administrador de Consorcio | Administrador General, Auditor |
| **Actas** | Actas de asamblea y reuniones de consorcio | Administrador de Consorcio | Todos los residentes |
| **Seguros** | Pólizas vigentes (incendio, responsabilidad civil, ascensores) | Administrador de Consorcio | Todos los residentes, Auditor |
| **Garantías** | Garantías de equipamiento y obras | Administrador / Proveedor | Administrador de Consorcio |
| **Manuales** | Manuales de uso de equipos (ascensor, bombas, portón) | Proveedor / Administrador | Encargado, Administrador |
| **Certificados** | Habilitaciones de activos de seguridad | Proveedor / Administrador | Todos los residentes, Auditor |
| **Documentación legal** | Habilitaciones municipales, AFIP, documentación laboral | Administrador de Consorcio | Administrador General, Auditor |

Este módulo es también el que sostiene el control de vencimientos que se explota visualmente en Gestión de activos (sección 9): cada certificado tiene una fecha de vencimiento que dispara el estado de "atención" o "crítico" del activo correspondiente.

**Nota de alcance:** este es el módulo donde la restricción de "no hay carga de archivos" (sección 1.4) deja de ser tolerable — es el punto del roadmap donde se decide e implementa el almacenamiento real de archivos, y donde los campos de URL del resto del sistema (fotos de reclamos, evidencias de órdenes de trabajo, comprobantes de pago) pasan a apuntar a él.

---

## 8. Gestión de proveedores

Uno de los puntos explícitos del pedido original: un directorio de contactos de confianza del consorcio, **diferenciando quiénes trabajan en exclusiva para el edificio de quienes también aceptan trabajos particulares** — algo que ningún competidor relevado ofrece de forma completa, y que le sirve directamente al vecino (poder contratar por su cuenta al plomero que ya conoce el edificio).

- **Alta:** nombre/razón social, contacto, rubros, y si es exclusivo del consorcio o también atiende particulares.
- **Rubros:** plomería, electricidad, gas, ascensores, matafuegos, jardinería, limpieza, seguridad, obras. Un proveedor puede tener varios.
- **Calificaciones y evaluaciones:** evaluación formal después de cada trabajo (cumplimiento de plazo, calidad, prolijidad) que alimenta una calificación general y queda como antecedente objetivo para decidir si se lo vuelve a contratar.
- **Contratos:** vínculo con el módulo documental.
- **Presupuestos:** historial de lo que presentó, se haya aprobado o no — permite comparar precios entre proveedores del mismo rubro a lo largo del tiempo.
- **Historial de intervenciones:** qué trabajo hizo, cuándo, en qué activo o espacio, a qué costo y cuánto tardó. Sale de las órdenes de trabajo, no se carga aparte.
- **Disponibilidad:** contacto y horarios, incluida la disponibilidad de emergencia — determinante en los rubros críticos.

**Dependencia conocida:** el modelo de Proveedor llega en una fase posterior a la financiera y a la de mantenimiento. Hasta entonces, los módulos que necesitan referenciar un proveedor (gastos, presupuestos, facturas, órdenes de trabajo) guardan la referencia **sin vínculo formal**, y ese vínculo se formaliza cuando el módulo existe. Es una decisión consciente para no bloquear tres módulos esperando a un cuarto.

---

## 9. Gestión de activos del edificio

Junto con el dashboard visual, el otro pilar del diferencial. Un "activo" es cualquier elemento físico que requiere seguimiento: matafuegos, ascensores, bocas de incendio, bombas de agua, portones, luces de emergencia.

| Atributo | Descripción |
|---|---|
| **Identificación** | Código único interno (tipo + ubicación, ej. "MAT-P3-01"). |
| **QR** | Código físico adherido al activo; al escanearlo abre su ficha completa desde el celular (para el encargado, el inspector o el proveedor). |
| **Fotos** | Registro fotográfico del estado actual y de instalación. |
| **Estado** | Calculado, nunca cargado a mano: verde (vigente), amarillo (próximo a vencer, ≤30 días), rojo (vencido o fuera de servicio). |
| **Ubicación** | Piso, espacio común o zona donde está instalado. |
| **Historial** | Todas las intervenciones sobre el activo, derivadas de las órdenes de trabajo. |
| **Garantía** | Vigencia de garantía del fabricante o instalador. |
| **Manual** | Manual de uso/mantenimiento (vínculo documental). |
| **Proveedor** | Responsable de su mantenimiento habitual. |
| **Próximo mantenimiento** | Fecha de la próxima inspección o recarga obligatoria. Dispara amarillo al acercarse y rojo si se vence sin registrarse. |
| **Costos acumulados** | Suma histórica de lo gastado en el activo, derivada de las órdenes de trabajo y gastos asociados. |

**Por qué importa:** en Argentina el vencimiento de la habilitación de matafuegos, ascensores o bocas de incendio no es un tema estético — es una obligación normativa que, si no se cumple, puede dejar al edificio inhabilitado y al administrador expuesto a responsabilidad civil ante un siniestro. El relevamiento lo confirmó textualmente: *"lo llevo con recordatorios en el celular o memoria, y ahí me la juego, porque la responsabilidad legal es mía"*.

---

## 10. Gestión de mantenimiento

Si Gestión de activos es la ficha de "qué es y en qué estado está", Gestión de mantenimiento es el flujo de "qué se hizo o se va a hacer".

### 10.1 Tipos

- **Preventivo:** programado para evitar fallas (recarga anual de matafuegos, service de ascensor).
- **Correctivo:** reparación de una falla ya detectada.
- **Programado:** trabajos planificados que no son ni preventivos ni urgentes (pintura de palier, impermeabilización) — el "plan de acciones futuras".
- **Emergencia:** intervención inmediata ante una situación crítica.

### 10.2 Órdenes de trabajo

Unidad central del módulo. Cada intervención genera una orden con: activo o espacio afectado, tipo, prioridad, responsable asignado, fechas de creación/inicio/cierre, costo y evidencias.

**Tres orígenes posibles:** manual (administrador o encargado), automática (por vencimiento de un activo) o **desde un reclamo** — en este último caso quedan vinculados, para no perder la trazabilidad de "quién lo pidió" → "qué se hizo al respecto".

**Flujo de estados propio, distinto al del reclamo:** `pendiente → en curso → resuelta`, estrictamente lineal y sin reapertura. Una orden de trabajo es un **registro de ejecución**, no un hilo de seguimiento: si el trabajo resulta incompleto, se genera una orden nueva y la vieja queda archivada tal como se cerró.

**Regla de asignación:** una orden puede nacer sin asignar (pendiente), pero **no puede pasar a "en curso" sin alguien asignado** — un encargado o un proveedor. Nunca una orden "en curso" sin nadie real haciéndola.

**Sincronización con el reclamo de origen.** Cuando una orden nace de un reclamo, los dos flujos caminan en paralelo automáticamente: generar la orden marca el reclamo como *asignado*, iniciar la orden lo pasa a *en curso*, y resolverla lo pasa a *resuelto*. La sincronización **nunca fuerza** una transición inválida: si el reclamo ya llegó a un estado terminal por otra vía, se deja como está.

### 10.3 Evidencias fotográficas

Fotos de antes y después de cada intervención, adjuntas a la orden — respaldo tanto para el administrador como para un eventual reclamo de garantía al proveedor.

### 10.4 Costos

Costo real de la orden (mano de obra + materiales), cargado al cerrarla. Se acumula en el activo afectado y en el gasto general del edificio.

### 10.5 Tiempo de resolución

Tiempo entre la apertura y el cierre de la orden. Indicador clave: permite detectar si cierto tipo de trabajo o cierto proveedor demora sistemáticamente más de lo esperado. Alimenta los KPIs del Dashboard General y los gráficos de Analítica.

---

## 11. Gestión de reclamos

La puerta de entrada más habitual para el residente: el módulo por el cual reporta un problema y hace seguimiento hasta su resolución. Junto con la morosidad, uno de los dos factores que determinan el color de un departamento en el dashboard visual.

### 11.1 Creación

El propietario o inquilino carga el reclamo indicando **qué pasa, dónde y con qué prioridad lo percibe**. El "dónde" tiene exactamente tres opciones, y son excluyentes:

1. **Su propia unidad.**
2. **Un espacio común** del edificio (SUM, ascensor, pasillo, etc.).
3. **El edificio en general** (ninguna de las dos anteriores).

Nunca puede ser una unidad *y* un espacio común a la vez. Si el residente tiene una sola unidad —el caso más común, y siempre el del inquilino— el sistema no le pregunta cuál: se resuelve solo.

El Administrador y el Encargado también pueden cargar un reclamo: pueden detectar algo ellos mismos sin esperar a que un vecino lo reporte.

### 11.2 Fotos de respaldo

El reclamo admite varias fotos (hoy, links — ver 1.4), esenciales para que quien gestiona entienda la magnitud sin ir a ver en persona antes de actuar.

### 11.3 Prioridad

Tres niveles, con esta definición exacta (es el texto que ve el residente al elegir, para que la elección signifique lo mismo para todos):

- **Leve:** no compromete a nadie más que a quien reclama, no es urgente.
- **Medio:** empieza a afectar o podría afectar a otras unidades o al funcionamiento normal del edificio.
- **Crítico:** compromete la seguridad de los residentes o del edificio, requiere atención inmediata.

Leve y medio pintan **amarillo** en el dashboard; crítico pinta **rojo**. Leve y medio nunca se distinguen por color, solo por la urgencia percibida dentro del propio reclamo.

### 11.4 Seguimiento y estados

Flujo: `recibido → asignado → en curso → resuelto → cerrado`, visible en todo momento para quien lo cargó. Quién puede mover qué:

- El **Administrador o el Encargado del edificio** mueven el flujo normal completo.
- **Quien lo creó** puede comentar en cualquier estado, pero no mover el flujo.

**La excepción de reapertura.** Un reclamo dado por *resuelto* puede volver a *en curso* si quien lo reportó confirma que el problema sigue — y es la única transición que el residente puede disparar además de la gestión. Sin esto, la única forma de corregir un cierre prematuro sería cargar un reclamo nuevo, perdiendo el historial de comentarios y fotos del original.

**"Cerrado" es siempre terminal, a propósito.** La recurrencia se resuelve de otra forma (ver 11.5): el antecedente tiene que quedar archivado tal como se cerró. Un problema que vuelve es un reclamo **nuevo**, no la reapertura de uno viejo.

### 11.5 Historial

Todo reclamo queda archivado con su resolución, como antecedente para detectar problemas recurrentes en una misma unidad o activo: la misma pérdida de agua reportada tres veces en un año es la señal de que la reparación anterior no fue efectiva. Esta es también la funcionalidad que el relevamiento identificó como la más valorada por el residente — *"si el mismo problema vuelve dentro de un año, poder mostrar que ya lo reclamé antes y la reparación no funcionó"*.

### 11.6 Comentarios

Hilo de conversación dentro del propio reclamo, entre quien reclama y quien gestiona — evitando que la conversación se disperse en WhatsApp o llamados. Accesible para el autor del reclamo y para la gestión del edificio.

### 11.7 Tiempo de resolución

Se mide entre la **creación** y el **cierre** del reclamo (no hasta "resuelto", que todavía puede reabrirse). Indicador central del Dashboard General y de la calidad de gestión del consorcio.

---

## 12. Reglas transversales del producto

Decisiones que no pertenecen a un módulo sino a la plataforma entera. Todas surgieron de construir y probar, no de diseñar en abstracto.

| Regla | Qué significa | Por qué |
|---|---|---|
| **Formato de números argentino** | Punto como separador de miles, coma como decimal (`1.234.567,89`), en toda la aplicación — incluidos los campos donde el usuario **escribe** un monto, que se formatean mientras tipea. | Un monto mal leído en un módulo financiero es un error real, no cosmético. |
| **Ningún diálogo nativo del navegador** | Nunca `alert()`, `confirm()` ni `prompt()`. Las confirmaciones se resuelven dentro de la interfaz: la acción se intenta, el servidor responde "esto requiere confirmación" explicando qué va a pasar, y el botón cambia a "Confirmar y reemplazar". | Los diálogos nativos rompen la identidad visual, no son responsive y no permiten explicar las consecuencias. |
| **Toda acción destructiva se explica antes de ejecutarse** | El mensaje de confirmación dice exactamente qué se va a perder o reescribir, no "¿estás seguro?". | Ver el caso de regeneración de expensas (6.1). |
| **Nadie puede dañarse a sí mismo** | Un usuario no puede desactivar su propia cuenta; el residente no puede confirmar su propio pago. Y siempre con doble resguardo: el backend lo rechaza *y* la interfaz no lo ofrece. | Aprendido de un incidente real durante el desarrollo: un Administrador General se desactivó a sí mismo y quedó sin forma de volver a entrar (hizo falta reparar la base a mano). |
| **Los antecedentes no se reescriben** | Reclamo cerrado, orden de trabajo resuelta y expensa liquidada son inmutables. Donde hay una excepción, es acotada, avisada y documentada. | Es la condición para que el registro sirva como prueba (ver 2.3). |
| **Un archivo por dominio, no por rol** | Cada módulo es una sola pantalla que muestra lo que corresponde según quién la mira, no una pantalla distinta por rol. | Evita duplicar lógica y que una vista quede desactualizada respecto de la otra. |
| **Las fotos y adjuntos son links, por ahora** | Campo de URL, sin carga de archivo real, hasta que exista el módulo documental. | Ver 1.4 y sección 7. Es la deuda técnica más visible del producto, y está asumida explícitamente. |
| **Cada capacidad nueva tiene que ser usable** | Ninguna funcionalidad se considera terminada sin un punto de entrada real en la interfaz. No existe "está en el backend, después le hacemos pantalla". | Lo no usable no se puede probar, y lo no probado no está hecho. |

---

## 13. Estado de la especificación

El código fue eliminado, pero no todas las secciones de este documento tienen el mismo grado de validación. Esta tabla es honesta al respecto, y sirve para saber dónde apoyarse con confianza y dónde todavía hay diseño sin contrastar.

| Módulo | Estado de la especificación |
|---|---|
| Usuarios, roles y autenticación | **Validado en la práctica** — construido, probado y corregido (ver 3.1). |
| Estructura del edificio (pisos, unidades, cocheras, espacios) | **Validado en la práctica.** |
| Gestión financiera completa (6.1 a 6.9) | **Validado en la práctica**, con cuatro investigaciones de respaldo y errores reales ya corregidos. |
| Reclamos (sección 11) | **Validado en la práctica**, flujo completo probado punta a punta. |
| Mantenimiento / órdenes de trabajo (sección 10) | **Validado en la práctica** en backend; la interfaz quedó especificada pero no llegó a construirse. |
| Dashboard Visual del edificio | **Validado visualmente** (arquitectura y comportamiento cerrados en la skill `premium-uiux`, motor de severidad implementado y probado), pero nunca conectado a datos reales. |
| Dashboard General y Analítica | Diseño, sin implementar. |
| Activos y seguridad normativa | Diseño, sin implementar. |
| Gestión documental | Diseño, sin implementar. Bloquea la carga real de archivos del resto del sistema. |
| Proveedores | Diseño, sin implementar. Otros módulos ya lo referencian de forma preliminar. |
| Comunicación interna y reservas | Diseño, sin implementar. |
| Módulo de seguridad | Diseño, sin implementar. |
| Capa de IA | Diseño, sin implementar. Deliberadamente al final: necesita datos reales sobre los cuales operar. |

---

*Documentos relacionados: [`02_Documento_Tecnico.md`](02_Documento_Tecnico.md) (arquitectura y modelo de datos) · [`03_Documento_Frontend.md`](03_Documento_Frontend.md) (sistema de diseño e interfaz) · [`05_Roadmap.md`](05_Roadmap.md) (ejecución) · [`entrevistas.md`](entrevistas.md) (relevamiento de necesidad) · [`investigaciones/`](investigaciones/) (decisiones con respaldo normativo).*

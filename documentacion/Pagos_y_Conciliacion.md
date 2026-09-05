# Registro de pagos y conciliación — investigación y criterio adoptado

> **Qué es este documento.** Antes de implementar la Tarea 9 de la Fase 2 ("Backend: registro de pagos y conciliación") el usuario pidió sumar CBU/alias/QR como medio de pago, y validar si es viable legalmente y cuál es la mejor forma de implementarlo. Se investigó antes de escribir código — mismo criterio que `Prorrateo.md`, `Caja_chica.md` y `Presupuestos_y_Facturas.md`. Hay un hallazgo importante que cambia el alcance real de "el QR": se documenta acá completo, con la recomendación, antes de tocar el modelo de `Pago`.
>
> Referencias cruzadas: Documento General, sección 6.2 · Roadmap, Fase 2 (registro de pagos y conciliación) · código en `backend/app/models/pago.py` (a extender).

---

## 1. Qué dice hoy la documentación del proyecto

Documento General, sección 6.2 (textual, completo — es todo lo que dice hoy):

> - Registro de pagos realizados (transferencia, efectivo, débito), con comprobante adjunto.
> - Conciliación entre lo liquidado y lo efectivamente cobrado.
> - Estado de cuenta por unidad, visible para el propietario correspondiente.

No menciona CBU, alias ni QR en ningún punto — es un pedido nuevo del usuario, no un gap de algo ya planeado. Sí menciona explícitamente **"conciliación"**, que es la palabra clave de todo este documento (ver sección 3).

---

## 2. El hallazgo importante: el QR de pago tiene un límite legal real

### 2.1 Lo que existe en Argentina: Transferencias 3.0 (BCRA)

El Banco Central regula un sistema de QR interoperable ("Transferencias 3.0") donde escanear el código desde CUALQUIER billetera o app bancaria dispara una transferencia inmediata a la cuenta del comercio — es el QR que se ve en cualquier kiosco o comercio hoy.

**El punto crítico:** ese QR **lo generan las entidades financieras y los proveedores de servicios de pago (PSP) registrados** — no una aplicación de terceros. Un desarrollo como SMART Building no puede generar un QR "Transferencias 3.0" real y válido sin que el administrador del consorcio tenga una cuenta en un banco/PSP que emita ese QR específico (y en ese caso, el QR lo da el banco, no lo generamos nosotros).

### 2.2 Qué significa esto para el diseño

Hay dos caminos posibles, con implicancias muy distintas:

| Opción | Qué es | Esfuerzo | Legal/técnicamente |
|---|---|---|---|
| **A. QR de conveniencia** (recomendado) | Un QR que al escanearlo muestra el CBU/alias como texto (o los copia), para que el usuario lo pegue en su propia app bancaria. | Bajo — se genera con la misma librería `qrcode` ya prevista en el proyecto (Fase 4, activos). | 100% legal: es solo un código de barras con texto, exactamente igual a mostrar el CBU escrito. No es un medio de pago en sí, es una ayuda para copiarlo. |
| B. QR de pago real (Transferencias 3.0 / Mercado Pago, etc.) | Un QR que dispara la transferencia automáticamente al escanearlo desde cualquier app. | Alto — requiere integrar con un PSP real (Mercado Pago, un banco) vía su API, con el administrador del edificio dado de alta como comercio en ese proveedor. | Requiere ser (o integrar con) un PSP registrado — fuera del alcance actual del proyecto, ninguna fase del Roadmap lo contempla. |

**Recomendación original: Opción A** (QR de conveniencia) — resuelve el pedido sin prometer una función que técnicamente no se puede construir de forma legítima con el alcance actual.

**Decisión final del usuario (corrección):** ni siquiera el QR de conveniencia — directamente **CBU y alias como texto, cada uno con su propio botón de copiar**, para que el usuario los pegue en la app de su banco/billetera. Más simple de usar en la práctica (copiar un texto es un toque; escanear un QR para volver a copiar el texto que había adentro es un paso de más) y elimina cualquier ambigüedad sobre si "hay un QR" implica que el pago se dispara solo. `qrcode` sigue en `requirements.txt` porque la Fase 4 (activos) sí lo va a necesitar para los códigos QR de matafuegos/ascensores — no se saca la dependencia, solo se saca su uso acá.

---

## 3. Conciliación: por qué un pago cargado por el usuario no puede quedar "confirmado" solo

Investigado el circuito real de cobro de expensas en Argentina: *"el consorcista paga y envía un comprobante, esperando a que la administración identifique el movimiento"* — la conciliación es un paso humano, el administrador confirma que el comprobante corresponde a una acreditación real antes de dar la deuda por saldada. El propio Documento General ya lo anticipa ("Conciliación entre lo liquidado y lo efectivamente cobrado" — conciliar implica comparar dos fuentes, no confiar en una sola).

**Consecuencia de diseño:** si un inquilino/propietario carga un pago (comprobante + fecha + monto) y el sistema lo marca como pagado al instante, cualquiera podría cargar un comprobante falso o cualquier monto y aparecer sin deuda — sin que la plata haya entrado de verdad a la cuenta del consorcio. Un pago cargado por el usuario tiene que nacer en estado **`pendiente`**, y sea el Administrador (General o de Consorcio) quien lo pase a `confirmado` (contrastándolo contra el resumen bancario real) o `rechazado` (comprobante inválido, monto no coincide, etc.). Solo un pago `confirmado` cuenta para "no tener deuda".

Esto también aclara un punto legal aparte: mostrar el CBU/alias de la cuenta del consorcio no convierte a SMART Building en un procesador de pagos — la plata nunca pasa por la plataforma, solo se muestra el dato para que el pago se haga por fuera (transferencia bancaria directa), y el comprobante se carga después para que el administrador lo audite. Es exactamente lo mismo que hoy hace cualquier administración que manda el CBU por WhatsApp o email.

---

## 4. El punto que el usuario no contempló: propietarios con más de una unidad

El pedido es "esto se hace por usuario, no hace falta elegir el piso" — cierto para la mayoría de los casos, pero el propio modelo de este proyecto ya permite (a propósito, Fase 1) que **un propietario tenga más de un departamento**. Si Juan tiene el 3°A y el 5°B, "cargar un pago como Juan" no alcanza para saber a cuál de las dos expensas corresponde.

**Resuelto así:** el usuario nunca ve ni elige "de qué piso" en el sentido de navegar el edificio — pero si tiene más de una unidad a su nombre, elige entre SUS PROPIAS unidades (un selector chico con sus 2-3 departamentos, nunca el edificio completo). Con una sola unidad (el caso más común, y siempre el caso de un inquilino — ya no puede tener dos, Fase 1), el campo ni se muestra: se resuelve solo.

---

## 5. Qué se va a implementar (Tarea 9 de la Fase 2)

| Cambio | Detalle |
|---|---|
| `Edificio.cbu`, `Edificio.alias_cbu` | Nuevos campos de configuración (nullable — no todos los edificios los van a tener cargados de entrada), editables por Administrador General/de Consorcio del edificio, mismo criterio que `contacto_emergencia_nombre`. |
| `GET /api/edificios/{id}/medio-pago` devuelve solo `cbu`/`alias_cbu` como texto | Sin QR (corrección final del usuario) — el frontend los muestra con un botón de copiar cada uno. |
| `Pago.estado` (`pendiente` / `confirmado` / `rechazado`) | Nace en `pendiente` cuando lo carga un propietario/inquilino. Un Administrador lo pasa a `confirmado` o `rechazado`. Solo `confirmado` cuenta para el estado de deuda (próxima tarea: cálculo de deudores). |
| `POST /api/mis-pagos` (o similar, alcance del usuario logueado) | El propietario/inquilino carga comprobante + fecha + monto; el `departamento_id` se resuelve solo si tiene una única unidad, o se elige entre las propias si tiene más de una — nunca un desplegable del edificio completo. |
| `PATCH /api/pagos/{id}/estado` | Para que el Administrador confirme o rechace — separado del alta, porque lo hace un rol distinto. |

### Explícitamente fuera de alcance (por ahora)

- **QR de pago instantáneo real** (Transferencias 3.0 / Mercado Pago) — requiere integrar con un PSP registrado, no es una extensión chica; se deja anotado para evaluar como una fase nueva si el usuario lo pide más adelante.
- **Notificación automática** al Administrador cuando entra un pago pendiente de conciliar — depende del módulo de Comunicados (Fase 8).
- Comprobantes respaldatorios de **gastos** (distinto de comprobantes de pago) — hallazgo aparte de esta misma investigación: desde agosto 2024 CABA exige que la liquidación de expensas incluya acceso a los comprobantes de los gastos (vía QR o link) — ya cubierto conceptualmente por `Factura`/`Presupuesto` (Fase 2, Tareas 2 y 6), pero la exposición real (QR/link en la liquidación) queda para la tarea de reportes/pantalla de expensas, no esta.

---

## 6. Fuentes consultadas

| Fuente | Qué aportó |
|---|---|
| [Transferencias 3.0: claves del sistema — BCRA](https://www.bcra.gob.ar/Noticias/transferencia-3-0-preguntas-respuestas.asp) | Confirma que el QR interoperable es emitido por entidades financieras/PSP, no por terceros. |
| [Pagos digitales: todas las cuentas... deberán tener un QR — Infobae](https://www.infobae.com/economia/2021/08/19/pagos-digitales-todas-las-cuentas-de-empresas-deberan-tener-un-codigo-qr-para-facilitar-las-transferencias/) | El QR lo generan bancos/PSP para sus cuentas comerciales — no una app externa sin ese rol. |
| [Gestión financiera de consorcios: cobros, pagos y conciliación — ConsorcioAbierto](https://www.consorcioabierto.com/blog/2026/08/25/gestion-financiera-consorcios/) | Confirma el circuito real: el consorcista paga y envía comprobante, la administración concilia contra el movimiento bancario real antes de acreditar. |
| [Los administradores de consorcios deberán mandar los comprobantes de los gastos junto con las expensas — LA NACION](https://www.lanacion.com.ar/sociedad/a-partir-de-hoy-los-administradores-de-consorcios-deben-mandar-los-comprobantes-de-los-gastos-junto-nid01082024/) | Hallazgo aparte: disposición CABA (agosto 2024) sobre comprobantes de GASTOS en la liquidación — no es el QR de pago pedido acá, pero es relevante para una tarea futura. |

---

*Última actualización: se saca el QR de conveniencia — CBU/alias se copian por separado, decisión final del usuario — 2026-09-05. Este documento se actualiza antes que el código cada vez que el criterio de pagos/conciliación cambie.*

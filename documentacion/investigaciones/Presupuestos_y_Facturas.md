# Presupuestos y Facturas — investigación y criterio adoptado

> **Qué es este documento.** Antes de implementar la Tarea 6 de la Fase 2 (`Presupuesto` y `Factura`) se investigó cómo funciona realmente este tramo de la cadena "gasto → presupuesto → factura → pago" que pide el Documento General (secciones 6.7-6.8) — tanto la práctica estándar de compras (procure-to-pay) como la normativa argentina de administración de consorcios y facturación (AFIP) — para no modelarlo "a ojo" y corregirlo después, como pasó con la caja chica. Mismo criterio que `Prorrateo.md` y `Caja_chica.md`.
>
> Referencias cruzadas: Documento General, secciones 6.7 y 6.8 · Roadmap, Fase 2 Tarea 6 · `que_hice.html` (se completa al aprobarse la tarea) · código en `backend/app/models/presupuesto.py`.

---

## 1. Marco

### 1.1 El flujo estándar (procure-to-pay), y por qué SMART Building lo simplifica

La práctica de compras formal (empresas medianas/grandes) sigue un flujo **"procure-to-pay"**: requisición → **orden de compra** → recepción de la mercadería/servicio → **factura** del proveedor → **"cotejo de tres vías"** (comparar factura, orden de compra y recepción) → pago. Es el estándar de la industria cuando hay control de inventario y múltiples aprobadores.

**Por qué no se traslada tal cual acá:** un consorcio de propiedad horizontal no tiene orden de compra formal ni recepción de mercadería como proceso separado — el "gasto" ya definido en la Tarea 2 de esta fase cumple el rol de "lo que se decidió comprar/contratar". Trasladar la cadena completa (con `OrdenCompra` propia) sería sobre-modelar un proceso que en este dominio es mucho más chico: se comparan presupuestos, se decide, se genera el gasto, llega la factura, se paga. Se simplifica a **Presupuesto → Gasto → Factura**, sin una entidad de orden de compra separada.

### 1.2 ¿Hace falta un mínimo de presupuestos por ley?

No. Ni la Ley de Propiedad Horizontal ni el Código Civil y Comercial exigen una cantidad mínima de presupuestos antes de aprobar un gasto — es **buena práctica de gestión**, y en la práctica real queda librado a lo que fije el reglamento de cada consorcio o decida la asamblea (típicamente: "a partir de tal monto, pedir 2 o 3 presupuestos"). **Conclusión para el diseño:** no se fuerza ninguna cantidad mínima ni máxima de `Presupuesto` por gasto a nivel de modelo — el sistema tiene que permitir cero, uno o varios, sin objetar nada.

### 1.3 Facturación en Argentina (AFIP) — qué se modela y qué no

Una factura real en Argentina lleva datos formales de AFIP: tipo (A/B/C, según la condición fiscal de emisor y receptor), CUIT del emisor, punto de venta + número correlativo, y el CAE (Código de Autorización Electrónico) que la valida. **Nada de esto se modela en detalle acá**: SMART Building no tiene (ni tiene planeada, en ningún punto del Roadmap) integración con AFIP — es un archivo/registro de la factura para trazabilidad interna del gasto, no un sistema de facturación. Modelar CAE/condición IVA/punto de venta como columnas separadas sería construir para una integración que no existe ni está planeada, algo que el propio proyecto evita explícitamente en tareas anteriores (ver el mismo criterio en `Gasto.proveedor_id`, deferido hasta que exista Fase 7). El número de comprobante (ej. "B 0001-00000123") se guarda como un solo texto libre.

---

## 2. Fuentes consultadas

| Fuente | Qué aportó |
|---|---|
| [Procure-to-pay (P2P): guía completa — Amazon Business](https://business.amazon.es/es/blog/procure-to-pay) | Confirma el flujo estándar de compras (requisición → orden de compra → recepción → factura → cotejo de tres vías → pago) y por qué es más grande que lo que necesita este dominio. |
| [Orden de compra: qué es y para qué sirve — Vantegrate](https://vantegrate.com/glosario/orden-compra) | La orden de compra ancla el ciclo P2P — confirma que sin ese proceso formal (el caso de un consorcio chico), no tiene sentido modelarla aparte. |
| [Cuántos presupuestos debe solicitar el presidente de una comunidad](https://www.digitalmantenimientos.com/blog/cuantos-presupuestos-debe-solicitar-el-presidente-de-una-comunidad) | Confirma que no hay obligación legal de una cantidad mínima de presupuestos — queda a criterio del reglamento/asamblea. |
| [Factura Electrónica AFIP: Tipos A, B, C y E, el CAE — FacturaSimple](https://facturasimple.com/ar/blog/ar-factura-electronica-afip-cae-tipos) | Detalla los campos formales de una factura argentina (tipo, CUIT, CAE, punto de venta) — usado para decidir explícitamente qué NO modelar todavía. |

---

## 3. Qué decidimos tomar para SMART Building

| Decisión | Por qué |
|---|---|
| Cadena simplificada **Presupuesto → Gasto → Factura**, sin `OrdenCompra` propia. | El proceso de compras de un consorcio no tiene ese paso formal separado — el `Gasto` ya cumple ese rol. Agregar una orden de compra sería sobre-modelar (sección 1.1). |
| `Presupuesto` no exige cantidad mínima ni máxima por gasto — puede haber cero, uno o varios. | No hay obligación legal de una cantidad fija (sección 1.2); es una decisión de gestión de cada consorcio, no una regla que el modelo deba imponer. |
| `Presupuesto.estado` (`pendiente` / `aprobado` / `rechazado`), `CHECK` cerrado. | Es lo que realmente le da sentido a "comparar antes de aprobar" — sin un estado, no hay forma de registrar cuál de varios presupuestos se eligió. Mismo criterio que `Cochera.tipo`/`MovimientoFondo.tipo` (valores cerrados reales). |
| `Presupuesto.gasto_id` (`ForeignKey` real, nullable). | A diferencia de `proveedor_id`/`activo_id` en `Gasto` (deferidos porque esas tablas no existen), acá `gastos` ya existe — no hay motivo para no linkear de una vez el presupuesto aprobado con el gasto real que generó. Nullable porque un presupuesto puede quedar rechazado y nunca convertirse en gasto. |
| `Factura.gasto_id` (`ForeignKey` real, `NOT NULL`). | El Documento General 6.8 es explícito: "vinculadas a su gasto correspondiente" — no es opcional. |
| `Factura.numero` como texto libre (no se separan tipo/CUIT/CAE/punto de venta). | AFIP no está integrado ni planeado en este proyecto (sección 1.3) — separar esos campos sería modelar para una integración que no existe. |
| `proveedor_id` en ambos modelos, sin `ForeignKey` real todavía (igual que `Gasto`). | La tabla `proveedores` no existe hasta la Fase 7 — mismo criterio ya aplicado, documentado en la Tarea 2 de esta fase. |

### Explícitamente fuera de alcance (por ahora)

- **Integración con AFIP** (validación de CAE, consulta de CUIT, emisión de comprobantes) — no está en el Roadmap de este proyecto en ninguna fase.
- **Orden de compra formal** y **cotejo de tres vías** — de más para la escala de un consorcio; el `Gasto` ya cumple ese rol.
- **Carga del archivo de la factura** (PDF/foto) — depende de Gestión documental (Fase 7); por ahora solo un campo de texto/URL suelto, mismo criterio que `Pago.comprobante_url`.
- **Regla de "a partir de tal monto, exigir N presupuestos"** — es una configuración de cada edificio (reglamento propio), no una regla fija del sistema; si se pide más adelante, es un campo de configuración del edificio (como `dias_vencimiento_expensas`), no una constante de código.

---

## 4. Estado de la implementación

Implementado en `backend/app/models/presupuesto.py`:

| Modelo | Campos clave |
|---|---|
| `Presupuesto` | `edificio_id` (FK), `proveedor_id` (suelto, sin FK), `descripcion`, `monto`, `fecha`, `estado` (`pendiente`/`aprobado`/`rechazado`), `gasto_id` (FK, nullable). |
| `Factura` | `gasto_id` (FK, `NOT NULL`), `proveedor_id` (suelto, sin FK), `numero` (texto libre), `monto`, `fecha`, `archivo_url` (nullable). |

Tests en `backend/tests/test_modelo_presupuesto.py` — persistencia básica, varios presupuestos para el mismo gasto potencial con distintos estados, `estado` inválido rechazado, factura vinculada a un gasto real, factura sin `gasto_id` rechazada.

## 5. Lo que falta (tareas futuras de la Fase 2)

- Endpoints CRUD de Presupuestos y Facturas (ya itemizados en el Roadmap), donde de verdad se decide "aprobar" un presupuesto y generar/vincular el `Gasto`.
- Pantalla dentro de `financiero.html` para cargar y comparar presupuestos, y archivar facturas.
- (Eventual, no pedido todavía) configuración por edificio de "monto a partir del cual se exigen N presupuestos".

---

*Última actualización: investigación inicial y diseño — 2026-09-04. Este documento se actualiza antes que el código cada vez que el criterio de presupuestos/facturas cambie.*

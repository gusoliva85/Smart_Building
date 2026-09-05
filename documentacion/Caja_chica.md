# Caja chica y Fondo de Reserva — investigación y criterio adoptado

> **Qué es este documento.** Al revisar la Tarea 5 de la Fase 2 (`Fondo`, `MovimientoFondo`, `Caja`) surgió la duda de si el modelo de `Caja` estaba bien planteado — se había implementado como un único registro por edificio con un responsable, sin ningún movimiento. Antes de tocar código de nuevo se investigó cómo funciona realmente una caja chica (tanto en la práctica de consorcios como en contabilidad general — es un concepto universal, no específico de Argentina) y este documento deja registrada esa investigación y la corrección de diseño que salió de ella. Mismo criterio que `Prorrateo.md`: separado del Documento General/Técnico porque es un tema con entidad propia que puede volver a revisarse, y cualquier cambio futuro a este criterio actualiza primero este documento, recién después el código.
>
> Referencias cruzadas: Documento General, secciones 6.5 y 6.6 · Roadmap, Fase 2 Tarea 5 · `que_hice.html`, slide `f2-t5` · código en `backend/app/models/fondo.py`.

---

## 1. Marco (legal y de práctica contable)

### 1.1 Fondo de Reserva — Código Civil y Comercial, art. 2049

El Fondo de Reserva **no es obligatorio por ley** en Argentina: el Código Civil y Comercial no lo exige de manera general, pero **sí es obligatorio para los propietarios si surge del reglamento de propiedad y administración** del edificio. Cuando existe:

- Se nutre de **aportes de los propietarios** (en la práctica, casi siempre un porcentaje adicional sobre la expensa mensual).
- Está pensado para **gastos imprevistos y mayores a los ordinarios** — no para el gasto corriente del mes (eso lo cubre la expensa normal).
- El **consejo de propietarios autoriza al administrador** a disponer de él ante ese tipo de gastos — no es una decisión unilateral del administrador.
- No sigue el sistema de "monto fijo repuesto periódicamente" (ver 1.2): simplemente **acumula** aportes y se reduce con los usos autorizados, sin un piso ni un techo fijado por ley.

### 1.2 Caja chica — el sistema de "fondo fijo" (universal, no específico de consorcios)

Acá está el punto que motivó esta investigación. La caja chica, tanto en consorcios como en cualquier organización, se maneja bajo el **sistema de fondo fijo (imprest system)**, con las mismas piezas en todas las fuentes consultadas:

1. Se asigna un **monto fijo inicial** (el "fondo fijo") para cubrir gastos menores e inmediatos.
2. Cada gasto se cubre contra un **comprobante** (recibo, factura, ticket, vale de caja chica).
3. Cuando el efectivo disponible baja a un mínimo, el responsable **rinde cuentas** (presenta los comprobantes acumulados) y se **repone** el fondo hasta volver a su monto original — la reposición es, en sí misma, un movimiento (un ingreso) a la caja.
4. Todo esto requiere un **libro de registro de movimientos** — fecha, concepto, monto, saldo — porque sin eso no hay forma de saber cuánto hay ni de rendir cuentas. Una de las fuentes lo resume así: es lo que permite "asegurar la trazabilidad de cada peso".

**La conclusión de la investigación:** un modelo de `Caja` que solo guarda "este edificio tiene esta persona responsable" no alcanza para nada de lo anterior — no puede calcular saldo, no puede rendir cuentas, no puede reponerse. Le falta exactamente el mecanismo que le da sentido a una caja chica.

---

## 2. Fuentes consultadas

| Fuente | Qué aportó |
|---|---|
| [ARTS. CODIGO CIVIL Y COMERCIAL — Título V, Propiedad horizontal](https://www.cpcesfe2.org.ar/wp-content/uploads/2019/03/4305-Codigo_Civil_y_Comercial_TituloV.pdf) | Confirma que el Fondo de Reserva depende del reglamento, no es de exigencia legal directa. |
| [Control de caja chica: ¿Por qué es importante y cómo se hace? — Rindegastos](https://blog.rindegastos.com/cu%C3%A1les-son-los-riesgos-de-una-caja-chica-mal-administrada) | El responsable rinde cuentas con comprobantes; se necesita un libro de registro (fecha, concepto, monto, saldo, firma) para trazabilidad. |
| [Mejorá tu gestión financiera: Caja Chica vs Fondo Fijo — Edenred](https://edenred.com.ar/blog/diferencias-caja-chica-fondo-fijo/) | Distingue caja chica de fondo fijo y confirma el mecanismo de reposición contra comprobantes. |
| [Fondo de Caja Chica - Registros y formatos a utilizar](https://blog.excelcontablex.com/fondo-de-caja-chica/) | Detalla el sistema de fondo fijo: monto fijo inicial, egresos contra comprobante, reposición al monto original cuando baja a un mínimo. |

---

## 3. Qué decidimos tomar para SMART Building

| Decisión | Por qué |
|---|---|
| `Fondo` + `MovimientoFondo` **quedan tal como están** (ya implementados y verificados) — sin cambios. | Coinciden con el art. 2049: acumulan aportes, se usan para gastos imprevistos autorizados, sin un monto fijo que reponer. No hacía falta corregir nada acá. |
| `Caja` suma un campo **`monto_fijo`** (el monto al que se repone). | Es la pieza central del sistema de fondo fijo — sin él, "reponer la caja" no tiene un objetivo numérico contra el cual reponerse. |
| Se agrega un modelo nuevo **`MovimientoCaja`**, con el mismo patrón que `MovimientoFondo` (`tipo` ingreso/egreso con `CHECK` cerrado, `monto`, `fecha`, `descripcion`). | Es el "libro de registro" que exige la práctica real — sin esto, la caja no puede calcular su saldo ni sostener una rendición de cuentas. Reutiliza el mismo patrón ya validado para `MovimientoFondo` en vez de inventar uno nuevo. |
| El saldo de la caja se sigue calculando **sumando movimientos** (ingresos − egresos), igual que en `Fondo` — no se guarda como columna aparte. | Mismo criterio ya aplicado: un número guardado aparte se puede desincronizar del historial real; sumar movimientos es la fuente de verdad. |
| Una reposición de caja es, en el modelo, un `MovimientoCaja` de tipo `"ingreso"` — no un campo ni una acción especial. | Es exactamente cómo funciona en la práctica: la reposición ES un movimiento más (el que trae el saldo de vuelta cerca del `monto_fijo`), no una operación distinta a nivel de datos. |

### Explícitamente fuera de alcance (por ahora)

- **Carga de comprobantes** (foto/PDF de cada vale o factura) — depende de Gestión documental (Fase 7), que todavía no existe. `MovimientoCaja.descripcion` alcanza para dejar constancia en texto por ahora.
- **Alertas automáticas** de "la caja está por debajo de su monto fijo, hay que reponerla" — es lógica de un endpoint/notificación futura, no del modelo de datos.
- **Vínculo entre un `MovimientoCaja` de egreso y un `Gasto` formal** — podría interesar más adelante para evitar doble carga del mismo gasto chico, pero no está pedido todavía y agregarlo ahora sería resolver un problema que no le toca el turno a esta tarea.

---

## 4. Estado de la implementación

`Fondo` y `MovimientoFondo` (`backend/app/models/fondo.py`) ya estaban implementados y verificados con 6 tests — sin cambios por esta investigación.

Corrección a `Caja`, en el mismo archivo:

| Cambio | Detalle |
|---|---|
| `Caja.monto_fijo` | `Numeric(12,2)`, `NOT NULL`, `CHECK > 0` — el monto al que se repone la caja. |
| Modelo nuevo `MovimientoCaja` | `caja_id` (FK), `tipo` (`CHECK IN ('ingreso','egreso')`), `monto` (`Numeric(12,2)`, `CHECK > 0`), `fecha`, `descripcion` — mismo esqueleto que `MovimientoFondo`. |
| `Caja.movimientos` | `relationship` nueva, mismo patrón que `Fondo.movimientos`. |

Tests nuevos en `backend/tests/test_modelo_fondo.py`: caja con reposición y egresos dando el saldo neto esperado, `tipo` inválido rechazado, `monto` inválido rechazado, `monto_fijo` en 0 o negativo rechazado.

## 5. Lo que falta (tareas futuras de la Fase 2)

- Endpoints CRUD de Fondos y Caja (ya itemizados en el Roadmap) — ahí es donde se calcula el saldo real sumando movimientos y se expone al frontend.
- Pantalla de "Fondos, Caja, Presupuestos y Facturas" dentro de `financiero.html`.
- (Eventual, no pedido todavía) vínculo entre `MovimientoCaja` y `Gasto`, y carga de comprobantes cuando exista Gestión documental.

---

*Última actualización: corrección de `Caja` (agrega `monto_fijo` y `MovimientoCaja`) tras investigar el sistema de fondo fijo — 2026-09-04. Este documento se actualiza antes que el código cada vez que el criterio de caja chica o fondo de reserva cambie.*

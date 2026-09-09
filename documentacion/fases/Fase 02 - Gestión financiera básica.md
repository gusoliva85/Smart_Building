# Fase 2 — Gestión financiera básica

**Estado:** completa (17 de 18 tareas aprobadas — la que falta es la prueba manual de punta a punta final, sin funcionalidad nueva pendiente).
**Corresponde a:** Documento General, sección 6; Documento Técnico, sección 8.

## Objetivo de la fase

Construir el ciclo financiero completo de un consorcio: **cargar gastos → prorratearlos entre departamentos → liquidar la expensa mensual → que el residente pague → que el Administrador concilie ese pago → saber quién debe y cuánto**. De acá sale, además, el dato de morosidad que en la Fase 5 va a colorear de amarillo/rojo un departamento en el Dashboard Visual.

Es el módulo más grande del proyecto hasta la fecha: 5 dominios de datos (`Gasto`, `Expensa`, `Pago`, `Fondo`/`Caja`, `Presupuesto`/`Factura`), una única pantalla (`financiero.html`) con 5 pestañas, y la primera vez que Propietario/Inquilino tienen algo real que ver en el sistema (hasta esta fase, esos roles solo veían un sidebar vacío).

---

## 1. El criterio de prorrateo — investigado antes de programar

Antes de tocar un modelo, se validó contra la normativa argentina real (Ley 13.512 y su continuación en el Código Civil y Comercial, arts. 2037 y siguientes) cómo se reparte un gasto entre propietarios. El resultado cambió el diseño: **no es "partes iguales" ni "por m²" como criterio global** — cada unidad tiene un **coeficiente (%) fijo**, registrado en el reglamento de propiedad horizontal del edificio real. "Partes iguales" y "por m²" quedan solo como atajos para completar ese coeficiente la primera vez.

```python
# services/finanzas.py — nunca redondea cada parte por separado: la última
# unidad recibe el resto exacto, así la suma siempre da el total real.
def prorratear_gasto(monto_total: float, coeficientes: list[float]) -> list[float]:
    validar_coeficientes(coeficientes)  # tienen que sumar 100%
    montos = [round(monto_total * c / 100, 2) for c in coeficientes[:-1]]
    montos.append(round(monto_total - sum(montos), 2))
    return montos
```

`calcular_prorrateo_periodo()` automatiza esto de punta a punta: suma los `Gasto` reales del mes y los cruza contra `Departamento.coeficiente` de la base — es la única función de este archivo que toca la base de datos, el resto es lógica pura y testeable sin ella. Investigación completa en [`investigaciones/Prorrateo.md`](../investigaciones/Prorrateo.md).

## 2. Los 5 dominios de datos

| Modelo | Qué guarda | Detalle importante |
|---|---|---|
| `Gasto` | Rubro, monto, fecha, descripción | Base de todo — sin gastos cargados no hay nada para prorratear. |
| `Expensa` + `ExpensaDetalle` + `ExpensaDepartamento` | Liquidación de un edificio para un período | `ExpensaDepartamento` es una **foto fija**: el monto que le tocó a cada unidad queda congelado al generar la expensa, nunca se recalcula si el coeficiente cambia después (mismo criterio que Stripe/Zuora para facturación real — ver `Prorrateo.md` sección 6). |
| `Pago` | Departamento, expensa, monto, medio de pago, `estado` | `estado` (`pendiente`/`confirmado`/`rechazado`) es el corazón de la conciliación — ver sección 4. |
| `Fondo`/`MovimientoFondo`, `Caja`/`MovimientoCaja` | Fondos especiales y caja chica | El saldo **nunca se guarda**, se calcula siempre sumando movimientos — así no hay forma de que un número quede desincronizado del historial real. `Caja` sigue el sistema real de "fondo fijo" (investigado en [`Caja_chica.md`](../investigaciones/Caja_chica.md) tras una duda del usuario sobre el primer diseño, que no tenía movimientos propios). |
| `Presupuesto`/`Factura` | Trazabilidad gasto→presupuesto→factura→pago | `Presupuesto` nace `pendiente`, pasa a `aprobado` (opcionalmente vinculado a un `Gasto` real) o `rechazado`. `Factura` siempre exige un `gasto_id` del mismo edificio. |

## 3. Generar la expensa mensual — transaccional de punta a punta

```python
# routers/financiero.py
@router.post("/{edificio_id}/expensas", response_model=ExpensaSalida, status_code=201)
def generar_expensa_mensual(datos, edificio=Depends(requerir_admin_del_edificio), db=Depends(obtener_db)):
    try:
        montos_por_departamento = calcular_prorrateo_periodo(db, edificio.id, datos.anio, datos.mes)
    except ValueError as error:
        raise HTTPException(400, str(error))   # coeficientes incompletos, sin gastos cargados, etc.

    expensa = Expensa(edificio_id=edificio.id, anio=datos.anio, mes=datos.mes, total=...)
    db.add(expensa)
    db.flush()   # dispara el UniqueConstraint de período si ya existe una expensa para ese mes
    for rubro, monto in totales_por_rubro.items():
        db.add(ExpensaDetalle(expensa_id=expensa.id, rubro=rubro, monto=monto))
    for departamento_id, monto in montos_por_departamento.items():
        db.add(ExpensaDepartamento(expensa_id=expensa.id, departamento_id=departamento_id, monto=monto))
    db.commit()   # todo junto, o nada — si el prorrateo falla, no queda una Expensa a medio crear
```

## 4. Pagos y conciliación — un pago nunca se acredita solo

Investigado contra la práctica real de consorcios ([`Pagos_y_Conciliacion.md`](../investigaciones/Pagos_y_Conciliacion.md)): el residente transfiere por fuera de la plataforma y carga el comprobante; el pago **nace `pendiente`** y solo cuenta como cobrado cuando un Administrador lo concilia contra el movimiento bancario real. Sin este paso, cualquiera podría cargar un comprobante falso y aparecer al día sin que la plata haya entrado.

```python
def _saldo(expensa_departamento) -> float:
    return round(float(expensa_departamento.monto) - _pagado_confirmado(expensa_departamento), 2)
    # _pagado_confirmado() solo suma los Pago con estado == "confirmado" — nunca los pendientes
```

**Decisión de UX, revertida a pedido del usuario:** se investigó un QR de pago (Transferencias 3.0/Mercado Pago), pero la normativa del BCRA exige que ese QR interoperable lo emita un banco/PSP registrado, no una app de terceros — quedó fuera de alcance. La primera versión mostraba un "QR de conveniencia" (que solo codificaba el CBU como texto); el usuario lo descartó explícitamente y pidió mostrar CBU y alias con un botón de copiar cada uno, para que el pago se haga desde la app del banco del propio usuario.

```html
<!-- financiero.html — CBU/alias, sin QR -->
<div class="dato-copiable">
  <div class="dato-copiable-label">CBU</div>
  <div class="dato-copiable-valor">0170099220000001234567</div>
  <button class="icon-btn icon-btn-sm" data-copiar="cbu">...</button>  <!-- assets/js/copiar.js -->
</div>
```

Al cargar un pago parcial, un aviso in-line confirma cuánto va a quedar pendiente — sin usar `confirm()` del navegador (el proyecto no usa esos diálogos en ningún lado):

```js
function actualizarAvisoParcial() {
  const saldo = Number(form.dataset.saldo);
  const monto = Number(campoMonto.value);
  if (monto > 0 && monto < saldo) {
    avisoParcial.textContent = `Es un pago parcial — te va a quedar un saldo de ${Moneda.formatear(saldo - monto)}.`;
  }
}
```

## 5. Deudores — vista calculada, nunca una tabla propia

Documento Técnico 5.2: la deuda de un departamento no se guarda, se recalcula recorriendo sus `ExpensaDepartamento` con saldo pendiente. `meses_atraso` es el dato que en la Fase 5 va a decidir si un departamento pinta amarillo (1 mes) o rojo (más de 1 mes) en el Dashboard Visual.

```python
def _calcular_deudores(db, edificio_id, hoy=None):
    for depto in departamentos_del_edificio:
        impagas = [(ed, saldo) for ed in depto.expensas_departamento if (saldo := _saldo(ed)) > TOLERANCIA]
        if not impagas:
            continue
        mas_vieja = min(ed.expensa.anio * 12 + ed.expensa.mes for ed, _ in impagas)
        meses_atraso = max(0, mes_actual_absoluto - mas_vieja)
        deudores.append(DeudorSalida(..., meses_atraso=meses_atraso, ...))
    return sorted(deudores, key=lambda d: d.meses_atraso, reverse=True)
```

## 6. Fondos, Caja, Presupuestos y Facturas — agrupados en una sola pestaña

Con datos reales de prueba, sumar 4 pestañas más a `financiero.html` (además de Gastos/Expensas/Pagos/Deudores) daba 8 botones en la misma fila — demasiado para el flujo principal. Se resolvió como **una pestaña "Fondos" con su propia sub-navegación** de 4 secciones, reutilizando el mismo `.view-switch` en dos niveles.

Presupuestos reutiliza los botones `.boton-chico`/`.boton-chico-critico` creados para la conciliación de Pagos — mismo patrón visual "Aprobar/Rechazar" que "Confirmar/Rechazar", documentado una sola vez en la skill para no reinventarlo cada vez que aparece un flujo de aprobación.

**Dos bugs reales, encontrados con Playwright antes de aprobar la tarea (no solo inspección visual):**
1. El saldo de un fondo mostraba el valor viejo después de cargar un movimiento — el modal se refrescaba con la caché sin haber vuelto a pedir el listado al backend primero.
2. Un `<select required>` oculto (el responsable de la caja chica, cuando el rol logueado no tiene acceso a `/usuarios`) bloqueaba el envío del formulario **en silencio**: Chromium no puede enfocar un campo obligatorio no renderizado para rechazarlo, así que el evento `submit` nunca llegaba a dispararse. Se sacó el `required` nativo del HTML y la validación quedó a cargo del JS del formulario.

## 7. Rol Inquilino — decisión de RBAC dejada deliberadamente así

Al revisar la Fase 2 completa se encontró que `services/autorizacion.py` fija `ve_financiero_unidad: False` para Inquilino por defecto ("habilitable por excepción recién en la Fase 11"), pero esa bandera nunca se aplicó en ningún endpoint — `GET /api/mis-departamentos` y `POST /api/pagos` tratan a Propietario e Inquilino exactamente igual. Consultado con el usuario, se decidió **dejarlo así a propósito** por ahora (más práctico para probar la app mientras el sistema de excepciones de la Fase 11 no existe) — queda anotado como el punto exacto a revisar cuando esa fase llegue.

Por el mismo motivo, el rol **Auditor** quedó fuera de la pestaña Deudores: la matriz le da lectura del financiero de un edificio, pero no existe ningún mecanismo que defina a qué edificios accede un Auditor puntual (la tabla `UsuarioEdificio`, pensada para esto desde la Fase 1, nunca se pobló) — se resuelve en la Fase 11 junto con el resto de permisos por excepción.

## 8. Frontend: una pantalla, dos audiencias

`financiero.html` + `financiero.js` es un solo archivo para las dos audiencias del módulo (Documento Técnico 4.1: un archivo por dominio, no uno por rol):

- **Administrador General/de Consorcio:** listado de edificios → detalle con las 5 pestañas de gestión.
- **Propietario/Inquilino:** directo a "Mi cuenta" — sus propias unidades, el estado de cada expensa, y desde ahí el botón "Pagar".

```js
// financiero.js — ruteo por rol al arrancar, nunca dos archivos separados
if (usuario.rol === 'propietario' || usuario.rol === 'inquilino') {
  mostrarSolo(vistaMiCuenta);
  await cargarMiCuenta();
} else if (usuario.rol === 'admin_general' || usuario.rol === 'admin_consorcio') {
  ...
}
```

## 9. Lo que encontró la prueba manual de punta a punta

La última tarea de la fase (probar todo con el frontend real, no solo con tests) encontró tres huecos genuinos y dos pedidos de ajuste — exactamente para eso sirve una prueba de punta a punta, y quedan documentados acá porque son parte real de lo que se entrega en esta fase, no un capítulo aparte:

- **La pantalla de Configuración de coeficientes no existía.** `Prorrateo.md` (sección 1) siempre anticipó que el coeficiente de cada departamento sería "editable después desde una pantalla de Configuración" — nunca se construyó, ni el endpoint ni la UI. Solo se notó porque el edificio usado en el resto de la fase ya tenía coeficientes cargados a mano en la base. Se agregó `PATCH .../departamentos/{id}/coeficiente` (manual) y `POST .../{id}/coeficientes/auto` (partes iguales / por m², reutilizando `services/finanzas.py`), con su UI en `edificios.html` → Estructura y un resumen en vivo de la suma. De paso apareció un bug real de precisión: los atajos redondeaban a 4 decimales pero la columna solo guarda 3, así que la suma dejaba de dar 100% recién al persistir en edificios grandes — corregido a 3 decimales.
- **No se podía editar un gasto ya cargado.** Se sumó `PATCH /api/edificios/{id}/gastos/{id}` + botón de editar, reutilizando el modal de alta en modo edición. Nunca reabre una expensa ya emitida (sigue valiendo la foto fija de la sección 3) — solo afecta a la próxima que se genere.
- **El modal de detalle de expensa no entraba en la pantalla en mobile.** `.modal`, el componente compartido de toda la skill, nunca tuvo `max-height`/`overflow-y` — corregido en un solo lugar, arregla todos los modales del proyecto.
- **El monto se cargaba sin ningún separador.** El campo Monto de Gastos pasa de `<input type="number">` a un campo de texto con separador de miles en vivo (`assets/js/monto-input.js`, nuevo y reutilizable) — mismo formato `es-AR` que ya usa `moneda.js` para mostrar montos.
- **No había forma de corregir una expensa ya generada.** Si un gasto o un coeficiente se corrige después de liquidar el período, hacía falta volver a generarla — antes era un error sin salida. Se agregó una excepción deliberada y acotada a la inmutabilidad de la sección 3: **solo la última expensa del edificio** admite reemplazo, con aviso (`409`) y confirmación explícita (`confirmar_reemplazo: true`) antes de ejecutar — nunca en silencio, nunca para un período anterior. Detalle completo en `Prorrateo.md`, sección 8.

---

## Cómo probarlo

Credenciales completas en [`usuarios.md`](../usuarios.md). El edificio de referencia con datos reales en los 3 estados posibles de Pago y Presupuesto es **"Torre Cierre Fase 1"**.

1. `admin@smartbuilding.test` → Financiero → Torre Cierre Fase 1: recorrer las 5 pestañas (Gastos, Expensas, Pagos, Deudores, Fondos).
2. En Pagos: confirmar el pago pendiente, ver que el saldo de Octubre baja.
3. `propietario@smartbuilding.test` o `renata.medina@ejemplo.test` (inquilina real de la misma unidad, `test1234`) → Mi cuenta: cargar un pago nuevo, ver el aviso de saldo parcial y la nota de "pendiente de confirmación".

## Estado final

242 tests automáticos de backend pasando (empezó en 87 al cierre de la Fase 1). Verificado con Playwright contra el backend real en cada pestaña — admin_general, admin_consorcio, propietario e inquilino, mobile + tema oscuro, cero errores de consola. Fase cerrada con sus 18 tareas aprobadas, incluida la prueba manual de punta a punta.

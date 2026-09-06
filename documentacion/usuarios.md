# Usuarios de prueba

Registro de **todos** los usuarios creados durante el desarrollo — a mano o por seed — con su contraseña real. Son deliberadamente triviales porque el proyecto está en modo test: nunca se guardan en texto plano en la base, solo hasheadas (Documento Técnico, sección 3.2). Este archivo es un caso de prueba, no un secreto — lo más probable es que se elimine (o se resetee la base) una vez que el proyecto esté listo para un edificio real.

**Cómo mantenerlo:** cada vez que se cree un usuario nuevo (a mano, por un endpoint, o por un script de seed) para verificar una tarea, se agrega una fila acá con su contraseña real en el momento de la creación — nunca después, porque la contraseña ya quedó hasheada en la base y no se puede recuperar.

---

## Usuarios nombrados (uno por rol/caso de prueba puntual)

| Nombre completo | Email | Contraseña | Rol | Unidad asignada | Origen |
|---|---|---|---|---|---|
| Administrador General | `admin@smartbuilding.test` | `admin123` | `admin_general` | — (cartera completa) | Seed (`python -m app.seed`), Fase 1 |
| Propietario de Prueba | `propietario@smartbuilding.test` | `prop123` | `propietario` | 1A y 1B de Torre Central; 1A de Torre Cierre Fase 1 | Alta manual, Fase 1 Tarea 7 |
| Administrador de Consorcio de Prueba | `consorcio@smartbuilding.test` | `consorcio123` | `admin_consorcio` | Administra Torre Playwright (x2) y Torres Independencia 3252 | Alta manual, Fase 1 Tarea 14 |
| Encargado de Prueba | `encargado@smartbuilding.test` | `encargado123` | `encargado` | — | Alta vía `usuarios.html`, Fase 1 Tarea 15 |
| Prueba Modal | `prueba.modal@smartbuilding.test` | *(desconocida — no quedó documentada al crearla)* | `inquilino` | Sin asignar | Alta ad-hoc durante una verificación puntual de un modal, antes de que existiera esta lista. Login inutilizable hasta resetear la contraseña (no hay endpoint de reseteo todavía) — se deja documentada igual para no perder el registro de que el usuario existe. |

---

## Propietarios e inquilinos random (`app/seed_propietarios_inquilinos.py`)

10 propietarios + 20 inquilinos con nombres/apellidos argentinos generados al azar (Fase 2, pedido explícito del usuario) — **contraseña compartida `test1234`** para los 30. Salvo la excepción marcada abajo, ninguno tiene todavía una unidad real asignada (quedan disponibles para probar la pantalla de asignación de `edificios.html` cuando haga falta un propietario/inquilino "nuevo").

| Nombre completo | Email | Rol | Unidad asignada |
|---|---|---|---|
| Isabella Sánchez | `isabella.sanchez@ejemplo.test` | `propietario` | Sin asignar |
| Pilar Sánchez | `pilar.sanchez@ejemplo.test` | `propietario` | Sin asignar |
| Sofía Castro | `sofia.castro@ejemplo.test` | `propietario` | Sin asignar |
| Antonella Vega | `antonella.vega@ejemplo.test` | `propietario` | Sin asignar |
| Gonzalo Torres | `gonzalo.torres@ejemplo.test` | `propietario` | Sin asignar |
| Lucas Silva | `lucas.silva@ejemplo.test` | `propietario` | Sin asignar |
| Sofía Castro | `sofia.castro30@ejemplo.test` | `propietario` | Sin asignar *(email con sufijo — coincidencia de nombre con la de arriba, generado al azar)* |
| Isabella Medina | `isabella.medina@ejemplo.test` | `propietario` | Sin asignar |
| Martina Álvarez | `martina.alvarez@ejemplo.test` | `propietario` | Sin asignar |
| Bautista Herrera | `bautista.herrera@ejemplo.test` | `propietario` | Sin asignar |
| **Renata Medina** | `renata.medina@ejemplo.test` | `inquilino` | **1A de Torre Cierre Fase 1** (misma unidad que Propietario de Prueba — así se puede probar la vista de Inquilino con datos financieros reales, Fase 2) |
| Antonella Torres | `antonella.torres@ejemplo.test` | `inquilino` | Sin asignar |
| Catalina García | `catalina.garcia@ejemplo.test` | `inquilino` | Sin asignar |
| Nicolás Sánchez | `nicolas.sanchez@ejemplo.test` | `inquilino` | Sin asignar |
| Gonzalo Sánchez | `gonzalo.sanchez@ejemplo.test` | `inquilino` | Sin asignar |
| Valentina Silva | `valentina.silva@ejemplo.test` | `inquilino` | Sin asignar |
| Antonella Benítez | `antonella.benitez@ejemplo.test` | `inquilino` | Sin asignar |
| Camila López | `camila.lopez@ejemplo.test` | `inquilino` | Sin asignar |
| Santiago Fernández | `santiago.fernandez@ejemplo.test` | `inquilino` | Sin asignar |
| Máximo González | `maximo.gonzalez@ejemplo.test` | `inquilino` | Sin asignar |
| Santiago Ibáñez | `santiago.ibanez@ejemplo.test` | `inquilino` | Sin asignar |
| Pilar Molina | `pilar.molina@ejemplo.test` | `inquilino` | Sin asignar |
| Camila Sosa | `camila.sosa@ejemplo.test` | `inquilino` | Sin asignar |
| Nicolás Ibáñez | `nicolas.ibanez@ejemplo.test` | `inquilino` | Sin asignar |
| Julieta Domínguez | `julieta.dominguez@ejemplo.test` | `inquilino` | Sin asignar |
| Julieta Vega | `julieta.vega@ejemplo.test` | `inquilino` | Sin asignar |
| Sofía Domínguez | `sofia.dominguez@ejemplo.test` | `inquilino` | Sin asignar |
| Bautista Molina | `bautista.molina@ejemplo.test` | `inquilino` | Sin asignar |
| Benjamín Benítez | `benjamin.benitez@ejemplo.test` | `inquilino` | Sin asignar |
| Ignacio Rojas | `ignacio.rojas@ejemplo.test` | `inquilino` | Sin asignar |

*(Nota de asignación 2026-09-06: Renata Medina se vinculó a mano vía `PATCH /api/edificios/departamentos/54/asignacion` para poder probar la Fase 2 — pestaña Pagos/Mi cuenta — con un Inquilino real, no solo con el Propietario de Prueba.)*

---

## Edificios de prueba y quién los administra

| Id | Nombre | Admin de Consorcio | Con datos financieros reales (Fase 2) |
|---|---|---|---|
| 1 | Torre Central | — (solo Admin General) | No |
| 2 | Torre Playwright | Administrador de Consorcio de Prueba | Solo Caja chica (creada probando la Tarea 16) |
| 3 | Torre Playwright | Administrador de Consorcio de Prueba | Solo Caja chica |
| 4 | Torre Geocodificada | — | No |
| 5 | Torres Independencia 3252 | Administrador de Consorcio de Prueba | No |
| 6 | Edificio Flujo Completo | — | No |
| 7 | **Torre Cierre Fase 1** | — (solo Admin General) | **Sí — el edificio de referencia de toda la Fase 2**: Gastos, 3 Expensas (Ago/Sep/Oct 2026), Pagos en los 3 estados (confirmado/pendiente/rechazado), 12 departamentos en Deudores, Fondos con movimientos, Caja chica configurada, Presupuestos en los 3 estados (pendiente/aprobado/rechazado), Facturas |

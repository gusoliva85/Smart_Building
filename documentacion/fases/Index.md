# Índice de fases — SMART Building

Resumen de lo que **realmente se construyó** en cada fase, actualizado recién cuando una fase se da por terminada. A diferencia de [`03_Roadmap.md`](../03_Roadmap.md) (que es el plan y va marcando tareas sobre la marcha), este documento es la foto final de cada fase ya cerrada — la documentación oficial para presentar. Cada fase completa tiene su propio archivo en esta carpeta, nombrado igual que en el Roadmap (ej. `Fase 02 - Gestión financiera básica.md`).

| Fase | Estado | Resumen |
|---|---|---|
| **Fase 0** — Fundación del proyecto | ✅ Completa | Esqueleto de backend (FastAPI + SQLAlchemy + SQLite) y frontend (HTML/CSS/JS vanilla, sin framework) comunicándose entre sí, con el sistema de diseño `premium-uiux` ya extraído del mockup aprobado. Sin funcionalidad de negocio todavía. *(Sin documento propio por ahora — el detalle completo vive en `03_Roadmap.md`.)* |
| **[Fase 1](<Fase 01 - Usuarios, autenticación y estructura del edificio.md>)** — Usuarios, autenticación y estructura del edificio | ✅ Completa | Login con JWT, matriz de roles (8 roles), CRUD de usuarios, y la estructura real de un edificio (pisos/departamentos/cocheras/espacios comunes) con generación automática al dar de alta. Base de la que depende todo lo demás. |
| **[Fase 2](<Fase 02 - Gestión financiera básica.md>)** — Gestión financiera básica | ✅ Completa | Ciclo financiero completo: gastos → prorrateo por coeficiente (investigado contra la Ley 13.512) → expensa mensual → pago con conciliación manual → deudores calculados. Primera pantalla real para Propietario/Inquilino (`financiero.html`, "Mi cuenta"). Fondos, Caja chica, Presupuestos y Facturas agrupados en una sub-navegación propia. |
| Fase 3 — Reclamos y mantenimiento | ⏳ No iniciada | — |
| Fase 4 — Activos y seguridad normativa | ⏳ No iniciada | — |
| Fase 5 — Dashboard Visual del Edificio (funcionalidad diferencial) | ⏳ No iniciada | — |
| Fase 6 — Dashboard General y Analítica | ⏳ No iniciada | — |
| Fase 7 — Gestión documental y proveedores | ⏳ No iniciada | — |
| Fase 8 — Comunicación interna y reservas de espacios comunes | ⏳ No iniciada | — |
| Fase 9 — Módulo de seguridad | ⏳ No iniciada | — |
| Fase 10 — Inteligencia Artificial | ⏳ No iniciada | — |
| Fase 11 — Configuración avanzada, permisos por excepción y auditoría | ⏳ No iniciada | Ya tiene dos deudas técnicas anotadas esperándola: la excepción de visibilidad financiera de Inquilino, y el vínculo Auditor↔edificio (ver Fase 2). |
| Fase 12 — Pulido de frontend, build de producción y PWA | ⏳ No iniciada | — |
| Fase 13 — Cierre y puesta en producción | ⏳ No iniciada | — |
| Fase X — Solicitud de Facultad | 🔶 En curso, no secuencial | Requisitos técnicos/UX/seguridad pedidos por la cátedra, verificados contra el código real a medida que se acercan — no es una fase de desarrollo de producto. Vive solo en `03_Roadmap.md`, no tiene documento propio en esta carpeta. |

## Cómo actualizar este índice

Cuando una fase se termina y se aprueba: crear su archivo `Fase 0N - <nombre completo tal cual el Roadmap>.md` en esta carpeta, y actualizar la fila correspondiente acá (estado a ✅ Completa, resumen breve, y el link al archivo nuevo). Nunca se documenta una fase a medio terminar.

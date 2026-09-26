# SMART Building

Plataforma de gestión y visualización integral de edificios y consorcios —
centraliza comunicación, administración financiera, mantenimiento, reclamos y
seguridad edilicia, con un dashboard visual que muestra el estado del edificio
de un vistazo.

> **Estado: Fase 0 (Fundación), en curso.** El esqueleto de backend y frontend
> está levantado y comunicándose, con el sistema de diseño aplicado. **Todavía
> no hay ninguna funcionalidad de negocio**: ni login, ni usuarios, ni
> edificios. Eso arranca en la Fase 1.
>
> El avance tarea por tarea vive en
> [`documentacion/05_Roadmap.md`](documentacion/05_Roadmap.md).

> **⚠️ La base de datos de producción sigue viva.** El PostgreSQL de Supabase
> conserva el esquema y los datos del código anterior, que se eliminó en el
> reinicio del 2026-09-25. Antes de desplegar cualquier cosa, leer
> [`04_Infraestructura.md`](documentacion/04_Infraestructura.md): el mecanismo
> de arranque agrega columnas pero **nunca modifica ni borra** las que ya están,
> así que un esquema viejo puede quedar desalineado **en silencio**.

---

## Requisitos

- **Python 3.12** (`python --version`).
- Nada más. No hace falta Node, ni npm, ni ningún gestor de paquetes de
  JavaScript: el frontend es HTML, CSS y JavaScript que se sirven tal como se
  editan, sin paso de compilación.

---

## Cómo se levanta

No hay script de un solo clic, a propósito: son **dos procesos independientes**,
cada uno en su terminal. Si uno se cae, el otro sigue.

### Terminal 1 — Backend

Queda en `http://127.0.0.1:8000`, con la documentación interactiva de la API en
`http://127.0.0.1:8000/docs`.

```bash
cd backend

python -m venv venv              # solo la primera vez
venv\Scripts\activate            # Windows   (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt  # la primera vez, y cuando cambien las dependencias

uvicorn app.main:app --reload
```

### Terminal 2 — Frontend

Queda en `http://127.0.0.1:8090/index.html`.

```bash
cd frontend
python servidor_dev.py           # o: python servidor_dev.py 9000
```

No usa el entorno virtual del backend: le alcanza con la librería estándar.

**Usar siempre `servidor_dev.py` y no `python -m http.server`.** El servidor de
la librería estándar deja que el navegador cachee los archivos, y entonces se
edita un `.css`, se recarga, no cambia nada, y se pierden veinte minutos
buscando un problema que no existe. Este manda `no-store` en cada respuesta.

### Verificar que todo está bien

Abrí `http://127.0.0.1:8090/index.html`. El punto de la barra superior consulta
la API al cargar:

| Indicador | Significa |
|---|---|
| Azul acero, "En línea" | El frontend habla con el backend. Todo en orden. |
| Rojo, "Sin conexión" | El backend no está levantado, o está en otro puerto. Revisá la Terminal 1. |

---

## Pruebas

```bash
cd backend
venv\Scripts\activate
pytest
```

**Antes de dar cualquier tarea por terminada se corre la suite completa, no solo
el archivo que se está escribiendo.** En la iteración anterior, dos regresiones
reales pasaron los tests del archivo nuevo y rompieron archivos ajenos.

---

## Estructura del repositorio

```
backend/
  app/
    core/        configuración, seguridad, dependencias, migraciones
    models/      SQLAlchemy — un archivo por dominio
    schemas/     Pydantic — entrada y salida separadas
    routers/     endpoints HTTP — un router por dominio
    services/    lógica de negocio pura, sin HTTP ni ORM
  tests/
frontend/
  index.html
  assets/{css,js,img}/
  servidor_dev.py
documentacion/
.claude/skills/premium-uiux/   el contrato visual del frontend
```

---

## Documentación

Leer en este orden:

| Documento | Qué contiene |
|---|---|
| [`01_Documento_General.md`](documentacion/01_Documento_General.md) | Producto y negocio: qué problema resuelve, para quién, con qué alcance y con qué reglas. |
| [`02_Documento_Tecnico.md`](documentacion/02_Documento_Tecnico.md) | Arquitectura, stack, modelo de datos, API, reglas de negocio, pruebas, despliegue y trampas conocidas. |
| [`03_Documento_Frontend.md`](documentacion/03_Documento_Frontend.md) | Sistema de diseño e interfaz: tokens, componentes, pantallas, responsive y reglas de interacción. |
| [`04_Infraestructura.md`](documentacion/04_Infraestructura.md) | **⚠️ Leer antes de desplegar.** Los recursos que existen fuera del repositorio y siguen vivos: Supabase, Vercel y las variables de entorno. |
| [`05_Roadmap.md`](documentacion/05_Roadmap.md) | La ejecución, tarea por tarea. Es el documento de trabajo diario. |

Material de apoyo:

- [`entrevistas.md`](documentacion/entrevistas.md) — relevamiento de necesidad con dos inquilinos y un administrador de consorcio.
- [`investigaciones/`](documentacion/investigaciones/) — decisiones con respaldo normativo: prorrateo de expensas, pagos y conciliación, caja chica, presupuestos y facturas.
- [`.claude/skills/premium-uiux/`](.claude/skills/premium-uiux/SKILL.md) — **el contrato visual del frontend.** Se carga antes de tocar cualquier pantalla.
- [`mockups/`](documentacion/mockups/) — exploración visual histórica. **No es el contrato visual.**

---

## Stack

- **Backend:** Python 3.12 + FastAPI + SQLAlchemy 2 + Pydantic v2 + Uvicorn.
- **Base de datos:** SQLite en desarrollo, PostgreSQL (Supabase) en producción.
  No se usa Alembic: el esquema evoluciona de forma aditiva al arrancar.
- **Frontend:** HTML + CSS propio (una hoja de tokens y un catálogo de
  componentes) + JavaScript vanilla, sin framework y **sin build**.
- **Despliegue:** Vercel — backend serverless y frontend estático.

---

## Usuarios de prueba

Se completa a medida que el seed y las pruebas los vayan creando.

| Nombre | Email | Contraseña | Rol |
|---|---|---|---|
| *(ninguno todavía: los crea la Fase 1)* | | | |

Son deliberadamente triviales porque el proyecto está en modo test, y **siempre
se guardan hasheadas** en la base, nunca en texto plano.

> **Anotarlas en el momento de crearlas.** En la iteración anterior quedó un
> usuario de prueba cuya contraseña nunca se documentó y, como no existe
> endpoint de reseteo, ese login quedó inutilizable.

---

## Cómo se trabaja

Una tarea del Roadmap a la vez, en orden **lógica → backend → frontend**. Se
implementa, se explica, el usuario la prueba, y recién con su aprobación
explícita se tilda y se pasa a la siguiente. Nunca se adelantan pantallas ni
endpoints de un módulo cuyo turno no llegó, y ninguna pantalla muestra secciones
vacías de funcionalidad futura.

El detalle completo está en
[`documentacion/05_Roadmap.md`](documentacion/05_Roadmap.md), sección 1.

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

python -m app.seed               # solo la primera vez: crea el administrador inicial

uvicorn app.main:app --reload
```

El seed es **idempotente**: correrlo de nuevo no duplica nada y no le pisa la
contraseña a un usuario que ya exista. Se corre a mano y no al arrancar la
aplicación, a propósito: ese mismo arranque es el de producción, y un seed
automático ahí significa que cada despliegue se asegura de que exista un
administrador con la contraseña que está escrita en este archivo. En producción
la guarda del seed exige `SEED_ADMIN_EMAIL` y `SEED_ADMIN_PASSWORD` por
variables de entorno, y no deja sembrar con las de desarrollo.

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

Hay **uno de cada rol**, los ocho. El primero lo crea el seed; los otros siete
los creé desde la pantalla de usuarios al cerrar `F1-T16`, que es la prueba de
punta a punta de este tema.

| Nombre | Email | Contraseña | Rol |
|---|---|---|---|
| Administrador General | `administrador@test.com` | `Test1234!` | `admin_general` |
| Prueba Administrador de Consorcio | `adminconsorcio@test.com` | `Test1234!` | `admin_consorcio` |
| Prueba Encargado | `encargado@test.com` | `Test1234!` | `encargado` |
| Prueba Propietario | `propietario@test.com` | `Test1234!` | `propietario` |
| Prueba Inquilino | `inquilino@test.com` | `Test1234!` | `inquilino` |
| Prueba Proveedor | `proveedor@test.com` | `Test1234!` | `proveedor` |
| Prueba Auditor | `auditor@test.com` | `Test1234!` | `auditor` |
| Prueba Seguridad | `seguridad@test.com` | `Test1234!` | `seguridad` |

**La misma contraseña para los ocho, a propósito.** Ocho contraseñas distintas
no prueban nada que esta no pruebe, y multiplican por ocho la posibilidad de
que alguna quede mal anotada — que es exactamente el error que dejó una cuenta
inutilizable en la iteración anterior. Cumple la política del sistema: ocho
caracteres, mayúscula, minúscula, número y símbolo.

**Hoy siete de los ocho entran y no ven ninguna pantalla**, y está bien: la
única construida es Usuarios, que es solo del Administrador General. El login
se los dice con palabras en vez de mandarlos a un error. Sirven para
verificar, desde ahora y en cada fase, que cada rol ve únicamente lo que le
toca.

El primero lo crea `python -m app.seed`, y es el único que no puede crear
nadie desde la aplicación: todos los demás los da de alta un Administrador
General.

> **Estos ocho viven solo en la base local.** `smart_building.db` no se
> versiona, así que en una máquina recién clonada hay que correr el seed y dar
> de alta los otros siete a mano. En producción está sembrado únicamente el
> Administrador General.

### Los usuarios que crean las pruebas automáticas

Los arneses de prueba crean usuarios al correr, y **se los distingue por el
dominio del email**: todo lo que crea una prueba usa `@ejemplo.com`, y los
ocho de la tabla de arriba usan `@test.com`. Sin esa convención no hay forma
mecánica de separar lo que hay que conservar de lo que se puede borrar.

Lo aprendí de la forma incómoda: al llegar a `F1-T16` la base de desarrollo
tenía **veinticinco** usuarios dejados por los arneses de `F1-T13`, `F1-T14` y
`F1-T15`, mezclados con el administrador. Ninguno molestaba al correr las
pruebas, pero el listado de la pantalla era ilegible y la verificación de "cada
rol ve lo que le toca" no se podía hacer sobre esa base. Se borran con una
consulta por dominio; no hay endpoint de borrado, y es correcto que no lo haya
— el sistema desactiva, no borra.

**Este mismo usuario existe también en producción**, y es una decisión tomada
a conciencia, no un descuido. Mientras el sistema no tenga un solo dato real
adentro, el despliegue es un entorno de prueba más —el que me deja verificar
cada tarea en el navegador contra la infraestructura de verdad— y usar las
mismas credenciales en los dos lados evita tener dos juegos que mantener.

> **Lo que eso implica, escrito para no olvidarlo.** Estas credenciales están
> en este archivo, que está en un repositorio de GitHub: cualquiera que lo lea
> puede entrar como Administrador General a la URL de producción. Es aceptable
> hoy porque no hay nada que proteger. **Deja de serlo en el momento en que
> entre el primer dato real de un consorcio**, y para entonces hay que: cambiar
> la contraseña de este usuario por una que viva solo en las variables de
> entorno, y sacar esta fila de la tabla. Es parte del cierre de la Fase 13.

Para sembrarlo en producción, apuntando el seed a Supabase desde una terminal
local (los valores por defecto del script ya son los de esta tabla, así que no
hace falta definir nada más):

```powershell
$env:DATABASE_URL = "<cadena del Transaction pooler de Supabase>"
venv\Scripts\python.exe -m app.seed
```

La cadena del pooler se saca de *Settings → Database → Connection string →
Transaction pooler*. Se reconoce por tres cosas: el host termina en
`pooler.supabase.com`, el puerto es `6543`, y el usuario es
`postgres.<proyecto>` y no `postgres` pelado. **Nunca se escribe en un archivo
del repositorio.**

> **Por qué `Test1234!` y no `test1234`.** La quería como `test1234`, y no
> entra: la política de contraseñas del propio sistema exige una mayúscula y un
> carácter especial. Sembrar esa contraseña habría obligado a saltear el
> validador, dejando al primer usuario del sistema con una contraseña que el
> sistema rechaza. La T mayúscula y el signo final son el cambio más chico que
> la hace cumplir, y así el seed valida su propia contraseña antes de hashearla.

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

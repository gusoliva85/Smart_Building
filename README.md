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

- [`Usuarios.md`](documentacion/Usuarios.md) — manual de uso: cómo se crea el Administrador General inicial, cuáles son los nueve roles con su valor exacto, y cómo cambiar un rol o una contraseña a mano en la base.
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

| Nombre | Email | Contraseña | Rol | ¿Lo siembra el script? |
|---|---|---|---|---|
| Administrador General | `administrador@test.com` | `Test1234!` | `admin_general` | Sí, siempre |
| Prueba Encargado | `encargado@test.com` | `Test1234!` | `encargado` | Sí, con `--con-pruebas` |
| Prueba Propietario | `propietario@test.com` | `Test1234!` | `propietario` | Sí, con `--con-pruebas` |
| Prueba Inquilino | `inquilino@test.com` | `Test1234!` | `inquilino` | Sí, con `--con-pruebas` |
| Prueba Administrador de Consorcio | `adminconsorcio@test.com` | `Test1234!` | `admin_consorcio` | No, a mano |
| Prueba Proveedor | `proveedor@test.com` | `Test1234!` | `proveedor` | No, a mano |
| Prueba Auditor | `auditor@test.com` | `Test1234!` | `auditor` | No, a mano |
| Prueba Seguridad | `seguridad@test.com` | `Test1234!` | `seguridad` | No, a mano |

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

### Cómo se crean

Hay **dos formas**, y la segunda entró en `F1-T16B`:

1. **El administrador da de alta a alguien** desde la pantalla de usuarios.
   Define sus datos y su contraseña inicial, y se la comunica él.
2. **La persona se registra sola**, con el botón "Crear una cuenta" del login.
   Carga sus datos y elige su propia contraseña, pero **no elige su rol**: la
   cuenta nace con el rol `pendiente`, que no da acceso a nada. Aparece en un
   bloque arriba del listado de usuarios y el administrador le asigna el rol
   ahí, o rechaza la solicitud — rechazar **desactiva la cuenta, no la borra**.

La segunda existe porque cuarenta unidades son cuarenta altas dictadas por
teléfono y cargadas por alguien que no es el dueño del dato. Así cada uno
carga lo suyo y el administrador solo decide el rol, que es la parte que sí le
corresponde a él.

> **Una cuenta pendiente puede iniciar sesión y no puede nada.** Es
> deliberado: entra y lee que su cuenta está esperando aprobación. Si quedara
> inactiva, el login le diría "email o contraseña incorrectos", que es mentira
> y la manda a pedir ayuda por el problema equivocado.

**El Administrador General es el único que no puede salir de ninguna de las
dos**: es el que aprueba, y al primero no hay quién lo apruebe. Por eso existe
el seed. Los cuatro primeros de la tabla los siembra el script; los otros
cuatro los doy de alta desde la pantalla de usuarios cuando los necesito.

```powershell
cd backend
venv\Scripts\python.exe -m app.seed                  # solo el administrador
venv\Scripts\python.exe -m app.seed --con-pruebas    # y los otros tres
```

**Es idempotente, y eso incluye no pisar contraseñas.** Correrlo dos veces no
duplica nada, y a un usuario que ya existe no le toca nada — ni el hash. Eso
importa: si alguien le cambió la contraseña a uno de estos usuarios, un seed
que la pisara volvería a dejar la del README sin avisar. **La contracara:** si
un usuario existe con una contraseña que no es la de esta tabla, el seed **no
lo arregla**. Lo dice en la salida (`ya existía. No se modificó nada.`), y la
única salida es borrar esa fila desde el panel de la base y volver a sembrar,
porque no hay endpoint de recuperación de contraseña.

> **Por qué los usuarios de prueba van detrás de una bandera y no por
> defecto.** Este mismo script es el que se va a correr el día que haya un
> despliegue con datos reales, y crear ahí en silencio tres cuentas más con una
> contraseña que está publicada en este archivo sería exactamente el problema
> que el seed trata de evitar. Con la bandera, la intención queda escrita en el
> comando y la limpieza de la Fase 13 tiene una sola cosa concreta que buscar.
> Si no se pasa, la salida avisa que la bandera existe.

### Antes de nada: las migraciones a mano

**Hay un paso previo al seed, y se corre una vez por base de datos.** No por
máquina: por base. La de desarrollo de cada clon y la de producción.

```powershell
cd backend
venv\Scripts\python.exe -m app.migraciones_manuales.m001_rol_pendiente
venv\Scripts\python.exe -m app.migraciones_manuales.m002_fk_asignacion_edificio
```

| Migración | Qué arregla |
|---|---|
| `m001_rol_pendiente` | El CHECK de `usuarios.rol` en una base creada antes de que existiera el rol `pendiente`. Sin esto, el registro público devuelve `202` sin crear nada. |
| `m002_fk_asignacion_edificio` | La clave foránea que le faltaba a `asignacion_edificio.edificio_id`. Recrea la tabla, que está vacía, y **se niega a hacerlo si tiene filas**. |

Son idempotentes: si el cambio ya está, lo dicen y no tocan nada, así que
correrlas de más es gratis y no hace falta recordar cuál corrió en qué base.
**Una base recién creada no las necesita** — nace con el esquema correcto —,
pero correrlas igual no cuesta nada y es más barato que averiguar si hacía
falta.

Por qué existen, y vale entenderlo una vez: el esquema se sincroniza al
arrancar la aplicación, pero ese mecanismo es **puramente aditivo** — crea
tablas y columnas que faltan, y nada más. No modifica lo que ya existe, a
propósito, porque es la única forma de que un arranque automático sea seguro
contra una base con datos. La contracara es que un cambio sobre algo que ya
existe —un CHECK nuevo, un tipo distinto— **no se aplica y tampoco da error**:
la aplicación arranca, informa "sin cambios" y trabaja contra una forma que no
es la que declaró.

> **Esto ya me morfió una tarde, así que lo dejo escrito.** El registro
> público de `F1-T16A` devolvía `202 Accepted` **sin crear el usuario** contra
> la base de desarrollo. La tabla `usuarios` de esa base se había creado antes
> de que existiera el rol `pendiente`, así que su CHECK listaba ocho roles y
> rechazaba el INSERT. Los tests no lo veían y no podían: pytest crea las
> tablas desde los modelos actuales, así que su CHECK sí lo incluía. **Un
> esquema declarado y una base real no son lo mismo, y ninguna prueba contra
> una base recién creada va a notar la diferencia.**

El detalle de cada migración y la convención para agregar la siguiente están
en `backend/app/migraciones_manuales/__init__.py`.

### En producción

**Los usuarios son datos, no código: pushear no los crea.** El seed no se
cuelga del arranque de la aplicación a propósito (está explicado en
`backend/app/seed.py`), así que después de desplegar hay que correrlo **una
vez** apuntando a Supabase, desde una terminal local:

```powershell
cd backend
$env:DATABASE_URL = "<cadena del Transaction pooler de Supabase>"
venv\Scripts\python.exe -m app.migraciones_manuales.m001_rol_pendiente
venv\Scripts\python.exe -m app.migraciones_manuales.m002_fk_asignacion_edificio
venv\Scripts\python.exe -m app.seed --con-pruebas
```

**La migración va primero y no es opcional**, porque la base de producción
existe desde antes del rol `pendiente`: sin ese paso, el registro desde el
login va a fallar allá aunque funcione en desarrollo, y la tabla `usuarios` de
Supabase además conserva el esquema de la iteración anterior del proyecto.
Contra una base vacía el seed solo también alcanza.

Abrir una terminal nueva después, o cerrar esa: `$env:DATABASE_URL` queda
definida para toda la sesión, y un `python -m app.seed` posterior pensando que
va a la base local iría a producción sin avisar.

La cadena del pooler se saca de *Settings → Database → Connection string →
Transaction pooler*. Se reconoce por tres cosas: el host termina en
`pooler.supabase.com`, el puerto es `6543`, y el usuario es
`postgres.<proyecto>` y no `postgres` pelado — la conexión directa no sirve
desde un entorno serverless y el backend lo rechaza al arrancar, explicando por
qué. **Nunca se escribe en un archivo del repositorio.**

> **Y una advertencia sobre el resguardo que existe, porque es nominal.** El
> seed tiene una guarda (`_verificar_que_se_puede_sembrar`) que debería impedir
> dejar un administrador de credenciales públicas en producción. **No se activa
> en este caso.** Pregunta por la variable de entorno `VERCEL`, es decir
> "¿estoy corriendo *en* Vercel?", y el seed se corre siempre desde una
> terminal local, también cuando apunta a la base de producción. Para que
> protegiera de verdad tendría que mirar la cadena de conexión, no el entorno
> de ejecución. Queda pendiente arreglarlo; mientras tanto, el único resguardo
> real es que no haya datos de nadie en esa base.

### Los usuarios que crean las pruebas automáticas

Los arneses de prueba crean usuarios al correr, y **se los distingue por el
dominio del email**: todo lo que crea una prueba usa un dominio que **empieza
con `ejemplo.`**, y los ocho de la tabla de arriba usan `@test.com`. Sin esa
convención no hay forma mecánica de separar lo que hay que conservar de lo que
se puede borrar.

> **Por qué "empieza con `ejemplo.`" y no "es `@ejemplo.com`".** Porque hay dos
> grafías en uso y las dos son necesarias: `@ejemplo.com` a secas, y
> `@ejemplo.com.ar` cuando el email pasa por un esquema que lo valida —
> `email-validator` rechaza los dominios de uso reservado, así que no sirve
> cualquiera. La primera versión del limpiador comparaba con `@ejemplo.com`
> exacto y por lo tanto no reconocía los del conftest de pytest. **Dos grafías
> para una sola convención es una convención que no se puede aplicar
> mecánicamente**, que era justamente el punto de tenerla. Ningún email real
> empieza su dominio con `ejemplo.`, así que el prefijo es un criterio seguro.

Lo aprendí de la forma incómoda: al llegar a `F1-T16` la base de desarrollo
tenía **veinticinco** usuarios dejados por los arneses de `F1-T13`, `F1-T14` y
`F1-T15`, mezclados con el administrador. Ninguno molestaba al correr las
pruebas, pero el listado de la pantalla era ilegible y la verificación de "cada
rol ve lo que le toca" no se podía hacer sobre esa base. Se borran con una
consulta por dominio; no hay endpoint de borrado, y es correcto que no lo haya
— el sistema desactiva, no borra.

**Estos usuarios existen también en producción**, y es una decisión tomada
a conciencia, no un descuido. Mientras el sistema no tenga un solo dato real
adentro, el despliegue es un entorno de prueba más —el que me deja verificar
cada tarea en el navegador contra la infraestructura de verdad— y usar las
mismas credenciales en los dos lados evita tener dos juegos que mantener.

> **Lo que eso implica, escrito para no olvidarlo.** Estas credenciales están
> en este archivo, que está en un repositorio de GitHub: cualquiera que lo lea
> puede entrar como Administrador General a la URL de producción. Es aceptable
> hoy porque no hay nada que proteger. **Deja de serlo en el momento en que
> entre el primer dato real de un consorcio**, y para entonces hay que: cambiar
> la contraseña del Administrador General por una que viva solo en las
> variables de entorno, **desactivar los tres usuarios de prueba** y sacar sus
> filas de la tabla. Es parte del cierre de la Fase 13.

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

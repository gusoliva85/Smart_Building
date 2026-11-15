# Infraestructura viva — SMART Building

> # ⚠️ LEER ANTES DE DESPLEGAR CUALQUIER COSA
>
> **Este documento describe infraestructura que EXISTE Y SIGUE VIVA fuera de este repositorio.** No se borró con el reinicio del proyecto del 2026-09-25 y **no debe borrarse sin una decisión explícita**.
>
> **Puesto al día el 2026-11-15** (`F2-T24`). El párrafo que estaba acá decía que la base de
> Supabase conservaba el esquema del código eliminado y que ése era el mayor riesgo del reinicio.
> **Dejó de ser cierto el 2026-09-27**, cuando `F05-T01` vació el esquema `public`, y el documento
> siguió diciéndolo dos meses más. El esquema real está hoy **alineado con los modelos** y lo
> verifiqué leyendo el catálogo de la base — ver sección 3.
>
> **La lección, que es la razón de ser de este archivo:** un documento de infraestructura que no se
> actualiza en la misma tarea que cambia la infraestructura no es una referencia, es una trampa. Una
> afirmación falsa acá es peor que un hueco, porque se actúa sobre ella.

---

## 1. Qué sobrevivió al reinicio y qué no

| Recurso | Estado | Quién lo controla |
|---|---|---|
| **Base de datos PostgreSQL (Supabase)** | 🟢 **VIVA.** Esquema vaciado y recreado desde los modelos nuevos (`F05-T01`), con los datos que se fueron cargando a mano desde entonces | Cuenta de Supabase del dueño del proyecto |
| **Despliegue en Vercel** (backend serverless + frontend estático) | 🟢 **Vivo y vinculado** al repositorio nuevo. Despliega solo en cada push a `main` (verificado el 2026-11-10, ver 2.2) | Cuenta de Vercel del dueño del proyecto |
| **Variables de entorno en Vercel** (secretos, cadena de conexión) | 🟢 Vivas, con sus valores | Panel de Vercel |
| **Repositorio de GitHub** | 🔴 **Eliminado** el 2026-09-25, se recrea vacío | Cuenta de GitHub del dueño |
| **Código del backend y del frontend** | 🔴 Eliminado deliberadamente | — |
| **Base SQLite local** (`backend/smart_building.db`) | 🔴 Eliminada con el backend. Nunca estuvo versionada. | — |

**Esto ya se resolvió, y lo dejo corregido acá porque la versión anterior de este párrafo me hizo dar un diagnóstico equivocado.** Decía que Vercel había quedado conectado al repositorio borrado y que los despliegues automáticos estaban rotos. Era cierto cuando lo escribí y **dejó de serlo** al crear el repositorio nuevo y volver a vincularlo; yo lo seguí repitiendo como si fuera el estado actual. **Comprobado el 2026-11-10**, con pedidos de lectura a la API desplegada: contesta `/api/salud` con la aplicación correcta, y existen las rutas de `F1-T23` (`/espacios-comunes`) y `F1-T24` (`/coeficientes`), que son de esta reimplementación — o sea que lo que está en línea es el código nuevo, al día con el último commit pusheado, y no la versión eliminada.

**La lección, que vale para todo este documento:** un recurso externo cambia de estado sin que el repositorio se entere, así que **el estado se mide antes de afirmarlo**. Cuatro pedidos de lectura a rutas que existen solo en una versión del código dicen exactamente qué está desplegado, y no hacen falta credenciales para eso: una ruta protegida que contesta 401 existe, y una que no existe contesta 404. Cuidado con una trampa al medirlo: `GET /api/edificios/opciones` contesta 401 incluso si esa ruta no existe, porque la captura `/api/edificios/{id}` y la guarda de sesión corre antes de que el id se valide. Hay que elegir rutas que ninguna otra pueda capturar.

---

## 2. Dónde está cada cosa

### 2.1 Base de datos de producción — Supabase

- **Motor:** PostgreSQL gestionado por Supabase.
- **Proyecto:** `tvytsejganribumoyodr`. El panel está en `https://supabase.com/dashboard/project/tvytsejganribumoyodr` y la URL del proyecto es `https://tvytsejganribumoyodr.supabase.co`. La referencia del proyecto no es un secreto —viaja en cada pedido del cliente— pero la contraseña de la base y las claves de servicio **no se escriben acá ni en ningún archivo del repositorio**: viven en el panel de Supabase y en la variable de entorno de Vercel.
- **Región:** `sa-east-1` (San Pablo).
- **Forma de conexión:** **a través del connection pooler de Supabase**, nunca la conexión directa. En un entorno serverless cada invocación abre su propia conexión, y sin pooler se agota el límite de conexiones de la base con muy poco tráfico.
- **Cadena de conexión:** vive **únicamente** en la variable de entorno `DATABASE_URL` del proyecto de Vercel y en el panel de Supabase. **Nunca estuvo en el repositorio y nunca debe estarlo.**
- **Driver:** `psycopg2-binary`, declarado en `requirements.txt`. Se usa solo cuando `DATABASE_URL` apunta a Postgres; en local no interviene.

### 2.2 Despliegue — Vercel

- **Backend:** función serverless de Python. La aplicación se instancia en cada arranque en frío.
- **Proyecto:** `smart-building`, en el equipo `gusoliva85s-projects`. El panel está en `https://vercel.com/gusoliva85s-projects/smart-building`.
- **Dominio del despliegue:** `https://smart-building-livid.vercel.app`. Lo anoto acá porque no estaba escrito en ninguna parte del repositorio, y es justo la clase de dato que este documento existe para no perder.
- **Repositorio conectado:** `github.com/gusoliva85/Smart_Building`, rama `main`. Cada push a `main` dispara un despliegue, así que **lo que no está commiteado y pusheado no está en producción**, por más que ande en local.
- **Región fijada a `gru1`** (San Pablo) mediante `vercel.json` **en la raíz del repositorio** — este documento decía `backend/vercel.json` y el archivo está en la raíz, que es donde Vercel lo busca. Contenido completo:

  ```json
  { "regions": ["gru1"] }
  ```

  **No es cosmético.** Se fijó tras medir en producción un costo fijo de ~500–600 ms por request incluso sin consultas de por medio: backend y base podían estar en continentes distintos. `gru1` se eligió para que coincida con la región `sa-east-1` de Supabase. **Si se cambia la región de la base, hay que cambiar esta también.**
- **Frontend:** estático, desplegado en el mismo proveedor.

### 2.3 Variables de entorno (en Vercel)

| Variable | Para qué | Si falta |
|---|---|---|
| `DATABASE_URL` | Cadena de conexión al Postgres de Supabase (vía pooler) | La aplicación cae a SQLite local, que en serverless **no persiste nada** |
| `JWT_SECRETO` | Secreto de firma de los tokens de sesión | **La aplicación se niega a arrancar** en producción (guarda deliberada: es preferible no desplegar a desplegar inseguro) |
| `CORS_ORIGENES_EXTRA` | Dominios adicionales permitidos, separados por coma (el dominio real del frontend) | El frontend desplegado no puede hablar con la API |
| `VERCEL` | La define Vercel sola; marca que se está en producción | — |

**Regla firme:** ningún secreto entra al repositorio, en ningún archivo, en ningún commit. Los valores por defecto que hay en el código son deliberadamente de desarrollo y la guarda de arranque los rechaza en producción.

---

## 3. El esquema de producción: qué pasó y cómo está hoy

**Verificado el 2026-11-15, leyendo el catálogo de la base real** con seis consultas de solo lectura
(tablas, columnas con su tipo, CHECK, claves foráneas, índices únicos y conteo de filas).

**El esquema coincide con los modelos.** Las **18 tablas** que hay son exactamente las 18 que
declaran los modelos: no quedó ninguna de las 23 que había creado el código eliminado — no están
`reclamos`, `ordenes_trabajo`, `ot_evidencias` ni `documentos`. Están los **36 CHECK** (los
catálogos de rubros, estados y medios de pago, el rol con `pendiente`, los rangos de coeficiente y
de latitud), los **30 índices únicos** que garantizan reglas del negocio —un período una expensa, un
inquilino una sola unidad, una caja por edificio— y **todas las claves foráneas menos una**.

**Por qué quedó así:** `F05-T01` vació el esquema `public` el 2026-09-27 y la aplicación lo recreó
desde los modelos al arrancar. O sea que el riesgo que describía la versión anterior de esta sección
**no se materializó: se eliminó**. Lo que falló fue el documento, que siguió anunciándolo.

**Los datos que hay hoy en producción**, cargados a mano: 1 edificio, 6 pisos, 24 departamentos, 5
usuarios y 1 gasto. Las nueve tablas financieras están creadas y vacías.

### 3.1 Lo que falta, y es una sola cosa

**`asignacion_edificio.edificio_id` no tiene su clave foránea**, porque `m002_fk_asignacion_edificio`
nunca se corrió contra Supabase. Esa columna nació sin FK en `F1-T03` —`edificios` no existía como
modelo todavía— y el modelo ya la declara, pero agregar una restricción a una columna existente no
lo hace el mecanismo de arranque.

Sin la FK la base acepta una asignación que apunta a un edificio inexistente, y eso **no se
manifiesta como un error**: se manifiesta como un auditor que tiene un edificio asignado y no ve
nada. La tabla tiene **0 filas** allá, que es justamente la condición que la migración exige —se
niega a tocarla si hay una sola—, así que se puede correr tal cual. **Está pendiente de ejecución, y
se avisa antes de correrla** (`05_Roadmap.md`, sección 1.5).

**Un punto abierto que es del código y no del despliegue:** `creado_en` está declarado con dos
criterios distintos. Las tres tablas de la Fase 1 usan `timestamp with time zone` con `now()`; las
nueve de la Fase 2, `timestamp` sin zona con `CURRENT_TIMESTAMP`. La base refleja fielmente el
código, así que hoy no rompe nada —ningún cálculo cruza los dos grupos— pero son dos criterios
conviviendo y se unifican en `F13-T01`.

**Y lo que quedó sin verificar:** el editor SQL de Supabase corta el resultado en 100 filas, así que
de la consulta de columnas faltan `pagos`, `pisos`, `presupuestos`, `usuarios` y la cola de
`movimientos_fondo`. Sus CHECK y sus claves foráneas sí se vieron completos y están correctos.

### 3.2 La regla que queda, aunque el riesgo de hoy esté cerrado

Esto se conserva porque **vuelve a aplicar en cada cambio de esquema que venga**, y los dos próximos
ya están identificados: la formalización de `activo_id` en la Fase 4 y la de los cuatro
`proveedor_id` en la Fase 7, las dos sobre columnas que van a tener datos encima.

El proyecto no usa Alembic. El esquema evoluciona con dos mecanismos que corren al arrancar la aplicación, y los dos son **aditivos**:

1. La creación de tablas **solo crea las que no existen**. Si una tabla ya está, no la toca, aunque el modelo nuevo la defina distinta.
2. El agregado de columnas (`core/migraciones.py`) **solo agrega columnas que falten**. Nunca modifica una columna existente, nunca cambia un tipo, nunca agrega ni quita una restricción, nunca borra una columna sobrante.

**Qué puede pasar, entonces, si se despliega el código nuevo contra esta base tal como está:**

| Si en la reimplementación… | Lo que pasa contra la base vieja |
|---|---|
| Una tabla se modela distinto (otra columna, otro tipo) | La tabla vieja queda tal cual, **en silencio**. El código nuevo trabaja contra una forma que no es la que declaró. |
| Se agrega una restricción `CHECK` o una clave foránea | **No se aplica.** La base acepta datos que el modelo cree imposibles. |
| Se renombra o se elimina una columna | La columna vieja **queda ahí para siempre**, ignorada. |
| Se cambia el tipo de una columna | **No cambia.** Puede fallar al leer o escribir, o peor, truncar en silencio. |
| Una columna diferida pasa a ser clave foránea real | **No se crea la restricción.** Ver Documento Técnico, sección 3.5. |

Ninguno de estos casos produce un error al desplegar. Producen comportamiento incorrecto más tarde, difícil de rastrear.

**Y la forma de medirlo ya está escrita.** El diagnóstico de la sección 3 se hizo con seis consultas
de solo lectura sobre `information_schema` y `pg_catalog` —tablas, columnas con tipo y
obligatoriedad, CHECK, claves foráneas, índices únicos y conteo real de filas— que se pueden correr
con la base en uso, sin bloquear nada y sin credenciales en el repositorio: las corre el dueño del
proyecto desde el editor de Supabase y pega el resultado. **Ante cualquier duda sobre si producción
coincide con los modelos, eso es lo que hay que hacer, en vez de suponerlo en una u otra dirección.**

### 3.3 Por qué ya no corresponde vaciar el esquema

Hasta el 2026-11-15 esta sección recomendaba vaciarlo antes de desplegar, y el fundamento era que lo
que había eran datos de prueba descartables. **Las dos mitades de esa recomendación cambiaron:** el
vaciado ya se hizo (`F05-T01`) y lo que hay ahora son datos cargados a mano, edificio por unidad,
que son horas de trabajo y ningún script reconstruye.

**Entonces la regla se invierte: de acá en adelante, una diferencia de esquema se resuelve con una
migración escrita para ese caso, que preserve las filas.** Vaciar dejó de ser la opción barata. Y es
exactamente el momento que anticipa el Documento Técnico (sección 6) para evaluar Alembic: "cuando
haya datos reales que no se puedan perder". Se decide en `F13-T01`.

### 3.4 Punto abierto: el engine y el pooler

El motor de conexión se creaba con la configuración por defecto de SQLAlchemy, sin `pool_pre_ping` ni un pool nulo. Contra un pooler en un entorno serverless eso puede dejar conexiones muertas reutilizadas entre invocaciones (se manifiesta como errores intermitentes de conexión, no como una falla constante). **No llegó a dar problemas en el volumen de prueba, pero está sin resolver.** Al reimplementar la conexión, evaluar `pool_pre_ping=True` y una estrategia de pool acorde a serverless.

---

## 4. Checklist del primer despliegue del proyecto nuevo

1. ~~Crear el repositorio de GitHub vacío y subir el proyecto.~~ **Hecho:** `github.com/gusoliva85/Smart_Building`.
2. ~~**Volver a vincular el proyecto de Vercel al repositorio nuevo.**~~ **Hecho y verificado el 2026-11-10:** despliega solo en cada push a `main`.
3. ~~Verificar que las tres variables de entorno siguen cargadas en Vercel: `DATABASE_URL`, `JWT_SECRETO`, `CORS_ORIGENES_EXTRA`.~~ **Hecho.** Que la API desplegada conteste y que el login funcione prueba las dos primeras; `CORS_ORIGENES_EXTRA` no hace falta mientras el frontend y la API compartan dominio, que es el caso.
4. ~~**Tomar la decisión sobre el esquema de Supabase, y ejecutarla.**~~ **Hecha y ejecutada en `F05-T01`**, y verificada el 2026-11-15 (sección 3). Queda pendiente una sola cosa: correr `m002_fk_asignacion_edificio` (sección 3.1).
5. ~~Confirmar que `vercel.json` fija la región `gru1`.~~ **Hecho.** El archivo está **en la raíz** del repositorio, que es donde Vercel lo busca — este punto decía `backend/vercel.json` y era la misma equivocación que ya corrige la sección 2.2.
6. ~~Desplegar y verificar contra el endpoint de salud de la API.~~ **Hecho y verificado el 2026-11-10** (ver sección 1).
7. ~~Ejecutar el seed y anotar las credenciales generadas en el `README.md`~~ **Hecho.** Están en el README.
8. ~~Confirmar desde el frontend desplegado que puede autenticarse.~~ **Hecho:** es lo que prueba que CORS y el secreto están bien.

**O sea que el checklist del primer despliegue está cerrado**, con la excepción del punto 4. Lo que
queda para la Fase 13 no es desplegar por primera vez: es la revisión final (`F13-T02` a `F13-T07`).

---

## 5. Qué hacer si algo de esto cambia

Este documento es la única memoria de infraestructura del proyecto, porque nada de esto vive en el código. **Si se cambia la región, el proveedor de base, un nombre de variable de entorno, o se agrega un servicio externo, se actualiza acá en la misma tarea.** Un recurso vivo que no está en este documento es un recurso que en algún momento se va a pagar sin saber para qué, o se va a borrar sin saber que hacía falta.

---

*Documentos relacionados: [`02_Documento_Tecnico.md`](02_Documento_Tecnico.md) sección 1.4 (entornos) y sección 6 (evolución del esquema) · [`05_Roadmap.md`](05_Roadmap.md) Fase 13 (puesta en producción).*

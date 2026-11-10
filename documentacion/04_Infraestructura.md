# Infraestructura viva — SMART Building

> # ⚠️ LEER ANTES DE DESPLEGAR CUALQUIER COSA
>
> **Este documento describe infraestructura que EXISTE Y SIGUE VIVA fuera de este repositorio.** No se borró con el reinicio del proyecto del 2026-09-25 y **no debe borrarse sin una decisión explícita**.
>
> En particular: **la base de datos de producción en Supabase sigue existiendo, con el esquema y los datos que creó el código eliminado.** Ese es el punto de mayor riesgo de todo el reinicio, y la sección 3 explica exactamente por qué.

---

## 1. Qué sobrevivió al reinicio y qué no

| Recurso | Estado | Quién lo controla |
|---|---|---|
| **Base de datos PostgreSQL (Supabase)** | 🟢 **VIVA, con esquema y datos** | Cuenta de Supabase del dueño del proyecto |
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

## 3. ⚠️ El riesgo principal: el esquema viejo sigue en la base

**Situación:** la base de Supabase contiene hoy las **23 tablas** que creó el código eliminado, con los datos de prueba que se cargaron en producción.

**Por qué esto es peligroso y no simplemente "ya está creado":** el proyecto no usa Alembic. El esquema evoluciona con dos mecanismos que corren al arrancar la aplicación, y los dos son **aditivos**:

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

### 3.1 La decisión que hay que tomar ANTES del primer despliegue

**Recomendación: vaciar el esquema de Supabase antes de desplegar el código nuevo por primera vez.**

Fundamento: lo que hay ahí son **datos de prueba**, no datos de un cliente real. El costo de perderlos es cero y el costo de arrastrar un esquema desalineado es alto y silencioso. Al arrancar contra una base vacía, el mecanismo de creación deja el esquema exactamente igual a los modelos nuevos, y el seed vuelve a cargar los usuarios de prueba.

**Cómo hacerlo:** desde el editor SQL de Supabase, eliminando el esquema `public` y volviéndolo a crear vacío. Es una operación destructiva e irreversible — **confirmar antes de ejecutarla que no haya nada que se quiera conservar.**

**Si en algún momento se decide NO vaciarla** (por ejemplo, porque ya hay datos reales de un consorcio), entonces cada diferencia entre el modelo nuevo y el esquema existente tiene que resolverse con una migración escrita a mano para ese caso, y **este documento deja de ser suficiente**: ahí corresponde incorporar Alembic, como ya anticipa el Documento Técnico (sección 6).

### 3.2 Punto abierto: el engine y el pooler

El motor de conexión se creaba con la configuración por defecto de SQLAlchemy, sin `pool_pre_ping` ni un pool nulo. Contra un pooler en un entorno serverless eso puede dejar conexiones muertas reutilizadas entre invocaciones (se manifiesta como errores intermitentes de conexión, no como una falla constante). **No llegó a dar problemas en el volumen de prueba, pero está sin resolver.** Al reimplementar la conexión, evaluar `pool_pre_ping=True` y una estrategia de pool acorde a serverless.

---

## 4. Checklist del primer despliegue del proyecto nuevo

1. ~~Crear el repositorio de GitHub vacío y subir el proyecto.~~ **Hecho:** `github.com/gusoliva85/Smart_Building`.
2. ~~**Volver a vincular el proyecto de Vercel al repositorio nuevo.**~~ **Hecho y verificado el 2026-11-10:** despliega solo en cada push a `main`.
3. Verificar que las tres variables de entorno siguen cargadas en Vercel: `DATABASE_URL`, `JWT_SECRETO`, `CORS_ORIGENES_EXTRA`. (Que la API desplegada conteste y que el login funcione ya prueba las dos primeras; `CORS_ORIGENES_EXTRA` no hace falta mientras el frontend y la API compartan dominio, que es el caso.)
4. **Tomar la decisión de la sección 3.1** sobre el esquema de Supabase, y ejecutarla.
5. Confirmar que `backend/vercel.json` fija la región `gru1`.
6. Desplegar y verificar contra el endpoint de salud de la API.
7. Ejecutar el seed y anotar las credenciales generadas en el `README.md` **en ese momento** (ver la advertencia del README).
8. Confirmar desde el frontend desplegado que puede autenticarse: es la prueba de que CORS y el secreto están bien.

---

## 5. Qué hacer si algo de esto cambia

Este documento es la única memoria de infraestructura del proyecto, porque nada de esto vive en el código. **Si se cambia la región, el proveedor de base, un nombre de variable de entorno, o se agrega un servicio externo, se actualiza acá en la misma tarea.** Un recurso vivo que no está en este documento es un recurso que en algún momento se va a pagar sin saber para qué, o se va a borrar sin saber que hacía falta.

---

*Documentos relacionados: [`02_Documento_Tecnico.md`](02_Documento_Tecnico.md) sección 1.4 (entornos) y sección 6 (evolución del esquema) · [`05_Roadmap.md`](05_Roadmap.md) Fase 13 (puesta en producción).*

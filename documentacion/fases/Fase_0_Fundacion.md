# Fase 0 — Fundación del proyecto

> **Cerrada el 2026-09-27.** 19 tareas, todas aprobadas.
>
> Este documento se escribe **una sola vez, al cerrar la fase**, cuando ya nada
> de lo que describe va a cambiar. El Roadmap sigue siendo el único documento
> vivo. Si una fase posterior modifica algo de acá, se agrega una línea al
> final — no se reescribe el cuerpo.

---

## 1. Qué resuelve esta fase

Nada, desde el punto de vista de un administrador de consorcio. Y eso es
deliberado.

La Fase 0 construye **el andamio**: el servidor que va a atender la API, la
conexión a la base, la primera página con la identidad visual definitiva, y el
puente entre las dos mitades. Al terminarla se puede levantar el proyecto en
dos terminales, abrir una pantalla que ya se ve como se va a ver el producto
final, y comprobar que el frontend le habla al backend.

Lo que **no** hay, a propósito: ni login, ni usuarios, ni edificios, ni un solo
dato de negocio. Una pantalla no muestra secciones vacías de funcionalidad
futura, así que la única pantalla que existe no promete nada que no pueda
cumplir.

La analogía es la de una obra: esta fase no levanta ninguna pared, hace el
replanteo y tira los cimientos. Si están torcidos, todo lo que venga después
sale torcido, y por eso se hizo primero y con cuidado.

---

## 2. Qué puede hacer cada rol

**Todavía ninguno.** El sistema de roles nace en la Fase 1 (`F1-T01`), y hasta
que exista el login no hay forma de entrar como nadie.

La única pantalla, `index.html`, es pública y no pide credenciales. Muestra la
marca, el indicador de conexión con la API y un texto que explica en qué estado
está el proyecto.

---

## 3. Recorrido de uso

### 3.1 Levantar el proyecto

Dos procesos independientes, cada uno en su terminal. Si uno se cae, el otro
sigue — que es justamente la razón de no tener un script de un solo clic.

**Terminal 1 — el backend:**

```
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload
```

Al arrancar escribe:

```
Iniciando SMART Building 0.1.0 en modo desarrollo
Esquema: sin cambios, la base ya coincide con los modelos.
Origenes CORS permitidos: http://localhost:8090, http://127.0.0.1:8090, ...
API lista en /api
```

Esas cuatro líneas dicen, en orden: en qué modo arrancó, qué hizo con la base,
quién tiene permiso de hablarle y que ya está atendiendo.

**Terminal 2 — el frontend:**

```
cd frontend
python servidor_dev.py
```

### 3.2 Qué se ve

En `http://127.0.0.1:8090/index.html`:

- La **barra superior** de vidrio, con la marca a la izquierda.
- El **indicador de conexión**, un punto luminoso que consulta la API al cargar.
- Un **panel** con dos párrafos explicando el estado del proyecto.
- El **botón de tema**, que alterna entre claro y oscuro.

El indicador tiene tres estados:

| Cómo se ve | Qué significa |
|---|---|
| Gris, latiendo, "Verificando" | Está preguntando. Dura una fracción de segundo. |
| Azul acero con halo, "En línea" | El frontend habla con el backend. Todo en orden. |
| Rojo sin halo, "Sin conexión" | El backend no está levantado, o está en otro puerto. |

El tercero se puede provocar a mano: cortá el backend con Ctrl+C y recargá. La
página **sigue funcionando**, el tema sigue cambiando, y el mensaje al pasar el
mouse dice exactamente qué pasó: *"No se pudo contactar al servidor. Verifica
que el backend esté levantado."*

### 3.3 Probar la API sin frontend

En `http://127.0.0.1:8000/docs` está la documentación interactiva, que permite
ejecutar cada endpoint desde el navegador. **Es la herramienta con la que se
prueba y se aprueba cada tarea de backend antes de que exista su pantalla**, y
por eso es una pieza del método de trabajo, no un extra.

Hoy tiene un solo endpoint:

```
GET /api/salud

200 OK
{
  "estado": "ok",
  "aplicacion": "SMART Building",
  "version": "0.1.0",
  "entorno": "desarrollo",
  "base_de_datos": "sqlite"
}
```

En producción, el mismo endpoint devuelve **menos**:

```json
{ "estado": "ok", "aplicacion": "SMART Building", "version": "0.1.0" }
```

Es un endpoint público y sin autenticación: no hay razón para contarle a un
visitante anónimo sobre qué motor de base corre el sistema.

---

## 4. Las reglas que quedaron fijadas

No son reglas de negocio —esas empiezan en la Fase 1— pero gobiernan todo lo
que se construya de acá en adelante.

### 4.1 La configuración se lee en un solo lugar

`core/config.py` es el **único** archivo del backend que lee variables de
entorno. Ningún otro módulo llama a `os.getenv`. Si algo necesita un valor de
configuración, lo importa de ahí. Lo mismo del lado del frontend con
`config.js`, que es la única fuente de la URL de la API.

### 4.2 La aplicación se niega a arrancar mal configurada

En producción se verifican tres cosas **antes** de abrir una sola conexión a la
base, y se informan **todas juntas** para no tener que desplegar tres veces:

| Se detecta | Por qué importa |
|---|---|
| El secreto de sesión es el de desarrollo | Cualquiera que lea el código puede firmar un token válido y hacerse pasar por cualquier usuario |
| La base apunta a SQLite | El entorno serverless no tiene disco persistente: **todo lo que se escriba se pierde** al terminar la invocación |
| No hay dominios de CORS declarados | El frontend desplegado no podría hablar con la API |

El criterio de fondo: **es preferible que el despliegue no arranque a que
arranque inseguro sin que nadie lo note.** Un backend caído se ve enseguida;
uno firmando tokens con un secreto público puede pasar meses sin que nadie lo
advierta.

### 4.3 Ninguna pantalla llama a `fetch` directo

Todas pasan por `api.js`, y por eso todas heredan gratis el token de sesión, el
parseo de JSON, el manejo uniforme de errores y la expulsión al login cuando la
sesión caduca.

Un caso concreto de lo que eso resuelve: cuando Pydantic rechaza el cuerpo de
una petición devuelve una **lista** de problemas por campo, no un texto. Sin
tratarlo, el usuario vería `[object Object]`. Con el envoltorio ve:

```
email: value is not a valid email address · password: String should have at least 8 characters
```

### 4.4 El 401 expulsa al login, salvo en el login

Cuando la sesión caduca, el envoltorio la limpia y manda al login. **La
excepción deliberada es el propio login**, donde un 401 significa "credenciales
incorrectas" y hay que mostrarlo en el formulario, no echar al usuario de la
pantalla en la que ya está. Esa pantalla pasa `redirigirEn401: false`.

### 4.5 Todo color sale de un token

Ninguna regla de CSS escribe un color, una sombra o una superficie de vidrio
como valor fijo. Hay exactamente **tres excepciones**, y las tres están
documentadas en el propio código:

| Excepción | Por qué |
|---|---|
| El blanco del texto sobre el acento sólido | No cambia con el tema: es contraste, no color de tema |
| El negro del velo del modal | Tiene que oscurecer lo mismo en ambos temas; si variara, en oscuro no separaría el modal del fondo |
| Los dos colores del favicon | Un favicon se carga fuera del documento y **no puede leer las variables CSS** de la página que lo referencia |

---

## 5. La parte técnica

### 5.1 Qué se construyó

**Backend** (`backend/`, 545 líneas de aplicación + 463 de pruebas):

| Archivo | Qué hace |
|---|---|
| `app/core/config.py` | Variables de entorno, CORS, JWT y la guarda de producción |
| `app/database.py` | Engine, sesión, base declarativa y la dependencia `obtener_db` |
| `app/core/migraciones.py` | Evolución aditiva del esquema al arrancar |
| `app/main.py` | La aplicación, el ciclo de vida y `GET /api/salud` |
| `tests/conftest.py` | El patrón de test de integración que se copia en todo el proyecto |

Las carpetas `models/`, `schemas/`, `routers/` y `services/` existen vacías,
cada una con un docstring que explica la regla que la gobierna. La de
`services/` es la que más importa: **un servicio nunca importa un modelo**,
recibe lo que necesita por *duck typing*.

**Frontend** (`frontend/`, 854 líneas de CSS + 426 de JS):

| Archivo | Qué hace |
|---|---|
| `assets/css/tokens.css` | 37 tokens en tema claro, 28 redefinidos en oscuro. **No dibuja nada**: solo declara variables |
| `assets/css/components.css` | El catálogo: vidrio en dos capas, esqueleto de la zona autenticada, y los componentes transversales |
| `assets/js/config.js` | La URL de la API, decidida por hostname |
| `assets/js/api.js` | El envoltorio único de `fetch` |
| `assets/js/conexion.js` | El indicador de conexión |
| `assets/js/theme.js` | El cambio de tema, con persistencia |
| `servidor_dev.py` | Servidor estático con caché desactivada |
| `index.html` | La única pantalla |

### 5.2 El modelo de datos

**Ninguna tabla todavía.** La primera nace en la Fase 1 con `Usuario`.

### 5.3 Los endpoints

Uno: `GET /api/salud`. El ejemplo completo de petición y respuesta está en la
sección 3.3.

### 5.4 Las pruebas

**23 tests, todos en verde**, en 0,2 segundos.

| Archivo | Tests | Qué cubre |
|---|---|---|
| `test_configuracion.py` | 10 | Arranca sin ninguna variable; ruta absoluta de SQLite; las tres formas de desplegar mal, una por una, y que las informe todas juntas; parseo de CORS; localhost excluido en producción |
| `test_migraciones.py` | 7 | Crea la tabla que falta; es idempotente; agrega columna sin perder datos; omite la obligatoria sin default; conserva e informa una columna sobrante; no vacía una tabla existente |
| `test_salud.py` | 6 | El endpoint responde; informa entorno en desarrollo; 404 en ruta inexistente; CORS permite el frontend local y **rechaza** un origen ajeno |

Las pruebas no tocan la base de desarrollo: se verificó borrándola, corriendo la
suite completa y confirmando que **no se recrea**.

---

## 6. Las decisiones, y por qué

### 6.1 Por qué el frontend no usa framework ni build

Es la decisión más visible de la fase, y se tomó en dos pasos.

**Sin framework de JavaScript**, desde el diseño original: para el tamaño de
este proyecto no aporta, y mantiene la promesa de una arquitectura simple. Cada
dominio de negocio es un `.html` independiente y la navegación es HTML estándar,
sin router.

**Sin framework de CSS**, decidido el 2026-09-27 durante esta fase. El plan
original incluía Tailwind —por CDN al principio, compilado con su binario más
adelante—. Al llegar el momento de agregarlo quedó claro que **no resolvía
ningún problema real**: el sistema visual de este proyecto son clases
compuestas propias (el vidrio en dos capas, el semáforo, el dashboard visual),
de modo que las utilidades de Tailwind no se usarían. Lo único que sumaba era
una dependencia externa y, más adelante, un paso de compilación.

Se descartó. Como consecuencia desapareció la tarea de la Fase 12 que iba a
migrar del CDN al binario, reemplazada por una revisión del peso de las hojas
propias.

**Qué se gana:** los archivos que se editan son exactamente los que se sirven.
No hay compilación, no hay `node_modules`, no hay un CDN de terceros del que
dependa que la aplicación se vea bien. Para levantar el frontend alcanza con
Python, que ya hace falta para el backend.

**Qué se resigna:** no hay utilidades listas para maquetar rápido, así que cada
patrón nuevo se escribe una vez en el catálogo. Es un costo asumido a cambio de
consistencia: es la misma razón por la que existe la regla de "reutilizar,
nunca reinventar".

### 6.2 Qué hace exactamente el mecanismo de migraciones, y qué no

El proyecto **no usa Alembic**. El esquema evoluciona con dos mecanismos que
corren cuando la aplicación arranca, y los dos son **puramente aditivos**:

1. Se crean las tablas que todavía no existen.
2. Se agregan las columnas que un modelo declara y la tabla real no tiene.

Nada más. No modifica, no renombra y no borra. Es la única forma de que un
arranque automático sea seguro contra una base con datos.

**Los límites exactos:**

| Cambio en el modelo | ¿Lo resuelve solo? |
|---|---|
| Columna nueva anulable | **Sí** |
| Columna nueva con valor por defecto | **Sí** |
| Columna obligatoria en una tabla con filas | No — se omite y avisa qué hacer |
| Clave foránea o CHECK sobre una columna existente | No |
| Cambiar el tipo de una columna | No |
| Renombrar o eliminar una columna | No, y se ignora |

Un ejemplo concreto de lo que sí hace. Supongamos una tabla de edificios con
dos filas cargadas y el modelo suma dos campos:

```python
Column("cp", String(10))                                       # anulable
Column("recargo_mora", Integer, server_default="8", nullable=False)
```

Al reiniciar:

```
Esquema: columna agregada edificios.cp
Esquema: columna agregada edificios.recargo_mora
```

Y los datos quedan así — **nada se perdió**:

| id | nombre | cp | recargo_mora |
|---|---|---|---|
| 1 | Torre Belgrano | *(vacío)* | 8 |
| 2 | Edificio Palermo | *(vacío)* | 8 |

Si en cambio el modelo sumara `cuit` como obligatoria y sin valor por defecto,
la columna **no se crea**, porque no hay nada que poner en las filas que ya
existen, y se registra:

```
Esquema: NO se agrego edificios.cuit. Es obligatoria y no tiene valor por
defecto... Resolvelo con una migracion escrita a mano, o declarala anulable.
```

**La consecuencia más importante de todo esto** es la que hay que tener
presente antes del primer despliegue: contra una base cuyo esquema **no**
coincide con los modelos, el mecanismo no corrige la diferencia **y tampoco da
error**. Deja la tabla vieja como está y la aplicación trabaja contra una forma
que no es la que declaró.

Ese es exactamente el riesgo de la base de producción de Supabase, que hoy
conserva el esquema del código eliminado. El mecanismo lo **informa** —lista las
columnas que están en la base y ya no en los modelos— pero solo en el log de
arranque, así que hay que leerlo. La decisión de qué hacer con ese esquema es la
tarea `F13-T01`, y bloquea al resto de esa fase.

### 6.3 Por qué no hay pool de conexiones en producción

Cada invocación serverless es un proceso efímero: un pool local nunca se
reutiliza y solo deja conexiones colgadas que el pooler de Supabase tiene que
reciclar. La aplicación usa `NullPool` en producción y le deja el trabajo de
agrupar a quien corresponde.

Esto cierra un punto que la documentación de infraestructura tenía marcado como
abierto: la configuración por defecto contra un pooler puede reutilizar
conexiones ya muertas entre invocaciones, y eso se manifiesta como errores
**intermitentes** de conexión — no como una falla constante, que sería mucho
más fácil de diagnosticar.

### 6.4 Por qué `autoflush` está desactivado

Con el valor por defecto, SQLAlchemy puede emitir un `INSERT` a mitad de una
función solo porque se hizo una consulta, y entonces un error de validación
posterior deja rastro de algo que nunca se confirmó. Con `autoflush` apagado, el
momento de escribir es siempre explícito. Va a importar mucho en el módulo
financiero.

### 6.5 Decisiones que se descartaron

| Se evaluó | Se descartó porque |
|---|---|
| **Tailwind CSS** | Ver 6.1 |
| **Una librería de configuración tipada** | Su parseo de listas desde el entorno espera JSON (`["https://..."]`), y quien carga la variable en el panel de Vercel escribe una lista separada por comas. Esa diferencia falla al arrancar con un error que no dice que el problema es el formato |
| **El barrido circular del toggle de tema** | Ya se había implementado en la iteración anterior y se revirtió a pedido explícito: bug de `z-index` y lentitud reportada en Chrome. Queda el cross-fade por defecto del navegador |
| **Un script de arranque de un solo clic** | Backend y frontend son dos procesos independientes; si uno se cae, el otro tiene que seguir. El script existió antes y se eliminó |
| **El helper de login en las pruebas** | Se planificó para esta fase, pero no existe todavía el endpoint contra el cual probarlo, y un helper que nadie ejecuta se pudre en silencio. Se construye en `F1-T07` |

---

## 7. Errores encontrados durante la fase

Vale la pena dejarlos registrados: los cuatro aparecieron **porque se verificó**,
no por leer el código dos veces.

| Qué pasó | Cómo se detectó |
|---|---|
| **El favicon no parseaba.** Los nombres de los tokens CSS llevan dos guiones, y dos guiones seguidos son ilegales dentro de un comentario XML: rompían el archivo entero. Los navegadores toleran eso en HTML, pero un SVG es XML estricto | Validando el archivo en vez de darlo por bueno |
| **En Windows, atar un puerto ya ocupado no falla.** `SO_REUSEADDR` se comporta distinto que en Linux: se levantaban dos servidores en el mismo puerto y las peticiones caían en cualquiera al azar — el síntoma habría sido "edito, recargo, y a veces cambia y a veces no" | La prueba de "puerto ocupado" se colgó 20 segundos en vez de fallar |
| **Una clase inventada para una sola pantalla** (`panel-inicio`), que es justo lo que la regla 11 de la skill prohíbe | El chequeo de "toda clase usada está definida en el catálogo" |
| **Una dependencia instalada que nadie importaba** | Al decidir no usarla, se quitó del `requirements.txt` en vez de dejarla |

---

## 8. Deuda asumida

| Deuda | Dónde se salda |
|---|---|
| No hay autenticación: la única pantalla es pública | **Fase 1** (`F1-T07`) |
| El helper de autenticación de las pruebas | **Fase 1** (`F1-T07`) |
| No hay ninguna tabla ni modelo | **Fase 1** (`F1-T03`) |
| Las fuentes se piden a un CDN externo: es la última dependencia de terceros del frontend | **Fase 12** (`F12-T01`), donde se evalúa servirlas desde el propio proyecto |
| El esquema viejo de la base de producción | **Fase 13** (`F13-T01`), y bloquea al resto de esa fase |

---

*Fase siguiente: [Fase 1 — Usuarios, roles y estructura del edificio](../05_Roadmap.md). Empieza por la lógica: la matriz de los 8 roles, antes de escribir una sola tabla.*

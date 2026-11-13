# Fase 1 — Usuarios, roles y estructura del edificio

> **Cerrada el 2026-11-13.** Las 30 tareas aprobadas. La única deuda que quedó
> abierta —ampliar el módulo de usuarios al Administrador de Consorcio— tiene
> tarea propia en la Fase 11 (`F11-T07`), y está en la tabla del final.

---

## 1. Qué resuelve esta fase

La Fase 0 dejó el andamio: un servidor, una base y una pantalla que se veía
bien y no hacía nada. Esta fase construye **la base de datos de la que depende
todo el resto del sistema**, y lo hace en dos mitades que se necesitan
mutuamente.

La primera mitad es **quién entra y qué puede hacer**. Un usuario se identifica
con email y contraseña, recibe una sesión, y a partir de ahí todo lo que el
sistema le deja ver o cambiar sale de su **rol**. Son ocho roles que no
inventé: salieron de las entrevistas con dos inquilinos y un administrador de
consorcio, y cada uno existe porque alguien real hace ese trabajo.

La segunda mitad es **sobre qué**. Un consorcio no es un nombre y una
dirección: es una estructura de pisos, unidades, cocheras y espacios comunes,
y cada unidad tiene un porcentaje —su coeficiente— que determina cuánto paga de
la expensa. Sin esa estructura cargada y sin esos porcentajes sumando 100%
exacto, **no se puede emitir una sola expensa**, así que toda la Fase 2 se
apoya en lo que quedó acá.

Al terminarla, un administrador puede entrar al sistema, dar de alta a las
personas del consorcio o aprobar a las que se registraron solas, cargar un
edificio con su estructura completa, asignarle responsables, decir cómo y
cuándo se cobra, y dejar los coeficientes en 100,000% exacto. Nada de eso
muestra plata todavía: lo financiero es la fase siguiente, y esta fase es la
que hace que la plata se pueda repartir bien.

---

## 2. Qué puede hacer cada rol

Los ocho roles del negocio, más el estado interno `pendiente`. Esta tabla es la
matriz de `services/autorizacion.py` leída en castellano.

| Rol | Alcance | Ve lo financiero de la unidad | Ve lo financiero del edificio | Escribe | Qué puede hacer hoy, con lo construido |
|---|---|---|---|---|---|
| **Administrador General** | La cartera completa | — | Sí | Sí | Todo: usuarios, alta de edificios, estructura, responsables, configuración y coeficientes. Es el único que crea edificios y el único que decide quién los administra. |
| **Administrador de Consorcio** | Los edificios que administra | — | Sí | Sí | Ve y configura **sus** edificios: estructura, cobranza, roles habilitados, coeficientes. No crea edificios ni cambia responsables. |
| **Encargado** | Su edificio | — | No (solo el semáforo, sin montos) | Sí | Entra y ve los espacios comunes de su edificio. Su pantalla propia llega con los reclamos (Fase 3). |
| **Propietario** | Su o sus unidades | Sí | No | Sí | Entra y ve los espacios comunes del edificio donde tiene unidad. Su cuenta y sus expensas llegan en la Fase 2. |
| **Inquilino** | Su unidad | Sí | No | Sí | Lo mismo que el propietario. Un inquilino tiene **una sola** unidad, y el sistema lo impide explícitamente. |
| **Proveedor / Técnico** | Las órdenes de trabajo que tiene asignadas | — | No | Sí | Entra y no alcanza ningún edificio: su vínculo nace de una orden de trabajo, que es Fase 5. |
| **Auditor** | Los edificios que le asignen | Sí | Sí | **No** | Entra y ve lo que se le asignó. Es el único rol de solo lectura, y eso lo aplica una dependencia propia y no una lista de roles. |
| **Personal de seguridad** | Su edificio | — | No | Sí | Entra y ve los espacios comunes del edificio que tiene asignado. |
| `pendiente` | **Ninguno** | No | No | No | Inicia sesión y lee que su cuenta espera aprobación. No alcanza ninguna pantalla. |

**Hoy seis de los ocho roles entran y no ven ninguna pantalla**, y está bien: las
dos construidas son Usuarios (solo Administrador General) y Edificios (los dos
administradores). El login no los manda a un error — les muestra una tarjeta que
explica que entraron bien y que todavía no hay nada para su rol.

> **`pendiente` no es un rol, es un estado de espera.** Lo escribe el sistema
> cuando alguien se registra solo, y lo que hace es dejar la cuenta **inerte**:
> entra, lee su situación, y no alcanza nada porque ninguna pantalla lo tiene en
> su lista de roles habilitados. Eso es lo que hace que tener el registro
> abierto no sea un problema de seguridad: lo peor que consigue un abuso es
> crear filas que no pueden nada.

---

## 3. Recorrido de uso

El recorrido completo, tal como lo hice para cerrar la fase.

### 3.1 El primer usuario

Todos los usuarios los da de alta un Administrador General, y al primero no lo
puede dar de alta nadie. Lo siembra un script, una sola vez por base de datos:

```powershell
cd backend
venv\Scripts\python.exe -m app.seed                  # solo el administrador
venv\Scripts\python.exe -m app.seed --con-pruebas    # y tres usuarios de prueba
```

En producción el script **se niega a sembrar** si no se le dan credenciales
propias por variable de entorno: sin eso usaría las que están publicadas en el
README. El detalle de uso está en [`../Usuarios.md`](../Usuarios.md).

### 3.2 Entrar y cargar las personas

Se entra con email y contraseña. Un Administrador General ve **Usuarios** en el
menú, da de alta a cada persona con su rol y su contraseña inicial, o aprueba a
las que se registraron solas desde el botón "Crear una cuenta" del login — esas
aparecen en un bloque arriba del listado, con la fecha en que se registraron y
dos acciones: Aprobar (abre el formulario con el rol a elegir) y Rechazar.

Rechazar **desactiva, no borra**. Y nadie puede desactivarse a sí mismo ni
bajarse el rol: las dos cosas dejan una cuenta sin forma de volver a entrar.

### 3.3 Dar de alta el edificio

En **Edificios**, "Nuevo edificio" pide nombre, dirección, código postal, CUIT
opcional, y los dos números del tamaño: cuántos pisos y cuántas unidades por
piso. Al salir del campo de dirección, el formulario busca la ubicación y
muestra el pin en un mapa; si no la encuentra **avisa y deja guardar igual**,
porque una calle nueva puede no estar indexada y eso no es motivo para no poder
cargar un edificio que existe.

Al guardar, el sistema crea el edificio **y toda su estructura en la misma
transacción**: 7 pisos por 4 unidades son 36 filas y un solo commit.

### 3.4 Completar y corregir

El botón "Abrir" de cada fila lleva al detalle, con tres pestañas:

- **Datos** — identidad y ubicación en el mapa, los dos responsables y el
  contacto de emergencia.
- **Estructura** — los pisos con sus unidades anidadas, las cocheras y los
  espacios comunes, con agregar, editar y borrar; la superficie, el propietario
  y el inquilino de cada unidad; y los coeficientes.
- **Configuración** — día de vencimiento, recargo por mora, CBU y alias con
  botón de copiar, y qué roles tienen sentido en ese edificio.

### 3.5 Los coeficientes

Es el paso que más importa y el que en la iteración anterior no existía. Se
cargan de tres maneras, y la pantalla muestra siempre la suma:

1. **A mano, unidad por unidad** — la que refleja el reglamento del consorcio.
2. **Con un reparto automático** — en partes iguales, o por metro cuadrado (este
   último necesita las superficies cargadas).
3. **Cargando algunas a mano y completando el resto** — reparte lo que falta
   para llegar a 100% entre las que quedaron en blanco, y no toca ninguna de las
   cargadas.

Cuando suman 100,000% exacto, la pill del título se pone verde y dice que el
edificio está listo para generar expensas. Mientras no, dice cuánto suman y
cuáles faltan.

---

## 4. Las reglas de negocio que quedaron fijadas

### 4.1 El reparto de coeficientes: el caso de las 28 unidades

Es el ejemplo numérico que pide la estructura de este documento, y es también
el error concreto que esta fase vino a corregir. **En la iteración anterior, un
edificio de 28 unidades repartido en partes iguales sumaba 99,989%.**

La cuenta: 100 ÷ 28 = 3,571428…, que con tres decimales —los que guarda la
columna— es **3,571**. Veintiocho veces 3,571 son **99,988**. Faltan 12 pasos
de 0,001.

| Cómo se reparte | Resultado |
|---|---|
| Redondeando cada parte por separado | 99,988% — faltan 12 milésimas y nadie las ve |
| Cargando el sobrante a la última unidad | 100,000%, pero esa unidad queda en 3,583 y paga esa diferencia **todos los meses** |
| **Lo que hace el sistema** | 100,000% exacto, con **12 unidades en 3,572** y las otras 16 en 3,571 |

La diferencia máxima entre dos vecinos es un paso de 0,001 y la suma cierra por
construcción. El método es el del **resto mayor** —el mismo con el que se
reparten escaños por cantidad de votos— y las cuentas intermedias se hacen con
fracciones exactas, no con decimales redondeados: 100/28 no termina nunca, y
cualquier redondeo intermedio es justo el error que había que no cometer.

Verificado contra el servidor real y fijado con tests: los valores distintos son
exactamente `3.571` y `3.572`, las que llevan el paso de más son **12**, y la
última unidad queda en 3,571 y no se come el resto.

El mismo criterio con el reparto por metro cuadrado: en un edificio de 28
unidades con superficies de 40 a 70 m², la de 70 m² paga **4,546%** y la de 40
m² paga **2,597%**, sumando 100,000% exacto.

### 4.2 Las demás reglas que quedaron escritas

- **Los decimales se rechazan, no se redondean.** Un coeficiente con cuatro
  decimales, un recargo por mora con tres o una superficie con tres devuelven un
  error. Guardarlos redondeados en silencio significa que el valor que se cobra
  no es el que alguien puso.
- **Un edificio sin coeficientes completos no puede liquidar**, y la pantalla lo
  dice mientras se carga, no tres fases después.
- **La suma no se bloquea mientras se carga, se informa.** Con un coeficiente
  cargado el edificio suma 3,5 y eso tiene que poder existir: rechazarlo
  obligaría a cargar las 28 unidades en un solo pedido.
- **Los coeficientes del reglamento no se pisan sin confirmación.** Un reparto
  automático sobre un edificio que ya tiene coeficientes cargados pide confirmar
  primero: esos valores salen del reglamento de propiedad horizontal, no se
  calculan, se copian.
- **Un inquilino tiene una sola unidad.** Asignarlo a una segunda lo rechaza
  nombrando dónde ya figura.
- **Un residente solo se puede asignar si su rol está habilitado en ese
  edificio.** Es lo que le da efecto a la lista de roles habilitados.
- **Desvincular funciona siempre**, incluso con el rol deshabilitado: si no,
  deshabilitar un rol dejaría a esas personas pegadas a sus unidades para
  siempre.
- **Un piso con unidades, una unidad con residente y una unidad con cocheras no
  se borran.** El sistema explica qué hay que desvincular primero en vez de
  borrar en cadena.
- **Una cochera rotativa no se asigna a una unidad.** Rotativa significa
  justamente que no es de nadie en particular.
- **La baja de un usuario es siempre lógica.** Un usuario borrado se lleva la
  trazabilidad de todo lo que cargó, y esos registros tienen que seguir diciendo
  quién los creó años después.
- **Nadie se desactiva ni se baja el rol a sí mismo.** Las dos cosas dejan una
  cuenta sin forma de volver a entrar y hacen falta otro administrador —o una
  reparación a mano— para salir.
- **El login no revela si un email está registrado.** "Ese email no existe" y
  "esa contraseña es incorrecta" son la misma respuesta, byte por byte, y el
  tiempo de respuesta está igualado a propósito.

---

## 5. La parte técnica

### 5.1 Los modelos

| Tabla | Campos |
|---|---|
| `usuarios` | `id`, `nombre`, `email` (único), `password_hash`, `rol` (con CHECK de los 9 valores), `telefono`, `activo`, `creado_en` |
| `edificios` | `id`, `nombre`, `direccion`, `cp`, `latitud`, `longitud` (`Numeric(9,6)`, anulables), `cuit`, `admin_consorcio_id`, `encargado_id`, `dias_vencimiento_expensas`, `recargo_mora_porcentual` (`Numeric(5,2)`), `contacto_emergencia_nombre`, `contacto_emergencia_telefono`, `roles_habilitados` (JSON), `cbu`, `alias_cbu`, `activo`, `creado_en` |
| `pisos` | `id`, `edificio_id`, `numero`, `orden` |
| `departamentos` | `id`, `piso_id`, `identificador`, `m2` (`Numeric(8,2)`), `propietario_id`, `inquilino_id`, `coeficiente` (`Numeric(6,3)`) |
| `cocheras` | `id`, `edificio_id`, `numero` (texto), `tipo`, `departamento_id` |
| `espacios_comunes` | `id`, `edificio_id`, `nombre`, `capacidad`, `reglas_uso` |
| `asignacion_edificio` | `id`, `usuario_id`, `edificio_id`, `creado_en` |

**Ningún monto ni porcentaje es `Float`.** Son `Numeric` con sus decimales
declarados, porque 0,1 no existe en binario y un porcentaje que se guarda
"casi" es un porcentaje que no suma 100.

**`numero` y `orden` del piso son dos campos distintos a propósito.** El nombre
de un piso y su lugar en la pila no siempre coinciden: hay edificios con
entrepiso y edificios que saltean el 13.

### 5.2 Los endpoints

**33 endpoints bajo `/api`.** Autenticación y usuarios:

```
POST   /api/auth/login              GET  /api/auth/me
POST   /api/auth/registro           GET  /api/auth/politica-password
GET    /api/usuarios                POST /api/usuarios
GET    /api/usuarios/opciones       GET  /api/usuarios/{id}
PATCH  /api/usuarios/{id}           POST /api/usuarios/{id}/estado
```

Edificios, estructura y coeficientes:

```
POST   /api/edificios                                   GET    /api/edificios
GET    /api/edificios/opciones                          GET    /api/edificios/{id}
PATCH  /api/edificios/{id}                              GET    /api/edificios/{id}/asignables
POST   /api/edificios/{id}/pisos                        PATCH  /api/edificios/{id}/pisos/{pid}
DELETE /api/edificios/{id}/pisos/{pid}                  POST   /api/edificios/{id}/pisos/{pid}/departamentos
PATCH  /api/edificios/{id}/departamentos/{did}          DELETE /api/edificios/{id}/departamentos/{did}
POST   /api/edificios/{id}/cocheras                     PATCH  /api/edificios/{id}/cocheras/{cid}
DELETE /api/edificios/{id}/cocheras/{cid}               GET    /api/edificios/{id}/espacios-comunes
POST   /api/edificios/{id}/espacios-comunes             PATCH  /api/edificios/{id}/espacios-comunes/{eid}
DELETE /api/edificios/{id}/espacios-comunes/{eid}       GET    /api/edificios/{id}/coeficientes
PATCH  /api/edificios/{id}/departamentos/{did}/coeficiente
POST   /api/edificios/{id}/coeficientes/aplicar-atajo
```

Un ejemplo real, el alta de un edificio de 3 pisos por 2 unidades:

```jsonc
// POST /api/edificios
{ "nombre": "Consorcio Mitre 500", "direccion": "Mitre 500", "cp": "C1000",
  "cuit": null, "latitud": -34.603700, "longitud": -58.381600,
  "cantidad_pisos": 3, "unidades_por_piso": 2 }

// 201 Created
{ "edificio": { "id": 7, "nombre": "Consorcio Mitre 500", "direccion": "Mitre 500",
                "cp": "C1000", "cuit": null, "latitud": "-34.603700",
                "longitud": "-58.381600", "admin_consorcio_id": null,
                "encargado_id": null, "dias_vencimiento_expensas": 10,
                "recargo_mora_porcentual": "0.00", "roles_habilitados": [...],
                "cbu": null, "alias_cbu": null, "activo": true,
                "creado_en": "2026-11-12T21:04:11" },
  "pisos": [ { "id": 19, "numero": 1, "orden": 1, "unidades": ["1A", "1B"] }, ... ],
  "cantidad_pisos": 3, "cantidad_departamentos": 6,
  "mensaje": "Se creó el edificio con 3 pisos y 6 unidades. Las unidades quedaron sin superficie, sin propietario y sin coeficiente: eso se completa después." }
```

Y el estado de los coeficientes, que es la respuesta de los tres endpoints del
módulo:

```jsonc
// GET /api/edificios/7/coeficientes
{ "suma": "99.500", "suma_cien": false, "cantidad_unidades": 6,
  "unidades_sin_coeficiente": 0,
  "unidades": [ { "id": 31, "identificador": "1A", "piso_numero": 1,
                  "m2": "62.50", "coeficiente": "16.083" }, ... ],
  "mensaje": "Los coeficientes suman 99.500%. Tienen que sumar exactamente 100% para poder generar una expensa." }
```

**Dos propiedades de los listados que se construyeron desde el principio y no
se optimizaron después:** el listado de edificios es **una sola consulta** haya
1 edificio o 300 —los dos conteos los calcula la base con subconsultas
correlacionadas— y el detalle son **cinco consultas fijas** sin importar
cuántos pisos tenga. Las dos están fijadas por tests que **cuentan las
consultas SQL**, y el contador se prueba a sí mismo provocando un N+1 real.

### 5.3 Los servicios y sus funciones puras

Toda regla no trivial se escribió y se probó como función pura antes de modelar
la tabla que la usa. Un servicio **nunca importa un modelo**.

| Servicio | Funciones |
|---|---|
| `services/autorizacion.py` | La matriz de los 9 roles: `obtener`, `etiqueta`, `alcance`, `es_solo_lectura`, `es_rol_valido`, `es_asignable`. Es la fuente única de los permisos, y el CHECK de la columna `rol` se arma desde esa misma tupla. |
| `services/finanzas.py` | `generar_estructura`, `contar_unidades`, `calcular_partes_iguales`, `calcular_por_metros_cuadrados`, `resto_por_repartir`, `completar_el_resto`, `validar_coeficientes`, y los topes de la generación automática. |
| `core/security.py` | Hash y verificación de contraseña, política de contraseña (`validar_password`, `requisitos_faltantes`, `textos_de_requisitos`), y el ciclo del token (`crear_token_de_acceso`, `decodificar_token`). |
| `core/alcance.py` | La otra mitad de la autorización: `limitar_a_los_que_administra` (el WHERE de los listados) y `puede_ver` (si una persona tiene algo que hacer en un edificio). |
| `core/errores.py` | El catálogo único de mensajes de error: 44 entradas, la excepción que se levanta por código y los tres manejadores. |

### 5.4 Los tests

**La suite pasó de 27 tests al cierre de la Fase 0 a 876**, en 24 archivos. No
hay tests de CRUD trivial: se testeó toda la lógica de servicio, toda regla de
autorización, todo cálculo y todo lo que ya había fallado alguna vez.

Los que más valor dieron, por si sirve de criterio para las fases que vienen:

- **Los que cuentan consultas SQL.** Fijan que el listado no vuelva a disparar
  un N+1 — el error que en la iteración anterior hacía 29 consultas para 7
  edificios.
- **Los parametrizados por rol.** No prueban "un rol prohibido" sino **los
  ocho**: una lista mal escrita puede dejar pasar justo al que nadie probó.
- **Los que verifican las dos mitades de una frase.** Que el encargado, el
  propietario, el inquilino y el agente de seguridad **vean** los espacios
  comunes, y que ninguno de los cuatro pueda **crear** uno.
- **Los que prueban que dos respuestas son idénticas.** El email inexistente y
  la contraseña incorrecta en el login, comparados campo por campo.
- **El que recorre el catálogo de errores** buscando nombres de tabla, de
  columna, de archivo e ids internos.

---

## 6. Decisiones tomadas, incluidas las que descarté

### 6.1 Cómo se resuelve el alcance de un usuario sobre un edificio (`F1-T02`)

Es la decisión más importante de la fase. La pregunta era: ¿cómo sabe el
sistema a qué edificios llega cada persona?

**Las dos opciones que había planteado al principio, y por qué descarté las
dos:** una tabla puente genérica `usuario_edificio` para los ocho roles, o una
columna `edificio_id` en el usuario. Las dos fallaban por el mismo lado:
**tratan a los ocho roles como si su vínculo con el edificio fuera de la misma
naturaleza, y no lo es.**

Hay tres naturalezas distintas, y cada una tiene un solo lugar correcto:

| Naturaleza del vínculo | Roles | Dónde vive |
|---|---|---|
| Derivado de un dato que ya existe | propietario, inquilino, proveedor | La unidad, la orden de trabajo |
| Responsabilidad única (1:1) | admin\_consorcio, encargado | Dos columnas en `edificios` |
| Asignación N:M | seguridad, auditor | La tabla `asignacion_edificio` |
| Sin vínculo: toda la cartera | admin\_general | — |

**Por qué la tabla puente genérica estaba mal:** el vínculo real de un
propietario **es su unidad**. Guardar además una fila que diga "alcanza el
edificio X" crea dos fuentes del mismo hecho, y en algún momento divergen —
asignar una unidad y olvidar la fila deja a esa persona con departamento y sin
acceso, sin que nada avise.

**Por qué la columna en el usuario estaba mal:** un edificio tiene un solo
administrador y un solo encargado, pero puede tener **varios** agentes de
seguridad (turnos), y un auditor puede auditar **varios** edificios. Eso no
entra en una columna.

Así que `asignacion_edificio` existe **solo** para los dos roles N:M, y eso es
deliberado.

La consecuencia práctica llegó en `F1-T23`: la pregunta "qué puede hacer un
rol" y la pregunta "sobre qué edificios" son **dos preguntas distintas** y
viven en dos archivos distintos. La matriz (`services/autorizacion.py`) es
lógica pura y no sabe que existe una base de datos; el alcance
(`core/alcance.py`) no se puede responder sin consultar.

### 6.2 Las otras decisiones

- **Los roles no son una tabla, y no deberían serlo.** Acá un rol no es un
  dato, es comportamiento: insertar una fila en una tabla `roles` no crearía
  ningún permiso, porque qué alcanza cada rol está en la matriz y en las
  dependencias. Quedaría una tabla donde se puede crear el rol "contador" y un
  sistema donde "contador" no puede nada, sin ningún error que lo avise. El
  catálogo de los 9 valores sí está en la base, como CHECK, y se genera desde la
  misma tupla que usa la aplicación.
- **El registro propio existe, pero no elige rol.** Cuarenta unidades son
  cuarenta altas dictadas por teléfono y cargadas por alguien que no es el dueño
  del dato. Con el registro, cada uno carga lo suyo y el administrador solo
  decide el rol. El esquema **no tiene** el campo `rol` y lo rechaza si llega:
  si ese campo entrara, cualquiera en internet se daría de alta como
  Administrador General.
- **Una cuenta pendiente queda activa, no inactiva.** Si quedara inactiva, el
  login le diría "email o contraseña incorrectos", que es mentira y la manda a
  pedir ayuda por el problema equivocado.
- **El coeficiente no entra por el PATCH de la unidad** (devuelve 422). Separado,
  el permiso y la validación se leen de un vistazo, y corregir una superficie no
  puede tocar un coeficiente por accidente.
- **Las unidades nacen sin coeficiente, no con un reparto automático.** Un
  edificio recién creado se vería listo para liquidar con porcentajes que nadie
  confirmó. Un dato ausente lo encuentra la validación; uno inventado no se
  descubre nunca.
- **El 409 es el mecanismo de confirmación de todo el sistema**, y en esta fase
  tiene un solo uso legítimo: pisar coeficientes ya cargados. El envoltorio de
  `fetch` lo convierte en un diálogo de "¿seguro?", y es la razón por la que el
  proyecto no usa un `confirm()` del navegador en ningún lado.
- **Las dos vistas de edificios viven en el mismo archivo** y la URL decide
  cuál: con `?id=7` el detalle, sin nada el listado. Así F5 no saca del edificio
  en el que se estaba, el botón de atrás vuelve al listado y el enlace de un
  edificio se puede mandar por mensaje.
- **Geocodificar nunca bloquea un alta.** Una dirección que no se encuentra, un
  servicio que no contesta o un CDN que no carga son todos el mismo resultado:
  no hay coordenadas, y el edificio se guarda igual.
- **Dos errores de contraste que estaban en producción se arreglaron al revisar
  la paleta:** el color de los labels medía 3,68:1 (por debajo del mínimo) y el
  botón primario en tema oscuro medía 2,27:1, porque tenía el texto en blanco
  fijo "por contraste sobre el acento sólido" — cierto en claro, falso en
  oscuro. La regla que quedó: un color que se escribe fijo porque "no depende
  del tema" se mide en los dos temas antes de afirmarlo.

---

## 7. Deuda asumida y qué fase la salda

| Deuda | Por qué se asumió | Quién la salda |
|---|---|---|
| **El módulo de usuarios sigue siendo solo del Administrador General.** Un Administrador de Consorcio no puede dar de alta ni editar a las personas de su edificio. | Cuando se construyó (`F1-T09`) el alcance no existía, y la elección real era dejarlo solo para el General o dárselo al de Consorcio **sin poder limitarlo** — que no es un filtro parcial, es que vea y edite los usuarios de todos los consorcios de la plataforma, incluidos los administradores de los otros. Entre un permiso que falta y un permiso de más, falta. | **`F11-T07`**, creada el 2026-11-12 al cerrar esta fase. Va en la Fase 11 y no acá porque necesita una regla que es de esa fase: **nadie puede crear ni asignar un rol de más permisos que el propio.** Sin esa regla, darle el alta al Administrador de Consorcio es darle la forma de hacerse Administrador General, así que las dos cosas van juntas o no van. El alcance que hacía falta ya está hecho (`core/alcance.py`, `F1-T23`). |
| **No hay recuperación de contraseña.** Si alguien olvida la suya, hay que escribirle el hash a mano en la base. | Hace falta enviar correo, y el sistema todavía no manda ninguno. | Pendiente de planificar. Está anotado en [`../Usuarios.md`](../Usuarios.md) con el comando para resolverlo a mano. |
| **No se editan los datos de identidad de un edificio** (nombre, dirección, CP, CUIT). | `PATCH /api/edificios/{id}` es de configuración; el endpoint de edición no existe. Si un nombre se carga mal, hoy se corrige en la base. | Sin tarea asignada. Es una tarea chica y la agrego cuando se pida. |
| **El alcance del Auditor no está cerrado.** Se decidió el mecanismo (`asignacion_edificio`) pero no hay pantalla para asignarle edificios. | Darle acceso a toda la cartera sin un vínculo real sería un sobre-permiso. | `F11-T05`, que además tiene que volver sobre las dependencias del módulo financiero. |
| **El Proveedor no alcanza ningún edificio.** | Su vínculo nace de una orden de trabajo, que no existe todavía. | Fase 5. |
| **Los topes de la estructura no se publican al frontend** (20 pisos, 10 unidades por piso). | Escribirlos en la pantalla sería tener el mismo número en dos lugares. Hoy un valor fuera de rango lo rechaza el backend con un mensaje que dice el tope. | Un `GET /api/edificios/opciones` ya existe y puede publicarlos cuando haga falta. |
| **`GET /api/edificios/{id}/asignables` le muestra a un Administrador de Consorcio el nombre y el email de todos los propietarios e inquilinos activos del sistema**, no solo de su edificio. | La misma persona puede ser propietaria en dos consorcios, y filtrar por edificio haría imposible asignarle su unidad en el segundo. | Si llega a molestar, se acota haciendo que el endpoint busque por email en vez de listar. Decisión abierta. |
| **La estructura del edificio se muestra en lista, no gráfica.** | La versión gráfica coloreada es el diferencial del producto y se hace completa, no a medias. | Fase 5, el Dashboard Visual. |
| **El esquema de producción conserva tablas del código anterior.** | La sincronización de esquema es aditiva: no corrige una tabla que ya existe con otra forma. | `F13-T01`. Antes de desplegar hay que leer [`../04_Infraestructura.md`](../04_Infraestructura.md) sección 3. |

---

*Documentos relacionados: [`../01_Documento_General.md`](../01_Documento_General.md) (producto y negocio) · [`../02_Documento_Tecnico.md`](../02_Documento_Tecnico.md) secciones 3 y 4 (modelo de datos, autenticación y permisos) · [`../03_Documento_Frontend.md`](../03_Documento_Frontend.md) (las dos pantallas construidas) · [`../Usuarios.md`](../Usuarios.md) (manual de uso de usuarios y roles) · [`../05_Roadmap.md`](../05_Roadmap.md) (las 30 tareas de esta fase, una por una).*

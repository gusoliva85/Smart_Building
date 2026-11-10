# Usuarios y roles

Este archivo existe para que no tenga que volver a preguntar dos cosas: **cómo nace el primer usuario del sistema** y **cuáles son los roles que existen**, con sus nombres exactos, para poder asignarlos a mano en la base cuando lo necesite.

No es documentación de diseño: el porqué de cada decisión está en [`02_Documento_Tecnico.md`](02_Documento_Tecnico.md) sección 4. Esto es el manual de uso.

---

## 1. Cómo se crea el Administrador General

**Lo crea un script que corro a mano, una sola vez por base de datos:** `backend/app/seed.py`.

Hace falta porque todos los usuarios los da de alta un Administrador General, y **al primero no lo puede dar de alta nadie**. Es el único que no puede salir de ninguno de los dos caminos normales —ni del alta que hace un administrador, ni del registro propio, porque una cuenta que se registra sola nace con el rol `pendiente` y necesita que un administrador la apruebe—. Alguien tiene que ser el primero, y ese es el que siembra el script.

```powershell
cd backend
venv\Scripts\python.exe -m app.seed                  # solo el Administrador General
venv\Scripts\python.exe -m app.seed --con-pruebas    # y además Encargado, Propietario e Inquilino
```

En desarrollo queda con las credenciales que están en el [`README.md`](../README.md): `administrador@test.com` / `Test1234!`.

### Por qué se corre a mano y no al arrancar la aplicación

Sería más cómodo colgarlo del arranque, al lado de la sincronización del esquema, y decidí que no. El arranque de la aplicación es el mismo en desarrollo y en producción: un seed automático ahí significa que **cada despliegue** se asegura de que exista un usuario con permisos totales y una contraseña que está escrita en el README de un repositorio. Sincronizar el esquema al arrancar es seguro porque es aditivo y no crea accesos; crear un administrador es exactamente lo contrario.

### En producción no acepta las credenciales de desarrollo

El script se niega a sembrar si detecta que está en producción sin que yo le haya dado credenciales propias. Hay que definir dos variables de entorno antes de correrlo:

| Variable | Qué es |
|---|---|
| `SEED_ADMIN_EMAIL` | El email del administrador inicial. Si falta, usaría `administrador@test.com`, que es público. |
| `SEED_ADMIN_PASSWORD` | Su contraseña. Si falta, usaría la del README, que también es pública. |

Es el mismo criterio que la guarda del secreto del JWT: prefiero que el paso falle fuerte y no arranque, a que arranque con un acceso que conoce cualquiera que lea el repositorio.

### Es idempotente, y eso incluye no pisar contraseñas

Correrlo dos veces no duplica nada y **a un usuario que ya existe no le toca nada, ni el hash de la contraseña**. Eso importa: si alguien le cambió la contraseña al administrador, un seed que la sobrescribiera volvería a dejar la del README sin avisar.

La contracara, que conviene tener presente: si una cuenta existe con una contraseña que no es la que yo creo, **el seed no la arregla**. Lo dice en la salida (`ya existía. No se modificó nada.`). Todavía no hay circuito de recuperación de contraseña, así que la salida es cambiarle el hash a mano — está en la sección 4.

---

## 2. Los roles que existen

Son **ocho roles del negocio**, más un noveno estado interno. Salieron de las entrevistas y son parte del dominio: no son algo que se dé de alta, igual que no se da de alta un tipo de comprobante.

| Valor exacto en la columna | Cómo se muestra en pantalla | Alcance | Permisos |
|---|---|---|---|
| `admin_general` | Administrador General | La cartera completa | Escribe |
| `admin_consorcio` | Administrador de Consorcio | Los edificios que administra | Escribe |
| `encargado` | Encargado | Su edificio | Escribe |
| `propietario` | Propietario | Su o sus unidades | Escribe |
| `inquilino` | Inquilino | Su unidad | Escribe |
| `proveedor` | Proveedor / Técnico | Las órdenes de trabajo que tiene asignadas | Escribe |
| `auditor` | Auditor | Los edificios que le asignen | **Solo lectura** |
| `seguridad` | Personal de seguridad | Su edificio | Escribe |
| `pendiente` | Pendiente de aprobación | **Ninguno** | Solo lectura |

**`pendiente` no es un rol que yo asigne.** Lo escribe el sistema cuando alguien se registra solo desde el login, y lo que hace es dejar la cuenta inerte: puede iniciar sesión —y lee que su cuenta espera aprobación— y no alcanza ninguna pantalla, porque `pendiente` no figura en la lista de roles habilitados de ninguna. Eso es lo que hace que tener el registro abierto no sea un problema de seguridad: lo peor que consigue un abuso es crear filas que no pueden nada. Cuando lo apruebo desde la pantalla de Usuarios, le asigno el rol real y deja de ser pendiente.

**De los ocho, siete se pueden habilitar por edificio.** Cada edificio tiene una lista de `roles_habilitados` que dice qué roles tienen sentido ahí (un edificio sin cocheras ni espacios comunes puede no querer `seguridad`). El que queda afuera es `admin_general`, porque su alcance es la cartera entera y no se habilita edificio por edificio.

### Dónde vive esta lista, y por qué no hay una tabla `roles`

La lista está en **un solo lugar**: la matriz de `backend/app/services/autorizacion.py`. El `CHECK` de la tabla `usuarios` se arma a partir de esa misma matriz, así que la base y la aplicación no pueden quedar en desacuerdo.

No hay una tabla `roles` y decidí que no la haya, porque acá **un rol no es un dato, es comportamiento**. Insertar una fila en esa tabla no crearía ningún permiso: qué alcanza cada rol, qué información financiera ve, si puede escribir y a qué pantallas entra está escrito en la matriz y en las dependencias de autorización. Tendría una tabla donde se puede crear el rol "contador" y un sistema donde "contador" no puede absolutamente nada, sin ningún error que lo avise. Y la misma verdad quedaría en dos lugares que pueden divergir.

Para ver la lista desde la base, está en la definición de la tabla:

```sql
-- En el editor SQL de Supabase, o con .schema usuarios en SQLite
CONSTRAINT ck_usuarios_rol_valido CHECK (rol IN ('admin_general', 'admin_consorcio',
  'encargado', 'propietario', 'inquilino', 'proveedor', 'auditor', 'seguridad', 'pendiente'))
```

Y desde la API, con sesión de Administrador General, `GET /api/usuarios/opciones` devuelve los ocho asignables con su etiqueta legible.

---

## 3. Cómo cambio el rol de un usuario a mano

Lo normal es hacerlo desde la pantalla de Usuarios, que es la que valida todo. Esto es para cuando necesito resolverlo directo en la base.

```sql
-- Convertir una cuenta en Administrador General
UPDATE usuarios SET rol = 'admin_general' WHERE email = 'gustavo@ejemplo.com';

-- Aprobar a mano una cuenta que se registró sola y quedó pendiente
UPDATE usuarios SET rol = 'propietario' WHERE email = 'ana@ejemplo.com';

-- Ver con qué rol quedó cada uno
SELECT id, nombre, email, rol, activo FROM usuarios ORDER BY rol, nombre;
```

Cuatro cosas que conviene saber antes de tocar la tabla:

1. **El valor tiene que ser exactamente uno de los nueve de la tabla de arriba**, en minúscula y con guion bajo. Cualquier otro lo rechaza el `CHECK` de la base, así que no se puede dejar un rol inválido guardado — el `UPDATE` falla y no pasa nada.
2. **El cambio toma efecto en el siguiente pedido**, no hace falta reiniciar el backend: el rol se lee de la base en cada pedido y no queda guardado en el token. Lo que sí hay que hacer es **recargar la pantalla**, porque el menú de la izquierda se arma al cargar la página.
3. **Para dar de baja a alguien no se borra la fila**: se pone `activo = false`. La baja de este sistema es siempre lógica, porque un usuario borrado se lleva puesta la trazabilidad de todo lo que cargó, y esos registros tienen que seguir diciendo quién los creó años después. Con `activo = false` el login lo rechaza y la cuenta se puede reactivar.
4. **Tampoco me conviene desactivarme a mí mismo.** La aplicación no lo permite —ni desde la pantalla ni por API— porque un Administrador General desactivado pierde en ese instante la forma de volver a entrar: el login rechaza inactivos y hace falta ser administrador para reactivar a alguien. Por SQL no hay nada que lo impida, así que ahí el cuidado es mío.

---

## 4. Cómo cambio una contraseña a mano

Todavía no hay circuito de recuperación, así que si una cuenta queda con una contraseña que nadie sabe, la única salida es escribirle el hash. **No se puede escribir la contraseña en texto plano en la columna**: la columna guarda un hash de bcrypt y un texto plano ahí deja la cuenta sin poder entrar nunca más.

El hash se genera con la misma función que usa la aplicación:

```powershell
cd backend
venv\Scripts\python.exe -c "from app.core import security; print(security.hashear_password('LaNueva123!'))"
```

Eso imprime algo de 60 caracteres que empieza con `$2b$12$`. Después:

```sql
UPDATE usuarios SET password_hash = '$2b$12$...el hash que imprimió...'
WHERE email = 'ana@ejemplo.com';
```

La contraseña nueva tiene que cumplir la política del sistema (ocho caracteres, mayúscula, minúscula, número y símbolo). El `UPDATE` directo no la valida —la validación está en la aplicación, no en la base— pero si no la cumple, la cuenta va a quedar con una contraseña que la pantalla de cambio de contraseña va a rechazar el día que exista.

---

*Documentos relacionados: [`02_Documento_Tecnico.md`](02_Documento_Tecnico.md) sección 4 (autenticación, matriz de roles y autorización) · [`README.md`](../README.md) (usuarios de prueba y sus credenciales) · [`05_Roadmap.md`](05_Roadmap.md) `F1-T06` (el seed) y `F1-T16B` (el registro propio y la aprobación).*

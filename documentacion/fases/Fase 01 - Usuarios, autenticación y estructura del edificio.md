# Fase 1 — Usuarios, autenticación y estructura del edificio

**Estado:** completa y aprobada.
**Corresponde a:** Documento General, secciones 3 (Actores del sistema) y 5 (Gestión de edificios); Documento Técnico, secciones 6 y 7.

## Objetivo de la fase

Antes de esta fase, el proyecto solo tenía un esqueleto de backend y frontend comunicándose entre sí (Fase 0), sin ningún dato de negocio. La Fase 1 construye la base de la que depende absolutamente todo lo demás: **quién puede entrar al sistema, qué puede ver/hacer según su rol, y cómo se representa un edificio real** (pisos, departamentos, cocheras, espacios comunes). Ninguna fase posterior tiene sentido sin esto — Financiero (Fase 2) necesita departamentos reales para prorratear gastos, el Dashboard Visual (Fase 5) necesita la estructura de pisos, etc.

Se dividió en dos bloques: **Usuarios y autenticación** primero, **Estructura del edificio** después — porque dar de alta un edificio ya necesita saber quién es su Administrador de Consorcio.

---

## Bloque 1: Usuarios y autenticación

### 1.1 — La matriz de roles (lógica, antes que código de infraestructura)

Documento Técnico, sección 6.2. Antes de escribir un solo modelo o endpoint, se definió en Python puro la matriz completa de los 8 roles del sistema y su alcance — para que cada endpoint futuro la reutilice en vez de reinventar el chequeo de permisos:

```python
# services/autorizacion.py
ROLES = (
    "admin_general", "admin_consorcio", "encargado", "propietario",
    "inquilino", "proveedor", "auditor", "seguridad",
)

MATRIZ_ROLES = {
    "admin_general":   {"alcance": ALCANCE_CARTERA,  "ve_financiero_edificio": True,  "solo_lectura": False},
    "admin_consorcio": {"alcance": ALCANCE_EDIFICIO,  "ve_financiero_edificio": True,  "solo_lectura": False},
    "propietario":     {"alcance": ALCANCE_UNIDAD,    "ve_financiero_unidad": True,    "solo_lectura": False},
    "inquilino":       {"alcance": ALCANCE_UNIDAD,    "ve_financiero_unidad": False,   "solo_lectura": False},
    "auditor":         {"alcance": ALCANCE_EDIFICIO_O_CARTERA, "ve_financiero_edificio": True, "solo_lectura": True},
    # ...
}
```

Esta matriz es la única fuente de verdad de permisos del proyecto — cuando en fases posteriores apareció una duda real de RBAC (por ejemplo, si Inquilino debía ver el financiero de su unidad, o si Auditor podía entrar a Deudores sin tener un edificio asignado), la respuesta siempre se buscó comparando el código contra esta tabla, nunca al revés.

### 1.2 — Modelo `Usuario` y contraseñas seguras

```python
# models/usuario.py
class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (CheckConstraint(f"rol IN ({_ROLES_SQL})", name="ck_usuarios_rol_valido"),)

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)   # nunca la contraseña real
    rol = Column(String, nullable=False)              # validado contra ROLES, no un string libre
    activo = Column(Boolean, nullable=False, default=True)
```

`activo` en vez de borrar filas: dar de baja a un usuario nunca lo elimina de la base (baja lógica), para no perder trazabilidad histórica de quién pagó qué o quién cargó qué reclamo.

Las contraseñas se hashean con `bcrypt` (vía `passlib`) — regla no negociable de todo el proyecto: **ninguna contraseña se guarda ni se loguea en texto plano, ni siquiera en modo test.**

```python
# core/security.py
_contexto_password = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hashear_password(password: str) -> str:
    return _contexto_password.hash(password)

def verificar_password(password: str, password_hash: str) -> bool:
    return _contexto_password.verify(password, password_hash)
```

### 1.3 — Login con JWT

```python
# routers/auth.py
@router.post("/login", response_model=TokenSalida)
def login(datos: LoginEntrada, db: Session = Depends(obtener_db)):
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if not usuario or not verificar_password(datos.password, usuario.password_hash):
        raise _ERROR_CREDENCIALES
    if not usuario.activo:
        raise HTTPException(status_code=401, detail="Usuario desactivado")
    token = crear_token_acceso({"sub": usuario.email, "rol": usuario.rol, "edificios": []})
    return TokenSalida(access_token=token)
```

El JWT es de corta duración y **sin estado en el servidor**: el backend no guarda sesiones, solo firma y valida el token en cada request. `GET /api/auth/me` deja que el frontend recupere "quién soy" a partir del token guardado, sin volver a pedir la contraseña.

### 1.4 — La dependencia de autorización, reutilizada por todo el backend

```python
# core/dependencies.py
def obtener_usuario_actual(credenciales=Depends(_esquema_bearer), db=Depends(obtener_db)) -> UsuarioAutenticado:
    try:
        datos = decodificar_token(credenciales.credentials)
    except TokenInvalido:
        raise HTTPException(status_code=401, detail="Token inválido o vencido")
    usuario = db.query(Usuario).filter(Usuario.email == datos.get("sub")).first()
    if not usuario or not usuario.activo:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")
    return UsuarioAutenticado(usuario=usuario, edificios=datos.get("edificios", []))
```

De acá en adelante, **cada endpoint protegido del proyecto** depende de `obtener_usuario_actual` (o de una dependencia más específica construida sobre ella, como `requerir_admin_del_edificio` en Financiero) — nunca se repite el chequeo de token a mano en un router nuevo.

### 1.5 — CRUD de usuarios y pantallas

`routers/usuarios.py` expone alta, edición y baja lógica; `usuarios.html` + `assets/js/usuarios.js` son la pantalla real (listado, alta con modal, edición, y un botón de estado con animación de *ripple* para activar/desactivar) — visible en el sidebar solo para los roles con permiso de gestionar usuarios (Admin General/Consorcio).

**Hallazgo de seguridad real, corregido en el momento:** un Administrador General podía desactivar su propia cuenta y quedar sin forma de volver a entrar (los usuarios inactivos no pueden loguearse). Se agregó una guarda explícita:

```python
def _prohibir_autodesactivacion(usuario_id: int, actual: UsuarioAutenticado) -> None:
    if usuario_id == actual.usuario.id:
        raise HTTPException(status_code=400, detail="No podés desactivar tu propia cuenta")
```

---

## Bloque 2: Estructura del edificio

### 2.1 — Generación automática de la estructura vacía

Documento General 5.1: al dar de alta un edificio indicando cantidad de pisos y unidades por piso, el sistema genera solo la estructura (pisos + departamentos sin propietario) — nadie la carga a mano piso por piso. Es lógica pura, sin tocar la base, para poder probarla antes de que existan los modelos reales:

```python
# services/edificios.py
def generar_estructura_vacia(cantidad_pisos: int, unidades_por_piso: int) -> list[dict]:
    letras = string.ascii_uppercase[:unidades_por_piso]
    return [
        {"numero": n, "departamentos": [f"{n}{letra}" for letra in letras]}
        for n in range(1, cantidad_pisos + 1)
    ]
    # generar_estructura_vacia(3, 4) -> pisos 1-3, cada uno con ["1A","1B","1C","1D"], etc.
```

### 2.2 — Modelos `Edificio`, `Piso`, `Departamento`, `Cochera`, `EspacioComun`

Un solo archivo (`models/edificio.py`) para las cinco entidades — regla del Documento Técnico: un archivo por dominio, no uno por tabla. `Edificio` guarda, entre otras cosas, el medio de pago (`cbu`/`alias_cbu`, usado recién en la Fase 2) y la configuración operativa (contacto de emergencia, vencimiento de expensas).

### 2.3 — Alta de edificio con estructura real

```python
# routers/edificios.py
@router.post("", response_model=EdificioSalida, status_code=201)
def crear_edificio(datos: EdificioEntrada, actual=Depends(_requerir_admin_general), db=Depends(obtener_db)):
    edificio = Edificio(nombre=datos.nombre, direccion=datos.direccion, ...)
    db.add(edificio)
    db.flush()
    for piso_data in generar_estructura_vacia(datos.cantidad_pisos, datos.unidades_por_piso):
        piso = Piso(edificio_id=edificio.id, numero=piso_data["numero"])
        db.add(piso)
        db.flush()
        for identificador in piso_data["departamentos"]:
            db.add(Departamento(piso_id=piso.id, identificador=identificador))
    db.commit()
    ...
```

Todo en una sola transacción: el edificio y su estructura completa se crean juntos, o no se crea nada.

### 2.4 — Asignar un propietario/inquilino a un departamento

```python
# routers/edificios.py
@router.patch("/departamentos/{departamento_id}/asignacion", response_model=DepartamentoSalida)
def asignar_departamento(departamento_id, datos, db, actual):
    ...
    # Un inquilino vive en UN solo lugar a la vez — a diferencia del
    # propietario, que sí puede tener varias unidades a su nombre.
    if campo == "inquilino_id":
        ya_asignado = db.query(Departamento).filter(
            Departamento.inquilino_id == valor, Departamento.id != departamento_id
        ).first()
        if ya_asignado:
            raise HTTPException(400, "Ese inquilino ya está asignado a otro departamento")
```

### 2.5 — Frontend: `edificios.html`

Alta de edificio con geocodificación real (dirección + CP contra la API de Nominatim/OpenStreetMap, mostrada en un mapa con Leaflet — la primera integración con una API externa del proyecto), listado de edificios, y una pestaña "Estructura" (vista en lista de pisos/departamentos/cocheras/espacios comunes — la versión gráfica coloreada es el Dashboard Visual de la Fase 5) con alta de piso/departamento y asignación de propietario/inquilino.

---

## Cómo probarlo

Credenciales completas en [`usuarios.md`](../usuarios.md). Punto de partida rápido:

1. Entrar como `admin@smartbuilding.test` / `admin123` → sidebar con "Edificios" y "Usuarios".
2. `usuarios.html`: dar de alta un usuario de cada rol, editar uno, desactivar y reactivar otro (el botón de estado).
3. `edificios.html`: dar de alta un edificio con estructura, entrar a su detalle, asignar un propietario a un departamento.
4. Salir y entrar como ese propietario → confirmar que el sidebar no tiene "Edificios" ni "Usuarios" (no le corresponden).

## Estado final

Backend cubierto por tests automáticos (RBAC, hash/JWT, CRUD de usuarios, generación de estructura, alta de edificio, asignación) — base sobre la que se construyó toda la suite de tests del proyecto, hoy en 223 tests pasando entre todas las fases.

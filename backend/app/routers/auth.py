"""Autenticacion: registrarse, iniciar sesion y saber quien soy.

Tres endpoints, y son la base de todo lo demas:

- ``POST /api/auth/registro`` — alta propia, queda esperando aprobacion.
- ``POST /api/auth/login``    — email y contrasenia a cambio de un token.
- ``GET  /api/auth/me``       — el usuario de la sesion.

**`/registro` es el unico endpoint de escritura sin autenticacion de todo el
sistema.** Eso cambia su superficie de ataque respecto de cualquier otro: lo
puede llamar cualquiera, desde cualquier parte, sin credenciales. Las tres
defensas que lo hacen aceptable estan documentadas en el propio endpoint y
ninguna es opcional.

`/auth/me` es lo que el frontend pide al cargar cualquier pantalla autenticada
para armar la navegacion segun el rol (F1-T11). Por eso devuelve, ademas de los
datos del usuario, la fila de la matriz de permisos que le corresponde: asi la
interfaz no tiene que declarar su propia copia de la matriz.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import security
from app.core.dependencies import UsuarioActual
from app.database import obtener_db
from app.models.usuario import Usuario
from app.schemas.usuario import (
    PoliticaDePassword,
    RegistroAceptado,
    RegistroPublico,
    Token,
    UsuarioRespuesta,
    normalizar_email,
)
from app.services import autorizacion

router = APIRouter(prefix="/auth", tags=["Autenticacion"])


@router.post("/login", response_model=Token)
def login(
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(obtener_db)],
) -> Token:
    """Valida las credenciales y devuelve el token de sesion.

    **El campo se llama `username` y lleva el email.** Es el nombre que fija el
    estandar de OAuth2, y respetarlo es lo que hace que el boton "Authorize" de
    /docs funcione — que es la herramienta con la que se prueba cada endpoint
    protegido antes de que exista su pantalla. Renombrarlo a `email` obligaria
    a escribir el login a mano en /docs para cada prueba.

    El email se normaliza con la MISMA funcion que el alta. Sin eso, quien se
    da de alta como `Ana@...` queda guardado en minusculas y despues no entra
    escribiendo exactamente lo mismo que puso al registrarse.
    """
    email = normalizar_email(formulario.username)
    usuario = db.scalar(select(Usuario).where(Usuario.email == email))

    # Un unico mensaje y un unico codigo para los tres casos: el usuario no
    # existe, la contrasenia esta mal, o el usuario esta desactivado.
    #
    # Es deliberado. Si "ese email no existe" y "esa contrasenia es incorrecta"
    # dieran respuestas distintas, el login se convertiria en una herramienta
    # para averiguar que direcciones estan registradas en el sistema, probando
    # emails de a uno. Y distinguir al usuario inactivo le confirmaria a quien
    # pruebe que esa cuenta existe.
    #
    # La verificacion de la contrasenia se corre IGUAL cuando el usuario no
    # existe, contra un hash descartable. Si se cortara antes, la respuesta del
    # caso "no existe" seria notablemente mas rapida que la del caso
    # "contrasenia incorrecta", y esa diferencia de tiempos alcanza para
    # distinguirlos aunque el mensaje sea el mismo.
    if usuario is None:
        security.verificar_password(formulario.password, _HASH_DESCARTABLE)
        raise _CREDENCIALES_INVALIDAS

    if not security.verificar_password(formulario.password, usuario.password_hash):
        raise _CREDENCIALES_INVALIDAS

    # Un usuario inactivo no inicia sesion. Y como `obtener_usuario_actual`
    # vuelve a verificar `activo` en cada request, tampoco sigue operando con
    # un token que ya tenia: la baja es efectiva en el momento, no cuando el
    # token vence.
    if not usuario.activo:
        raise _CREDENCIALES_INVALIDAS

    return Token(access_token=security.crear_token_de_acceso(usuario.id))


@router.post(
    "/registro",
    response_model=RegistroAceptado,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Registrarse y quedar a la espera de aprobacion",
)
def registro(
    datos: RegistroPublico,
    db: Annotated[Session, Depends(obtener_db)],
) -> RegistroAceptado:
    """Crea una cuenta propia, sin rol, a la espera de que la aprueben.

    Existe para que el Administrador General no tenga que cargar a mano los
    datos de cada persona del consorcio. Cuarenta unidades son cuarenta altas
    dictadas por telefono o por mensaje, y encima cargadas por alguien que no
    es el dueño del dato. Con esto, cada uno carga lo suyo y el administrador
    solo **aprueba**, que es la decision que si le corresponde.

    ========================================================================
    1. EL ROL NO VIENE EN EL PEDIDO. LO PONE ESTA FUNCION.
    ========================================================================

    `RegistroPublico` no tiene el campo `rol` y rechaza los campos que no
    conoce, asi que mandarlo es un 422. Y aun si pasara, aca abajo el rol se
    escribe como constante: `autorizacion.PENDIENTE`, sin leer nada del
    cuerpo. Son dos barreras para lo mismo a proposito, porque el costo de
    equivocarse es que cualquiera se de de alta como Administrador General.

    ========================================================================
    2. UN USUARIO `pendiente` PUEDE ENTRAR Y NO PUEDE HACER NADA
    ========================================================================

    Queda con `activo=True`, o sea que inicia sesion. Es querido: la persona
    tiene que poder entrar y leer que su cuenta esta esperando aprobacion. Si
    quedara inactiva, el login le diria "email o contraseña incorrectos" —
    que es mentira y la manda a pedir ayuda por el problema equivocado.

    Que pueda entrar no le da acceso a nada: en este sistema el rol es lo
    unico que habilita, cada pantalla declara su lista de roles permitidos y
    `pendiente` no esta en ninguna. Una cuenta pendiente es **inerte**, y eso
    es lo que hace que un endpoint publico de registro no sea un problema de
    seguridad: lo peor que logra un abuso es crear filas que no pueden nada.

    ========================================================================
    3. LA RESPUESTA ES LA MISMA EXISTA O NO EL EMAIL
    ========================================================================

    Es la defensa que menos se ve y la mas facil de romper sin querer. El alta
    del administrador devuelve 400 cuando el email ya existe, y ahi esta bien:
    la usa una sola persona de confianza y el mensaje le ahorra una consulta.
    En un endpoint **publico**, esa misma distincion es un oraculo: cualquiera
    prueba direcciones de a una y averigua quien tiene cuenta en el sistema —
    o sea, quien vive en el edificio.

    Asi que el email duplicado **no se consulta antes**: se intenta el INSERT y
    se deja que el indice unico de la tabla lo rechace. Se traga el
    `IntegrityError` y se responde exactamente lo mismo que en el caso exitoso.
    El aviso de "ya tenias cuenta" es informacion para el dueño de la casilla,
    no para quien manda el pedido, y se va a mandar por mail cuando el sistema
    tenga mail.

    **Y el tiempo tambien tiene que parecerse**, porque una diferencia de
    tiempos alcanza para distinguir dos respuestas idénticas. El hash de la
    contrasenia —con diferencia, lo mas caro de esta funcion— se calcula
    **antes** del INSERT, asi que los dos caminos lo pagan igual. Lo unico que
    cambia es un rollback contra un commit, que al lado de bcrypt no se mide.
    Si alguna vez se agrega una verificacion previa del email, hay que
    acordarse de que tiene que correr en los dos casos, igual que en el login.
    """
    usuario = Usuario(
        nombre=datos.nombre,
        email=datos.email,
        # El hash va antes del INSERT, y eso importa: ver el punto 3.
        password_hash=security.hashear_password(datos.password),
        # Constante, no un dato del pedido. Ver el punto 1.
        rol=autorizacion.PENDIENTE,
        telefono=datos.telefono,
        # Explicito aunque sea el valor por defecto de la columna, porque acá
        # es una decision y no una omision. Ver el punto 2.
        activo=True,
    )
    db.add(usuario)

    try:
        db.commit()
    except IntegrityError:
        # El rollback no es opcional: sin el, la sesion queda en estado fallido
        # y cualquier consulta posterior de este mismo request revienta con un
        # error que no menciona en ningun momento el INSERT que lo causo.
        db.rollback()

        # ====================================================================
        # SOLO SE TRAGA EL EMAIL REPETIDO. CUALQUIER OTRA COSA SE PROPAGA.
        # ====================================================================
        #
        # La primera version de esto atrapaba `IntegrityError` a secas, y eso
        # convertia CUALQUIER falla de integridad en un 202 con la base
        # intacta. No es una hipotesis: paso. La tabla de la base de
        # desarrollo se habia creado antes de que existiera `pendiente`, asi
        # que su CHECK de `rol` listaba ocho valores y rechazaba el INSERT. El
        # endpoint respondia "listo, recibimos tus datos" y no habia creado
        # nada, sin un solo log. Es el peor tipo de bug que se puede escribir:
        # el sistema afirma que hizo algo que no hizo.
        #
        # Asi que se verifica el motivo. Si el email esta en la tabla, el
        # choque fue el indice unico y corresponde la respuesta uniforme. Si
        # no esta, el INSERT fallo por OTRA razon y hay que enterarse: se
        # vuelve a lanzar, sale un 500 y queda en el log.
        #
        # Se pregunta por el estado de la base en vez de leer el codigo de
        # error del driver a proposito: ese codigo es distinto en SQLite y en
        # PostgreSQL, y el proyecto corre contra los dos. Una comprobacion que
        # funcione en desarrollo y no en produccion seria peor que ninguna.
        #
        # Sobre el canal de tiempos del punto 3: esta consulta de mas corre
        # unicamente en el camino del email repetido, asi que lo hace un poco
        # mas lento. Es una busqueda por indice unico —menos de un
        # milisegundo— contra el hash de bcrypt, que son cientos y lo pagan
        # los dos caminos. La diferencia queda muy por debajo del ruido de la
        # red.
        ya_existia = db.scalar(
            select(Usuario.id).where(Usuario.email == datos.email)
        )
        if ya_existia is None:
            raise

    return _REGISTRO_ACEPTADO


@router.get(
    "/politica-password",
    response_model=PoliticaDePassword,
    summary="Los requisitos de la contrasenia, para el formulario de registro",
)
def politica_de_password() -> PoliticaDePassword:
    """Los requisitos de la contrasenia, sin autenticar.

    ========================================================================
    POR QUE NO ALCANZABA CON `/usuarios/opciones`
    ========================================================================

    Ese endpoint ya devuelve esta misma politica, pero pide sesion de
    Administrador General, y con razon: ademas de la politica devuelve el
    catalogo de roles, que es estructura interna del sistema.

    El formulario de registro necesita la politica y, por definicion, lo usa
    alguien que todavia no tiene cuenta. Las alternativas eran peores:

      - Escribir los requisitos en el HTML. Seria la politica en dos lugares,
        que es exactamente lo que `textos_de_requisitos()` existe para
        evitar: el dia que cambie, la pantalla seguiria pidiendo lo de antes
        y la persona leeria un requisito y recibiria el rechazo por otro.
      - No mostrar nada y dejar que se entere por el 422. Funciona, pero le
        hace adivinar la contrasenia a quien no tiene a quien preguntarle.

    ========================================================================
    POR QUE ES SEGURO QUE SEA PUBLICO
    ========================================================================

    No revela nada que no se pueda averiguar mandando una contrasenia mala al
    registro: el 422 ya devuelve la lista completa de requisitos que faltan.
    Esto solo la dice antes. Y conocer la politica no debilita ninguna
    contrasenia concreta — si lo hiciera, el problema seria la politica.

    No lleva `db` ni sesion: lee dos constantes del modulo de seguridad.
    """
    return PoliticaDePassword.vigente()


@router.get("/me", response_model=UsuarioRespuesta)
def yo(usuario: UsuarioActual) -> Usuario:
    """El usuario de la sesion, con la fila de la matriz que le corresponde.

    Es el primer pedido de toda pantalla autenticada: el frontend lo usa para
    saber que accesos mostrar en el sidebar. Y es, de paso, la forma mas simple
    de verificar que un token sigue valiendo.
    """
    return usuario


_REGISTRO_ACEPTADO = RegistroAceptado(
    mensaje=(
        "Listo, recibimos tus datos. Un administrador tiene que aprobar la "
        "cuenta antes de que puedas usar el sistema. Ya podés iniciar sesión "
        "para ver en qué estado está."
    )
)
"""La respuesta del registro, una sola instancia para los dos caminos.

Que sea UNA constante y no dos mensajes armados en cada rama es lo que hace
imposible que se desacoplen sin que nadie lo note. Dos textos "iguales"
escritos en dos lugares son dos textos que en algun momento dejan de ser
iguales, y la diferencia volveria a distinguir el email que existe del que no.
"""

_CREDENCIALES_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Email o contraseña incorrectos.",
    headers={"WWW-Authenticate": "Bearer"},
)

# Un hash real de una contrasenia que no le sirve a nadie, calculado una sola
# vez al importar el modulo. Existe solo para que el caso "el email no existe"
# pague el mismo costo de verificacion que el caso "la contrasenia esta mal".
_HASH_DESCARTABLE = security.hashear_password("hash-descartable-para-igualar-tiempos")

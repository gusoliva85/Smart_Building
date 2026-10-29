"""Siembra el primer Administrador General.

Sin esto no hay forma de iniciar sesion la primera vez: todos los usuarios los
crea un Administrador General, y el primero no lo puede crear nadie.

Se corre a mano, desde `backend/`:

    venv\\Scripts\\python.exe -m app.seed

============================================================================
POR QUE SE CORRE A MANO Y NO AL ARRANCAR LA APLICACION
============================================================================

Seria comodo colgarlo del ciclo de vida de `main.py`, al lado de
`sincronizar_esquema()`. No se hace, y es deliberado: ese mismo arranque es el
de produccion. Un seed automatico ahi significa que **cada despliegue** se
asegura de que exista un usuario administrador con credenciales que estan
escritas en el README de un repositorio, y que por lo tanto conoce cualquiera.

Sincronizar el esquema al arrancar es seguro porque es aditivo y no crea
accesos. Crear un usuario con permisos totales es exactamente lo contrario.

============================================================================
IDEMPOTENTE
============================================================================

Correrlo dos veces no duplica nada ni sobrescribe la contrasenia de un usuario
existente. Que no sobrescriba importa: si alguien le cambio la contrasenia al
administrador, un seed que la pisara volveria a dejar la del README sin avisar.
"""

import logging
import os
import sys
from dataclasses import dataclass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config, security
from app.core.migraciones import sincronizar_esquema
from app.database import SessionLocal
from app.models.usuario import Usuario
from app.schemas.usuario import normalizar_email
from app.services import autorizacion

logger = logging.getLogger(__name__)

# --------------------------------------------------- credenciales iniciales --

# Valores de desarrollo: conocidos, publicos y anotados en el README. La guarda
# de abajo impide que lleguen a produccion, igual que hace `config.py` con el
# secreto del JWT. Es el mismo patron a proposito: si el proyecto ya tiene una
# forma de tratar un valor de desarrollo peligroso, conviene que haya una sola.
EMAIL_ADMIN_DESARROLLO = "administrador@test.com"
PASSWORD_ADMIN_DESARROLLO = "Test1234!"

NOMBRE_ADMIN = "Administrador General"

EMAIL_ADMIN = normalizar_email(os.getenv("SEED_ADMIN_EMAIL", EMAIL_ADMIN_DESARROLLO))
PASSWORD_ADMIN = os.getenv("SEED_ADMIN_PASSWORD", PASSWORD_ADMIN_DESARROLLO)


class SeedInseguro(RuntimeError):
    """Se intento sembrar en produccion con las credenciales de desarrollo."""


class SeedEmailInvalido(ValueError):
    """`SEED_ADMIN_EMAIL` no es un email valido."""


@dataclass(frozen=True)
class ResultadoSeed:
    """Que hizo el seed. Se devuelve en vez de solo loguearse para que los
    tests puedan verificar la idempotencia sin leer logs."""

    email: str
    creado: bool

    @property
    def ya_existia(self) -> bool:
        return not self.creado


def _verificar_que_se_puede_sembrar() -> None:
    """Impide dejar un administrador de credenciales publicas en produccion.

    En desarrollo no hace nada. En produccion exige que las dos credenciales
    vengan por variables de entorno: un administrador con la contrasenia que
    figura en el README es, en la practica, una puerta abierta.
    """
    if not config.ES_PRODUCCION:
        return

    problemas = []

    if PASSWORD_ADMIN == PASSWORD_ADMIN_DESARROLLO:
        problemas.append(
            "SEED_ADMIN_PASSWORD no esta definida, asi que se usaria la "
            "contrasenia de desarrollo, que esta escrita en el README del "
            "repositorio. Cualquiera que lo lea entra como administrador."
        )

    if EMAIL_ADMIN == EMAIL_ADMIN_DESARROLLO:
        problemas.append(
            "SEED_ADMIN_EMAIL no esta definida, asi que se usaria "
            f"{EMAIL_ADMIN_DESARROLLO}, que tambien es publico."
        )

    if problemas:
        raise SeedInseguro(
            "No se puede sembrar el administrador inicial en produccion:\n"
            + "\n".join(f"  - {p}" for p in problemas)
        )


def _verificar_que_el_email_es_valido() -> None:
    """Valida `SEED_ADMIN_EMAIL` con la misma regla que el alta de usuarios.

    El seed es la UNICA via por la que entra un usuario sin pasar por
    `UsuarioCrear`, asi que es la unica que podria meter en la base un email
    que el resto del sistema no considera valido. Y un email invalido guardado
    no se nota al sembrar: se nota despues, cuando algo que lo valida falla
    sobre una fila que ya existe.
    """
    try:
        TypeAdapter(EmailStr).validate_python(EMAIL_ADMIN)
    except ValidationError as error:
        raise SeedEmailInvalido(
            f"SEED_ADMIN_EMAIL no es un email valido: {EMAIL_ADMIN!r}.\n"
            f"  {error.errors()[0]['msg']}"
        ) from error


def sembrar(db: Session) -> ResultadoSeed:
    """Crea el Administrador General inicial si todavia no existe.

    La contrasenia pasa por `validar_password` antes de hashearse. No es un
    tramite: es lo que garantiza que el usuario que siembra el sistema cumpla
    la misma politica que el sistema le exige a todos los demas. Si algun dia
    alguien cambia la contrasenia de desarrollo por una debil, esto falla en el
    momento en vez de dejar al administrador fuera de la regla.
    """
    _verificar_que_se_puede_sembrar()
    _verificar_que_el_email_es_valido()
    security.validar_password(PASSWORD_ADMIN)

    existente = db.scalar(select(Usuario).where(Usuario.email == EMAIL_ADMIN))
    if existente is not None:
        logger.info("Seed: %s ya existe, no se toca.", EMAIL_ADMIN)
        return ResultadoSeed(email=EMAIL_ADMIN, creado=False)

    db.add(
        Usuario(
            nombre=NOMBRE_ADMIN,
            email=EMAIL_ADMIN,
            password_hash=security.hashear_password(PASSWORD_ADMIN),
            rol=autorizacion.ADMIN_GENERAL,
        )
    )
    db.commit()

    logger.info("Seed: creado %s con rol %s.", EMAIL_ADMIN, autorizacion.ADMIN_GENERAL)
    return ResultadoSeed(email=EMAIL_ADMIN, creado=True)


def main() -> int:
    """Punto de entrada del script. Devuelve el codigo de salida del proceso."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")

    # Se sincroniza el esquema antes de sembrar, y no es redundante con el
    # arranque de la aplicacion: sobre un repositorio recien clonado la base no
    # tiene ninguna tabla todavia, porque las crea el ciclo de vida de
    # `main.py`. Sin esto, el primer `python -m app.seed` de cualquier persona
    # falla con "no such table: usuarios", que no dice en ningun momento que lo
    # que falta es haber levantado el backend una vez.
    #
    # Es seguro: `sincronizar_esquema` es puramente aditiva y no crea accesos.
    # Lo que no se cuelga del arranque de la aplicacion es el seed, que si los
    # crea.
    sincronizar_esquema()

    db = SessionLocal()
    try:
        resultado = sembrar(db)
    except (SeedInseguro, SeedEmailInvalido, security.PasswordInsegura) as error:
        logger.error("%s", error)
        return 1
    finally:
        db.close()

    if resultado.creado:
        # El email si, la contrasenia NO. La regla de `core/security.py` es que
        # ninguna contrasenia se loguea en texto plano en ningun punto, ni
        # siquiera en modo test, y un seed no es una excepcion: su salida
        # termina en la consola de un deploy o en el historial de una terminal.
        # Quien la necesita la tiene en el README.
        print(f"\nAdministrador General creado: {resultado.email}")
        print("La contrasenia esta en README.md, en la seccion 'Usuarios de prueba'.")
    else:
        print(f"\n{resultado.email} ya existia. No se modifico nada.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

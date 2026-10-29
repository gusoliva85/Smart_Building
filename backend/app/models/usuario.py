"""Usuario y su vinculo N:M con los edificios asignados.

Dos tablas viven aca:

- ``Usuario``            — quien entra al sistema y con que rol.
- ``AsignacionEdificio`` — los edificios de un rol `seguridad` o `auditor`.

La segunda existe porque la decision de `F1-T02` encontro que los ocho roles no
tienen todos la misma clase de vinculo con un edificio, y que cada clase tiene
que vivir en UN solo lugar:

| Naturaleza del vinculo        | Roles                            | Donde vive            |
|-------------------------------|----------------------------------|-----------------------|
| Derivado de un dato existente | propietario, inquilino, proveedor| la unidad, la orden   |
| Responsabilidad unica (1:1)   | admin_consorcio, encargado       | columnas de edificios |
| Asignacion N:M                | seguridad, auditor               | esta tabla            |
| Sin vinculo                   | admin_general                    | toda la cartera       |

`AsignacionEdificio` NO es una tabla puente generica para los ocho roles. Si lo
fuera, duplicaria la verdad: el vinculo real de un propietario es su unidad, y
guardar ademas una fila diciendo "alcanza el edificio X" crea dos fuentes del
mismo hecho, que en algun momento divergen.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import expression

from app.database import Base
from app.services import autorizacion

# La lista de roles validos NO se repite escrita a mano: se arma desde la misma
# tupla que usa la autorizacion. Si se escribiera dos veces, en algun momento
# una copia quedaria atras y la base aceptaria un rol que la aplicacion no
# conoce, o al reves — y ese desfasaje no da error, da comportamiento raro.
_ROLES_PARA_CHECK = ", ".join(f"'{rol}'" for rol in autorizacion.ROLES)


class Usuario(Base):
    """Una persona con acceso al sistema.

    La baja es SIEMPRE logica (`activo = False`), nunca un DELETE: un usuario
    borrado fisicamente se lleva puesta la trazabilidad de todo lo que cargo
    (gastos, reclamos, pagos), y esos registros tienen que seguir diciendo
    quien los creo incluso anios despues de que la persona dejo el consorcio.
    """

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    nombre: Mapped[str] = mapped_column(String(120), nullable=False)

    # Es la credencial de login, asi que la unicidad la garantiza la base y no
    # una consulta previa en el endpoint: entre el "¿existe?" y el INSERT hay
    # una ventana en la que otro request puede insertar el mismo email.
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # Solo el hash. La contrasenia en texto plano no se guarda, no se loguea y
    # no se devuelve en ninguna respuesta, en ningun entorno. El hasheo lo hace
    # `core/security.py` (F1-T04); el largo alcanza para bcrypt y para argon2
    # si alguna vez se cambia de algoritmo.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    rol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    telefono: Mapped[str | None] = mapped_column(String(40), nullable=True)

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=expression.true(),
    )

    # server_default y no default de Python: asi la fecha la pone el motor, es
    # consistente para todas las filas insertadas en la misma transaccion, y la
    # columna se puede agregar a una tabla con filas (ver core/migraciones.py).
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        # El rol se valida DOS veces, a proposito y en dos capas distintas:
        # en Pydantic, para que el error sea un 422 que dice que roles existen;
        # y aca, para que la base sea la ultima linea de defensa. Un INSERT que
        # no pase por la API — un script de carga, un arreglo a mano en una
        # consola de psql — igual no puede escribir un rol inexistente.
        CheckConstraint(f"rol IN ({_ROLES_PARA_CHECK})", name="ck_usuarios_rol_valido"),
    )

    def __repr__(self) -> str:
        return f"<Usuario {self.id} {self.email} ({self.rol})>"


class AsignacionEdificio(Base):
    """Un edificio asignado a un usuario de rol `seguridad` o `auditor`.

    Hace falta que sea N:M y no una columna mas en `edificios` porque un
    edificio tiene un solo administrador y un solo encargado, pero puede tener
    VARIOS agentes de seguridad (son turnos), y un auditor puede auditar varios
    edificios. Nada de eso entra en una columna.
    """

    __tablename__ = "asignacion_edificio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # ondelete no se declara: los usuarios no se borran, se desactivan. Si una
    # asignacion tuviera que dejar de valer, se borra la asignacion.
    usuario_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=False,
        index=True,
    )

    # CLAVE FORANEA DIFERIDA, y no por olvido: `edificios` todavia no existe
    # como modelo — nace en F1-T18 — y una FK contra una tabla ausente hace
    # fallar la creacion del esquema entero al arrancar.
    #
    # Esto NO repite la deuda de `activo_id` y `proveedor_id` (seccion 4 del
    # Roadmap), porque esas quedaron sin FK con datos ya cargados encima, y
    # agregarsela despues no lo resuelve el mecanismo aditivo de migraciones.
    # Aca la tabla esta VACIA durante toda la ventana: lo primero que escribe
    # una asignacion es la pantalla de F11-T05. Formalizar la FK en F1-T18 es
    # entonces recrear una tabla vacia, no migrar datos.
    edificio_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        # Asignar dos veces el mismo usuario al mismo edificio no es un error
        # que valga la pena manejar en la aplicacion: la fila repetida no
        # significa nada distinto de la primera, y dejarla entrar obligaria a
        # desduplicar en cada consulta de alcance.
        UniqueConstraint(
            "usuario_id",
            "edificio_id",
            name="uq_asignacion_edificio_usuario_edificio",
        ),
    )

    def __repr__(self) -> str:
        return f"<AsignacionEdificio usuario={self.usuario_id} edificio={self.edificio_id}>"

"""El edificio: la unidad de consorcio sobre la que gira todo el sistema.

Casi todo lo demas cuelga de aca — pisos, departamentos, cocheras, espacios
comunes, gastos, expensas, reclamos, activos — y los alcances de la
autorizacion se resuelven contra esta tabla: "el edificio del que es
responsable" (Encargado, Administrador de Consorcio) sale de las dos columnas
de responsables que estan mas abajo.

====================================================================
EL ERROR QUE ESTE MODELO EXISTE PARA NO REPETIR: `encargado_id`
====================================================================

En la iteracion anterior esta tabla **no tenia `encargado_id`**. El rol
Encargado existia desde el primer dia, con alcance de edificio declarado en la
matriz de autorizacion, pero no habia absolutamente nada que vinculara a un
encargado con un edificio concreto. La consecuencia no aparecio hasta la
Fase 3, cuando hubo que responder "¿que reclamos puede gestionar este
encargado?" y resulto que la pregunta no tenia respuesta posible.

La leccion quedo como regla del proyecto: **un rol con alcance de edificio
necesita su vinculo declarado en el modelo, en la misma tarea que crea el
modelo, no cuando aparezca la pantalla que lo necesita.** `F1-T02` ya clasifico
los ocho roles por la naturaleza de su vinculo (ver `models/usuario.py`), y los
dos que son responsabilidad unica 1:1 —administrador de consorcio y encargado—
van aca, como columnas, porque un edificio tiene uno de cada uno.
"""

import json
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    or_,
    text,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import expression

from app.database import Base
from app.services import autorizacion

# El default de `roles_habilitados` se escribe UNA vez y se usa en los dos
# lugares que tienen que coincidir: el default de Python (lo que pone la
# aplicacion) y el server_default (lo que pone la base si la fila se inserta
# desde un script o una consola). Si se escribieran por separado, un dia una
# fila nacida por cada camino tendria una lista distinta.
_ROLES_HABILITADOS_POR_DEFECTO = json.dumps(list(autorizacion.ROLES_HABILITABLES))

# Un CBU argentino tiene exactamente 22 digitos. No es una longitud maxima
# arbitraria: es el formato, y uno de 21 digitos es un CBU mal copiado, no un
# CBU corto.
LARGO_CBU = 22

DIAS_VENCIMIENTO_POR_DEFECTO = 10
"""El dia del mes en que vencen las expensas si nadie configura otra cosa.

Diez es lo habitual en la practica administrativa. Se edita por edificio en
`F1-T22`; esta aca para que un edificio recien creado tenga una fecha de
vencimiento valida y no un `NULL` que haya que preguntarle a cada calculo.
"""


class Edificio(Base):
    """Un consorcio con su direccion, sus responsables y su configuracion.

    La baja es logica (`activo = False`), igual que en `Usuario` y por el mismo
    motivo: un edificio borrado fisicamente se lleva puesta la historia de
    expensas, pagos y reclamos de todos sus propietarios, que tiene que seguir
    existiendo anios despues de que la administracion deje de atenderlo.
    """

    __tablename__ = "edificios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    nombre: Mapped[str] = mapped_column(String(160), nullable=False)

    # -------------------------------------------------------- ubicacion ----

    direccion: Mapped[str] = mapped_column(String(255), nullable=False)

    # Codigo postal y no ciudad ni provincia: es mas preciso para geocodificar
    # (`F1-T25` consulta Nominatim con direccion + CP) y alcanza para todo lo
    # que la plataforma hace con la ubicacion. Guardar ademas ciudad y
    # provincia seria guardar tres veces un dato que el CP ya determina.
    cp: Mapped[str] = mapped_column(String(16), nullable=False)

    # Las dos nacen en NULL y se completan con la geocodificacion. Son
    # anulables a proposito: `F1-T25` fija que una direccion que Nominatim no
    # encuentra **avisa pero no bloquea el alta**, porque una calle nueva puede
    # no estar indexada todavia y eso no es motivo para no poder cargar un
    # edificio que existe.
    #
    # Numeric y no Float: seis decimales de grado son unos 11 centimetros, mas
    # que suficiente para ubicar un edificio, y un decimal exacto se compara y
    # se guarda sin la sorpresa de que 0,1 no exista en binario.
    latitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)

    # -------------------------------------------------------- identidad ----

    # El CUIT del consorcio. Anulable porque al dar de alta un edificio no
    # siempre se tiene a mano, y no es unico a proposito: un mismo consorcio
    # puede administrar dos torres cargadas como dos edificios distintos, y
    # ponerle una restriccion de unicidad bloquearia ese caso real.
    cuit: Mapped[str | None] = mapped_column(String(13), nullable=True)

    # ----------------------------------------------------- responsables ----

    # Las dos apuntan a `usuarios` y las dos son anulables: un edificio recien
    # cargado puede no tener todavia a quien lo administra dado de alta como
    # usuario, y hay edificios sin encargado.
    #
    # Que apunten a un usuario con el ROL correcto no lo puede garantizar la
    # base: seria un CHECK que consulta otra tabla, que ningun motor permite.
    # Lo valida `F1-T22` al grabar. Es una de las poquisimas reglas de este
    # modelo que no tiene su red abajo, y conviene saberlo.
    admin_consorcio_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )

    encargado_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )

    # `foreign_keys` es obligatorio aca: hay DOS claves foraneas a `usuarios` y
    # SQLAlchemy no puede adivinar cual corresponde a cual relacion. Sin esto
    # el error no aparece al importar el modulo, aparece al primer uso de la
    # relacion y con un mensaje que no menciona este archivo.
    #
    # Son de un solo lado (sin `back_populates`): `Usuario` no necesita saber
    # de que edificios es responsable, y agregarselo obligaria a declarar dos
    # colecciones mas en un modelo que no las usa.
    admin_consorcio = relationship("Usuario", foreign_keys=[admin_consorcio_id])
    encargado = relationship("Usuario", foreign_keys=[encargado_id])

    # ------------------------------------------------------- estructura ----

    # El `order_by` va declarado aca y no repetido en cada consulta: un piso 10
    # dibujado antes del 2 no es un detalle estetico en una pantalla cuyo
    # trabajo es parecerse a un edificio.
    #
    # NO se declara `cascade="all, delete-orphan"`, y es a proposito. Suena
    # comodo —sacar un piso de la lista lo borraria— y es justo lo que no
    # conviene: un departamento puede tener expensas y pagos apuntandole, asi
    # que darlo de baja no es un borrado silencioso sino una decision con
    # consecuencias, y la toma `F1-T23`. Con el comportamiento por defecto,
    # intentar borrar un piso que todavia tiene departamentos falla
    # ruidosamente, que es exactamente lo que corresponde que pase.
    pisos = relationship(
        "Piso",
        back_populates="edificio",
        order_by="Piso.orden",
    )
    cocheras = relationship(
        "Cochera",
        back_populates="edificio",
        order_by="Cochera.numero",
    )
    espacios_comunes = relationship(
        "EspacioComun",
        back_populates="edificio",
        order_by="EspacioComun.nombre",
    )

    # ----------------------------------------------------- configuracion ---

    dias_vencimiento_expensas: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text(str(DIAS_VENCIMIENTO_POR_DEFECTO)),
    )

    # Numeric y no Float porque es un porcentaje que multiplica deuda real.
    # Cinco digitos con dos decimales llegan hasta 999,99: el CHECK lo limita a
    # 100, pero el tipo deja margen por si alguna vez se guarda un recargo
    # acumulado.
    recargo_mora_porcentual: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        server_default=text("0"),
    )

    contacto_emergencia_nombre: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )
    contacto_emergencia_telefono: Mapped[str | None] = mapped_column(
        String(40), nullable=True
    )

    # Que roles tienen sentido en ESTE edificio. La lista valida es
    # `autorizacion.ROLES_HABILITABLES` y el default es "todos" — ver el
    # docstring de esa constante para el porque.
    #
    # DOS CUIDADOS con una columna JSON:
    #
    # 1. SQLAlchemy no detecta una modificacion EN EL LUGAR. `edificio
    #    .roles_habilitados.remove("encargado")` no se guarda nunca y no da
    #    error. Hay que ASIGNAR una lista nueva. Se resuelve asi, y no con
    #    `MutableList`, porque el unico escritor es el PATCH de `F1-T22`, que
    #    recibe la lista completa y la asigna entera.
    # 2. Lo que la lista contiene no lo valida la base: un CHECK no puede leer
    #    adentro de un JSON de forma portable entre SQLite y PostgreSQL. Lo
    #    valida el esquema Pydantic de `F1-T22` contra `ROLES_HABILITABLES`.
    roles_habilitados: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: list(autorizacion.ROLES_HABILITABLES),
        server_default=text(f"'{_ROLES_HABILITADOS_POR_DEFECTO}'"),
    )

    # ------------------------------------------- cuenta del consorcio ------

    # Los dos son texto y no numero. El CBU tiene 22 digitos y puede arrancar
    # con cero; guardado como entero perderia ese cero y dejaria de ser un CBU.
    cbu: Mapped[str | None] = mapped_column(String(LARGO_CBU), nullable=True)
    alias_cbu: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # ------------------------------------------------------------ estado ---

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=expression.true(),
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        # El dia de vencimiento es un dia del mes. 0 y 32 no son fechas, y un
        # 0 silencioso rompe el calculo de la primera expensa que se genere.
        CheckConstraint(
            "dias_vencimiento_expensas >= 1 AND dias_vencimiento_expensas <= 31",
            name="ck_edificios_dias_vencimiento",
        ),
        # Un recargo negativo seria un descuento por pagar tarde. Mas de 100%
        # seria mas que duplicar la deuda de un mes.
        CheckConstraint(
            "recargo_mora_porcentual >= 0 AND recargo_mora_porcentual <= 100",
            name="ck_edificios_recargo_mora",
        ),
        # `length()` existe igual en SQLite y en PostgreSQL. Un CBU de 21
        # digitos es uno mal copiado, y el error tiene que aparecer al
        # guardarlo, no cuando un propietario intente transferir.
        CheckConstraint(
            f"cbu IS NULL OR length(cbu) = {LARGO_CBU}",
            name="ck_edificios_cbu_largo",
        ),
        # Coordenadas fuera de rango son un error de geocodificacion, no una
        # ubicacion rara. Una latitud de 200 pone el edificio en ningun lado y
        # el mapa de `F1-T25` no mostraria nada sin decir por que.
        CheckConstraint(
            "latitud IS NULL OR (latitud >= -90 AND latitud <= 90)",
            name="ck_edificios_latitud",
        ),
        CheckConstraint(
            "longitud IS NULL OR (longitud >= -180 AND longitud <= 180)",
            name="ck_edificios_longitud",
        ),
        # Un usuario tiene UN rol, asi que la misma persona no puede ser a la
        # vez administrador de consorcio y encargado. Si las dos columnas
        # apuntan al mismo id, alguno de los dos roles esta mal.
        CheckConstraint(
            "admin_consorcio_id IS NULL "
            "OR encargado_id IS NULL "
            "OR admin_consorcio_id <> encargado_id",
            name="ck_edificios_responsables_distintos",
        ),
    )

    def __repr__(self) -> str:
        return f"<Edificio {self.id} {self.nombre}>"


# ==========================================================================
# LA ESTRUCTURA DEL EDIFICIO (F1-T19)
# ==========================================================================
#
# Cuatro tablas que cuelgan del edificio. Las cuatro nacen VACIAS de datos
# cargados a mano: `F1-T20` crea pisos y departamentos a partir de "cantidad de
# pisos por unidades por piso" usando `services/finanzas.generar_estructura()`,
# y el resto —metros cuadrados, propietario, coeficiente— se completa despues,
# unidad por unidad.
#
# Ninguna de las cuatro tiene `activo`: la baja de un piso o de un departamento
# es un borrado real y la decide `F1-T23`, que tiene que mirar primero si hay
# expensas o pagos apuntandole.


class Piso(Base):
    """Un piso del edificio.

    `numero` y `orden` son dos cosas distintas y por eso son dos columnas: el
    nombre de un piso y su lugar en la pila no siempre coinciden. Una planta
    baja es el piso de mas abajo y se llama 0 (o no se llama con un numero),
    un entrepiso va entre el 0 y el 1, y hay edificios que saltean el 13. Con
    una sola columna habria que elegir entre dibujar el edificio en el orden
    correcto o llamar a cada piso como lo llaman sus vecinos.

    `generar_estructura()` los crea con `numero == orden`, que es el caso
    parejo y lo unico que se puede saber sin preguntar; corregir el nombre de
    un piso despues es trabajo de `F1-T23`.
    """

    __tablename__ = "pisos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    edificio_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("edificios.id"),
        nullable=False,
        index=True,
    )

    numero: Mapped[int] = mapped_column(Integer, nullable=False)

    orden: Mapped[int] = mapped_column(Integer, nullable=False)

    edificio = relationship("Edificio", back_populates="pisos")

    # Se ordena por `identificador` y no por un campo de orden propio porque
    # el Roadmap no le declara uno a `Departamento`. Tiene una consecuencia
    # que conviene saber: con mas de 26 unidades en un mismo piso, el orden
    # alfabetico pone "1AA" antes de "1B". Con 26 o menos —todos los casos
    # reales— el orden es el correcto.
    departamentos = relationship(
        "Departamento",
        back_populates="piso",
        order_by="Departamento.identificador",
    )

    __table_args__ = (
        # Dos pisos 3 en el mismo edificio es un error de carga, no una
        # estructura rara. En edificios distintos, obviamente, se repite.
        UniqueConstraint("edificio_id", "numero", name="uq_pisos_edificio_numero"),
        UniqueConstraint("edificio_id", "orden", name="uq_pisos_edificio_orden"),
    )

    def __repr__(self) -> str:
        return f"<Piso {self.id} n={self.numero} edificio={self.edificio_id}>"


class Departamento(Base):
    """Una unidad funcional: lo que paga expensas y lo que tiene un coeficiente.

    Es la tabla mas referenciada del sistema despues de `usuarios`: le apuntan
    las expensas por unidad, los pagos, los reclamos y las cocheras fijas.
    """

    __tablename__ = "departamentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    piso_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pisos.id"),
        nullable=False,
        index=True,
    )

    # "1A", "2B", "PB-C". Texto y no numero porque casi nunca es un numero.
    identificador: Mapped[str] = mapped_column(String(20), nullable=False)

    # Nace sin cargar: la estructura automatica no puede inventar superficies.
    # Es, ademas, lo que necesita el atajo de coeficientes por m2, asi que un
    # edificio sin m2 cargados solo puede usar el atajo de partes iguales.
    m2: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    # ------------------------------------------------------- quien la usa ---

    # Un propietario puede tener VARIAS unidades, incluso en edificios
    # distintos: no lleva restriccion de unicidad.
    propietario_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )

    # Un inquilino tiene UNA sola, y eso lo garantiza la base con una
    # restriccion de unicidad. No es una limitacion arbitraria: simplifica
    # toda la interfaz del residente. Donde el propietario a veces necesita
    # elegir de cual de sus unidades esta hablando, el inquilino nunca.
    #
    # La unicidad sobre una columna anulable permite muchos NULL —tanto en
    # SQLite como en PostgreSQL—, asi que no obliga a que toda unidad tenga
    # inquilino: solo impide que la misma persona figure en dos.
    inquilino_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )

    # --------------------------------------------------- el coeficiente ----

    # Tres decimales, los mismos que reparte `services/finanzas.py`. Nace en
    # NULL a proposito: un coeficiente inventado es peor que uno ausente,
    # porque el ausente lo encuentra la validacion antes de generar una
    # expensa y el inventado reparte plata mal sin que nadie lo note.
    coeficiente: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 3), nullable=True
    )

    # ------------------------------------------------------ relaciones -----

    piso = relationship("Piso", back_populates="departamentos")

    # `foreign_keys` obligatorio: dos claves foraneas a `usuarios`.
    propietario = relationship("Usuario", foreign_keys=[propietario_id])
    inquilino = relationship("Usuario", foreign_keys=[inquilino_id])

    cocheras = relationship("Cochera", back_populates="departamento")

    # --------------------------------------------------------- ocupado -----

    @hybrid_property
    def ocupado(self) -> bool:
        """¿La unidad esta ocupada? Se DERIVA, no se carga a mano.

        El Roadmap lo pide explicitamente y vale escribir por que: una columna
        booleana que hay que mantener al dia es una columna que algun dia dice
        que la unidad esta vacia mientras tiene un inquilino con un contrato
        firmado. El dato ya esta —hay propietario o hay inquilino—, asi que
        guardarlo aparte es guardar dos veces el mismo hecho, y cuando un
        hecho esta guardado dos veces es cuestion de tiempo que las dos copias
        no coincidan.

        Es `hybrid_property` y no una `property` comun porque asi tambien se
        puede filtrar en SQL (`select(Departamento).where(Departamento.ocupado)`)
        sin traer las filas a Python para descartarlas.
        """
        return self.propietario_id is not None or self.inquilino_id is not None

    @ocupado.inplace.expression
    @classmethod
    def _ocupado_en_sql(cls):
        return or_(
            cls.propietario_id.is_not(None),
            cls.inquilino_id.is_not(None),
        )

    __table_args__ = (
        UniqueConstraint(
            "piso_id",
            "identificador",
            name="uq_departamentos_piso_identificador",
        ),
        # La regla "un inquilino, una sola unidad", garantizada por la base.
        UniqueConstraint("inquilino_id", name="uq_departamentos_inquilino"),
        # El coeficiente es un porcentaje. Fuera de 0-100 no es un numero raro,
        # es un prorrateo que reparte de mas o de menos entre propietarios
        # reales.
        CheckConstraint(
            "coeficiente IS NULL OR (coeficiente >= 0 AND coeficiente <= 100)",
            name="ck_departamentos_coeficiente",
        ),
        # Una unidad de 0 m2 no existe, y un 0 silencioso rompe el atajo de
        # coeficientes por superficie.
        CheckConstraint("m2 IS NULL OR m2 > 0", name="ck_departamentos_m2"),
        # Nadie se alquila su propia unidad. Un usuario tiene un solo rol, asi
        # que si las dos columnas apuntan a la misma persona, alguna esta mal.
        CheckConstraint(
            "propietario_id IS NULL "
            "OR inquilino_id IS NULL "
            "OR propietario_id <> inquilino_id",
            name="ck_departamentos_propietario_distinto_inquilino",
        ),
    )

    def __repr__(self) -> str:
        return f"<Departamento {self.id} {self.identificador}>"


# Los dos tipos de cochera. Son constantes y no texto suelto por el mismo
# motivo que los roles: el CHECK de la tabla y la validacion de Pydantic se
# arman desde aca, asi que no pueden discrepar.
COCHERA_FIJA = "fija"
COCHERA_ROTATIVA = "rotativa"

TIPOS_COCHERA: tuple[str, ...] = (COCHERA_FIJA, COCHERA_ROTATIVA)

_TIPOS_PARA_CHECK = ", ".join(f"'{tipo}'" for tipo in TIPOS_COCHERA)


class Cochera(Base):
    """Una cochera del edificio, fija o rotativa.

    Cuelga del edificio y no del piso: una cochera esta en la planta baja o en
    un subsuelo que no es un piso de departamentos, y asignarla a un piso
    obligaria a inventar pisos que no tienen unidades.
    """

    __tablename__ = "cocheras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    edificio_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("edificios.id"),
        nullable=False,
        index=True,
    )

    # Texto y no entero: en la practica las cocheras estan rotuladas, y el
    # rotulo dice "S2-14" o "12 bis" tan seguido como dice "12".
    numero: Mapped[str] = mapped_column(String(20), nullable=False)

    tipo: Mapped[str] = mapped_column(String(16), nullable=False)

    # Anulable: una cochera fija puede estar sin asignar, y una rotativa no se
    # asigna nunca por definicion.
    departamento_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("departamentos.id"),
        nullable=True,
        index=True,
    )

    edificio = relationship("Edificio", back_populates="cocheras")
    departamento = relationship("Departamento", back_populates="cocheras")

    __table_args__ = (
        UniqueConstraint(
            "edificio_id", "numero", name="uq_cocheras_edificio_numero"
        ),
        CheckConstraint(
            f"tipo IN ({_TIPOS_PARA_CHECK})", name="ck_cocheras_tipo"
        ),
        # Una cochera rotativa con un departamento asignado es una
        # contradiccion: rotativa significa justamente que no es de nadie en
        # particular. Que lo impida la base evita que una pantalla de
        # asignacion mal hecha genere un dato que despues nadie entiende.
        CheckConstraint(
            f"tipo = '{COCHERA_FIJA}' OR departamento_id IS NULL",
            name="ck_cocheras_rotativa_sin_departamento",
        ),
    )

    def __repr__(self) -> str:
        return f"<Cochera {self.id} {self.numero} ({self.tipo})>"


class EspacioComun(Base):
    """Un espacio comun del edificio: SUM, parrilla, pileta, laundry.

    Se usa en dos lugares bien distintos, y conviene tenerlo presente desde
    aca: es lo que se reserva (Fase 6) y es uno de los tres destinos posibles
    de un reclamo —una unidad, un espacio comun, o el edificio en general—.

    **Verlo NO puede ser exclusivo del administrador.** En la iteracion
    anterior el listado quedo admin-only por error y dejo sin poder reportar un
    reclamo sobre un espacio comun a Propietario, Inquilino y Encargado, que
    son justamente los que estan ahi. Se descubrio recien en la Fase 3. Crear
    un espacio comun si es exclusivo del administrador; verlo, no. Queda
    anotado aca porque el permiso se escribe en `F1-T23`, y para entonces el
    motivo ya no va a estar a la vista.
    """

    __tablename__ = "espacios_comunes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    edificio_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("edificios.id"),
        nullable=False,
        index=True,
    )

    nombre: Mapped[str] = mapped_column(String(120), nullable=False)

    # Cuantas personas admite a la vez. Anulable: hay espacios sin un limite
    # declarado (un laundry con dos lavarropas no tiene aforo), y un 0 como
    # "sin dato" seria un espacio que no admite a nadie.
    capacidad: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Texto largo y libre: son las reglas del reglamento interno, que cada
    # consorcio escribe a su manera. Un campo estructurado aca seria adivinar
    # una forma que no existe.
    reglas_uso: Mapped[str | None] = mapped_column(Text, nullable=True)

    edificio = relationship("Edificio", back_populates="espacios_comunes")

    __table_args__ = (
        # Dos "Parrilla" en el mismo edificio no se distinguen en una lista de
        # reserva. Si de verdad hay dos, se llaman "Parrilla 1" y "Parrilla 2".
        UniqueConstraint(
            "edificio_id", "nombre", name="uq_espacios_comunes_edificio_nombre"
        ),
        CheckConstraint(
            "capacidad IS NULL OR capacidad > 0",
            name="ck_espacios_comunes_capacidad",
        ),
    )

    def __repr__(self) -> str:
        return f"<EspacioComun {self.id} {self.nombre}>"

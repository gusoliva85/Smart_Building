"""Modelos del dominio "Edificios" — Documento General, sección 5;
Documento Técnico, sección 5.1. Un solo archivo para las cinco entidades
estructurales (`Edificio`, `Piso`, `Departamento`, `Cochera`,
`EspacioComun`), tal como lo fija la sección 2.3 del Documento Técnico
(un archivo por dominio en `models/`, no uno por tabla).
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Edificio(Base):
    """Registro que se crea una sola vez por cada edificio nuevo que se
    suma a la plataforma. Con el modelo `Edificio` ya existiendo, queda
    resuelta la referencia que `UsuarioEdificio` (models/usuario_edificio.py)
    dejó pendiente unas tareas atrás."""

    __tablename__ = "edificios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    direccion = Column(String, nullable=False)
    cp = Column(String, nullable=True)  # código postal — reemplaza a "ciudad" (más preciso para geocodificar)
    cuit = Column(String, nullable=True)

    # Geocodificados en el frontend al completar Dirección + CP (Nominatim/
    # OpenStreetMap, Documento Técnico sección 7) y guardados tal cual los
    # devuelve el alta — el backend no vuelve a geocodificar, solo persiste.
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)

    # Nullable por ahora: la validación de que ese usuario tenga rol
    # admin_consorcio es una regla de aplicación (se aplica en el endpoint
    # de alta, próxima tarea), no algo que un CHECK de SQLite pueda
    # expresar de forma simple contra otra tabla.
    admin_consorcio_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    dias_vencimiento_expensas = Column(Integer, nullable=False, default=10)
    recargo_mora_porcentual = Column(Integer, nullable=False, default=0)  # % simple por mes de atraso

    # Configuración (Documento General, sección 5.2) — se completan recién
    # en esta tarea, después del alta. `roles_habilitados` se guarda como
    # texto separado por comas (SQLite no tiene un tipo lista nativo);
    # NULL significa "todos los roles habilitados", el default real.
    contacto_emergencia_nombre = Column(String, nullable=True)
    contacto_emergencia_telefono = Column(String, nullable=True)
    roles_habilitados = Column(Text, nullable=True)

    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relaciones ORM — se agregan recién ahora, que el endpoint de alta
    # (próxima tarea) necesita devolver el edificio con su estructura
    # anidada en la misma respuesta. `order_by` deja el orden de apilado
    # (Documento Técnico, sección 1.3.8) resuelto en la propia consulta.
    pisos = relationship("Piso", backref="edificio", order_by="Piso.orden")


class Piso(Base):
    """Pertenece a un edificio. `numero` es el nombre/identificador que ve
    el usuario (típicamente "1", "2", ... aunque el formato admite a futuro
    "PB" o "Subsuelo"); `orden` es el entero que decide el apilado real en
    el Dashboard Visual (Documento Técnico, sección 1.3.8) — normalmente
    coincide con `numero`, pero se separan porque el nombre visible y el
    orden de apilado no tienen por qué ser siempre el mismo número."""

    __tablename__ = "pisos"

    id = Column(Integer, primary_key=True, index=True)
    edificio_id = Column(Integer, ForeignKey("edificios.id"), nullable=False)
    numero = Column(String, nullable=False)
    orden = Column(Integer, nullable=False)

    departamentos = relationship("Departamento", backref="piso", order_by="Departamento.identificador")


class Departamento(Base):
    """Pertenece a un piso. `propietario_id`/`inquilino_id` son opcionales
    porque, al generarse la estructura vacía del edificio (Documento
    General, sección 5.1), todavía no tienen a nadie asignado."""

    __tablename__ = "departamentos"

    id = Column(Integer, primary_key=True, index=True)
    piso_id = Column(Integer, ForeignKey("pisos.id"), nullable=False)
    identificador = Column(String, nullable=False)  # ej. "7A", igual a services/edificios.py
    m2 = Column(Float, nullable=True)
    propietario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    inquilino_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    ocupado = Column(Boolean, nullable=False, default=False)  # "estado ocupacional" del Documento Técnico


class Cochera(Base):
    __tablename__ = "cocheras"
    __table_args__ = (CheckConstraint("tipo IN ('fija', 'rotativa')", name="ck_cocheras_tipo_valido"),)

    id = Column(Integer, primary_key=True, index=True)
    edificio_id = Column(Integer, ForeignKey("edificios.id"), nullable=False)
    numero = Column(String, nullable=False)
    tipo = Column(String, nullable=False)
    departamento_id = Column(Integer, ForeignKey("departamentos.id"), nullable=True)


class EspacioComun(Base):
    __tablename__ = "espacios_comunes"

    id = Column(Integer, primary_key=True, index=True)
    edificio_id = Column(Integer, ForeignKey("edificios.id"), nullable=False)
    nombre = Column(String, nullable=False)  # ej. "SUM", "Parrilla", "Gimnasio"
    capacidad = Column(Integer, nullable=True)
    reglas_uso = Column(Text, nullable=True)

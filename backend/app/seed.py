"""Script de inicialización: crea el primer Administrador General.

Como no existe un registro público (los usuarios los da de alta un
administrador, no se anota cualquiera), hace falta un comando que cree, la
primera vez que se levanta el proyecto, un usuario Administrador General
inicial con credenciales conocidas — de otro modo nadie podría loguearse
nunca (Documento Técnico, sección 3.2).

Uso: python -m app.seed
Es seguro correrlo más de una vez — si el usuario ya existe, no hace nada.
"""

import app.models  # noqa: F401 — registra todos los modelos en Base.metadata
from app.database import Base, SesionLocal, engine
from app.core.security import hashear_password
from app.models.usuario import Usuario

EMAIL_ADMIN_GENERAL = "admin@smartbuilding.test"
PASSWORD_ADMIN_GENERAL = "admin123"  # trivial a propósito: proyecto en modo test


def crear_admin_general():
    Base.metadata.create_all(bind=engine)  # todas las tablas registradas hasta ahora, no solo Usuario

    db = SesionLocal()
    try:
        ya_existe = db.query(Usuario).filter(Usuario.email == EMAIL_ADMIN_GENERAL).first()
        if ya_existe:
            print(f"Ya existe un Administrador General ({EMAIL_ADMIN_GENERAL}) — no se crea de nuevo.")
            return ya_existe

        admin = Usuario(
            nombre="Administrador General",
            email=EMAIL_ADMIN_GENERAL,
            password_hash=hashear_password(PASSWORD_ADMIN_GENERAL),
            rol="admin_general",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"Administrador General creado: {EMAIL_ADMIN_GENERAL}")
        return admin
    finally:
        db.close()


if __name__ == "__main__":
    crear_admin_general()

"""Script de datos de prueba: 10 propietarios y 20 inquilinos con datos
random (nombre, email, teléfono), para tener una base de usuarios más
realista con la que probar el resto de la aplicación (asignaciones,
prorrateo con muchos departamentos reales, listados, etc.) en vez de los
2-3 usuarios de siempre.

Uso: python -m app.seed_propietarios_inquilinos
Es seguro correrlo más de una vez — nunca borra usuarios existentes, y
si por casualidad el email random ya existe, lo saltea y genera otro.
No asigna a estos usuarios a ningún departamento — quedan disponibles
para asignar a mano desde `edificios.html` cuando haga falta.
"""

import random

import app.models  # noqa: F401 — registra todos los modelos en Base.metadata
from app.core.security import hashear_password
from app.database import Base, SesionLocal, engine
from app.models.usuario import Usuario

PASSWORD_COMPARTIDA = "test1234"  # trivial a propósito, mismo criterio que el resto de los usuarios de prueba

NOMBRES = [
    "Martina", "Lucas", "Sofía", "Mateo", "Valentina", "Joaquín", "Camila", "Benjamín",
    "Emma", "Tomás", "Julieta", "Santiago", "Delfina", "Bautista", "Catalina", "Agustín",
    "Isabella", "Franco", "Renata", "Ignacio", "Guadalupe", "Nicolás", "Pilar", "Facundo",
    "Milagros", "Gonzalo", "Antonella", "Máximo", "Victoria", "Lautaro",
]

APELLIDOS = [
    "González", "Rodríguez", "Fernández", "López", "Martínez", "García", "Pérez", "Sánchez",
    "Romero", "Sosa", "Torres", "Álvarez", "Ruiz", "Flores", "Acosta", "Benítez", "Medina",
    "Herrera", "Aguirre", "Vega", "Molina", "Ortiz", "Silva", "Cabrera", "Rojas", "Núñez",
    "Domínguez", "Castro", "Ibáñez", "Paz",
]


def _generar_personas(cantidad, usados):
    personas = []
    nombres_disponibles = random.sample(NOMBRES, len(NOMBRES))
    apellidos_disponibles = random.sample(APELLIDOS, len(APELLIDOS))
    intentos = 0
    while len(personas) < cantidad and intentos < cantidad * 20:
        intentos += 1
        nombre = random.choice(nombres_disponibles)
        apellido = random.choice(apellidos_disponibles)
        nombre_completo = f"{nombre} {apellido}"
        base_email = f"{nombre}.{apellido}".lower().replace(" ", "")
        for letra in "áéíóúñ":
            base_email = base_email.replace(letra, {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}[letra])
        email = f"{base_email}@ejemplo.test"
        if email in usados:
            email = f"{base_email}{random.randint(2, 99)}@ejemplo.test"
            if email in usados:
                continue
        usados.add(email)
        telefono = f"11-{random.randint(3000, 6999)}-{random.randint(1000, 9999)}"
        personas.append((nombre_completo, email, telefono))
    return personas


def crear_propietarios_e_inquilinos():
    Base.metadata.create_all(bind=engine)

    db = SesionLocal()
    try:
        emails_existentes = {u.email for u in db.query(Usuario.email).all()}

        propietarios = _generar_personas(10, set(emails_existentes))
        inquilinos = _generar_personas(20, set(emails_existentes) | {p[1] for p in propietarios})

        creados = 0
        for nombre, email, telefono in propietarios:
            if email in emails_existentes:
                continue
            db.add(Usuario(
                nombre=nombre, email=email, password_hash=hashear_password(PASSWORD_COMPARTIDA),
                rol="propietario", telefono=telefono,
            ))
            creados += 1

        for nombre, email, telefono in inquilinos:
            if email in emails_existentes:
                continue
            db.add(Usuario(
                nombre=nombre, email=email, password_hash=hashear_password(PASSWORD_COMPARTIDA),
                rol="inquilino", telefono=telefono,
            ))
            creados += 1

        db.commit()
        print(f"Creados {creados} usuarios nuevos ({len(propietarios)} propietarios, {len(inquilinos)} inquilinos).")
        print(f"Password compartida de prueba: {PASSWORD_COMPARTIDA}")
        print("\nPropietarios:")
        for nombre, email, telefono in propietarios:
            print(f"  {nombre} <{email}> {telefono}")
        print("\nInquilinos:")
        for nombre, email, telefono in inquilinos:
            print(f"  {nombre} <{email}> {telefono}")
    finally:
        db.close()


if __name__ == "__main__":
    crear_propietarios_e_inquilinos()

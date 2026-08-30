# SMART Building

Plataforma de gestión y visualización integral de edificios/consorcios —
centraliza comunicación, administración financiera, mantenimiento, reclamos
y seguridad edilicia, con un dashboard visual que muestra el estado del
edificio de un vistazo.

- **Qué es y por qué** → [`documentacion/01_Documento_General.md`](documentacion/01_Documento_General.md)
- **Arquitectura, stack, modelo de datos** → [`documentacion/02_Documento_Tecnico.md`](documentacion/02_Documento_Tecnico.md)
- **Fases y tareas, en curso** → [`documentacion/03_Roadmap.md`](documentacion/03_Roadmap.md)
- **Bitácora de desarrollo (qué se hizo, cómo, con qué código)** → `que_hice.html` (abrilo en el navegador)
- **Sistema de diseño obligatorio del frontend** → [`.claude/skills/premium-uiux/`](.claude/skills/premium-uiux/SKILL.md)

## Stack

Backend: Python 3.12 + FastAPI + SQLAlchemy + SQLite.
Frontend: HTML + Tailwind CSS (CDN) + JavaScript vanilla, sin framework ni build.

## Cómo levantar el proyecto en desarrollo

No hay un script de un solo clic — backend y frontend se levantan a mano,
cada uno en su propia terminal.

### 1. Backend (FastAPI)

```bash
cd backend
python -m venv venv                 # solo la primera vez
venv\Scripts\activate                # Windows (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt      # solo la primera vez, o si requirements.txt cambió
python -m app.seed                   # solo la primera vez: crea el Administrador General inicial
python -m uvicorn app.main:app --reload --port 8000
```

Con esto el backend queda en `http://127.0.0.1:8000` y la documentación
interactiva de la API en `http://127.0.0.1:8000/docs`.

### 2. Frontend (estático)

En otra terminal:

```bash
cd frontend
python servidor_dev.py 8090
```

`servidor_dev.py` es un servidor estático que además le dice al navegador
que no guarde nada en caché — usarlo siempre en vez de `python -m http.server`,
para no terminar viendo una versión vieja de un `.js` o `.css` después de un
cambio.

### 3. Abrir la aplicación

`http://127.0.0.1:8090/index.html` — credenciales de prueba en la sección
"Credenciales de prueba" de `que_hice.html`.

## Metodología del proyecto

Una tarea del Roadmap a la vez, en orden **lógica → backend → frontend**,
probada de punta a punta antes de pasar a la siguiente. El detalle completo
de la metodología vive en `documentacion/03_Roadmap.md`.

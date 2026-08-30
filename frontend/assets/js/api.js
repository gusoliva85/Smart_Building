// api.js — wrapper único de fetch() para hablar con el backend.
//
// Centraliza acá lo que, si no, se repetiría en cada pantalla: la URL base
// de la API, agregar el token de sesión, convertir la respuesta a JSON y
// manejar los errores siempre de la misma forma. Cada pantalla usa
// `Api.get(...)`, `Api.post(...)`, etc. en vez de llamar a fetch() directo.

const API_BASE_URL = 'http://127.0.0.1:8000/api';
const CLAVE_TOKEN = 'smart_building_token';

function obtenerToken() {
  return localStorage.getItem(CLAVE_TOKEN);
}

function guardarToken(token) {
  localStorage.setItem(CLAVE_TOKEN, token);
}

function borrarToken() {
  localStorage.removeItem(CLAVE_TOKEN);
}

async function apiFetch(ruta, opciones = {}) {
  const token = obtenerToken();
  const encabezados = { 'Content-Type': 'application/json', ...(opciones.headers || {}) };
  if (token) {
    encabezados['Authorization'] = `Bearer ${token}`;
  }

  let respuesta;
  try {
    respuesta = await fetch(`${API_BASE_URL}${ruta}`, { ...opciones, headers: encabezados });
  } catch (error) {
    // No es un error HTTP (401, 404, ...) sino que ni siquiera hubo respuesta:
    // el backend no está corriendo, o CORS lo bloqueó.
    throw new Error('No se pudo conectar con el servidor. Verificá que el backend esté corriendo.');
  }

  // Sesión inválida o vencida: se limpia el token y se vuelve al login.
  // Excepción a propósito: /auth/login también responde 401 cuando el
  // email o la contraseña están mal — ahí un 401 NO significa "se venció
  // la sesión" (todavía no hay ninguna), significa "credenciales
  // incorrectas". Tratarlo igual mostraría el mensaje equivocado en la
  // pantalla de login, así que esa ruta se deja pasar directo a la rama
  // genérica de abajo, que sí conserva el detalle real del backend.
  if (respuesta.status === 401 && ruta !== '/auth/login') {
    borrarToken();
    const yaEstaEnLogin = location.pathname.endsWith('index.html') || location.pathname === '/';
    if (!yaEstaEnLogin) {
      location.href = 'index.html';
    }
    throw new Error('Sesión inválida o expirada.');
  }

  const tipoContenido = respuesta.headers.get('content-type') || '';
  const cuerpo = tipoContenido.includes('application/json') ? await respuesta.json() : null;

  if (!respuesta.ok) {
    const mensaje = (cuerpo && (cuerpo.detail || cuerpo.mensaje)) || `Error ${respuesta.status}`;
    throw new Error(mensaje);
  }

  return cuerpo;
}

window.Api = {
  get: (ruta) => apiFetch(ruta, { method: 'GET' }),
  post: (ruta, datos) => apiFetch(ruta, { method: 'POST', body: JSON.stringify(datos) }),
  put: (ruta, datos) => apiFetch(ruta, { method: 'PUT', body: JSON.stringify(datos) }),
  patch: (ruta, datos) => apiFetch(ruta, { method: 'PATCH', body: JSON.stringify(datos) }),
  eliminar: (ruta) => apiFetch(ruta, { method: 'DELETE' }),
  guardarToken,
  borrarToken,
  obtenerToken,
};

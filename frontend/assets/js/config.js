// config.js — única fuente de la URL del backend, según el entorno.
//
// Sin build ni variables de entorno del lado del frontend (es HTML/JS
// vanilla, sin Node): la forma más simple de distinguir "estoy en mi
// máquina" de "estoy desplegado" es mirar el propio hostname del navegador.
// Se carga ANTES que api.js en cada página.
const ES_LOCAL = ['localhost', '127.0.0.1'].includes(location.hostname);

const PRODUCCION_API_URL = 'https://smartbuildingbackend.vercel.app/api';

window.API_BASE_URL = ES_LOCAL ? 'http://127.0.0.1:8000/api' : PRODUCCION_API_URL;

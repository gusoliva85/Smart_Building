// mapa.js — geocodificación (Nominatim) + mapa (Leaflet), reutilizable por
// cualquier formulario futuro que necesite ubicar una dirección.
//
// Nominatim (OpenStreetMap) es gratuito y sin API key, pero pide un uso
// respetuoso del servicio (como mucho ~1 request/segundo). Acá se dispara
// solo al perder el foco de un campo (nunca en cada tecla), así que nunca
// se acerca a ese límite aunque alguien complete el formulario rápido.

const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search';

/**
 * Geocodifica "direccion, cp" contra Nominatim. Devuelve el primer
 * resultado ({lat, lon, display_name, ...}) o `null` si no encontró nada
 * — nunca lanza por "no encontrado", solo por un problema real de red.
 */
async function geocodificar(direccion, cp) {
  const consulta = `${direccion}, ${cp}`;
  const url = `${NOMINATIM_URL}?format=json&limit=1&q=${encodeURIComponent(consulta)}`;
  const respuesta = await fetch(url, { headers: { 'Accept-Language': 'es' } });
  if (!respuesta.ok) {
    throw new Error('No se pudo consultar el servicio de mapas.');
  }
  const resultados = await respuesta.json();
  return resultados.length ? resultados[0] : null;
}

/** Crea (o recrea) un mapa Leaflet centrado en lat/lon, con un marcador. */
function crearMapa(contenedorId, lat, lon) {
  const mapa = L.map(contenedorId, { zoomControl: false, attributionControl: true }).setView([lat, lon], 16);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; colaboradores de OpenStreetMap',
  }).addTo(mapa);
  L.marker([lat, lon]).addTo(mapa);
  return mapa;
}

window.Mapa = { geocodificar, crearMapa };

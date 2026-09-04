// cargando.js — indicador de carga reutilizable: dos frases rotando
// ("Cargando" / "Por favor aguarde") con puntos suspensivos animados
// (. → .. → ...), adaptado del componente de referencia "WordRotate".
// Reemplaza el "Cargando…" estático que usaban usuarios.html y
// edificios.html en cada listado/detalle con carga real de datos.
//
// window.Cargando.html() devuelve solo el <span> — quien lo llama decide
// el contenedor y el estilo (un <p> para un listado, directo dentro de un
// <h1> para un título — el tamaño de fuente y el color los hereda de ahí,
// nunca los fija este componente).
//
// Un único intervalo global anima TODAS las instancias que haya en la
// página en cada momento — se re-descubren en cada tick, así funciona
// también con instancias recién insertadas vía innerHTML, sin necesitar
// un timer por instancia que haya que limpiar a mano cuando se reemplaza
// el contenido (evita el leak clásico de setInterval por elemento).
const FRASES_CARGANDO = ['Cargando', 'Por favor aguarde'];
const DURACION_TICK_MS = 450; // cada tick cambia la cantidad de puntos
const TICKS_POR_FRASE = 6; // 6 * 450ms = 2.7s mostrando cada frase

let tick = 0;

function html() {
  return '<span class="cargando-rotativo"><span class="cargando-texto"></span></span>';
}

function actualizarTick() {
  const spans = document.querySelectorAll('.cargando-rotativo .cargando-texto');
  if (spans.length > 0) {
    const indiceFrase = Math.floor(tick / TICKS_POR_FRASE) % FRASES_CARGANDO.length;
    const puntos = '.'.repeat((tick % 3) + 1);
    const texto = `${FRASES_CARGANDO[indiceFrase]}${puntos}`;
    const esCambioDeFrase = tick % TICKS_POR_FRASE === 0;

    spans.forEach((span) => {
      if (!esCambioDeFrase) {
        span.textContent = texto;
        return;
      }
      // cambio de frase: se desvanece, cambia el texto invisible, y
      // recién ahí vuelve a aparecer — el "rotate" visual del componente
      // de referencia. El doble requestAnimationFrame asegura que el
      // navegador ya pintó el estado invisible antes de animar de vuelta
      // (si no, a veces "salta" directo al final sin transición real).
      span.classList.add('cambiando');
      span.textContent = texto;
      requestAnimationFrame(() => {
        requestAnimationFrame(() => span.classList.remove('cambiando'));
      });
    });
  }
  tick++;
}

document.addEventListener('DOMContentLoaded', () => {
  actualizarTick();
  setInterval(actualizarTick, DURACION_TICK_MS);
});

window.Cargando = { html };

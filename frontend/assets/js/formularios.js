// formularios.js — evita que Enter dispare el submit del formulario antes
// de llegar al último campo.
//
// Por default, un <form> con más de un input envía el formulario apenas
// se presiona Enter en CUALQUIER campo de texto — no hace falta ni un
// botón submit. Eso fue lo que creó un edificio real con datos a medio
// cargar: se completó Nombre y Dirección, y al presionar Enter en CP
// (para "pasar al siguiente campo", como se hace con Tab) el formulario
// se mandó entero, saltando el resto de los campos y el mapa.
//
// Con esto, Enter se comporta como Tab (mueve el foco al siguiente campo
// visible) en todos los campos salvo el último, donde sí dispara el envío
// normal — el comportamiento esperado. Se aplica a cualquier formulario
// nuevo con `window.Formularios.habilitarEnterComoTab(formulario)`.
function habilitarEnterComoTab(formulario) {
  formulario.addEventListener('keydown', (evento) => {
    if (evento.key !== 'Enter') return;

    const objetivo = evento.target;
    // Enter en un <textarea> siempre inserta un salto de línea, nunca "avanza".
    if (objetivo.tagName === 'TEXTAREA') return;
    // Un botón (incluido el de submit) se comporta como corresponde.
    if (objetivo.tagName === 'BUTTON' || objetivo.type === 'submit') return;

    const campos = Array.from(
      formulario.querySelectorAll('input, select, textarea')
    ).filter((el) => !el.disabled && el.offsetParent !== null); // solo campos visibles y habilitados

    const indiceActual = campos.indexOf(objetivo);
    if (indiceActual === -1) return;

    const siguiente = campos[indiceActual + 1];
    if (siguiente) {
      evento.preventDefault();
      siguiente.focus();
      if (typeof siguiente.select === 'function') siguiente.select();
    }
    // Si es el último campo visible, no se previene nada: Enter dispara
    // el submit normal — es exactamente lo que se espera ahí.
  });
}

// Campo de contraseña con botón de mostrar/ocultar (ojo). Se auto-conecta
// solo con que la pantalla tenga la estructura de .campo-password-wrap
// (ver components.css) — ninguna pantalla nueva tiene que llamar nada.
const ICONO_OJO = '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>';
const ICONO_OJO_TACHADO = '<path d="M9.9 4.24A10.94 10.94 0 0112 4c6.4 0 10 7 10 7a18.5 18.5 0 01-3.22 4.32M6.5 6.64A18.36 18.36 0 002 11s3.6 7 10 7a10.9 10.9 0 004.13-.81M9.88 9.88a3 3 0 104.24 4.24"/><path d="M2 2l20 20"/>';

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.campo-password-toggle').forEach((boton) => {
    const input = boton.closest('.campo-password-wrap').querySelector('input');
    boton.addEventListener('click', () => {
      const seVaAMostrar = input.type === 'password';
      input.type = seVaAMostrar ? 'text' : 'password';
      boton.innerHTML = seVaAMostrar ? ICONO_OJO_TACHADO : ICONO_OJO;
      boton.setAttribute('aria-label', seVaAMostrar ? 'Ocultar contraseña' : 'Mostrar contraseña');
    });
  });
});

window.Formularios = { habilitarEnterComoTab, ICONO_OJO };

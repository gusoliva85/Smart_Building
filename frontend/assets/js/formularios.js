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

window.Formularios = { habilitarEnterComoTab };

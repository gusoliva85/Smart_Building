// view-switch.js — indicador deslizante para cualquier .view-switch de la
// app (selector segmentado con texto adentro: "Datos generales"/"Estructura"
// hoy, más adelante el selector General/Incidentes/Deudores/Mantenimiento
// del Dashboard Visual). Se engancha solo a cada .view-switch que encuentre
// en la página — ninguna pantalla nueva tiene que llamar nada.
//
// La técnica es la que se usaría para animar un switch on/off (un "thumb"
// que se desliza entre dos posiciones), adaptada acá a un selector de N
// opciones con texto: en vez de mover un círculo entre dos extremos, el
// indicador se mueve y cambia de ancho para calzar exacto con el botón
// activo, usando sus coordenadas reales (getBoundingClientRect) — así
// funciona igual con 2, 3 o 6 opciones, y con texto de cualquier largo.
function inicializarViewSwitch(contenedor) {
  const indicador = document.createElement('span');
  indicador.className = 'view-switch-indicador';
  contenedor.prepend(indicador);

  function botonActivo() {
    return contenedor.querySelector('button.active') || contenedor.querySelector('button');
  }

  function moverIndicadorA(boton, instantaneo) {
    if (!boton) return;
    const rectContenedor = contenedor.getBoundingClientRect();
    if (rectContenedor.width === 0) return; // el switch está oculto (display:none) — el ResizeObserver reintenta cuando aparezca
    const rectBoton = boton.getBoundingClientRect();
    if (instantaneo) indicador.style.transition = 'none';
    indicador.style.width = `${rectBoton.width}px`;
    indicador.style.transform = `translateX(${rectBoton.left - rectContenedor.left}px)`;
    if (instantaneo) {
      // fuerza el reflow antes de reactivar la transición — si no, el
      // navegador puede animar igual desde 0 aunque se pidió instantáneo
      void indicador.offsetWidth;
      indicador.style.transition = '';
    }
  }

  contenedor.querySelectorAll('button').forEach((boton) => {
    boton.addEventListener('click', () => moverIndicadorA(boton, false));
  });

  // Reposiciona sin animar cada vez que cambia el tamaño del switch — cubre
  // tanto la carga inicial (el panel puede seguir oculto con display:none
  // en el momento en que este script corre, ej. #vista-detalle de
  // edificios.html hasta que termina de cargar el edificio) como un
  // resize de ventana o una rotación del celular.
  const observador = new ResizeObserver(() => moverIndicadorA(botonActivo(), true));
  observador.observe(contenedor);
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.view-switch').forEach(inicializarViewSwitch);
});

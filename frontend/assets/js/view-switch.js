/* ============================================================================
   view-switch.js — El indicador deslizante de TODO selector segmentado.

   La idea, que es una decision de diseno y no un adorno: el fondo del boton
   activo no lo pinta cada boton por separado. Lo pinta un unico indicador
   que se mueve Y cambia de ancho para calzar exacto con el boton activo. Es
   la misma tecnica con la que se animaria un switch on/off —un "thumb" que
   viaja entre dos posiciones— extendida a N opciones de cualquier largo de
   texto.

   SE ENGANCHA SOLO a cualquier `.view-switch` de la pagina, y tambien a los
   que se inserten despues. Ninguna pantalla lo inicializa a mano.

   DIVISION DE RESPONSABILIDADES, que es lo que permite que conviva con la
   logica de cada pantalla sin pisarla:

     - Este archivo se ocupa de la PIEL: que boton se ve activo y donde esta
       el indicador.
     - La pantalla se ocupa del DATO: que se muestra cuando cambia la vista,
       con su propio listener de click sobre los mismos botones.

   Los dos escuchan el mismo clic y no se estorban. Y si una pantalla cambia
   el boton activo por codigo —restaurando un estado guardado, por ejemplo—,
   el indicador la sigue igual: ver el MutationObserver de mas abajo.

   No depende de config.js ni de api.js: no habla con el backend.
   ========================================================================== */

(function () {
  'use strict';

  var CLASE_ACTIVO = 'activo';
  var CLASE_INDICADOR = 'view-switch-indicador';
  var CLASE_SIN_ANIMACION = 'sin-animacion';

  /* --------------------------------------------------------- utilidades --- */

  function botonesDe(selector) {
    return Array.prototype.slice.call(selector.querySelectorAll('button'));
  }

  function botonActivo(selector) {
    /* Si ninguno vino marcado en el HTML, el primero es el activo: un
       selector segmentado siempre tiene una opcion elegida. */
    return selector.querySelector('button.' + CLASE_ACTIVO) ||
           selector.querySelector('button');
  }

  /* ----------------------------------------------------------- indicador -- */

  /* El indicador lo crea este archivo, NO el HTML de la pantalla. Asi una
     pantalla nueva solo escribe los botones y el resto le llega gratis. */
  function asegurarIndicador(selector) {
    var indicador = selector.querySelector('.' + CLASE_INDICADOR);
    if (!indicador) {
      indicador = document.createElement('span');
      indicador.className = CLASE_INDICADOR;
      indicador.setAttribute('aria-hidden', 'true');
      /* Primero en el DOM: los botones van con z-index por encima, y asi el
         orden del documento tambien los deja arriba. */
      selector.insertBefore(indicador, selector.firstChild);
    }
    return indicador;
  }

  /**
   * Coloca el indicador debajo del boton activo.
   *
   * @param {boolean} animar  false para saltar sin transicion.
   */
  function colocar(selector, animar) {
    var indicador = asegurarIndicador(selector);
    var boton = botonActivo(selector);
    if (!boton) return;

    var cajaSelector = selector.getBoundingClientRect();
    var cajaBoton = boton.getBoundingClientRect();

    /* Medir con el selector oculto (display:none, un panel que todavia no
       cargo) da todo en cero. Si se colocara igual, el indicador quedaria
       pegado al borde izquierdo y del ancho de nada PARA SIEMPRE, porque
       esta funcion no volveria a correr. Se descarta la medicion y se espera:
       el ResizeObserver de abajo la vuelve a disparar en cuanto el selector
       tenga tamano real. */
    if (!cajaBoton.width) return;

    /* El desplazamiento se calcula contra el borde del selector y sumando su
       scroll: en mobile el selector puede tener scroll horizontal propio, y
       sin sumarlo el indicador se queda atras al desplazarse. */
    var desplazamiento = cajaBoton.left - cajaSelector.left + selector.scrollLeft;

    if (!animar) indicador.classList.add(CLASE_SIN_ANIMACION);

    indicador.style.width = cajaBoton.width + 'px';
    indicador.style.transform = 'translateX(' + desplazamiento + 'px)';

    if (!animar) {
      /* Dos frames, no uno. Con uno solo, el navegador puede no haber
         aplicado todavia el estilo nuevo cuando se saca la clase, y la
         transicion se dispara igual — que es justo lo que se queria evitar. */
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          indicador.classList.remove(CLASE_SIN_ANIMACION);
        });
      });
    }
  }

  /* -------------------------------------------------------------- estado -- */

  function marcarActivo(selector, boton) {
    botonesDe(selector).forEach(function (otro) {
      var esActivo = otro === boton;
      otro.classList.toggle(CLASE_ACTIVO, esActivo);
      /* Un lector de pantalla no ve el indicador deslizante: la opcion
         elegida tiene que estar dicha en el arbol de accesibilidad. */
      otro.setAttribute('aria-selected', esActivo ? 'true' : 'false');
      /* Solo la pestana activa es tabulable; entre las demas se navega con
         las flechas. Es el comportamiento estandar de un grupo de pestanas,
         y evita que un selector de seis opciones se coma seis tabs. */
      otro.setAttribute('tabindex', esActivo ? '0' : '-1');
    });
  }

  /* ------------------------------------------------------------- eventos -- */

  function alHacerClic(evento) {
    var destino = evento.target;
    if (!destino || !destino.closest) return;

    var boton = destino.closest('.view-switch button');
    if (!boton) return;

    var selector = boton.closest('.view-switch');
    if (!selector) return;

    marcarActivo(selector, boton);

    /* Se coloca aca TAMBIEN, y no solo desde el MutationObserver. Parece
       redundante y no lo es: el observador cubre el cambio hecho por codigo
       de la pantalla, y esta linea cubre el clic incluso si el navegador no
       tuviera MutationObserver. Las dos llamadas terminan en la misma
       funcion con el mismo boton activo, asi que repetirla no hace nada. */
    colocar(selector, true);
  }

  /* Flechas para moverse entre pestanas, Home/End para ir a los extremos.
     Es lo que espera cualquiera que navegue con teclado en un grupo de
     pestanas, y es parte de la accesibilidad minima obligatoria. */
  function alPresionarTecla(evento) {
    var destino = evento.target;
    if (!destino || !destino.closest) return;

    var boton = destino.closest('.view-switch button');
    if (!boton) return;

    var selector = boton.closest('.view-switch');
    if (!selector) return;

    var botones = botonesDe(selector);
    var posicion = botones.indexOf(boton);
    var siguiente = null;

    if (evento.key === 'ArrowRight' || evento.key === 'ArrowDown') {
      siguiente = botones[(posicion + 1) % botones.length];
    } else if (evento.key === 'ArrowLeft' || evento.key === 'ArrowUp') {
      siguiente = botones[(posicion - 1 + botones.length) % botones.length];
    } else if (evento.key === 'Home') {
      siguiente = botones[0];
    } else if (evento.key === 'End') {
      siguiente = botones[botones.length - 1];
    }

    if (!siguiente) return;

    evento.preventDefault();
    /* Se dispara el clic en vez de solo enfocar, para que la pantalla que
       escucha el clic cambie el dato igual que con el mouse. */
    siguiente.focus();
    siguiente.click();
  }

  /* ----------------------------------------------------------- observador -- */

  /* El ResizeObserver es lo que hace que el indicador no quede nunca mal
     puesto, y resuelve tres problemas de una sola vez:

       1. El selector estaba oculto al cargar y midio cero (el caso que
          obligo a escribirlo asi: con una medicion unica al cargar, quedaba
          mal para siempre).
       2. La ventana cambio de tamano.
       3. El telefono rotó.

     No animar en estos casos es deliberado: no hubo una eleccion del
     usuario, el indicador solo esta recalculando donde le toca estar. */
  function observarTamano(selector) {
    if (typeof ResizeObserver === 'undefined') return;

    var observador = new ResizeObserver(function () {
      colocar(selector, false);
    });
    observador.observe(selector);
  }

  /* Reposiciona cuando el boton activo cambia, sin importar QUIEN lo cambio:
     el clic de este archivo o el codigo de la pantalla restaurando un estado
     guardado. */
  function observarClaseActiva(selector) {
    if (typeof MutationObserver === 'undefined') return;

    var observador = new MutationObserver(function () {
      colocar(selector, true);
    });

    botonesDe(selector).forEach(function (boton) {
      observador.observe(boton, { attributes: true, attributeFilter: ['class'] });
    });
  }

  /* ------------------------------------------------------------- arranque -- */

  function montarSelector(selector) {
    if (selector.dataset.viewSwitchListo === '1') return;
    selector.dataset.viewSwitchListo = '1';

    /* Un grupo de pestanas se anuncia como tal. El rol va en el contenedor
       aunque la pantalla no lo haya puesto: es parte del componente. */
    if (!selector.getAttribute('role')) selector.setAttribute('role', 'tablist');
    botonesDe(selector).forEach(function (boton) {
      if (!boton.getAttribute('role')) boton.setAttribute('role', 'tab');
    });

    marcarActivo(selector, botonActivo(selector));
    colocar(selector, false);

    observarTamano(selector);
    observarClaseActiva(selector);
  }

  function montarTodos(raiz) {
    var selectores = (raiz || document).querySelectorAll('.view-switch');
    Array.prototype.forEach.call(selectores, montarSelector);
  }

  document.addEventListener('click', alHacerClic);
  document.addEventListener('keydown', alPresionarTecla);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { montarTodos(); });
  } else {
    montarTodos();
  }

  /* Las fuentes de Google llegan despues del DOMContentLoaded y cambian el
     ancho del texto de los botones. Sin esto, el indicador queda calzado
     para la tipografia de respaldo y desfasado para la definitiva. El
     ResizeObserver ya lo cubre donde existe; esto es el respaldo barato. */
  window.addEventListener('load', function () {
    Array.prototype.forEach.call(
      document.querySelectorAll('.view-switch'),
      function (selector) { colocar(selector, false); }
    );
  });

  window.ViewSwitch = {
    /* Para una pantalla que inserte un selector despues de cargar (dentro de
       un modal, por ejemplo) y quiera engancharlo sin esperar al primer
       clic. El indicador ya funciona sin llamar esto si el selector estaba
       en el HTML inicial. */
    montar: montarTodos,
    colocar: colocar
  };
}());

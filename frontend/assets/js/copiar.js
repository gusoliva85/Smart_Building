/* ============================================================================
   copiar.js — Copiar un dato al portapapeles, con feedback inmediato.

   El caso de origen es el CBU y el alias del edificio: datos que nadie lee,
   se copian y se pegan en el homebanking. Un dato de 22 digitos transcrito a
   mano es un error de tipeo esperando, y en un CBU ese error manda la plata a
   otra cuenta.

   ==========================================================================
   EL FEEDBACK NO ES UN ADORNO: ES LA MITAD DE LA FUNCION
   ==========================================================================

   Copiar no cambia nada en la pantalla. Sin una senial, quien hizo clic no
   tiene forma de saber si funciono, y lo que hace entonces es volver a hacer
   clic — o peor, pegar y descubrir que pego otra cosa. Asi que el icono pasa
   a un check por un segundo y medio y la etiqueta para lectores de pantalla
   dice "Copiado".

   ==========================================================================
   SI EL NAVEGADOR NO DA PERMISO, NO SE ROMPE NADA
   ==========================================================================

   `navigator.clipboard` no existe en contextos no seguros (http servido a
   otra maquina) y puede ser rechazado por el navegador. En ese caso se
   selecciona el texto del dato, que es lo unico util que queda: la persona
   copia con Ctrl+C. Lo que no se hace es mostrar un error: no poder copiar
   con un boton no impide seguir trabajando.

   SE ENGANCHA SOLO, por delegacion en `document`, igual que formularios.js.
   Cualquier boton con `data-copiar` funciona, tambien si se inserto despues
   de cargar la pagina — que es el caso normal, porque los datos de un
   edificio se dibujan al traerlos del backend.

       <button type="button" data-copiar="#cbu-del-edificio" aria-label="Copiar CBU">
         <svg ...></svg>
       </button>

   El valor de `data-copiar` es un selector del elemento que tiene el texto.
   Se apunta al elemento y no se escribe el texto en el atributo a proposito:
   asi el dato existe UNA vez en el DOM y no hay forma de que el boton copie
   un valor viejo despues de redibujar.

   No depende de config.js ni de api.js: no habla con el backend.
   ========================================================================== */

(function () {
  'use strict';

  /* Cuanto dura el check. Un segundo y medio es lo que tarda en leerse sin
     que el boton quede "raro" si alguien vuelve a mirarlo mas tarde. */
  var DURACION_DEL_CHECK = 1500;

  var ICONO_COPIAR =
    '<rect x="9" y="9" width="11" height="11" rx="2"/>' +
    '<path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1"/>';

  var ICONO_CHECK = '<path d="M20 6L9 17l-5-5"/>';

  /* Los temporizadores por boton. Hacen falta porque dos clics seguidos
     tienen que reiniciar la cuenta, no encadenar dos restauraciones: con una
     sola variable global, el segundo clic en OTRO boton dejaria el primero
     con el check puesto para siempre. */
  var pendientes = [];

  function temporizadorDe(boton) {
    for (var i = 0; i < pendientes.length; i += 1) {
      if (pendientes[i].boton === boton) return pendientes[i];
    }
    var nuevo = { boton: boton, id: null, etiqueta: null, icono: null };
    pendientes.push(nuevo);
    return nuevo;
  }

  function pintarIcono(boton, contenido) {
    /* Al <svg> interno, NUNCA al <button>. Un <button> es HTML: su parser no
       reconoce <path> ni <rect> como elementos SVG fuera de un <svg>, los
       deja como elementos desconocidos invisibles, y el icono desaparece al
       primer clic. Fue un bug real del proyecto. */
    var svg = boton.querySelector('svg');
    if (svg) svg.innerHTML = contenido;
  }

  function avisarQueCopio(boton) {
    var estado = temporizadorDe(boton);

    /* Se guarda el estado original una sola vez: si se guardara en cada clic,
       el segundo clic guardaria el check como "original" y el boton se
       quedaria con el check puesto. */
    if (estado.id === null) {
      estado.etiqueta = boton.getAttribute('aria-label');
      var svg = boton.querySelector('svg');
      estado.icono = svg ? svg.innerHTML : ICONO_COPIAR;
    } else {
      window.clearTimeout(estado.id);
    }

    pintarIcono(boton, ICONO_CHECK);
    boton.setAttribute('aria-label', 'Copiado');
    boton.classList.add('copiado');

    estado.id = window.setTimeout(function () {
      pintarIcono(boton, estado.icono);
      if (estado.etiqueta) boton.setAttribute('aria-label', estado.etiqueta);
      boton.classList.remove('copiado');
      estado.id = null;
    }, DURACION_DEL_CHECK);
  }

  /* Lo que queda cuando no se puede copiar: dejar el texto seleccionado para
     que Ctrl+C funcione. No es lo mismo que copiar, pero es mucho mejor que
     no hacer nada y no decir nada. */
  function seleccionar(elemento) {
    try {
      var rango = document.createRange();
      rango.selectNodeContents(elemento);
      var seleccion = window.getSelection();
      seleccion.removeAllRanges();
      seleccion.addRange(rango);
    } catch (error) {
      /* Si ni eso se puede, no hay nada mas que ofrecer. */
    }
  }

  /**
   * Copia un texto y avisa en el boton.
   *
   * @param {HTMLElement} boton El boton que se toco, donde va el feedback.
   * @param {string} texto Lo que se copia.
   * @param {HTMLElement} [elemento] El elemento que muestra el dato, para
   *   seleccionarlo si el portapapeles no esta disponible.
   * @returns {Promise<boolean>} si copio de verdad. **No rechaza nunca.**
   */
  function alPortapapeles(boton, texto, elemento) {
    if (!texto) return Promise.resolve(false);

    if (!navigator.clipboard || !navigator.clipboard.writeText) {
      if (elemento) seleccionar(elemento);
      return Promise.resolve(false);
    }

    return navigator.clipboard.writeText(texto).then(
      function () {
        avisarQueCopio(boton);
        return true;
      },
      function () {
        /* Permiso denegado, o el documento no esta enfocado. Mismo camino que
           la ausencia de la API: se ofrece la seleccion y se sigue. */
        if (elemento) seleccionar(elemento);
        return false;
      }
    );
  }

  function alHacerClic(evento) {
    var destino = evento.target;
    if (!destino || !destino.closest) return;

    var boton = destino.closest('[data-copiar]');
    if (!boton) return;

    var fuente = document.querySelector(boton.getAttribute('data-copiar'));
    if (!fuente) return;

    alPortapapeles(boton, (fuente.textContent || '').trim(), fuente);
  }

  document.addEventListener('click', alHacerClic);

  window.Copiar = {
    alPortapapeles: alPortapapeles,
    /* Expuesto para que ninguna pantalla vuelva a dibujar el mismo icono. */
    ICONO_COPIAR: ICONO_COPIAR,
    ICONO_CHECK: ICONO_CHECK
  };
}());

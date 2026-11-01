/* ============================================================================
   formularios.js — Comportamiento comun a TODO formulario del proyecto.

   Dos cosas, las dos nacidas de un problema real:

     1. Enter avanza de campo en vez de enviar, salvo en el ultimo. Se creo
        un edificio a medio cargar porque Enter en un campo intermedio envio
        el formulario entero. Quien carga datos usa Enter como separador,
        igual que en una planilla, y la pantalla tiene que acompanar eso.

     2. El toggle de mostrar/ocultar de los campos de contrasenia.

   SE ENGANCHA SOLO. Las dos cosas trabajan por delegacion en `document`, asi
   que funcionan igual en un formulario que ya estaba en el HTML y en uno que
   se inserta despues (el modal de alta, por ejemplo). Ninguna pantalla llama
   nada a mano, y no hay que acordarse de reinicializar nada al redibujar.

   No depende de config.js ni de api.js: no habla con el backend.
   ========================================================================== */

(function () {
  'use strict';

  /* Los dos iconos del toggle, como contenido INTERIOR de un <svg> ya
     existente: trazo, viewBox 24x24, extremos redondeados, como todo icono
     del proyecto. Se exponen en window.Formularios para que cualquier
     pantalla que necesite el mismo dibujo use este y no lo redibuje. */

  /* Ojo abierto: la contrasenia esta OCULTA, y el boton invita a mostrarla. */
  var ICONO_OJO =
    '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7z"/>' +
    '<circle cx="12" cy="12" r="3"/>';

  /* Ojo tachado: la contrasenia esta VISIBLE, y el boton invita a ocultarla. */
  var ICONO_OJO_TACHADO =
    '<path d="M10.6 5.2A9.9 9.9 0 0 1 12 5c6.4 0 10 7 10 7a18.6 18.6 0 0 1-2.2 3.1"/>' +
    '<path d="M6.6 6.7A18.3 18.3 0 0 0 2 12s3.6 7 10 7a9.6 9.6 0 0 0 4.2-.9"/>' +
    '<path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>' +
    '<path d="M3 3l18 18"/>';

  /* Tipos de <input> que no son un campo para escribir: Enter sobre ellos
     tiene que hacer lo de siempre (enviar), no avanzar. */
  var TIPOS_NO_NAVEGABLES = ['submit', 'button', 'reset', 'image', 'hidden'];

  /* ------------------------------------------------- Enter avanza de campo -- */

  /**
   * Los campos de un formulario en el orden en que se recorren, ya filtrados.
   *
   * getClientRects() y NO offsetParent para descartar los invisibles: un
   * campo dentro de un contenedor con position:fixed —todo modal del
   * proyecto— tiene offsetParent nulo aunque se vea perfecto, y con ese
   * criterio la lista de un modal saldria vacia.
   */
  function camposNavegables(formulario) {
    return Array.prototype.filter.call(
      formulario.querySelectorAll('input, select, textarea'),
      function (campo) {
        if (campo.disabled || campo.readOnly) return false;
        if (TIPOS_NO_NAVEGABLES.indexOf(campo.type) !== -1) return false;
        return campo.getClientRects().length > 0;
      }
    );
  }

  function alPresionarTecla(evento) {
    if (evento.key !== 'Enter') return;

    /* Con un modificador apretado Enter significa otra cosa (Ctrl+Enter para
       enviar es una convencion extendida); no se intercepta. */
    if (evento.ctrlKey || evento.metaKey || evento.altKey || evento.shiftKey) return;

    var campo = evento.target;
    if (!campo || !campo.tagName) return;

    /* En un textarea Enter es un salto de linea y nada mas. */
    if (campo.tagName === 'TEXTAREA') return;
    if (campo.tagName !== 'INPUT' && campo.tagName !== 'SELECT') return;
    if (TIPOS_NO_NAVEGABLES.indexOf(campo.type) !== -1) return;

    var formulario = campo.form;
    if (!formulario) return;

    var lista = camposNavegables(formulario);
    var posicion = lista.indexOf(campo);

    /* En el ultimo campo Enter SI envia: es el atajo que la gente espera, y
       ahi el formulario ya esta completo. Si el campo no esta en la lista
       (quedo oculto entre medio), tampoco se toca nada. */
    if (posicion === -1 || posicion === lista.length - 1) return;

    evento.preventDefault();
    lista[posicion + 1].focus();
  }

  /* --------------------------------------------- Mostrar/ocultar contrasenia -- */

  function pintarToggle(boton, visible) {
    /* Se le pisa el innerHTML al <svg> interno, NUNCA al <button>.
       Un <button> es HTML, no SVG: su parser no reconoce <path> ni <circle>
       como elementos SVG reales fuera de un tag <svg>, los deja como
       elementos desconocidos invisibles, y el icono desaparece al primer
       clic. Fue un bug real. */
    var svg = boton.querySelector('svg');
    if (svg) svg.innerHTML = visible ? ICONO_OJO_TACHADO : ICONO_OJO;

    boton.setAttribute(
      'aria-label',
      visible ? 'Ocultar contrasenia' : 'Mostrar contrasenia'
    );
  }

  function campoDelToggle(boton) {
    var contenedor = boton.closest('.campo-password-wrap');
    return contenedor ? contenedor.querySelector('input') : null;
  }

  function alternarVisibilidad(boton) {
    var campo = campoDelToggle(boton);
    if (!campo) return;

    var mostrar = campo.type === 'password';

    /* Cambiar el type del input mueve el cursor al final. Se guarda la
       posicion antes y se restaura despues, para que alguien que toco el ojo
       en medio de la palabra siga escribiendo donde estaba. */
    var desde = campo.selectionStart;
    var hasta = campo.selectionEnd;

    campo.type = mostrar ? 'text' : 'password';
    pintarToggle(boton, mostrar);

    /* El foco vuelve al campo: el usuario toco el ojo para seguir
       escribiendo, no para quedarse en el boton. */
    campo.focus();
    try {
      if (desde !== null && hasta !== null) campo.setSelectionRange(desde, hasta);
    } catch (error) {
      /* Algun navegador no deja leer/escribir la seleccion segun el type.
         Perder la posicion del cursor no justifica cortar el toggle. */
    }
  }

  function alHacerClic(evento) {
    var destino = evento.target;
    if (!destino || !destino.closest) return;

    var boton = destino.closest('.campo-password-toggle');
    if (boton) alternarVisibilidad(boton);
  }

  /* Sincroniza cada toggle con el type real de su campo. Importa porque el
     navegador restaura valores al volver atras, y porque asi el HTML de una
     pantalla puede nacer con el campo visible sin que el icono mienta. */
  function sincronizarToggles(raiz) {
    var botones = (raiz || document).querySelectorAll('.campo-password-toggle');
    Array.prototype.forEach.call(botones, function (boton) {
      var campo = campoDelToggle(boton);
      if (campo) pintarToggle(boton, campo.type !== 'password');
    });
  }

  /* ------------------------------------------------------------- arranque -- */

  document.addEventListener('keydown', alPresionarTecla);
  document.addEventListener('click', alHacerClic);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { sincronizarToggles(); });
  } else {
    sincronizarToggles();
  }

  window.Formularios = {
    ICONO_OJO: ICONO_OJO,
    ICONO_OJO_TACHADO: ICONO_OJO_TACHADO,
    /* Para el caso en que una pantalla inserte un campo de contrasenia y
       quiera dejar el icono coherente sin esperar al primer clic. El toggle
       ya funciona sin llamar esto. */
    sincronizarToggles: sincronizarToggles,
    camposNavegables: camposNavegables
  };
}());

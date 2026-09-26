/* ============================================================================
   theme.js — Cambio de tema claro/oscuro, con persistencia.

   Trabaja en pareja con el script inline del <head> de cada pagina. La
   division es deliberada:

     - El script del <head> APLICA el tema guardado, sincrono y antes de las
       hojas de estilo, para que no se vea un destello claro antes de pasar a
       oscuro. Tiene que ser minimo y no puede esperar a este archivo.
     - Este archivo ALTERNA el tema cuando el usuario toca el boton, y guarda
       la eleccion.

   Se engancha solo: cualquier boton con id "boton-tema" o con el atributo
   data-toggle-tema queda conectado al cargar la pagina. Ninguna pantalla
   llama nada a mano.
   ========================================================================== */

(function () {
  'use strict';

  var CLAVE = 'tema';
  var CLARO = 'light';
  var OSCURO = 'dark';

  var raiz = document.documentElement;

  /* --------------------------------------------------------- persistencia -- */
  /* localStorage puede lanzar (modo privado, almacenamiento bloqueado por
     politica del sitio). Un fallo ahi no puede tumbar el cambio de tema: se
     pierde la preferencia entre paginas, nada mas. */

  function leerGuardado() {
    try {
      return localStorage.getItem(CLAVE);
    } catch (error) {
      return null;
    }
  }

  function guardar(valor) {
    try {
      localStorage.setItem(CLAVE, valor);
    } catch (error) {
      /* sin persistencia, pero el tema cambia igual en esta pagina */
    }
  }

  /* ---------------------------------------------------------------- estado -- */

  function temaActual() {
    return raiz.getAttribute('data-theme') === OSCURO ? OSCURO : CLARO;
  }

  /* El atributo se saca en lugar de ponerlo en "light": el tema claro es el
     estado por defecto de :root, no una variante. Dejar data-theme="light"
     escrito sugiere que existe un tercer estado que no existe. */
  function aplicar(valor) {
    if (valor === OSCURO) {
      raiz.setAttribute('data-theme', OSCURO);
    } else {
      raiz.removeAttribute('data-theme');
    }
    guardar(valor);
    actualizarBotones(valor);
  }

  /* ---------------------------------------------------------- accesibilidad -- */
  /* El icono no cambia: la skill define un unico icono para este boton y no se
     inventa uno nuevo por estado. Lo que si cambia es la etiqueta accesible,
     porque un lector de pantalla necesita saber QUE va a pasar al activarlo. */

  function actualizarBotones(valor) {
    var texto = valor === OSCURO ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro';
    botones().forEach(function (boton) {
      boton.setAttribute('aria-label', texto);
      boton.setAttribute('title', texto);
    });
  }

  function botones() {
    return Array.prototype.slice.call(
      document.querySelectorAll('#boton-tema, [data-toggle-tema]')
    );
  }

  /* --------------------------------------------------------------- alternar -- */

  function prefiereMenosMovimiento() {
    return window.matchMedia
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function alternar() {
    var siguiente = temaActual() === OSCURO ? CLARO : OSCURO;
    var cambio = function () { aplicar(siguiente); };

    /* View Transitions API con el cross-fade que trae el navegador por
       defecto, SIN personalizar.

       Ojo: se implemento una vez un barrido circular que nacia en el punto
       del clic y se revirtio a pedido explicito del usuario — tuvo un bug de
       z-index y se reporto como lento en Chrome en produccion. No se vuelve a
       intentar sin una decision nueva.

       Sin soporte de la API, o con movimiento reducido, el cambio es
       instantaneo: degradacion aceptable. */
    if (document.startViewTransition && !prefiereMenosMovimiento()) {
      document.startViewTransition(cambio);
    } else {
      cambio();
    }
  }

  /* ------------------------------------------------------------- arranque --- */

  function enganchar() {
    /* El <head> ya aplico el tema guardado; aca solo se sincronizan las
       etiquetas de los botones con el estado real. */
    actualizarBotones(temaActual());

    botones().forEach(function (boton) {
      if (boton.dataset.temaEnganchado) return;   // idempotente
      boton.dataset.temaEnganchado = '1';
      boton.addEventListener('click', alternar);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enganchar);
  } else {
    enganchar();
  }

  /* Se expone para las pantallas que necesiten alternar el tema desde otro
     control, y para poder probarlo. */
  window.Tema = {
    actual: temaActual,
    aplicar: aplicar,
    alternar: alternar,
    enganchar: enganchar,
    guardado: leerGuardado
  };
}());

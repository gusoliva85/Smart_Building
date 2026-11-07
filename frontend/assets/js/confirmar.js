/* confirmar.js — preguntar antes de una accion que no se deshace.
 *
 * Reemplaza a window.confirm(), que esta prohibido en todo el proyecto: no es
 * responsive, no respeta el tema, y sobre todo no deja explicar la
 * consecuencia — un "Aceptar / Cancelar" sin contexto se contesta en
 * automatico, asi que no previene nada.
 *
 * Se usa asi, desde cualquier pantalla:
 *
 *   window.Confirmar.pedir({
 *     titulo: 'Desactivar la cuenta',
 *     mensaje: 'Ana Prueba no va a poder volver a iniciar sesion.',
 *     textoAccion: 'Confirmar y desactivar'
 *   }).then(function (confirmo) {
 *     if (!confirmo) return;
 *     ...
 *   });
 *
 * La promesa SIEMPRE se resuelve, nunca se rechaza: cancelar no es un error,
 * es una respuesta. Un reject obligaria a cada pantalla a poner un catch que
 * no distinguiria "dijo que no" de "se rompio algo".
 *
 * El HTML lo arma este archivo, no las pantallas. Si cada pantalla copiara el
 * bloque del modal, el dia que cambie el componente habria que acordarse de
 * los catorce lugares. La contra es que el modal no existe en el DOM hasta la
 * primera pregunta; para un elemento que arranca oculto no cambia nada.
 *
 * Reglas de redaccion del mensaje, que son la mitad del componente:
 *   - Nunca "¿Estas seguro?". Dice QUE va a pasar, con el nombre de lo
 *     afectado adentro.
 *   - Si se puede deshacer, lo aclara. Es lo que permite confirmar tranquilo.
 *   - El boton de accion lleva el verbo, no "Aceptar": leido solo, tiene que
 *     alcanzar para saber lo que se esta por hacer.
 */
(function () {
  'use strict';

  /* Se arma una sola vez y se reutiliza. Las referencias quedan guardadas para
     no volver a buscarlas en cada pregunta. */
  var pieza = null;

  /* Quien contesta la pregunta abierta, y a donde vuelve el foco al cerrar.
     Se guardan afuera porque los listeners del teclado viven mas que la
     llamada a pedir(). */
  var responder = null;
  var ultimoFoco = null;

  var TEXTO_CANCELAR = 'Cancelar';

  function construir() {
    var fondo = document.createElement('div');
    fondo.className = 'modal-backdrop';
    fondo.id = 'modal-confirmar';

    /* Cerrado, el modal sigue en el DOM: el velo se esconde con opacity y
       pointer-events, que lo saca del mouse pero NO del teclado ni del lector
       de pantalla. Sin inert, un Tab desde el listado se mete en los dos
       botones de una pregunta que no esta abierta. inert los saca de las dos
       cosas a la vez, y es la unica razon por la que esta aca. */
    fondo.inert = true;
    fondo.setAttribute('aria-hidden', 'true');

    /* El <div> de afuera es solo el velo: el role="dialog" va en la caja de
       vidrio, que es la que tiene el titulo y el mensaje. */
    fondo.innerHTML =
      '<div class="modal shell modal-confirmar" role="dialog" aria-modal="true"' +
      ' aria-labelledby="modal-confirmar-titulo"' +
      ' aria-describedby="modal-confirmar-mensaje">' +
      '<h3 id="modal-confirmar-titulo"></h3>' +
      '<p id="modal-confirmar-mensaje"></p>' +
      '<div class="modal-acciones">' +
      '<button type="button" class="boton-primario boton-secundario"' +
      ' data-confirmar="no"></button>' +
      '<button type="button" class="boton-primario boton-peligro"' +
      ' data-confirmar="si"></button>' +
      '</div></div>';

    document.body.appendChild(fondo);

    pieza = {
      fondo: fondo,
      caja: fondo.querySelector('.modal-confirmar'),
      titulo: fondo.querySelector('#modal-confirmar-titulo'),
      mensaje: fondo.querySelector('#modal-confirmar-mensaje'),
      no: fondo.querySelector('[data-confirmar="no"]'),
      si: fondo.querySelector('[data-confirmar="si"]')
    };

    pieza.si.addEventListener('click', function () { cerrar(true); });
    pieza.no.addEventListener('click', function () { cerrar(false); });

    /* Este modal SI se cierra tocando el velo, al contrario del modal de
       formulario. La diferencia no es de gusto: en un alta a medio tipear un
       toque al costado pierde trabajo, y aca no hay nada que perder — tocar
       afuera es exactamente lo mismo que cancelar. */
    fondo.addEventListener('click', function (evento) {
      if (evento.target === fondo) cerrar(false);
    });

    /* Un solo listener en el documento, enganchado una vez, que no hace nada
       mientras no haya una pregunta abierta. */
    document.addEventListener('keydown', function (evento) {
      if (!responder) return;

      if (evento.key === 'Escape') {
        evento.preventDefault();
        cerrar(false);
        return;
      }

      if (evento.key === 'Tab') atraparFoco(evento);
    });
  }

  /* El foco no puede salirse del modal mientras esta abierto: si saliera, el
     siguiente Tab recorreria el listado de atras, que es justamente lo que el
     modal esta tapando. Son solo dos botones, asi que el ciclo se escribe a
     mano en vez de recolectar todo lo enfocable. */
  function atraparFoco(evento) {
    var primero = pieza.no;
    var ultimo = pieza.si;

    if (evento.shiftKey && document.activeElement === primero) {
      evento.preventDefault();
      ultimo.focus();
      return;
    }

    if (!evento.shiftKey && document.activeElement === ultimo) {
      evento.preventDefault();
      primero.focus();
      return;
    }

    /* Si el foco esta fuera de los dos botones (por ejemplo quedo en el body
       porque algo lo movio), el Tab lo trae de vuelta al primero. */
    if (document.activeElement !== primero &&
        document.activeElement !== ultimo) {
      evento.preventDefault();
      primero.focus();
    }
  }

  function cerrar(respuesta) {
    if (!responder) return;

    var contestar = responder;
    responder = null;

    /* Vuelve a donde estaba. Sin esto, el foco se queda en un boton que acaba
       de volverse invisible y el siguiente Tab arranca desde el principio de
       la pagina.

       El <body> no cuenta como "donde estaba": es lo que devuelve
       activeElement cuando no habia foco en ninguna parte, y pedirle focus()
       no mueve nada, asi que el foco se quedaria igual en el boton del modal.
       Tampoco cuenta un elemento que ya no esta en el documento (la fila pudo
       haberse reemplazado al recargarse el listado). En esos dos casos lo
       correcto es soltar el foco antes de volver el modal inerte. */
    var volverA = ultimoFoco;
    if (!volverA || !volverA.focus || volverA === document.body ||
        !document.contains(volverA)) {
      volverA = null;
    }

    if (volverA) volverA.focus();
    else if (document.activeElement && document.activeElement.blur) {
      document.activeElement.blur();
    }
    ultimoFoco = null;

    /* El inert se pone DESPUES de mover el foco: puesto antes, el navegador ya
       habria sacado el foco de la caja por su cuenta y volverA.focus() estaria
       compitiendo con eso. */
    pieza.fondo.classList.remove('abierto');
    pieza.fondo.inert = true;
    pieza.fondo.setAttribute('aria-hidden', 'true');

    contestar(respuesta);
  }

  function pedir(opciones) {
    var datos = opciones || {};

    if (!pieza) construir();

    return new Promise(function (resolver) {
      /* Si ya hay una pregunta abierta, la nueva no se encola: se contesta que
         no y no se toca la que esta. Dos modales de confirmacion superpuestos
         dejarian al usuario confirmando algo que no puede leer. */
      if (responder) {
        resolver(false);
        return;
      }

      /* textContent y no innerHTML: el mensaje lleva adentro el nombre y el
         mail de un usuario, que son datos cargados por una persona. Con
         innerHTML, un nombre con "<" rompe el modal — o algo peor. */
      pieza.titulo.textContent = datos.titulo || 'Confirmar la accion';
      pieza.mensaje.textContent = datos.mensaje || '';
      pieza.si.textContent = datos.textoAccion || 'Confirmar';
      pieza.no.textContent = datos.textoCancelar || TEXTO_CANCELAR;

      /* Por defecto el boton de accion es rojo, porque el componente existe
         para acciones destructivas. destructiva:false lo deja con el acento,
         para una confirmacion que no destruye nada (reemplazar un archivo,
         reenviar un aviso). */
      var destructiva = datos.destructiva !== false;
      pieza.si.classList.toggle('boton-peligro', destructiva);

      responder = resolver;
      ultimoFoco = document.activeElement;

      /* Se sale de inert ANTES de pedir el foco: a un elemento inerte no se le
         puede dar foco, asi que al revés el .focus() de abajo no haria nada. */
      pieza.fondo.inert = false;
      pieza.fondo.removeAttribute('aria-hidden');
      pieza.fondo.classList.add('abierto');

      /* El foco arranca en CANCELAR, no en el boton de accion. Es a proposito:
         con el foco en la accion, un Enter de mas —el mismo que venia de
         enviar un formulario— confirma el borrado sin que nadie lea el
         mensaje. Puesto en la salida segura, Enter no hace nada malo y
         confirmar pide un Tab. */
      pieza.no.focus();
    });
  }

  function abierto() {
    return Boolean(responder);
  }

  window.Confirmar = { pedir: pedir, abierto: abierto };
}());

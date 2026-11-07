/* ============================================================================
   cargando.js — El indicador de "esperando al servidor" del proyecto.

   Reemplaza cualquier "Cargando…" escrito a mano. Alterna dos frases
   ("Cargando" / "Por favor aguardá") y les anima los puntos suspensivos.

   POR QUE UN SOLO INTERVALO GLOBAL Y NO UN TIMER POR INSTANCIA. Un listado
   se reemplaza entero con innerHTML cada vez que se recarga, asi que la
   instancia a la que un timer propio estaria apuntando desaparece del DOM sin
   avisar y el timer queda corriendo contra un elemento huerfano. Un unico
   intervalo que en cada tick busca los indicadores que hay AHORA funciona
   igual con los que se insertaron despues, que es el caso normal.

   Uso:
       lista.innerHTML = '<p class="lista-vacia">' + window.Cargando.html() + '</p>';

   No fija tamanio ni color: los hereda de donde se lo inserte.
   ========================================================================== */

(function () {
  'use strict';

  var FRASES = ['Cargando', 'Por favor aguardá'];

  /* 450ms por tick. Los puntos cambian en cada uno; la frase recien cada 6,
     o sea cada 2,7 segundos. Son dos ritmos distintos a proposito: si TODO
     se desvaneciera cada 450ms, el indicador parpadearia sin parar y se
     sentiria como un error en vez de una espera. */
  var MS_POR_TICK = 450;
  var TICKS_POR_FRASE = 6;

  var tick = 0;
  var intervalo = null;

  function html() {
    return '<span class="cargando-rotativo" role="status" aria-live="polite">' +
           '<span class="cargando-texto"></span></span>';
  }

  function pintar() {
    var indicadores = document.querySelectorAll('.cargando-rotativo');

    /* Sin nada que animar, el intervalo se apaga. No es una optimizacion de
       rendimiento: es que un intervalo vivo para siempre en una pestania
       abierta todo el dia es exactamente el tipo de cosa que despues nadie
       encuentra. Se vuelve a prender solo cuando aparece un indicador. */
    if (!indicadores.length) {
      window.clearInterval(intervalo);
      intervalo = null;
      return;
    }

    var frase = FRASES[Math.floor(tick / TICKS_POR_FRASE) % FRASES.length];
    var puntos = new Array((tick % 3) + 2).join('.');
    var cambiaFrase = tick % TICKS_POR_FRASE === 0;

    indicadores.forEach(function (indicador) {
      var texto = indicador.querySelector('.cargando-texto');
      if (!texto) return;

      if (!cambiaFrase) {
        texto.textContent = frase + puntos;
        return;
      }

      /* Al cambiar de frase se desvanece, se reemplaza el texto con la
         transicion todavia corriendo y se vuelve a aparecer. El retraso
         coincide con la transicion declarada en components.css. */
      indicador.classList.add('cambiando');
      window.setTimeout(function () {
        texto.textContent = frase + puntos;
        indicador.classList.remove('cambiando');
      }, 220);
    });

    tick += 1;
  }

  /* Lo llama html(), para que el primer dibujo no espere los 450ms del
     primer tick: sin esto, el indicador aparece vacio casi medio segundo. */
  function arrancar() {
    if (intervalo !== null) return;
    tick = 0;
    intervalo = window.setInterval(pintar, MS_POR_TICK);
    /* El primer pintado va en el siguiente cuadro, no ya: quien llamo a
       html() todavia no inserto el elemento en el DOM. */
    window.requestAnimationFrame(pintar);
  }

  window.Cargando = {
    html: function () {
      arrancar();
      return html();
    }
  };
}());

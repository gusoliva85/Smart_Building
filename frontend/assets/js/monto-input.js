/* ============================================================================
   monto-input.js — formato de miles MIENTRAS se tipea (F2-T17)

   Se engancha solo, por delegacion en `document`, a todo input con
   `data-monto`. Ninguna pantalla lo inicializa.

   ============================================================================
   POR QUE NO SIRVE <input type="number">
   ============================================================================

   Esta ya anotada como trampa del proyecto y vale repetirla, porque es
   contraintuitiva: un `type="number"` **nunca agrupa los miles**. Su modelo de
   valor es un numero, y "1.234.567" no es un numero valido para el navegador,
   asi que o no se puede escribir el punto o el campo queda en blanco al
   validarse. Tampoco respeta la coma decimal del formato argentino.

   Asi que es `type="text"` con `inputmode="decimal"`, que mantiene el teclado
   numerico en el telefono, y el formato lo hace este modulo.

   ============================================================================
   LO QUE HACE DIFICIL ESTO: EL CURSOR
   ============================================================================

   Reescribir el valor de un input mueve el cursor al final. Si alguien esta
   corrigiendo el tercer digito de "1.234.567" y al tipear el cursor salta al
   final, el campo es inusable.

   La solucion no es recordar la posicion: al agregar un separador, el largo
   del texto cambia y la posicion vieja ya no apunta al mismo lugar. Lo que se
   hace es **contar cuanto cambio el largo y mover el cursor esa misma
   cantidad**. Con eso el cursor se queda pegado al digito que se estaba
   tocando, se agreguen o se saquen puntos.

   ============================================================================
   LO QUE SE GUARDA NO ES LO QUE SE VE
   ============================================================================

   La pantalla muestra "1.234.567,89" y el backend tiene que recibir
   "1234567.89". La conversion la hace `valorDe()`, que es lo que toda pantalla
   usa al armar el cuerpo del pedido. **Nunca se manda el texto del input tal
   cual**: los puntos de miles lo volverian un numero distinto.
   ========================================================================= */

(function () {
  'use strict';

  var DECIMALES = 2;

  /* Deja solo digitos, y como maximo una coma decimal con dos decimales.

     Se trabaja sobre el texto crudo que escribio la persona: se le saca todo
     lo que no sirve y se vuelve a formatear. Aceptar el punto como coma
     decimal es deliberado: en el teclado numerico del telefono el punto esta a
     mano y la coma no, asi que quien escribe "1234.56" quiere decir "1234,56"
     y no un separador de miles. */
  function limpiar(texto) {
    texto = String(texto == null ? '' : texto);

    /* El punto escrito por la persona se trata como coma decimal SOLO si no
       hay una coma ya escrita: si escribio "1.234,56", los puntos son miles. */
    if (texto.indexOf(',') === -1) {
      var puntos = texto.split('.').length - 1;
      /* Un solo punto con uno o dos digitos detras es una coma decimal; dos o
         mas puntos, o un punto con tres digitos detras, son miles. */
      if (puntos === 1) {
        var detras = texto.length - texto.indexOf('.') - 1;
        if (detras > 0 && detras <= DECIMALES) texto = texto.replace('.', ',');
      }
    }

    var negativo = texto.charAt(0) === '-';
    var solo = texto.replace(/[^0-9,]/g, '');

    /* Una sola coma: la primera manda, las demas se tiran. */
    var corte = solo.indexOf(',');
    var entero = corte === -1 ? solo : solo.slice(0, corte);
    var decimales = corte === -1 ? null : solo.slice(corte + 1).replace(/,/g, '');

    if (decimales !== null) decimales = decimales.slice(0, DECIMALES);

    /* Los ceros de la izquierda se sacan, pero "0," y "0" se respetan: alguien
       escribiendo "0,50" pasa por "0" y por "0," antes de llegar. */
    entero = entero.replace(/^0+(?=\d)/, '');

    return {
      negativo: negativo && (entero !== '' || decimales !== null),
      entero: entero,
      decimales: decimales
    };
  }

  function conMiles(entero) {
    var partes = [];
    while (entero.length > 3) {
      partes.unshift(entero.slice(-3));
      entero = entero.slice(0, -3);
    }
    partes.unshift(entero);
    return partes.join('.');
  }

  /* El texto que se ve en el campo.

     **La coma a medio escribir se conserva.** Si alguien escribio "1234," y
     esto devolviera "1.234", el siguiente digito seria un millar en vez de un
     centavo y la persona veria su numero multiplicarse por cien. */
  function formatear(texto) {
    var partido = limpiar(texto);
    if (partido.entero === '' && partido.decimales === null) return '';

    var visible = conMiles(partido.entero || '0');
    if (partido.decimales !== null) visible += ',' + partido.decimales;

    return (partido.negativo ? '-' : '') + visible;
  }

  /* Lo que se le manda al backend: punto decimal y sin separadores de miles.

     Devuelve '' si el campo esta vacio, para que la pantalla pueda distinguir
     "no escribio nada" de "escribio cero". */
  function valorDe(input) {
    if (!input) return '';
    var partido = limpiar(input.value);
    if (partido.entero === '' && partido.decimales === null) return '';

    var crudo = (partido.entero || '0');
    if (partido.decimales !== null && partido.decimales !== '') {
      crudo += '.' + partido.decimales;
    }
    return (partido.negativo ? '-' : '') + crudo;
  }

  /* Escribe un monto del backend ("1234.56") en el campo, ya formateado.

     Lo usa la edicion: el formulario se abre con el monto que ya tenia. */
  function escribir(input, valor) {
    if (!input) return;
    if (valor === null || valor === undefined || valor === '') {
      input.value = '';
      return;
    }
    input.value = formatear(String(valor).replace('.', ','));
  }

  /* ------------------------------------------------------- el enganche -- */

  function alEscribir(evento) {
    var input = evento.target;
    if (!input || !input.matches || !input.matches('input[data-monto]')) return;

    var antes = input.value;
    var cursor = input.selectionStart;
    var despues = formatear(antes);

    if (despues === antes) return;

    input.value = despues;

    /* **La cuenta del cursor.** Se mueve exactamente lo que cambio el largo
       del texto, asi queda pegado al digito que se estaba tocando. */
    var corrimiento = despues.length - antes.length;
    var nuevo = Math.max(0, Math.min(despues.length, cursor + corrimiento));

    try {
      input.setSelectionRange(nuevo, nuevo);
    } catch (e) {
      /* Algunos navegadores lanzan si el input no esta enfocado. No es grave:
         el valor ya quedo formateado, que es lo que importa. */
    }
  }

  /* Al salir del campo se completan los centavos: "1.234" pasa a "1.234,00".

     No se hace mientras se tipea, porque agregar ",00" en medio de la
     escritura pelea con la persona en cada tecla. Se hace al salir, que es
     cuando el numero ya esta. */
  function alSalir(evento) {
    var input = evento.target;
    if (!input || !input.matches || !input.matches('input[data-monto]')) return;
    if (!input.value) return;

    var partido = limpiar(input.value);
    if (partido.entero === '' && partido.decimales === null) {
      input.value = '';
      return;
    }

    var decimales = (partido.decimales === null ? '' : partido.decimales);
    decimales = (decimales + '00').slice(0, DECIMALES);

    input.value =
      (partido.negativo ? '-' : '') +
      conMiles(partido.entero || '0') + ',' + decimales;
  }

  document.addEventListener('input', alEscribir);
  /* `focusout` y no `blur`: blur no burbujea, asi que delegado en document no
     se dispara nunca. Es un error silencioso y facil de cometer. */
  document.addEventListener('focusout', alSalir);

  window.MontoInput = {
    valorDe: valorDe,
    escribir: escribir,
    formatear: formatear
  };
}());

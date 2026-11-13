/* ============================================================================
   moneda.js — formato argentino de montos, para MOSTRAR (F2-T17)

   Una sola funcion y un solo lugar. Toda pantalla que muestre plata la usa, y
   ninguna arma su propio formateador.

   ============================================================================
   POR QUE ESTO ES UN MODULO Y NO TRES LINEAS EN CADA PANTALLA
   ============================================================================

   Porque "tres lineas en cada pantalla" fueron, en la iteracion anterior,
   cuatro formatos distintos del mismo numero: la misma expensa se veia como
   "$4849900", "4.849.900", "$ 4849900.00" y "$4.849.900,00" segun donde se
   mirara. Y el consorcista que compara su recibo con la pantalla no sabe si
   son el mismo numero.

   ============================================================================
   LA SEPARACION QUE IMPORTA: MOSTRAR NO ES CALCULAR
   ============================================================================

   Esto formatea para que una persona lea. **No se usa nunca para volver a
   calcular nada.** Los montos llegan del backend como texto decimal exacto
   ("4849900.00") porque son `Numeric` de un extremo al otro; pasarlos por
   `Number()` para mostrarlos y despues sumar esos numeros es como se pierde un
   centavo.

   Si una pantalla necesita un total, lo pide al backend. No hay una sola suma
   de plata en el frontend de este proyecto, y es a proposito.

   ============================================================================
   EL FORMATO, Y POR QUE NO SE USA toLocaleString A SECAS
   ============================================================================

   Argentina usa punto para los miles y coma para los decimales: 4.849.900,00.
   `toLocaleString('es-AR')` lo hace bien, pero recibe un `Number`, y ese es
   justamente el paso que queremos evitar para montos grandes con centavos.

   Asi que se parte el texto por la coma decimal y se agrupan los miles a mano
   sobre la parte entera. Es mas codigo y no pierde ni un centavo, porque nunca
   deja de ser texto.
   ========================================================================= */

(function () {
  'use strict';

  /* Agrupa de a tres desde la derecha: "4849900" -> "4.849.900". */
  function conMiles(entero) {
    var signo = '';
    if (entero.charAt(0) === '-') {
      signo = '-';
      entero = entero.slice(1);
    }

    var partes = [];
    while (entero.length > 3) {
      partes.unshift(entero.slice(-3));
      entero = entero.slice(0, -3);
    }
    partes.unshift(entero);

    return signo + partes.join('.');
  }

  /* Separa un monto en parte entera y decimales, sin pasar por Number.

     Acepta lo que manda el backend ("1234.56"), lo que escribe una persona
     ("1234,56") y un numero ya convertido, por si alguna pantalla lo tiene
     asi. Devuelve null si no hay nada que mostrar. */
  function partir(valor) {
    if (valor === null || valor === undefined || valor === '') return null;

    var texto = String(valor).trim().replace(',', '.');
    if (!texto || isNaN(Number(texto))) return null;

    var negativo = texto.charAt(0) === '-';
    if (negativo) texto = texto.slice(1);

    var corte = texto.indexOf('.');
    var entero = corte === -1 ? texto : texto.slice(0, corte);
    var decimales = corte === -1 ? '' : texto.slice(corte + 1);

    /* Dos decimales exactos, siempre: "1234.5" se muestra "1.234,50". Un
       monto con un solo decimal se lee como si le faltara algo. */
    decimales = (decimales + '00').slice(0, 2);

    return {
      negativo: negativo,
      entero: entero || '0',
      decimales: decimales
    };
  }

  /* El formato completo con el signo de peso: "$ 4.849.900,00".

     El espacio despues del signo es deliberado y es el uso local; sin el,
     "$4.849.900,00" se lee peor en pantalla a 12px. */
  function pesos(valor, opciones) {
    opciones = opciones || {};
    var partido = partir(valor);

    /* Un monto que no existe NO se muestra como "$ 0,00": cero y "no hay dato"
       son dos cosas distintas, y confundirlas en una pantalla de plata es como
       se interpreta un hueco como una deuda saldada. */
    if (!partido) return opciones.vacio !== undefined ? opciones.vacio : '—';

    var cuerpo = conMiles(partido.entero) + ',' + partido.decimales;
    var signo = partido.negativo ? '-' : '';

    /* `conSigno` muestra el "+" de un saldo a favor. Lo pide Mi cuenta: un
       numero sin signo al lado de otro con signo se lee como si los dos
       fueran deuda. */
    if (!partido.negativo && opciones.conSigno && cuerpo !== '0,00') signo = '+';

    return signo + '$ ' + cuerpo;
  }

  /* Sin el signo de peso, para columnas donde el encabezado ya dice que es
     plata y repetir el "$" en cada fila es ruido. */
  function numero(valor, opciones) {
    var completo = pesos(valor, opciones);
    return completo.replace('$ ', '');
  }

  /* Un porcentaje como lo manda el backend ("50.00" o null).

     El null se respeta y no se vuelve cero: en los reportes, "no hay nada
     contra que medir" es distinto de "no se cobro nada", y un cero en lugar de
     un hueco muestra una caida que nunca existio. */
  function porcentaje(valor, opciones) {
    opciones = opciones || {};
    if (valor === null || valor === undefined || valor === '') {
      return opciones.vacio !== undefined ? opciones.vacio : '—';
    }

    var partido = partir(valor);
    if (!partido) return opciones.vacio !== undefined ? opciones.vacio : '—';

    /* Los porcentajes se leen mejor sin decimales cuando son redondos:
       "50%" y no "50,00%". Con decimales reales se muestran. */
    var cuerpo = partido.decimales === '00'
      ? conMiles(partido.entero)
      : conMiles(partido.entero) + ',' + partido.decimales;

    return (partido.negativo ? '-' : '') + cuerpo + '%';
  }

  /* Un periodo "11/2026" como lo escribe una persona: "noviembre de 2026".

     Vive aca y no en cada pantalla porque el periodo acompana a casi todos los
     montos del modulo. **No pasa por `new Date()`**: un "2026-11" convertido a
     fecha se interpreta como medianoche UTC y en Argentina retrocede un dia,
     que es la trampa ya anotada en el catalogo del proyecto. Se parte el texto
     y se busca el nombre en una lista. */
  var MESES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
  ];

  function periodoLargo(periodo) {
    if (!periodo) return '—';
    var partes = String(periodo).split('/');
    if (partes.length !== 2) return periodo;

    var mes = parseInt(partes[0], 10);
    if (!(mes >= 1 && mes <= 12)) return periodo;

    return MESES[mes - 1] + ' de ' + partes[1];
  }

  /* Una fecha "2026-11-05" del backend como "05/11/2026".

     Mismo motivo que arriba: se parte el texto, nunca `new Date()`. */
  function fecha(valor) {
    if (!valor) return '—';
    var partes = String(valor).slice(0, 10).split('-');
    if (partes.length !== 3) return String(valor);
    return partes[2] + '/' + partes[1] + '/' + partes[0];
  }

  window.Moneda = {
    pesos: pesos,
    numero: numero,
    porcentaje: porcentaje,
    periodoLargo: periodoLargo,
    fecha: fecha,
    MESES: MESES
  };
}());

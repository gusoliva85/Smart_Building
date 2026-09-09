// monto-input.js — convierte un <input type="text"> en un campo de monto
// con el formato real de toda la app (Intl 'es-AR', igual que
// assets/js/moneda.js): "." como separador de miles, "," como separador
// decimal, agregado en vivo a medida que se escribe. Reemplaza a
// <input type="number"> en los campos de monto — ese tipo nativo no
// admite ningún separador de miles mientras se tipea (el value model de
// number es siempre un string sin agrupar).
(function () {
  function formatearParteEntera(digitos) {
    return digitos.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  // Reformatea el valor actual del input en cada tecleo, preservando (lo
  // mejor posible) la posición del cursor relativa a lo recién tipeado —
  // el truco de siempre para un campo que se reescribe solo: medir cuánto
  // cambió el largo total y correr el cursor esa misma diferencia.
  function reformatear(input) {
    const cursorOriginal = input.selectionStart;
    const largoOriginal = input.value.length;

    const indiceComa = input.value.indexOf(',');
    const crudo = indiceComa === -1 ? input.value : input.value.slice(0, indiceComa);
    let parteEntera = crudo.replace(/\D/g, '').replace(/^0+(?=\d)/, '');
    const parteDecimal = indiceComa === -1 ? null : input.value.slice(indiceComa + 1).replace(/\D/g, '').slice(0, 2);

    const nuevoValor = indiceComa === -1
      ? formatearParteEntera(parteEntera)
      : `${formatearParteEntera(parteEntera || '0')},${parteDecimal}`;

    input.value = nuevoValor;
    const nuevaPosicion = Math.max(0, cursorOriginal + (nuevoValor.length - largoOriginal));
    input.setSelectionRange(nuevaPosicion, nuevaPosicion);
  }

  // "1.234,5" -> 1234.5 — lo que de verdad viaja al backend.
  function aNumero(valorFormateado) {
    if (!valorFormateado) return 0;
    return Number(valorFormateado.replace(/\./g, '').replace(',', '.')) || 0;
  }

  // Para precargar el campo al editar algo ya existente (ej. "Editar
  // gasto") — mismas 2 decimales que window.Moneda.formatear, sin el "$".
  function formatearParaInput(numero) {
    if (numero === null || numero === undefined || Number.isNaN(Number(numero))) return '';
    return new Intl.NumberFormat('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(numero);
  }

  function habilitar(input) {
    input.addEventListener('input', () => reformatear(input));
  }

  window.MontoInput = { habilitar, aNumero, formatearParaInput };
})();

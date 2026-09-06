// moneda.js — formato de montos en pesos argentinos, centralizado acá
// porque financiero.html es la primera pantalla que muestra dinero real
// (Expensas, Pagos, Deudores, etc. lo van a necesitar igual) — evita que
// cada pantalla nueva arme su propio Intl.NumberFormat suelto.
const FORMATEADOR_ARS = new Intl.NumberFormat('es-AR', {
  style: 'currency',
  currency: 'ARS',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatearMoneda(valor) {
  return FORMATEADOR_ARS.format(Number(valor) || 0);
}

window.Moneda = { formatear: formatearMoneda };

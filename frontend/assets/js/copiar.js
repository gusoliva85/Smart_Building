// copiar.js — copiar un valor al portapapeles desde un icon-btn-sm, con
// feedback visual inmediato: el ícono cambia a un check por un instante.
//
// Nace de la pestaña "Pagos" (Fase 2, Tarea 15): el CBU y el alias del
// edificio se copian por separado (sin QR, decisión final del usuario —
// ver Pagos_y_Conciliacion.md), y el usuario tiene que ver que el click
// realmente copió algo antes de irse a pegarlo en su app de banco
// (heurística "visibilidad del estado del sistema"). Reutilizable en
// cualquier otro dato copiable que aparezca más adelante.
(function () {
  const ICONO_COPIAR = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="8" y="4" width="10" height="14" rx="2"/><path d="M8 8H6a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-2"/></svg>';
  const ICONO_COPIADO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>';

  async function alPortapapeles(boton, texto) {
    try {
      await navigator.clipboard.writeText(texto);
    } catch (error) {
      return; // sin permiso de portapapeles: el botón no da feedback, pero tampoco rompe el flujo
    }
    const tituloOriginal = boton.getAttribute('aria-label');
    boton.innerHTML = ICONO_COPIADO;
    boton.setAttribute('aria-label', 'Copiado');
    setTimeout(() => {
      boton.innerHTML = ICONO_COPIAR;
      boton.setAttribute('aria-label', tituloOriginal);
    }, 1500);
  }

  window.Copiar = { alPortapapeles, ICONO_COPIAR };
})();

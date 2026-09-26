/* ============================================================================
   conexion.js — Indicador de conexion con la API.

   Pregunta por GET /api/salud al cargar la pagina y refleja el resultado en
   el punto luminoso de la topbar. Es la verificacion mas barata de que el
   backend esta levantado: sin esto, un backend apagado se manifiesta recien
   cuando algo falla, y parece un error de la pantalla.

   Se engancha solo a cualquier elemento con data-indicador-conexion.
   Depende de config.js y api.js, cargados antes.

   NO ES UN MONITOR: consulta una vez, al cargar. Un sondeo periodico contra
   un backend serverless despierta la funcion cada pocos segundos para nada.
   ========================================================================== */

(function () {
  'use strict';

  var ESTADOS = ['verificando', 'conectado', 'sin-conexion'];

  function indicadores() {
    return Array.prototype.slice.call(
      document.querySelectorAll('[data-indicador-conexion]')
    );
  }

  function pintar(elemento, estado, etiqueta, detalle) {
    ESTADOS.forEach(function (nombre) { elemento.classList.remove(nombre); });
    elemento.classList.add(estado);

    var texto = elemento.querySelector('span');
    if (texto) texto.textContent = etiqueta;

    elemento.setAttribute('title', detalle);
    /* El estado se anuncia por texto, no solo por color: un lector de
       pantalla no ve el punto, y quien no distingue rojo de azul tampoco. */
    elemento.setAttribute('aria-label', detalle);
  }

  function verificar() {
    var elementos = indicadores();
    if (!elementos.length) return;

    elementos.forEach(function (elemento) {
      pintar(elemento, 'verificando', 'Verificando', 'Verificando la conexion con el servidor');
    });

    /* El catch cubre TODO: backend apagado, CORS mal configurado, un 500.
       Sin el, un backend apagado deja una promesa rechazada sin atender y el
       navegador la reporta como error no manejado en la consola. */
    window.Api.get('/salud').then(
      function (datos) {
        var version = datos && datos.version ? ' v' + datos.version : '';
        elementos.forEach(function (elemento) {
          pintar(
            elemento,
            'conectado',
            'En linea',
            'Conectado a la API' + version + ' (' + window.Config.API + ')'
          );
        });
      },
      function (error) {
        elementos.forEach(function (elemento) {
          pintar(elemento, 'sin-conexion', 'Sin conexion', error.message);
        });
      }
    );
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', verificar);
  } else {
    verificar();
  }

  window.Conexion = { verificar: verificar };
}());

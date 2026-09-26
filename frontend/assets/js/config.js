/* ============================================================================
   config.js — Unica fuente de la URL del backend.

   Ningun otro archivo del frontend escribe una URL de API. Si alguna pantalla
   necesita saber donde vive el backend, lo pregunta aca.

   SE CARGA SIEMPRE ANTES QUE api.js. Si se invierte el orden, api.js arranca
   sin saber a donde pegar y falla con un mensaje que no menciona este archivo.
   ========================================================================== */

(function () {
  'use strict';

  /* El entorno se decide por el hostname, no por una variable de build: no
     hay build. Es la unica forma de que el mismo archivo sirva en local y
     desplegado sin tocarlo. */
  var HOSTS_LOCALES = ['localhost', '127.0.0.1', '0.0.0.0', ''];

  var esLocal = HOSTS_LOCALES.indexOf(window.location.hostname) !== -1;

  /* En local el backend vive en su propio puerto (8000) y el frontend en el
     8090, asi que la URL tiene que ser absoluta — y por eso el backend
     declara esos dos origenes en su whitelist de CORS.

     Desplegado, el backend y el frontend comparten dominio: la ruta relativa
     alcanza, y de paso evita el problema de tener que actualizar un dominio
     escrito a mano cada vez que cambia. */
  var API = esLocal ? 'http://127.0.0.1:8000/api' : '/api';

  window.Config = {
    ES_LOCAL: esLocal,
    API: API,

    /* Claves de localStorage, juntas y en un solo lugar: escritas a mano en
       cada archivo terminan divergiendo por un typo que nadie encuentra. */
    CLAVE_TOKEN: 'token',
    CLAVE_TEMA: 'tema',

    /* A donde se manda al usuario cuando su sesion deja de valer. */
    PAGINA_LOGIN: 'index.html'
  };
}());

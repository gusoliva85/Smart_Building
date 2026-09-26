/* ============================================================================
   api.js — Envoltorio unico de fetch.

   Ninguna pantalla llama a fetch() directo. Todas pasan por aca, y por eso
   todas heredan gratis: el token de sesion, el parseo de JSON, el manejo
   uniforme de errores y la expulsion al login cuando la sesion caduca.

   Depende de config.js, que SIEMPRE se carga antes.
   ========================================================================== */

(function () {
  'use strict';

  var cfg = window.Config;

  /* --------------------------------------------------------------- sesion -- */

  var Sesion = {
    token: function () {
      try {
        return localStorage.getItem(cfg.CLAVE_TOKEN);
      } catch (error) {
        return null;
      }
    },
    guardarToken: function (token) {
      try { localStorage.setItem(cfg.CLAVE_TOKEN, token); } catch (error) { /* modo privado */ }
    },
    limpiar: function () {
      try { localStorage.removeItem(cfg.CLAVE_TOKEN); } catch (error) { /* modo privado */ }
    },
    activa: function () {
      return Boolean(Sesion.token());
    }
  };

  /* ---------------------------------------------------------------- error -- */

  /* Un solo tipo de error para todo el frontend, con el codigo HTTP adentro.
     Eso es lo que permite que una pantalla distinga un 409 ("necesito que
     confirmes") de un 400 cualquiera sin parsear el texto del mensaje. */
  function ErrorApi(mensaje, estado, datos) {
    var error = new Error(mensaje);
    error.name = 'ErrorApi';
    error.estado = estado;        // codigo HTTP, o 0 si no hubo respuesta
    error.datos = datos || null;  // cuerpo crudo, cuando el backend manda mas
    error.esDeRed = estado === 0;
    error.necesitaConfirmacion = estado === 409;
    return error;
  }

  /* FastAPI devuelve el mensaje en "detail". Cuando la validacion de Pydantic
     rechaza el cuerpo (422), "detail" es una LISTA de problemas por campo, no
     un texto: hay que armar algo legible en vez de mostrar "[object Object]". */
  function mensajeDelCuerpo(cuerpo, estado) {
    if (!cuerpo) return 'Error ' + estado;

    var detalle = cuerpo.detail;

    if (typeof detalle === 'string') return detalle;

    if (Array.isArray(detalle)) {
      return detalle.map(function (problema) {
        var campo = (problema.loc || []).filter(function (parte) {
          return parte !== 'body';
        }).join('.');
        return campo ? campo + ': ' + problema.msg : problema.msg;
      }).join(' · ');
    }

    if (typeof cuerpo.mensaje === 'string') return cuerpo.mensaje;

    return 'Error ' + estado;
  }

  /* ---------------------------------------------------------------- pedir -- */

  /**
   * @param {string}  metodo   GET, POST, PATCH, DELETE
   * @param {string}  ruta     Ruta relativa a la API, empezando con "/"
   * @param {object}  cuerpo   Se serializa a JSON. Omitir en GET.
   * @param {object}  opciones { redirigirEn401: boolean }
   */
  function pedir(metodo, ruta, cuerpo, opciones) {
    opciones = opciones || {};

    var cabeceras = {};
    var token = Sesion.token();
    if (token) cabeceras.Authorization = 'Bearer ' + token;

    var init = { method: metodo, headers: cabeceras };
    if (cuerpo !== undefined && cuerpo !== null) {
      cabeceras['Content-Type'] = 'application/json';
      init.body = JSON.stringify(cuerpo);
    }

    return fetch(cfg.API + ruta, init).then(
      function (respuesta) {
        return leerCuerpo(respuesta).then(function (datos) {
          if (respuesta.ok) return datos;
          throw manejarFallo(respuesta.status, datos, opciones);
        });
      },
      function () {
        /* fetch solo rechaza cuando no hubo respuesta: backend apagado, sin
           red, CORS mal configurado. Un 500 NO cae aca, cae arriba. El
           mensaje tiene que ser accionable, no "Failed to fetch". */
        throw ErrorApi(
          'No se pudo contactar al servidor. Verifica que el backend este levantado.',
          0
        );
      }
    );
  }

  function leerCuerpo(respuesta) {
    /* 204 y 205 no traen cuerpo; leerlos como JSON tira un error de parseo. */
    if (respuesta.status === 204 || respuesta.status === 205) {
      return Promise.resolve(null);
    }
    return respuesta.text().then(function (texto) {
      if (!texto) return null;
      try {
        return JSON.parse(texto);
      } catch (error) {
        /* Un error no manejado del servidor puede devolver HTML. Se conserva
           el texto para poder mirarlo, sin romper el flujo. */
        return { detail: texto };
      }
    });
  }

  function manejarFallo(estado, datos, opciones) {
    var mensaje = mensajeDelCuerpo(datos, estado);

    /* 401 significa "tu sesion no vale": se limpia y se vuelve al login.
       LA EXCEPCION DELIBERADA es el propio login, donde un 401 significa
       "credenciales incorrectas" y hay que MOSTRARLO en el formulario, no
       expulsar al usuario de la pantalla en la que ya esta. Esa pantalla
       pasa redirigirEn401: false. */
    if (estado === 401 && opciones.redirigirEn401 !== false) {
      Sesion.limpiar();
      if (window.location.pathname.indexOf(cfg.PAGINA_LOGIN) === -1) {
        window.location.href = cfg.PAGINA_LOGIN;
      }
      return ErrorApi('Tu sesion vencio. Volve a iniciar sesion.', 401, datos);
    }

    return ErrorApi(mensaje, estado, datos);
  }

  /* --------------------------------------------------------------- publico -- */

  window.Api = {
    get: function (ruta, opciones) { return pedir('GET', ruta, null, opciones); },
    post: function (ruta, cuerpo, opciones) { return pedir('POST', ruta, cuerpo, opciones); },
    patch: function (ruta, cuerpo, opciones) { return pedir('PATCH', ruta, cuerpo, opciones); },
    borrar: function (ruta, opciones) { return pedir('DELETE', ruta, null, opciones); },
    pedir: pedir,
    Sesion: Sesion,
    ErrorApi: ErrorApi
  };
}());

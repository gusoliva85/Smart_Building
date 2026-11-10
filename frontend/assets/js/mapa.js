/* ============================================================================
   mapa.js — Geocodificacion (Nominatim) y mapa (Leaflet).

   Lo usa el alta de edificio: al completar direccion y CP se busca la
   ubicacion y se muestra en un mapa dentro del propio formulario, para que
   quien carga el edificio VEA si el sistema entendio la direccion antes de
   guardarla. Un par de coordenadas escrito en una columna no se puede
   verificar mirandolo; un pin en una esquina, si.

   ==========================================================================
   LA REGLA QUE ORDENA TODO ESTE ARCHIVO: AVISAR, NUNCA BLOQUEAR
   ==========================================================================

   Nada de lo que pasa aca puede impedir dar de alta un edificio. Ni que
   Nominatim no encuentre la direccion, ni que conteste con un error, ni que
   el CDN de Leaflet no cargue, ni que el navegador no tenga internet. Una
   calle nueva puede no estar indexada todavia, y un edificio que existe en la
   realidad tiene que poder cargarse igual. Las coordenadas son un dato
   opcional del edificio —la columna es anulable a proposito— y este archivo
   trata cada fallo como "no hay coordenadas", no como un error del alta.

   Por eso ninguna promesa de este modulo se rechaza por un fallo de la
   busqueda: `geocodificar()` resuelve con `null` cuando no hay resultado y con
   un objeto cuando lo hay. Quien llama no necesita un try/catch para que la
   pantalla siga funcionando.

   ==========================================================================
   POR QUE NOMINATIM Y LEAFLET, Y POR QUE SE CARGAN TARDE
   ==========================================================================

   Nominatim (OpenStreetMap) y Leaflet no piden clave de API ni facturacion,
   que es la razon por la que estan elegidos en el Documento Tecnico en lugar
   de Google Maps o Mapbox: el proyecto no depende de una credencial externa
   que haya que renovar ni de una tarjeta asociada.

   Leaflet se carga **la primera vez que se abre un mapa**, no al abrir la
   pantalla. Son unos 160 KB entre el script y su hoja de estilos, y el
   listado de edificios —que es lo que se mira casi siempre— no los necesita.
   Se piden una sola vez por pagina: la promesa queda guardada, asi que abrir
   el modal cinco veces no vuelve a descargar nada.

   Las dos URLs llevan `integrity`, que es lo que hace que el navegador
   verifique el contenido antes de ejecutarlo: si el CDN devolviera un archivo
   distinto al que se probo, el script no corre. Y van con la version clavada
   (`1.9.4`), no con un rango: "la ultima" significa que el dia que publiquen
   una version nueva cambia el codigo que corre en produccion sin que nadie
   haya tocado el proyecto.

   No depende de config.js ni de api.js, y es deliberado: estos dos servicios
   no son el backend de SMART Building. Van por fetch directo, y las reglas de
   api.js —el token de sesion, la expulsion al login en un 401— no tienen
   ningun sentido contra un servidor de terceros.
   ========================================================================== */

(function () {
  'use strict';

  /* ------------------------------------------------------------ constantes -- */

  var LEAFLET_VERSION = '1.9.4';
  var LEAFLET_JS = 'https://unpkg.com/leaflet@' + LEAFLET_VERSION + '/dist/leaflet.js';
  var LEAFLET_CSS = 'https://unpkg.com/leaflet@' + LEAFLET_VERSION + '/dist/leaflet.css';

  /* Huellas de los dos archivos de la version 1.9.4, medidas sobre lo que
     sirve el CDN. Si alguna vez se cambia la version hay que recalcularlas:
     con la huella vieja, el navegador rechaza el archivo nuevo y el mapa deja
     de aparecer sin un error que lo explique. */
  var LEAFLET_JS_SRI = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';
  var LEAFLET_CSS_SRI = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';

  var NOMINATIM = 'https://nominatim.openstreetmap.org/search';

  /* La politica de uso de Nominatim es de un pedido por segundo como maximo,
     y es un servicio gratuito sostenido por donaciones: respetarla no es una
     formalidad, es la condicion para seguir usandolo. Se cumple de dos formas
     a la vez — no se busca mientras se tipea (ver cuando lo llama edificios.js)
     y, ademas, dos busquedas seguidas se separan al menos este tiempo. */
  var MINIMO_ENTRE_PEDIDOS = 1100;

  /* Si el servicio no contesta en este tiempo, se abandona y se sigue sin
     coordenadas. Un formulario que espera indefinidamente a un servidor de
     terceros es un formulario trabado. */
  var TIMEOUT = 10000;

  /* El pais se fija: este sistema administra consorcios argentinos, y sin esto
     "Avenida Rivadavia 1234" puede resolver en otro continente. */
  var PAIS = 'ar';

  /* Zoom al que se muestra una direccion encontrada: lo suficiente para
     reconocer la cuadra, que es lo que se esta verificando. */
  var ZOOM_DIRECCION = 17;

  /* Estado del modulo, declarado todo junto arriba. Es la convencion del
     proyecto: una variable declarada mas abajo de donde la usa el codigo que
     corre al inicio explota con "Cannot access before initialization". */
  var cargaDeLeaflet = null;   /* la promesa, una sola vez por pagina */
  var ultimoPedido = 0;        /* cuando se le pidio algo a Nominatim */
  var abortador = null;        /* para cancelar la busqueda anterior */

  /* ------------------------------------------------------ carga de Leaflet -- */

  function agregarHoja() {
    /* Si ya esta puesta no se duplica: dos veces la misma hoja no rompe nada,
       pero deja el <head> sucio y confunde al depurar. */
    if (document.querySelector('link[data-leaflet]')) return;

    var hoja = document.createElement('link');
    hoja.rel = 'stylesheet';
    hoja.href = LEAFLET_CSS;
    hoja.integrity = LEAFLET_CSS_SRI;
    /* crossOrigin es obligatorio para que integrity se pueda verificar: sin
       el, el navegador no puede leer el contenido de una respuesta de otro
       dominio y descarta el recurso. */
    hoja.crossOrigin = 'anonymous';
    hoja.setAttribute('data-leaflet', '');
    document.head.appendChild(hoja);
  }

  /**
   * Carga Leaflet una sola vez y resuelve con `L`.
   *
   * La promesa se guarda: dos llamadas simultaneas —abrir el modal mientras
   * todavia esta cargando— comparten la misma descarga en vez de pedirla dos
   * veces.
   *
   * @returns {Promise<object>} el objeto global de Leaflet.
   */
  function cargarLeaflet() {
    if (window.L) return Promise.resolve(window.L);
    if (cargaDeLeaflet) return cargaDeLeaflet;

    cargaDeLeaflet = new Promise(function (resolver, rechazar) {
      agregarHoja();

      var script = document.createElement('script');
      script.src = LEAFLET_JS;
      script.integrity = LEAFLET_JS_SRI;
      script.crossOrigin = 'anonymous';
      script.async = true;

      script.onload = function () {
        if (window.L) {
          resolver(window.L);
          return;
        }
        /* El script cargo pero no dejo el global: pasa si el CDN devuelve una
           pagina de error con codigo 200. */
        rechazar(new Error('Leaflet cargó pero no quedó disponible.'));
      };

      script.onerror = function () {
        /* Tambien entra por aca cuando la verificacion de `integrity` falla.
           Se limpia la promesa guardada para que un segundo intento —el
           usuario que vuelve a abrir el modal con la red ya restablecida—
           pueda reintentar la descarga en vez de recibir el fallo viejo. */
        cargaDeLeaflet = null;
        rechazar(new Error('No se pudo cargar el mapa.'));
      };

      document.head.appendChild(script);
    });

    return cargaDeLeaflet;
  }

  /* ------------------------------------------------------- geocodificacion -- */

  /* Arma el texto de busqueda. El CP va junto con la direccion porque es lo
     que la desambigua: "San Martin 500" existe en cientos de localidades
     argentinas, y el codigo postal es justamente el dato que el alta pide en
     lugar de la ciudad (es mas preciso para geocodificar y determina la
     localidad y la provincia, asi que guardar las tres seria tener el mismo
     dato tres veces). */
  function consulta(direccion, cp) {
    var partes = [];
    if (direccion) partes.push(String(direccion).trim());
    if (cp) partes.push(String(cp).trim());
    return partes.filter(Boolean).join(', ');
  }

  function esperarElTurno() {
    var desde = Date.now() - ultimoPedido;
    if (desde >= MINIMO_ENTRE_PEDIDOS) return Promise.resolve();

    return new Promise(function (resolver) {
      window.setTimeout(resolver, MINIMO_ENTRE_PEDIDOS - desde);
    });
  }

  /**
   * Busca una direccion y devuelve su ubicacion, o null.
   *
   * NUNCA RECHAZA. Un fallo de red, un error del servicio o una direccion que
   * no existe son todos el mismo resultado desde la pantalla: no hay
   * coordenadas, y el alta sigue. Quien llama distingue los casos por el
   * `motivo` del objeto que devuelve.
   *
   * @param {string} direccion
   * @param {string} cp
   * @returns {Promise<{encontrada: boolean, motivo: string,
   *                    latitud: number, longitud: number, etiqueta: string}>}
   */
  function geocodificar(direccion, cp) {
    var texto = consulta(direccion, cp);

    if (!texto) {
      return Promise.resolve({ encontrada: false, motivo: 'sin-datos' });
    }

    /* Se cancela la busqueda anterior: si alguien corrige el CP mientras la
       primera viaja, la respuesta vieja podria llegar despues y pintar en el
       mapa la direccion que ya no es. */
    if (abortador) abortador.abort();
    abortador = new AbortController();
    var senial = abortador.signal;

    var parametros = new URLSearchParams({
      q: texto,
      format: 'jsonv2',
      limit: '1',
      countrycodes: PAIS,
      /* El idioma de la etiqueta que se muestra debajo del mapa. */
      'accept-language': 'es'
    });

    return esperarElTurno().then(function () {
      ultimoPedido = Date.now();

      var vencido = window.setTimeout(function () {
        if (abortador) abortador.abort();
      }, TIMEOUT);

      return fetch(NOMINATIM + '?' + parametros.toString(), {
        method: 'GET',
        signal: senial,
        /* Sin cabeceras propias a proposito: cualquier cabecera que no sea de
           las simples convierte esto en un pedido con preflight, y un servicio
           publico de terceros no tiene por que responder uno. El navegador
           manda el Referer solo, que es la forma en que Nominatim identifica
           a la aplicacion que consulta (el User-Agent no se puede fijar desde
           el navegador). */
        headers: {}
      }).then(function (respuesta) {
        window.clearTimeout(vencido);
        if (!respuesta.ok) {
          return { encontrada: false, motivo: 'servicio' };
        }
        return respuesta.json().then(leerResultado);
      }, function () {
        window.clearTimeout(vencido);
        /* Entra por aca tanto la falta de red como la cancelacion. Se tratan
           igual: en los dos casos no hay coordenadas para mostrar. */
        return { encontrada: false, motivo: 'red' };
      });
    });
  }

  function leerResultado(datos) {
    if (!Array.isArray(datos) || !datos.length) {
      return { encontrada: false, motivo: 'no-encontrada' };
    }

    var primero = datos[0];
    var latitud = parseFloat(primero.lat);
    var longitud = parseFloat(primero.lon);

    /* Si el servicio devolviera algo que no se puede leer como numero, es un
       resultado que no sirve: mejor "no se encontro" que un pin en el
       meridiano cero. */
    if (isNaN(latitud) || isNaN(longitud)) {
      return { encontrada: false, motivo: 'no-encontrada' };
    }

    return {
      encontrada: true,
      motivo: 'ok',
      latitud: latitud,
      longitud: longitud,
      etiqueta: primero.display_name || ''
    };
  }

  /* ------------------------------------------------------------- el mapa --- */

  /**
   * Monta un mapa dentro de un contenedor y devuelve como manejarlo.
   *
   * @param {HTMLElement} contenedor
   * @returns {Promise<{ubicar: Function, limpiar: Function, destruir: Function}>}
   */
  function montar(contenedor) {
    return cargarLeaflet().then(function (L) {
      var mapa = L.map(contenedor, {
        /* La rueda del mouse NO hace zoom, y es una decision: este mapa vive
           dentro de un formulario en un modal con scroll propio. Con el zoom
           por rueda prendido, alguien que baja la pagina con el puntero
           encima del mapa termina en una vista satelital de Sudamerica en vez
           de llegar al boton de guardar. Se hace zoom con los botones y, en
           mobile, pellizcando. */
        scrollWheelZoom: false,
        /* El control de atribucion se arma a mano abajo para poder acortar el
           texto: el de Leaflet agrega su propio nombre con un enlace, y el
           credito que corresponde dar es el de los datos (OpenStreetMap). */
        attributionControl: false,
        zoomControl: true
      });

      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19
      }).addTo(mapa);

      L.control.attribution({ prefix: false })
        .addAttribution('&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>')
        .addTo(mapa);

      var marcador = null;

      /* Leaflet mide el contenedor cuando se crea el mapa. Si el contenedor
         estaba oculto —dentro de un modal que todavia no se abrio, que es
         exactamente este caso— mide cero y el mapa queda gris con los mosaicos
         a medio cargar. invalidateSize() lo obliga a medir de nuevo, y hay que
         llamarlo DESPUES de que el contenedor sea visible. */
      function remedir() {
        mapa.invalidateSize();
      }

      function ubicar(latitud, longitud) {
        mapa.setView([latitud, longitud], ZOOM_DIRECCION);

        if (marcador) {
          marcador.setLatLng([latitud, longitud]);
        } else {
          marcador = L.marker([latitud, longitud]).addTo(mapa);
        }

        /* El pin recien agregado puede quedar fuera de vista si el contenedor
           cambio de tamanio mientras el mapa estaba oculto. */
        remedir();
      }

      function limpiar() {
        if (!marcador) return;
        mapa.removeLayer(marcador);
        marcador = null;
      }

      function destruir() {
        mapa.remove();
      }

      return {
        ubicar: ubicar,
        limpiar: limpiar,
        remedir: remedir,
        destruir: destruir,
        /* Expuesto para el caso raro en que una pantalla necesite el mapa
           crudo. Hoy no lo usa nadie. */
        leaflet: mapa
      };
    });
  }

  /* -------------------------------------------------------------- publico -- */

  window.Mapa = {
    geocodificar: geocodificar,
    montar: montar,
    /* Para una pantalla que quiera precargar Leaflet antes de abrir el modal.
       Hoy no lo usa nadie: la carga tardia es justamente el comportamiento
       buscado. */
    precargar: cargarLeaflet,
    ZOOM_DIRECCION: ZOOM_DIRECCION
  };
}());

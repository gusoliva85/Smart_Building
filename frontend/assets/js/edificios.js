/* ============================================================================
   edificios.js — Logica de la pantalla de edificios (edificios.html).

   Un .js por pantalla, igual que usuarios.js: se ocupa solo de SU pantalla y
   apoya todo lo transversal en los modulos compartidos (api.js, layout.js,
   formularios.js, cargando.js, mapa.js).

   Lo que hace:
     1. Monta el esqueleto por layout.js, declarando quien puede entrar.
     2. Lista los edificios del alcance de quien mira, con sus dos conteos.
     3. Da de alta uno nuevo en un modal, geocodificando la direccion.

   Desde `F1-T26` tambien **decide cual de las dos vistas se muestra**: con
   `?id=` en la URL monta el detalle —que vive en `edificio-detalle.js`— y sin
   nada, el listado. Es lo unico que los dos archivos comparten: ninguno lee
   variables del otro.

   LO QUE NO HACE, Y ES A PROPOSITO: no edita ni da de baja un edificio. La
   edicion de los datos de identidad (nombre, direccion, CP, CUIT) no tiene
   endpoint todavia —`PATCH /api/edificios/{id}` es de configuracion— y la
   baja logica del edificio tampoco. Cuando existan, van en el detalle.

   Depende de config.js, api.js, cargando.js, mapa.js, layout.js y
   edificio-detalle.js, cargados antes.
   ========================================================================== */

(function () {
  'use strict';

  /* Los roles que pueden ver esta pantalla. Es la misma lista que la fila de
     la tabla de accesos de layout.js, y es deliberado que este escrita dos
     veces: la tabla decide que se MUESTRA en el menu, esto decide que pasa si
     alguien escribe la URL a mano. Son dos preguntas distintas, y ninguna de
     las dos es el control real — ese lo hace el backend en cada endpoint. */
  var ROLES_HABILITADOS = ['admin_general', 'admin_consorcio'];

  /* El alta es exclusiva del Administrador General (el endpoint la limita a
     ese rol), mientras el listado lo ven los dos. Por eso el boton de "Nuevo
     edificio" se muestra por separado y no alcanza con el permiso de la
     pantalla. */
  var ROL_ADMIN_GENERAL = 'admin_general';

  /* Todo el estado de la pantalla declarado junto arriba. Es la convencion del
     proyecto y viene de un error cometido tres veces: una variable declarada
     mas abajo de donde la usa el codigo que corre al inicio explota con
     "Cannot access before initialization". */
  var pantalla = {};
  var usuarioSesion = null;    /* quien esta mirando */
  var ultimoFoco = null;       /* a donde vuelve el foco al cerrar el modal */
  var mapa = null;             /* el controlador que devuelve mapa.js */
  var mapaFallo = false;       /* el CDN no cargo: no se reintenta en loop */
  var coordenadas = null;      /* lo ultimo que geocodifico, o null */
  var textoGeocodificado = ''; /* para no repetir la misma busqueda */
  var buscando = false;        /* hay una busqueda en vuelo */

  /* ------------------------------------------------------------ utilidades -- */

  /* El id del edificio que se esta mirando, o null si estamos en el listado.

     Vive en la URL y no en una variable por tres razones concretas: F5 no te
     saca del edificio en el que estabas, el boton de atras del navegador
     vuelve al listado sin que haya que programar nada, y el enlace de un
     edificio se puede mandar por mensaje. Un ruteo en memoria pierde las tres.

     Se valida que sea un entero positivo: con `?id=hola` el backend
     responderia un 422 que habla de tipos, y lo correcto es no pedir nada. */
  function idDeLaUrl() {
    var crudo = new URLSearchParams(window.location.search).get('id');
    if (!crudo) return null;
    var numero = Number(crudo);
    if (!Number.isInteger(numero) || numero < 1) return null;
    return numero;
  }

  function icono(contenido, ancho) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
           'stroke-width="' + (ancho || 1.8) + '" stroke-linecap="round" ' +
           'stroke-linejoin="round" aria-hidden="true">' + contenido + '</svg>';
  }

  /* Escapa lo que va a entrar por innerHTML.

     Hace falta de verdad, no por formalismo: el nombre y la direccion los
     escribio una persona y viajaron por la red. Un nombre con un "<" rompe el
     listado entero, y uno con una etiqueta <script> lo ejecuta. */
  function textoSeguro(valor) {
    if (valor === null || valor === undefined) return '';
    return String(valor)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* "7 pisos" / "1 piso". El plural se arma aca y no con un ternario repetido
     en cada lugar que muestra un conteo. */
  function plural(cantidad, singular, plural_) {
    return cantidad + ' ' + (cantidad === 1 ? singular : plural_);
  }

  /* ------------------------------------------------------------- mensajes --- */

  function mostrarError(caja, texto, mensaje) {
    texto.textContent = mensaje;
    caja.hidden = false;
  }

  function limpiarError(caja, texto) {
    caja.hidden = true;
    texto.textContent = '';
  }

  /* El aviso de "se creo" se inserta arriba de la lista y se va solo: el
     edificio nuevo ya esta visible en el listado, que es la confirmacion de
     verdad. Un cartel que se queda obliga a cerrarlo a mano o se acumula con
     el siguiente. */
  function avisarExito(mensaje) {
    var aviso = document.createElement('div');
    aviso.className = 'mensaje-exito';
    aviso.setAttribute('role', 'status');
    aviso.innerHTML = icono('<path d="M20 6L9 17l-5-5"/>', 2) + '<span></span>';
    aviso.querySelector('span').textContent = mensaje;

    pantalla.lista.parentNode.insertBefore(aviso, pantalla.lista);
    window.setTimeout(function () {
      if (aviso.parentNode) aviso.parentNode.removeChild(aviso);
    }, 5000);
  }

  /* --------------------------------------------------------------- listado -- */

  function htmlDeFila(edificio) {
    /* Los datos secundarios van en una sola linea separados por un punto
       medio. El CUIT solo aparece si existe: un " · " colgando al final se lee
       como un dato que falta. */
    var secundarios = [edificio.direccion, 'CP ' + edificio.cp];
    if (edificio.cuit) secundarios.push('CUIT ' + edificio.cuit);

    /* Sin coordenadas se dice con palabras y no con un icono solo: es un dato
       que falta y que se completa en la configuracion del edificio, no un
       error. */
    if (edificio.latitud === null || edificio.longitud === null) {
      secundarios.push('sin ubicación en el mapa');
    }

    /* El conteo de unidades es el dato que mas se consulta de un edificio
       —determina el reparto de la expensa— asi que va en la ranura de la
       derecha, donde en el listado de usuarios va el rol. */
    var tamanio = plural(edificio.cantidad_departamentos, 'unidad', 'unidades') +
                  ' · ' + plural(edificio.cantidad_pisos, 'piso', 'pisos');

    /* Es un <a> y no un <button> con JavaScript: asi funcionan el clic del
       medio, el "abrir en pestaña nueva" y el arrastre al marcador. Y el
       destino es una URL de verdad, que es lo que hace que el detalle se
       pueda compartir. */
    var enlace =
      '<a class="boton-primario boton-secundario boton-chico" ' +
        'href="edificios.html?id=' + edificio.id + '" ' +
        'aria-label="Abrir ' + textoSeguro(edificio.nombre) + '">Abrir</a>';

    return '<article class="fila-lista content-glass' +
           (edificio.activo ? '' : ' inactiva') + '">' +
             '<div class="fila-lista-dato">' +
               '<b>' + textoSeguro(edificio.nombre) + '</b>' +
               '<span>' + textoSeguro(secundarios.join(' · ')) + '</span>' +
             '</div>' +
             '<div class="fila-lista-acciones">' +
               '<span class="fila-lista-estado rol-badge">' +
                 textoSeguro(tamanio) +
               '</span>' +
               '<div class="fila-lista-botones">' + enlace + '</div>' +
             '</div>' +
           '</article>';
  }

  function pintarListado(edificios) {
    if (!edificios.length) {
      /* El texto depende del rol, porque "no hay edificios" significa dos
         cosas distintas: el Administrador General no creo ninguno todavia, y
         el Administrador de Consorcio no tiene ninguno asignado — que no es
         algo que pueda resolver solo. Decirle "creá el primero" a quien no
         tiene el boton seria mandarlo a buscar algo que no existe. */
      pantalla.lista.innerHTML = puedeCrear()
        ? '<div class="lista-vacia"><b>Todavía no hay edificios</b>' +
          'Creá el primero con el botón de arriba: con los pisos y las ' +
          'unidades por piso se genera toda la estructura.</div>'
        : '<div class="lista-vacia"><b>No tenés edificios asignados</b>' +
          'Cuando el Administrador General te asigne uno, va a aparecer ' +
          'acá.</div>';
      return;
    }

    pantalla.lista.innerHTML = edificios.map(htmlDeFila).join('');
  }

  function cargarListado() {
    limpiarError(pantalla.errorListado, pantalla.textoErrorListado);
    pantalla.lista.innerHTML =
      '<div class="lista-vacia">' + window.Cargando.html() + '</div>';

    return window.Api.get('/edificios').then(
      function (edificios) {
        pintarListado(edificios);
      },
      function (error) {
        /* La lista se vacia: dejar las filas viejas debajo de un error de
           recarga muestra datos que ya no se sabe si siguen siendo ciertos. */
        pantalla.lista.innerHTML = '';
        mostrarError(
          pantalla.errorListado,
          pantalla.textoErrorListado,
          error.message
        );
      }
    );
  }

  /* ------------------------------------------------------------- el mapa --- */

  function decirEstadoDelMapa(mensaje) {
    pantalla.estadoMapa.textContent = mensaje || '';
  }

  function mostrarVacioDelMapa(mensaje) {
    pantalla.mapaVacio.textContent = mensaje;
    pantalla.mapaVacio.hidden = false;
  }

  /* Monta el mapa la primera vez que hace falta.

     Se monta DESPUES de abrir el modal y no al cargar la pantalla, por dos
     razones: Leaflet son unos 160 KB que el listado no necesita, y un mapa
     creado dentro de un contenedor oculto mide cero y queda gris (de eso se
     ocupa `remedir()` en mapa.js, pero conviene no depender de un remedido
     para el caso normal).

     Si la carga falla, se deja dicho con palabras y NO se reintenta en cada
     busqueda: el alta no necesita el mapa para funcionar. */
  function asegurarMapa() {
    if (mapa) return Promise.resolve(mapa);
    if (mapaFallo) return Promise.resolve(null);

    return window.Mapa.montar(pantalla.contenedorMapa).then(
      function (control) {
        mapa = control;
        /* El contenedor ya es visible en este punto, asi que el mapa puede
           medirse bien. */
        mapa.remedir();
        return mapa;
      },
      function () {
        mapaFallo = true;
        mostrarVacioDelMapa(
          'No se pudo cargar el mapa. La dirección se guarda igual: el mapa ' +
          'es solo para verificarla.'
        );
        return null;
      }
    );
  }

  /* Pide la ubicacion y la muestra.

     `motivo` es el por que, no un codigo de error: cada caso necesita una
     frase distinta, y las cuatro terminan diciendo lo mismo —que el edificio
     se puede guardar igual— porque es verdad. La columna de coordenadas es
     anulable justamente para esto: una calle nueva puede no estar indexada
     todavia, y eso no es motivo para no poder cargar un edificio que existe.

     @param {boolean} aPedido true si lo pidio el boton. Cambia los textos: una
       busqueda automatica que no encuentra nada avisa; una pedida a mano tiene
       que contestar siempre algo, aunque sea "faltan datos". */
  function buscarUbicacion(aPedido) {
    var direccion = pantalla.campoDireccion.value.trim();
    var cp = pantalla.campoCp.value.trim();
    var texto = direccion + '|' + cp;

    if (!direccion || !cp) {
      if (aPedido) {
        decirEstadoDelMapa('Completá la dirección y el código postal para ' +
                           'buscar la ubicación.');
      }
      return;
    }

    /* Ya se busco exactamente esto. Sin esta guarda, salir y volver a entrar
       al campo de CP sin cambiar nada dispara otro pedido a un servicio
       publico y gratuito que pide, con razon, que no se lo use de mas. Si el
       boton se aprieta a proposito, se busca igual: puede ser un reintento
       despues de un fallo de red. */
    if (!aPedido && texto === textoGeocodificado) return;
    if (buscando) return;

    buscando = true;
    textoGeocodificado = texto;
    decirEstadoDelMapa('Buscando la dirección…');
    pantalla.botonBuscar.disabled = true;

    window.Mapa.geocodificar(direccion, cp).then(function (resultado) {
      buscando = false;
      pantalla.botonBuscar.disabled = false;

      if (!resultado.encontrada) {
        /* Las coordenadas anteriores se descartan: si alguien corrige la
           direccion y la nueva no se encuentra, dejar el pin viejo guardaria
           la ubicacion de la direccion equivocada. */
        coordenadas = null;
        if (mapa) mapa.limpiar();

        decirEstadoDelMapa(mensajeDeFallo(resultado.motivo));

        /* Si el fallo fue de red o del servicio, la proxima vez conviene
           reintentar: se olvida la busqueda para que salir y volver a entrar
           al campo vuelva a intentarlo. Una direccion que no existe en el
           mapa, en cambio, no va a aparecer por reintentar. */
        if (resultado.motivo !== 'no-encontrada') textoGeocodificado = '';
        return;
      }

      coordenadas = {
        latitud: resultado.latitud,
        longitud: resultado.longitud
      };

      decirEstadoDelMapa(
        resultado.etiqueta
          ? 'Se encontró: ' + resultado.etiqueta
          : 'Dirección encontrada.'
      );

      asegurarMapa().then(function (control) {
        if (!control) return;
        pantalla.mapaVacio.hidden = true;
        control.ubicar(coordenadas.latitud, coordenadas.longitud);
      });
    });
  }

  function mensajeDeFallo(motivo) {
    if (motivo === 'no-encontrada') {
      return 'No encontramos esa dirección en el mapa. Podés guardar el ' +
             'edificio igual: la ubicación se completa después.';
    }
    if (motivo === 'servicio') {
      return 'El servicio de mapas no respondió bien. Podés guardar el ' +
             'edificio igual y volver a intentarlo más tarde.';
    }
    /* 'red' y cualquier otro caso que aparezca. */
    return 'No se pudo consultar el mapa. Revisá tu conexión, o guardá el ' +
           'edificio igual: la ubicación no es obligatoria.';
  }

  /* --------------------------------------------------------- modal de alta -- */

  function puedeCrear() {
    return Boolean(usuarioSesion) && usuarioSesion.rol === ROL_ADMIN_GENERAL;
  }

  /* Dice cuanto se va a generar, con los dos numeros que hay escritos.

     Se muestra ANTES de guardar porque es la unica parte del alta que crea
     filas que despues hay que corregir a mano: 7 pisos por 4 unidades son 28
     departamentos, y leer ese numero antes es mas facil que borrar veinte
     unidades de mas despues. */
  function actualizarResumen() {
    var pisos = parseInt(pantalla.campoPisos.value, 10);
    var porPiso = parseInt(pantalla.campoUnidades.value, 10);

    if (!pisos || !porPiso || pisos < 1 || porPiso < 1) {
      pantalla.resumen.textContent = '';
      return;
    }

    pantalla.resumen.textContent =
      'Se van a generar ' + plural(pisos, 'piso', 'pisos') + ' con ' +
      plural(pisos * porPiso, 'unidad', 'unidades') + ' en total, numeradas ' +
      'por piso (1A, 1B, 2A…).';
  }

  function abrirModal() {
    /* Quien abrio el modal, para devolverle el foco al cerrarlo. Sin esto, al
       cerrar con Escape el foco se va al <body> y el siguiente Tab arranca
       desde el principio de la pagina. */
    ultimoFoco = document.activeElement;

    pantalla.formulario.reset();
    coordenadas = null;
    textoGeocodificado = '';
    decirEstadoDelMapa('');
    actualizarResumen();
    limpiarError(pantalla.errorAlta, pantalla.textoErrorAlta);

    /* El mapa vuelve a su estado inicial: el pin del edificio anterior no
       tiene nada que ver con este. */
    if (mapa) mapa.limpiar();
    mostrarVacioDelMapa(
      'Completá la dirección y el código postal: la ubicación se busca sola ' +
      'al salir del campo.'
    );

    pantalla.modal.classList.add('abierto');
    pantalla.campoNombre.focus();
  }

  function cerrarModal() {
    pantalla.modal.classList.remove('abierto');
    pantalla.formulario.reset();
    limpiarError(pantalla.errorAlta, pantalla.textoErrorAlta);
    if (ultimoFoco && ultimoFoco.focus) ultimoFoco.focus();
  }

  function modalAbierto() {
    return pantalla.modal.classList.contains('abierto');
  }

  /* ------------------------------------------------------------------ alta -- */

  function bloquearEnvio(bloqueado) {
    pantalla.botonCrear.disabled = bloqueado;
    pantalla.botonCrear.textContent = bloqueado ? 'Creando…' : 'Crear edificio';
  }

  function guardar(evento) {
    evento.preventDefault();
    limpiarError(pantalla.errorAlta, pantalla.textoErrorAlta);

    var nombre = pantalla.campoNombre.value.trim();
    var direccion = pantalla.campoDireccion.value.trim();
    var cp = pantalla.campoCp.value.trim();
    var cuit = pantalla.campoCuit.value.trim();
    var pisos = parseInt(pantalla.campoPisos.value, 10);
    var porPiso = parseInt(pantalla.campoUnidades.value, 10);

    /* Validacion minima en el cliente, solo para no gastar un viaje de ida y
       vuelta en algo que ya se sabe que esta incompleto. NO duplica la del
       backend: los largos, el formato y los topes de pisos y unidades los
       valida el backend, que es el que manda — y los topes salen de
       `services/finanzas.py`, asi que escribirlos aca seria tener el mismo
       numero en dos lugares. */
    if (!nombre || !direccion || !cp) {
      mostrarError(pantalla.errorAlta, pantalla.textoErrorAlta,
                   'Completá el nombre, la dirección y el código postal.');
      return;
    }

    if (!pisos || !porPiso) {
      mostrarError(pantalla.errorAlta, pantalla.textoErrorAlta,
                   'Indicá cuántos pisos tiene y cuántas unidades hay por piso.');
      return;
    }

    bloquearEnvio(true);

    /* null y no "" cuando no hay CUIT: el esquema lo acepta como opcional, y
       una cadena vacia guardada se lee despues como un CUIT que existe y esta
       en blanco, no como uno que no se cargo.

       Las coordenadas van solo si se encontraron. Si no, viajan en null, que
       es lo que la columna admite a proposito. */
    var datos = {
      nombre: nombre,
      direccion: direccion,
      cp: cp,
      cuit: cuit || null,
      latitud: coordenadas ? coordenadas.latitud : null,
      longitud: coordenadas ? coordenadas.longitud : null,
      cantidad_pisos: pisos,
      unidades_por_piso: porPiso
    };

    window.Api.post('/edificios', datos).then(function (creado) {
      cerrarModal();
      /* El mensaje lo arma el backend y dice exactamente que se genero
         ("Se creó el edificio con 7 pisos y 28 unidades."). Escribirlo de
         nuevo aca seria una segunda version de la misma frase, capaz de
         quedar en desacuerdo con lo que de verdad se guardo. */
      avisarExito(creado.mensaje);
      return cargarListado();
    }).catch(function (error) {
      /* El error se muestra DENTRO del modal, que sigue abierto con todo lo
         tipeado en su lugar. Cerrarlo obligaria a escribir los seis campos de
         nuevo por un nombre repetido. */
      mostrarError(pantalla.errorAlta, pantalla.textoErrorAlta, error.message);
    }).then(function () {
      bloquearEnvio(false);
    });
  }

  /* --------------------------------------------------------------- arranque -- */

  function engancharModal() {
    pantalla.botonNuevo.addEventListener('click', abrirModal);
    pantalla.botonCerrar.addEventListener('click', cerrarModal);
    pantalla.botonCancelar.addEventListener('click', cerrarModal);
    pantalla.formulario.addEventListener('submit', guardar);

    /* La busqueda se dispara al SALIR del campo, no mientras se tipea.

       Es la diferencia entre un pedido por direccion y uno por cada letra:
       Nominatim es un servicio publico y gratuito que pide un maximo de un
       pedido por segundo, y buscar "A", "Av", "Av.", "Av. R"… es exactamente
       lo que no hay que hacer. Buscar al salir del campo es ademas cuando el
       dato esta completo, que es cuando el resultado sirve. */
    pantalla.campoDireccion.addEventListener('blur', function () {
      buscarUbicacion(false);
    });
    pantalla.campoCp.addEventListener('blur', function () {
      buscarUbicacion(false);
    });

    /* El boton existe para el reintento: una busqueda que fallo por red, o una
       direccion que se corrigio en el mapa mental de quien carga. */
    pantalla.botonBuscar.addEventListener('click', function () {
      buscarUbicacion(true);
    });

    pantalla.campoPisos.addEventListener('input', actualizarResumen);
    pantalla.campoUnidades.addEventListener('input', actualizarResumen);

    /* A PROPOSITO: ningun listener de clic en el backdrop. Este modal no se
       cierra tocando afuera — perder seis campos y una busqueda de direccion
       por un clic al costado es un problema real. Escape si lo cierra, porque
       es una accion intencional. */
    document.addEventListener('keydown', function (evento) {
      if (evento.key === 'Escape' && modalAbierto()) cerrarModal();
    });
  }

  function iniciar() {
    pantalla = {
      vistaListado: document.getElementById('vista-listado'),
      lista: document.getElementById('lista-edificios'),
      errorListado: document.getElementById('error-listado'),
      textoErrorListado: document.querySelector('[data-texto-error-listado]'),

      botonNuevo: document.getElementById('boton-nuevo'),
      modal: document.getElementById('modal-alta'),
      botonCerrar: document.getElementById('boton-cerrar-modal'),
      botonCancelar: document.getElementById('boton-cancelar'),
      botonCrear: document.getElementById('boton-crear'),

      formulario: document.getElementById('form-alta'),
      campoNombre: document.getElementById('campo-nombre'),
      campoDireccion: document.getElementById('campo-direccion'),
      campoCp: document.getElementById('campo-cp'),
      campoCuit: document.getElementById('campo-cuit'),
      campoPisos: document.getElementById('campo-pisos'),
      campoUnidades: document.getElementById('campo-unidades'),
      resumen: document.querySelector('[data-resumen-estructura]'),

      contenedorMapa: document.getElementById('mapa-contenedor'),
      mapaVacio: document.querySelector('[data-mapa-vacio]'),
      estadoMapa: document.querySelector('[data-mapa-estado]'),
      botonBuscar: document.getElementById('boton-buscar-mapa'),

      errorAlta: document.getElementById('error-alta'),
      textoErrorAlta: document.querySelector('[data-texto-error-alta]')
    };

    /* Guarda barata: si este archivo se incluyera en otra pagina, no tira un
       error de consola sobre un elemento nulo. */
    if (!pantalla.lista) return;

    /* El esqueleto primero. Si no hay sesion, layout.js redirige al login y
       devuelve una promesa que no se resuelve nunca, asi que nada de lo que
       sigue corre. Lo mismo si el rol no esta habilitado. */
    window.Layout.montar({ roles: ROLES_HABILITADOS }).then(function (usuario) {
      usuarioSesion = usuario;

      /* EL RUTEO, y es lo primero que se decide: con `?id=` esta pantalla no
         es un listado, es el detalle de un edificio. Se esconde la vista del
         listado y se le pasa el control al otro modulo, que ya tiene su propio
         HTML en este mismo archivo.

         El usuario se le pasa en vez de que lo pida de nuevo: `Layout.montar`
         ya consulto `/auth/me`, y un segundo pedido para saber lo mismo es un
         viaje de red que no hace falta. */
      var id = idDeLaUrl();
      if (id !== null) {
        pantalla.vistaListado.hidden = true;
        window.EdificioDetalle.montar(id, usuario);
        return;
      }

      /* El boton de alta aparece solo para quien puede crear. El listado, en
         cambio, lo ven los dos roles — el Administrador de Consorcio ve
         unicamente los edificios que administra, y eso lo filtra el backend,
         no esta pantalla. */
      if (puedeCrear()) {
        pantalla.botonNuevo.hidden = false;
        engancharModal();
      }

      cargarListado();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
}());

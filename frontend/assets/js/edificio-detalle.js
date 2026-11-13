/* ============================================================================
   edificio-detalle.js — Las tres pestañas del edificio (F1-T26).

   Vive en el mismo archivo HTML que el listado (`edificios.html`) y se monta
   solo cuando la URL trae `?id=`. Quien decide eso es `edificios.js`, que es
   el modulo de la pantalla; este se ocupa de una vista.

   ==========================================================================
   POR QUE ESTO ES UN ARCHIVO APARTE Y NO MAS CODIGO EN edificios.js
   ==========================================================================

   La convencion del proyecto es un `.js` por pantalla, y la sigo: las dos
   vistas son la misma pantalla y comparten el HTML. Lo que no comparten es
   nada mas: el listado tiene un formulario con un mapa, y el detalle tiene
   tres pestañas, trece operaciones de estructura y cinco bloques de
   configuracion que se guardan por separado. Juntos pasaban las mil lineas, y
   el propio Documento Frontend anota que a `financiero.js` le paso eso y
   llego a 1400 con ocho sub-pestañas.

   El limite entre los dos archivos es el que importa: `edificios.js` rutea y
   maneja el listado y el alta; este archivo recibe un id y se ocupa de todo
   lo que pasa adentro de un edificio. Ninguno lee variables del otro — el
   unico contacto es `window.EdificioDetalle.montar(id, usuario)`.

   ==========================================================================
   LA ESTRUCTURA SE MUESTRA EN LISTA, NO GRAFICA
   ==========================================================================

   La vista grafica del edificio, con los pisos coloreados por estado, es el
   Dashboard Visual de la Fase 5. No se adelanta nada de eso aca, ni
   parcialmente: media version grafica es trabajo que despues hay que rehacer
   y una expectativa que no se cumple. Lo que hace falta ahora es poder
   corregir y completar la estructura, y para eso una lista es mejor.

   Depende de config.js, api.js, cargando.js, confirmar.js, copiar.js,
   view-switch.js y layout.js, cargados antes.
   ========================================================================== */

(function () {
  'use strict';

  /* El rol que puede cambiar quien administra el edificio. No es el mismo que
     puede entrar a la pantalla: los dos administradores ven el detalle, pero
     los responsables los decide la plataforma. Si un Administrador de
     Consorcio pudiera tocarlos, podria sacarse a si mismo —perdiendo el acceso
     al edificio sin forma de recuperarlo— o asignarse un edificio ajeno. El
     backend lo rechaza con un 403; esto es para no ofrecerselo. */
  var ROL_ADMIN_GENERAL = 'admin_general';

  /* La pestaña que se ve al abrir. Datos y no Estructura porque es lo primero
     que se quiere confirmar al entrar a un edificio: que es el que se buscaba
     y quien esta a cargo. */
  var VISTA_INICIAL = 'datos';

  /* Todo el estado declarado junto arriba. Es la convencion del proyecto y
     viene de un error cometido tres veces: una variable declarada mas abajo de
     donde la usa el codigo que corre al inicio explota con "Cannot access
     before initialization". */
  var pantalla = {};
  var edificioId = null;
  var usuarioSesion = null;
  var detalle = null;       /* la ultima respuesta de GET /edificios/{id} */
  var coeficientes = null;  /* la ultima respuesta de GET /coeficientes */
  var opciones = null;      /* catalogos y topes, se piden una sola vez */
  var asignables = null;    /* candidatos por rol para los desplegables */
  var formularioAbierto = null;  /* el que guarda el modal generico */
  var mapa = null;          /* el controlador de mapa.js, una sola vez */
  var mapaFallo = false;    /* el CDN no cargo: no se reintenta en loop */
  var ultimoFoco = null;

  /* ------------------------------------------------------------ utilidades -- */

  function icono(contenido, ancho) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
           'stroke-width="' + (ancho || 1.8) + '" stroke-linecap="round" ' +
           'stroke-linejoin="round" aria-hidden="true">' + contenido + '</svg>';
  }

  var ICONO_LAPIZ =
    '<path d="M4 20h4l10-10a2.1 2.1 0 0 0-3-3L5 17v3z"/>' +
    '<path d="M14.5 6.5l3 3"/>';

  var ICONO_TACHO =
    '<path d="M4 7h16"/>' +
    '<path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>' +
    '<path d="M6 7l1 12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-12"/>';

  var ICONO_MAS = '<path d="M12 5v14M5 12h14"/>';

  /* Escapa lo que va a entrar por innerHTML. Hace falta de verdad: el nombre
     de un piso, el identificador de una unidad y las reglas de uso de un
     espacio comun los escribio una persona. Un "<" rompe la lista entera y
     una etiqueta <script> se ejecuta. */
  function textoSeguro(valor) {
    if (valor === null || valor === undefined) return '';
    return String(valor)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function plural(cantidad, singular, plural_) {
    return cantidad + ' ' + (cantidad === 1 ? singular : plural_);
  }

  /* Un numero decimal como lo escribe la gente en castellano: coma. Solo para
     MOSTRAR; lo que se manda al backend viaja con punto, que es lo que espera
     el JSON. */
  function conComa(valor) {
    if (valor === null || valor === undefined || valor === '') return '';
    return String(valor).replace('.', ',');
  }

  /* La fecha de alta, corta y en castellano. Si el texto no trae zona horaria
     se le agrega la Z: el backend guarda en UTC y, sobre SQLite, la fecha
     vuelve sin offset — sin esto el navegador la leeria como hora local y un
     edificio creado hoy a la noche podria mostrarse con la fecha de mañana. */
  function fechaCorta(iso) {
    if (!iso) return '';
    var texto = String(iso);
    if (!/(Z|[+-]\d\d:?\d\d)$/.test(texto)) texto += 'Z';
    var fecha = new Date(texto);
    if (isNaN(fecha.getTime())) return '';
    return fecha.toLocaleDateString('es-AR', {
      day: 'numeric', month: 'long', year: 'numeric'
    });
  }

  function puedeTocarResponsables() {
    return Boolean(usuarioSesion) && usuarioSesion.rol === ROL_ADMIN_GENERAL;
  }

  /* --------------------------------------------------------------- avisos --- */

  function mostrarError(caja, texto, mensaje) {
    texto.textContent = mensaje;
    caja.hidden = false;
    /* El error del detalle vive arriba de las pestañas, asi que si se esta
       mirando la de abajo puede quedar fuera de la pantalla. Se lleva la vista
       hasta el: un error que no se ve es un error que no existe para quien
       aprieta el boton por segunda vez. */
    if (caja === pantalla.errorDetalle && caja.scrollIntoView) {
      caja.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function limpiarError(caja, texto) {
    caja.hidden = true;
    texto.textContent = '';
  }

  function errorDelDetalle(mensaje) {
    mostrarError(pantalla.errorDetalle, pantalla.textoErrorDetalle, mensaje);
  }

  /* El aviso de que algo se guardo se inserta arriba de las pestañas y se va
     solo: lo que confirma de verdad es el dato ya cambiado en la lista, y un
     cartel que se queda obliga a cerrarlo a mano o se acumula con el
     siguiente. */
  function avisarExito(mensaje) {
    var aviso = document.createElement('div');
    aviso.className = 'mensaje-exito';
    aviso.setAttribute('role', 'status');
    aviso.innerHTML = icono('<path d="M20 6L9 17l-5-5"/>', 2) + '<span></span>';
    aviso.querySelector('span').textContent = mensaje;

    pantalla.pestanias.parentNode.insertBefore(aviso, pantalla.pestanias);
    window.setTimeout(function () {
      if (aviso.parentNode) aviso.parentNode.removeChild(aviso);
    }, 5000);
  }

  /* ---------------------------------------------------------------- carga --- */

  function cargarTodo() {
    limpiarError(pantalla.errorDetalle, pantalla.textoErrorDetalle);

    /* Los tres pedidos van en paralelo y no en cadena: son independientes y
       encadenarlos triplicaria la espera contra un backend serverless, donde
       cada viaje cuesta. */
    var pedidos = [
      window.Api.get('/edificios/' + edificioId),
      window.Api.get('/edificios/' + edificioId + '/asignables'),
      opciones ? Promise.resolve(opciones) : window.Api.get('/edificios/opciones'),
      window.Api.get('/edificios/' + edificioId + '/coeficientes')
    ];

    return Promise.all(pedidos).then(
      function (respuestas) {
        detalle = respuestas[0];
        asignables = respuestas[1];
        opciones = respuestas[2];
        coeficientes = respuestas[3];
        pintarTodo();
      },
      function (error) {
        /* El 404 del backend es deliberadamente igual para un edificio que no
           existe y para uno fuera del alcance de quien consulta, asi que el
           texto no puede afirmar cual de los dos es. */
        pantalla.pestanias.hidden = true;
        errorDelDetalle(
          error.estado === 404
            ? 'No encontramos este edificio, o no está entre los que administrás.'
            : error.message
        );
      }
    );
  }

  /* Recarga despues de un cambio. Se vuelven a pedir las dos cosas que un
     cambio puede haber movido —el edificio y los candidatos— y no las
     opciones, que son constantes del backend. */
  function recargar() {
    return Promise.all([
      window.Api.get('/edificios/' + edificioId),
      window.Api.get('/edificios/' + edificioId + '/asignables'),
      /* Los coeficientes se vuelven a pedir aunque el cambio haya sido en otra
         pestaña: agregar o borrar una unidad cambia la suma, y una suma vieja
         es peor que ninguna — diria que el edificio esta listo para liquidar
         cuando le falta la unidad que se acaba de crear. */
      window.Api.get('/edificios/' + edificioId + '/coeficientes')
    ]).then(function (respuestas) {
      detalle = respuestas[0];
      asignables = respuestas[1];
      coeficientes = respuestas[2];
      pintarTodo();
    }, function (error) {
      errorDelDetalle(error.message);
    });
  }

  function pintarTodo() {
    pantalla.pestanias.hidden = false;
    pintarCabecera();
    pintarDatos();
    pintarEstructura();
    pintarCoeficientes();
    pintarConfiguracion();
  }

  /* ------------------------------------------------------------- cabecera -- */

  function pintarCabecera() {
    var edificio = detalle.edificio;

    document.title = edificio.nombre + ' · SMART Building';
    pantalla.nombre.textContent = edificio.nombre;

    var partes = [edificio.direccion, 'CP ' + edificio.cp];
    if (!edificio.activo) partes.push('inactivo');
    pantalla.bajada.textContent = partes.join(' · ');

    pantalla.tamanio.textContent =
      plural(detalle.cantidad_departamentos, 'unidad', 'unidades') + ' · ' +
      plural(detalle.cantidad_pisos, 'piso', 'pisos');
  }

  /* -------------------------------------------------------- pestaña Datos -- */

  function htmlDeDato(etiqueta, valor, textoSiFalta) {
    var hay = valor !== null && valor !== undefined && valor !== '';
    return '<div class="ficha-dato">' +
             '<div class="ficha-dato-label">' + textoSeguro(etiqueta) + '</div>' +
             '<div class="ficha-dato-valor' + (hay ? '' : ' vacio') + '">' +
               textoSeguro(hay ? valor : (textoSiFalta || 'Sin cargar')) +
             '</div>' +
           '</div>';
  }

  function pintarDatos() {
    var edificio = detalle.edificio;

    var ubicacion = (edificio.latitud !== null && edificio.longitud !== null)
      ? conComa(edificio.latitud) + ', ' + conComa(edificio.longitud)
      : null;

    pantalla.fichaIdentidad.innerHTML =
      htmlDeDato('Dirección', edificio.direccion) +
      htmlDeDato('Código postal', edificio.cp) +
      htmlDeDato('CUIT', edificio.cuit) +
      htmlDeDato('Coordenadas', ubicacion,
                 'No se geocodificó la dirección') +
      htmlDeDato('Alta', fechaCorta(edificio.creado_en)) +
      htmlDeDato('Estado', edificio.activo ? 'Activo' : 'Inactivo');

    pintarResponsables();
    pintarMapaDelEdificio();

    pantalla.emergenciaNombre.value = edificio.contacto_emergencia_nombre || '';
    pantalla.emergenciaTelefono.value = edificio.contacto_emergencia_telefono || '';
  }

  /* Busca un candidato por id dentro de una de las listas de asignables.
     Devuelve null si no esta, que es el caso de un responsable cuya cuenta se
     desactivo despues de haber sido asignado. */
  function candidato(lista, id) {
    if (!id) return null;
    for (var i = 0; i < lista.length; i += 1) {
      if (lista[i].id === id) return lista[i];
    }
    return null;
  }

  /* El nombre de quien ocupa un puesto o una unidad.

     Si el id esta cargado pero la persona no aparece entre los candidatos, su
     cuenta esta desactivada: se dice asi, con el id, en vez de mostrar un
     hueco. El hueco haria pensar que el puesto esta libre, y no lo esta — y
     eso explica por que el edificio puede estar funcionando con un encargado
     que no puede entrar al sistema. */
  function nombreDe(lista, id) {
    if (!id) return null;
    var persona = candidato(lista, id);
    if (persona) return persona.nombre + ' · ' + persona.email;
    return 'Usuario #' + id + ' (cuenta desactivada)';
  }

  /* El mapa de la ubicacion, en la pestaña Datos.

     Es el mismo modulo que usa el alta (`mapa.js`) y aca no geocodifica nada:
     muestra el punto que quedo guardado. Sirve para verificar de un vistazo
     que el edificio esta donde tiene que estar — un par de coordenadas en una
     ficha no se puede verificar mirandolo, un pin en una esquina si.

     Se monta tarde, igual que en el alta: son unos 160 KB de Leaflet que no
     hacen falta si quien entra va directo a la pestaña de Estructura. Y se
     remide cada vez que se vuelve a la pestaña, porque Leaflet mide su
     contenedor al crearse y un contenedor oculto mide cero.

     Si no hay coordenadas no se monta nada: se explica por que no hay. */
  function pintarMapaDelEdificio() {
    var edificio = detalle.edificio;
    var hayUbicacion = edificio.latitud !== null && edificio.longitud !== null;

    if (!hayUbicacion) {
      pantalla.mapaVacio.textContent =
        'No se encontró esta dirección en el mapa cuando se dio de alta el ' +
        'edificio, así que no quedaron coordenadas guardadas. No es un ' +
        'problema para operar: se usan en los reportes y en el dashboard.';
      pantalla.mapaVacio.hidden = false;
      return;
    }

    if (mapaFallo) return;

    var latitud = Number(edificio.latitud);
    var longitud = Number(edificio.longitud);

    if (mapa) {
      pantalla.mapaVacio.hidden = true;
      mapa.ubicar(latitud, longitud);
      return;
    }

    window.Mapa.montar(pantalla.contenedorMapa).then(
      function (control) {
        mapa = control;
        pantalla.mapaVacio.hidden = true;
        mapa.ubicar(latitud, longitud);
        mapa.remedir();
      },
      function () {
        /* El CDN no cargo. No se reintenta en cada cambio de pestaña, y sobre
           todo no se muestra un error: el mapa es una verificacion visual, no
           un dato que falte. */
        mapaFallo = true;
        pantalla.mapaVacio.textContent =
          'No se pudo cargar el mapa. Las coordenadas guardadas son ' +
          conComa(edificio.latitud) + ', ' + conComa(edificio.longitud) + '.';
        pantalla.mapaVacio.hidden = false;
      }
    );
  }

  function pintarResponsables() {
    var edificio = detalle.edificio;

    if (!puedeTocarResponsables()) {
      /* Al Administrador de Consorcio se le muestran los dos puestos como
         datos, no como un desplegable deshabilitado: un control gris que no se
         puede usar invita a preguntarse por que, y la respuesta no esta en la
         pantalla. */
      pantalla.notaResponsables.textContent =
        'Quién administra el edificio lo define el Administrador General. Si ' +
        'hay que cambiarlo, se lo pedís a él.';
      pantalla.formResponsables.hidden = true;
      pantalla.fichaResponsables.hidden = false;
      pantalla.fichaResponsables.innerHTML =
        htmlDeDato('Administrador de Consorcio',
                   nombreDe(asignables.admin_consorcio, edificio.admin_consorcio_id),
                   'Sin asignar') +
        htmlDeDato('Encargado',
                   nombreDe(asignables.encargado, edificio.encargado_id),
                   'Sin asignar');
      return;
    }

    pantalla.notaResponsables.textContent =
      'Solo vos podés cambiar esto: si un Administrador de Consorcio pudiera, ' +
      'podría sacarse a sí mismo y perder el acceso al edificio. Los ' +
      'desplegables traen únicamente usuarios activos con el rol que el ' +
      'puesto exige. Dejar "Sin asignar" desvincula a quien esté.';
    pantalla.fichaResponsables.hidden = true;
    pantalla.formResponsables.hidden = false;

    llenarSelectDePersonas(
      pantalla.campoAdminConsorcio, asignables.admin_consorcio,
      edificio.admin_consorcio_id
    );
    llenarSelectDePersonas(
      pantalla.campoEncargado, asignables.encargado, edificio.encargado_id
    );
  }

  /* Llena un <select> de personas y deja seleccionada la que esta asignada.

     Si el asignado no esta entre los candidatos —cuenta desactivada— se le
     agrega una opcion propia. Sin eso, el navegador ignoraria el valor
     desconocido, el desplegable mostraria "Sin asignar", y guardar el
     formulario por cualquier otro motivo **desvincularia a esa persona sin que
     nadie lo haya pedido**. */
  function llenarSelectDePersonas(select, candidatos, idAsignado) {
    select.innerHTML = '';

    var vacia = document.createElement('option');
    vacia.value = '';
    vacia.textContent = 'Sin asignar';
    select.appendChild(vacia);

    candidatos.forEach(function (persona) {
      var opcion = document.createElement('option');
      opcion.value = String(persona.id);
      /* textContent y no innerHTML: el nombre y el email vienen de la red. */
      opcion.textContent = persona.nombre + ' (' + persona.email + ')';
      select.appendChild(opcion);
    });

    if (idAsignado && !candidato(candidatos, idAsignado)) {
      var desactivada = document.createElement('option');
      desactivada.value = String(idAsignado);
      desactivada.textContent = 'Usuario #' + idAsignado + ' (cuenta desactivada)';
      select.appendChild(desactivada);
    }

    select.value = idAsignado ? String(idAsignado) : '';
  }

  /* --------------------------------------------------- pestaña Estructura -- */

  function botonesDeFila(acciones) {
    return '<div class="fila-hija-botones">' + acciones.join('') + '</div>';
  }

  /* Un boton de accion de una fila: agregar, editar o borrar.

     `variante` es la que da el color, y el color dice QUE hace: `sumar` va
     rellena con el acento (es la accion que agrega), `editar` usa el acento en
     vidrio y `borrar` el rojo del semaforo — la unica excepcion a que el
     semaforo no decore, porque "destructivo" es una convencion universal y no
     es un estado del edificio.

     `textoCorto` es la etiqueta que se ve **solo en telefono**. Tres iconos
     sueltos al lado de un campo, en 390 px de ancho, no entran bien y no se
     entienden; con etiqueta se reparten el ancho en columnas parejas. Desde
     640 px el CSS la esconde y el boton vuelve a ser cuadrado.

     `aria-label` va siempre y es la frase larga ("Borrar la unidad 3A"): es lo
     que escucha un lector de pantalla, y "Borrar" a secas no dice que. */
  function botonAccion(accion, id, etiqueta, dibujo, variante, textoCorto) {
    return '<button type="button" class="accion ' + variante + '" ' +
           'data-accion="' + accion + '" data-id="' + id + '" ' +
           'aria-label="' + textoSeguro(etiqueta) + '">' +
           icono(dibujo, 1.9) +
           '<span class="accion-texto">' + textoSeguro(textoCorto) + '</span>' +
           '</button>';
  }

  function htmlDeUnidad(unidad) {
    var secundarios = [];

    if (unidad.m2 !== null) secundarios.push(conComa(unidad.m2) + ' m²');

    var propietario = nombreDe(asignables.propietario, unidad.propietario_id);
    var inquilino = nombreDe(asignables.inquilino, unidad.inquilino_id);

    if (propietario) secundarios.push('Propietario: ' + propietario);
    if (inquilino) secundarios.push('Inquilino: ' + inquilino);
    if (!propietario && !inquilino) secundarios.push('sin ocupantes');
    if (unidad.coeficiente === null) secundarios.push('sin coeficiente');

    /* El coeficiente se edita ACA, en la fila de la unidad, y no en una
       segunda lista.

       Primero estuvo en un bloque aparte que listaba todas las unidades otra
       vez, y estaba mal: la misma unidad aparecia dos veces en la misma
       pantalla y habia que buscar en cual de las dos listas estaba lo que se
       queria cambiar. La unidad es la fila, y en la fila va todo lo suyo.

       Lo que SI queda arriba es el estado del edificio —cuanto suman y si se
       puede liquidar— y las dos acciones que se aplican a todas las unidades
       juntas. Eso no es la lista repetida: es lo que no se puede leer unidad
       por unidad. */
    /* El campo va con **coma**, que es como se escribe un decimal en
       castellano, y eso obliga a `type="text"`: un `type="number"` rechaza la
       coma —el navegador la descarta y el campo queda vacio— y ese era el
       origen del punto. `inputmode="decimal"` igual abre el teclado numerico
       en telefono, asi que no se pierde nada.

       La etiqueta visible solo se ve en telefono: en una fila de escritorio el
       contexto alcanza, y en una tarjeta apilada no. */
    var campoDelCoeficiente =
      '<div class="campo-coeficiente">' +
        '<span class="campo-coeficiente-label">Coeficiente</span>' +
        '<div class="campo-coeficiente-caja">' +
          '<input type="text" inputmode="decimal" ' +
            'data-coeficiente-de="' + unidad.id + '" ' +
            'aria-label="Coeficiente de la unidad ' +
              textoSeguro(unidad.identificador) + '" ' +
            'placeholder="0,000" ' +
            'value="' + (unidad.coeficiente === null
                          ? '' : textoSeguro(conComa(unidad.coeficiente))) + '">' +
          '<span class="campo-coeficiente-sufijo">%</span>' +
        '</div>' +
      '</div>';

    /* La pill de "sin cargar" va DENTRO de la fila, al lado del
       identificador: el amarillo del fondo no comunica solo, nunca. */
    var aviso = unidad.coeficiente === null
      ? ' <span class="pill warn">' +
          icono('<path d="M12 8v4M12 16h.01"/><circle cx="12" cy="12" r="9"/>', 2.4) +
          'sin cargar</span>'
      : '';

    return '<div class="fila-hija' + (unidad.ocupado ? '' : ' libre') +
             (unidad.coeficiente === null ? ' sin-coeficiente' : '') + '">' +
             '<div class="fila-hija-dato">' +
               '<b>' + textoSeguro(unidad.identificador) + aviso + '</b>' +
               '<span>' + textoSeguro(secundarios.join(' · ')) + '</span>' +
             '</div>' +
             campoDelCoeficiente +
             botonesDeFila([
               botonAccion('editar-unidad', unidad.id,
                           'Editar la unidad ' + unidad.identificador,
                           ICONO_LAPIZ, 'editar', 'Editar'),
               botonAccion('borrar-unidad', unidad.id,
                           'Borrar la unidad ' + unidad.identificador,
                           ICONO_TACHO, 'borrar', 'Borrar')
             ]) +
           '</div>';
  }

  function htmlDePiso(piso) {
    var unidades = piso.departamentos.map(htmlDeUnidad).join('');

    /* El numero del piso en un circulo con relieve, y la cabecera con una
       banda teñida: antes era un bloque blanco con texto negro y no habia
       forma de ver donde empezaba un piso sin leer. */
    var acciones =
      '<div class="grupo-piso-acciones">' +
        botonAccion('nueva-unidad', piso.id,
                    'Agregar una unidad al piso ' + piso.numero,
                    ICONO_MAS, 'sumar', 'Unidad') +
        botonAccion('editar-piso', piso.id,
                    'Editar el piso ' + piso.numero,
                    ICONO_LAPIZ, 'editar', 'Piso') +
        botonAccion('borrar-piso', piso.id,
                    'Borrar el piso ' + piso.numero,
                    ICONO_TACHO, 'borrar', 'Borrar') +
      '</div>';

    return '<div class="grupo-piso content-glass">' +
             '<div class="grupo-piso-cabecera">' +
               '<div class="grupo-piso-numero">' + textoSeguro(piso.numero) + '</div>' +
               '<div class="grupo-piso-nombre">Piso ' + textoSeguro(piso.numero) +
                 '<span>' + plural(piso.departamentos.length, 'unidad', 'unidades') +
                 ' · posición ' + textoSeguro(piso.orden) + '</span>' +
               '</div>' +
               acciones +
             '</div>' +
             (unidades ||
              '<div class="lista-vacia">Este piso no tiene unidades.</div>') +
           '</div>';
  }

  function htmlDeCochera(cochera) {
    var unidad = unidadPorId(cochera.departamento_id);
    var secundarios = [cochera.tipo === 'fija' ? 'Fija' : 'Rotativa'];
    if (cochera.departamento_id) {
      secundarios.push('asignada a ' +
        (unidad ? unidad.identificador : '#' + cochera.departamento_id));
    } else if (cochera.tipo === 'fija') {
      secundarios.push('sin asignar');
    }

    return '<div class="fila-hija">' +
             '<div class="fila-hija-dato">' +
               '<b>Cochera ' + textoSeguro(cochera.numero) + '</b>' +
               '<span>' + textoSeguro(secundarios.join(' · ')) + '</span>' +
             '</div>' +
             botonesDeFila([
               botonAccion('editar-cochera', cochera.id,
                           'Editar la cochera ' + cochera.numero,
                           ICONO_LAPIZ, 'editar', 'Editar'),
               botonAccion('borrar-cochera', cochera.id,
                           'Borrar la cochera ' + cochera.numero,
                           ICONO_TACHO, 'borrar', 'Borrar')
             ]) +
           '</div>';
  }

  function htmlDeEspacio(espacio) {
    var secundarios = [];
    if (espacio.capacidad !== null) {
      secundarios.push(plural(espacio.capacidad, 'persona', 'personas'));
    }
    if (espacio.reglas_uso) secundarios.push(espacio.reglas_uso);
    if (!secundarios.length) secundarios.push('sin capacidad ni reglas cargadas');

    return '<div class="fila-hija">' +
             '<div class="fila-hija-dato">' +
               '<b>' + textoSeguro(espacio.nombre) + '</b>' +
               '<span>' + textoSeguro(secundarios.join(' · ')) + '</span>' +
             '</div>' +
             botonesDeFila([
               botonAccion('editar-espacio', espacio.id,
                           'Editar ' + espacio.nombre,
                           ICONO_LAPIZ, 'editar', 'Editar'),
               botonAccion('borrar-espacio', espacio.id,
                           'Borrar ' + espacio.nombre,
                           ICONO_TACHO, 'borrar', 'Borrar')
             ]) +
           '</div>';
  }

  function pintarEstructura() {
    pantalla.listaPisos.innerHTML = detalle.pisos.length
      ? detalle.pisos.map(htmlDePiso).join('')
      : '<div class="lista-vacia"><b>Este edificio no tiene pisos</b>' +
        'Agregá el primero con el botón de arriba.</div>';

    pantalla.listaCocheras.innerHTML = detalle.cocheras.length
      ? detalle.cocheras.map(htmlDeCochera).join('')
      : '<div class="lista-vacia">No hay cocheras cargadas.</div>';

    pantalla.listaEspacios.innerHTML = detalle.espacios_comunes.length
      ? detalle.espacios_comunes.map(htmlDeEspacio).join('')
      : '<div class="lista-vacia">No hay espacios comunes cargados.</div>';
  }

  /* ============================================================= */
  /* COEFICIENTES (F1-T27)                                         */
  /* ============================================================= */

  /* El coeficiente es el porcentaje de la expensa que paga cada unidad, y es
     **el** dato del que depende todo el modulo financiero: sin coeficientes
     cargados no hay expensa posible. En la iteracion anterior no habia forma
     de cargarlos desde la interfaz y el problema aparecio recien al intentar
     liquidar, con un mensaje que no decia ni cuantas unidades faltaban ni
     cuales. Por eso este bloque muestra siempre las cuatro cosas: la suma, si
     es 100% exacto, cuantas faltan y cuales son las primeras.

     NO SE CALCULA NADA ACA. La suma, el "suma_cien" y el mensaje los manda el
     backend en cada respuesta — las tres operaciones devuelven el estado
     completo del edificio. Sumar los valores en JavaScript con numeros de
     punto flotante daria 99.99999999999999 para un edificio que suma 100
     exacto, y la pantalla diria que no se puede liquidar un edificio que si
     se puede. El dato de si cierra o no lo tiene el que hace las cuentas con
     Decimal. */

  function pintarEstadoDeLaSuma() {
    var estado = coeficientes;
    var cierra = Boolean(estado.suma_cien);

    pantalla.pillSuma.hidden = false;
    pantalla.pillSuma.className = 'pill ' + (cierra ? 'ok' : 'crit');
    /* El color nunca comunica solo: el texto dice el porcentaje. Es la regla
       del sistema de diseño y acá importa el doble, porque la diferencia entre
       99,999% y 100,000% no se ve en un color. */
    pantalla.pillSuma.textContent = 'Suman ' + conComa(estado.suma) + '%';

    /* La barra, que es la lectura de un vistazo. El ancho se calcula con la
       suma tal como la mando el backend; el 100% exacto lo decide `suma_cien`
       y no este porcentaje, porque 99,9995 redondeado tambien daria 100. */
    var porcentaje = Math.max(0, Math.min(100, parseFloat(estado.suma) || 0));

    pantalla.panelTotal.hidden = estado.cantidad_unidades === 0;
    pantalla.panelTotal.classList.toggle('cierra', cierra);
    pantalla.totalBarra.classList.toggle('cierra', cierra);
    /* querySelector y no firstChild: un espacio en el HTML entre el div y el
       span haria que firstChild sea un nodo de texto, y eso rompe el pintado
       entero con un error que no menciona el espacio. */
    pantalla.totalBarra.querySelector('span').style.width = porcentaje + '%';
    pantalla.totalNumero.textContent = conComa(estado.suma) + '%';
    pantalla.totalEtiqueta.textContent = cierra
      ? 'Coeficientes cargados · el edificio puede liquidar'
      : (estado.unidades_sin_coeficiente
          ? 'Coeficientes cargados · ' +
            plural(estado.unidades_sin_coeficiente, 'unidad', 'unidades') +
            ' sin cargar'
          : 'Coeficientes cargados · no suman 100%');

    pantalla.totalChips.innerHTML =
      '<span class="chip">' +
        textoSeguro(plural(estado.cantidad_unidades, 'unidad', 'unidades')) +
      '</span>' +
      '<span class="chip">' +
        textoSeguro(plural(detalle ? detalle.cantidad_pisos : 0, 'piso', 'pisos')) +
      '</span>';

    /* El mensaje lo escribe el backend y nombra las primeras unidades que
       faltan ("Faltan 3 unidades sin coeficiente: 1A, 1B, 2C"). Escribirlo acá
       seria una segunda version de la misma frase, capaz de quedar en
       desacuerdo con la que valida la expensa. */
    pantalla.notaCoeficientes.textContent = estado.mensaje;
  }

  /* Las unidades ya se dibujan en la lista de pisos, con su campo de
     coeficiente adentro. Lo unico que queda para este modulo es el estado del
     edificio y habilitar o deshabilitar los dos atajos. */
  function pintarCoeficientes() {
    pintarEstadoDeLaSuma();

    /* Sin unidades no hay nada que repartir, y el backend devuelve 400. Los
       botones se deshabilitan para no ofrecer una accion que va a fallar. */
    var sinUnidades = coeficientes.unidades.length === 0;
    pantalla.botonPartesIguales.disabled = sinUnidades;
    pantalla.botonMetros.disabled = sinUnidades;

    /* "Completar el resto" se habilita solo cuando tiene sentido: hace falta
       al menos una unidad cargada —de donde sale cuanto falta— y al menos una
       en blanco —donde escribirlo—. Con todas en blanco no se habilita, aunque
       el backend lo aceptaria: ahi el resto es 100% y el resultado seria
       identico a "repartir en partes iguales", asi que dos botones que hacen
       exactamente lo mismo solo generan la duda de en que se diferencian.

       El `title` dice POR QUE esta deshabilitado. Un boton gris sin
       explicacion es la clase de cosa que se interpreta como que la pantalla
       esta rota. */
    var enBlanco = coeficientes.unidades_sin_coeficiente;
    var cargadas = coeficientes.cantidad_unidades - enBlanco;

    pantalla.botonCompletar.disabled = !(cargadas > 0 && enBlanco > 0);
    pantalla.botonCompletar.title = pantalla.botonCompletar.disabled
      ? (enBlanco === 0
          ? 'Todas las unidades ya tienen coeficiente: no queda resto que completar.'
          : 'Cargá al menos un coeficiente a mano y esto reparte lo que falta ' +
            'entre las unidades que queden en blanco.')
      : 'Reparte lo que falta para llegar a 100% entre las ' + enBlanco +
        (enBlanco === 1 ? ' unidad que está' : ' unidades que están') +
        ' en blanco. No toca las que ya cargaste.';
  }

  /* Guarda el coeficiente de UNA unidad.

     Se dispara en el evento `change`, no en `input`: `change` ocurre al salir
     del campo o al apretar Enter, o sea cuando el numero esta completo.
     Guardando en `input` se mandaria un pedido por cada tecla —"3", "3,"
     "3,5", "3,57"— y los intermedios son valores que nadie quiso guardar. */
  function guardarCoeficiente(campo) {
    var id = Number(campo.dataset.coeficienteDe);
    var crudo = String(campo.value).trim().replace(',', '.');

    limpiarError(pantalla.errorDetalle, pantalla.textoErrorDetalle);

    if (crudo === '') {
      /* Vaciar el campo no borra el coeficiente: el endpoint no acepta `null`
         —el esquema pide un numero— y "dejarlo sin cargar" no es una operacion
         que exista. Se repinta el valor que tenia y se explica. */
      errorDelDetalle(
        'Para dejar una unidad sin coeficiente no alcanza con vaciar el campo. ' +
        'Si quedó cargado por error, poné 0: eso es una unidad exenta, que es ' +
        'un caso real y distinto de un dato que falta.'
      );
      pintarEstructura();
      return;
    }

    campo.disabled = true;

    window.Api.patch(
      '/edificios/' + edificioId + '/departamentos/' + id + '/coeficiente',
      { coeficiente: crudo }
    ).then(
      function (estado) {
        coeficientes = estado;

        /* Se repinta SOLO el estado de la suma y el valor de esta fila, no la
           lista entera. Redibujar todo con innerHTML se lleva puesto el foco,
           y quien carga veinte coeficientes se mueve con Tab de uno al
           siguiente: perder el foco en cada guardado haria la carga inviable. */
        pintarEstadoDeLaSuma();

        var unidad = null;
        for (var i = 0; i < estado.unidades.length; i += 1) {
          if (estado.unidades[i].id === id) unidad = estado.unidades[i];
        }
        if (unidad) {
          /* Se escribe lo que respondio el backend y no lo que se tipeo: si
             alguien puso "3.5", la columna guarda 3,500 y el campo tiene que
             mostrar eso. */
          campo.value = conComa(unidad.coeficiente);
          var fila = campo.closest('.fila-hija');
          if (fila) fila.classList.remove('sin-coeficiente');

          /* La copia en memoria del detalle tambien se actualiza: es de donde
             sale el valor cuando la lista de pisos se redibuja por cualquier
             otro motivo —agregar una cochera, por ejemplo— y si quedara vieja,
             ese redibujado volveria a mostrar el coeficiente anterior. */
          var enDetalle = unidadPorId(id);
          if (enDetalle) enDetalle.coeficiente = unidad.coeficiente;
        }
      },
      function (error) {
        errorDelDetalle(error.message);
        /* El valor vuelve al que estaba guardado: dejar en el campo un numero
           que el servidor rechazo haria creer que quedo cargado. */
        pintarEstructura();
      }
    ).then(function () {
      campo.disabled = false;
    });
  }

  /* Aplica uno de los dos atajos a todo el edificio.

     ========================================================================
     EL 409 ES EL MECANISMO DE CONFIRMACION DEL PROYECTO
     ========================================================================

     Los coeficientes de un consorcio real estan escritos en el reglamento de
     propiedad horizontal: no se calculan, se copian. El atajo es para el
     edificio que todavia no lo tiene cargado, asi que pisar coeficientes ya
     cargados es destruir el dato verdadero y dejar uno plausible.

     Si alguna unidad ya tiene coeficiente, el backend responde **409** con el
     texto de la pregunta, y `api.js` convierte ese codigo en
     `error.necesitaConfirmacion`. Esta pantalla no escribe la pregunta: la
     muestra tal como la mando el servidor, porque es el que sabe cuantas
     unidades se van a pisar. Si se confirma, se repite el pedido con
     `sobrescribir: true`. Nunca un `confirm()` del navegador, que esta
     prohibido en el proyecto. */
  function aplicarAtajo(criterio, boton) {
    limpiarError(pantalla.errorDetalle, pantalla.textoErrorDetalle);

    var textoOriginal = boton.textContent;
    boton.disabled = true;
    boton.textContent = criterio === 'completar_el_resto'
      ? 'Completando…'
      : 'Repartiendo…';

    function pedir(sobrescribir) {
      return window.Api.post(
        '/edificios/' + edificioId + '/coeficientes/aplicar-atajo',
        { criterio: criterio, sobrescribir: sobrescribir }
      );
    }

    function listo(estado) {
      coeficientes = estado;

      /* El atajo toca TODAS las unidades, asi que la copia en memoria del
         detalle queda vieja entera: se actualiza con lo que respondio el
         backend antes de redibujar la lista. */
      estado.unidades.forEach(function (unidad) {
        var enDetalle = unidadPorId(unidad.id);
        if (enDetalle) enDetalle.coeficiente = unidad.coeficiente;
      });

      pintarCoeficientes();
      pintarEstructura();
      avisarExito(
        estado.suma_cien
          ? 'Se repartieron los coeficientes: suman ' + conComa(estado.suma) +
            '% exacto.'
          : 'Se repartieron los coeficientes. ' + estado.mensaje
      );
    }

    pedir(false).then(listo, function (error) {
      if (!error.necesitaConfirmacion) {
        /* El 400 por falta de superficies trae los identificadores de las
           unidades que las necesitan: el mensaje del backend es mas util que
           cualquier texto generico que pueda escribir acá. */
        errorDelDetalle(error.message);
        return;
      }

      return window.Confirmar.pedir({
        titulo: 'Reemplazar los coeficientes cargados',
        mensaje: error.message,
        textoAccion: 'Confirmar y reemplazar'
      }).then(function (confirmo) {
        if (!confirmo) return;
        return pedir(true).then(listo, function (segundoError) {
          errorDelDetalle(segundoError.message);
        });
      });
    }).then(function () {
      boton.disabled = false;
      boton.textContent = textoOriginal;
    });
  }

  /* ------------------------------------------------ pestaña Configuracion -- */

  function pintarConfiguracion() {
    var edificio = detalle.edificio;

    pantalla.campoVencimiento.value = edificio.dias_vencimiento_expensas;
    pantalla.campoMora.value = edificio.recargo_mora_porcentual;

    pantalla.cbuGuardado.textContent = edificio.cbu || 'Sin cargar';
    pantalla.cbuGuardado.classList.toggle('vacio', !edificio.cbu);
    pantalla.aliasGuardado.textContent = edificio.alias_cbu || 'Sin cargar';
    pantalla.aliasGuardado.classList.toggle('vacio', !edificio.alias_cbu);

    pantalla.campoCbu.value = edificio.cbu || '';
    pantalla.campoAlias.value = edificio.alias_cbu || '';

    /* Las casillas salen del catalogo del backend, no de una lista escrita
       aca: el dia que la Fase 11 agregue un rol, esta pantalla lo ofrece sola. */
    var habilitados = edificio.roles_habilitados || [];
    pantalla.casillasRoles.innerHTML = '';

    opciones.roles_habilitables.forEach(function (rol) {
      var etiqueta = document.createElement('label');
      etiqueta.className = 'casilla';

      var casilla = document.createElement('input');
      casilla.type = 'checkbox';
      casilla.value = rol.nombre;
      casilla.checked = habilitados.indexOf(rol.nombre) !== -1;

      var texto = document.createElement('span');
      /* textContent: la etiqueta viene de la red. */
      texto.textContent = rol.etiqueta;

      etiqueta.appendChild(casilla);
      etiqueta.appendChild(texto);
      pantalla.casillasRoles.appendChild(etiqueta);
    });
  }

  /* ------------------------------------------- guardar un bloque (PATCH) --- */

  /* Cada bloque guarda SOLO sus campos, y eso es posible porque el endpoint es
     un PATCH de verdad: lo que no viaja no se toca. Con un PUT, guardar la
     cobranza obligaria a mandar tambien los responsables y el contacto, y el
     dia que un campo nuevo no viajara en ese formulario, guardar la cobranza
     lo borraria sin que nadie lo pida. */
  function guardarBloque(datos, boton, textoExito) {
    var textoOriginal = boton.textContent;
    /* El formulario del bloque, para poder marcar sus campos. Cada bloque es
       un `<form>` propio porque se guarda por separado. */
    var formulario = boton.form || (boton.closest && boton.closest('form'));

    boton.disabled = true;
    boton.textContent = 'Guardando…';
    limpiarError(pantalla.errorDetalle, pantalla.textoErrorDetalle);
    window.Formularios.limpiarErrores(formulario);

    return window.Api.patch('/edificios/' + edificioId, datos).then(
      function () {
        avisarExito(textoExito);
        return recargar();
      },
      function (error) {
        /* El campo marcado alcanza: el bloque esta a la vista de quien acaba
           de apretar su boton, asi que repetir el texto arriba de las
           pestañas seria decir dos veces lo mismo y mas lejos. */
        if (window.Formularios.marcarErrores(formulario, error.campos)) return;
        errorDelDetalle(error.message);
      }
    ).then(function () {
      boton.disabled = false;
      boton.textContent = textoOriginal;
    });
  }

  /* Un campo de texto vacio se manda en `null` y no en `""`.

     Son dos cosas distintas para el backend: `null` vacia el dato y la cadena
     vacia quedaria guardada como un dato que existe y esta en blanco. Despues
     hay que preguntar por las dos formas en cada consulta, y el dia que
     alguien pregunte por una sola, la mitad de las filas no aparece. */
  function textoONulo(valor) {
    var limpio = (valor || '').trim();
    return limpio || null;
  }

  function guardarResponsables(evento) {
    evento.preventDefault();
    guardarBloque(
      {
        admin_consorcio_id: pantalla.campoAdminConsorcio.value
          ? Number(pantalla.campoAdminConsorcio.value) : null,
        encargado_id: pantalla.campoEncargado.value
          ? Number(pantalla.campoEncargado.value) : null
      },
      evento.submitter || pantalla.formResponsables.querySelector('[type=submit]'),
      'Se guardaron los responsables del edificio.'
    );
  }

  function guardarEmergencia(evento) {
    evento.preventDefault();
    guardarBloque(
      {
        contacto_emergencia_nombre: textoONulo(pantalla.emergenciaNombre.value),
        contacto_emergencia_telefono: textoONulo(pantalla.emergenciaTelefono.value)
      },
      evento.submitter || pantalla.formEmergencia.querySelector('[type=submit]'),
      'Se guardó el contacto de emergencia.'
    );
  }

  function guardarExpensas(evento) {
    evento.preventDefault();

    var dias = parseInt(pantalla.campoVencimiento.value, 10);
    var mora = pantalla.campoMora.value;

    /* Estos dos NO se pueden vaciar: la columna es NOT NULL y el backend lo
       rechaza con un 422. Se ataja antes para que el mensaje hable del
       formulario y no de un esquema. */
    if (!dias || mora === '') {
      errorDelDetalle('El día de vencimiento y el recargo por mora no pueden ' +
                      'quedar vacíos.');
      return;
    }

    guardarBloque(
      {
        dias_vencimiento_expensas: dias,
        /* El recargo viaja como texto y no como `Number` a proposito: el
           backend lo lee como Decimal y un `Number` de JavaScript podria
           llegar como 1.5500000000000002. El esquema rechaza mas de dos
           decimales, asi que ese redondeo del binario se convertiria en un
           error de validacion imposible de entender mirando el campo. */
        recargo_mora_porcentual: String(mora).replace(',', '.')
      },
      evento.submitter || pantalla.formExpensas.querySelector('[type=submit]'),
      'Se guardaron los datos de la expensa.'
    );
  }

  function guardarCobranza(evento) {
    evento.preventDefault();
    guardarBloque(
      {
        cbu: textoONulo(pantalla.campoCbu.value),
        alias_cbu: textoONulo(pantalla.campoAlias.value)
      },
      evento.submitter || pantalla.formCobranza.querySelector('[type=submit]'),
      'Se guardaron los datos de cobranza.'
    );
  }

  function guardarRoles(evento) {
    evento.preventDefault();

    var elegidos = [];
    var casillas = pantalla.casillasRoles.querySelectorAll('input[type=checkbox]');
    Array.prototype.forEach.call(casillas, function (casilla) {
      if (casilla.checked) elegidos.push(casilla.value);
    });

    /* La lista vacia es un pedido legitimo —"en este edificio no hay ningun
       rol habilitado"— y el backend la acepta. No se ataja: lo que si hace
       falta es que el aviso diga que eso bloquea toda asignacion nueva, porque
       destildar todo sin querer no da ningun error. */
    guardarBloque(
      { roles_habilitados: elegidos },
      evento.submitter || pantalla.formRoles.querySelector('[type=submit]'),
      elegidos.length
        ? 'Se guardaron los roles habilitados.'
        : 'Se guardó: este edificio quedó sin ningún rol habilitado, así que ' +
          'no se van a poder asignar personas hasta que habilites alguno.'
    );
  }

  /* ================================================================= */
  /* EL MODAL GENERICO DE LAS FILAS DE LA ESTRUCTURA                   */
  /* ================================================================= */

  /* Un solo modal para piso, unidad, cochera y espacio comun, en alta y en
     edicion. La forma la describe un objeto:

       {
         titulo, sub, textoBoton,
         campos: [{nombre, etiqueta, tipo, valor, opciones, ayuda, ...}],
         guardar: function (valores) { return <promesa> }
       }

     Ocho formularios escritos a mano serian el mismo `.campo` con su label
     ocho veces, y el dia que se agregue un campo habria que acordarse de los
     ocho. Lo unico que cambia entre ellos es QUE campos hay. */

  function htmlDeCampo(campo) {
    var id = 'campo-fila-' + campo.nombre;
    var ayuda = campo.ayuda
      ? '<p class="campo-ayuda">' + textoSeguro(campo.ayuda) + '</p>'
      : '';

    var control;

    if (campo.tipo === 'select') {
      var opcionesHtml = (campo.opciones || []).map(function (opcion) {
        var elegido = String(opcion.valor) === String(campo.valor === null ||
                      campo.valor === undefined ? '' : campo.valor);
        return '<option value="' + textoSeguro(opcion.valor) + '"' +
               (elegido ? ' selected' : '') + '>' +
               textoSeguro(opcion.etiqueta) + '</option>';
      }).join('');
      control = '<select id="' + id + '" data-campo="' + campo.nombre + '"' +
                (campo.deshabilitado ? ' disabled' : '') + '>' +
                opcionesHtml + '</select>';
    } else if (campo.tipo === 'textarea') {
      control = '<textarea id="' + id + '" data-campo="' + campo.nombre + '" ' +
                'rows="3" maxlength="' + (campo.largo || 500) + '">' +
                textoSeguro(campo.valor === null ? '' : campo.valor) +
                '</textarea>';
    } else {
      var atributos = '';
      if (campo.tipo === 'numero') {
        atributos = ' type="number" inputmode="' +
                    (campo.paso ? 'decimal' : 'numeric') + '"' +
                    (campo.minimo !== undefined ? ' min="' + campo.minimo + '"' : '') +
                    (campo.maximo !== undefined ? ' max="' + campo.maximo + '"' : '') +
                    ' step="' + (campo.paso || 1) + '"';
      } else {
        atributos = ' type="text" maxlength="' + (campo.largo || 120) + '"';
      }
      control = '<input id="' + id + '" data-campo="' + campo.nombre + '"' +
                atributos + ' autocomplete="off" value="' +
                textoSeguro(campo.valor === null || campo.valor === undefined
                            ? '' : campo.valor) + '"' +
                (campo.placeholder
                  ? ' placeholder="' + textoSeguro(campo.placeholder) + '"' : '') +
                '>';
    }

    return '<div class="campo">' +
             '<label for="' + id + '">' + textoSeguro(campo.etiqueta) +
               (campo.opcional
                 ? ' <span style="font-weight:400;color:var(--ink-3)">(opcional)</span>'
                 : '') +
             '</label>' +
             control + ayuda +
           '</div>';
  }

  function abrirFormulario(formulario) {
    formularioAbierto = formulario;
    ultimoFoco = document.activeElement;

    pantalla.tituloFila.textContent = formulario.titulo;
    pantalla.subFila.textContent = formulario.sub || '';
    pantalla.botonGuardarFila.textContent = formulario.textoBoton || 'Guardar';
    pantalla.camposFila.innerHTML = formulario.campos.map(htmlDeCampo).join('');
    limpiarError(pantalla.errorFila, pantalla.textoErrorFila);

    pantalla.modalFila.classList.add('abierto');

    var primero = pantalla.camposFila.querySelector('input, select, textarea');
    if (primero) primero.focus();
  }

  function cerrarFormulario() {
    pantalla.modalFila.classList.remove('abierto');
    pantalla.camposFila.innerHTML = '';
    formularioAbierto = null;
    if (ultimoFoco && ultimoFoco.focus) ultimoFoco.focus();
  }

  function formularioEstaAbierto() {
    return pantalla.modalFila.classList.contains('abierto');
  }

  /* Lee los controles del modal y arma el cuerpo del pedido.

     Un numero vacio viaja en `null` y no en 0: son dos cosas distintas, y una
     superficie de 0 m² no existe — es una superficie que no se cargo. */
  function valoresDelFormulario() {
    var valores = {};

    formularioAbierto.campos.forEach(function (campo) {
      var control = pantalla.camposFila.querySelector(
        '[data-campo="' + campo.nombre + '"]'
      );
      if (!control) return;

      var crudo = control.value;

      if (campo.tipo === 'numero') {
        if (String(crudo).trim() === '') {
          valores[campo.nombre] = null;
          return;
        }
        /* Los decimales viajan como texto, igual que el recargo por mora: el
           backend los lee como Decimal y un `Number` de JavaScript puede
           llegar con la basura del binario (1.5500000000000002) y chocar
           contra el limite de decimales del esquema. */
        valores[campo.nombre] = campo.paso
          ? String(crudo).replace(',', '.')
          : parseInt(crudo, 10);
        return;
      }

      if (campo.tipo === 'select') {
        valores[campo.nombre] = crudo === ''
          ? null
          : (campo.comoNumero ? Number(crudo) : crudo);
        return;
      }

      valores[campo.nombre] = textoONulo(crudo);
    });

    return valores;
  }

  function enviarFormulario(evento) {
    evento.preventDefault();
    if (!formularioAbierto) return;

    limpiarError(pantalla.errorFila, pantalla.textoErrorFila);

    var valores = valoresDelFormulario();
    var faltantes = formularioAbierto.campos.filter(function (campo) {
      return !campo.opcional &&
             (valores[campo.nombre] === null || valores[campo.nombre] === undefined);
    });

    if (faltantes.length) {
      mostrarError(pantalla.errorFila, pantalla.textoErrorFila,
                   'Completá ' + faltantes[0].etiqueta.toLowerCase() + '.');
      return;
    }

    var guardar = formularioAbierto;
    pantalla.botonGuardarFila.disabled = true;
    var textoBoton = pantalla.botonGuardarFila.textContent;
    pantalla.botonGuardarFila.textContent = 'Guardando…';

    guardar.guardar(valores).then(function () {
      cerrarFormulario();
      avisarExito(guardar.exito);
      return recargar();
    }).catch(function (error) {
      /* El error se muestra DENTRO del modal, que sigue abierto con todo lo
         tipeado en su lugar: cerrarlo obligaria a escribir de nuevo por un
         identificador repetido. Y se marca en el campo cuando el backend dice
         cual es — ver el comentario de `edificios.js`. */
      var marcados = window.Formularios.marcarErrores(
        pantalla.formFila, error.campos
      );

      mostrarError(
        pantalla.errorFila,
        pantalla.textoErrorFila,
        marcados
          ? (marcados === 1
              ? 'Revisá el campo marcado.'
              : 'Revisá los ' + marcados + ' campos marcados.')
          : error.message
      );
    }).then(function () {
      pantalla.botonGuardarFila.disabled = false;
      pantalla.botonGuardarFila.textContent = textoBoton;
    });
  }

  /* ---------------------------------------- los ocho formularios concretos -- */

  function unidadPorId(id) {
    if (!id) return null;
    for (var i = 0; i < detalle.pisos.length; i += 1) {
      var unidades = detalle.pisos[i].departamentos;
      for (var j = 0; j < unidades.length; j += 1) {
        if (unidades[j].id === id) return unidades[j];
      }
    }
    return null;
  }

  function pisoPorId(id) {
    for (var i = 0; i < detalle.pisos.length; i += 1) {
      if (detalle.pisos[i].id === id) return detalle.pisos[i];
    }
    return null;
  }

  function filaPorId(lista, id) {
    for (var i = 0; i < lista.length; i += 1) {
      if (lista[i].id === id) return lista[i];
    }
    return null;
  }

  /* Las opciones de un desplegable de personas, para el modal. La lista vacia
     no se oculta: se muestra deshabilitada con la explicacion, porque "no hay
     a quien elegir" y "ese rol no se usa en este edificio" son dos cosas
     distintas y la segunda se resuelve en la pestaña de Configuracion. */
  function opcionesDePersonas(lista) {
    var opcionesLista = [{ valor: '', etiqueta: 'Sin asignar' }];
    lista.forEach(function (persona) {
      opcionesLista.push({
        valor: persona.id,
        etiqueta: persona.nombre + ' (' + persona.email + ')'
      });
    });
    return opcionesLista;
  }

  function ayudaDeResidente(rol, lista) {
    var habilitado = (detalle.edificio.roles_habilitados || []).indexOf(rol) !== -1;
    if (!habilitado) {
      return 'El rol ' + (rol === 'propietario' ? 'Propietario' : 'Inquilino') +
             ' no está habilitado en este edificio, así que no se puede ' +
             'asignar. Se habilita en la pestaña Configuración.';
    }
    if (!lista.length) {
      return 'Todavía no hay usuarios activos con ese rol. Se dan de alta en ' +
             'la pantalla de Usuarios.';
    }
    return 'Dejar "Sin asignar" desvincula a quien esté.';
  }

  function campoDeResidente(nombre, etiqueta, rol, lista, valor) {
    var habilitado = (detalle.edificio.roles_habilitados || []).indexOf(rol) !== -1;
    return {
      nombre: nombre,
      etiqueta: etiqueta,
      tipo: 'select',
      opcional: true,
      comoNumero: true,
      valor: valor,
      opciones: opcionesDePersonas(lista),
      /* Se deshabilita solo si no hay nada que elegir Y no hay nadie asignado:
         si hay alguien asignado, el desplegable tiene que seguir usable para
         poder desvincularlo — deshabilitar el rol de un edificio no puede
         dejar a esa persona pegada a la unidad para siempre. */
      deshabilitado: (!habilitado || !lista.length) && !valor,
      ayuda: ayudaDeResidente(rol, lista)
    };
  }

  function nuevoPiso() {
    abrirFormulario({
      titulo: 'Agregar un piso',
      sub: 'El número es cómo se llama el piso y puede no ser un número ' +
           'corrido: hay edificios que saltean el 13 o tienen un entrepiso. ' +
           'Si no indicás la posición, el piso va arriba del último.',
      textoBoton: 'Agregar piso',
      exito: 'Se agregó el piso.',
      campos: [
        { nombre: 'numero', etiqueta: 'Número del piso', tipo: 'numero',
          minimo: -10, maximo: 200, placeholder: '8' },
        { nombre: 'orden', etiqueta: 'Posición en la pila', tipo: 'numero',
          opcional: true, minimo: 1 }
      ],
      guardar: function (valores) {
        return window.Api.post('/edificios/' + edificioId + '/pisos', valores);
      }
    });
  }

  function editarPiso(id) {
    var piso = pisoPorId(id);
    if (!piso) return;

    abrirFormulario({
      titulo: 'Editar el piso ' + piso.numero,
      sub: 'El número es el nombre del piso; la posición es su lugar en la ' +
           'pila, que es lo que ordena las unidades en las pantallas.',
      textoBoton: 'Guardar cambios',
      exito: 'Se guardaron los cambios del piso.',
      campos: [
        { nombre: 'numero', etiqueta: 'Número del piso', tipo: 'numero',
          valor: piso.numero, minimo: -10, maximo: 200 },
        { nombre: 'orden', etiqueta: 'Posición en la pila', tipo: 'numero',
          valor: piso.orden, minimo: 1 }
      ],
      guardar: function (valores) {
        return window.Api.patch(
          '/edificios/' + edificioId + '/pisos/' + id, valores
        );
      }
    });
  }

  function nuevaUnidad(pisoId) {
    var piso = pisoPorId(pisoId);
    if (!piso) return;

    abrirFormulario({
      titulo: 'Agregar una unidad al piso ' + piso.numero,
      sub: 'El identificador es como se la nombra en el consorcio: 3B, 12, ' +
           'PB-A. La superficie es opcional acá y hace falta para repartir ' +
           'los coeficientes por metro cuadrado.',
      textoBoton: 'Agregar unidad',
      exito: 'Se agregó la unidad.',
      campos: [
        { nombre: 'identificador', etiqueta: 'Identificador', tipo: 'texto',
          largo: 20, placeholder: '3B' },
        { nombre: 'm2', etiqueta: 'Superficie en m²', tipo: 'numero',
          opcional: true, paso: '0.01', minimo: 0, placeholder: '62,50' }
      ],
      guardar: function (valores) {
        return window.Api.post(
          '/edificios/' + edificioId + '/pisos/' + pisoId + '/departamentos',
          valores
        );
      }
    });
  }

  function editarUnidad(id) {
    var unidad = unidadPorId(id);
    if (!unidad) return;

    abrirFormulario({
      titulo: 'Editar la unidad ' + unidad.identificador,
      /* El coeficiente no esta en este formulario, y es deliberado: el backend
         lo rechaza por esta via (da 422) porque corregir una superficie no
         tiene que poder tocar un coeficiente por accidente. */
      sub: 'El coeficiente no se edita acá: tiene su propia pantalla, con el ' +
           'indicador de la suma, porque lo que importa no es el de una ' +
           'unidad sino que los de todas den 100% exacto.',
      textoBoton: 'Guardar cambios',
      exito: 'Se guardaron los cambios de la unidad.',
      campos: [
        { nombre: 'identificador', etiqueta: 'Identificador', tipo: 'texto',
          valor: unidad.identificador, largo: 20 },
        { nombre: 'm2', etiqueta: 'Superficie en m²', tipo: 'numero',
          opcional: true, paso: '0.01', minimo: 0,
          valor: unidad.m2 === null ? '' : unidad.m2 },
        campoDeResidente('propietario_id', 'Propietario', 'propietario',
                         asignables.propietario, unidad.propietario_id),
        campoDeResidente('inquilino_id', 'Inquilino', 'inquilino',
                         asignables.inquilino, unidad.inquilino_id)
      ],
      guardar: function (valores) {
        return window.Api.patch(
          '/edificios/' + edificioId + '/departamentos/' + id, valores
        );
      }
    });
  }

  /* Las opciones del desplegable de unidades, para asignar una cochera fija. */
  function opcionesDeUnidades() {
    var lista = [{ valor: '', etiqueta: 'Sin asignar' }];
    detalle.pisos.forEach(function (piso) {
      piso.departamentos.forEach(function (unidad) {
        lista.push({ valor: unidad.id, etiqueta: unidad.identificador });
      });
    });
    return lista;
  }

  function camposDeCochera(cochera) {
    return [
      { nombre: 'numero', etiqueta: 'Número o nombre', tipo: 'texto',
        largo: 20, valor: cochera ? cochera.numero : '', placeholder: '12' },
      { nombre: 'tipo', etiqueta: 'Tipo', tipo: 'select',
        valor: cochera ? cochera.tipo : opciones.tipos_cochera[0],
        opciones: opciones.tipos_cochera.map(function (tipo) {
          /* La etiqueta se arma capitalizando el valor y no de una lista
             escrita aca: asi un tipo nuevo en el backend aparece solo. */
          return {
            valor: tipo,
            etiqueta: tipo.charAt(0).toUpperCase() + tipo.slice(1)
          };
        }) },
      { nombre: 'departamento_id', etiqueta: 'Unidad asignada', tipo: 'select',
        opcional: true, comoNumero: true,
        valor: cochera ? cochera.departamento_id : null,
        opciones: opcionesDeUnidades(),
        ayuda: 'Solo una cochera fija se puede asignar a una unidad. Una ' +
               'rotativa no es de nadie en particular, así que tiene que ' +
               'quedar sin asignar.' }
    ];
  }

  function nuevaCochera() {
    abrirFormulario({
      titulo: 'Agregar una cochera',
      sub: 'El número puede ser texto: hay cocheras que se nombran "A-12" o ' +
           '"Subsuelo 3".',
      textoBoton: 'Agregar cochera',
      exito: 'Se agregó la cochera.',
      campos: camposDeCochera(null),
      guardar: function (valores) {
        return window.Api.post('/edificios/' + edificioId + '/cocheras', valores);
      }
    });
  }

  function editarCochera(id) {
    var cochera = filaPorId(detalle.cocheras, id);
    if (!cochera) return;

    abrirFormulario({
      titulo: 'Editar la cochera ' + cochera.numero,
      textoBoton: 'Guardar cambios',
      exito: 'Se guardaron los cambios de la cochera.',
      campos: camposDeCochera(cochera),
      guardar: function (valores) {
        return window.Api.patch(
          '/edificios/' + edificioId + '/cocheras/' + id, valores
        );
      }
    });
  }

  function camposDeEspacio(espacio) {
    return [
      { nombre: 'nombre', etiqueta: 'Nombre', tipo: 'texto', largo: 120,
        valor: espacio ? espacio.nombre : '', placeholder: 'SUM' },
      { nombre: 'capacidad', etiqueta: 'Capacidad de personas', tipo: 'numero',
        opcional: true, minimo: 1,
        valor: espacio && espacio.capacidad !== null ? espacio.capacidad : '' },
      { nombre: 'reglas_uso', etiqueta: 'Reglas de uso', tipo: 'textarea',
        opcional: true, largo: 500,
        valor: espacio ? espacio.reglas_uso : '',
        ayuda: 'Lo que el consorcista tiene que saber antes de reservarlo: ' +
               'horarios, si hay depósito, qué queda prohibido.' }
    ];
  }

  function nuevoEspacio() {
    abrirFormulario({
      titulo: 'Agregar un espacio común',
      sub: 'El SUM, la terraza, el gimnasio. Los ve cualquiera que tenga algo ' +
           'que hacer en el edificio, porque son el objeto de un reclamo o de ' +
           'una reserva.',
      textoBoton: 'Agregar espacio',
      exito: 'Se agregó el espacio común.',
      campos: camposDeEspacio(null),
      guardar: function (valores) {
        return window.Api.post(
          '/edificios/' + edificioId + '/espacios-comunes', valores
        );
      }
    });
  }

  function editarEspacio(id) {
    var espacio = filaPorId(detalle.espacios_comunes, id);
    if (!espacio) return;

    abrirFormulario({
      titulo: 'Editar ' + espacio.nombre,
      textoBoton: 'Guardar cambios',
      exito: 'Se guardaron los cambios del espacio común.',
      campos: camposDeEspacio(espacio),
      guardar: function (valores) {
        return window.Api.patch(
          '/edificios/' + edificioId + '/espacios-comunes/' + id, valores
        );
      }
    });
  }

  /* ------------------------------------------------------------- borrados -- */

  /* Las bajas de la estructura son fisicas, al contrario de la de un usuario:
     un piso que no existe no tiene historia que preservar. Por eso las cuatro
     piden confirmacion, con `Confirmar.pedir()` y nunca con un `confirm()` del
     navegador, que esta prohibido en el proyecto.

     El mensaje dice QUE se borra y, cuando corresponde, que se lleva con el.
     El backend ademas se niega a borrar un piso con unidades, una unidad con
     residente y una unidad con cocheras: si eso pasa, su mensaje es el que se
     muestra, porque explica el motivo mejor que cualquier texto generico. */
  function borrar(ruta, titulo, mensaje, exito) {
    window.Confirmar.pedir({
      titulo: titulo,
      mensaje: mensaje,
      textoAccion: 'Confirmar y borrar'
    }).then(function (confirmo) {
      if (!confirmo) return;

      limpiarError(pantalla.errorDetalle, pantalla.textoErrorDetalle);

      window.Api.borrar(ruta).then(function () {
        avisarExito(exito);
        return recargar();
      }, function (error) {
        errorDelDetalle(error.message);
      });
    });
  }

  function borrarPiso(id) {
    var piso = pisoPorId(id);
    if (!piso) return;

    borrar(
      '/edificios/' + edificioId + '/pisos/' + id,
      'Borrar el piso ' + piso.numero,
      'El piso ' + piso.numero + ' se borra de la estructura. Si todavía ' +
      'tiene unidades cargadas, el sistema no lo va a dejar: primero hay que ' +
      'borrar o mover esas unidades, porque borrarlas en cadena se llevaría ' +
      'puestos sus coeficientes y sus ocupantes sin preguntar.',
      'Se borró el piso ' + piso.numero + '.'
    );
  }

  function borrarUnidad(id) {
    var unidad = unidadPorId(id);
    if (!unidad) return;

    borrar(
      '/edificios/' + edificioId + '/departamentos/' + id,
      'Borrar la unidad ' + unidad.identificador,
      'La unidad ' + unidad.identificador + ' se borra del edificio, con su ' +
      'superficie y su coeficiente. Si tiene propietario, inquilino o ' +
      'cocheras asignadas, el sistema no lo va a dejar hasta que la ' +
      'desvincules.',
      'Se borró la unidad ' + unidad.identificador + '.'
    );
  }

  function borrarCochera(id) {
    var cochera = filaPorId(detalle.cocheras, id);
    if (!cochera) return;

    borrar(
      '/edificios/' + edificioId + '/cocheras/' + id,
      'Borrar la cochera ' + cochera.numero,
      'La cochera ' + cochera.numero + ' se borra del edificio. Si estaba ' +
      'asignada a una unidad, esa unidad queda sin cochera.',
      'Se borró la cochera ' + cochera.numero + '.'
    );
  }

  function borrarEspacio(id) {
    var espacio = filaPorId(detalle.espacios_comunes, id);
    if (!espacio) return;

    borrar(
      '/edificios/' + edificioId + '/espacios-comunes/' + id,
      'Borrar ' + espacio.nombre,
      espacio.nombre + ' se borra del edificio. Dejaría de poder elegirse ' +
      'como objeto de un reclamo o de una reserva.',
      'Se borró ' + espacio.nombre + '.'
    );
  }

  /* --------------------------------------------------------------- pestañas -- */

  /* Esta pantalla NO toca la clase .activo ni el indicador: de eso se ocupa
     view-switch.js, que se engancha solo. Acá solo se cambia el panel que se
     ve, que es el dato. Los dos listeners conviven sobre los mismos botones. */
  function mostrarVista(vista) {
    Array.prototype.forEach.call(pantalla.paneles, function (panel) {
      panel.hidden = panel.dataset.panel !== vista;
    });

    /* Leaflet mide su contenedor una sola vez, al crearse. Si el mapa se monto
       mientras esta pestaña estaba oculta —o si la ventana cambio de tamaño
       mientras se miraba otra— queda gris con los mosaicos a medio cargar.
       Remedirlo al volver es una linea y ataja todos esos casos juntos. */
    if (vista === 'datos' && mapa) mapa.remedir();
  }

  function engancharPestanias() {
    Array.prototype.forEach.call(
      pantalla.pestanias.querySelectorAll('button'),
      function (boton) {
        boton.addEventListener('click', function () {
          mostrarVista(boton.dataset.vista);
        });
      }
    );
    mostrarVista(VISTA_INICIAL);
  }

  /* --------------------------------------------------------------- arranque -- */

  /* Un listener en el panel de estructura, no uno por fila: el panel se
     reemplaza entero con innerHTML en cada recarga, asi que los listeners
     puestos fila por fila se perderian. El boton se busca con closest()
     porque el clic puede caer en el <svg> de adentro. */
  function alHacerClicEnLaEstructura(evento) {
    var boton = evento.target.closest('[data-accion]');
    if (!boton) return;

    var id = Number(boton.dataset.id);

    var acciones = {
      'nuevo-piso': nuevoPiso,
      'editar-piso': function () { editarPiso(id); },
      'borrar-piso': function () { borrarPiso(id); },
      'nueva-unidad': function () { nuevaUnidad(id); },
      'editar-unidad': function () { editarUnidad(id); },
      'borrar-unidad': function () { borrarUnidad(id); },
      'nueva-cochera': nuevaCochera,
      'editar-cochera': function () { editarCochera(id); },
      'borrar-cochera': function () { borrarCochera(id); },
      'nuevo-espacio': nuevoEspacio,
      'editar-espacio': function () { editarEspacio(id); },
      'borrar-espacio': function () { borrarEspacio(id); },
      'atajo-partes-iguales': function () {
        aplicarAtajo('partes_iguales', boton);
      },
      'atajo-metros': function () { aplicarAtajo('metros_cuadrados', boton); },
      'atajo-completar': function () { aplicarAtajo('completar_el_resto', boton); }
    };

    var accion = acciones[boton.dataset.accion];
    if (accion) accion();
  }

  function tomarElementos() {
    pantalla = {
      vista: document.getElementById('vista-detalle'),
      nombre: document.querySelector('[data-detalle-nombre]'),
      bajada: document.querySelector('[data-detalle-bajada]'),
      tamanio: document.querySelector('[data-detalle-tamanio]'),
      errorDetalle: document.getElementById('error-detalle'),
      textoErrorDetalle: document.querySelector('[data-texto-error-detalle]'),

      pestanias: document.getElementById('pestanias-edificio'),
      paneles: document.querySelectorAll('[data-panel]'),
      panelEstructura: document.querySelector('[data-panel="estructura"]'),

      fichaIdentidad: document.querySelector('[data-ficha-identidad]'),
      notaResponsables: document.querySelector('[data-nota-responsables]'),
      formResponsables: document.getElementById('form-responsables'),
      fichaResponsables: document.querySelector('[data-ficha-responsables]'),
      campoAdminConsorcio: document.getElementById('campo-admin-consorcio'),
      campoEncargado: document.getElementById('campo-encargado'),
      formEmergencia: document.getElementById('form-emergencia'),
      emergenciaNombre: document.getElementById('campo-emergencia-nombre'),
      emergenciaTelefono: document.getElementById('campo-emergencia-telefono'),

      contenedorMapa: document.getElementById('mapa-del-edificio'),
      mapaVacio: document.querySelector('[data-mapa-detalle-vacio]'),

      pillSuma: document.querySelector('[data-pill-suma]'),
      panelTotal: document.querySelector('[data-panel-total]'),
      totalBarra: document.querySelector('[data-total-barra]'),
      totalNumero: document.querySelector('[data-total-numero]'),
      totalEtiqueta: document.querySelector('[data-total-etiqueta]'),
      totalChips: document.querySelector('[data-total-chips]'),
      notaCoeficientes: document.querySelector('[data-nota-coeficientes]'),
      botonPartesIguales:
        document.querySelector('[data-accion="atajo-partes-iguales"]'),
      botonMetros: document.querySelector('[data-accion="atajo-metros"]'),
      botonCompletar: document.querySelector('[data-accion="atajo-completar"]'),

      listaPisos: document.querySelector('[data-lista-pisos]'),
      listaCocheras: document.querySelector('[data-lista-cocheras]'),
      listaEspacios: document.querySelector('[data-lista-espacios]'),

      formExpensas: document.getElementById('form-expensas'),
      campoVencimiento: document.getElementById('campo-vencimiento'),
      campoMora: document.getElementById('campo-mora'),
      formCobranza: document.getElementById('form-cobranza'),
      campoCbu: document.getElementById('campo-cbu'),
      campoAlias: document.getElementById('campo-alias'),
      cbuGuardado: document.getElementById('cbu-guardado'),
      aliasGuardado: document.getElementById('alias-guardado'),
      formRoles: document.getElementById('form-roles'),
      casillasRoles: document.querySelector('[data-casillas-roles]'),

      modalFila: document.getElementById('modal-fila'),
      tituloFila: document.getElementById('modal-fila-titulo'),
      subFila: document.querySelector('[data-fila-sub]'),
      camposFila: document.querySelector('[data-campos-fila]'),
      formFila: document.getElementById('form-fila'),
      errorFila: document.getElementById('error-fila'),
      textoErrorFila: document.querySelector('[data-texto-error-fila]'),
      botonGuardarFila: document.getElementById('boton-guardar-fila'),
      botonCerrarFila: document.getElementById('boton-cerrar-fila'),
      botonCancelarFila: document.getElementById('boton-cancelar-fila')
    };
  }

  function enganchar() {
    engancharPestanias();

    pantalla.formResponsables.addEventListener('submit', guardarResponsables);
    pantalla.formEmergencia.addEventListener('submit', guardarEmergencia);
    pantalla.formExpensas.addEventListener('submit', guardarExpensas);
    pantalla.formCobranza.addEventListener('submit', guardarCobranza);
    pantalla.formRoles.addEventListener('submit', guardarRoles);

    pantalla.panelEstructura.addEventListener('click', alHacerClicEnLaEstructura);

    /* Un solo listener para los veinte campos de coeficiente, por delegacion
       en la lista de pisos: la lista se reemplaza entera con innerHTML en cada
       recarga, asi que los listeners puestos campo por campo se perderian.
       `change` burbujea, al contrario de `focus` y `blur`, asi que delegar
       funciona. */
    pantalla.listaPisos.addEventListener('change', function (evento) {
      var campo = evento.target.closest('[data-coeficiente-de]');
      if (campo) guardarCoeficiente(campo);
    });

    /* Enter en un campo de coeficiente guarda y no hace nada mas.

       Hace falta atajarlo porque formularios.js mueve el foco al campo
       siguiente con Enter —que es lo correcto en un formulario— y estos
       campos NO estan en un <form>: son veinte guardados independientes. Sin
       esto, Enter no dispararia `change` hasta que el campo pierda el foco de
       otra forma, y quien carga veinte coeficientes apretando Enter no veria
       actualizarse la suma. */
    pantalla.listaPisos.addEventListener('keydown', function (evento) {
      if (evento.key !== 'Enter') return;
      var campo = evento.target.closest('[data-coeficiente-de]');
      if (!campo) return;
      evento.preventDefault();
      campo.blur();
    });

    pantalla.formFila.addEventListener('submit', enviarFormulario);
    pantalla.botonCerrarFila.addEventListener('click', cerrarFormulario);
    pantalla.botonCancelarFila.addEventListener('click', cerrarFormulario);

    /* A PROPOSITO: ningun listener de clic en el backdrop. Escape si cierra,
       porque es una accion intencional y es lo que cualquiera espera. */
    document.addEventListener('keydown', function (evento) {
      if (evento.key === 'Escape' && formularioEstaAbierto()) cerrarFormulario();
    });
  }

  /**
   * Monta el detalle de un edificio.
   *
   * @param {number} id El edificio, que sale de la URL.
   * @param {object} usuario El de la sesion, que ya pidio `edificios.js`.
   */
  function montar(id, usuario) {
    edificioId = id;
    usuarioSesion = usuario;

    tomarElementos();
    if (!pantalla.vista) return;

    pantalla.vista.hidden = false;
    enganchar();

    pantalla.listaPisos.innerHTML =
      '<div class="lista-vacia">' + window.Cargando.html() + '</div>';
    pantalla.fichaIdentidad.innerHTML =
      '<div class="lista-vacia">' + window.Cargando.html() + '</div>';

    cargarTodo();
  }

  window.EdificioDetalle = { montar: montar };
}());

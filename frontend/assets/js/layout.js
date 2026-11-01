/* ============================================================================
   layout.js — El esqueleto de TODA pantalla autenticada.

   Monta el sidebar y el topbar, hace la guarda de sesion, pide el usuario
   actual y arma los accesos que le corresponden a su rol. Cada pantalla lo
   llama UNA vez y recibe el usuario; ninguna reescribe esta logica, ni arma
   su propio menu, ni consulta /auth/me por su cuenta.

   A DIFERENCIA de formularios.js y view-switch.js, este modulo NO se
   engancha solo. Es a proposito: montar el esqueleto implica pedir datos al
   backend y, si no hay sesion, sacar al usuario de la pagina. Eso no puede
   pasar por el solo hecho de incluir un <script>; la pantalla tiene que
   pedirlo, y ademas necesita el usuario que devuelve para rutear por rol.

       window.Layout.montar().then(function (usuario) {
         // aca recien se dibuja el contenido propio de la pantalla
       });

   Lo que cada pantalla tiene que traer en su HTML es solo esto:

       <body class="layout-app" data-pantalla="usuarios" data-titulo="Usuarios">
         <div class="main-column">
           <header class="topbar shell" data-topbar></header>
           <main class="page-content"> ...contenido propio... </main>
         </div>
       </body>

   El sidebar, el backdrop y el contenido del topbar los genera este archivo.
   Que no se repitan en catorce HTML es justamente el punto: un acceso nuevo
   se agrega en un solo lugar y aparece en toda la aplicacion.

   Depende de config.js y api.js, cargados antes.
   ========================================================================== */

(function () {
  'use strict';

  /* ========================================================================
     LA TABLA DE ACCESOS — la unica fuente de que ve cada rol en el menu.

     Esta tabla es el menu entero de la aplicacion. Crece una linea por fase
     y no se declara en ningun otro lado: si manana el Encargado tiene que
     ver Reclamos, se agrega su rol a esa fila y aparece en todas las
     pantallas de una vez. La alternativa —que cada HTML escriba su propio
     menu— garantiza que en algun momento dos pantallas muestren menus
     distintos para el mismo usuario.

     `construida: false` es lo que mantiene la regla de no enlazar NUNCA un
     archivo que todavia no existe. La fila se declara igual, con su rol y su
     icono, para que la tabla se lea como el plan completo del menu; pero
     mientras el archivo no este, el acceso no se dibuja. Cuando la pantalla
     se construye se cambia ese `false` por `true` y nada mas.

     OJO con lo que NO va aca: esto decide que se MUESTRA, no que se puede
     hacer. El permiso real lo controla el backend en cada endpoint. Ocultar
     un acceso es una cortesia para no ofrecer lo que va a ser rechazado,
     nunca un mecanismo de seguridad — quien escriba la URL a mano llega
     igual a la pantalla, y ahi lo frena el backend.
     ===================================================================== */

  var ACCESOS = [
    {
      id: 'usuarios',
      etiqueta: 'Usuarios',
      archivo: 'usuarios.html',
      construida: false,          /* se construye en F1-T13 */
      roles: ['admin_general'],
      icono: '<path d="M16 19v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 17.5V19"/>' +
             '<circle cx="10" cy="7.5" r="3.5"/>' +
             '<path d="M20 19v-1.5a3.5 3.5 0 0 0-2.6-3.4M15.5 4.2a3.5 3.5 0 0 1 0 6.6"/>'
    }
  ];

  /* Iconos del esqueleto. Trazo, viewBox 24x24, extremos redondeados, como
     todo icono del proyecto. */
  var ICONO_MARCA =
    '<path d="M4 21V6l8-3 8 3v15"/>' +
    '<path d="M9 21v-6h6v6"/>' +
    '<path d="M9 10h.01M15 10h.01M9 14h.01M15 14h.01"/>';

  var ICONO_HAMBURGUESA = '<path d="M4 7h16M4 12h16M4 17h16"/>';

  var ICONO_TEMA =
    '<circle cx="12" cy="12" r="4"/>' +
    '<path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2' +
    'M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>';

  var ICONO_SALIR =
    '<path d="M15 17l5-5-5-5"/>' +
    '<path d="M20 12H9"/>' +
    '<path d="M12 21H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h6"/>';

  /* Estado del modulo, todo declarado junto arriba. Es la convencion del
     proyecto, y viene de un error cometido tres veces: una variable
     declarada mas abajo de donde la usa el codigo que corre al inicio
     explota con "Cannot access before initialization". */
  var elementos = {};
  var usuarioActual = null;

  /* --------------------------------------------------------- utilidades --- */

  function svg(contenido, ancho) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
           'stroke-width="' + (ancho || 1.8) + '" stroke-linecap="round" ' +
           'stroke-linejoin="round" aria-hidden="true">' + contenido + '</svg>';
  }

  /* El nombre de archivo de la pagina actual. Sirve para marcar el acceso
     activo. Si la URL termina en "/" el servidor sirve index.html. */
  function archivoActual() {
    var partes = window.location.pathname.split('/');
    var ultimo = partes[partes.length - 1];
    return ultimo || 'index.html';
  }

  function accesosDe(rol) {
    return ACCESOS.filter(function (acceso) {
      return acceso.construida && acceso.roles.indexOf(rol) !== -1;
    });
  }

  /* ------------------------------------------------------------- sidebar -- */

  function htmlDeAccesos(rol) {
    var disponibles = accesosDe(rol);

    /* Un rol sin ninguna pantalla habilitada ve un texto que explica por
       que, nunca un menu vacio que parece roto. Hoy lo ven todos los roles,
       porque la primera pantalla del menu llega en F1-T13. */
    if (!disponibles.length) {
      return '<p class="sidebar-vacio">Todavía no hay pantallas habilitadas ' +
             'para tu rol. Se van a ir sumando a medida que el sistema crezca.</p>';
    }

    var actual = archivoActual();

    return disponibles.map(function (acceso) {
      var activo = acceso.archivo === actual;
      return '<a class="sidebar-link' + (activo ? ' activo' : '') + '" ' +
             'href="' + acceso.archivo + '"' +
             (activo ? ' aria-current="page"' : '') + '>' +
             svg(acceso.icono, 1.7) +
             '<span>' + acceso.etiqueta + '</span>' +
             '</a>';
    }).join('');
  }

  function construirSidebar(usuario) {
    var aside = document.createElement('aside');
    aside.className = 'sidebar shell';
    aside.id = 'sidebar';

    /* La marca enlaza a index.html y no a una pantalla de inicio que no
       existe: hoy ahi esta el login, que con sesion activa muestra quien
       entro. Cuando exista el dashboard, se cambia este href. */
    aside.innerHTML =
      '<a class="sidebar-brand" href="index.html">' +
        '<span class="brand-mark">' + svg(ICONO_MARCA) + '</span>' +
        '<span class="brand-text">' +
          '<b>SMART Building</b>' +
          '<span>Gestión integral de consorcios</span>' +
        '</span>' +
      '</a>' +

      '<nav class="sidebar-nav" aria-label="Secciones">' +
        htmlDeAccesos(usuario.rol) +
      '</nav>' +

      '<div class="sidebar-footer">' +
        '<div class="sidebar-usuario content-glass">' +
          '<b data-usuario-nombre></b>' +
          '<span data-usuario-rol></span>' +
        '</div>' +
        '<button type="button" class="boton-primario boton-secundario" id="boton-cerrar-sesion">' +
          'Cerrar sesión' +
        '</button>' +
      '</div>';

    /* textContent y no interpolacion en el innerHTML de arriba: el nombre lo
       escribio una persona en un formulario, y armar HTML con eso es
       exactamente como se inyecta un script. El resto del bloque es texto
       fijo del proyecto; estos dos son el unico dato que viene de afuera. */
    aside.querySelector('[data-usuario-nombre]').textContent = usuario.nombre;
    aside.querySelector('[data-usuario-rol]').textContent = usuario.rol_etiqueta;

    return aside;
  }

  function construirBackdrop() {
    var backdrop = document.createElement('div');
    backdrop.className = 'sidebar-backdrop';
    backdrop.id = 'sidebar-backdrop';
    return backdrop;
  }

  /* -------------------------------------------------------------- topbar -- */

  function llenarTopbar() {
    var topbar = document.querySelector('[data-topbar]');
    if (!topbar) return;

    var titulo = document.body.dataset.titulo || document.title;

    topbar.innerHTML =
      '<button type="button" class="icon-btn hamburguesa" id="boton-hamburguesa" ' +
              'aria-label="Abrir el menú" aria-controls="sidebar" aria-expanded="false">' +
        svg(ICONO_HAMBURGUESA, 1.9) +
      '</button>' +
      '<h1 class="topbar-titulo"></h1>' +
      '<div class="topbar-actions">' +
        '<button type="button" class="icon-btn" id="boton-tema" aria-label="Cambiar tema">' +
          svg(ICONO_TEMA, 1.7) +
        '</button>' +
      '</div>';

    topbar.querySelector('.topbar-titulo').textContent = titulo;
  }

  /* ---------------------------------------------------- panel en mobile --- */

  /* El sidebar de mobile usa el MISMO patron de panel deslizante que el
     panel de detalle del Dashboard Visual: un componente conceptual
     reutilizado, no dos implementaciones. Su backdrop es transparente y
     solo sirve para cerrar al tocar afuera — el unico backdrop que oscurece
     en todo el proyecto es el de los modales, porque ahi hay algo que leer
     antes de seguir. */

  function abrirPanel() {
    elementos.sidebar.classList.add('abierta');
    elementos.backdrop.classList.add('abierta');
    elementos.hamburguesa.setAttribute('aria-expanded', 'true');
  }

  function cerrarPanel() {
    elementos.sidebar.classList.remove('abierta');
    elementos.backdrop.classList.remove('abierta');
    elementos.hamburguesa.setAttribute('aria-expanded', 'false');
    /* El foco vuelve al boton que abrio el panel: si se quedara dentro de un
       panel cerrado, el siguiente Tab seguiria recorriendo elementos que ya
       no se ven. */
    elementos.hamburguesa.focus();
  }

  function panelAbierto() {
    return elementos.sidebar.classList.contains('abierta');
  }

  function engancharPanel() {
    elementos.hamburguesa.addEventListener('click', function () {
      if (panelAbierto()) cerrarPanel(); else abrirPanel();
    });

    elementos.backdrop.addEventListener('click', cerrarPanel);

    /* Escape cierra cualquier capa superpuesta. Vale para el panel igual que
       para un modal: es la tecla que la gente aprieta sin pensar. */
    document.addEventListener('keydown', function (evento) {
      if (evento.key === 'Escape' && panelAbierto()) cerrarPanel();
    });

    /* Tocar un acceso navega a otra pagina, asi que cerrar el panel no se
       nota — salvo cuando el acceso es la pantalla en la que ya estamos, que
       no recarga nada y dejaria el panel abierto sin explicacion. */
    elementos.sidebar.addEventListener('click', function (evento) {
      if (evento.target.closest('.sidebar-link') && panelAbierto()) {
        elementos.sidebar.classList.remove('abierta');
        elementos.backdrop.classList.remove('abierta');
        elementos.hamburguesa.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ------------------------------------------------------ cerrar sesion --- */

  function cerrarSesion() {
    window.Api.Sesion.limpiar();
    window.location.href = window.Config.PAGINA_LOGIN;
  }

  /* ------------------------------------------------------------- montaje -- */

  function montarEsqueleto(usuario) {
    var columna = document.querySelector('.main-column');

    elementos.sidebar = construirSidebar(usuario);
    elementos.backdrop = construirBackdrop();

    /* El sidebar va ANTES de la columna principal en el DOM, no solo en el
       dibujo: el orden del documento es el orden en que se recorre con Tab y
       el que lee un lector de pantalla. Llegar al menu despues del contenido
       obligaria a recorrer toda la pantalla para volver a navegar. */
    document.body.insertBefore(elementos.sidebar, columna);
    document.body.insertBefore(elementos.backdrop, columna);

    llenarTopbar();

    elementos.hamburguesa = document.getElementById('boton-hamburguesa');
    elementos.botonSalir = document.getElementById('boton-cerrar-sesion');

    engancharPanel();
    elementos.botonSalir.addEventListener('click', cerrarSesion);

    /* theme.js engancha cualquier boton con id "boton-tema" al cargar la
       pagina. El del topbar lo acaba de crear este archivo, o sea despues:
       hay que pedirle que lo tome. */
    if (window.Tema && window.Tema.enganchar) window.Tema.enganchar();
  }

  /**
   * Monta el esqueleto y devuelve el usuario de la sesion.
   *
   * @returns {Promise<object>} el usuario, ya con su rol y sus permisos.
   */
  function montar() {
    /* Guarda de sesion. Sin token no se pide nada ni se dibuja nada: se
       vuelve al login.
       La promesa que se devuelve NO se resuelve nunca, y es deliberado: lo
       que sigue en la pantalla esta encadenado a este .then(), asi que no
       resolver es lo que evita que se dibuje medio contenido mientras el
       navegador cambia de pagina. */
    if (!window.Api.Sesion.activa()) {
      window.location.href = window.Config.PAGINA_LOGIN;
      return new Promise(function () {});
    }

    /* Sin redirigirEn401: false, o sea con el comportamiento normal del
       envoltorio: si el token no vale, api.js limpia la sesion y manda al
       login. Que es exactamente lo que corresponde aca — al contrario del
       login, donde un 401 significa "credenciales incorrectas". */
    return window.Api.get('/auth/me').then(function (usuario) {
      usuarioActual = usuario;
      montarEsqueleto(usuario);
      return usuario;
    });
  }

  window.Layout = {
    montar: montar,
    /* Para una pantalla que ya monto el esqueleto y necesita el usuario otra
       vez sin volver a pedirlo al backend. */
    usuario: function () { return usuarioActual; },
    /* La tabla, expuesta para poder leerla desde la consola al depurar por
       que un rol no ve un acceso. Se lee, no se modifica. */
    ACCESOS: ACCESOS
  };
}());

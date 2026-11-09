/* ============================================================================
   usuarios.js — Logica de la pantalla de usuarios (usuarios.html).

   Un .js por pantalla, igual que login.js: se ocupa solo de SU pantalla y
   apoya todo lo transversal en los modulos compartidos (api.js, layout.js,
   formularios.js, cargando.js).

   Lo que hace:
     1. Monta el esqueleto por layout.js, declarando quien puede entrar.
     2. Lista los usuarios (activos e inactivos).
     3. Da de alta uno nuevo en un modal.
     4. Aprueba o rechaza las cuentas que se registraron solas (F1-T16B).

   LA APROBACION ES UNA EDICION, NO UN ENDPOINT NUEVO. Aprobar es asignarle
   un rol a quien tiene `pendiente`, o sea el PATCH que ya existia. Lo unico
   propio es la presentacion: un bloque aparte arriba del listado, y el modal
   en un modo que obliga a elegir el rol en vez de ofrecer uno por defecto.

   LO QUE NO HACE, Y ES A PROPOSITO: no edita ni activa/desactiva. El icono de
   editar y el boton de estado con ripple llegan en F1-T13+1 (F1-T14), y la
   confirmacion de accion destructiva en F1-T15. La fila ya deja el lugar
   preparado —ver `.fila-lista-botones` en components.css— pero no lo dibuja
   todavia: un boton que no hace nada es peor que un boton que no esta.

   Depende de config.js, api.js, cargando.js y layout.js, cargados antes.
   ========================================================================== */

(function () {
  'use strict';

  /* Los roles que pueden ver esta pantalla. Es la misma lista que la fila de
     la tabla de accesos de layout.js, y es deliberado que este escrita dos
     veces: la tabla decide que se MUESTRA en el menu, esto decide que pasa si
     alguien escribe la URL a mano. Son dos preguntas distintas y en algun
     momento van a tener respuestas distintas — una pantalla puede estar fuera
     del menu de un rol y seguir siendo accesible por un enlace directo.

     Ninguna de las dos es el control real: ese lo hace el backend en cada
     endpoint. */
  var ROLES_HABILITADOS = ['admin_general'];

  /* El rol que el backend le pone a quien se registra solo. No es un rol
     asignable —no aparece en el <select>— pero si un valor que llega en el
     listado, y es lo que separa las dos secciones de la pantalla. */
  var ROL_PENDIENTE = 'pendiente';

  /* El valor del <option> que no es un rol. Existe para que el <select> NO
     arranque en una opcion valida: ver el comentario de asegurarOpciones(). */
  var SIN_ROL = '';

  /* Todo el estado de la pantalla declarado junto arriba. Es la convencion del
     proyecto y viene de un error cometido tres veces: una variable declarada
     mas abajo de donde la usa el codigo que corre al inicio explota con
     "Cannot access before initialization". */
  var pantalla = {};
  var opcionesDeAlta = null;   /* roles y politica, se piden una sola vez */
  var ultimoFoco = null;       /* a donde vuelve el foco al cerrar el modal */
  var usuarioSesion = null;    /* quien esta mirando: su fila no se puede tocar */
  var enEdicion = null;        /* el usuario que se esta editando, o null si es un alta */
  var listado = [];            /* lo ultimo que trajo el backend */

  var ICONO_LAPIZ =
    '<path d="M4 20h4l10-10a2.1 2.1 0 0 0-3-3L5 17v3z"/>' +
    '<path d="M14.5 6.5l3 3"/>';

  /* ------------------------------------------------------------ utilidades -- */

  function icono(contenido, ancho) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
           'stroke-width="' + (ancho || 1.8) + '" stroke-linecap="round" ' +
           'stroke-linejoin="round" aria-hidden="true">' + contenido + '</svg>';
  }

  /* Escapa lo que va a entrar por innerHTML.

     Hace falta de verdad, no por formalismo: el nombre y el email los escribio
     una persona y viajaron por la red. Un nombre con un "<" rompe el listado
     entero, y uno con una etiqueta <script> lo ejecuta. Donde se puede se usa
     textContent, que no necesita esto; donde se arma una fila completa de una
     sola vez —que es mas rapido y mas legible— se escapa. */
  function textoSeguro(valor) {
    if (valor === null || valor === undefined) return '';
    return String(valor)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* La fecha de registro, corta y en castellano. Dos cosas que no son
     adorno:

     - Si el texto no trae zona horaria, se le agrega la Z. El backend guarda
       en UTC; sobre SQLite la fecha vuelve sin offset y, sin esto, el
       navegador la interpretaria como hora local y una solicitud de hace un
       rato podria mostrarse con la fecha de mañana. Sobre PostgreSQL vuelve
       con offset y entonces no se toca nada.
     - Si la fecha no se puede leer, devuelve cadena vacia y quien llama no
       muestra el dato. Un "Invalid Date" en una fila es peor que no decir
       cuando se registro. */
  function fechaCorta(iso) {
    if (!iso) return '';

    var texto = String(iso);
    if (!/(Z|[+-]\d\d:?\d\d)$/.test(texto)) texto += 'Z';

    var fecha = new Date(texto);
    if (isNaN(fecha.getTime())) return '';

    return fecha.toLocaleDateString('es-AR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
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

  /* El aviso de "se creo" se inserta arriba de la lista y se va solo.

     Se va solo porque no comunica nada que haga falta volver a leer: el
     usuario nuevo ya esta visible en el listado, que es la confirmacion de
     verdad. Un cartel que se queda ahi obliga a cerrarlo a mano o se acumula
     con el siguiente. */
  function avisarExito(mensaje) {
    var aviso = document.createElement('div');
    aviso.className = 'mensaje-exito';
    aviso.setAttribute('role', 'status');
    aviso.innerHTML =
      icono('<path d="M20 6L9 17l-5-5"/>', 2) +
      '<span></span>';
    aviso.querySelector('span').textContent = mensaje;

    /* Arriba del bloque de pendientes y no de la lista de abajo: el aviso
       tiene que quedar cerca de donde se hizo la accion, y aprobar o rechazar
       se hace arriba. Cuando no hay pendientes, ese bloque esta oculto y no
       ocupa lugar, asi que el aviso aparece pegado al listado igual que
       antes — sin un `if` que pregunte en cual de los dos estamos. */
    pantalla.seccionPendientes.parentNode.insertBefore(
      aviso, pantalla.seccionPendientes
    );
    window.setTimeout(function () {
      if (aviso.parentNode) aviso.parentNode.removeChild(aviso);
    }, 5000);
  }

  /* --------------------------------------------------------------- listado -- */

  function htmlDeFila(usuario) {
    /* Los datos secundarios van en una sola linea separados por un punto
       medio, y el telefono solo aparece si existe: un " · " colgando al final
       de la linea se lee como un dato que falta. */
    var secundarios = [usuario.email];
    if (usuario.telefono) secundarios.push(usuario.telefono);

    /* ES UNO MISMO. Es la unica fila donde el boton de estado va
       deshabilitado, y la razon no es estetica: un Administrador General que
       se desactiva pierde en ese instante la forma de volver a entrar —el
       login rechaza inactivos y hace falta ser admin para reactivar a
       alguien—. Paso de verdad y hubo que reparar la base a mano.

       El backend lo rechaza igual con un 400. Esto es la segunda capa, para
       que no se llegue a intentar. */
    var esUnoMismo = usuarioSesion && usuario.id === usuarioSesion.id;

    var razonBloqueo = 'No podés cambiar el estado de tu propia cuenta: si la ' +
                       'desactivaras, no podrías volver a entrar.';

    var botonEstado =
      '<button type="button" class="boton-estado-usuario ' +
        (usuario.activo ? 'activo' : 'inactivo') + '" ' +
        'data-accion="estado" data-id="' + usuario.id + '" ' +
        'data-activo="' + usuario.activo + '"' +
        (esUnoMismo ? ' disabled title="' + textoSeguro(razonBloqueo) + '"' : '') +
        ' aria-label="' + (usuario.activo ? 'Desactivar' : 'Activar') +
        ' la cuenta de ' + textoSeguro(usuario.nombre) + '">' +
        '<span class="boton-estado-texto">' +
          (usuario.activo ? 'Activo' : 'Inactivo') +
        '</span>' +
      '</button>';

    var botonEditar =
      '<button type="button" class="icon-btn icon-btn-sm" ' +
        'data-accion="editar" data-id="' + usuario.id + '" ' +
        'aria-label="Editar los datos de ' + textoSeguro(usuario.nombre) + '">' +
        icono(ICONO_LAPIZ, 1.8) +
      '</button>';

    return '<article class="fila-lista content-glass' +
           (usuario.activo ? '' : ' inactiva') + '">' +
             '<div class="fila-lista-dato">' +
               '<b>' + textoSeguro(usuario.nombre) + '</b>' +
               '<span>' + textoSeguro(secundarios.join(' · ')) + '</span>' +
             '</div>' +
             '<div class="fila-lista-acciones">' +
               /* rol_etiqueta lo calcula el backend desde la matriz de roles.
                  El frontend NO tiene su propia tabla de nombres de rol. */
               /* Dos clases y no una: .fila-lista-estado es la ranura (queda
                  anclada al nombre) y .rol-badge es el aspecto (etiqueta
                  neutra, reutilizable fuera de un listado). */
               '<span class="fila-lista-estado rol-badge">' +
                 textoSeguro(usuario.rol_etiqueta) +
               '</span>' +
               '<div class="fila-lista-botones">' +
                 botonEditar +
                 botonEstado +
               '</div>' +
             '</div>' +
           '</article>';
  }

  /* La fila de una cuenta que espera aprobacion. Es parecida a la de arriba
     pero NO es la misma con un `if`: cambian las dos acciones, cambia el dato
     secundario y cambia el borde. Un htmlDeFila() con cuatro condicionales
     adentro seria mas corto de escribir y mas dificil de leer que dos
     funciones que se entienden solas.

     Lo que NO lleva, a proposito:
       - El boton de estado con ripple. Dice "Activo", y en una cuenta sin
         aprobar esa palabra es engañosa: la cuenta esta habilitada para
         entrar y no sirve para nada. Aca las acciones son aprobar y
         rechazar, que es la decision real.
       - El lapiz de editar. Aprobar ya abre el formulario completo, asi que
         un segundo boton al lado llevaria al mismo lugar. */
  function htmlDeFilaPendiente(usuario) {
    var secundarios = [usuario.email];
    if (usuario.telefono) secundarios.push(usuario.telefono);

    var fecha = fechaCorta(usuario.creado_en);
    if (fecha) secundarios.push('se registró el ' + fecha);

    var botonAprobar =
      '<button type="button" class="boton-primario boton-chico" ' +
        'data-accion="aprobar" data-id="' + usuario.id + '" ' +
        'aria-label="Aprobar la cuenta de ' + textoSeguro(usuario.nombre) +
        ' y asignarle un rol">Aprobar</button>';

    var botonRechazar =
      '<button type="button" class="boton-primario boton-secundario boton-chico" ' +
        'data-accion="rechazar" data-id="' + usuario.id + '" ' +
        'aria-label="Rechazar la solicitud de ' + textoSeguro(usuario.nombre) +
        '">Rechazar</button>';

    return '<article class="fila-lista content-glass pendiente">' +
             '<div class="fila-lista-dato">' +
               '<b>' + textoSeguro(usuario.nombre) + '</b>' +
               '<span>' + textoSeguro(secundarios.join(' · ')) + '</span>' +
             '</div>' +
             '<div class="fila-lista-acciones">' +
               /* La etiqueta sale del backend, igual que en el listado de
                  abajo: el frontend no tiene su propia tabla de nombres. */
               '<span class="fila-lista-estado rol-badge">' +
                 textoSeguro(usuario.rol_etiqueta) +
               '</span>' +
               '<div class="fila-lista-botones">' +
                 botonRechazar +
                 botonAprobar +
               '</div>' +
             '</div>' +
           '</article>';
  }

  /* Reparte lo que trajo el backend en los dos bloques de la pantalla.

     El criterio de "pendiente" incluye `activo`: una solicitud rechazada
     queda inactiva y baja al listado de abajo. El bloque de arriba es lo que
     hay que decidir, no el historial de lo que ya se decidio — y si alguien
     reactiva esa cuenta desde abajo, vuelve a aparecer para decidir, que es
     exactamente lo correcto. */
  function pintarPendientes(usuarios) {
    var pendientes = usuarios.filter(function (usuario) {
      return usuario.rol === ROL_PENDIENTE && usuario.activo;
    });

    /* El bloque entero se esconde si no hay ninguna, y con el se esconde el
       titulo del listado de abajo: sin pendientes, la pantalla vuelve a ser
       exactamente la de antes de esta tarea. */
    pantalla.seccionPendientes.hidden = pendientes.length === 0;
    pantalla.tituloConRol.hidden = pendientes.length === 0;
    pantalla.contadorPendientes.textContent = String(pendientes.length);
    pantalla.listaPendientes.innerHTML = pendientes.map(htmlDeFilaPendiente).join('');

    return pendientes;
  }

  function pintarListado(todos) {
    /* La copia en memoria es la lista COMPLETA, incluidos los pendientes: es
       la que consultan el modal de edicion y los mensajes de confirmacion, y
       tiene que poder encontrar a cualquiera de los dos bloques. */
    listado = todos;

    var pendientes = pintarPendientes(todos);

    /* Los pendientes activos ya se pintaron arriba: aca va el resto. Sin
       esta resta, cada uno apareceria dos veces en la pantalla. */
    var usuarios = todos.filter(function (usuario) {
      return pendientes.indexOf(usuario) === -1;
    });

    if (!usuarios.length) {
      /* Este caso no deberia poder verse nunca —quien esta mirando la
         pantalla es, el mismo, un usuario del listado— pero el estado vacio se
         escribe igual: es parte del checklist de pantalla terminada, y el dia
         que el listado se filtre por alcance (F1-T08) va a ser alcanzable. */
      /* Con pendientes arriba, este estado vacio significa otra cosa: no es
         que no haya usuarios, es que todos los que hay estan esperando. El
         texto generico ahi diria algo que la pantalla contradice tres
         centimetros mas arriba. */
      pantalla.lista.innerHTML = pendientes.length
        ? '<div class="lista-vacia"><b>Todavía no aprobaste a nadie</b>' +
          'Las cuentas de arriba no tienen rol, así que no pueden usar el ' +
          'sistema.</div>'
        : '<div class="lista-vacia"><b>No hay usuarios todavía</b>' +
          'Creá el primero con el botón de arriba.</div>';
      return;
    }

    pantalla.lista.innerHTML = usuarios.map(htmlDeFila).join('');
  }

  /* Deja la pantalla sin ninguna fila. Se usa al empezar a cargar y cuando la
     carga falla, y tiene que vaciar LOS DOS bloques: dejar las filas viejas
     debajo de un error de recarga muestra datos que ya no se sabe si siguen
     siendo ciertos, y eso vale igual para las solicitudes pendientes — peor
     todavia ahi, porque son las que invitan a hacer clic. */
  function vaciarFilas() {
    pantalla.lista.innerHTML = '';
    pantalla.listaPendientes.innerHTML = '';
    pantalla.seccionPendientes.hidden = true;
    pantalla.tituloConRol.hidden = true;
  }

  function cargarListado() {
    limpiarError(pantalla.errorListado, pantalla.textoErrorListado);
    vaciarFilas();
    pantalla.lista.innerHTML =
      '<div class="lista-vacia">' + window.Cargando.html() + '</div>';

    return window.Api.get('/usuarios').then(
      function (usuarios) {
        pintarListado(usuarios);
      },
      function (error) {
        /* Las dos listas se vacian: ver vaciarFilas(). */
        vaciarFilas();
        mostrarError(
          pantalla.errorListado,
          pantalla.textoErrorListado,
          error.message
        );
      }
    );
  }

  /* ----------------------------------------------------------- modal de alta */

  /* Llena el <select> de roles y la ayuda de contrasenia con lo que manda el
     backend. Se pide UNA sola vez y queda guardado: el catalogo de roles y la
     politica no cambian entre dos altas de la misma sesion. */
  function asegurarOpciones() {
    if (opcionesDeAlta) return Promise.resolve(opcionesDeAlta);

    return window.Api.get('/usuarios/opciones').then(function (datos) {
      opcionesDeAlta = datos;

      pantalla.campoRol.innerHTML = '';

      /* UNA OPCION QUE NO ES UN ROL, PRIMERA Y SELECCIONADA.

         Antes el <select> arrancaba en el primer rol de la lista, que es el
         de MAS permisos: la matriz esta ordenada de mas a menos, asi que
         enviar el formulario sin tocar el rol creaba un Administrador
         General. En el alta eso ya era un riesgo tonto; con la aprobacion de
         pendientes pasa a ser el camino mas probable de todos, porque el
         administrador va a aprobar de a varios y el campo que no se toca es
         justo el que importa.

         Que el valor sea cadena vacia es lo que permite que guardar() lo
         detecte y pida elegir, en vez de que el backend reciba un rol que
         nadie eligio. */
      var sinRol = document.createElement('option');
      sinRol.value = SIN_ROL;
      sinRol.textContent = 'Elegí un rol…';
      pantalla.campoRol.appendChild(sinRol);

      datos.roles.forEach(function (rol) {
        var opcion = document.createElement('option');
        opcion.value = rol.nombre;
        /* textContent y no innerHTML: la etiqueta viene de la red. */
        opcion.textContent = rol.etiqueta;
        pantalla.campoRol.appendChild(opcion);
      });

      pantalla.requisitos.innerHTML = '';
      datos.password.requisitos.forEach(function (requisito) {
        var item = document.createElement('li');
        item.textContent = requisito;
        pantalla.requisitos.appendChild(item);
      });

      return datos;
    });
  }

  /* Pone el modal en modo alta o en modo edicion.

     ES EL MISMO MODAL, no dos. Un segundo modal "de edicion" seria el mismo
     formulario escrito dos veces, y el dia que se agregue un campo habria que
     acordarse de los dos. Lo que cambia es el titulo, la bajada, el texto del
     boton y si el campo de contrasenia esta. */
  /* Aprobar es editar a alguien que tiene el rol `pendiente`. Se DEDUCE del
     usuario que se esta editando en vez de guardarse en una variable aparte:
     un `modoAprobacion` separado seria un segundo estado que puede quedar en
     desacuerdo con `enEdicion`, y entonces el modal mostraria un titulo que
     no corresponde al usuario que tiene cargado. */
  function aprobando() {
    return Boolean(enEdicion) && enEdicion.rol === ROL_PENDIENTE;
  }

  function configurarModal(usuario) {
    enEdicion = usuario || null;

    var editando = Boolean(usuario);
    var aprueba = aprobando();

    pantalla.titulo.textContent = aprueba
      ? 'Aprobar la cuenta'
      : (editando ? 'Editar usuario' : 'Nuevo usuario');

    pantalla.botonCrear.textContent = aprueba
      ? 'Aprobar la cuenta'
      : (editando ? 'Guardar cambios' : 'Crear usuario');

    pantalla.subtitulo.textContent = aprueba
      ? 'Elegí el rol que le corresponde: desde que lo guardes, la cuenta ' +
        'queda habilitada con los permisos de ese rol. Los datos los cargó ' +
        'la propia persona, así que revisalos y corregí lo que haga falta.'
      : (editando
        ? 'La contraseña no se cambia desde acá: el backend no la acepta por ' +
          'esta vía y todavía no hay circuito de recuperación.'
        : 'Nace activo y con la contraseña que definas acá — se la comunicás ' +
          'vos, todavía no hay circuito de invitación por email.');

    /* El campo de contrasenia se ESCONDE al editar, no se deshabilita: un
       campo gris que no se puede usar invita a preguntarse por que. Y se
       vacia, para que no viaje nada en el PATCH. */
    pantalla.campoPassword.value = '';
    pantalla.bloquePassword.hidden = editando;

    if (editando) {
      pantalla.campoNombre.value = usuario.nombre;
      pantalla.campoEmail.value = usuario.email;
      pantalla.campoTelefono.value = usuario.telefono || '';
      /* El rol se asigna despues de que lleguen las opciones: todavia no hay
         <option> ninguno al que apuntar. */
    } else {
      pantalla.formulario.reset();
    }
  }

  function abrirModal(usuario) {
    /* Quien abrio el modal, para devolverle el foco al cerrarlo. Sin esto, al
       cerrar con Escape el foco se va al <body> y el siguiente Tab arranca
       desde el principio de la pagina. */
    ultimoFoco = document.activeElement;

    configurarModal(usuario);
    limpiarError(pantalla.errorAlta, pantalla.textoErrorAlta);
    pantalla.modal.classList.add('abierto');

    /* Las opciones se piden al abrir y no al cargar la pantalla: el formulario
       es lo unico que las necesita, y la mayoria de las visitas al listado no
       dan de alta a nadie. El campo queda deshabilitado hasta que lleguen, asi
       no se puede enviar un alta sin rol. */
    pantalla.campoRol.disabled = true;
    pantalla.botonCrear.disabled = true;

    asegurarOpciones().then(
      function () {
        pantalla.campoRol.disabled = false;
        pantalla.botonCrear.disabled = false;

        /* Recien aca se puede elegir el rol: los <option> los acaba de crear
           asegurarOpciones(). Fijarlo antes no haria nada.

           Al APROBAR no se preselecciona ninguno —el rol actual es
           `pendiente`, que no es una opcion del <select>— y queda la opcion
           vacia, que es justo lo que se busca: el rol tiene que elegirse a
           mano. Si se intentara fijar `pendiente`, el navegador ignoraria el
           valor desconocido y dejaria la primera opcion, que es la vacia; o
           sea, el resultado seria el mismo por accidente. Preguntarlo lo
           convierte en una decision escrita. */
        if (enEdicion && !aprobando()) pantalla.campoRol.value = enEdicion.rol;

        /* Al aprobar, el foco va al rol y no al nombre: los datos ya estan
           cargados y lo unico que falta es esa decision. */
        (aprobando() ? pantalla.campoRol : pantalla.campoNombre).focus();
      },
      function (error) {
        mostrarError(
          pantalla.errorAlta,
          pantalla.textoErrorAlta,
          'No se pudieron cargar los roles. ' + error.message
        );
      }
    );
  }

  function cerrarModal() {
    pantalla.modal.classList.remove('abierto');
    enEdicion = null;
    pantalla.bloquePassword.hidden = false;
    pantalla.formulario.reset();
    limpiarError(pantalla.errorAlta, pantalla.textoErrorAlta);

    /* El toggle de mostrar/ocultar queda como lo dejo el usuario: reset() no
       devuelve el input a type="password". Se le pide a formularios.js que
       vuelva a sincronizarlo, para que el proximo alta no arranque con la
       contrasenia a la vista. */
    pantalla.campoPassword.type = 'password';
    if (window.Formularios && window.Formularios.sincronizarToggles) {
      window.Formularios.sincronizarToggles();
    }

    if (ultimoFoco && ultimoFoco.focus) ultimoFoco.focus();
  }

  function modalAbierto() {
    return pantalla.modal.classList.contains('abierto');
  }

  /* ------------------------------------------------------------------- alta -- */

  function bloquearEnvio(bloqueado) {
    pantalla.botonCrear.disabled = bloqueado;

    if (bloqueado) {
      pantalla.botonCrear.textContent = enEdicion ? 'Guardando…' : 'Creando…';
      return;
    }
    pantalla.botonCrear.textContent = enEdicion ? 'Guardar cambios' : 'Crear usuario';
  }

  function guardar(evento) {
    evento.preventDefault();
    limpiarError(pantalla.errorAlta, pantalla.textoErrorAlta);

    var editando = Boolean(enEdicion);

    var nombre = pantalla.campoNombre.value.trim();
    var email = pantalla.campoEmail.value.trim();
    var password = pantalla.campoPassword.value;
    var telefono = pantalla.campoTelefono.value.trim();

    /* Validacion minima en el cliente, solo para no gastar un viaje de ida y
       vuelta en algo que ya se sabe que esta incompleto. NO duplica la del
       backend: el largo del nombre, el formato del email y la politica de
       contrasenia los valida el backend, que es el que manda. */
    if (!nombre || !email || (!editando && !password)) {
      mostrarError(
        pantalla.errorAlta,
        pantalla.textoErrorAlta,
        editando
          ? 'Completá el nombre y el email.'
          : 'Completá el nombre, el email y la contraseña.'
      );
      return;
    }

    /* El rol dejo de tener un valor por defecto, asi que hay que pedirlo. Es
       la contracara de la opcion vacia del <select>, y vale la molestia: el
       defecto anterior era el rol de mas permisos del sistema. */
    if (pantalla.campoRol.value === SIN_ROL) {
      mostrarError(
        pantalla.errorAlta,
        pantalla.textoErrorAlta,
        aprobando()
          ? 'Elegí el rol que le corresponde antes de aprobar la cuenta.'
          : 'Elegí el rol del usuario.'
      );
      pantalla.campoRol.focus();
      return;
    }

    bloquearEnvio(true);

    /* null y no "" cuando no hay telefono. El esquema lo acepta como opcional,
       y una cadena vacia guardada se lee despues como un telefono que existe y
       esta en blanco, no como uno que no se cargo. */
    var datos = {
      nombre: nombre,
      email: email,
      rol: pantalla.campoRol.value,
      telefono: telefono || null
    };

    /* UN SOLO lugar decide si es POST o PATCH, y el cuerpo es casi el mismo.

       En la edicion NO se manda la contrasenia: el esquema de edicion del
       backend no la acepta y, con extra="forbid", mandarla devuelve un 422.
       Y como el PATCH es un PATCH de verdad —lo que no viene no se toca—,
       alcanza con no incluirla. */
    var pedido = editando
      ? window.Api.patch('/usuarios/' + enEdicion.id, datos)
      : window.Api.post('/usuarios', Object.assign({ password: password }, datos));

    /* Se lee ANTES del pedido: despues de que conteste, `guardado.rol` ya no
       es `pendiente` y aprobando() diria que no. */
    var aprueba = aprobando();

    pedido.then(function (guardado) {
      var mensaje = aprueba
        ? 'Se aprobó la cuenta de ' + guardado.nombre + ' como ' +
          guardado.rol_etiqueta + '. Ya puede entrar al sistema.'
        : (editando
          ? 'Se guardaron los cambios de ' + guardado.nombre + '.'
          : 'Se creó la cuenta de ' + guardado.nombre + '.');
      cerrarModal();
      avisarExito(mensaje);
      return cargarListado();
    }).catch(function (error) {
      /* El error se muestra DENTRO del modal, que sigue abierto con todo lo
         tipeado en su lugar. Cerrarlo obligaria a escribir todo de nuevo por
         un email repetido. */
      mostrarError(pantalla.errorAlta, pantalla.textoErrorAlta, error.message);
    }).then(function () {
      bloquearEnvio(false);
    });
  }

  /* --------------------------------------------------- estado de la cuenta -- */

  /* El ripple nace del punto exacto del clic, y se pinta con el color AL QUE el
     boton esta yendo, no con uno fijo: asi el ripple y la transicion del fondo
     aterrizan juntos en el mismo color nuevo. */
  /* El segundo argumento es el punto del clic: sirve el evento de click tal
     cual, o un {clientX, clientY} copiado de uno. Hace falta que acepte una
     copia porque entre el clic y el ripple ahora puede haber un modal de
     confirmacion, y para entonces el evento original ya no existe. */
  function dispararRipple(boton, punto, color) {
    var caja = boton.getBoundingClientRect();

    /* El doble del lado mas largo: es lo que garantiza que el circulo cubra el
       boton entero aunque el clic haya sido en una esquina. */
    var tamanio = Math.max(caja.width, caja.height) * 2;

    /* Las coordenadas del clic son relativas a la ventana, y la fila puede
       haberse movido mientras el modal estaba abierto (si aparecio o se fue el
       aviso de exito de arriba). Si el punto guardado ya cae fuera del boton,
       no sirve: el ripple nace del centro, que siempre esta bien. */
    var x = punto.clientX;
    var y = punto.clientY;
    var afuera = x < caja.left || x > caja.right ||
                 y < caja.top || y > caja.bottom;
    if (afuera) {
      x = caja.left + caja.width / 2;
      y = caja.top + caja.height / 2;
    }

    var ripple = document.createElement('span');
    ripple.className = 'ripple';
    ripple.style.width = tamanio + 'px';
    ripple.style.height = tamanio + 'px';
    ripple.style.left = (x - caja.left - tamanio / 2) + 'px';
    ripple.style.top = (y - caja.top - tamanio / 2) + 'px';
    ripple.style.background = color;

    boton.appendChild(ripple);
    ripple.addEventListener('animationend', function () {
      if (ripple.parentNode) ripple.parentNode.removeChild(ripple);
    });
  }

  /* Pinta el boton como si el cambio ya hubiera ocurrido. Se usa para el cambio
     optimista y, con el valor anterior, para revertirlo si falla. */
  function pintarEstado(boton, activo) {
    boton.classList.toggle('activo', activo);
    boton.classList.toggle('inactivo', !activo);
    boton.dataset.activo = String(activo);

    /* Al <span> interno, NUNCA al boton: textContent sobre el boton reemplaza
       todos sus hijos, y se llevaria puestos los ripples que esten animando. */
    boton.querySelector('.boton-estado-texto').textContent =
      activo ? 'Activo' : 'Inactivo';

    boton.setAttribute(
      'aria-label',
      (activo ? 'Desactivar' : 'Activar') + ' esta cuenta'
    );

    var fila = boton.closest('.fila-lista');
    if (fila) fila.classList.toggle('inactiva', !activo);
  }

  /* Decide si hay que preguntar, y recien despues aplica.

     Se pregunta SOLO al desactivar. Activar no destruye nada y se deshace con
     otro toque, asi que pedir confirmacion ahi solo agrega un paso — y un
     modal que aparece siempre se cierra sin leerlo, que es como se arruina el
     unico momento en que el mensaje importa de verdad. */
  function alternarEstado(boton, evento) {
    var eraActivo = boton.dataset.activo === 'true';

    /* Las coordenadas se copian ACA. El evento de click no sobrevive al modal:
       para cuando se contesta la pregunta, leerle clientX ya no es confiable. */
    var punto = { clientX: evento.clientX, clientY: evento.clientY };

    if (!eraActivo) {
      aplicarEstado(boton, punto);
      return;
    }

    var usuario = usuarioDelListado(Number(boton.dataset.id));
    var nombre = usuario ? usuario.nombre : 'Esta persona';

    /* El boton NO se deshabilita mientras se decide, aunque el primer impulso
       sea hacerlo. Al cerrar, el modal devuelve el foco a quien lo abrio, y el
       foco no entra en un boton deshabilitado: se iria al <body> y el teclado
       quedaria recorriendo la pagina desde el principio. Tampoco hace falta:
       el modal tapa la fila, asi que un segundo clic cae en el velo, y si
       llegara otra pregunta, Confirmar.pedir() la contesta que no sin tocar la
       que esta abierta. */
    window.Confirmar.pedir({
      titulo: 'Desactivar la cuenta',

      /* El mensaje dice QUE pasa y QUE NO pasa. Lo segundo importa tanto como
         lo primero: sin la segunda frase, "desactivar" se lee como "borrar" y
         la respuesta honesta pasa a ser cancelar siempre. */
      mensaje: nombre + ' no va a poder volver a iniciar sesión. Sus datos no ' +
               'se borran y la cuenta se puede reactivar desde este mismo ' +
               'listado cuando haga falta.',

      textoAccion: 'Confirmar y desactivar'
    }).then(function (confirmo) {
      if (confirmo) aplicarEstado(boton, punto);
    });
  }

  function aplicarEstado(boton, punto) {
    var id = Number(boton.dataset.id);
    var eraActivo = boton.dataset.activo === 'true';
    var quedaActivo = !eraActivo;

    /* CAMBIO OPTIMISTA: el ripple y el color nuevo salen al instante, sin
       esperar al servidor. Es lo que hace que el boton se sienta inmediato. Si
       el pedido falla, se revierte y se explica. */
    dispararRipple(boton, punto, quedaActivo ? 'var(--ok)' : 'var(--crit)');
    pintarEstado(boton, quedaActivo);

    /* Mientras viaja el pedido no se puede volver a tocar: dos clics rapidos
       mandarian dos cambios y el estado final dependeria de cual conteste
       ultimo. */
    boton.disabled = true;

    window.Api.post('/usuarios/' + id + '/estado', { activo: quedaActivo }).then(
      function (actualizado) {
        /* Se repinta con lo que respondio el backend y no con lo que se supuso:
           si otra pestania cambio algo en el medio, manda el servidor. */
        pintarEstado(boton, actualizado.activo);
        actualizarEnListado(actualizado);
        avisarExito(
          actualizado.activo
            ? 'Se reactivó la cuenta de ' + actualizado.nombre + '.'
            : 'Se desactivó la cuenta de ' + actualizado.nombre +
              '. Ya no puede iniciar sesión.'
        );
      },
      function (error) {
        pintarEstado(boton, eraActivo);
        mostrarError(
          pantalla.errorListado,
          pantalla.textoErrorListado,
          error.message
        );
      }
    ).then(function () {
      boton.disabled = false;
    });
  }

  /* ------------------------------------------------------------- rechazo -- */

  /* Rechazar una solicitud es DESACTIVAR la cuenta, no borrarla.

     Es la misma decision que el resto del sistema: la baja es logica y nadie
     desaparece del registro. Aca ademas resuelve un caso concreto: si se
     borrara, la persona podria volver a registrarse con el mismo email a los
     cinco minutos, y el administrador tendria que rechazarla de nuevo, sin
     ninguna constancia de que ya lo habia hecho. Desactivada, el email sigue
     ocupado, la solicitud baja al listado de abajo marcada como inactiva, y
     se puede reactivar y aprobar si fue un error.

     Usa el MISMO endpoint que el boton de estado del listado
     (POST /usuarios/{id}/estado), no uno nuevo: es exactamente el mismo
     cambio, pedido desde otro lugar de la pantalla. */
  function rechazar(boton) {
    var id = Number(boton.dataset.id);
    var usuario = usuarioDelListado(id);
    var nombre = usuario ? usuario.nombre : 'Esta persona';
    var email = usuario ? usuario.email : '';

    window.Confirmar.pedir({
      titulo: 'Rechazar la solicitud',

      /* El mensaje dice que NO se borra. Sin esa frase, "rechazar" se lee
         como "eliminar" y lo honesto pasa a ser cancelar siempre. */
      mensaje: nombre + (email ? ' (' + email + ')' : '') + ' no va a poder ' +
               'iniciar sesión. La cuenta no se borra: baja al listado como ' +
               'inactiva, y si fue un error la podés reactivar y aprobar ' +
               'desde ahí.',

      textoAccion: 'Confirmar y rechazar'
    }).then(function (confirmo) {
      if (!confirmo) return;

      /* Sin cambio optimista, al contrario del boton de estado: aca la fila
         no cambia de color, cambia de bloque. Pintar algo antes de la
         respuesta significaria moverla de lugar y tener que devolverla si el
         pedido falla. */
      boton.disabled = true;

      window.Api.post('/usuarios/' + id + '/estado', { activo: false }).then(
        function (actualizado) {
          avisarExito(
            'Se rechazó la solicitud de ' + actualizado.nombre +
            '. La cuenta quedó inactiva.'
          );
          return cargarListado();
        },
        function (error) {
          boton.disabled = false;
          mostrarError(
            pantalla.errorListado,
            pantalla.textoErrorListado,
            error.message
          );
        }
      );
    });
  }

  /* Actualiza la copia en memoria, para que el modal de edicion no abra con
     datos viejos sin tener que recargar el listado entero. */
  function actualizarEnListado(usuario) {
    for (var i = 0; i < listado.length; i += 1) {
      if (listado[i].id === usuario.id) {
        listado[i] = usuario;
        return;
      }
    }
  }

  function usuarioDelListado(id) {
    for (var i = 0; i < listado.length; i += 1) {
      if (listado[i].id === id) return listado[i];
    }
    return null;
  }

  /* --------------------------------------------------------------- arranque -- */

  /* Un solo listener en el contenedor del listado, no uno por fila.

     El listado se reemplaza entero con innerHTML cada vez que se recarga, asi
     que los listeners puestos fila por fila se pierden en cada recarga y hay
     que volver a engancharlos. Delegando, las filas nuevas funcionan solas.

     El boton se busca con closest() y no se compara contra event.target,
     porque el clic puede caer en el <svg> o en el <span> de adentro. */
  function alHacerClicEnUnaFila(evento) {
    var boton = evento.target.closest('[data-accion]');
    if (!boton || !evento.currentTarget.contains(boton)) return;

    var accion = boton.dataset.accion;
    var id = Number(boton.dataset.id);

    /* Editar y aprobar abren el MISMO modal con el mismo usuario: el modo lo
       deduce el modal del rol que tiene cargado, asi que las dos acciones no
       necesitan decirselo. */
    if (accion === 'editar' || accion === 'aprobar') {
      var usuario = usuarioDelListado(id);
      if (usuario) abrirModal(usuario);
      return;
    }

    if (accion === 'rechazar') {
      rechazar(boton);
      return;
    }

    if (accion === 'estado') alternarEstado(boton, evento);
  }

  /* Un listener por CONTENEDOR, no uno por fila: las dos listas se reemplazan
     enteras con innerHTML en cada recarga, y los listeners puestos fila por
     fila se perderian con ellas. Delegando, las filas nuevas funcionan solas.

     Son dos contenedores y un solo manejador. `evento.currentTarget` es el
     contenedor al que esta enganchado —no el elemento clickeado—, asi que la
     comprobacion de pertenencia funciona igual en los dos sin preguntar en
     cual estamos. */
  function engancharListado() {
    pantalla.lista.addEventListener('click', alHacerClicEnUnaFila);
    pantalla.listaPendientes.addEventListener('click', alHacerClicEnUnaFila);
  }

  function engancharModal() {
    /* La funcion se llama sin argumentos a proposito: el evento de click que
       pasaria addEventListener se interpretaria como el usuario a editar. */
    pantalla.botonNuevo.addEventListener('click', function () { abrirModal(); });
    pantalla.botonCerrar.addEventListener('click', cerrarModal);
    pantalla.botonCancelar.addEventListener('click', cerrarModal);
    pantalla.formulario.addEventListener('submit', guardar);

    /* A PROPOSITO: ningun listener de clic en el backdrop. Este modal no se
       cierra tocando afuera — perder un alta a medio tipear es un problema
       real. Escape si lo cierra, porque es una accion intencional y es lo que
       cualquiera espera de un dialogo. */
    document.addEventListener('keydown', function (evento) {
      if (evento.key === 'Escape' && modalAbierto()) cerrarModal();
    });
  }

  function iniciar() {
    pantalla = {
      lista: document.getElementById('lista-usuarios'),
      seccionPendientes: document.getElementById('seccion-pendientes'),
      listaPendientes: document.getElementById('lista-pendientes'),
      contadorPendientes: document.querySelector('[data-contador-pendientes]'),
      tituloConRol: document.getElementById('titulo-con-rol'),
      errorListado: document.getElementById('error-listado'),
      textoErrorListado: document.querySelector('[data-texto-error-listado]'),

      botonNuevo: document.getElementById('boton-nuevo'),
      modal: document.getElementById('modal-alta'),
      titulo: document.getElementById('modal-alta-titulo'),
      subtitulo: document.querySelector('[data-modal-sub]'),
      bloquePassword: document.getElementById('bloque-password'),
      botonCerrar: document.getElementById('boton-cerrar-modal'),
      botonCancelar: document.getElementById('boton-cancelar'),
      botonCrear: document.getElementById('boton-crear'),

      formulario: document.getElementById('form-alta'),
      campoNombre: document.getElementById('campo-nombre'),
      campoEmail: document.getElementById('campo-email-alta'),
      campoPassword: document.getElementById('campo-password-alta'),
      campoRol: document.getElementById('campo-rol'),
      campoTelefono: document.getElementById('campo-telefono'),
      requisitos: document.getElementById('requisitos-password'),

      errorAlta: document.getElementById('error-alta'),
      textoErrorAlta: document.querySelector('[data-texto-error-alta]')
    };

    /* Guarda barata: si este archivo se incluyera en otra pagina, no tira un
       error de consola sobre un elemento nulo. */
    if (!pantalla.lista) return;

    /* El esqueleto primero. Si no hay sesion, layout.js redirige al login y
       devuelve una promesa que no se resuelve nunca, asi que nada de lo que
       sigue corre. Lo mismo si el rol no esta habilitado: monta el esqueleto,
       explica por que no puede entrar y no resuelve. */
    window.Layout.montar({ roles: ROLES_HABILITADOS }).then(function (usuario) {
      /* Se guarda quien esta mirando: su propia fila lleva el boton de estado
         deshabilitado, porque desactivarse a uno mismo deja la cuenta sin
         forma de volver a entrar. */
      usuarioSesion = usuario;

      engancharListado();
      engancharModal();
      cargarListado();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
}());

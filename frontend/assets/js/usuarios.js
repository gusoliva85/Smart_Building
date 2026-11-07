/* ============================================================================
   usuarios.js — Logica de la pantalla de usuarios (usuarios.html).

   Un .js por pantalla, igual que login.js: se ocupa solo de SU pantalla y
   apoya todo lo transversal en los modulos compartidos (api.js, layout.js,
   formularios.js, cargando.js).

   Lo que hace:
     1. Monta el esqueleto por layout.js, declarando quien puede entrar.
     2. Lista los usuarios (activos e inactivos).
     3. Da de alta uno nuevo en un modal.

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

    pantalla.lista.parentNode.insertBefore(aviso, pantalla.lista);
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

  function pintarListado(usuarios) {
    if (!usuarios.length) {
      /* Este caso no deberia poder verse nunca —quien esta mirando la
         pantalla es, el mismo, un usuario del listado— pero el estado vacio se
         escribe igual: es parte del checklist de pantalla terminada, y el dia
         que el listado se filtre por alcance (F1-T08) va a ser alcanzable. */
      pantalla.lista.innerHTML =
        '<div class="lista-vacia"><b>No hay usuarios todavía</b>' +
        'Creá el primero con el botón de arriba.</div>';
      return;
    }

    listado = usuarios;
    pantalla.lista.innerHTML = usuarios.map(htmlDeFila).join('');
  }

  function cargarListado() {
    limpiarError(pantalla.errorListado, pantalla.textoErrorListado);
    pantalla.lista.innerHTML =
      '<div class="lista-vacia">' + window.Cargando.html() + '</div>';

    return window.Api.get('/usuarios').then(
      function (usuarios) {
        pintarListado(usuarios);
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

  /* ----------------------------------------------------------- modal de alta */

  /* Llena el <select> de roles y la ayuda de contrasenia con lo que manda el
     backend. Se pide UNA sola vez y queda guardado: el catalogo de roles y la
     politica no cambian entre dos altas de la misma sesion. */
  function asegurarOpciones() {
    if (opcionesDeAlta) return Promise.resolve(opcionesDeAlta);

    return window.Api.get('/usuarios/opciones').then(function (datos) {
      opcionesDeAlta = datos;

      pantalla.campoRol.innerHTML = '';
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
  function configurarModal(usuario) {
    enEdicion = usuario || null;

    var editando = Boolean(usuario);

    pantalla.titulo.textContent = editando ? 'Editar usuario' : 'Nuevo usuario';
    pantalla.botonCrear.textContent = editando ? 'Guardar cambios' : 'Crear usuario';

    pantalla.subtitulo.textContent = editando
      ? 'La contraseña no se cambia desde acá: el backend no la acepta por ' +
        'esta vía y todavía no hay circuito de recuperación.'
      : 'Nace activo y con la contraseña que definas acá — se la comunicás ' +
        'vos, todavía no hay circuito de invitación por email.';

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
           asegurarOpciones(). Fijarlo antes no haria nada y el <select>
           quedaria en el primer rol de la lista, que es el de mas permisos. */
        if (enEdicion) pantalla.campoRol.value = enEdicion.rol;

        pantalla.campoNombre.focus();
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

    pedido.then(function (guardado) {
      var mensaje = editando
        ? 'Se guardaron los cambios de ' + guardado.nombre + '.'
        : 'Se creó la cuenta de ' + guardado.nombre + '.';
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
  function engancharListado() {
    pantalla.lista.addEventListener('click', function (evento) {
      var boton = evento.target.closest('[data-accion]');
      if (!boton || !pantalla.lista.contains(boton)) return;

      var id = Number(boton.dataset.id);

      if (boton.dataset.accion === 'editar') {
        var usuario = usuarioDelListado(id);
        if (usuario) abrirModal(usuario);
        return;
      }

      if (boton.dataset.accion === 'estado') alternarEstado(boton, evento);
    });
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

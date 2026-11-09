/* ============================================================================
   login.js — Logica de la pantalla de inicio de sesion (index.html).

   Es el primer archivo "por pantalla" del proyecto: la convencion es un .js
   por dominio, que se ocupa solo de SU pantalla y apoya todo lo transversal
   en los modulos compartidos (api.js, formularios.js, theme.js).

   Lo que hace, y nada mas que esto:
     1. Pide el token con las credenciales.
     2. Lo guarda.
     3. Verifica con GET /auth/me que el token sirve de verdad, y muestra
        quien entro.
     4. Da de alta una cuenta propia, sin rol, desde la misma pantalla.

   LAS TRES TARJETAS, QUE ENTRARON EN F1-T16B. index.html tiene tres
   secciones y este archivo decide cual se ve; nunca dos a la vez:

     - login: el formulario de credenciales. Es el estado normal.
     - registro: el alta propia. No pide rol, y eso es el punto de la tarea
       entera — el rol lo pone el backend como constante y lo asigna despues
       un administrador.
     - sesion: el final para quien entro bien y no tiene a donde ir. Son dos
       casos distintos con el mismo aspecto: un rol sin pantallas todavia, y
       una cuenta que espera aprobacion. El texto los distingue, porque
       quedarse en el login despues de entrar bien se lee como un fallo si no
       se explica.

   LA REDIRECCION, QUE ENTRO EN F1-T13. El destino no es una constante: es
   la primera pantalla construida que el rol del usuario puede ver, leida de
   la tabla de accesos de layout.js. Dos razones por las que sale de ahi:

     - No hay una pantalla de inicio unica todavia. El dashboard llega en la
       Fase 5; hasta entonces "la pantalla inicial" es la primera del menu, y
       eso cambia en cada fase.
     - Un rol puede no tener ninguna pantalla construida. Hoy les pasa a
       siete de los ocho. Mandarlos igual a usuarios.html seria mandarlos a
       una pantalla que les va a decir que no es para ellos. Para esos, el
       login sigue mostrando la tarjeta de sesion, que ahora explica eso.

   Depende de config.js, api.js y layout.js, cargados antes.
   ========================================================================== */

(function () {
  'use strict';

  /* El rol que pone el backend al registrarse. Esta escrito aca como cadena
     y es consistente con el resto del frontend —layout.js tiene la lista de
     roles de cada acceso, usuarios.js la de los que pueden entrar—, pero vale
     decir por que no se deduce de los permisos que manda el backend: se
     podria mirar `usuario.permisos.alcance === 'ninguno'`, que hoy da lo
     mismo, y seria peor. "Alcance ninguno" describe lo que la cuenta puede
     ver; "pendiente" describe por que. El dia que exista otro rol sin alcance
     —un usuario suspendido, por ejemplo— ese atajo le mostraria el texto de
     "esperando aprobacion" a alguien que no esta esperando nada. */
  var ROL_PENDIENTE = 'pendiente';

  /* Los elementos se buscan una sola vez y se guardan juntos arriba. Es la
     convencion del proyecto para el estado de una pantalla: todo declarado
     en un solo bloque, no repartido por el archivo. */
  var pantalla = {};

  /* La politica de contrasenia, pedida una sola vez por visita y solo si
     alguien abre el registro. Guardarla evita volver a pedirla si la persona
     va y vuelve entre las dos tarjetas. */
  var politica = null;

  /* ---------------------------------------------------------- vista -------- */

  /* Las tres tarjetas son excluyentes. Se esconden todas y se muestra una:
     con un hidden por tarjeta repartido en cada funcion, agregar la tercera
     habria significado revisar que las dos viejas se acordaran de esconderla.
     Asi, una tarjeta nueva se suma en un solo lugar. */
  function mostrarSolo(cual) {
    pantalla.tarjetaLogin.hidden = cual !== pantalla.tarjetaLogin;
    pantalla.tarjetaRegistro.hidden = cual !== pantalla.tarjetaRegistro;
    pantalla.tarjetaSesion.hidden = cual !== pantalla.tarjetaSesion;
  }

  function mostrarFormulario() {
    mostrarSolo(pantalla.tarjetaLogin);
  }

  /* La tarjeta de sesion es el final de quien entro bien y no tiene a donde
     ir. Son DOS situaciones, y el texto es lo unico que las distingue:

       - Una cuenta que espera aprobacion. No es un faltante del sistema: es
         el estado normal de quien se acaba de registrar, y hay que decirle
         que falta un paso y que lo da otra persona. Si leyera el texto del
         otro caso —"todavia no hay pantallas para tu rol"— se quedaria
         esperando una version del sistema que no es lo que le falta.
       - Un rol que todavia no tiene ninguna pantalla construida. Hoy les
         pasa a siete de los ocho.

     En los dos casos la tarjeta muestra los datos de la cuenta, porque es lo
     que confirma que el login funciono de verdad. */
  function mostrarSesion(usuario) {
    var pendiente = usuario.rol === ROL_PENDIENTE;

    /* rol_etiqueta lo calcula el backend desde la matriz de roles. El
       frontend NO tiene su propia tabla de nombres de rol: seria una
       traduccion paralela que algun dia queda desactualizada. */
    pantalla.sesionNombre.textContent = usuario.nombre;
    pantalla.sesionRol.textContent = usuario.rol_etiqueta;
    pantalla.sesionEmail.textContent = usuario.email;

    pantalla.sesionTitulo.textContent = pendiente
      ? 'Tu cuenta espera aprobación'
      : 'Sesión iniciada';

    pantalla.sesionNota.textContent = pendiente
      ? 'Tus datos están cargados y la contraseña funciona: por eso pudiste ' +
        'entrar. Falta que un administrador te asigne el rol que te ' +
        'corresponde, y hasta entonces no vas a ver nada del consorcio. ' +
        'Volvé a iniciar sesión más adelante para ver si ya está aprobada.'
      : 'Entraste bien, pero todavía no hay ninguna pantalla para el rol ' +
        usuario.rol_etiqueta + '. Se van a ir sumando a medida que el sistema ' +
        'crezca; mientras tanto, esto confirma que la cuenta funciona.';

    mostrarSolo(pantalla.tarjetaSesion);
  }

  /* Manda al usuario a su primera pantalla, o muestra la tarjeta si no tiene
     ninguna. Es el UNICO lugar del archivo que decide eso: cuando exista el
     dashboard de la Fase 5, se cambia aca y en ningun otro lado. */
  function entrarALaAplicacion(usuario) {
    /* El pendiente no pasa por la tabla de accesos. Hoy daria lo mismo
       —`pendiente` no figura en ninguna fila, asi que paginaInicialDe()
       devuelve null igual— pero preguntarlo primero deja la decision escrita
       donde se lee: una cuenta sin aprobar no se rutea a ninguna pantalla,
       ni siquiera si manana alguien agrega `pendiente` a un acceso por error.
       Y es la unica forma de mostrarle el texto que le corresponde. */
    if (usuario.rol === ROL_PENDIENTE) {
      mostrarSesion(usuario);
      return;
    }

    var destino = window.Layout.paginaInicialDe(usuario.rol);

    if (destino) {
      window.location.href = destino;
      return;
    }

    mostrarSesion(usuario);
  }

  /* Las cajas de mensaje reciben la caja y su <span>, en vez de haber una
     funcion por tarjeta. Es la misma forma que usa usuarios.js, y la razon es
     la que aparecio al agregar la segunda tarjeta: con una funcion por caja,
     cada tarjeta nueva trae su par de funciones iguales a las anteriores. */
  function mostrarMensaje(caja, texto, mensaje) {
    texto.textContent = mensaje;
    caja.hidden = false;
  }

  function limpiarMensaje(caja, texto) {
    caja.hidden = true;
    texto.textContent = '';
  }

  function mostrarError(mensaje) {
    mostrarMensaje(pantalla.error, pantalla.textoError, mensaje);
  }

  function limpiarError() {
    limpiarMensaje(pantalla.error, pantalla.textoError);
  }

  /* El boton se bloquea mientras dura el pedido —si no, tres clics son tres
     intentos— y se rehabilita pase lo que pase.

     En el registro el bloqueo importa mas que en el login: tres clics son
     tres altas, y la segunda y la tercera chocarian con el email de la
     primera. El usuario leeria "ese email ya existe" sobre una cuenta que
     acaba de crear el mismo. */
  function bloquear(boton, bloqueado, textoOcupado, textoNormal) {
    boton.disabled = bloqueado;
    boton.textContent = bloqueado ? textoOcupado : textoNormal;
  }

  function bloquearEnvio(bloqueado) {
    bloquear(pantalla.botonEntrar, bloqueado, 'Ingresando…', 'Iniciar sesión');
  }

  /* ---------------------------------------------------------- acciones ----- */

  function entrar(evento) {
    evento.preventDefault();
    limpiarError();
    /* El aviso del registro se va al primer intento de login: a partir de
       ahi, lo que importa es el resultado de ESTE pedido. Dejarlo visible
       junto a un error de credenciales mostraria dos mensajes que se
       contradicen. */
    limpiarMensaje(pantalla.exitoLogin, pantalla.textoExitoLogin);

    var email = pantalla.campoEmail.value.trim();
    var password = pantalla.campoPassword.value;

    /* Validacion minima en el cliente, con los mensajes del proyecto y no
       los globos nativos del navegador (de ahi el novalidate del <form>).
       No reemplaza a la del backend: solo evita un viaje de ida y vuelta
       para algo que ya se sabe que esta incompleto. */
    if (!email || !password) {
      mostrarError('Completá el email y la contraseña.');
      (email ? pantalla.campoPassword : pantalla.campoEmail).focus();
      return;
    }

    bloquearEnvio(true);

    /* Dos cosas que no son obvias en esta llamada:

       - `username` y no `email`: el endpoint usa el formulario estandar de
         OAuth2, donde el campo del identificador se llama asi. El backend lo
         documenta: respetarlo es lo que hace que el boton "Authorize" de
         /docs funcione.

       - redirigirEn401: false. Es LA excepcion deliberada del envoltorio de
         api.js. En cualquier otra pantalla un 401 significa "tu sesion
         vencio" y corresponde expulsar al login; aca significa "esas
         credenciales no son correctas" y hay que mostrarlo en el formulario,
         no recargar la pantalla en la que el usuario ya esta. */
    window.Api.postFormulario(
      '/auth/login',
      { username: email, password: password },
      { redirigirEn401: false }
    ).then(function (datos) {
      window.Api.Sesion.guardarToken(datos.access_token);

      /* Guardar el token no prueba que sirva. Este segundo pedido es el que
         lo verifica, y de paso trae el nombre y el rol para mostrar. */
      return window.Api.get('/auth/me', { redirigirEn401: false });
    }).then(function (usuario) {
      pantalla.formulario.reset();
      entrarALaAplicacion(usuario);
    }).catch(function (error) {
      /* Si el login funciono pero /auth/me fallo, el token guardado no
         sirve: se descarta para no dejar una sesion a medias que despues
         expulse al usuario desde cualquier otra pantalla. */
      window.Api.Sesion.limpiar();
      mostrarError(error.message);
      pantalla.campoPassword.value = '';
      pantalla.campoPassword.focus();
    }).then(function () {
      bloquearEnvio(false);
    });
  }

  /* ---------------------------------------------------------- registro ---- */

  /* Los requisitos de la contrasenia los escribe el backend. Se piden al
     abrir la tarjeta y no al cargar la pagina: la enorme mayoria de las
     visitas al login no se registran, y es un pedido que no hace falta.

     Si el pedido falla, la tarjeta se abre igual y sin la ayuda. Es
     deliberado: la politica es una ayuda, no un requisito para escribir, y el
     backend la aplica igual. Bloquear el registro porque no se pudo traer un
     texto explicativo seria cambiar un inconveniente por una pared. */
  function pedirPolitica() {
    if (politica) return Promise.resolve(politica);

    return window.Api.get('/auth/politica-password').then(function (datos) {
      politica = datos;

      pantalla.requisitos.innerHTML = '';
      datos.requisitos.forEach(function (requisito) {
        var item = document.createElement('li');
        /* textContent y no innerHTML: el texto viene de la red. */
        item.textContent = requisito;
        pantalla.requisitos.appendChild(item);
      });

      return datos;
    });
  }

  function irAlRegistro() {
    limpiarError();
    limpiarMensaje(pantalla.exitoLogin, pantalla.textoExitoLogin);
    limpiarMensaje(pantalla.errorRegistro, pantalla.textoErrorRegistro);
    mostrarSolo(pantalla.tarjetaRegistro);
    pantalla.campoRegistroNombre.focus();

    /* El fallo se traga a proposito: ver el comentario de pedirPolitica(). */
    pedirPolitica().catch(function () {});
  }

  function volverAlLogin() {
    limpiarMensaje(pantalla.errorRegistro, pantalla.textoErrorRegistro);
    mostrarFormulario();
    pantalla.campoEmail.focus();
  }

  function registrarse(evento) {
    evento.preventDefault();
    limpiarMensaje(pantalla.errorRegistro, pantalla.textoErrorRegistro);

    var nombre = pantalla.campoRegistroNombre.value.trim();
    var email = pantalla.campoRegistroEmail.value.trim();
    var password = pantalla.campoRegistroPassword.value;
    var telefono = pantalla.campoRegistroTelefono.value.trim();

    /* Validacion minima, con los mensajes del proyecto y no los globos
       nativos del navegador. NO duplica la del backend: el largo del nombre,
       el formato del email y la politica de contrasenia los valida el
       backend, que es el que manda. */
    if (!nombre || !email || !password) {
      mostrarMensaje(
        pantalla.errorRegistro,
        pantalla.textoErrorRegistro,
        'Completá el nombre, el email y la contraseña.'
      );
      return;
    }

    bloquear(pantalla.botonRegistrar, true, 'Creando…', 'Crear la cuenta');

    /* NO SE MANDA NINGUN ROL, y no es un olvido: el esquema del backend no
       tiene ese campo y rechaza los que no conoce, asi que mandarlo seria un
       422. El rol lo pone el endpoint como constante.

       null y no "" cuando no hay telefono: una cadena vacia guardada se lee
       despues como un telefono que existe y esta en blanco, no como uno que
       no se cargo.

       redirigirEn401: false no hace falta aca —este endpoint no devuelve
       401— y por eso no esta: el envoltorio hace lo correcto solo. */
    window.Api.post('/auth/registro', {
      nombre: nombre,
      email: email,
      password: password,
      telefono: telefono || null
    }).then(function (respuesta) {
      pantalla.formularioRegistro.reset();

      /* El toggle de mostrar/ocultar queda como lo dejo el usuario: reset()
         no devuelve el input a type="password". Se le pide a formularios.js
         que lo sincronice, para que la contrasenia no quede a la vista si
         alguien vuelve a abrir el registro. */
      pantalla.campoRegistroPassword.type = 'password';
      if (window.Formularios && window.Formularios.sincronizarToggles) {
        window.Formularios.sincronizarToggles();
      }

      /* Se vuelve al login con el email ya puesto y el mensaje del backend
         arriba. El mensaje NO se escribe aca: es el que decidio el endpoint,
         y es el mismo para un email nuevo que para uno que ya existia —esa
         indistinguibilidad es una defensa deliberada contra averiguar quien
         tiene cuenta, y escribir el texto en el frontend seria la forma mas
         facil de arruinarla sin darse cuenta. */
      mostrarFormulario();
      mostrarMensaje(
        pantalla.exitoLogin,
        pantalla.textoExitoLogin,
        respuesta.mensaje
      );
      pantalla.campoEmail.value = email;
      pantalla.campoPassword.focus();
    }).catch(function (error) {
      mostrarMensaje(
        pantalla.errorRegistro,
        pantalla.textoErrorRegistro,
        error.message
      );
    }).then(function () {
      bloquear(pantalla.botonRegistrar, false, 'Creando…', 'Crear la cuenta');
    });
  }

  function salir() {
    window.Api.Sesion.limpiar();
    limpiarError();
    mostrarFormulario();
    pantalla.campoEmail.focus();
  }

  /* ---------------------------------------------------------- arranque ----- */

  /* Si ya hay un token guardado, la pantalla no vuelve a pedir las
     credenciales: verifica el token contra el backend. Es lo que hace que
     recargar la pagina no pierda la sesion.

     Si el token ya no vale, api.js lo limpia solo al recibir el 401 y se
     muestra el formulario, sin ningun mensaje de error: no es un fallo del
     usuario, simplemente venia de antes. */
  function revisarSesionPrevia() {
    if (!window.Api.Sesion.activa()) {
      mostrarFormulario();
      return;
    }

    window.Api.get('/auth/me', { redirigirEn401: false }).then(
      function (usuario) {
        entrarALaAplicacion(usuario);
      },
      function () {
        window.Api.Sesion.limpiar();
        mostrarFormulario();
      }
    );
  }

  function iniciar() {
    pantalla = {
      tarjetaLogin: document.getElementById('tarjeta-login'),
      tarjetaSesion: document.getElementById('tarjeta-sesion'),
      formulario: document.getElementById('form-login'),
      campoEmail: document.getElementById('campo-email'),
      campoPassword: document.getElementById('campo-password'),
      botonEntrar: document.getElementById('boton-entrar'),
      botonSalir: document.getElementById('boton-salir'),
      error: document.getElementById('error-login'),
      textoError: document.querySelector('[data-texto-error]'),
      exitoLogin: document.getElementById('exito-login'),
      textoExitoLogin: document.querySelector('[data-texto-exito-login]'),

      tarjetaRegistro: document.getElementById('tarjeta-registro'),
      formularioRegistro: document.getElementById('form-registro'),
      campoRegistroNombre: document.getElementById('campo-registro-nombre'),
      campoRegistroEmail: document.getElementById('campo-registro-email'),
      campoRegistroPassword: document.getElementById('campo-registro-password'),
      campoRegistroTelefono: document.getElementById('campo-registro-telefono'),
      botonRegistrar: document.getElementById('boton-registrar'),
      botonIrRegistro: document.getElementById('boton-ir-registro'),
      botonVolverLogin: document.getElementById('boton-volver-login'),
      requisitos: document.getElementById('requisitos-registro'),
      errorRegistro: document.getElementById('error-registro'),
      textoErrorRegistro: document.querySelector('[data-texto-error-registro]'),

      sesionTitulo: document.querySelector('[data-sesion-titulo]'),
      sesionNombre: document.querySelector('[data-sesion-nombre]'),
      sesionRol: document.querySelector('[data-sesion-rol]'),
      sesionEmail: document.querySelector('[data-sesion-email]'),
      sesionNota: document.querySelector('[data-sesion-nota]')
    };

    /* Este archivo se carga solo desde index.html, pero la guarda es barata:
       si alguna vez se incluye en otra pagina, no tira un error de consola
       sobre un elemento nulo. */
    if (!pantalla.formulario) return;

    pantalla.formulario.addEventListener('submit', entrar);
    pantalla.botonSalir.addEventListener('click', salir);

    pantalla.botonIrRegistro.addEventListener('click', irAlRegistro);
    pantalla.botonVolverLogin.addEventListener('click', volverAlLogin);
    pantalla.formularioRegistro.addEventListener('submit', registrarse);

    revisarSesionPrevia();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
}());

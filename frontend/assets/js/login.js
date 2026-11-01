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

   SOBRE LA REDIRECCION QUE TODAVIA NO ESTA. El plan para esta tarea decia
   "token en localStorage y redireccion". No hay a donde redirigir: la
   primera pantalla autenticada (usuarios.html) llega en F1-T13 y la regla
   del proyecto prohibe enlazar un archivo que no existe. En vez de dejar un
   enlace roto, el login muestra el resultado del pedido autenticado, que es
   lo que hay que poder verificar hoy. Cuando exista la pantalla, se cambia
   `mostrarSesion` por la redireccion: es un solo lugar.

   Depende de config.js y api.js, cargados antes.
   ========================================================================== */

(function () {
  'use strict';

  /* Los elementos se buscan una sola vez y se guardan juntos arriba. Es la
     convencion del proyecto para el estado de una pantalla: todo declarado
     en un solo bloque, no repartido por el archivo. */
  var pantalla = {};

  /* ---------------------------------------------------------- vista -------- */

  /* Las dos tarjetas son excluyentes: nunca se ven las dos juntas. */
  function mostrarFormulario() {
    pantalla.tarjetaLogin.hidden = false;
    pantalla.tarjetaSesion.hidden = true;
  }

  function mostrarSesion(usuario) {
    /* rol_etiqueta lo calcula el backend desde la matriz de roles. El
       frontend NO tiene su propia tabla de nombres de rol: seria una
       traduccion paralela que algun dia queda desactualizada. */
    pantalla.sesionNombre.textContent = usuario.nombre;
    pantalla.sesionRol.textContent = usuario.rol_etiqueta;
    pantalla.sesionEmail.textContent = usuario.email;

    pantalla.tarjetaLogin.hidden = true;
    pantalla.tarjetaSesion.hidden = false;
  }

  function mostrarError(mensaje) {
    pantalla.textoError.textContent = mensaje;
    pantalla.error.hidden = false;
  }

  function limpiarError() {
    pantalla.error.hidden = true;
    pantalla.textoError.textContent = '';
  }

  /* El boton se bloquea mientras dura el pedido —si no, tres clics son tres
     intentos de login— y se rehabilita pase lo que pase. */
  function bloquearEnvio(bloqueado) {
    pantalla.botonEntrar.disabled = bloqueado;
    pantalla.botonEntrar.textContent = bloqueado ? 'Ingresando…' : 'Iniciar sesión';
  }

  /* ---------------------------------------------------------- acciones ----- */

  function entrar(evento) {
    evento.preventDefault();
    limpiarError();

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
      mostrarSesion(usuario);
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
        mostrarSesion(usuario);
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
      sesionNombre: document.querySelector('[data-sesion-nombre]'),
      sesionRol: document.querySelector('[data-sesion-rol]'),
      sesionEmail: document.querySelector('[data-sesion-email]')
    };

    /* Este archivo se carga solo desde index.html, pero la guarda es barata:
       si alguna vez se incluye en otra pagina, no tira un error de consola
       sobre un elemento nulo. */
    if (!pantalla.formulario) return;

    pantalla.formulario.addEventListener('submit', entrar);
    pantalla.botonSalir.addEventListener('click', salir);

    revisarSesionPrevia();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
}());

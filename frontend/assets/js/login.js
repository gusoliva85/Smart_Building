// login.js — lógica propia de index.html (pantalla de login).
//
// Sin selector de rol visible: el rol lo determina el backend a partir del
// usuario, nunca lo elige quien se loguea. Tras un login exitoso (o si ya
// hay un token guardado de una sesión previa), redirige a dashboard.html
// — el "home" de la zona autenticada, que sí tiene el sidebar de navegación
// (Documento Técnico, sección 4.1).
document.addEventListener('DOMContentLoaded', async () => {
  // Ya hay una sesión guardada (recarga, o volver atrás desde otra pestaña):
  // no tiene sentido mostrar el formulario de nuevo.
  if (window.Api.obtenerToken()) {
    location.href = 'dashboard.html';
    return;
  }

  const formulario = document.getElementById('form-login');
  window.Formularios.habilitarEnterComoTab(formulario);
  const campoEmail = document.getElementById('campo-email');
  const campoPassword = document.getElementById('campo-password');
  const mensajeError = document.getElementById('mensaje-error');
  const mensajeErrorTexto = document.getElementById('mensaje-error-texto');
  const botonIngresar = document.getElementById('boton-ingresar');

  formulario.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    mensajeError.style.display = 'none';
    botonIngresar.disabled = true;
    botonIngresar.textContent = 'Ingresando…';

    try {
      const respuesta = await window.Api.post('/auth/login', {
        email: campoEmail.value.trim(),
        password: campoPassword.value,
      });
      window.Api.guardarToken(respuesta.access_token);
      location.href = 'dashboard.html';
    } catch (error) {
      mensajeErrorTexto.textContent = error.message;
      mensajeError.style.display = 'flex';
      botonIngresar.disabled = false;
      botonIngresar.textContent = 'Ingresar';
    }
  });
});

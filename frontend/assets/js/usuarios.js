// usuarios.js — lógica de usuarios.html (listado, alta, activar/desactivar).
document.addEventListener('DOMContentLoaded', async () => {
  const usuarioActual = await window.Layout.montar('usuarios.html');
  if (!usuarioActual) return;

  const vistaNoAutorizado = document.getElementById('vista-no-autorizado');
  const vistaUsuarios = document.getElementById('vista-usuarios');

  if (usuarioActual.rol !== 'admin_general') {
    vistaNoAutorizado.style.display = 'block';
    return;
  }

  vistaUsuarios.style.display = 'block';

  const listaUsuarios = document.getElementById('lista-usuarios');
  const modalAlta = document.getElementById('modal-alta');
  const formulario = document.getElementById('form-alta');
  const mensajeError = document.getElementById('mensaje-error');
  const mensajeErrorTexto = document.getElementById('mensaje-error-texto');
  const botonGuardar = document.getElementById('boton-guardar');

  window.Formularios.habilitarEnterComoTab(formulario);

  const ETIQUETAS_ROL = window.Layout.ETIQUETAS_ROL;

  async function cargarListado() {
    listaUsuarios.innerHTML = '<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">Cargando…</p>';
    let usuarios;
    try {
      usuarios = await window.Api.get('/usuarios');
    } catch (error) {
      listaUsuarios.innerHTML = `<p style="font-size:12.5px;color:var(--crit);padding:10px 0;">${error.message}</p>`;
      return;
    }

    listaUsuarios.innerHTML = usuarios
      .map((u) => `
        <div class="detail-item content-glass fila-lista" data-id="${u.id}">
          <div>
            <b style="font-size:13.5px;">${u.nombre}</b>
            <div style="font-size:11.5px;color:var(--ink-3);">${u.email}</div>
          </div>
          <div class="fila-lista-acciones">
            <span class="rol-badge">${ETIQUETAS_ROL[u.rol] || u.rol}</span>
            <span class="pill ${u.activo ? 'ok' : 'crit'}">${u.activo ? 'Activo' : 'Inactivo'}</span>
            <button type="button" class="chip-link boton-alternar-estado" data-id="${u.id}" data-activo="${u.activo}">
              ${u.activo ? 'Desactivar' : 'Reactivar'}
            </button>
          </div>
        </div>`)
      .join('');

    listaUsuarios.querySelectorAll('.boton-alternar-estado').forEach((boton) => {
      boton.addEventListener('click', () => alternarEstado(boton));
    });
  }

  async function alternarEstado(boton) {
    const id = boton.dataset.id;
    const estaActivo = boton.dataset.activo === 'true';
    boton.disabled = true;
    try {
      if (estaActivo) {
        await window.Api.post(`/usuarios/${id}/desactivar`);
      } else {
        await window.Api.patch(`/usuarios/${id}`, { activo: true });
      }
      await cargarListado();
    } catch (error) {
      boton.disabled = false;
      alert(error.message); // acción secundaria de una fila — no amerita su propio modal
    }
  }

  // ---------------------------------------------------------------
  // Modal de alta — a diferencia del panel .detail que usaba antes, este
  // NUNCA se cierra tocando el fondo: solo con la X, Cancelar, o
  // completando el formulario (feedback explícito del usuario).
  // ---------------------------------------------------------------
  function abrirModal() {
    modalAlta.classList.add('open');
    document.getElementById('campo-nombre').focus();
  }
  function cerrarModal() {
    modalAlta.classList.remove('open');
    formulario.reset();
    mensajeError.style.display = 'none';
    // el toggle de contraseña no se resetea solo con formulario.reset()
    const inputPassword = document.getElementById('campo-password');
    const botonToggle = modalAlta.querySelector('.campo-password-toggle');
    inputPassword.type = 'password';
    botonToggle.querySelector('svg').innerHTML = window.Formularios.ICONO_OJO;
    botonToggle.setAttribute('aria-label', 'Mostrar contraseña');
  }
  document.getElementById('boton-nuevo-usuario').addEventListener('click', abrirModal);
  document.getElementById('modal-alta-cerrar').addEventListener('click', cerrarModal);
  document.getElementById('boton-cancelar').addEventListener('click', cerrarModal);

  formulario.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    mensajeError.style.display = 'none';
    botonGuardar.disabled = true;
    botonGuardar.textContent = 'Creando…';

    try {
      await window.Api.post('/usuarios', {
        nombre: document.getElementById('campo-nombre').value.trim(),
        email: document.getElementById('campo-email').value.trim(),
        password: document.getElementById('campo-password').value,
        rol: document.getElementById('campo-rol').value,
        telefono: document.getElementById('campo-telefono').value.trim() || null,
      });
      cerrarModal();
      await cargarListado();
    } catch (error) {
      mensajeErrorTexto.textContent = error.message;
      mensajeError.style.display = 'flex';
    } finally {
      botonGuardar.disabled = false;
      botonGuardar.textContent = 'Crear usuario';
    }
  });

  await cargarListado();
});

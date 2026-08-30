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
  const backdrop = document.getElementById('backdrop');
  const detail = document.getElementById('detail');
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
  // Panel de alta (.detail)
  // ---------------------------------------------------------------
  function abrirDetail() {
    detail.classList.add('open');
    backdrop.classList.add('open');
    document.getElementById('campo-nombre').focus();
  }
  function cerrarDetail() {
    detail.classList.remove('open');
    backdrop.classList.remove('open');
    formulario.reset();
    mensajeError.style.display = 'none';
  }
  document.getElementById('boton-nuevo-usuario').addEventListener('click', abrirDetail);
  document.getElementById('detail-close').addEventListener('click', cerrarDetail);
  backdrop.addEventListener('click', cerrarDetail);

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
      cerrarDetail();
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

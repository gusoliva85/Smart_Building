// usuarios.js — lógica de usuarios.html (listado, alta, edición, activar/desactivar).
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
  const modalTitulo = document.getElementById('modal-alta-titulo');
  const modalSub = document.getElementById('modal-alta-sub');
  const formulario = document.getElementById('form-alta');
  const mensajeError = document.getElementById('mensaje-error');
  const mensajeErrorTexto = document.getElementById('mensaje-error-texto');
  const botonGuardar = document.getElementById('boton-guardar');
  const bloquePassword = document.getElementById('bloque-password');
  const campoNombre = document.getElementById('campo-nombre');
  const campoEmail = document.getElementById('campo-email');
  const campoPassword = document.getElementById('campo-password');
  const campoRol = document.getElementById('campo-rol');
  const campoTelefono = document.getElementById('campo-telefono');

  window.Formularios.habilitarEnterComoTab(formulario);

  const ETIQUETAS_ROL = window.Layout.ETIQUETAS_ROL;

  // usuarioEditandoId: null mientras el modal está en modo alta; el id del
  // usuario cuando está en modo edición — determina qué hace el submit.
  let usuarioEditandoId = null;
  let usuariosCache = {};

  // Arma el HTML de una fila a partir del usuario — la usan tanto el
  // listado completo (carga inicial) como reemplazarFila (actualización
  // puntual de una sola fila, sin recargar todo).
  function renderFila(u) {
    // Nadie puede desactivar su propia cuenta (el backend también lo
    // rechaza — esto es solo para no dejar ni intentarlo: un Admin
    // General que se desactiva a sí mismo queda afuera del sistema sin
    // vuelta, porque hace falta estar logueado como admin_general para
    // reactivar a alguien).
    const esUnoMismo = u.id === usuarioActual.id;
    return `
        <div class="detail-item content-glass fila-lista" data-id="${u.id}">
          <div>
            <b style="font-size:13.5px;">${u.nombre}</b>
            <div style="font-size:11.5px;color:var(--ink-3);">${u.email}</div>
          </div>
          <div class="fila-lista-acciones">
            <div class="fila-lista-estado">
              <span class="rol-badge">${ETIQUETAS_ROL[u.rol] || u.rol}</span>
            </div>
            <div class="fila-lista-botones">
              <button type="button" class="icon-btn icon-btn-sm boton-editar" data-id="${u.id}" aria-label="Editar usuario">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
              </button>
              <button type="button" class="boton-estado-usuario ${u.activo ? 'activo' : 'inactivo'} boton-alternar-estado"
                data-id="${u.id}" data-activo="${u.activo}" ${esUnoMismo ? 'disabled title="No podés desactivar tu propia cuenta"' : ''}>
                <span class="boton-estado-texto">${u.activo ? 'Activo' : 'Inactivo'}</span>
              </button>
            </div>
          </div>
        </div>`;
  }

  function conectarFila(fila) {
    fila.querySelector('.boton-editar').addEventListener('click', () => abrirModalEdicion(fila.dataset.id));
    fila.querySelector('.boton-alternar-estado').addEventListener('click', (evento) => alternarEstado(evento.currentTarget, evento));
  }

  // Ripple del color al que el botón está transicionando (adaptado de
  // RippleButton) — nace del punto exacto del clic, del tamaño necesario
  // para cubrir el botón entero desde cualquier esquina.
  function dispararRipple(boton, evento, color) {
    const rect = boton.getBoundingClientRect();
    const tamano = Math.max(rect.width, rect.height) * 2;
    const x = evento.clientX - rect.left - tamano / 2;
    const y = evento.clientY - rect.top - tamano / 2;
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    ripple.style.width = `${tamano}px`;
    ripple.style.height = `${tamano}px`;
    ripple.style.left = `${x}px`;
    ripple.style.top = `${y}px`;
    ripple.style.background = color;
    boton.appendChild(ripple);
    ripple.addEventListener('animationend', () => ripple.remove());
  }

  function pintarBotonEstado(boton, activo) {
    boton.dataset.activo = String(activo);
    boton.classList.toggle('activo', activo);
    boton.classList.toggle('inactivo', !activo);
    boton.querySelector('.boton-estado-texto').textContent = activo ? 'Activo' : 'Inactivo';
  }

  // Reemplaza SOLO el nodo de una fila con el usuario actualizado — la usan
  // alternarEstado y el submit en modo edición. Evita recargar/parpadear
  // el listado entero por cambiar un solo usuario.
  function reemplazarFila(usuario) {
    usuariosCache[usuario.id] = usuario;
    const filaActual = listaUsuarios.querySelector(`.fila-lista[data-id="${usuario.id}"]`);
    if (!filaActual) return;
    const contenedor = document.createElement('div');
    contenedor.innerHTML = renderFila(usuario).trim();
    const filaNueva = contenedor.firstElementChild;
    conectarFila(filaNueva);
    filaActual.replaceWith(filaNueva);
  }

  async function cargarListado() {
    listaUsuarios.innerHTML = `<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">${window.Cargando.html()}</p>`;
    let usuarios;
    try {
      usuarios = await window.Api.get('/usuarios');
    } catch (error) {
      listaUsuarios.innerHTML = `<p style="font-size:12.5px;color:var(--crit);padding:10px 0;">${error.message}</p>`;
      return;
    }

    usuariosCache = {};
    usuarios.forEach((u) => { usuariosCache[u.id] = u; });
    listaUsuarios.innerHTML = usuarios.map(renderFila).join('');
    listaUsuarios.querySelectorAll('.fila-lista').forEach(conectarFila);
  }

  // El botón muestra el estado actual Y lo alterna al click (fusiona lo
  // que antes eran dos elementos separados — un .pill de solo lectura +
  // un botón de acción — pedido explícito para aliviar el mobile). Cambio
  // optimista: el ripple y el color nuevo aparecen al instante del clic,
  // no recién cuando responde la API — si la llamada falla, se revierte.
  async function alternarEstado(boton, evento) {
    const id = boton.dataset.id;
    const estabaActivo = boton.dataset.activo === 'true';
    const nuevoActivo = !estabaActivo;

    dispararRipple(boton, evento, nuevoActivo ? 'var(--ok)' : 'var(--crit)');
    pintarBotonEstado(boton, nuevoActivo);
    boton.disabled = true;

    try {
      const usuarioActualizado = estabaActivo
        ? await window.Api.post(`/usuarios/${id}/desactivar`)
        : await window.Api.patch(`/usuarios/${id}`, { activo: true });
      usuariosCache[id] = usuarioActualizado; // mantiene la cache consistente para el modal de edición
    } catch (error) {
      pintarBotonEstado(boton, estabaActivo); // revertir — la API no confirmó el cambio
      alert(error.message); // acción secundaria de una fila — no amerita su propio modal
    } finally {
      boton.disabled = false;
    }
  }

  // ---------------------------------------------------------------
  // Modal de alta/edición — a diferencia del panel .detail que usaba antes,
  // este NUNCA se cierra tocando el fondo: solo con la X, Cancelar, o
  // completando el formulario (feedback explícito del usuario).
  //
  // Es el MISMO modal para crear y editar. Email y Contraseña solo se
  // piden al crear — el backend (UsuarioEdicion) no los acepta por
  // PATCH, así que en modo edición Email queda visible pero deshabilitado
  // (para que quede claro a quién se está editando) y Contraseña se
  // oculta directamente.
  // ---------------------------------------------------------------
  function abrirModal() {
    usuarioEditandoId = null;
    modalTitulo.textContent = 'Nuevo usuario';
    modalSub.textContent = 'Se crea con la contraseña que definas acá — se la comunicás vos.';
    campoEmail.disabled = false;
    campoEmail.required = true;
    bloquePassword.style.display = '';
    campoPassword.required = true;
    botonGuardar.textContent = 'Crear usuario';
    formulario.reset();
    modalAlta.classList.add('open');
    campoNombre.focus();
  }

  function abrirModalEdicion(id) {
    const usuario = usuariosCache[id];
    if (!usuario) return;
    usuarioEditandoId = id;
    modalTitulo.textContent = 'Editar usuario';
    modalSub.textContent = 'El email y la contraseña no se editan desde acá.';
    campoNombre.value = usuario.nombre;
    campoEmail.value = usuario.email;
    campoEmail.disabled = true;
    campoEmail.required = false;
    bloquePassword.style.display = 'none';
    campoPassword.required = false;
    campoRol.value = usuario.rol;
    campoTelefono.value = usuario.telefono || '';
    botonGuardar.textContent = 'Guardar cambios';
    mensajeError.style.display = 'none';
    modalAlta.classList.add('open');
    campoNombre.focus();
  }

  function cerrarModal() {
    modalAlta.classList.remove('open');
    formulario.reset();
    mensajeError.style.display = 'none';
    campoEmail.disabled = false;
    usuarioEditandoId = null;
    // el toggle de contraseña no se resetea solo con formulario.reset()
    const botonToggle = modalAlta.querySelector('.campo-password-toggle');
    campoPassword.type = 'password';
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

    try {
      if (usuarioEditandoId) {
        botonGuardar.textContent = 'Guardando…';
        const usuarioActualizado = await window.Api.patch(`/usuarios/${usuarioEditandoId}`, {
          nombre: campoNombre.value.trim(),
          rol: campoRol.value,
          telefono: campoTelefono.value.trim() || null,
        });
        reemplazarFila(usuarioActualizado);
      } else {
        botonGuardar.textContent = 'Creando…';
        await window.Api.post('/usuarios', {
          nombre: campoNombre.value.trim(),
          email: campoEmail.value.trim(),
          password: campoPassword.value,
          rol: campoRol.value,
          telefono: campoTelefono.value.trim() || null,
        });
        await cargarListado();
      }
      cerrarModal();
    } catch (error) {
      mensajeErrorTexto.textContent = error.message;
      mensajeError.style.display = 'flex';
    } finally {
      botonGuardar.disabled = false;
      botonGuardar.textContent = usuarioEditandoId ? 'Guardar cambios' : 'Crear usuario';
    }
  });

  await cargarListado();
});

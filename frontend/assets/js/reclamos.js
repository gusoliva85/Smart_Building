// reclamos.js — lógica de reclamos.html.
//
// Fase 3, "creación de reclamo": por ahora esta pantalla es solo la de
// Propietario/Inquilino, para cargar uno nuevo. Administrador/Encargado
// suman su propia vista de gestión en la próxima tarea de esta fase
// ("seguimiento de reclamos") — mismo archivo, mismo criterio que
// financiero.js (un archivo por dominio, no uno por rol).
document.addEventListener('DOMContentLoaded', async () => {
  const usuario = await window.Layout.montar('reclamos.html');
  if (!usuario) return; // montarLayout ya mandó al login si hacía falta

  const vistaNoAutorizado = document.getElementById('vista-no-autorizado');
  const vistaNuevoReclamo = document.getElementById('vista-nuevo-reclamo');

  if (usuario.rol === 'propietario' || usuario.rol === 'inquilino') {
    vistaNuevoReclamo.style.display = 'block';
    await iniciarFormularioNuevoReclamo();
  } else {
    vistaNoAutorizado.style.display = 'block';
  }

  // ---------------------------------------------------------------
  // Nuevo reclamo (Propietario/Inquilino)
  // ---------------------------------------------------------------
  async function iniciarFormularioNuevoReclamo() {
    const avisoSinUnidades = document.getElementById('aviso-sin-unidades');
    const form = document.getElementById('form-reclamo');
    const campoUnidadWrap = document.getElementById('campo-unidad-propia-wrap');
    const campoUnidad = document.getElementById('campo-unidad-propia');
    const objetivoUnidadTitulo = document.getElementById('objetivo-unidad-titulo');
    const objetivoGrid = document.getElementById('objetivo-grid');
    const campoEspacioWrap = document.getElementById('campo-espacio-comun-wrap');
    const campoEspacio = document.getElementById('campo-espacio-comun');
    const prioridadGrid = document.getElementById('prioridad-grid');
    const fotosLista = document.getElementById('fotos-lista');
    const botonAgregarFoto = document.getElementById('boton-agregar-foto');
    const mensajeExito = document.getElementById('mensaje-exito-reclamo');
    const mensajeExitoTexto = document.getElementById('mensaje-exito-reclamo-texto');
    const mensajeError = document.getElementById('mensaje-error-reclamo');
    const mensajeErrorTexto = document.getElementById('mensaje-error-reclamo-texto');

    let departamentos;
    try {
      departamentos = await window.Api.get('/mis-departamentos');
    } catch (error) {
      mensajeError.style.display = 'flex';
      mensajeErrorTexto.textContent = error.message;
      return;
    }

    if (departamentos.length === 0) {
      avisoSinUnidades.style.display = 'block';
      return;
    }

    // Contexto actual: de qué edificio (y, si el objetivo es "mi unidad",
    // de qué departamento puntual) es el reclamo — con una sola unidad
    // propia se resuelve solo, mismo criterio que la carga de un Pago
    // (Fase 2): el selector ni se muestra.
    let contexto = departamentos[0];
    if (departamentos.length > 1) {
      campoUnidadWrap.style.display = 'flex';
      campoUnidad.innerHTML = departamentos
        .map((d, i) => `<option value="${i}">${d.identificador} · ${d.edificio_nombre}</option>`)
        .join('');
      campoUnidad.addEventListener('change', () => {
        contexto = departamentos[Number(campoUnidad.value)];
        actualizarTituloUnidad();
        if (objetivoActual === 'espacio') cargarEspaciosComunes();
      });
    }

    function actualizarTituloUnidad() {
      objetivoUnidadTitulo.textContent = departamentos.length > 1 ? `Mi unidad (${contexto.identificador})` : 'Mi unidad';
    }
    actualizarTituloUnidad();

    form.style.display = 'block';
    window.Formularios.habilitarEnterComoTab(form);

    // ------------------------- Objetivo -------------------------
    let objetivoActual = null;
    const espaciosCache = {}; // edificio_id -> lista de espacios comunes, para no repedir al ida y vuelta

    async function cargarEspaciosComunes() {
      campoEspacio.disabled = true;
      campoEspacio.innerHTML = `<option>${window.Cargando.html()}</option>`;
      try {
        if (!espaciosCache[contexto.edificio_id]) {
          espaciosCache[contexto.edificio_id] = await window.Api.get(`/edificios/${contexto.edificio_id}/espacios-comunes`);
        }
        const espacios = espaciosCache[contexto.edificio_id];
        campoEspacio.disabled = false;
        campoEspacio.innerHTML = espacios.length
          ? espacios.map((e) => `<option value="${e.id}">${e.nombre}</option>`).join('')
          : '<option value="" disabled selected>No hay espacios comunes cargados en este edificio</option>';
      } catch (error) {
        campoEspacio.innerHTML = `<option value="" disabled selected>${error.message}</option>`;
      }
    }

    objetivoGrid.querySelectorAll('.opcion-card').forEach((boton) => {
      boton.addEventListener('click', () => {
        objetivoActual = boton.dataset.objetivo;
        objetivoGrid.querySelectorAll('.opcion-card').forEach((b) => b.classList.toggle('selected', b === boton));
        campoEspacioWrap.style.display = objetivoActual === 'espacio' ? 'block' : 'none';
        if (objetivoActual === 'espacio' && !espaciosCache[contexto.edificio_id]) cargarEspaciosComunes();
      });
    });

    // ------------------------- Prioridad -------------------------
    let prioridadActual = null;
    prioridadGrid.querySelectorAll('.opcion-card').forEach((boton) => {
      boton.addEventListener('click', () => {
        prioridadActual = boton.dataset.prioridad;
        prioridadGrid.querySelectorAll('.opcion-card').forEach((b) => b.classList.toggle('selected', b === boton));
      });
    });

    // ------------------------- Fotos (URLs) -------------------------
    function agregarFilaFoto() {
      const fila = document.createElement('div');
      fila.style.cssText = 'display:flex; gap:8px; margin-bottom:8px;';
      fila.innerHTML = `
        <input type="text" class="campo-foto-url" placeholder="Link a la foto" style="flex:1; min-width:0; box-sizing:border-box; font:inherit; padding:10px 13px; border-radius:var(--r-sm); background:var(--glass-content-bg); border:1px solid var(--line); color:var(--ink);">
        <button type="button" class="icon-btn icon-btn-sm boton-quitar-foto" aria-label="Quitar foto">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </button>`;
      fila.querySelector('.boton-quitar-foto').addEventListener('click', () => fila.remove());
      fotosLista.appendChild(fila);
    }
    botonAgregarFoto.addEventListener('click', agregarFilaFoto);

    // ------------------------- Envío -------------------------
    form.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      mensajeError.style.display = 'none';
      mensajeExito.style.display = 'none';

      if (!objetivoActual) {
        mensajeError.style.display = 'flex';
        mensajeErrorTexto.textContent = 'Elegí dónde es el problema.';
        return;
      }
      if (!prioridadActual) {
        mensajeError.style.display = 'flex';
        mensajeErrorTexto.textContent = 'Elegí una prioridad.';
        return;
      }

      const payload = {
        descripcion: document.getElementById('campo-reclamo-descripcion').value.trim(),
        prioridad: prioridadActual,
        fotos: Array.from(fotosLista.querySelectorAll('.campo-foto-url'))
          .map((input) => input.value.trim())
          .filter(Boolean),
      };
      if (objetivoActual === 'unidad') payload.departamento_id = contexto.departamento_id;
      if (objetivoActual === 'espacio') {
        if (!campoEspacio.value) {
          mensajeError.style.display = 'flex';
          mensajeErrorTexto.textContent = 'Elegí un espacio común.';
          return;
        }
        payload.espacio_comun_id = Number(campoEspacio.value);
      }

      const boton = document.getElementById('boton-reclamo-guardar');
      boton.disabled = true;
      try {
        await window.Api.post(`/edificios/${contexto.edificio_id}/reclamos`, payload);
        mensajeExito.style.display = 'flex';
        mensajeExitoTexto.textContent = 'Reclamo enviado — el administrador o encargado del edificio lo va a revisar.';
        form.reset();
        fotosLista.innerHTML = '';
        objetivoActual = null;
        prioridadActual = null;
        objetivoGrid.querySelectorAll('.opcion-card').forEach((b) => b.classList.remove('selected'));
        prioridadGrid.querySelectorAll('.opcion-card').forEach((b) => b.classList.remove('selected'));
        campoEspacioWrap.style.display = 'none';
      } catch (error) {
        mensajeError.style.display = 'flex';
        mensajeErrorTexto.textContent = error.message;
      } finally {
        boton.disabled = false;
      }
    });
  }
});

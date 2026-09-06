// financiero.js — lógica de financiero.html: listado de edificios y,
// dentro de cada uno, la pestaña "Gastos" (primera del módulo — el resto
// de las pestañas se suman en sus propias tareas del Roadmap).
document.addEventListener('DOMContentLoaded', async () => {
  const usuario = await window.Layout.montar('financiero.html');
  if (!usuario) return; // montarLayout ya mandó al login si hacía falta

  const vistaNoAutorizado = document.getElementById('vista-no-autorizado');
  const vistaListado = document.getElementById('vista-listado');
  const vistaDetalle = document.getElementById('vista-detalle');

  if (usuario.rol !== 'admin_general' && usuario.rol !== 'admin_consorcio') {
    vistaNoAutorizado.style.display = 'block';
    return;
  }

  function mostrarSolo(vista) {
    [vistaListado, vistaDetalle].forEach((v) => { v.style.display = 'none'; });
    vista.style.display = 'block';
  }

  // "YYYY-MM-DD" -> "DD/MM/YYYY" sin pasar por Date() — new Date('2026-08-05')
  // se interpreta como medianoche UTC, y toLocaleDateString con la zona
  // horaria de Argentina (UTC-3) la muestra un día antes. Reordenar el
  // texto a mano evita ese corrimiento por completo.
  function formatearFecha(fechaISO) {
    const [anio, mes, dia] = fechaISO.split('-');
    return `${dia}/${mes}/${anio}`;
  }

  // Declaradas ACÁ ARRIBA a propósito (no más abajo, junto a iniciarDetalle):
  // el ruteo de la línea siguiente ya puede llamar a iniciarDetalle antes de
  // que la ejecución llegue a esa parte del archivo — con "let" declarado
  // más abajo tira "Cannot access 'edificioId' before initialization"
  // (temporal dead zone), el mismo bug ya visto en edificios.js (Fase 1).
  let edificioId;
  let gastosCache = []; // último listado sin filtrar, para poblar el select de años

  const idParam = new URLSearchParams(location.search).get('id');
  if (idParam) {
    mostrarSolo(vistaDetalle);
    await iniciarDetalle(Number(idParam));
  } else {
    mostrarSolo(vistaListado);
    await cargarListadoEdificios();
  }

  // ---------------------------------------------------------------
  // Listado de edificios — mismo patrón que edificios.html.
  // ---------------------------------------------------------------
  async function cargarListadoEdificios() {
    const lista = document.getElementById('lista-edificios');
    lista.innerHTML = `<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">${window.Cargando.html()}</p>`;
    let edificios;
    try {
      edificios = await window.Api.get('/edificios');
    } catch (error) {
      lista.innerHTML = `<p style="font-size:12.5px;color:var(--crit);padding:10px 0;">${error.message}</p>`;
      return;
    }

    if (edificios.length === 0) {
      lista.innerHTML = '<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">Todavía no hay edificios cargados.</p>';
      return;
    }

    lista.innerHTML = edificios
      .map((e) => `
        <a href="financiero.html?id=${e.id}" class="detail-item content-glass fila-lista" style="text-decoration:none; color:inherit;">
          <div>
            <b style="font-size:13.5px;">${e.nombre}</b>
            <div style="font-size:11.5px;color:var(--ink-3);">${e.direccion}${e.cp ? ' · CP ' + e.cp : ''}</div>
          </div>
          <div class="fila-lista-acciones">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--ink-4);"><path d="M9 18l6-6-6-6"/></svg>
          </div>
        </a>`)
      .join('');
  }

  // ---------------------------------------------------------------
  // Detalle: pestaña Gastos
  // ---------------------------------------------------------------
  async function iniciarDetalle(id) {
    edificioId = id;
    document.getElementById('detalle-titulo').innerHTML = window.Cargando.html();

    let edificio;
    try {
      edificio = await window.Api.get(`/edificios/${id}`);
    } catch (error) {
      document.getElementById('detalle-titulo').textContent = 'No se pudo cargar el edificio';
      document.getElementById('detalle-subtitulo').textContent = error.message;
      return;
    }

    document.getElementById('detalle-titulo').textContent = edificio.nombre;
    document.getElementById('detalle-subtitulo').textContent =
      `${edificio.direccion}${edificio.cp ? ' · CP ' + edificio.cp : ''}`;

    document.getElementById('filtro-anio').addEventListener('change', cargarGastos);
    document.getElementById('filtro-mes').addEventListener('change', cargarGastos);

    await cargarGastos();
    configurarModalGasto();
  }

  async function cargarGastos() {
    const contenedor = document.getElementById('lista-gastos');
    contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">${window.Cargando.html()}</p>`;

    const anio = document.getElementById('filtro-anio').value;
    const mes = document.getElementById('filtro-mes').value;
    const parametros = new URLSearchParams();
    if (anio) parametros.set('anio', anio);
    if (mes) parametros.set('mes', mes);
    const query = parametros.toString() ? `?${parametros.toString()}` : '';

    let gastos;
    try {
      gastos = await window.Api.get(`/edificios/${edificioId}/gastos${query}`);
    } catch (error) {
      contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--crit);padding:10px 0;">${error.message}</p>`;
      return;
    }

    // El listado sin filtrar (primera carga) define qué años ofrecer en
    // el select — se hace una sola vez, no en cada filtrado.
    if (!anio && !mes) {
      gastosCache = gastos;
      poblarFiltroAnio(gastos);
    }

    renderResumen(gastos);
    renderListaGastos(gastos);
  }

  function poblarFiltroAnio(gastos) {
    const select = document.getElementById('filtro-anio');
    const anioSeleccionado = select.value;
    const anios = [...new Set(gastos.map((g) => g.fecha.slice(0, 4)))].sort((a, b) => b - a);
    select.innerHTML = '<option value="">Todos los años</option>' +
      anios.map((a) => `<option value="${a}">${a}</option>`).join('');
    select.value = anioSeleccionado;
  }

  function renderResumen(gastos) {
    const total = gastos.reduce((suma, g) => suma + g.monto, 0);
    const resumen = document.getElementById('resumen-gastos');
    resumen.textContent = gastos.length
      ? `${gastos.length} gasto${gastos.length === 1 ? '' : 's'} · ${window.Moneda.formatear(total)} en total`
      : 'Sin gastos cargados para este filtro.';
  }

  function renderListaGastos(gastos) {
    const contenedor = document.getElementById('lista-gastos');
    if (gastos.length === 0) {
      contenedor.innerHTML = '<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">Todavía no hay gastos cargados — usá "+ Nuevo gasto".</p>';
      return;
    }
    contenedor.innerHTML = gastos
      .map((g) => `
        <div class="detail-item content-glass fila-lista">
          <div>
            <b style="font-size:13.5px;">${g.rubro}</b>
            <div style="font-size:11.5px;color:var(--ink-3);">${formatearFecha(g.fecha)}${g.descripcion ? ' · ' + g.descripcion : ''}</div>
          </div>
          <div class="fila-lista-acciones">
            <span style="font-size:13.5px; font-weight:700; font-family:Outfit, sans-serif;">${window.Moneda.formatear(g.monto)}</span>
          </div>
        </div>`)
      .join('');
  }

  // ---------------------------------------------------------------
  // Modal: nuevo gasto
  // ---------------------------------------------------------------
  function configurarModalGasto() {
    const modal = document.getElementById('modal-gasto');
    const form = document.getElementById('form-gasto');
    const mensajeError = document.getElementById('mensaje-error-gasto');
    const mensajeErrorTexto = document.getElementById('mensaje-error-gasto-texto');

    window.Formularios.habilitarEnterComoTab(form);

    function abrir() {
      form.reset();
      document.getElementById('campo-gasto-fecha').value = new Date().toISOString().slice(0, 10);
      mensajeError.style.display = 'none';
      modal.classList.add('open');
    }
    function cerrar() {
      modal.classList.remove('open');
    }

    document.getElementById('boton-nuevo-gasto').addEventListener('click', abrir);
    document.getElementById('modal-gasto-cerrar').addEventListener('click', cerrar);
    document.getElementById('boton-gasto-cancelar').addEventListener('click', cerrar);

    form.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      mensajeError.style.display = 'none';
      try {
        await window.Api.post(`/edificios/${edificioId}/gastos`, {
          rubro: document.getElementById('campo-gasto-rubro').value.trim(),
          monto: Number(document.getElementById('campo-gasto-monto').value),
          fecha: document.getElementById('campo-gasto-fecha').value,
          descripcion: document.getElementById('campo-gasto-descripcion').value.trim() || null,
        });
        cerrar();
        // Reset de filtros: un gasto recién cargado tiene que verse sin
        // que el usuario tenga que adivinar que el filtro lo está tapando.
        document.getElementById('filtro-anio').value = '';
        document.getElementById('filtro-mes').value = '';
        await cargarGastos();
      } catch (error) {
        mensajeErrorTexto.textContent = error.message;
        mensajeError.style.display = 'flex';
      }
    });
  }
});

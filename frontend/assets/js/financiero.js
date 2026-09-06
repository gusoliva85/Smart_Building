// financiero.js — lógica de financiero.html.
//
// Dos audiencias en el mismo archivo (Documento Técnico 4.1: un archivo
// por dominio, no uno por rol): Administrador General/de Consorcio ve el
// listado de edificios y, dentro de cada uno, las pestañas de gestión
// (Gastos, Expensas — el resto se suma en sus propias tareas del
// Roadmap). Propietario/Inquilino ve directo "Mi cuenta": sus propias
// unidades y el estado de sus expensas (GET /api/mis-departamentos, sin
// elegir edificio ni navegar nada ajeno) — cargar un pago todavía no,
// esa es la próxima tarea ("pestaña Pagos").
document.addEventListener('DOMContentLoaded', async () => {
  const usuario = await window.Layout.montar('financiero.html');
  if (!usuario) return; // montarLayout ya mandó al login si hacía falta

  const vistaNoAutorizado = document.getElementById('vista-no-autorizado');
  const vistaListado = document.getElementById('vista-listado');
  const vistaDetalle = document.getElementById('vista-detalle');
  const vistaMiCuenta = document.getElementById('vista-mi-cuenta');
  const TODAS_LAS_VISTAS = [vistaListado, vistaDetalle, vistaMiCuenta];

  function mostrarSolo(vista) {
    TODAS_LAS_VISTAS.forEach((v) => { v.style.display = 'none'; });
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

  const NOMBRE_MES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

  // Declaradas ACÁ ARRIBA a propósito (no más abajo, junto a iniciarDetalle):
  // el ruteo de más abajo ya puede llamar a iniciarDetalle antes de que la
  // ejecución llegue a esa parte del archivo — con "let" declarado más
  // abajo tira "Cannot access 'edificioId' before initialization" (temporal
  // dead zone), el mismo bug ya visto en edificios.js (Fase 1).
  let edificioId;
  let gastosCache = []; // último listado sin filtrar, para poblar el select de años

  // ---------------------------------------------------------------
  // Ruteo por rol
  // ---------------------------------------------------------------
  if (usuario.rol === 'propietario' || usuario.rol === 'inquilino') {
    mostrarSolo(vistaMiCuenta);
    await cargarMiCuenta();
  } else if (usuario.rol === 'admin_general' || usuario.rol === 'admin_consorcio') {
    const idParam = new URLSearchParams(location.search).get('id');
    if (idParam) {
      mostrarSolo(vistaDetalle);
      await iniciarDetalle(Number(idParam));
    } else {
      mostrarSolo(vistaListado);
      await cargarListadoEdificios();
    }
  } else {
    vistaNoAutorizado.style.display = 'block';
  }

  // ---------------------------------------------------------------
  // Mi cuenta (Propietario/Inquilino)
  // ---------------------------------------------------------------
  async function cargarMiCuenta() {
    const contenedor = document.getElementById('lista-mis-departamentos');
    contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">${window.Cargando.html()}</p>`;

    let departamentos;
    try {
      departamentos = await window.Api.get('/mis-departamentos');
    } catch (error) {
      contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--crit);padding:10px 0;">${error.message}</p>`;
      return;
    }

    if (departamentos.length === 0) {
      contenedor.innerHTML = '<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">Todavía no tenés ninguna unidad asignada.</p>';
      return;
    }

    contenedor.innerHTML = departamentos.map((depto) => `
      <div class="detail-item content-glass" style="margin-bottom:12px;">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
          <b style="font-size:13.5px;">${depto.identificador} · ${depto.edificio_nombre}</b>
        </div>
        ${depto.expensas.length === 0
          ? '<p style="font-size:12px;color:var(--ink-3);margin:0;">Todavía no tenés expensas generadas.</p>'
          : depto.expensas.map((exp) => `
              <div class="fila-lista" style="padding:8px 0; border-top:1px solid var(--line-2);">
                <div>
                  <b style="font-size:13px;">${NOMBRE_MES[exp.mes]} ${exp.anio}</b>
                  <div style="font-size:11px;color:var(--ink-3);">${window.Moneda.formatear(exp.monto)} total</div>
                </div>
                <div class="fila-lista-acciones">
                  ${exp.saldo <= 0.01
                    ? '<span class="rol-badge">Al día</span>'
                    : `<span style="font-size:13px; font-weight:700; color:var(--crit); font-family:Outfit, sans-serif;">${window.Moneda.formatear(exp.saldo)}</span>`}
                </div>
              </div>`).join('')}
      </div>`).join('');
  }

  // ---------------------------------------------------------------
  // Listado de edificios (Administrador) — mismo patrón que edificios.html.
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
  // Detalle de un edificio: pestañas Gastos / Expensas
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

    configurarViewSwitchDetalle();
    await cargarGastos();
    configurarModalGasto();
    configurarModalGenerarExpensa();
    configurarModalDetalleExpensa();
  }

  function configurarViewSwitchDetalle() {
    const switchEl = document.getElementById('detalle-view-switch');
    const panelGastos = document.getElementById('panel-gastos');
    const panelExpensas = document.getElementById('panel-expensas');
    let expensasCargadas = false;

    switchEl.querySelectorAll('button').forEach((boton) => {
      boton.addEventListener('click', async () => {
        switchEl.querySelectorAll('button').forEach((b) => b.classList.remove('active'));
        boton.classList.add('active');
        const esGastos = boton.dataset.view === 'gastos';
        panelGastos.style.display = esGastos ? 'block' : 'none';
        panelExpensas.style.display = esGastos ? 'none' : 'block';
        if (!esGastos && !expensasCargadas) {
          expensasCargadas = true;
          await cargarExpensas();
        }
      });
    });
  }

  // --------------------------- Pestaña Gastos ---------------------------
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

  // -------------------------- Pestaña Expensas --------------------------
  async function cargarExpensas() {
    const contenedor = document.getElementById('lista-expensas');
    contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">${window.Cargando.html()}</p>`;

    let expensas;
    try {
      expensas = await window.Api.get(`/edificios/${edificioId}/expensas`);
    } catch (error) {
      contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--crit);padding:10px 0;">${error.message}</p>`;
      return;
    }

    if (expensas.length === 0) {
      contenedor.innerHTML = '<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">Todavía no se generó ninguna expensa — usá "+ Generar expensa".</p>';
      return;
    }

    contenedor.innerHTML = expensas
      .map((exp) => `
        <button type="button" class="detail-item content-glass fila-lista boton-ver-expensa" data-id="${exp.id}" style="width:100%; text-align:left; border:0; cursor:pointer; font:inherit; color:inherit;">
          <div>
            <b style="font-size:13.5px;">${NOMBRE_MES[exp.mes]} ${exp.anio}</b>
            <div style="font-size:11.5px;color:var(--ink-3);">${exp.detalles.length} rubro${exp.detalles.length === 1 ? '' : 's'} · ${exp.por_departamento.length} unidad${exp.por_departamento.length === 1 ? '' : 'es'}</div>
          </div>
          <div class="fila-lista-acciones">
            <span style="font-size:13.5px; font-weight:700; font-family:Outfit, sans-serif;">${window.Moneda.formatear(exp.total)}</span>
          </div>
        </button>`)
      .join('');

    contenedor.querySelectorAll('.boton-ver-expensa').forEach((boton) => {
      boton.addEventListener('click', () => mostrarDetalleExpensa(Number(boton.dataset.id)));
    });
  }

  function configurarModalGenerarExpensa() {
    const modal = document.getElementById('modal-generar-expensa');
    const form = document.getElementById('form-generar-expensa');
    const mensajeError = document.getElementById('mensaje-error-generar-expensa');
    const mensajeErrorTexto = document.getElementById('mensaje-error-generar-expensa-texto');

    window.Formularios.habilitarEnterComoTab(form);

    function abrir() {
      form.reset();
      const hoy = new Date();
      document.getElementById('campo-expensa-anio').value = hoy.getFullYear();
      document.getElementById('campo-expensa-mes').value = hoy.getMonth() + 1;
      mensajeError.style.display = 'none';
      modal.classList.add('open');
    }
    function cerrar() {
      modal.classList.remove('open');
    }

    document.getElementById('boton-generar-expensa').addEventListener('click', abrir);
    document.getElementById('modal-generar-expensa-cerrar').addEventListener('click', cerrar);
    document.getElementById('boton-generar-expensa-cancelar').addEventListener('click', cerrar);

    form.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      mensajeError.style.display = 'none';
      try {
        await window.Api.post(`/edificios/${edificioId}/expensas`, {
          anio: Number(document.getElementById('campo-expensa-anio').value),
          mes: Number(document.getElementById('campo-expensa-mes').value),
        });
        cerrar();
        await cargarExpensas();
      } catch (error) {
        mensajeErrorTexto.textContent = error.message;
        mensajeError.style.display = 'flex';
      }
    });
  }

  function configurarModalDetalleExpensa() {
    document.getElementById('modal-detalle-expensa-cerrar').addEventListener('click', () => {
      document.getElementById('modal-detalle-expensa').classList.remove('open');
    });
  }

  async function mostrarDetalleExpensa(expensaId) {
    const modal = document.getElementById('modal-detalle-expensa');
    document.getElementById('detalle-expensa-titulo').textContent = 'Cargando...';
    modal.classList.add('open');

    let expensa;
    try {
      expensa = await window.Api.get(`/edificios/${edificioId}/expensas/${expensaId}`);
    } catch (error) {
      document.getElementById('detalle-expensa-titulo').textContent = 'No se pudo cargar';
      document.getElementById('detalle-expensa-total').textContent = error.message;
      return;
    }

    document.getElementById('detalle-expensa-titulo').textContent = `${NOMBRE_MES[expensa.mes]} ${expensa.anio}`;
    document.getElementById('detalle-expensa-total').textContent = `Total: ${window.Moneda.formatear(expensa.total)}`;

    document.getElementById('detalle-expensa-rubros').innerHTML = expensa.detalles
      .map((d) => `
        <div style="display:flex; align-items:center; justify-content:space-between; padding:6px 0;">
          <span style="font-size:12.5px;">${d.rubro}</span>
          <span style="font-size:12.5px; font-weight:700; font-family:Outfit, sans-serif;">${window.Moneda.formatear(d.monto)}</span>
        </div>`)
      .join('');

    document.getElementById('detalle-expensa-departamentos').innerHTML = expensa.por_departamento
      .map((d) => `
        <div style="display:flex; align-items:center; justify-content:space-between; padding:6px 0;">
          <span style="font-size:12.5px;">${d.identificador}</span>
          <span style="font-size:12.5px; font-weight:700; font-family:Outfit, sans-serif;">${window.Moneda.formatear(d.monto)}</span>
        </div>`)
      .join('');
  }
});

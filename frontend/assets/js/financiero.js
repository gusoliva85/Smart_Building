// financiero.js — lógica de financiero.html.
//
// Dos audiencias en el mismo archivo (Documento Técnico 4.1: un archivo
// por dominio, no uno por rol): Administrador General/de Consorcio ve el
// listado de edificios y, dentro de cada uno, las pestañas de gestión
// (Gastos, Expensas, Pagos — el resto se suma en sus propias tareas del
// Roadmap). Propietario/Inquilino ve directo "Mi cuenta": sus propias
// unidades y el estado de sus expensas (GET /api/mis-departamentos, sin
// elegir edificio ni navegar nada ajeno), y desde ahí puede cargar su
// propio pago contra una expensa con saldo (Tarea 15, "pestaña Pagos") —
// nace `pendiente` hasta que un Administrador lo concilia en su propia
// pestaña Pagos.
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
  let deudoresCache = []; // último listado de deudores, para abrir el detalle sin volver a pedirlo
  let fondosCache = [];
  let fondoActualId = null; // fondo que tiene abierto su modal de detalle/movimientos
  let cajaActual = null; // null = todavía no configurada en este edificio
  let usuariosCache = null; // se resuelve una sola vez (null = todavía no se intentó pedir)
  let presupuestosCache = [];
  let presupuestoAprobarId = null; // presupuesto que tiene abierto su modal de aprobación

  // ---------------------------------------------------------------
  // Ruteo por rol
  // ---------------------------------------------------------------
  if (usuario.rol === 'propietario' || usuario.rol === 'inquilino') {
    mostrarSolo(vistaMiCuenta);
    await cargarMiCuenta();
    configurarModalPago();
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
              <div style="padding:8px 0; border-top:1px solid var(--line-2);">
                <div class="fila-lista">
                  <div>
                    <b style="font-size:13px;">${NOMBRE_MES[exp.mes]} ${exp.anio}</b>
                    <div style="font-size:11px;color:var(--ink-3);">${window.Moneda.formatear(exp.monto)} total</div>
                  </div>
                  <div class="fila-lista-acciones">
                    ${exp.saldo <= 0.01
                      ? '<span class="rol-badge">Al día</span>'
                      : `<span style="font-size:13px; font-weight:700; color:var(--crit); font-family:Outfit, sans-serif;">${window.Moneda.formatear(exp.saldo)}</span>
                         <button type="button" class="boton-chico boton-cargar-pago" data-departamento-id="${depto.departamento_id}" data-edificio-id="${depto.edificio_id}" data-expensa-id="${exp.expensa_id}" data-periodo="${NOMBRE_MES[exp.mes]} ${exp.anio}" data-saldo="${exp.saldo}">Pagar</button>`}
                  </div>
                </div>
                ${exp.pendiente_de_confirmacion > 0.01
                  ? `<p style="font-size:11px;color:var(--ink-3);margin:4px 0 0;">Cargaste ${window.Moneda.formatear(exp.pendiente_de_confirmacion)} — pendiente de confirmación del administrador.</p>`
                  : ''}
              </div>`).join('')}
      </div>`).join('');

    contenedor.querySelectorAll('.boton-cargar-pago').forEach((boton) => {
      boton.addEventListener('click', () => abrirModalPago(boton.dataset));
    });
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

    document.getElementById('filtro-estado-pago').addEventListener('change', cargarPagos);

    configurarViewSwitchDetalle();
    await cargarGastos();
    configurarModalGasto();
    configurarModalGenerarExpensa();
    configurarModalDetalleExpensa();
    configurarAccionesPago();
    configurarModalDetalleDeudor();
    configurarSubViewSwitchFondos();
    configurarModalFondo();
    configurarModalDetalleFondo();
    configurarModalCaja();
    configurarModalPresupuesto();
    configurarModalAprobarPresupuesto();
    configurarModalFactura();
  }

  function configurarViewSwitchDetalle() {
    const switchEl = document.getElementById('detalle-view-switch');
    const paneles = {
      gastos: document.getElementById('panel-gastos'),
      expensas: document.getElementById('panel-expensas'),
      pagos: document.getElementById('panel-pagos'),
      deudores: document.getElementById('panel-deudores'),
      fondos: document.getElementById('panel-fondos'),
    };
    const cargadores = { expensas: cargarExpensas, pagos: cargarPagos, deudores: cargarDeudores, fondos: cargarFondos };
    const yaCargado = { gastos: true, expensas: false, pagos: false, deudores: false, fondos: false };

    switchEl.querySelectorAll('button').forEach((boton) => {
      boton.addEventListener('click', async () => {
        switchEl.querySelectorAll('button').forEach((b) => b.classList.remove('active'));
        boton.classList.add('active');
        const vista = boton.dataset.view;
        Object.keys(paneles).forEach((v) => { paneles[v].style.display = v === vista ? 'block' : 'none'; });
        if (!yaCargado[vista]) {
          yaCargado[vista] = true;
          await cargadores[vista]();
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

  // --------------------------- Pestaña Pagos (Administrador) ---------------------------
  // Cola de conciliación (Documento General 6.2): un pago cargado por el
  // propio residente nace `pendiente` acá hasta que un Administrador lo
  // confirma o rechaza contra el movimiento bancario real.
  async function cargarPagos() {
    const contenedor = document.getElementById('lista-pagos');
    contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">${window.Cargando.html()}</p>`;
    document.getElementById('mensaje-error-conciliar').style.display = 'none';

    const estado = document.getElementById('filtro-estado-pago').value;
    const query = estado ? `?estado=${estado}` : '';

    let pagos;
    try {
      pagos = await window.Api.get(`/edificios/${edificioId}/pagos${query}`);
    } catch (error) {
      contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--crit);padding:10px 0;">${error.message}</p>`;
      return;
    }

    renderListaPagos(pagos);
  }

  function renderListaPagos(pagos) {
    const contenedor = document.getElementById('lista-pagos');
    document.getElementById('resumen-pagos').textContent = pagos.length
      ? `${pagos.length} pago${pagos.length === 1 ? '' : 's'}`
      : '';

    if (pagos.length === 0) {
      contenedor.innerHTML = '<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">No hay pagos para este filtro.</p>';
      return;
    }

    contenedor.innerHTML = pagos
      .map((p) => `
        <div class="detail-item content-glass fila-lista" style="margin-bottom:10px;">
          <div>
            <b style="font-size:13.5px;">${p.identificador} · ${NOMBRE_MES[p.mes]} ${p.anio}</b>
            <div style="font-size:11.5px;color:var(--ink-3);">${formatearFecha(p.fecha)} · ${p.medio_pago}${p.comprobante_url ? ` · <a href="${p.comprobante_url}" target="_blank" rel="noopener" style="color:inherit;">comprobante</a>` : ''}</div>
          </div>
          <div class="fila-lista-acciones">
            <span style="font-size:13.5px; font-weight:700; font-family:Outfit, sans-serif;">${window.Moneda.formatear(p.monto)}</span>
            ${p.estado === 'pendiente'
              ? `<button type="button" class="boton-chico boton-conciliar" data-id="${p.id}" data-estado="confirmado">Confirmar</button>
                 <button type="button" class="boton-chico boton-chico-critico boton-conciliar" data-id="${p.id}" data-estado="rechazado">Rechazar</button>`
              : p.estado === 'confirmado'
                ? '<span class="rol-badge">Confirmado</span>'
                : '<span style="font-size:12px; font-weight:700; color:var(--crit);">Rechazado</span>'}
          </div>
        </div>`)
      .join('');
  }

  function configurarAccionesPago() {
    document.getElementById('lista-pagos').addEventListener('click', async (evento) => {
      const boton = evento.target.closest('.boton-conciliar');
      if (!boton) return;
      const mensajeError = document.getElementById('mensaje-error-conciliar');
      mensajeError.style.display = 'none';
      document.querySelectorAll('.boton-conciliar').forEach((b) => { b.disabled = true; });
      try {
        await window.Api.patch(`/pagos/${boton.dataset.id}/estado`, { estado: boton.dataset.estado });
        await cargarPagos();
      } catch (error) {
        document.getElementById('mensaje-error-conciliar-texto').textContent = error.message;
        mensajeError.style.display = 'flex';
        document.querySelectorAll('.boton-conciliar').forEach((b) => { b.disabled = false; });
      }
    });
  }

  // --------------------- Modal "Cargar pago" (Propietario/Inquilino) ---------------------
  function configurarModalPago() {
    const modal = document.getElementById('modal-pago');
    const form = document.getElementById('form-pago');
    const mensajeError = document.getElementById('mensaje-error-pago');
    const mensajeErrorTexto = document.getElementById('mensaje-error-pago-texto');
    const campoMonto = document.getElementById('campo-pago-monto');
    const avisoParcial = document.getElementById('aviso-pago-parcial');

    window.Formularios.habilitarEnterComoTab(form);

    function actualizarAvisoParcial() {
      const saldo = Number(form.dataset.saldo);
      const monto = Number(campoMonto.value);
      if (monto > 0 && monto < saldo) {
        avisoParcial.textContent = `Es un pago parcial — te va a quedar un saldo de ${window.Moneda.formatear(saldo - monto)}.`;
        avisoParcial.style.display = 'block';
      } else {
        avisoParcial.style.display = 'none';
      }
    }
    campoMonto.addEventListener('input', actualizarAvisoParcial);

    function cerrar() {
      modal.classList.remove('open');
    }
    document.getElementById('modal-pago-cerrar').addEventListener('click', cerrar);
    document.getElementById('boton-pago-cancelar').addEventListener('click', cerrar);

    form.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      mensajeError.style.display = 'none';
      try {
        await window.Api.post('/pagos', {
          departamento_id: Number(form.dataset.departamentoId),
          expensa_id: Number(form.dataset.expensaId),
          monto: Number(campoMonto.value),
          fecha: document.getElementById('campo-pago-fecha').value,
          medio_pago: document.getElementById('campo-pago-medio').value.trim(),
          comprobante_url: document.getElementById('campo-pago-comprobante').value.trim() || null,
        });
        cerrar();
        await cargarMiCuenta();
      } catch (error) {
        mensajeErrorTexto.textContent = error.message;
        mensajeError.style.display = 'flex';
      }
    });
  }

  async function abrirModalPago(datos) {
    const modal = document.getElementById('modal-pago');
    const form = document.getElementById('form-pago');
    form.reset();
    document.getElementById('mensaje-error-pago').style.display = 'none';
    document.getElementById('aviso-pago-parcial').style.display = 'none';
    form.dataset.departamentoId = datos.departamentoId;
    form.dataset.expensaId = datos.expensaId;
    form.dataset.saldo = datos.saldo;
    document.getElementById('modal-pago-sub').textContent = `${datos.periodo} — saldo pendiente ${window.Moneda.formatear(Number(datos.saldo))}`;
    document.getElementById('campo-pago-monto').value = datos.saldo;
    document.getElementById('campo-pago-monto').max = datos.saldo;
    document.getElementById('campo-pago-fecha').value = new Date().toISOString().slice(0, 10);
    modal.classList.add('open');

    const contenedorMedioPago = document.getElementById('medio-pago-datos');
    contenedorMedioPago.innerHTML = `<p style="font-size:12px;color:var(--ink-3);margin:0;">${window.Cargando.html()}</p>`;
    try {
      const medioPago = await window.Api.get(`/edificios/${datos.edificioId}/medio-pago`);
      contenedorMedioPago.innerHTML = renderMedioPago(medioPago);
      configurarBotonesCopiar(contenedorMedioPago, medioPago);
    } catch (error) {
      contenedorMedioPago.innerHTML = `<p style="font-size:12px;color:var(--crit);margin:0;">${error.message}</p>`;
    }
  }

  function renderMedioPago(medioPago) {
    if (!medioPago.cbu && !medioPago.alias_cbu) {
      return '<p style="font-size:12px;color:var(--ink-3);margin:0;">El edificio todavía no cargó un CBU ni un alias — consultá directamente con la administración para transferir.</p>';
    }
    return `
      ${medioPago.cbu ? `
        <div class="dato-copiable">
          <div>
            <div class="dato-copiable-label">CBU</div>
            <div class="dato-copiable-valor">${medioPago.cbu}</div>
          </div>
          <button type="button" class="icon-btn icon-btn-sm" data-copiar="cbu" aria-label="Copiar CBU">${window.Copiar.ICONO_COPIAR}</button>
        </div>` : ''}
      ${medioPago.alias_cbu ? `
        <div class="dato-copiable">
          <div>
            <div class="dato-copiable-label">Alias</div>
            <div class="dato-copiable-valor">${medioPago.alias_cbu}</div>
          </div>
          <button type="button" class="icon-btn icon-btn-sm" data-copiar="alias" aria-label="Copiar alias">${window.Copiar.ICONO_COPIAR}</button>
        </div>` : ''}
      <p style="font-size:11px;color:var(--ink-3);margin:8px 0 0;">Transferí desde tu banco o billetera virtual y cargá el pago acá — nace pendiente hasta que la administración lo confirme.</p>`;
  }

  function configurarBotonesCopiar(contenedor, medioPago) {
    contenedor.querySelectorAll('[data-copiar]').forEach((boton) => {
      const valor = boton.dataset.copiar === 'cbu' ? medioPago.cbu : medioPago.alias_cbu;
      boton.addEventListener('click', () => window.Copiar.alPortapapeles(boton, valor));
    });
  }

  // --------------------------- Pestaña Deudores (Administrador) ---------------------------
  // Documento Técnico 5.2: vista calculada, nunca una tabla propia — el
  // backend ya la devuelve ordenada de más a menos atrasado. Solo lectura:
  // la única acción para saldar una deuda es conciliar el pago en la
  // pestaña Pagos, no algo que se haga desde acá.
  async function cargarDeudores() {
    const contenedor = document.getElementById('lista-deudores');
    contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">${window.Cargando.html()}</p>`;

    let deudores;
    try {
      deudores = await window.Api.get(`/edificios/${edificioId}/deudores`);
    } catch (error) {
      contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--crit);padding:10px 0;">${error.message}</p>`;
      return;
    }

    deudoresCache = deudores;
    renderListaDeudores(deudores);
  }

  function renderListaDeudores(deudores) {
    const contenedor = document.getElementById('lista-deudores');
    const resumen = document.getElementById('resumen-deudores');

    if (deudores.length === 0) {
      resumen.textContent = '';
      contenedor.innerHTML = '<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">Sin deudores — todas las expensas generadas están saldadas.</p>';
      return;
    }

    const deudaTotal = deudores.reduce((suma, d) => suma + d.deuda_total, 0);
    resumen.textContent = `${deudores.length} departamento${deudores.length === 1 ? '' : 's'} con deuda · ${window.Moneda.formatear(deudaTotal)} en total`;

    contenedor.innerHTML = deudores
      .map((d) => `
        <button type="button" class="detail-item content-glass fila-lista boton-ver-deudor" data-id="${d.departamento_id}" style="width:100%; text-align:left; border:0; cursor:pointer; font:inherit; color:inherit;">
          <div>
            <b style="font-size:13.5px;">${d.identificador}</b>
            <div style="font-size:11.5px;color:var(--ink-3);">${d.meses_atraso} mes${d.meses_atraso === 1 ? '' : 'es'} de atraso · ${d.expensas_impagas.length} expensa${d.expensas_impagas.length === 1 ? '' : 's'} impaga${d.expensas_impagas.length === 1 ? '' : 's'}</div>
          </div>
          <div class="fila-lista-acciones">
            <span style="font-size:13.5px; font-weight:700; color:var(--crit); font-family:Outfit, sans-serif;">${window.Moneda.formatear(d.deuda_total)}</span>
          </div>
        </button>`)
      .join('');

    contenedor.querySelectorAll('.boton-ver-deudor').forEach((boton) => {
      boton.addEventListener('click', () => mostrarDetalleDeudor(Number(boton.dataset.id)));
    });
  }

  function configurarModalDetalleDeudor() {
    document.getElementById('modal-detalle-deudor-cerrar').addEventListener('click', () => {
      document.getElementById('modal-detalle-deudor').classList.remove('open');
    });
  }

  function mostrarDetalleDeudor(departamentoId) {
    const deudor = deudoresCache.find((d) => d.departamento_id === departamentoId);
    if (!deudor) return;

    document.getElementById('detalle-deudor-titulo').textContent = deudor.identificador;
    document.getElementById('detalle-deudor-resumen').textContent =
      `${window.Moneda.formatear(deudor.deuda_total)} de deuda · ${deudor.meses_atraso} mes${deudor.meses_atraso === 1 ? '' : 'es'} de atraso`;

    document.getElementById('detalle-deudor-expensas').innerHTML = deudor.expensas_impagas
      .map((e) => `
        <div style="display:flex; align-items:center; justify-content:space-between; padding:6px 0;">
          <span style="font-size:12.5px;">${NOMBRE_MES[e.mes]} ${e.anio}</span>
          <span style="font-size:12.5px; font-weight:700; color:var(--crit); font-family:Outfit, sans-serif;">${window.Moneda.formatear(e.saldo)}</span>
        </div>`)
      .join('');

    document.getElementById('modal-detalle-deudor').classList.add('open');
  }

  // --------------------------- Pestaña Fondos (Administrador) ---------------------------
  // Fondos, Caja chica, Presupuestos y Facturas comparten una sub-navegación
  // propia (`#fondos-view-switch`) dentro de la misma pestaña principal —
  // son registros de gestión secundarios, no el flujo Gastos→Expensas→
  // Pagos→Deudores.
  function configurarSubViewSwitchFondos() {
    const switchEl = document.getElementById('fondos-view-switch');
    const paneles = {
      fondos: document.getElementById('subpanel-fondos'),
      caja: document.getElementById('subpanel-caja'),
      presupuestos: document.getElementById('subpanel-presupuestos'),
      facturas: document.getElementById('subpanel-facturas'),
    };
    const cargadores = { caja: cargarCaja, presupuestos: cargarPresupuestos, facturas: cargarFacturas };
    const yaCargado = { fondos: true, caja: false, presupuestos: false, facturas: false };

    switchEl.querySelectorAll('button').forEach((boton) => {
      boton.addEventListener('click', async () => {
        switchEl.querySelectorAll('button').forEach((b) => b.classList.remove('active'));
        boton.classList.add('active');
        const vista = boton.dataset.subview;
        Object.keys(paneles).forEach((v) => { paneles[v].style.display = v === vista ? 'block' : 'none'; });
        if (!yaCargado[vista]) {
          yaCargado[vista] = true;
          await cargadores[vista]();
        }
      });
    });
  }

  // Movimientos de Fondo y de Caja comparten la misma forma (tipo/monto/
  // fecha/descripción) — un solo render para los dos. Sin color de
  // ingreso/egreso a propósito: el signo (+/−) ya lo dice, y --ok/--crit
  // quedan reservados para el semáforo real del edificio (mismo criterio
  // que "Al día" en Mi cuenta, Tarea 14).
  function renderMovimientos(movimientos) {
    if (movimientos.length === 0) {
      return '<p style="font-size:12px;color:var(--ink-3);margin:0;">Todavía no hay movimientos cargados.</p>';
    }
    return movimientos
      .map((m) => `
        <div style="display:flex; align-items:center; justify-content:space-between; padding:6px 0;">
          <span style="font-size:12.5px;">${formatearFecha(m.fecha)}${m.descripcion ? ' · ' + m.descripcion : ''}</span>
          <span style="font-size:12.5px; font-weight:700; font-family:Outfit, sans-serif;">${m.tipo === 'ingreso' ? '+' : '−'} ${window.Moneda.formatear(m.monto)}</span>
        </div>`)
      .join('');
  }

  // Usuarios (para elegir el responsable de la caja chica): solo
  // admin_general puede pedir /usuarios — admin_consorcio no tiene ningún
  // listado de usuarios disponible todavía en el sistema, así que para
  // ese rol el campo cae a un ID numérico simple en vez de romper el flujo.
  async function obtenerUsuariosSiSePuede() {
    if (usuariosCache !== null) return usuariosCache;
    if (usuario.rol !== 'admin_general') {
      usuariosCache = [];
      return usuariosCache;
    }
    try {
      usuariosCache = await window.Api.get('/usuarios');
    } catch (error) {
      usuariosCache = [];
    }
    return usuariosCache;
  }

  function nombreUsuario(id) {
    const u = (usuariosCache || []).find((x) => x.id === id);
    return u ? `${u.nombre} (${window.Layout.ETIQUETAS_ROL[u.rol] || u.rol})` : `Usuario #${id}`;
  }

  // ------------------------------- Fondos -------------------------------
  async function cargarFondos() {
    const contenedor = document.getElementById('lista-fondos');
    contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">${window.Cargando.html()}</p>`;
    try {
      fondosCache = await window.Api.get(`/edificios/${edificioId}/fondos`);
    } catch (error) {
      contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--crit);padding:10px 0;">${error.message}</p>`;
      return;
    }
    renderListaFondos(fondosCache);
  }

  function renderListaFondos(fondos) {
    const contenedor = document.getElementById('lista-fondos');
    if (fondos.length === 0) {
      contenedor.innerHTML = '<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">Todavía no hay fondos creados — usá "+ Nuevo fondo".</p>';
      return;
    }
    contenedor.innerHTML = fondos
      .map((f) => `
        <button type="button" class="detail-item content-glass fila-lista boton-ver-fondo" data-id="${f.id}" style="width:100%; text-align:left; border:0; cursor:pointer; font:inherit; color:inherit;">
          <b style="font-size:13.5px;">${f.nombre}</b>
          <div class="fila-lista-acciones">
            <span style="font-size:13.5px; font-weight:700; font-family:Outfit, sans-serif;">${window.Moneda.formatear(f.saldo)}</span>
          </div>
        </button>`)
      .join('');
    contenedor.querySelectorAll('.boton-ver-fondo').forEach((boton) => {
      boton.addEventListener('click', () => mostrarDetalleFondo(Number(boton.dataset.id)));
    });
  }

  function configurarModalFondo() {
    const modal = document.getElementById('modal-fondo');
    const form = document.getElementById('form-fondo');
    const mensajeError = document.getElementById('mensaje-error-fondo');
    const mensajeErrorTexto = document.getElementById('mensaje-error-fondo-texto');
    window.Formularios.habilitarEnterComoTab(form);

    function abrir() {
      form.reset();
      mensajeError.style.display = 'none';
      modal.classList.add('open');
    }
    function cerrar() { modal.classList.remove('open'); }

    document.getElementById('boton-nuevo-fondo').addEventListener('click', abrir);
    document.getElementById('modal-fondo-cerrar').addEventListener('click', cerrar);
    document.getElementById('boton-fondo-cancelar').addEventListener('click', cerrar);

    form.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      mensajeError.style.display = 'none';
      try {
        await window.Api.post(`/edificios/${edificioId}/fondos`, {
          nombre: document.getElementById('campo-fondo-nombre').value.trim(),
        });
        cerrar();
        await cargarFondos();
      } catch (error) {
        mensajeErrorTexto.textContent = error.message;
        mensajeError.style.display = 'flex';
      }
    });
  }

  function configurarModalDetalleFondo() {
    document.getElementById('modal-detalle-fondo-cerrar').addEventListener('click', () => {
      document.getElementById('modal-detalle-fondo').classList.remove('open');
    });

    const form = document.getElementById('form-movimiento-fondo');
    const mensajeError = document.getElementById('mensaje-error-movimiento-fondo');
    const mensajeErrorTexto = document.getElementById('mensaje-error-movimiento-fondo-texto');
    window.Formularios.habilitarEnterComoTab(form);

    form.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      mensajeError.style.display = 'none';
      try {
        await window.Api.post(`/edificios/${edificioId}/fondos/${fondoActualId}/movimientos`, {
          tipo: document.getElementById('campo-movimiento-fondo-tipo').value,
          monto: Number(document.getElementById('campo-movimiento-fondo-monto').value),
          fecha: document.getElementById('campo-movimiento-fondo-fecha').value,
          descripcion: document.getElementById('campo-movimiento-fondo-descripcion').value.trim() || null,
        });
        await cargarFondos(); // refresca fondosCache primero — si no, el saldo de abajo se recalcula con el dato viejo
        await refrescarMovimientosFondoAbierto();
        form.reset();
        document.getElementById('campo-movimiento-fondo-fecha').value = new Date().toISOString().slice(0, 10);
      } catch (error) {
        mensajeErrorTexto.textContent = error.message;
        mensajeError.style.display = 'flex';
      }
    });
  }

  // Separada de mostrarDetalleFondo() a propósito: esta NO toca
  // modal.classList.add('open') ni resetea el formulario apenas se llama —
  // reusar mostrarDetalleFondo() acá reabría el modal solo si el usuario
  // lo cerraba mientras el POST del movimiento todavía estaba en vuelo
  // (bug real, encontrado con Playwright antes de aprobar esta tarea).
  async function refrescarMovimientosFondoAbierto() {
    const fondo = fondosCache.find((f) => f.id === fondoActualId);
    document.getElementById('detalle-fondo-saldo').textContent = fondo ? `Saldo: ${window.Moneda.formatear(fondo.saldo)}` : '—';

    const contenedor = document.getElementById('detalle-fondo-movimientos');
    try {
      const movimientos = await window.Api.get(`/edificios/${edificioId}/fondos/${fondoActualId}/movimientos`);
      contenedor.innerHTML = renderMovimientos(movimientos);
    } catch (error) {
      contenedor.innerHTML = `<p style="font-size:12px;color:var(--crit);margin:0;">${error.message}</p>`;
    }
  }

  function mostrarDetalleFondo(fondoId) {
    fondoActualId = fondoId;
    const modal = document.getElementById('modal-detalle-fondo');
    const fondo = fondosCache.find((f) => f.id === fondoId);

    document.getElementById('detalle-fondo-titulo').textContent = fondo ? fondo.nombre : '—';
    document.getElementById('detalle-fondo-saldo').textContent = fondo ? `Saldo: ${window.Moneda.formatear(fondo.saldo)}` : '—';
    document.getElementById('mensaje-error-movimiento-fondo').style.display = 'none';
    document.getElementById('form-movimiento-fondo').reset();
    document.getElementById('campo-movimiento-fondo-fecha').value = new Date().toISOString().slice(0, 10);
    modal.classList.add('open');

    document.getElementById('detalle-fondo-movimientos').innerHTML = `<p style="font-size:12px;color:var(--ink-3);margin:0;">${window.Cargando.html()}</p>`;
    refrescarMovimientosFondoAbierto();
  }

  // -------------------------------- Caja --------------------------------
  // A diferencia de Fondos (una lista), Caja es un único registro por
  // edificio — se muestra directo en el sub-panel, sin una lista intermedia.
  async function cargarCaja() {
    const contenedor = document.getElementById('caja-contenido');
    contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">${window.Cargando.html()}</p>`;
    await obtenerUsuariosSiSePuede();
    try {
      cajaActual = await window.Api.get(`/edificios/${edificioId}/caja`);
      renderCaja(cajaActual);
    } catch (error) {
      cajaActual = null;
      renderCajaSinConfigurar();
    }
  }

  function renderCajaSinConfigurar() {
    document.getElementById('caja-contenido').innerHTML = `
      <div class="detail-item content-glass" style="text-align:center; padding:24px 16px;">
        <p style="font-size:12.5px;color:var(--ink-3);margin:0 0 12px;">Este edificio todavía no tiene caja chica configurada.</p>
        <button type="button" class="boton-primario" id="boton-configurar-caja" style="width:auto; padding:9px 16px;">Configurar caja chica</button>
      </div>`;
    document.getElementById('boton-configurar-caja').addEventListener('click', () => abrirModalCaja(null));
  }

  function renderCaja(caja) {
    document.getElementById('caja-contenido').innerHTML = `
      <div class="detail-item content-glass" style="margin-bottom:16px;">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;">
          <div>
            <div style="font-size:10.5px; color:var(--ink-3); text-transform:uppercase; letter-spacing:.05em;">Saldo actual</div>
            <div style="font-size:20px; font-weight:700; font-family:Outfit, sans-serif;">${window.Moneda.formatear(caja.saldo)}</div>
          </div>
          <button type="button" class="icon-btn icon-btn-sm" id="boton-editar-caja" aria-label="Editar caja chica">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
          </button>
        </div>
        <div style="display:flex; gap:18px; flex-wrap:wrap; font-size:12px; color:var(--ink-3);">
          <span>Monto fijo: <b style="color:var(--ink-2);">${window.Moneda.formatear(caja.monto_fijo)}</b></span>
          <span>Responsable: <b style="color:var(--ink-2);">${nombreUsuario(caja.responsable_id)}</b></span>
        </div>
      </div>

      <h4 style="margin:0 0 8px; font-size:12.5px; color:var(--ink-3);">Movimientos</h4>
      <div id="caja-movimientos" class="detail-item content-glass" style="margin-bottom:16px;"><!-- generado por JS --></div>

      <div class="mensaje-error" id="mensaje-error-movimiento-caja" style="display:none;">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex:none;"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>
        <span id="mensaje-error-movimiento-caja-texto"></span>
      </div>
      <form id="form-movimiento-caja" autocomplete="off">
        <div class="form-grid-2">
          <div class="campo">
            <label for="campo-movimiento-caja-tipo">Tipo</label>
            <select id="campo-movimiento-caja-tipo" required>
              <option value="ingreso">Ingreso (reposición)</option>
              <option value="egreso">Egreso</option>
            </select>
          </div>
          <div class="campo">
            <label for="campo-movimiento-caja-monto">Monto</label>
            <input type="number" id="campo-movimiento-caja-monto" min="0.01" step="0.01" required placeholder="0.00">
          </div>
        </div>
        <div class="form-grid-2">
          <div class="campo">
            <label for="campo-movimiento-caja-fecha">Fecha</label>
            <input type="date" id="campo-movimiento-caja-fecha" required>
          </div>
          <div class="campo">
            <label for="campo-movimiento-caja-descripcion">Descripción (opcional)</label>
            <input type="text" id="campo-movimiento-caja-descripcion" placeholder="Detalle breve">
          </div>
        </div>
        <div class="modal-formulario-acciones">
          <button type="submit" class="boton-primario" id="boton-movimiento-caja-guardar">+ Cargar movimiento</button>
        </div>
      </form>`;

    document.getElementById('boton-editar-caja').addEventListener('click', () => abrirModalCaja(caja));
    document.getElementById('campo-movimiento-caja-fecha').value = new Date().toISOString().slice(0, 10);
    cargarMovimientosCaja();

    const form = document.getElementById('form-movimiento-caja');
    window.Formularios.habilitarEnterComoTab(form);
    form.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      const mensajeError = document.getElementById('mensaje-error-movimiento-caja');
      mensajeError.style.display = 'none';
      try {
        await window.Api.post(`/edificios/${edificioId}/caja/movimientos`, {
          tipo: document.getElementById('campo-movimiento-caja-tipo').value,
          monto: Number(document.getElementById('campo-movimiento-caja-monto').value),
          fecha: document.getElementById('campo-movimiento-caja-fecha').value,
          descripcion: document.getElementById('campo-movimiento-caja-descripcion').value.trim() || null,
        });
        await cargarCaja(); // recarga todo el sub-panel: saldo, monto fijo y la lista de movimientos
      } catch (error) {
        document.getElementById('mensaje-error-movimiento-caja-texto').textContent = error.message;
        mensajeError.style.display = 'flex';
      }
    });
  }

  async function cargarMovimientosCaja() {
    const contenedor = document.getElementById('caja-movimientos');
    contenedor.innerHTML = `<p style="font-size:12px;color:var(--ink-3);margin:0;">${window.Cargando.html()}</p>`;
    try {
      const movimientos = await window.Api.get(`/edificios/${edificioId}/caja/movimientos`);
      contenedor.innerHTML = renderMovimientos(movimientos);
    } catch (error) {
      contenedor.innerHTML = `<p style="font-size:12px;color:var(--crit);margin:0;">${error.message}</p>`;
    }
  }

  function configurarModalCaja() {
    const modal = document.getElementById('modal-caja-config');
    const form = document.getElementById('form-caja-config');
    const mensajeError = document.getElementById('mensaje-error-caja-config');
    const mensajeErrorTexto = document.getElementById('mensaje-error-caja-config-texto');
    window.Formularios.habilitarEnterComoTab(form);

    function cerrar() { modal.classList.remove('open'); }
    document.getElementById('modal-caja-config-cerrar').addEventListener('click', cerrar);
    document.getElementById('boton-caja-config-cancelar').addEventListener('click', cerrar);

    form.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      mensajeError.style.display = 'none';

      const seEligeConSelect = document.getElementById('campo-caja-responsable-select-wrap').style.display !== 'none';
      const responsableId = seEligeConSelect
        ? Number(document.getElementById('campo-caja-responsable-select').value)
        : Number(document.getElementById('campo-caja-responsable-numero').value);
      if (!responsableId) {
        mensajeErrorTexto.textContent = 'Falta indicar el responsable.';
        mensajeError.style.display = 'flex';
        return;
      }
      const montoFijo = Number(document.getElementById('campo-caja-monto-fijo').value);

      try {
        if (cajaActual) {
          await window.Api.patch(`/edificios/${edificioId}/caja`, { responsable_id: responsableId, monto_fijo: montoFijo });
        } else {
          await window.Api.post(`/edificios/${edificioId}/caja`, { responsable_id: responsableId, monto_fijo: montoFijo });
        }
        cerrar();
        await cargarCaja();
      } catch (error) {
        mensajeErrorTexto.textContent = error.message;
        mensajeError.style.display = 'flex';
      }
    });
  }

  async function abrirModalCaja(cajaExistente) {
    const modal = document.getElementById('modal-caja-config');
    document.getElementById('form-caja-config').reset();
    document.getElementById('mensaje-error-caja-config').style.display = 'none';
    document.getElementById('modal-caja-config-titulo').textContent = cajaExistente ? 'Editar caja chica' : 'Configurar caja chica';

    const usuarios = await obtenerUsuariosSiSePuede();
    const selectWrap = document.getElementById('campo-caja-responsable-select-wrap');
    const numeroWrap = document.getElementById('campo-caja-responsable-numero-wrap');

    if (usuarios.length > 0) {
      selectWrap.style.display = 'block';
      numeroWrap.style.display = 'none';
      const select = document.getElementById('campo-caja-responsable-select');
      select.innerHTML = usuarios
        .map((u) => `<option value="${u.id}">${u.nombre} (${window.Layout.ETIQUETAS_ROL[u.rol] || u.rol})</option>`)
        .join('');
      if (cajaExistente) select.value = cajaExistente.responsable_id;
    } else {
      selectWrap.style.display = 'none';
      numeroWrap.style.display = 'block';
      if (cajaExistente) document.getElementById('campo-caja-responsable-numero').value = cajaExistente.responsable_id;
    }

    document.getElementById('campo-caja-monto-fijo').value = cajaExistente ? cajaExistente.monto_fijo : '';
    modal.classList.add('open');
  }

  // ---------------------------- Gastos para selects ----------------------------
  // Presupuestos (al aprobar) y Facturas (siempre) necesitan elegir un
  // Gasto real de este edificio — se pide fresco cada vez que se abre el
  // modal correspondiente, nunca depende de si la pestaña Gastos ya se
  // visitó o no.
  async function obtenerGastosParaSelect() {
    try {
      return await window.Api.get(`/edificios/${edificioId}/gastos`);
    } catch (error) {
      return [];
    }
  }

  // ---------------------------- Presupuestos ----------------------------
  async function cargarPresupuestos() {
    const contenedor = document.getElementById('lista-presupuestos');
    contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">${window.Cargando.html()}</p>`;
    try {
      presupuestosCache = await window.Api.get(`/edificios/${edificioId}/presupuestos`);
    } catch (error) {
      contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--crit);padding:10px 0;">${error.message}</p>`;
      return;
    }
    document.getElementById('resumen-presupuestos').textContent = presupuestosCache.length
      ? `${presupuestosCache.length} presupuesto${presupuestosCache.length === 1 ? '' : 's'}`
      : '';
    renderListaPresupuestos(presupuestosCache);
  }

  function renderListaPresupuestos(presupuestos) {
    const contenedor = document.getElementById('lista-presupuestos');
    if (presupuestos.length === 0) {
      contenedor.innerHTML = '<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">Todavía no hay presupuestos cargados — usá "+ Nuevo presupuesto".</p>';
      return;
    }
    contenedor.innerHTML = presupuestos
      .map((p) => `
        <div class="detail-item content-glass fila-lista" style="margin-bottom:10px;">
          <div>
            <b style="font-size:13.5px;">${p.descripcion}</b>
            <div style="font-size:11.5px;color:var(--ink-3);">${formatearFecha(p.fecha)}${p.gasto_id ? ' · vinculado al gasto #' + p.gasto_id : ''}</div>
          </div>
          <div class="fila-lista-acciones">
            <span style="font-size:13.5px; font-weight:700; font-family:Outfit, sans-serif;">${window.Moneda.formatear(p.monto)}</span>
            ${p.estado === 'pendiente'
              ? `<button type="button" class="boton-chico boton-aprobar-presupuesto" data-id="${p.id}">Aprobar</button>
                 <button type="button" class="boton-chico boton-chico-critico boton-rechazar-presupuesto" data-id="${p.id}">Rechazar</button>`
              : p.estado === 'aprobado'
                ? '<span class="rol-badge">Aprobado</span>'
                : '<span style="font-size:12px; font-weight:700; color:var(--crit);">Rechazado</span>'}
          </div>
        </div>`)
      .join('');

    contenedor.querySelectorAll('.boton-aprobar-presupuesto').forEach((boton) => {
      boton.addEventListener('click', () => abrirModalAprobarPresupuesto(Number(boton.dataset.id)));
    });
    contenedor.querySelectorAll('.boton-rechazar-presupuesto').forEach((boton) => {
      boton.addEventListener('click', () => rechazarPresupuesto(Number(boton.dataset.id), boton));
    });
  }

  async function rechazarPresupuesto(id, boton) {
    const mensajeError = document.getElementById('mensaje-error-presupuestos-lista');
    mensajeError.style.display = 'none';
    boton.disabled = true;
    try {
      await window.Api.patch(`/edificios/${edificioId}/presupuestos/${id}/estado`, { estado: 'rechazado' });
      await cargarPresupuestos();
    } catch (error) {
      boton.disabled = false;
      document.getElementById('mensaje-error-presupuestos-lista-texto').textContent = error.message;
      mensajeError.style.display = 'flex';
    }
  }

  function configurarModalPresupuesto() {
    const modal = document.getElementById('modal-presupuesto');
    const form = document.getElementById('form-presupuesto');
    const mensajeError = document.getElementById('mensaje-error-presupuesto');
    const mensajeErrorTexto = document.getElementById('mensaje-error-presupuesto-texto');
    window.Formularios.habilitarEnterComoTab(form);

    function abrir() {
      form.reset();
      document.getElementById('campo-presupuesto-fecha').value = new Date().toISOString().slice(0, 10);
      mensajeError.style.display = 'none';
      modal.classList.add('open');
    }
    function cerrar() { modal.classList.remove('open'); }

    document.getElementById('boton-nuevo-presupuesto').addEventListener('click', abrir);
    document.getElementById('modal-presupuesto-cerrar').addEventListener('click', cerrar);
    document.getElementById('boton-presupuesto-cancelar').addEventListener('click', cerrar);

    form.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      mensajeError.style.display = 'none';
      try {
        await window.Api.post(`/edificios/${edificioId}/presupuestos`, {
          descripcion: document.getElementById('campo-presupuesto-descripcion').value.trim(),
          monto: Number(document.getElementById('campo-presupuesto-monto').value),
          fecha: document.getElementById('campo-presupuesto-fecha').value,
        });
        cerrar();
        await cargarPresupuestos();
      } catch (error) {
        mensajeErrorTexto.textContent = error.message;
        mensajeError.style.display = 'flex';
      }
    });
  }

  function configurarModalAprobarPresupuesto() {
    const modal = document.getElementById('modal-aprobar-presupuesto');
    const form = document.getElementById('form-aprobar-presupuesto');
    const mensajeError = document.getElementById('mensaje-error-aprobar-presupuesto');
    const mensajeErrorTexto = document.getElementById('mensaje-error-aprobar-presupuesto-texto');
    window.Formularios.habilitarEnterComoTab(form);

    function cerrar() { modal.classList.remove('open'); }
    document.getElementById('modal-aprobar-presupuesto-cerrar').addEventListener('click', cerrar);
    document.getElementById('boton-aprobar-presupuesto-cancelar').addEventListener('click', cerrar);

    form.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      mensajeError.style.display = 'none';
      const gastoId = document.getElementById('campo-aprobar-presupuesto-gasto').value;
      try {
        await window.Api.patch(`/edificios/${edificioId}/presupuestos/${presupuestoAprobarId}/estado`, {
          estado: 'aprobado',
          gasto_id: gastoId ? Number(gastoId) : null,
        });
        cerrar();
        await cargarPresupuestos();
      } catch (error) {
        mensajeErrorTexto.textContent = error.message;
        mensajeError.style.display = 'flex';
      }
    });
  }

  async function abrirModalAprobarPresupuesto(id) {
    presupuestoAprobarId = id;
    const presupuesto = presupuestosCache.find((p) => p.id === id);
    document.getElementById('aprobar-presupuesto-sub').textContent = presupuesto
      ? `${presupuesto.descripcion} · ${window.Moneda.formatear(presupuesto.monto)}`
      : '—';
    document.getElementById('mensaje-error-aprobar-presupuesto').style.display = 'none';

    const gastos = await obtenerGastosParaSelect();
    const select = document.getElementById('campo-aprobar-presupuesto-gasto');
    select.innerHTML = '<option value="">Sin vincular todavía</option>' +
      gastos.map((g) => `<option value="${g.id}">${g.rubro} · ${formatearFecha(g.fecha)} · ${window.Moneda.formatear(g.monto)}</option>`).join('');

    document.getElementById('modal-aprobar-presupuesto').classList.add('open');
  }

  // ------------------------------- Facturas ------------------------------
  async function cargarFacturas() {
    const contenedor = document.getElementById('lista-facturas');
    contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">${window.Cargando.html()}</p>`;
    let facturas;
    try {
      facturas = await window.Api.get(`/edificios/${edificioId}/facturas`);
    } catch (error) {
      contenedor.innerHTML = `<p style="font-size:12.5px;color:var(--crit);padding:10px 0;">${error.message}</p>`;
      return;
    }
    document.getElementById('resumen-facturas').textContent = facturas.length
      ? `${facturas.length} factura${facturas.length === 1 ? '' : 's'}`
      : '';
    renderListaFacturas(facturas);
  }

  function renderListaFacturas(facturas) {
    const contenedor = document.getElementById('lista-facturas');
    if (facturas.length === 0) {
      contenedor.innerHTML = '<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">Todavía no hay facturas cargadas — usá "+ Nueva factura".</p>';
      return;
    }
    contenedor.innerHTML = facturas
      .map((f) => `
        <div class="detail-item content-glass fila-lista">
          <div>
            <b style="font-size:13.5px;">${f.numero}</b>
            <div style="font-size:11.5px;color:var(--ink-3);">${formatearFecha(f.fecha)} · gasto #${f.gasto_id}${f.archivo_url ? ` · <a href="${f.archivo_url}" target="_blank" rel="noopener" style="color:inherit;">archivo</a>` : ''}</div>
          </div>
          <div class="fila-lista-acciones">
            <span style="font-size:13.5px; font-weight:700; font-family:Outfit, sans-serif;">${window.Moneda.formatear(f.monto)}</span>
          </div>
        </div>`)
      .join('');
  }

  function configurarModalFactura() {
    const modal = document.getElementById('modal-factura');
    const form = document.getElementById('form-factura');
    const mensajeError = document.getElementById('mensaje-error-factura');
    const mensajeErrorTexto = document.getElementById('mensaje-error-factura-texto');
    window.Formularios.habilitarEnterComoTab(form);

    async function abrir() {
      form.reset();
      mensajeError.style.display = 'none';
      document.getElementById('campo-factura-fecha').value = new Date().toISOString().slice(0, 10);

      const gastos = await obtenerGastosParaSelect();
      document.getElementById('campo-factura-gasto').innerHTML = gastos.length
        ? gastos.map((g) => `<option value="${g.id}">${g.rubro} · ${formatearFecha(g.fecha)} · ${window.Moneda.formatear(g.monto)}</option>`).join('')
        : '<option value="" disabled selected>Este edificio todavía no tiene gastos cargados</option>';

      modal.classList.add('open');
    }
    function cerrar() { modal.classList.remove('open'); }

    document.getElementById('boton-nueva-factura').addEventListener('click', abrir);
    document.getElementById('modal-factura-cerrar').addEventListener('click', cerrar);
    document.getElementById('boton-factura-cancelar').addEventListener('click', cerrar);

    form.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      mensajeError.style.display = 'none';
      try {
        await window.Api.post(`/edificios/${edificioId}/facturas`, {
          gasto_id: Number(document.getElementById('campo-factura-gasto').value),
          numero: document.getElementById('campo-factura-numero').value.trim(),
          monto: Number(document.getElementById('campo-factura-monto').value),
          fecha: document.getElementById('campo-factura-fecha').value,
          archivo_url: document.getElementById('campo-factura-archivo').value.trim() || null,
        });
        cerrar();
        await cargarFacturas();
      } catch (error) {
        mensajeErrorTexto.textContent = error.message;
        mensajeError.style.display = 'flex';
      }
    });
  }
});

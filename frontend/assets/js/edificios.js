// edificios.js — lógica de edificios.html: listado, alta, y detalle
// (Datos generales / Estructura) de un edificio existente.
document.addEventListener('DOMContentLoaded', async () => {
  const usuario = await window.Layout.montar('edificios.html');
  if (!usuario) return; // montarLayout ya mandó al login si hacía falta

  const vistaNoAutorizado = document.getElementById('vista-no-autorizado');
  const vistaListado = document.getElementById('vista-listado');
  const vistaAlta = document.getElementById('vista-alta');
  const vistaExito = document.getElementById('vista-exito');
  const vistaDetalle = document.getElementById('vista-detalle');

  if (usuario.rol !== 'admin_general') {
    vistaNoAutorizado.style.display = 'block';
    return;
  }

  function mostrarSolo(vista) {
    [vistaListado, vistaAlta, vistaExito, vistaDetalle].forEach((v) => { v.style.display = 'none'; });
    vista.style.display = 'block';
  }

  // Declarados acá arriba (no más abajo, junto a iniciarDetalle) porque el
  // ruteo de más abajo ya puede llamar a iniciarDetalle antes de que la
  // ejecución llegue a esa parte del archivo — con "let" más abajo tiraba
  // "Cannot access 'edificioActual' before initialization" (temporal dead
  // zone), aunque la función en sí ya estuviera hoisted.
  let edificioActual = null;
  let usuariosCache = []; // para resolver nombres de admin/propietario/inquilino y poblar los selects de asignación

  await cargarAdministradoresDeConsorcio();
  window.Formularios.habilitarEnterComoTab(document.getElementById('form-alta'));
  window.Formularios.habilitarEnterComoTab(document.getElementById('form-piso'));
  window.Formularios.habilitarEnterComoTab(document.getElementById('form-departamento'));

  // ---------------------------------------------------------------
  // Ruteo simple por query string: ?id=N muestra el detalle de ESE
  // edificio; sin id, el listado. Sin router — es una sola página.
  // ---------------------------------------------------------------
  const idParam = new URLSearchParams(location.search).get('id');
  if (idParam) {
    mostrarSolo(vistaDetalle);
    await iniciarDetalle(Number(idParam));
  } else {
    mostrarSolo(vistaListado);
    await cargarListadoEdificios();
  }

  document.getElementById('boton-nuevo-edificio').addEventListener('click', () => mostrarSolo(vistaAlta));
  document.getElementById('boton-volver-desde-alta').addEventListener('click', () => mostrarSolo(vistaListado));

  // ---------------------------------------------------------------
  // Listado de edificios
  // ---------------------------------------------------------------
  async function cargarListadoEdificios() {
    const lista = document.getElementById('lista-edificios');
    lista.innerHTML = '<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">Cargando…</p>';
    let edificios;
    try {
      edificios = await window.Api.get('/edificios');
    } catch (error) {
      lista.innerHTML = `<p style="font-size:12.5px;color:var(--crit);padding:10px 0;">${error.message}</p>`;
      return;
    }

    if (edificios.length === 0) {
      lista.innerHTML = '<p style="font-size:12.5px;color:var(--ink-3);padding:10px 0;">Todavía no hay edificios — creá el primero con "+ Nuevo edificio".</p>';
      return;
    }

    lista.innerHTML = edificios
      .map((e) => {
        const totalUnidades = e.pisos.reduce((suma, p) => suma + p.departamentos.length, 0);
        return `
        <a href="edificios.html?id=${e.id}" class="detail-item content-glass fila-lista" style="text-decoration:none; color:inherit;">
          <div>
            <b style="font-size:13.5px;">${e.nombre}</b>
            <div style="font-size:11.5px;color:var(--ink-3);">${e.direccion}${e.cp ? ' · CP ' + e.cp : ''}</div>
          </div>
          <div class="fila-lista-acciones">
            <span class="rol-badge">${e.pisos.length} piso(s) · ${totalUnidades} unidad(es)</span>
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--ink-4);"><path d="M9 18l6-6-6-6"/></svg>
          </div>
        </a>`;
      })
      .join('');
  }

  // ---------------------------------------------------------------
  // Detalle: Datos generales / Estructura
  // ---------------------------------------------------------------
  async function iniciarDetalle(id) {
    document.getElementById('detalle-titulo').textContent = 'Cargando…';
    document.getElementById('boton-ver-estructura').href = `edificios.html?id=${id}`;

    try {
      [edificioActual, usuariosCache] = await Promise.all([
        window.Api.get(`/edificios/${id}`),
        window.Api.get('/usuarios'),
      ]);
    } catch (error) {
      document.getElementById('detalle-titulo').textContent = 'No se pudo cargar el edificio';
      document.getElementById('detalle-direccion').textContent = error.message;
      return;
    }

    document.getElementById('detalle-titulo').textContent = edificioActual.nombre;
    document.getElementById('detalle-direccion').textContent =
      `${edificioActual.direccion}${edificioActual.cp ? ' · CP ' + edificioActual.cp : ''}`;

    renderDatosGenerales();
    await renderEstructura();
    configurarViewSwitch();
  }

  function configurarViewSwitch() {
    const switchEl = document.getElementById('detalle-view-switch');
    const panelGeneral = document.getElementById('panel-datos-generales');
    const panelEstructura = document.getElementById('panel-estructura');
    switchEl.querySelectorAll('button').forEach((boton) => {
      boton.addEventListener('click', () => {
        switchEl.querySelectorAll('button').forEach((b) => b.classList.remove('active'));
        boton.classList.add('active');
        const esGeneral = boton.dataset.view === 'general';
        panelGeneral.style.display = esGeneral ? 'block' : 'none';
        panelEstructura.style.display = esGeneral ? 'none' : 'block';
      });
    });
  }

  function renderDatosGenerales() {
    const e = edificioActual;
    const admin = usuariosCache.find((u) => u.id === e.admin_consorcio_id);
    const panel = document.getElementById('panel-datos-generales');
    panel.innerHTML = `
      <div class="form-grid-2">
        <div class="campo"><label>Dirección</label><div style="font-size:14px;">${e.direccion}</div></div>
        <div class="campo"><label>CP</label><div style="font-size:14px;">${e.cp || '—'}</div></div>
        <div class="campo"><label>CUIT / razón social</label><div style="font-size:14px;">${e.cuit || '—'}</div></div>
        <div class="campo"><label>Administrador de Consorcio</label><div style="font-size:14px;">${admin ? admin.nombre : 'Sin asignar'}</div></div>
        <div class="campo"><label>Días vencimiento expensas</label><div style="font-size:14px;">${e.dias_vencimiento_expensas}</div></div>
        <div class="campo"><label>Recargo por mora</label><div style="font-size:14px;">${e.recargo_mora_porcentual}%</div></div>
      </div>
      ${e.latitud && e.longitud ? '<div class="mapa-campo"><label>Ubicación</label><div class="mapa-contenedor" id="mapa-detalle" style="height:220px;"></div></div>' : ''}
    `;
    if (e.latitud && e.longitud) {
      window.Mapa.crearMapa('mapa-detalle', e.latitud, e.longitud);
    }
  }

  async function renderEstructura() {
    renderPisos();
    await Promise.all([renderCocheras(), renderEspacios()]);
  }

  function renderPisos() {
    const contenedor = document.getElementById('lista-pisos');
    const pisos = [...edificioActual.pisos].sort((a, b) => a.orden - b.orden);
    if (pisos.length === 0) {
      contenedor.innerHTML = '<p style="font-size:12.5px;color:var(--ink-3);">Sin pisos todavía.</p>';
      return;
    }
    contenedor.innerHTML = pisos
      .map((piso) => `
        <div class="detail-item content-glass" style="margin-bottom:10px;">
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">
            <b style="font-size:13.5px;">Piso ${piso.numero}</b>
            <span style="font-size:11px;color:var(--ink-3);">${piso.departamentos.length} unidad(es)</span>
          </div>
          ${piso.departamentos.length === 0
            ? '<p style="font-size:12px;color:var(--ink-3);margin:6px 0 0;">Sin departamentos.</p>'
            : piso.departamentos.map((d) => filaDepartamento(d)).join('')}
        </div>`)
      .join('');
    contenedor.querySelectorAll('.boton-asignar').forEach((boton) => {
      boton.addEventListener('click', () => abrirModalAsignacion(boton.dataset.id));
    });
  }

  function filaDepartamento(d) {
    const propietario = usuariosCache.find((u) => u.id === d.propietario_id);
    const inquilino = usuariosCache.find((u) => u.id === d.inquilino_id);
    const partes = [];
    if (propietario) partes.push(`Prop.: ${propietario.nombre}`);
    if (inquilino) partes.push(`Inq.: ${inquilino.nombre}`);
    return `
      <div class="fila-lista${d.ocupado ? ' ocupado' : ''}" style="padding:8px 0; border-top:1px solid var(--line-2);">
        <div>
          <b style="font-size:13px;">${d.identificador}</b>
          <div style="font-size:11px;color:var(--ink-3);">${d.m2 ? d.m2 + ' m² · ' : ''}${partes.length ? partes.join(' · ') : 'Sin asignar'}</div>
        </div>
        <div class="fila-lista-acciones">
          ${d.ocupado ? '<span class="rol-badge">Ocupado</span>' : '<span style="font-size:11px;color:var(--ink-3);">Vacío</span>'}
          <button type="button" class="chip-link boton-asignar" data-id="${d.id}">Asignar</button>
        </div>
      </div>`;
  }

  async function renderCocheras() {
    const contenedor = document.getElementById('lista-cocheras');
    let cocheras;
    try {
      cocheras = await window.Api.get(`/edificios/${edificioActual.id}/cocheras`);
    } catch (error) {
      contenedor.innerHTML = `<p style="font-size:12px;color:var(--crit);">${error.message}</p>`;
      return;
    }
    contenedor.innerHTML = cocheras.length === 0
      ? '<p style="font-size:12px;color:var(--ink-3);">Sin cocheras cargadas.</p>'
      : cocheras.map((c) => `
          <div class="fila-lista" style="padding:6px 0;">
            <b style="font-size:13px;">Cochera ${c.numero}</b>
            <span class="rol-badge">${c.tipo === 'fija' ? 'Fija' : 'Rotativa'}</span>
          </div>`).join('');
  }

  async function renderEspacios() {
    const contenedor = document.getElementById('lista-espacios');
    let espacios;
    try {
      espacios = await window.Api.get(`/edificios/${edificioActual.id}/espacios-comunes`);
    } catch (error) {
      contenedor.innerHTML = `<p style="font-size:12px;color:var(--crit);">${error.message}</p>`;
      return;
    }
    contenedor.innerHTML = espacios.length === 0
      ? '<p style="font-size:12px;color:var(--ink-3);">Sin espacios comunes cargados.</p>'
      : espacios.map((e) => `
          <div class="fila-lista" style="padding:6px 0;">
            <b style="font-size:13px;">${e.nombre}</b>
            <span style="font-size:11px;color:var(--ink-3);">${e.capacidad ? 'Capacidad: ' + e.capacidad : ''}</span>
          </div>`).join('');
  }

  async function recargarEstructura() {
    edificioActual = await window.Api.get(`/edificios/${edificioActual.id}`);
    await renderEstructura();
  }

  // ---------------------------------------------------------------
  // Modal: nuevo piso
  // ---------------------------------------------------------------
  const modalPiso = document.getElementById('modal-piso');
  const formPiso = document.getElementById('form-piso');
  function abrirModalPiso() { modalPiso.classList.add('open'); document.getElementById('campo-piso-numero').focus(); }
  function cerrarModalPiso() { modalPiso.classList.remove('open'); formPiso.reset(); document.getElementById('mensaje-error-piso').style.display = 'none'; }
  document.getElementById('boton-nuevo-piso').addEventListener('click', abrirModalPiso);
  document.getElementById('modal-piso-cerrar').addEventListener('click', cerrarModalPiso);
  document.getElementById('boton-piso-cancelar').addEventListener('click', cerrarModalPiso);

  formPiso.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const mensajeError = document.getElementById('mensaje-error-piso');
    const boton = document.getElementById('boton-piso-guardar');
    mensajeError.style.display = 'none';
    boton.disabled = true;
    boton.textContent = 'Creando…';
    try {
      await window.Api.post(`/edificios/${edificioActual.id}/pisos`, {
        numero: document.getElementById('campo-piso-numero').value.trim(),
        orden: Number(document.getElementById('campo-piso-orden').value),
      });
      cerrarModalPiso();
      await recargarEstructura();
    } catch (error) {
      document.getElementById('mensaje-error-piso-texto').textContent = error.message;
      mensajeError.style.display = 'flex';
    } finally {
      boton.disabled = false;
      boton.textContent = 'Crear piso';
    }
  });

  // ---------------------------------------------------------------
  // Modal: nuevo departamento
  // ---------------------------------------------------------------
  const modalDepartamento = document.getElementById('modal-departamento');
  const formDepartamento = document.getElementById('form-departamento');
  function abrirModalDepartamento() {
    const select = document.getElementById('campo-departamento-piso');
    const pisos = [...edificioActual.pisos].sort((a, b) => a.orden - b.orden);
    select.innerHTML = pisos.length
      ? pisos.map((p) => `<option value="${p.id}">Piso ${p.numero}</option>`).join('')
      : '<option value="">Creá un piso primero</option>';
    modalDepartamento.classList.add('open');
    document.getElementById('campo-departamento-identificador').focus();
  }
  function cerrarModalDepartamento() { modalDepartamento.classList.remove('open'); formDepartamento.reset(); document.getElementById('mensaje-error-departamento').style.display = 'none'; }
  document.getElementById('boton-nuevo-departamento').addEventListener('click', abrirModalDepartamento);
  document.getElementById('modal-departamento-cerrar').addEventListener('click', cerrarModalDepartamento);
  document.getElementById('boton-departamento-cancelar').addEventListener('click', cerrarModalDepartamento);

  formDepartamento.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const mensajeError = document.getElementById('mensaje-error-departamento');
    const boton = document.getElementById('boton-departamento-guardar');
    mensajeError.style.display = 'none';
    boton.disabled = true;
    boton.textContent = 'Creando…';
    const m2 = document.getElementById('campo-departamento-m2').value;
    try {
      await window.Api.post(`/edificios/${edificioActual.id}/departamentos`, {
        piso_id: Number(document.getElementById('campo-departamento-piso').value),
        identificador: document.getElementById('campo-departamento-identificador').value.trim(),
        m2: m2 ? Number(m2) : null,
      });
      cerrarModalDepartamento();
      await recargarEstructura();
    } catch (error) {
      document.getElementById('mensaje-error-departamento-texto').textContent = error.message;
      mensajeError.style.display = 'flex';
    } finally {
      boton.disabled = false;
      boton.textContent = 'Crear departamento';
    }
  });

  // ---------------------------------------------------------------
  // Modal: asignar propietario/inquilino
  // ---------------------------------------------------------------
  const modalAsignacion = document.getElementById('modal-asignacion');
  const formAsignacion = document.getElementById('form-asignacion');
  let departamentoAsignandoId = null;

  function poblarSelectRol(selectId, rol, valorActual, idsAExcluir = []) {
    const select = document.getElementById(selectId);
    const opciones = usuariosCache.filter((u) => u.rol === rol && u.activo && !idsAExcluir.includes(u.id));
    select.innerHTML = '<option value="">Sin asignar</option>' +
      opciones.map((u) => `<option value="${u.id}">${u.nombre} (${u.email})</option>`).join('');
    select.value = valorActual || '';
  }

  function abrirModalAsignacion(departamentoId) {
    const todosLosDeptos = edificioActual.pisos.flatMap((p) => p.departamentos);
    const depto = todosLosDeptos.find((d) => String(d.id) === String(departamentoId));
    if (!depto) return;
    departamentoAsignandoId = depto.id;
    document.getElementById('modal-asignacion-sub').textContent = `Departamento "${depto.identificador}"`;
    poblarSelectRol('campo-asignacion-propietario', 'propietario', depto.propietario_id);
    // Un inquilino vive en un solo lugar a la vez (a diferencia del
    // propietario, que sí puede tener varias unidades a su nombre) — el
    // combo no ofrece un inquilino que ya está en OTRO departamento de
    // este edificio. El backend es quien realmente hace cumplir la regla
    // (PATCH /departamentos/{id}/asignacion); esto es solo para no ni
    // siquiera mostrar una opción que el backend va a rechazar.
    const inquilinosYaAsignados = todosLosDeptos
      .filter((d) => d.id !== depto.id && d.inquilino_id)
      .map((d) => d.inquilino_id);
    poblarSelectRol('campo-asignacion-inquilino', 'inquilino', depto.inquilino_id, inquilinosYaAsignados);
    modalAsignacion.classList.add('open');
  }
  function cerrarModalAsignacion() { modalAsignacion.classList.remove('open'); document.getElementById('mensaje-error-asignacion').style.display = 'none'; }
  document.getElementById('modal-asignacion-cerrar').addEventListener('click', cerrarModalAsignacion);
  document.getElementById('boton-asignacion-cancelar').addEventListener('click', cerrarModalAsignacion);

  formAsignacion.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const mensajeError = document.getElementById('mensaje-error-asignacion');
    const boton = document.getElementById('boton-asignacion-guardar');
    mensajeError.style.display = 'none';
    boton.disabled = true;
    boton.textContent = 'Guardando…';
    const propietarioId = document.getElementById('campo-asignacion-propietario').value;
    const inquilinoId = document.getElementById('campo-asignacion-inquilino').value;
    try {
      await window.Api.patch(`/edificios/departamentos/${departamentoAsignandoId}/asignacion`, {
        propietario_id: propietarioId ? Number(propietarioId) : null,
        inquilino_id: inquilinoId ? Number(inquilinoId) : null,
      });
      cerrarModalAsignacion();
      await recargarEstructura();
    } catch (error) {
      document.getElementById('mensaje-error-asignacion-texto').textContent = error.message;
      mensajeError.style.display = 'flex';
    } finally {
      boton.disabled = false;
      boton.textContent = 'Guardar asignación';
    }
  });

  // ---------------------------------------------------------------
  // Mapa del alta: se geocodifica recién cuando Dirección Y CP están
  // completos (al perder el foco de cualquiera de los dos) — nunca
  // antes, y nunca se valida "a mitad de carga" mientras el otro
  // campo sigue vacío.
  // ---------------------------------------------------------------
  const campoDireccion = document.getElementById('campo-direccion');
  const campoCp = document.getElementById('campo-cp');
  const bloqueMapa = document.getElementById('bloque-mapa');
  const modalDireccion = document.getElementById('modal-direccion');

  let mapaActual = null;
  let ultimaUbicacion = null; // {lat, lon} del último geocode exitoso — es lo que viaja en el alta

  async function intentarGeocodificar() {
    const direccion = campoDireccion.value.trim();
    const cp = campoCp.value.trim();
    if (!direccion || !cp) return; // falta uno de los dos: no se hace nada todavía

    bloqueMapa.style.display = 'block';
    mostrarEstadoMapa('Buscando ubicación…');

    let resultado;
    try {
      resultado = await window.Mapa.geocodificar(direccion, cp);
    } catch (error) {
      mostrarEstadoMapa('No se pudo consultar el mapa en este momento.');
      return;
    }

    if (!resultado) {
      ultimaUbicacion = null;
      mostrarEstadoMapa('Dirección no encontrada.');
      abrirModalDireccion();
      return;
    }

    ultimaUbicacion = { lat: parseFloat(resultado.lat), lon: parseFloat(resultado.lon) };
    dibujarMapa(ultimaUbicacion.lat, ultimaUbicacion.lon);
  }

  function mostrarEstadoMapa(texto) {
    let contenedor = document.getElementById('mapa-contenedor');
    contenedor.innerHTML = `<div class="mapa-vacio">${texto}</div>`;
  }

  function dibujarMapa(lat, lon) {
    const contenedor = document.getElementById('mapa-contenedor');
    contenedor.innerHTML = ''; // Leaflet necesita el div limpio antes de re-inicializar
    if (mapaActual) {
      mapaActual.remove();
      mapaActual = null;
    }
    mapaActual = window.Mapa.crearMapa('mapa-contenedor', lat, lon);
  }

  function abrirModalDireccion() {
    modalDireccion.classList.add('open');
  }
  function cerrarModalDireccion() {
    modalDireccion.classList.remove('open');
  }
  document.getElementById('boton-cerrar-modal').addEventListener('click', cerrarModalDireccion);
  modalDireccion.addEventListener('click', (evento) => {
    if (evento.target === modalDireccion) cerrarModalDireccion();
  });

  campoDireccion.addEventListener('blur', intentarGeocodificar);
  campoCp.addEventListener('blur', intentarGeocodificar);

  // ---------------------------------------------------------------
  // Administrador de Consorcio (select con datos reales)
  // ---------------------------------------------------------------
  async function cargarAdministradoresDeConsorcio() {
    const select = document.getElementById('campo-admin-consorcio');
    try {
      const usuarios = await window.Api.get('/usuarios');
      usuarios
        .filter((u) => u.rol === 'admin_consorcio' && u.activo)
        .forEach((u) => {
          const opcion = document.createElement('option');
          opcion.value = u.id;
          opcion.textContent = `${u.nombre} (${u.email})`;
          select.appendChild(opcion);
        });
    } catch (error) {
      // no bloquea el alta — el campo simplemente queda con la única opción "Sin asignar"
    }
  }

  // ---------------------------------------------------------------
  // Envío del formulario de alta
  // ---------------------------------------------------------------
  const formulario = document.getElementById('form-alta');
  const mensajeError = document.getElementById('mensaje-error');
  const mensajeErrorTexto = document.getElementById('mensaje-error-texto');
  const botonGuardar = document.getElementById('boton-guardar');

  formulario.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    mensajeError.style.display = 'none';
    botonGuardar.disabled = true;
    botonGuardar.textContent = 'Creando…';

    const adminConsorcioId = document.getElementById('campo-admin-consorcio').value;

    try {
      const edificio = await window.Api.post('/edificios', {
        nombre: document.getElementById('campo-nombre').value.trim(),
        direccion: campoDireccion.value.trim(),
        cp: campoCp.value.trim() || null,
        cuit: document.getElementById('campo-cuit').value.trim() || null,
        latitud: ultimaUbicacion ? ultimaUbicacion.lat : null,
        longitud: ultimaUbicacion ? ultimaUbicacion.lon : null,
        admin_consorcio_id: adminConsorcioId ? Number(adminConsorcioId) : null,
        cantidad_pisos: Number(document.getElementById('campo-pisos').value),
        unidades_por_piso: Number(document.getElementById('campo-unidades').value),
      });

      const totalDeptos = edificio.pisos.reduce((suma, piso) => suma + piso.departamentos.length, 0);
      document.getElementById('exito-resumen').textContent =
        `"${edificio.nombre}" — ${edificio.pisos.length} piso(s), ${totalDeptos} departamento(s) generados automáticamente.`;
      document.getElementById('boton-ver-estructura').href = `edificios.html?id=${edificio.id}`;

      mostrarSolo(vistaExito);
    } catch (error) {
      mensajeErrorTexto.textContent = error.message;
      mensajeError.style.display = 'flex';
    } finally {
      botonGuardar.disabled = false;
      botonGuardar.textContent = 'Crear edificio';
    }
  });

  document.getElementById('boton-crear-otro').addEventListener('click', () => {
    formulario.reset();
    document.getElementById('campo-pisos').value = 1;
    document.getElementById('campo-unidades').value = 4;
    bloqueMapa.style.display = 'none';
    if (mapaActual) { mapaActual.remove(); mapaActual = null; }
    ultimaUbicacion = null;
    mostrarSolo(vistaAlta);
  });
});

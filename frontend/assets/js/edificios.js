// edificios.js — lógica de edificios.html (alta de edificio).
document.addEventListener('DOMContentLoaded', async () => {
  const usuario = await window.Layout.montar('edificios.html');
  if (!usuario) return; // montarLayout ya mandó al login si hacía falta

  const vistaNoAutorizado = document.getElementById('vista-no-autorizado');
  const vistaAlta = document.getElementById('vista-alta');
  const vistaExito = document.getElementById('vista-exito');

  if (usuario.rol !== 'admin_general') {
    vistaNoAutorizado.style.display = 'block';
    return;
  }

  vistaAlta.style.display = 'block';
  await cargarAdministradoresDeConsorcio();
  window.Formularios.habilitarEnterComoTab(document.getElementById('form-alta'));

  // ---------------------------------------------------------------
  // Mapa: se geocodifica recién cuando Dirección Y CP están completos
  // (al perder el foco de cualquiera de los dos) — nunca antes, y nunca
  // se valida "a mitad de carga" mientras el otro campo sigue vacío.
  // ---------------------------------------------------------------
  const campoDireccion = document.getElementById('campo-direccion');
  const campoCp = document.getElementById('campo-cp');
  const bloqueMapa = document.getElementById('bloque-mapa');
  const mapaVacio = document.getElementById('mapa-vacio');
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
  // Envío del formulario
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

      vistaAlta.style.display = 'none';
      vistaExito.style.display = 'block';
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
    vistaExito.style.display = 'none';
    vistaAlta.style.display = 'block';
  });
});

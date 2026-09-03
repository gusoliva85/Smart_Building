// layout.js — sidebar de navegación compartido por toda la zona autenticada.
//
// Documento Técnico, sección 4.1: cada pantalla detrás de login llama a
// `window.Layout.montar('archivo-actual.html')` una sola vez al cargar.
// Hace la guarda de sesión (sin token -> login), pide /auth/me, arma los
// accesos según el rol, marca el activo, engancha logout y el toggle
// mobile — ninguna pantalla nueva vuelve a escribir esto a mano.

const ICONOS_SIDEBAR = {
  edificios: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 21V6l8-3 8 3v15"/><path d="M9 21v-6h6v6"/><path d="M9 10h.01M15 10h.01M9 14h.01M15 14h.01"/></svg>',
  usuarios: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>',
};

// Accesos habilitados por rol. Se completa a medida que existen más
// pantallas — nunca se linkea a un archivo que todavía no existe.
const ACCESOS_POR_ROL = {
  admin_general: [
    { href: 'edificios.html', texto: 'Edificios', icono: 'edificios' },
    { href: 'usuarios.html', texto: 'Usuarios', icono: 'usuarios' },
  ],
};

// Traducción de los 8 roles (Documento General, sección 3) a texto legible
// — compartida por el sidebar y cualquier pantalla que necesite mostrar el
// rol de alguien (usuarios.html hoy, proveedores/reclamos después).
const ETIQUETAS_ROL = {
  admin_general: 'Admin General',
  admin_consorcio: 'Admin de Consorcio',
  encargado: 'Encargado',
  propietario: 'Propietario',
  inquilino: 'Inquilino',
  proveedor: 'Proveedor',
  auditor: 'Auditor',
  seguridad: 'Personal de seguridad',
};

async function montarLayout(paginaActual) {
  if (!window.Api.obtenerToken()) {
    location.href = 'index.html';
    return null;
  }

  let usuario;
  try {
    usuario = await window.Api.get('/auth/me');
  } catch (error) {
    location.href = 'index.html';
    return null;
  }

  const nav = document.getElementById('sidebar-nav');
  const accesos = ACCESOS_POR_ROL[usuario.rol] || [];
  nav.innerHTML = accesos.length
    ? accesos
        .map(
          (a) => `<a class="sidebar-link${a.href === paginaActual ? ' activo' : ''}" href="${a.href}">${ICONOS_SIDEBAR[a.icono] || ''}<span>${a.texto}</span></a>`
        )
        .join('')
    : '<p style="font-size:12px;color:var(--ink-4);padding:10px 12px;">Todavía no hay pantallas para tu rol.</p>';

  document.getElementById('sidebar-user-nombre').textContent = usuario.nombre;
  document.getElementById('sidebar-user-rol').textContent = ETIQUETAS_ROL[usuario.rol] || usuario.rol;

  document.getElementById('boton-logout').addEventListener('click', () => {
    window.Api.borrarToken();
    location.href = 'index.html';
  });

  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  const menuBtn = document.getElementById('menu-btn');
  const abrir = () => { sidebar.classList.add('open'); backdrop.classList.add('open'); };
  const cerrar = () => { sidebar.classList.remove('open'); backdrop.classList.remove('open'); };
  if (menuBtn) menuBtn.addEventListener('click', abrir);
  if (backdrop) backdrop.addEventListener('click', cerrar);

  return usuario;
}

window.Layout = { montar: montarLayout, ETIQUETAS_ROL };

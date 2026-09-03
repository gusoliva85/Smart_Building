// theme.js — toggle de tema claro/oscuro, compartido por todas las pantallas.
//
// Arranca siempre en tema claro (Documento Técnico, sección 1.3.2): nunca se
// guarda "oscuro" como default, es una preferencia que el usuario elige a
// mano en cada visita.
//
// Animación: barrido circular que nace del punto exacto del clic — el
// refinamiento que la skill premium-uiux (componentes.md, "Toggle de tema")
// dejaba documentado como pendiente. Usa la View Transitions API para
// congelar un snapshot del estado anterior, y Web Animations API para animar
// un clip-path circle() creciendo desde el botón hasta cubrir toda la
// pantalla, aplicado sobre el pseudo-elemento ::view-transition-new(root).
// Si el navegador no soporta View Transitions, el cambio es instantáneo.

const ICONO_SOL = '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>';
const ICONO_LUNA = '<path d="M20.5 14.3A8.5 8.5 0 119.7 3.5a7 7 0 0010.8 10.8z"/>';

function pintarIcono(boton, tema) {
  const svg = boton.querySelector('svg');
  if (svg) svg.innerHTML = tema === 'dark' ? ICONO_LUNA : ICONO_SOL;
}

document.addEventListener('DOMContentLoaded', () => {
  const boton = document.getElementById('theme-toggle');
  if (!boton) return;

  const raiz = document.documentElement;
  pintarIcono(boton, raiz.getAttribute('data-theme'));

  boton.addEventListener('click', (evento) => {
    const siguiente = raiz.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    const aplicar = () => {
      raiz.setAttribute('data-theme', siguiente);
      pintarIcono(boton, siguiente);
    };

    if (!document.startViewTransition) {
      aplicar();
      return;
    }

    const { clientX: x, clientY: y } = evento;
    const radioMaximo = Math.hypot(
      Math.max(x, window.innerWidth - x),
      Math.max(y, window.innerHeight - y),
    );

    const transicion = document.startViewTransition(aplicar);
    transicion.ready.then(() => {
      raiz.animate(
        { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radioMaximo}px at ${x}px ${y}px)`] },
        { duration: 550, easing: 'ease-in-out', pseudoElement: '::view-transition-new(root)' },
      );
    });
  });
});

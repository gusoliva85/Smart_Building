// theme.js — toggle de tema claro/oscuro, compartido por todas las pantallas.
//
// Arranca siempre en tema claro (Documento Técnico, sección 1.3.2): nunca se
// guarda "oscuro" como default, es una preferencia que el usuario elige a
// mano en cada visita. Usa la View Transitions API para animar el cambio;
// si el navegador no la soporta, el cambio es instantáneo pero sigue
// funcionando igual.
document.addEventListener('DOMContentLoaded', () => {
  const boton = document.getElementById('theme-toggle');
  if (!boton) return;

  boton.addEventListener('click', () => {
    const raiz = document.documentElement;
    const siguiente = raiz.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    const aplicar = () => raiz.setAttribute('data-theme', siguiente);

    if (document.startViewTransition) {
      document.startViewTransition(aplicar);
    } else {
      aplicar();
    }
  });
});

// theme.js — toggle de tema claro/oscuro, compartido por todas las pantallas.
//
// Persiste la elección en localStorage y la vuelve a aplicar en cada
// página nueva (ver el script inline en el <head> de cada HTML, que la
// aplica ANTES de que se pinte nada, para no mostrar un parpadeo de claro
// antes de pasar a oscuro). Arranca en claro únicamente cuando no hay
// ninguna preferencia guardada todavía (primera visita).
//
// Antes de esto, el tema se reiniciaba a claro en cada pantalla nueva —
// bug real reportado por el usuario: cambiar a oscuro y navegar a
// Edificios o Usuarios volvía a claro sin querer.
//
// La animación es la que trae el navegador por default con la View
// Transitions API (cross-fade). Se probó un barrido circular más
// elaborado (Fase 12) pero se revirtió a pedido explícito del usuario:
// tuvo un bug real de z-index y, sobre todo, se reportó como lento
// específicamente en Chrome en producción.
document.addEventListener('DOMContentLoaded', () => {
  const boton = document.getElementById('theme-toggle');
  if (!boton) return;

  boton.addEventListener('click', () => {
    const raiz = document.documentElement;
    const siguiente = raiz.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    const aplicar = () => {
      raiz.setAttribute('data-theme', siguiente);
      try {
        localStorage.setItem('tema', siguiente);
      } catch (error) {
        // modo privado o storage bloqueado — el toggle sigue funcionando, solo no persiste
      }
    };

    if (document.startViewTransition) {
      document.startViewTransition(aplicar);
    } else {
      aplicar();
    }
  });
});

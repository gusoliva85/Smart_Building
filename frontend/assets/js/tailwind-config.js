// tailwind-config.js
//
// Se carga DESPUÉS del script del CDN de Tailwind (cdn.tailwindcss.com) en
// cada página. Le enseña a las utilidades de color de Tailwind (bg-accent,
// text-ink-3, border-crit, etc.) a leer las MISMAS variables CSS que ya
// definimos en tokens.css, en vez de traer su propia paleta de colores por
// default — así se puede maquetar con clases utilitarias sueltas
// ("class=p-4 rounded-2xl bg-accent") sin perder el sistema de theming
// claro/oscuro (Documento Técnico, sección 1.3.1).
tailwind.config = {
  theme: {
    extend: {
      colors: {
        // Superficies y texto
        'bg-1': 'var(--bg-1)', 'bg-2': 'var(--bg-2)',
        ink: 'var(--ink)', 'ink-2': 'var(--ink-2)', 'ink-3': 'var(--ink-3)', 'ink-4': 'var(--ink-4)',
        line: 'var(--line)', 'line-2': 'var(--line-2)', 'line-strong': 'var(--line-strong)',
        // Acento de marca
        accent: 'var(--accent)', 'accent-2': 'var(--accent-2)', 'accent-soft': 'var(--accent-soft)',
        // Semáforo funcional — únicos colores con licencia para representar estado
        ok: 'var(--ok)', warn: 'var(--warn)', pend: 'var(--pend)', crit: 'var(--crit)',
        navy: 'var(--navy)',
      },
      fontFamily: {
        display: ['Outfit', 'sans-serif'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        card: 'var(--r-card)',
        lg2: 'var(--r-lg)',
        sm2: 'var(--r-sm)',
      },
      // Los dos quiebres responsive del proyecto (Documento Técnico, 1.3.7):
      // mobile-first real, con tablet en 640px y desktop/web en 1024px.
      screens: {
        sm: '640px',
        lg: '1024px',
      },
    },
  },
};

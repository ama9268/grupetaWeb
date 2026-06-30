/**
 * GrupetaWeb · 6el1 — Lógica de tema claro/oscuro
 * Incluir en base.html ANTES del </head> para evitar flash de color.
 * Clave localStorage: 'g6_theme'  →  '1' = oscuro, '0' = claro
 */
(function () {
  const KEY = 'g6_theme';
  const html = document.documentElement;

  function applyTheme(dark) {
    if (dark) {
      html.classList.add('dark');
      html.classList.remove('light');
    } else {
      html.classList.remove('dark');
      html.classList.add('light');
    }
  }

  function loadTheme() {
    const stored = localStorage.getItem(KEY);
    if (stored !== null) return stored === '1';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  window.toggleTheme = function () {
    const dark = !html.classList.contains('dark');
    localStorage.setItem(KEY, dark ? '1' : '0');
    applyTheme(dark);
    const label = document.getElementById('theme-label');
    if (label) label.textContent = dark ? 'Oscuro' : 'Claro';
  };

  applyTheme(loadTheme());

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
    if (localStorage.getItem(KEY) === null) applyTheme(e.matches);
  });
})();

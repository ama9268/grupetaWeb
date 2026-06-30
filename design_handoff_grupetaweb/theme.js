/**
 * GrupetaWeb · 6el1 — Lógica de tema claro/oscuro
 * Copiar en: static/js/theme.js
 * Incluir en base.html ANTES del </head> para evitar flash:
 *   <script src="{% static 'js/theme.js' %}"></script>
 */

(function () {
  const KEY = 'g6_theme'; // '1' = oscuro, '0' = claro
  const html = document.documentElement;

  // Aplica el tema inmediatamente (antes del paint)
  function applyTheme(dark) {
    if (dark) {
      html.classList.add('dark');
      html.classList.remove('light');
    } else {
      html.classList.remove('dark');
      html.classList.add('light');
    }
  }

  // Lee preferencia guardada; si no hay, usa preferencia del sistema
  function loadTheme() {
    const stored = localStorage.getItem(KEY);
    if (stored !== null) return stored === '1';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  // Toggle público
  window.toggleTheme = function () {
    const dark = !html.classList.contains('dark');
    localStorage.setItem(KEY, dark ? '1' : '0');
    applyTheme(dark);
    // Actualiza el texto del botón si existe
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.textContent = dark ? 'Oscuro' : 'Claro';
  };

  // Aplicar en carga
  applyTheme(loadTheme());

  // Escuchar cambios del sistema operativo
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (localStorage.getItem(KEY) === null) applyTheme(e.matches);
  });
})();

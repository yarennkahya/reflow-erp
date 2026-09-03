/* ============================================================================
   Tema değiştirici. Bootstrap 5.3'ün yerel [data-bs-theme] mekanizması.
   FOUC engelleyen kısa IIFE <head>'de inline kalır — buraya taşınamaz.
   ========================================================================== */
(function (window, document) {
  'use strict';

  var KEY = 'reflow-theme';
  var root = document.documentElement;

  function current() {
    return root.getAttribute('data-bs-theme') === 'dark' ? 'dark' : 'light';
  }

  function paintButton(theme) {
    O.$$('[data-o-theme-toggle]').forEach(function (btn) {
      var icon = btn.querySelector('i');
      if (icon) icon.className = 'bi bi-' + (theme === 'dark' ? 'sun' : 'moon');
      btn.setAttribute('aria-pressed', String(theme === 'dark'));
    });
  }

  function apply(theme) {
    root.setAttribute('data-bs-theme', theme);
    try { window.localStorage.setItem(KEY, theme); } catch (e) { /* gizli sekme */ }
    paintButton(theme);
    // Grafikler renklerini CSS token'larından okur; yeniden çizmeleri gerekir.
    O.emit('o:theme', { theme: theme });
  }

  document.addEventListener('click', function (event) {
    var btn = event.target.closest ? event.target.closest('[data-o-theme-toggle]') : null;
    if (!btn) return;
    event.preventDefault();
    apply(current() === 'dark' ? 'light' : 'dark');
  });

  paintButton(current());
})(window, document);

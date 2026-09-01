/* Public sayfalar: şifre göster/gizle + yumuşak kaydırma. */
(function (window, document) {
  'use strict';

  document.addEventListener('click', function (event) {
    var btn = event.target.closest ? event.target.closest('[data-o-password-toggle]') : null;
    if (!btn) return;
    var field = document.querySelector(btn.getAttribute('data-o-password-toggle'));
    if (!field) return;
    var show = field.type === 'password';
    field.type = show ? 'text' : 'password';
    var icon = btn.querySelector('i');
    if (icon) icon.className = 'bi bi-eye' + (show ? '-slash' : '');
  });
})(window, document);

/* ============================================================================
   O — çekirdek yardımcılar. Tüm diğer o-*.js dosyaları bunu bekler.
   Modül YOK: nginx arkasında type="module" CORS/MIME sivri uçları getirir.
   ========================================================================== */
(function (window, document) {
  'use strict';

  var O = window.O || {};

  O.$  = function (sel, root) { return (root || document).querySelector(sel); };
  O.$$ = function (sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  };

  O.csrfToken = function () {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  };

  /** <body data-msg-*> üzerinden çevrilebilir metinler. */
  O.text = function (key, fallback) {
    var value = document.body && document.body.dataset ? document.body.dataset[key] : null;
    return value || fallback || '';
  };

  O.debounce = function (fn, wait) {
    var timer = null;
    return function () {
      var args = arguments, self = this;
      window.clearTimeout(timer);
      timer = window.setTimeout(function () { fn.apply(self, args); }, wait);
    };
  };

  /** Basit olay veriyolu — widget'lar birbirini import etmeden haberleşir. */
  O.emit = function (name, detail) {
    document.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
  };
  O.on = function (name, handler) { document.addEventListener(name, handler); };

  /* ── Toast ───────────────────────────────────────────────────────────── */
  function stack() {
    var el = document.getElementById('o-toasts');
    if (!el) {
      el = document.createElement('div');
      el.id = 'o-toasts';
      el.className = 'o-toasts';
      el.setAttribute('aria-live', 'polite');
      el.setAttribute('aria-atomic', 'true');
      document.body.appendChild(el);
    }
    return el;
  }

  O.toast = function (message, variant, timeout) {
    var toast = document.createElement('div');
    toast.className = 'o-toast o-toast--' + (variant || 'info');
    toast.setAttribute('role', variant === 'error' || variant === 'danger' ? 'alert' : 'status');

    var body = document.createElement('div');
    body.className = 'o-toast-body';
    body.textContent = message;

    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'o-toast-close';
    close.setAttribute('aria-label', O.text('msgClose', 'Kapat'));
    close.innerHTML = '&times;';
    close.addEventListener('click', function () { toast.remove(); });

    toast.appendChild(body);
    toast.appendChild(close);
    stack().appendChild(toast);

    window.setTimeout(function () { toast.remove(); }, timeout || 5000);
    return toast;
  };

  // Sunucudan render edilen toast'lar (django messages) da kapanabilmeli.
  document.addEventListener('click', function (event) {
    var btn = event.target.closest ? event.target.closest('.o-toast-close') : null;
    if (!btn) return;
    var toast = btn.closest('.o-toast');
    if (toast) toast.remove();
  });

  document.addEventListener('DOMContentLoaded', function () {
    O.$$('#o-toasts .o-toast').forEach(function (toast, index) {
      window.setTimeout(function () { toast.remove(); }, 6000 + index * 400);
    });
  });

  window.O = O;
})(window, document);

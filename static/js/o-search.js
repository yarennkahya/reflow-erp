/* ============================================================================
   Arama çubuğu facet'leri.

   Filtre/gruplama panelindeki radio'lar zaten o-ajax.js'in change handler'ına
   takılıyor — burada YALNIZCA facet "×" davranışı var.
   ========================================================================== */
(function (window, document) {
  'use strict';

  document.addEventListener('click', function (event) {
    var btn = event.target.closest ? event.target.closest('[data-o-facet-clear]') : null;
    if (!btn) return;

    var form = btn.closest('form');
    if (!form) return;
    event.preventDefault();

    var param = btn.getAttribute('data-o-facet-clear');

    // Metin girdisi -> boşalt. Radio grubu -> 'all'/'' seçeneğine dön.
    var field = form.querySelector('[name="' + param + '"]');
    if (field && (field.type === 'search' || field.type === 'text' || field.type === 'hidden')) {
      field.value = '';
    } else {
      var options = form.querySelectorAll('input[name="' + param + '"]');
      var reset = null;
      options.forEach(function (opt) {
        if (opt.value === 'all' || opt.value === '') reset = opt;
      });
      if (reset) reset.checked = true;
      else options.forEach(function (opt) { opt.checked = false; });
    }

    if (form.requestSubmit) form.requestSubmit();
    else form.submit();
  });
})(window, document);

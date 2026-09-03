/* ============================================================================
   Onay diyaloğu — onsubmit="return confirm()" yerine.

   ÖNEMLİ: gerçek POST yapmaya devam eder. Silme view'larının bir kısmı
   ProtectedError yakalayıp messages.error basıyor; AJAX çağrısı onu yutardı.
   ========================================================================== */
(function (window, document) {
  'use strict';

  var pending = null;

  function dialog() {
    var el = document.getElementById('o-confirm-dialog');
    if (el) return el;

    el = document.createElement('dialog');
    el.id = 'o-confirm-dialog';
    el.className = 'o-dialog';
    el.innerHTML =
      '<form method="dialog">' +
      '  <div class="o-dialog-body">' +
      '    <h2 class="o-dialog-title" data-o-title></h2>' +
      '    <p class="o-dialog-text" data-o-text></p>' +
      '  </div>' +
      '  <div class="o-dialog-foot">' +
      '    <button class="o-btn" value="cancel" data-o-cancel></button>' +
      '    <button class="o-btn o-btn--primary" value="ok" data-o-ok></button>' +
      '  </div>' +
      '</form>';
    document.body.appendChild(el);

    el.querySelector('[data-o-cancel]').textContent = O.text('msgCancel', 'Vazgeç');
    el.querySelector('[data-o-ok]').textContent = O.text('msgConfirm', 'Onayla');
    el.querySelector('[data-o-title]').textContent = O.text('msgAreYouSure', 'Emin misiniz?');

    el.addEventListener('close', function () {
      if (el.returnValue === 'ok' && pending) {
        var form = pending;
        pending = null;
        form.dataset.oConfirmed = '1';
        if (form.requestSubmit) form.requestSubmit();
        else form.submit();
      }
      pending = null;
    });
    return el;
  }

  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (!form || !form.hasAttribute || !form.hasAttribute('data-o-confirm')) return;
    if (form.dataset.oConfirmed === '1') {
      delete form.dataset.oConfirmed;
      return;                                    // ikinci turda geç
    }
    event.preventDefault();

    var el = dialog();
    el.querySelector('[data-o-text]').textContent = form.getAttribute('data-o-confirm');
    pending = form;

    if (typeof el.showModal === 'function') {
      el.showModal();
    } else if (window.confirm(form.getAttribute('data-o-confirm'))) {
      // <dialog> desteklemeyen tarayıcı — yerel confirm'e düş
      pending = null;
      form.dataset.oConfirmed = '1';
      form.submit();
    }
  });
})(window, document);

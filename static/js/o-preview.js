/* ============================================================================
   Önizleme diyaloğu.

   [data-o-preview-url="/…"] taşıyan bir buton, o adresteki PARÇAYI bir
   <dialog> içine yükler. Tam sayfaya gitmeden fatura vb. içerik gösterilir.
   ========================================================================== */
(function (window, document) {
  'use strict';

  function dialog() {
    var el = document.getElementById('o-preview-dialog');
    if (el) return el;

    el = document.createElement('dialog');
    el.id = 'o-preview-dialog';
    el.className = 'o-dialog o-dialog--wide';
    el.innerHTML =
      '<div class="o-preview-head">' +
      '  <span class="o-preview-title"></span>' +
      '  <div class="o-preview-actions"></div>' +
      '  <button type="button" class="o-preview-close" aria-label="' +
           O.text('msgClose', 'Kapat') + '">&times;</button>' +
      '</div>' +
      '<div class="o-preview-body" tabindex="-1"></div>';
    document.body.appendChild(el);

    el.querySelector('.o-preview-close').addEventListener('click', function () {
      el.close();
    });
    // Boşluğa tıklayınca kapansın
    el.addEventListener('click', function (event) {
      if (event.target === el) el.close();
    });
    return el;
  }

  document.addEventListener('click', function (event) {
    var btn = event.target.closest ? event.target.closest('[data-o-preview-url]') : null;
    if (!btn) return;
    event.preventDefault();

    var el = dialog();
    var body = el.querySelector('.o-preview-body');
    var actions = el.querySelector('.o-preview-actions');

    el.querySelector('.o-preview-title').textContent = btn.getAttribute('data-o-preview-title') || '';
    actions.innerHTML = '';
    body.innerHTML = '<p class="o-preview-loading">' +
                     O.text('msgLoading', 'Yükleniyor…') + '</p>';

    if (typeof el.showModal === 'function') el.showModal();

    fetch(btn.getAttribute('data-o-preview-url'), {
      credentials: 'same-origin',
      headers: {'X-Requested-With': 'XMLHttpRequest'}
    })
      .then(function (r) { if (!r.ok) throw new Error('preview'); return r.text(); })
      .then(function (html) {
        body.innerHTML = html;
        // Butonun yanındaki eylemleri (gönder, detaya git) diyaloğa taşı
        var group = btn.closest('[data-o-preview-actions]');
        if (group) {
          O.$$('[data-o-preview-action]', group).forEach(function (node) {
            actions.appendChild(node.cloneNode(true));
          });
        }
        body.focus();
      })
      .catch(function () {
        body.innerHTML = '<p class="o-preview-loading">' +
                         O.text('msgPreviewFailed', 'Önizleme yüklenemedi.') + '</p>';
      });
  });
})(window, document);

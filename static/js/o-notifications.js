/* ============================================================================
   Bildirim zili. base.html'den taşındı; veri sözleşmesi aynen korundu:
   data-notification-feed-url / -menu / -read / -redirect, JSON {count, html}.
   ========================================================================== */
(function (window, document) {
  'use strict';

  function trigger() { return document.querySelector('[data-notification-feed-url]'); }

  function updateCount(count) {
    var btn = trigger();
    if (!btn) return;
    var badge = btn.querySelector('.o-appbar-badge');
    if (count > 0) {
      if (badge) { badge.textContent = count; return; }
      badge = document.createElement('span');
      badge.className = 'o-appbar-badge';
      badge.textContent = count;
      btn.appendChild(badge);
    } else if (badge) {
      badge.remove();
    }
  }

  function refresh() {
    var btn = trigger();
    var menu = document.querySelector('[data-notification-menu]');
    if (!btn || !menu) return;

    fetch(btn.dataset.notificationFeedUrl, {
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' }
    })
      .then(function (r) { if (!r.ok) throw new Error('feed'); return r.json(); })
      .then(function (payload) {
        menu.innerHTML = payload.html;
        updateCount(payload.count);
      })
      .catch(function () { /* sunucudan gelen ilk çıktı kullanılmaya devam eder */ });
  }

  var btn = trigger();
  if (btn) btn.addEventListener('show.bs.dropdown', refresh);

  document.addEventListener('submit', function (event) {
    var form = event.target.closest
      ? event.target.closest('form[data-notification-read]') : null;
    if (!form) return;
    event.preventDefault();

    var button = form.querySelector('button[type="submit"]');
    if (button) button.disabled = true;

    fetch(form.action, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json',
        'X-CSRFToken': O.csrfToken(),
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: new FormData(form)
    })
      .then(function (r) { if (!r.ok) throw new Error('read'); return r.json(); })
      .then(function (payload) {
        updateCount(payload.count);
        var redirect = payload.redirect_url || form.dataset.notificationRedirect;
        if (redirect) { window.location.assign(redirect); return; }

        var row = form.closest('tr');
        if (row) {
          row.classList.remove('o-unread');
          var status = row.querySelector('[data-notification-status]');
          if (status) {
            status.className = 'o-badge o-badge--muted';
            status.textContent = O.text('msgRead', 'Okundu');
          }
        }
        refresh();
      })
      .catch(function () {
        O.toast(O.text('msgNotifFailed', 'Bildirim güncellenemedi.'), 'error');
        if (button) button.disabled = false;
      });
  });
})(window, document);

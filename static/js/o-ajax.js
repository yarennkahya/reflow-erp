/* ============================================================================
   AJAX bölge çerçevesi.

   base.html'den OLDUĞU GİBİ taşındı — çalışıyor ve 8 partial buna bağlı.
   Yalnızca üç değişiklik:
     1) showError()  -> O.toast()
     2) hata metinleri <body data-*> üzerinden çevrilebilir
     3) replaceWith() sonrası 'o:region-replaced' olayı yayınlanır

   (3) gizli bir hatayı kapatıyor: eskiden bölge değişince içindeki hiçbir şey
   yeniden kurulmuyordu. Bölge içinde JS gerektiren bir şey olmadığı için
   görünmüyordu — ama kanban ve grafikler tam da bu bölgelerin içine giriyor.

   KURAL: data-ajax-region içinde yalnızca DEKLARATİF Bootstrap kullan
   (data-bs-toggle). new bootstrap.X() örneği swap'ta ölür.
   ========================================================================== */
(function (window, document) {
  'use strict';

  var AJAX_HEADERS = {
    'Accept': 'text/html',
    'X-Requested-With': 'XMLHttpRequest'
  };
  var controllers = new WeakMap();
  var debounceTimers = new WeakMap();

  function findTarget(selector) {
    try { return document.querySelector(selector); } catch (e) { return null; }
  }

  function fail(key, fallback) {
    O.toast(O.text(key, fallback), 'error');
  }

  function setBusy(form, isBusy) {
    form.setAttribute('aria-busy', String(isBusy));
    O.$$('button[type="submit"], input[type="submit"]', form).forEach(function (button) {
      if (isBusy) {
        button.dataset.ajaxWasDisabled = String(button.disabled);
        button.disabled = true;
      } else {
        button.disabled = button.dataset.ajaxWasDisabled === 'true';
        delete button.dataset.ajaxWasDisabled;
      }
    });
  }

  function getRequestUrl(form) {
    var url = new URL(form.getAttribute('action') || window.location.pathname,
                      window.location.origin);
    var params = new URLSearchParams();
    new FormData(form).forEach(function (value, key) {
      if (value !== '') params.append(key, value);
    });
    url.search = params.toString();
    return url;
  }

  function replaceRegion(url, targetSelector, signal) {
    return fetch(url, {
      credentials: 'same-origin',
      headers: AJAX_HEADERS,
      signal: signal
    }).then(function (response) {
      if (response.redirected) {
        window.location.assign(response.url);
        return null;
      }
      if (!response.ok) {
        throw new Error('HTTP ' + response.status);
      }
      return response.text().then(function (html) {
        var parsed = new DOMParser().parseFromString(html, 'text/html');
        var incoming = parsed.querySelector(targetSelector);
        var currentRegion = findTarget(targetSelector);
        if (!incoming || !currentRegion) {
          throw new Error('region-not-found');
        }
        var fresh = document.importNode(incoming, true);
        currentRegion.replaceWith(fresh);

        // Bölge içindeki widget'lar (kanban, grafik, x2many) yeniden kurulmalı.
        O.emit('o:region-replaced', { region: fresh, selector: targetSelector });

        return response.url;
      });
    });
  }

  function submitFilter(form, updateHistory) {
    var targetSelector = form.dataset.ajaxTarget;
    if (!targetSelector) return;

    var previous = controllers.get(form);
    if (previous) previous.abort();

    var controller = new AbortController();
    controllers.set(form, controller);
    setBusy(form, true);

    replaceRegion(getRequestUrl(form), targetSelector, controller.signal)
      .then(function (responseUrl) {
        if (responseUrl && updateHistory !== false) {
          var resolved = new URL(responseUrl, window.location.origin);
          history.replaceState({}, '', resolved.pathname + resolved.search + resolved.hash);
        }
      })
      .catch(function (error) {
        if (error.name !== 'AbortError') {
          fail('msgListFailed', 'Liste güncellenemedi. Lütfen tekrar deneyin.');
        }
      })
      .then(function () {
        if (controllers.get(form) === controller) setBusy(form, false);
      });
  }

  function followAjaxLink(link) {
    var targetSelector = link.dataset.ajaxTarget;
    if (!targetSelector) return;

    link.setAttribute('aria-busy', 'true');
    replaceRegion(link.href, targetSelector)
      .then(function (responseUrl) {
        if (responseUrl) {
          var resolved = new URL(responseUrl, window.location.origin);
          history.pushState({}, '', resolved.pathname + resolved.search + resolved.hash);
        }
      })
      .catch(function () {
        fail('msgContentFailed', 'İçerik güncellenemedi. Lütfen tekrar deneyin.');
      })
      .then(function () { link.setAttribute('aria-busy', 'false'); });
  }

  document.addEventListener('submit', function (event) {
    var form = event.target.closest
      ? event.target.closest('form[data-ajax-filter]') : null;
    if (!form) return;
    event.preventDefault();
    submitFilter(form);
  });

  document.addEventListener('input', function (event) {
    var input = event.target;
    if (!input || !input.closest) return;
    var form = input.closest('form[data-ajax-filter][data-ajax-autosubmit]');
    if (!form || !input.matches('input[type="search"], input[type="text"]')) return;

    window.clearTimeout(debounceTimers.get(form));
    debounceTimers.set(form, window.setTimeout(function () {
      form.requestSubmit();
    }, 300));
  });

  document.addEventListener('change', function (event) {
    var input = event.target;
    if (!input || !input.closest) return;
    var form = input.closest('form[data-ajax-filter][data-ajax-autosubmit]');
    if (!form || !input.matches('select, input[type="checkbox"], input[type="radio"]')) return;
    form.requestSubmit();
  });

  document.addEventListener('click', function (event) {
    var link = event.target.closest ? event.target.closest('a[data-ajax-link]') : null;
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey ||
        event.ctrlKey || event.shiftKey || event.altKey || link.target ||
        link.hasAttribute('download')) return;
    event.preventDefault();
    followAjaxLink(link);
  });

  window.addEventListener('popstate', function () {
    var region = document.querySelector('[data-ajax-region]');
    if (!region || !region.id) return;
    replaceRegion(window.location.href, '#' + region.id).catch(function () {
      window.location.reload();
    });
  });

  O.replaceRegion = replaceRegion;
})(window, document);

/* ============================================================================
   App bar davranışı: apps overlay + menü taşması.
   ========================================================================== */
(function (window, document) {
  'use strict';

  /* ── Apps overlay ────────────────────────────────────────────────────── */
  var overlay = document.getElementById('o-apps-overlay');
  var toggle = document.querySelector('[data-o-apps-toggle]');
  var filter = document.querySelector('[data-o-apps-filter]');
  var lastFocus = null;

  function tiles() { return O.$$('.o-apps-tile', overlay); }
  function visibleTiles() {
    return tiles().filter(function (t) { return !t.hidden && t.tagName === 'A'; });
  }

  function open() {
    if (!overlay) return;
    lastFocus = document.activeElement;
    overlay.hidden = false;
    document.body.classList.add('o-apps-open');
    if (toggle) toggle.setAttribute('aria-expanded', 'true');
    if (filter) { filter.value = ''; applyFilter(); filter.focus(); }
  }

  function close() {
    if (!overlay || overlay.hidden) return;
    overlay.hidden = true;
    document.body.classList.remove('o-apps-open');
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  function applyFilter() {
    var term = (filter ? filter.value : '').trim().toLowerCase();
    tiles().forEach(function (tile) {
      var name = tile.getAttribute('data-o-app-name') || '';
      tile.hidden = term !== '' && name.indexOf(term) === -1;
    });
  }

  if (toggle && overlay) {
    toggle.addEventListener('click', function (event) {
      event.preventDefault();
      overlay.hidden ? open() : close();
    });

    overlay.addEventListener('click', function (event) {
      if (event.target === overlay) close();      // boşluğa tıklama
    });

    if (filter) {
      filter.addEventListener('input', applyFilter);
      filter.addEventListener('keydown', function (event) {
        if (event.key !== 'Enter') return;
        var first = visibleTiles()[0];
        if (first) { event.preventDefault(); window.location.assign(first.href); }
      });
    }

    document.addEventListener('keydown', function (event) {
      if (overlay.hidden) return;

      if (event.key === 'Escape') { event.preventDefault(); close(); return; }

      if (event.key === 'ArrowDown' || event.key === 'ArrowRight' ||
          event.key === 'ArrowUp' || event.key === 'ArrowLeft') {
        var list = visibleTiles();
        if (!list.length) return;
        event.preventDefault();
        var index = list.indexOf(document.activeElement);
        var step = (event.key === 'ArrowDown' || event.key === 'ArrowRight') ? 1 : -1;
        var next = index === -1 ? 0 : (index + step + list.length) % list.length;
        list[next].focus();
        return;
      }

      // Odağı overlay içinde tut
      if (event.key === 'Tab') {
        var focusable = [filter].concat(visibleTiles()).filter(Boolean);
        if (!focusable.length) return;
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault(); last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault(); first.focus();
        }
      }
    });
  }

  /* ── Menü taşması: sığmayan sekmeler "…" dropdown'ına ─────────────────── */
  var menus = document.querySelector('[data-o-menu-overflow]');

  function reflowMenus() {
    if (!menus) return;
    var more = menus.querySelector('.o-appbar-more');
    var list = more ? more.querySelector('.dropdown-menu') : null;
    if (!more || !list) return;

    // Önce hepsini geri al, sonra yeniden ölç.
    O.$$('a', list).forEach(function (link) { menus.insertBefore(link, more); });
    list.innerHTML = '';
    more.classList.add('d-none');

    var links = O.$$(':scope > .o-appbar-menu', menus);
    var guard = 0;
    while (menus.scrollWidth > menus.clientWidth && links.length > 1 && guard < 40) {
      guard += 1;
      var victim = links.pop();
      var item = document.createElement('li');
      victim.classList.add('dropdown-item');
      item.appendChild(victim);
      list.insertBefore(item, list.firstChild);
      more.classList.remove('d-none');
    }
  }

  if (menus) {
    window.addEventListener('resize', O.debounce(reflowMenus, 150));
    reflowMenus();
  }
})(window, document);

/* ============================================================================
   Kanban sürükle-bırak.

   Kütüphane yok (build adımı yok). Pointer Events kullanılır: HTML5 drag&drop
   dokunmatikte çalışmaz, Pointer Events hem farede hem dokunmada çalışır.
     · fare      -> 5px hareket sürüklemeyi başlatır
     · dokunmatik-> 250ms basılı tutma başlatır (yoksa panoyu kaydıramazsınız)

   Sunucu sözleşmesi:
     [data-o-kanban][data-o-kanban-url="/x/__pk__/set-stage/"]
     [data-o-kanban-col][data-o-kanban-value="<aşama>"]
     [data-o-kanban-card][data-o-kanban-id="<pk>"]
     [data-o-kanban-readonly="<sebep>"]   -> pano salt okunur

   İyimser taşıma yapılır; sunucu 400 dönerse kart ESKİ YERİNE geri alınır ve
   sunucunun mesajı toast olarak gösterilir. Aşama geçişleri her zaman ilgili
   servis katmanından geçtiği için iş kuralları atlanamaz.
   ========================================================================== */
(function (window, document) {
  'use strict';

  var HOLD_MS = 250;      // dokunmatikte sürüklemeyi başlatan basılı tutma
  var MOVE_PX = 5;        // farede sürüklemeyi başlatan hareket eşiği

  var drag = null;        // aktif sürükleme durumu

  function boardOf(el) { return el.closest('[data-o-kanban]'); }

  function isInteractive(el) {
    return !!el.closest('a, button, input, select, textarea, form, label');
  }

  function cards(col) { return O.$$('[data-o-kanban-card]', col); }

  function refreshCounts(board) {
    O.$$('[data-o-kanban-col]', board).forEach(function (col) {
      var badge = col.querySelector('.o-kanban-count');
      if (badge) badge.textContent = cards(col).length;
      var empty = col.querySelector('.o-kanban-empty');
      if (empty) empty.hidden = cards(col).length > 0;
    });
  }

  function clearTargets(board) {
    O.$$('[data-o-kanban-col]', board).forEach(function (c) {
      c.classList.remove('o-drop-target');
    });
  }

  function columnAt(board, x, y) {
    var found = null;
    O.$$('[data-o-kanban-col]', board).forEach(function (col) {
      var r = col.getBoundingClientRect();
      if (x >= r.left && x <= r.right && y >= r.top && y <= r.bottom) found = col;
    });
    return found;
  }

  function begin(state) {
    var card = state.card;
    var rect = card.getBoundingClientRect();

    var ghost = card.cloneNode(true);
    ghost.classList.add('o-kanban-ghost');
    ghost.style.width = rect.width + 'px';
    ghost.style.left = rect.left + 'px';
    ghost.style.top = rect.top + 'px';
    document.body.appendChild(ghost);

    card.classList.add('o-kanban-dragging');
    document.body.classList.add('o-kanban-dragging-active');

    state.ghost = ghost;
    state.dx = state.startX - rect.left;
    state.dy = state.startY - rect.top;
    state.origin = card.parentElement;
    state.originNext = card.nextElementSibling;
    state.active = true;
  }

  function moveGhost(state, x, y) {
    state.ghost.style.left = (x - state.dx) + 'px';
    state.ghost.style.top = (y - state.dy) + 'px';
  }

  function finish(state, commit) {
    if (state.timer) window.clearTimeout(state.timer);
    if (!state.active) { drag = null; return; }

    if (state.ghost) state.ghost.remove();
    state.card.classList.remove('o-kanban-dragging');
    document.body.classList.remove('o-kanban-dragging-active');
    clearTargets(state.board);

    var target = commit ? state.target : null;
    drag = null;

    if (!target || target === state.origin.closest('[data-o-kanban-col]')) return;

    var body = target.querySelector('[data-o-kanban-body]') || target;
    var placeholder = body.querySelector('.o-kanban-empty');
    if (placeholder) body.insertBefore(state.card, placeholder);
    else body.appendChild(state.card);
    refreshCounts(state.board);

    var url = state.board.getAttribute('data-o-kanban-url')
                .replace('__pk__', state.card.getAttribute('data-o-kanban-id'));
    var value = target.getAttribute('data-o-kanban-value');

    var data = new FormData();
    data.append('stage', value);

    state.card.classList.add('o-kanban-saving');
    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': O.csrfToken(), 'X-Requested-With': 'XMLHttpRequest' },
      body: data
    })
      .then(function (r) {
        return r.json().catch(function () { return {ok: r.ok}; })
                .then(function (payload) { return {status: r.status, payload: payload}; });
      })
      .then(function (res) {
        state.card.classList.remove('o-kanban-saving');
        if (res.status >= 200 && res.status < 300 && res.payload.ok !== false) {
          // Sunucu yan etki üretmiş olabilir (ör. kazanılan fırsat taslak
          // sipariş doğurur); sayımların doğru olması için bölgeyi tazele.
          O.emit('o:kanban-moved', {card: state.card, value: value});
          return;
        }
        revert(state);
        O.toast(res.payload.error || O.text('msgMoveFailed', 'Taşıma başarısız oldu.'), 'error');
      })
      .catch(function () {
        state.card.classList.remove('o-kanban-saving');
        revert(state);
        O.toast(O.text('msgMoveFailed', 'Taşıma başarısız oldu.'), 'error');
      });
  }

  function revert(state) {
    if (state.originNext) state.origin.insertBefore(state.card, state.originNext);
    else state.origin.appendChild(state.card);
    refreshCounts(state.board);
  }

  document.addEventListener('pointerdown', function (event) {
    if (event.button !== 0 && event.pointerType === 'mouse') return;

    var card = event.target.closest ? event.target.closest('[data-o-kanban-card]') : null;
    if (!card || isInteractive(event.target)) return;

    var board = boardOf(card);
    if (!board || board.hasAttribute('data-o-kanban-readonly')) return;

    var state = {
      card: card, board: board, target: null, active: false,
      startX: event.clientX, startY: event.clientY,
      pointerId: event.pointerId, touch: event.pointerType !== 'mouse'
    };
    drag = state;

    if (state.touch) {
      // Dokunmatikte hemen başlatmak panonun kaydırılmasını imkânsız kılar.
      state.timer = window.setTimeout(function () {
        if (drag === state) { begin(state); moveGhost(state, state.startX, state.startY); }
      }, HOLD_MS);
    }
  });

  document.addEventListener('pointermove', function (event) {
    var state = drag;
    if (!state || event.pointerId !== state.pointerId) return;

    if (!state.active) {
      if (state.touch) {
        // Basılı tutma dolmadan parmak kaydıysa bu bir kaydırmadır.
        if (Math.abs(event.clientX - state.startX) > MOVE_PX ||
            Math.abs(event.clientY - state.startY) > MOVE_PX) {
          window.clearTimeout(state.timer); drag = null;
        }
        return;
      }
      if (Math.abs(event.clientX - state.startX) < MOVE_PX &&
          Math.abs(event.clientY - state.startY) < MOVE_PX) return;
      begin(state);
    }

    event.preventDefault();
    moveGhost(state, event.clientX, event.clientY);

    var col = columnAt(state.board, event.clientX, event.clientY);
    if (col !== state.target) {
      clearTargets(state.board);
      state.target = col;
      if (col) col.classList.add('o-drop-target');
    }
  }, {passive: false});

  document.addEventListener('pointerup', function (event) {
    if (drag && event.pointerId === drag.pointerId) finish(drag, true);
  });
  document.addEventListener('pointercancel', function () { if (drag) finish(drag, false); });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && drag) finish(drag, false);
  });

  // Salt okunur panolarda sebebi bir kez göster.
  function explainReadonly(scope) {
    O.$$('[data-o-kanban-readonly]', scope || document).forEach(function (board) {
      if (board.dataset.oReadonlyShown === '1') return;
      board.dataset.oReadonlyShown = '1';
      var note = document.createElement('p');
      note.className = 'o-kanban-note';
      note.innerHTML = '<i class="bi bi-info-circle" aria-hidden="true"></i> ' +
                       board.getAttribute('data-o-kanban-readonly');
      board.parentNode.insertBefore(note, board);
    });
  }

  document.addEventListener('DOMContentLoaded', function () { explainReadonly(); });
  O.on('o:region-replaced', function (e) { explainReadonly(e.detail.region); });
})(window, document);

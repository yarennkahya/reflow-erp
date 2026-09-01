/* ============================================================================
   AI sohbet sayfası.
   POST /api/ai/chat/   {message, conversation_id} -> {answer, conversation_id}
   POST /api/ai/upload/ multipart {file}           -> {filename, chars, text}
   ========================================================================== */
(function (window, document) {
  'use strict';

  var form = document.getElementById('o-chat-form');
  if (!form) return;

  var feed        = document.getElementById('o-chat-feed');
  var input       = document.getElementById('o-chat-input');
  var welcome     = document.getElementById('o-chat-welcome');
  var pillsEl     = document.getElementById('o-chat-file-pills');
  var attachBtn   = document.getElementById('o-chat-attach');
  var fileInput   = document.getElementById('o-chat-file-input');
  var dropOverlay = document.getElementById('o-chat-drop-overlay');
  var chatMain    = form.closest('.o-chat-main');

  var url       = form.getAttribute('data-o-chat-url');
  var uploadUrl = form.getAttribute('data-o-upload-url');
  var conversationId = form.getAttribute('data-o-conversation-id') || null;

  /* ── Attached files: [{filename, text}] ─────────────────────────────── */
  var attachedFiles = [];

  /* ── Render message bubble ───────────────────────────────────────────── */
  function render(role, content, asMarkdown) {
    if (welcome) { welcome.remove(); welcome = null; }

    var msg = document.createElement('div');
    msg.className = 'o-chat-msg' + (role === 'user' ? ' o-chat-msg--user' : '');

    var avatar = document.createElement('span');
    avatar.className = 'o-chat-avatar';
    avatar.innerHTML = role === 'user'
      ? '<i class="bi bi-person-fill"></i>' : '<i class="bi bi-robot"></i>';

    var bubble = document.createElement('div');
    bubble.className = 'o-chat-bubble';
    if (asMarkdown && window.marked) {
      bubble.innerHTML = window.marked.parse(content);
    } else {
      bubble.textContent = content;
    }

    msg.appendChild(avatar);
    msg.appendChild(bubble);
    feed.appendChild(msg);
    feed.scrollTop = feed.scrollHeight;
    return bubble;
  }

  /* ── Restore history from JSON island ───────────────────────────────── */
  var island = document.getElementById('o-chat-initial');
  if (island) {
    try {
      JSON.parse(island.textContent || '[]').forEach(function (m) {
        render(m.role, m.content, m.role === 'assistant');
      });
    } catch (e) { /* boş geçmiş */ }
  }

  /* ── Textarea auto-grow ──────────────────────────────────────────────── */
  function autoGrow() {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  }
  input.addEventListener('input', autoGrow);

  input.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  /* ── Suggestion chips ────────────────────────────────────────────────── */
  document.addEventListener('click', function (event) {
    var chip = event.target.closest ? event.target.closest('.o-chat-chip') : null;
    if (!chip) return;
    input.value = chip.textContent.trim();
    autoGrow();
    input.focus();
  });

  /* ── File pill management ────────────────────────────────────────────── */
  function addPill(filename, index) {
    var pill = document.createElement('span');
    pill.className = 'o-chat-file-pill o-chat-file-pill--loading';
    pill.dataset.idx = index;

    var icon = document.createElement('i');
    icon.className = 'bi bi-file-earmark-text';
    icon.setAttribute('aria-hidden', 'true');

    var name = document.createElement('span');
    name.className = 'o-chat-file-pill-name';
    name.textContent = filename;

    var removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'o-chat-file-pill-remove';
    removeBtn.setAttribute('aria-label', 'Kaldır');
    removeBtn.innerHTML = '<i class="bi bi-x" aria-hidden="true"></i>';
    removeBtn.addEventListener('click', function () {
      attachedFiles.splice(parseInt(pill.dataset.idx, 10), 1);
      pill.remove();
      refreshPillIndices();
    });

    pill.appendChild(icon);
    pill.appendChild(name);
    pill.appendChild(removeBtn);
    pillsEl.appendChild(pill);
    return pill;
  }

  function refreshPillIndices() {
    Array.from(pillsEl.children).forEach(function (p, i) { p.dataset.idx = i; });
  }

  /* ── Upload a File object ────────────────────────────────────────────── */
  function uploadFile(file) {
    var index = attachedFiles.length;
    attachedFiles.push(null);
    var pill = addPill(file.name, index);

    var fd = new FormData();
    fd.append('file', file);

    fetch(uploadUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': O.csrfToken() },
      body: fd,
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) {
          pill.remove();
          attachedFiles.splice(index, 1);
          refreshPillIndices();
          alert(data.error);
          return;
        }
        attachedFiles[index] = { filename: data.filename, text: data.text };
        pill.classList.remove('o-chat-file-pill--loading');
        var icon = pill.querySelector('i');
        if (icon) icon.className = 'bi bi-file-earmark-check';
      })
      .catch(function () {
        pill.remove();
        attachedFiles.splice(index, 1);
        refreshPillIndices();
        alert('Dosya yüklenemedi.');
      });
  }

  /* ── Paperclip button ────────────────────────────────────────────────── */
  if (attachBtn && fileInput) {
    attachBtn.addEventListener('click', function () { fileInput.click(); });
    fileInput.addEventListener('change', function () {
      Array.from(fileInput.files).forEach(uploadFile);
      fileInput.value = '';
    });
  }

  /* ── Drag & drop on .o-chat-main ─────────────────────────────────────── */
  var dragDepth = 0;

  function showOverlay() {
    if (dropOverlay) { dropOverlay.classList.add('is-active'); dropOverlay.removeAttribute('aria-hidden'); }
  }
  function hideOverlay() {
    if (dropOverlay) { dropOverlay.classList.remove('is-active'); dropOverlay.setAttribute('aria-hidden', 'true'); }
  }

  if (chatMain) {
    chatMain.addEventListener('dragenter', function (e) {
      if (!e.dataTransfer.types.includes('Files')) return;
      e.preventDefault();
      dragDepth++;
      showOverlay();
    });

    chatMain.addEventListener('dragover', function (e) {
      if (!e.dataTransfer.types.includes('Files')) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
    });

    chatMain.addEventListener('dragleave', function (e) {
      dragDepth--;
      if (dragDepth <= 0) { dragDepth = 0; hideOverlay(); }
    });

    chatMain.addEventListener('drop', function (e) {
      e.preventDefault();
      dragDepth = 0;
      hideOverlay();
      var files = e.dataTransfer.files;
      if (!files.length) return;
      Array.from(files).forEach(uploadFile);
    });
  }

  /* ── Form submit ─────────────────────────────────────────────────────── */
  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var userText = input.value.trim();
    if (!userText && !attachedFiles.some(Boolean)) return;

    var ready = attachedFiles.filter(Boolean);
    var pending = attachedFiles.filter(function (f) { return f === null; });
    if (pending.length) {
      alert('Dosyalar henüz yükleniyor, lütfen bekleyin.');
      return;
    }

    var contextBlocks = ready.map(function (f) {
      return '=== Dosya: ' + f.filename + ' ===\n' + f.text;
    });

    var fullMessage = userText;
    if (contextBlocks.length) {
      fullMessage = contextBlocks.join('\n\n') + '\n\n---\n\n' + (userText || '');
    }

    var displayText = userText || ready.map(function (f) { return '📎 ' + f.filename; }).join(', ');
    render('user', displayText, false);

    input.value = ''; autoGrow();
    attachedFiles = [];
    pillsEl.innerHTML = '';

    var typing = render('assistant', '', false);
    typing.innerHTML = '<span class="o-typing"><i></i><i></i><i></i></span>';

    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': O.csrfToken() },
      body: JSON.stringify({ message: fullMessage, conversation_id: conversationId }),
    })
      .then(function (r) { if (!r.ok) throw new Error('chat'); return r.json(); })
      .then(function (data) {
        typing.innerHTML = window.marked ? window.marked.parse(data.answer || '') : '';
        if (!window.marked) typing.textContent = data.answer || '';
        if (data.conversation_id) conversationId = String(data.conversation_id);
        feed.scrollTop = feed.scrollHeight;
      })
      .catch(function () {
        typing.textContent = O.text('msgChatFailed', 'Yanıt alınamadı. Lütfen tekrar deneyin.');
        typing.classList.add('o-chat-bubble--error');
      });
  });
})(window, document);

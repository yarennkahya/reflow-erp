/* ============================================================================
   AI sohbet sayfası. Sunucu sözleşmesi değişmedi:
   POST /api/ai/chat/  {message, conversation_id} -> {answer, conversation_id}
   ========================================================================== */
(function (window, document) {
  'use strict';

  var form = document.getElementById('o-chat-form');
  if (!form) return;

  var feed = document.getElementById('o-chat-feed');
  var input = document.getElementById('o-chat-input');
  var welcome = document.getElementById('o-chat-welcome');
  var url = form.getAttribute('data-o-chat-url');
  var conversationId = form.getAttribute('data-o-conversation-id') || null;

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
      bubble.innerHTML = window.marked.parse(content);   // yalnız asistan yanıtı
    } else {
      bubble.textContent = content;                      // kullanıcı metni ASLA HTML değil
    }

    msg.appendChild(avatar);
    msg.appendChild(bubble);
    feed.appendChild(msg);
    feed.scrollTop = feed.scrollHeight;
    return bubble;
  }

  // Sunucudan gelen geçmiş
  var island = document.getElementById('o-chat-initial');
  if (island) {
    try {
      JSON.parse(island.textContent || '[]').forEach(function (m) {
        render(m.role, m.content, m.role === 'assistant');
      });
    } catch (e) { /* boş geçmiş */ }
  }

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

  document.addEventListener('click', function (event) {
    var chip = event.target.closest ? event.target.closest('.o-chat-chip') : null;
    if (!chip) return;
    input.value = chip.textContent.trim();
    autoGrow();
    input.focus();
  });

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var message = input.value.trim();
    if (!message) return;

    render('user', message, false);
    input.value = ''; autoGrow();

    var typing = render('assistant', '', false);
    typing.innerHTML = '<span class="o-typing"><i></i><i></i><i></i></span>';

    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': O.csrfToken() },
      body: JSON.stringify({ message: message, conversation_id: conversationId })
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

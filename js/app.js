/* =========================================================
   1. ТЕМА (работает на всех страницах)
   ========================================================= */
(function initTheme() {
  const KEY = 'flora-theme';
  const btn = document.getElementById('themeToggle');

  function apply(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(KEY, theme);
    if (btn) btn.textContent = theme === 'dark' ? '☀️' : '🌙';
  }

  if (btn) {
    btn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      apply(current === 'dark' ? 'light' : 'dark');
    });
  }

  apply(document.documentElement.getAttribute('data-theme') || 'light');
})();


/* =========================================================
   2. ТОСТ
   ========================================================= */
function showToast(message) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = message;
  document.body.appendChild(el);
  requestAnimationFrame(() => el.classList.add('show'));
  setTimeout(() => {
    el.classList.remove('show');
    setTimeout(() => el.remove(), 320);
  }, 2600);
}


/* =========================================================
   3. ГЛАВНЫЙ ЧАТ (index.html) — реальная интеграция с API
   ========================================================= */
(function initChat() {
  const listEl = document.getElementById('chatList');
  if (!listEl) return;

  const messagesEl = document.getElementById('messages');
  const form = document.getElementById('composerForm');
  const input = document.getElementById('composerInput');
  const newChatBtn = document.getElementById('newChatBtn');
  const sendBtn = document.getElementById('sendBtn');
  const serviceStatus = document.getElementById('serviceStatus');
  const photoBtn = document.getElementById('photoBtn');
  const photoInput = document.getElementById('photoInput');
  const photoPanel = document.getElementById('photoPanel');
  const photoPreview = document.getElementById('photoPreview');
  const photoName = document.getElementById('photoName');
  const identifyBtn = document.getElementById('identifyBtn');
  const cancelPhotoBtn = document.getElementById('cancelPhotoBtn');
  const API_BASE = `${(document.querySelector('meta[name="api-base-url"]')?.content || '').replace(/\/$/, '')}/api/v1`;
  const CHATS_KEY = 'bestiary-chats-v1';
  const ACTIVE_KEY = 'bestiary-active-chat-v1';

  function loadChats() {
    try {
      const value = JSON.parse(localStorage.getItem(CHATS_KEY) || '[]');
      return Array.isArray(value) ? value.filter(chat => chat && Array.isArray(chat.messages)) : [];
    } catch (_) {
      return [];
    }
  }

  let chats = loadChats();
  if (!chats.length) chats = [{ id: Date.now(), title: 'Новый чат', time: 'Сейчас', messages: [] }];
  let activeId = Number(localStorage.getItem(ACTIVE_KEY)) || chats[0].id;
  if (!chats.some(chat => chat.id === activeId)) activeId = chats[0].id;
  let nextId = Math.max(Date.now(), ...chats.map(chat => Number(chat.id) || 0)) + 1;
  let busy = false;
  let selectedFile = null;
  let previewUrl = null;

  function saveChats() {
    try {
      localStorage.setItem(CHATS_KEY, JSON.stringify(chats.slice(0, 50)));
      localStorage.setItem(ACTIVE_KEY, String(activeId));
    } catch (_) {
      showToast('Не удалось сохранить историю чатов в браузере.');
    }
  }

  function activeChat() {
    return chats.find(chat => chat.id === activeId);
  }

  function renderList() {
    listEl.replaceChildren();
    chats.forEach((chat, index) => {
      const li = document.createElement('li');
      li.className = 'chat-item' + (chat.id === activeId ? ' active' : '');
      li.style.animationDelay = `${index * 30}ms`;
      const title = document.createElement('span');
      title.className = 'chat-item-title';
      title.textContent = chat.title || 'Новый чат';
      const time = document.createElement('span');
      time.className = 'chat-item-time';
      time.textContent = chat.time || '';
      li.append(title, time);
      li.tabIndex = 0;
      li.setAttribute('role', 'button');
      li.setAttribute('aria-current', chat.id === activeId ? 'true' : 'false');
      const activate = () => {
        activeId = chat.id;
        saveChats();
        renderList();
        renderMessages();
      };
      li.addEventListener('click', activate);
      li.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(); }
      });
      listEl.appendChild(li);
    });
  }

  function addSourceList(container, sources) {
    if (!Array.isArray(sources) || !sources.length) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'source-list';
    const heading = document.createElement('strong');
    heading.textContent = 'Источники и фрагменты';
    wrapper.appendChild(heading);
    sources.forEach(source => {
      const item = document.createElement('div');
      item.className = 'source-item';
      const title = document.createElement('span');
      title.className = 'source-item-title';
      title.textContent = `[${source.source_ref || 'Источник'}] ${source.title || source.document_id || 'Материал'}`;
      item.appendChild(title);
      if (source.scientific_name) {
        const latin = document.createElement('em');
        latin.textContent = source.scientific_name;
        item.appendChild(latin);
      }
      const sourceTitle = document.createElement('small');
      sourceTitle.textContent = source.source_title || 'Название источника не указано';
      item.appendChild(sourceTitle);
      if (source.snippet) {
        const snippet = document.createElement('p');
        snippet.className = 'source-snippet';
        snippet.textContent = source.snippet;
        item.appendChild(snippet);
      }
      if (source.record_status === 'demo_unverified') {
        const warning = document.createElement('small');
        warning.className = 'source-warning';
        warning.textContent = 'Демонстрационная запись: требует фактчекинга';
        item.appendChild(warning);
      }
      if (source.source_url) {
        try {
          const url = new URL(source.source_url);
          if (url.protocol === 'https:' || url.protocol === 'http:') {
            const link = document.createElement('a');
            link.href = url.href;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = 'Открыть первоисточник ↗';
            item.appendChild(link);
          }
        } catch (_) { /* malformed source URLs are omitted */ }
      }
      wrapper.appendChild(item);
    });
    container.appendChild(wrapper);
  }

  function renderIdentification(container, message) {
    const note = document.createElement('p');
    note.textContent = message.message || 'Это предварительные варианты определения.';
    container.appendChild(note);
    const candidates = document.createElement('div');
    candidates.className = 'plant-candidates';
    (message.candidates || []).forEach(candidate => {
      const card = document.createElement('div');
      card.className = 'plant-candidate';
      const name = document.createElement('strong');
      name.textContent = (candidate.common_names || [])[0] || candidate.scientific_name || 'Неизвестный вид';
      const scientific = document.createElement('em');
      scientific.textContent = candidate.scientific_name || '';
      const score = document.createElement('small');
      score.textContent = Number.isFinite(candidate.score) ? `Оценка сервиса: ${(candidate.score * 100).toFixed(1)}% (не вероятность)` : 'Оценка сервиса не указана';
      const choose = document.createElement('button');
      choose.type = 'button';
      choose.textContent = 'Искать сведения об этом растении';
      choose.addEventListener('click', () => {
        const queryName = (candidate.common_names || [])[0] || candidate.scientific_name;
        if (queryName) sendQuestion(`Расскажи о растении ${queryName} по материалам базы.`);
      });
      card.append(name, scientific, score, choose);
      candidates.appendChild(card);
    });
    container.appendChild(candidates);
  }

  function addBubble(message, animate = true) {
    const emptyState = messagesEl.querySelector('.empty-state');
    if (emptyState) emptyState.remove();
    const from = message.from || 'bot';
    const div = document.createElement('div');
    div.className = `msg ${from}`;
    if (!animate) div.style.animation = 'none';
    if (message.kind === 'identify') {
      renderIdentification(div, message);
    } else {
      const text = document.createElement('div');
      text.className = 'message-text';
      text.textContent = message.text || '';
      div.appendChild(text);
      if (message.warning) {
        const warning = document.createElement('div');
        warning.className = 'message-warning';
        warning.textContent = message.warning;
        div.appendChild(warning);
      }
      if (message.meta) {
        const meta = document.createElement('small');
        meta.className = 'message-meta';
        meta.textContent = message.meta;
        div.appendChild(meta);
      }
      addSourceList(div, message.sources);
    }
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
  }

  function renderMessages() {
    const chat = activeChat();
    messagesEl.replaceChildren();
    if (!chat || chat.messages.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'empty-state';
      empty.innerHTML = '<div class="empty-icon">🌿</div><h2>О каком растении хотите узнать?</h2><p>Задайте вопрос по внутренней базе знаний или загрузите фотографию для предварительного распознавания.</p>';
      messagesEl.appendChild(empty);
      return;
    }
    chat.messages.forEach(message => addBubble(message, false));
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function setBusy(value) {
    busy = value;
    sendBtn.disabled = value;
    identifyBtn.disabled = value;
    photoBtn.disabled = value;
    input.disabled = value;
    sendBtn.setAttribute('aria-busy', value ? 'true' : 'false');
  }

  async function sendQuestion(rawText) {
    const text = String(rawText || '').trim();
    if (!text || busy) return;
    const chat = activeChat();
    if (!chat) return;
    if (!chat.messages.length) {
      chat.title = text.length > 28 ? `${text.slice(0, 28)}…` : text;
      chat.time = 'Сейчас';
    }
    chat.messages.push({ from: 'user', text });
    saveChats();
    renderList();
    renderMessages();
    input.value = '';
    setBusy(true);
    const loader = addBubble({ from: 'bot', text: 'Ищу материалы в базе знаний и формирую ответ…' });
    try {
      const response = await fetch(`${API_BASE}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text, limit: 5 })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail?.message || data.detail || 'Сервис вернул ошибку.');
      loader.remove();
      const retrieval = data.retrieval || {};
      const modeLabel = data.generation_mode === 'agentic_rag' ? 'Agentic RAG' :
        data.generation_mode === 'rag' ? 'RAG' : data.generation_mode === 'retrieval_only' ? 'Только поиск BM25' : 'Поиск';
      const calls = retrieval.tool_calls ? ` · дополнительных запросов: ${retrieval.tool_calls}` : '';
      chat.messages.push({
        from: 'bot', text: data.answer, sources: data.sources || [], warning: data.warning || '',
        meta: `${modeLabel} · фрагментов: ${retrieval.total_context_chunks || 0}${calls}`
      });
      saveChats();
      renderMessages();
    } catch (error) {
      loader.remove();
      chat.messages.push({ from: 'bot', text: `Не удалось получить ответ от сервера. ${error.message || 'Проверьте, запущен ли backend.'}` });
      saveChats();
      renderMessages();
    } finally {
      setBusy(false);
      input.focus();
    }
  }

  async function identifySelectedImage() {
    if (!selectedFile || busy) return;
    if (selectedFile.size > 10 * 1024 * 1024) {
      showToast('Изображение должно быть меньше 10 МБ.');
      return;
    }
    setBusy(true);
    identifyBtn.textContent = 'Распознавание…';
    const chat = activeChat();
    const loader = addBubble({ from: 'bot', text: 'Передаю изображение в сервис распознавания…' });
    try {
      const formData = new FormData();
      formData.append('image', selectedFile);
      const response = await fetch(`${API_BASE}/identify`, { method: 'POST', body: formData });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail?.message || data.detail || 'Не удалось распознать изображение.');
      loader.remove();
      chat.messages.push({ from: 'bot', kind: 'identify', message: data.message, candidates: data.candidates || [] });
      saveChats();
      renderMessages();
      clearSelectedImage();
    } catch (error) {
      loader.remove();
      chat.messages.push({ from: 'bot', text: `Распознавание недоступно. ${error.message || ''}` });
      saveChats();
      renderMessages();
    } finally {
      setBusy(false);
      identifyBtn.textContent = 'Распознать растение';
    }
  }

  function clearSelectedImage() {
    selectedFile = null;
    photoInput.value = '';
    photoPanel.hidden = true;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    photoPreview.removeAttribute('src');
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    sendQuestion(input.value);
  });

  newChatBtn.addEventListener('click', () => {
    const id = nextId++;
    chats.unshift({ id, title: 'Новый чат', time: 'Сейчас', messages: [] });
    activeId = id;
    saveChats();
    renderList();
    renderMessages();
    input.focus();
  });

  photoBtn.addEventListener('click', () => photoInput.click());
  photoInput.addEventListener('change', () => {
    const file = photoInput.files?.[0];
    if (!file) return;
    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      showToast('Поддерживаются JPEG и PNG.');
      photoInput.value = '';
      return;
    }
    selectedFile = file;
    photoName.textContent = file.name;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(file);
    photoPreview.src = previewUrl;
    photoPanel.hidden = false;
  });
  identifyBtn.addEventListener('click', identifySelectedImage);
  cancelPhotoBtn.addEventListener('click', clearSelectedImage);

  fetch(`${API_BASE}/config`).then(response => {
    if (!response.ok) throw new Error('API unavailable');
    return response.json();
  }).then(config => {
    const provider = config.llm_configured ? `${config.llm_provider} · ${config.llm_model}` : 'LLM не настроена';
    const plantnet = config.identification_configured ? ' · распознавание фото доступно' : ' · фото не настроено';
    serviceStatus.textContent = `База подключена · BM25 · ${provider}${plantnet}`;
  }).catch(() => {
    serviceStatus.textContent = 'Backend не подключён. Запустите сервер по инструкции в README.';
  });

  renderList();
  renderMessages();
  input.focus();
})();


/* =========================================================
   4. ВАЛИДАЦИЯ ФОРМ (register.html / login.html)
   ========================================================= */

/* правила из ТЗ */
const RULES = {
  name: {
    test(v) {
      const errors = [];
      if (v.length < 3 || v.length > 30)
        errors.push('Имя должно содержать от 3 до 30 символов.');
      if (v && !/^[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё\s'-]*$/.test(v))
        errors.push('Имя должно содержать только буквы, пробел, дефис или апостроф.');
      return errors;
    }
  },
  login: {
    test(v) {
      const errors = [];
      if (v.length < 3 || v.length > 30)
        errors.push('Логин должен содержать от 3 до 30 символов.');
      if (v && !/^[A-Za-z0-9_-]+$/.test(v))
        errors.push('Логин должен содержать только латинские буквы, цифры, дефис или подчеркивание.');
      return errors;
    }
  },
  password: {
    test(v) {
      const errors = [];
      if (v.length < 5 || v.length > 20)
        errors.push('Пароль должен содержать от 5 до 20 символов.');
      if (v && !/^[A-Za-z0-9]+$/.test(v))
        errors.push('Пароль должен содержать только цифры и латинские буквы.');
      return errors;
    }
  }
};

/* навешиваем валидацию на форму, если она есть на странице */
(function initForms() {

  function setupForm(formId, onSuccess) {
    const form = document.getElementById(formId);
    if (!form) return;

    const fields = form.querySelectorAll('.field');

    fields.forEach(field => {
      const key   = field.dataset.field;
      const input = field.querySelector('input');
      if (!input || !RULES[key]) return;

      // живая перепроверка после первой неудачной попытки
      input.addEventListener('input', () => {
        if (field.classList.contains('error')) validateField(field, true);
      });
    });

    form.addEventListener('submit', e => {
      e.preventDefault();
      let ok = true;

      fields.forEach(field => {
        if (!validateField(field, false)) ok = false;
      });

      if (ok) onSuccess(form);
    });
  }

  function validateField(field, live) {
    const key   = field.dataset.field;
    const input = field.querySelector('input');
    const box   = field.querySelector('.error-text');
    if (!input || !RULES[key]) return true;

    const errors = RULES[key].test(input.value.trim());

    if (errors.length) {
      field.classList.add('error');
      box.innerHTML = errors.map(e => `<span>${e}</span>`).join('');
      return false;
    } else {
      field.classList.remove('error');
      box.innerHTML = '';
      return true;
    }
  }

  /* --- РЕГИСТРАЦИЯ --- */
  setupForm('registerForm', () => {
    showToast('Регистрация прошла успешно! Переходим в чат...');
    setTimeout(() => { window.location.href = 'index.html'; }, 1200);
  });

  /* --- ВХОД --- */
  setupForm('loginForm', () => {
    showToast('Вход выполнен! Переходим в чат...');
    setTimeout(() => { window.location.href = 'index.html'; }, 1200);
  });

  /* --- "забыли пароль?" --- */
  const forgot = document.getElementById('forgotLink');
  if (forgot) {
    forgot.addEventListener('click', e => {
      e.preventDefault();
      showToast('Ссылка для восстановления пароля отправлена на почту');
    });
  }

})();
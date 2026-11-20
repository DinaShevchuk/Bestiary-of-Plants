(function () {
  const $ = (id) => document.getElementById(id);
  const STORAGE = { users: 'flora-admin-users', plants: 'flora-admin-plants' };
  const defaults = {
    users: [
      { id: 1, name: 'Екатерина Смирнова', login: 'katya_s', role: 'Пользователь', status: 'Активен' },
      { id: 2, name: 'Алексей Морозов', login: 'alex_m', role: 'Пользователь', status: 'Активен' },
      { id: 3, name: 'Администратор', login: 'admin', role: 'Администратор', status: 'Активен' }
    ],
    plants: [
      { id: 1, name: 'Венерина мухоловка', extra: 'Dionaea muscipula', description: 'Хищное растение с подвижными ловушками на концах листьев.' },
      { id: 2, name: 'Росянка', extra: 'Drosera', description: 'Насекомоядное растение, листья которого покрыты клейкими железистыми волосками.' },
      { id: 3, name: 'Раффлезия', extra: 'Rafflesia', description: 'Род паразитических растений, известный крупными цветками.' }
    ]
  };
  const load = (key) => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE[key]));
      return Array.isArray(saved) ? saved : defaults[key].slice();
    } catch (_) { return defaults[key].slice(); }
  };
  let users = load('users');
  let plants = load('plants');
  let editing = null;
  let entityType = 'users';

  function persist() {
    localStorage.setItem(STORAGE.users, JSON.stringify(users));
    localStorage.setItem(STORAGE.plants, JSON.stringify(plants));
    $('statUsers').textContent = users.length;
    $('statPlants').textContent = plants.length;
  }
  function safe(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  }
  function renderUsers() {
    const query = $('userSearch').value.trim().toLowerCase();
    const filtered = users.filter(u => `${u.name} ${u.login}`.toLowerCase().includes(query));
    $('userCount').textContent = `${filtered.length} из ${users.length}`;
    $('usersTable').innerHTML = filtered.map(u => `<tr><td><b>${safe(u.name)}</b></td><td>${safe(u.login)}</td><td>${safe(u.role)}</td><td><span class="table-status ${u.status === 'Активен' ? 'is-active' : 'is-blocked'}">${safe(u.status)}</span></td><td><div class="row-actions"><button data-action="toggle" data-id="${u.id}">${u.status === 'Активен' ? 'Заблокировать' : 'Разблокировать'}</button><button data-action="edit" data-id="${u.id}">Изменить</button><button class="danger-action" data-action="delete" data-id="${u.id}">Удалить</button></div></td></tr>`).join('') || '<tr><td colspan="5" class="empty-table">Пользователи не найдены</td></tr>';
  }
  function renderPlants() {
    const query = $('plantSearch').value.trim().toLowerCase();
    const filtered = plants.filter(p => `${p.name} ${p.extra} ${p.description}`.toLowerCase().includes(query));
    $('plantCount').textContent = `${filtered.length} записей`;
    $('plantGrid').innerHTML = filtered.map(p => `<article class="plant-admin-card"><div class="plant-card-icon">❀</div><div class="plant-card-content"><h3>${safe(p.name)}</h3><em>${safe(p.extra)}</em><p>${safe(p.description)}</p><div class="row-actions"><button data-action="edit" data-id="${p.id}">Изменить</button><button class="danger-action" data-action="delete" data-id="${p.id}">Удалить</button></div></div></article>`).join('') || '<p class="empty-table">Растения не найдены</p>';
  }
  function renderChats() {
    const rows = [
      ['Растение похоже на те...', '12:04', '2', 'Демонстрационные данные'],
      ['Трава найдена на поле...', 'Вчера', '1', 'Демонстрационные данные'],
      ['Листья с зубчатым краем', 'Пн', '0', 'Демонстрационные данные']
    ];
    $('chatsTable').innerHTML = rows.map(r => `<tr>${r.map(v => `<td>${safe(v)}</td>`).join('')}</tr>`).join('');
  }
  function showSection(name) {
    document.querySelectorAll('.admin-section').forEach(s => s.classList.toggle('active', s.id === `section-${name}`));
    document.querySelectorAll('.admin-nav a').forEach(a => a.classList.toggle('active', a.dataset.section === name));
    const titles = { overview: 'Обзор', users: 'Пользователи', plants: 'Каталог растений', chats: 'История чатов', about: 'О проекте' };
    $('pageTitle').textContent = titles[name] || 'Обзор';
    if (location.hash !== `#${name}`) history.replaceState(null, '', `#${name}`);
  }
  document.querySelectorAll('.admin-nav a').forEach(a => a.addEventListener('click', e => { e.preventDefault(); showSection(a.dataset.section); }));
  document.querySelectorAll('[data-go]').forEach(b => b.addEventListener('click', () => showSection(b.dataset.go)));
  $('userSearch').addEventListener('input', renderUsers);
  $('plantSearch').addEventListener('input', renderPlants);

  function openDialog(type, item) {
    entityType = type;
    editing = item ? item.id : null;
    const isUser = type === 'users';
    $('dialogEyebrow').textContent = editing ? 'РЕДАКТИРОВАНИЕ' : 'НОВАЯ ЗАПИСЬ';
    $('dialogTitle').textContent = editing ? 'Изменить запись' : (isUser ? 'Добавить пользователя' : 'Добавить растение');
    $('fieldNameLabel').firstChild.textContent = isUser ? 'Имя' : 'Название';
    $('fieldExtraLabel').firstChild.textContent = isUser ? 'Логин' : 'Научное название';
    $('fieldDescriptionLabel').style.display = isUser ? 'none' : 'block';
    $('fieldExtraLabel').style.display = 'block';
    $('fieldName').value = item?.name || '';
    $('fieldExtra').value = isUser ? (item?.login || '') : (item?.extra || '');
    $('fieldDescription').value = item?.description || '';
    $('entityDialog').showModal();
  }
  function closeDialog() { $('entityDialog').close(); }
  $('addUserBtn').addEventListener('click', () => openDialog('users'));
  $('addPlantBtn').addEventListener('click', () => openDialog('plants'));
  $('closeDialog').addEventListener('click', closeDialog);
  $('cancelDialog').addEventListener('click', closeDialog);
  $('entityForm').addEventListener('submit', e => {
    e.preventDefault();
    const name = $('fieldName').value.trim();
    const extra = $('fieldExtra').value.trim();
    if (!name || !extra) return;
    const collection = entityType === 'users' ? users : plants;
    if (entityType === 'users' && collection.some(u => u.login.toLowerCase() === extra.toLowerCase() && u.id !== editing)) {
      alert('Пользователь с таким логином уже существует.'); return;
    }
    if (editing) {
      const item = collection.find(x => x.id === editing);
      Object.assign(item, entityType === 'users' ? { name, login: extra } : { name, extra, description: $('fieldDescription').value.trim() });
    } else {
      const id = Math.max(0, ...collection.map(x => x.id)) + 1;
      collection.push(entityType === 'users' ? { id, name, login: extra, role: 'Пользователь', status: 'Активен' } : { id, name, extra, description: $('fieldDescription').value.trim() });
    }
    persist(); renderUsers(); renderPlants(); closeDialog();
  });
  $('usersTable').addEventListener('click', e => {
    const btn = e.target.closest('button[data-action]'); if (!btn) return;
    const item = users.find(u => u.id === Number(btn.dataset.id)); if (!item) return;
    if (btn.dataset.action === 'edit') openDialog('users', item);
    if (btn.dataset.action === 'toggle') { item.status = item.status === 'Активен' ? 'Заблокирован' : 'Активен'; persist(); renderUsers(); }
    if (btn.dataset.action === 'delete' && confirm(`Удалить пользователя «${item.name}»?`)) { users = users.filter(u => u.id !== item.id); persist(); renderUsers(); }
  });
  $('plantGrid').addEventListener('click', e => {
    const btn = e.target.closest('button[data-action]'); if (!btn) return;
    const item = plants.find(p => p.id === Number(btn.dataset.id)); if (!item) return;
    if (btn.dataset.action === 'edit') openDialog('plants', item);
    if (btn.dataset.action === 'delete' && confirm(`Удалить растение «${item.name}»?`)) { plants = plants.filter(p => p.id !== item.id); persist(); renderPlants(); }
  });
  persist(); renderUsers(); renderPlants(); renderChats();
  showSection(location.hash.slice(1) || 'overview');
})();

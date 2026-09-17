'use strict';
const $ = (id) => document.getElementById(id);
// subject doküman düzenlemesini, searchSubject sohbetin isteğe bağlı filtresini yönetir.
const state = { user: null, subjects: [], subject: null, searchSubject: null, documents: [], view: 'study', busy: false, deleteId: null, timer: null };
const labels = { queued: 'Sırada', processing: 'İşleniyor', ready: 'Hazır', error: 'Hata', deleting: 'Siliniyor', delete_error: 'Silme hatası' };
function node(tag, text, className) { const element = document.createElement(tag); if (text !== undefined) element.textContent = text; if (className) element.className = className; return element; }
function toast(message, error = false) { const box = $('toast'); box.textContent = message; box.className = 'toast' + (error ? ' error' : ''); box.hidden = false; clearTimeout(state.timer); state.timer = setTimeout(() => { box.hidden = true; }, 6500); }
async function api(path, options = {}) {
  const headers = { 'X-Requested-With': 'DersAtlas', ...(options.headers || {}) };
  if (options.body && !(options.body instanceof FormData)) { headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(options.body); }
  const abort = new AbortController();
  const timeout = setTimeout(() => abort.abort(), path === '/api/questions' ? 900000 : 30000);
  try {
    const response = await fetch(path, { ...options, headers, credentials: 'same-origin', signal: abort.signal });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401 && path !== '/api/login') showLogin();
      throw new Error(typeof data.detail === 'string' ? data.detail : 'İstek tamamlanamadı. Alanları ve sistem durumunu kontrol et.');
    }
    return data;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('İstek zaman aşımına uğradı. Sunucudaki işlem sürüyor olabilir; yeniden göndermeden durumu kontrol et.');
    throw error;
  } finally { clearTimeout(timeout); }
}
function currentSubject() { return state.subjects.find(s => s.id === state.subject); }
function searchSubject() { return state.subjects.find(s => s.id === state.searchSubject); }
function scopeName() { return searchSubject()?.name || 'Tüm dersler'; }
function updateChatScope() {
  $('scope-hint').textContent = state.searchSubject
    ? 'Yalnızca ' + scopeName() + ' dersinin erişilebilir, hazır notları aranır.'
    : 'Erişebildiğin tüm derslerin hazır notları aranır. Soldaki seçim yalnızca doküman düzenlemek içindir.';
  $('method-hint').textContent = $('mode').value === 'agent'
    ? 'Ajan alt sorularla ek aramalar yapar. Yalnızca notları okuyabilir; komut çalıştıramaz veya dosya değiştiremez.'
    : 'RAG ilgili notları bulur ve yerel modelle kaynaklı cevap hazırlar.';
  $('send').disabled = state.busy || !state.user || !state.subjects.length;
  if ($('welcome-text')) $('welcome-text').textContent = state.subjects.length
    ? 'Tarih, Coğrafya veya Vatandaşlık: dersi seçmeden sor. İstersen Arama kapsamı filtresini kullan. Her soru bağımsızdır.'
    : 'Önce bir ders oluşturup Dokümanlar bölümünden notlarını ekle.';
  if (state.view === 'study') $('page-title').textContent = state.searchSubject ? scopeName() + ' · Sohbet' : 'Genel Sohbet';
}
function showLogin() {
  state.user = null; state.subjects = []; state.subject = null; state.searchSubject = null; state.documents = [];
  clearChat(); $('question').value = '';
  $('subject-select').replaceChildren(); $('search-subject-select').replaceChildren(node('option', 'Tüm dersler'));
  $('document-rows').replaceChildren(); $('system-cards').replaceChildren(); $('metric-cards').replaceChildren();
  $('login-view').hidden = false; $('app-view').hidden = true; $('password').value = '';
}
function setView(view) {
  state.view = view;
  for (const key of ['study', 'documents', 'system']) $(key + '-view').hidden = key !== view;
  document.querySelectorAll('[data-view]').forEach(button => { button.classList.toggle('active', button.dataset.view === view); if (button.dataset.view === view) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current'); });
  $('page-eyebrow').textContent = { study: 'NOTLARINLA SOHBET', documents: 'DOKÜMAN YÖNETİMİ', system: 'YEREL ALTYAPI' }[view];
  $('page-title').textContent = view === 'system' ? 'Sistem ve ölçümler' : (currentSubject()?.name || 'Bir ders ekle');
  updateChatScope();
  if (view === 'documents') refreshDocuments().catch(e => toast(e.message, true));
  if (view === 'system') refreshSystem().catch(e => toast(e.message, true));
}
async function loadApp(user) {
  if (state.user?.id !== user.id) { state.subject = null; state.searchSubject = null; clearChat(); }
  state.user = user;
  $('login-view').hidden = true; $('app-view').hidden = false;
  $('user-name').textContent = user.username; $('user-avatar').textContent = user.username[0].toLocaleUpperCase('tr');
  $('user-role').textContent = user.role === 'admin' ? 'Ders yöneticisi' : 'Öğrenci · okuma erişimi';
  $('add-subject').hidden = user.role !== 'admin';
  await loadSubjects();
  refreshSystem().catch(e => toast(e.message, true));
}
async function loadSubjects(preferred) {
  const requestUserId = state.user?.id;
  const subjects = await api('/api/subjects');
  if (state.user?.id !== requestUserId) return;
  state.subjects = subjects;
  state.subject = preferred || (state.subjects.some(s => s.id === state.subject) ? state.subject : state.subjects[0]?.id) || null;
  $('subject-select').replaceChildren();
  if (!state.subjects.length) $('subject-select').append(node('option', 'Henüz ders yok'));
  for (const subject of state.subjects) { const option = node('option', subject.name); option.value = subject.id; $('subject-select').append(option); }
  if (state.subject) $('subject-select').value = state.subject;
  if (!state.subjects.some(s => s.id === state.searchSubject)) state.searchSubject = null;
  const all = node('option', 'Tüm dersler'); all.value = '';
  $('search-subject-select').replaceChildren(all);
  for (const subject of state.subjects) { const option = node('option', subject.name); option.value = subject.id; $('search-subject-select').append(option); }
  $('search-subject-select').value = state.searchSubject || '';
  setView(state.view);
  await refreshDocuments();
}
function clearChat() {
  $('messages').replaceChildren();
  const welcome = node('div', undefined, 'welcome');
  const description = node('p'); description.id = 'welcome-text';
  welcome.append(node('span', '01 / KEŞFET', 'section-number'), node('h3', 'Hangi konuyu netleştirelim?'), description);
  $('messages').append(welcome); renderSources([]);
  updateChatScope();
}
function renderSources(sources) {
  $('source-count').textContent = String(sources.length); $('sources').replaceChildren();
  if (!sources.length) { const empty = node('div', undefined, 'source-empty'); empty.append(node('span', '02 / DOĞRULA', 'section-number'), node('h3', 'Henüz kaynak yok.'), node('p', 'Soru gönderdiğinde bulunan metin bölümlerini burada görebilirsin.')); $('sources').append(empty); return; }
  for (const [index, source] of sources.entries()) {
    const card = node('article', undefined, 'source-card');
    card.append(node('span', source.source_id || 'K' + (index + 1), 'source-label'),
      node('p', source.subject_name || 'Ders bilgisi yok', 'source-subject'),
      node('h3', source.filename), node('small', source.location));
    const details = node('details'); details.open = sources.length <= 3;
    details.append(node('summary', 'Kaynak metni oku'), node('p', source.text)); card.append(details);
    const link = node('a', 'Orijinal dokümanı indir'); link.href = '/api/documents/' + encodeURIComponent(source.document_id) + '/download'; card.append(link);
    $('sources').append(card);
  }
}
async function refreshDocuments() {
  const selected = state.subject, requestUserId = state.user?.id;
  const docs = selected ? await api('/api/subjects/' + encodeURIComponent(selected) + '/documents') : [];
  if (selected !== state.subject || state.user?.id !== requestUserId) return;
  state.documents = docs;
  const canWrite = Boolean(currentSubject()?.can_write);
  $('upload-zone').hidden = !canWrite;
  $('document-rows').replaceChildren(); $('doc-empty').hidden = docs.length > 0;
  for (const doc of docs) {
    const row = node('tr'); const nameCell = node('td'); nameCell.append(node('div', doc.filename, 'doc-name'));
    for (const message of [doc.error, doc.warning, doc.needs_reindex ? 'Embedding modeli değişti; yeniden indeksleme gerekiyor.' : '']) if (message) nameCell.append(node('small', message, 'doc-note'));
    const statusCell = node('td'); statusCell.append(node('span', doc.needs_reindex ? 'Yeniden indeksle' : labels[doc.status] || doc.status, 'badge ' + doc.status));
    const actionsCell = node('td'); const actions = node('div', undefined, 'row-actions');
    if (!['deleting', 'delete_error'].includes(doc.status)) { const link = node('a', 'İndir'); link.href = '/api/documents/' + encodeURIComponent(doc.id) + '/download'; actions.append(link); }
    if (canWrite && ['ready', 'error'].includes(doc.status)) { const retry = node('button', 'Yeniden indeksle'); retry.addEventListener('click', () => actionDocument(doc.id, 'reindex')); actions.append(retry); }
    if (canWrite && ['ready', 'error', 'delete_error'].includes(doc.status)) { const remove = node('button', 'Sil'); remove.addEventListener('click', () => { state.deleteId = doc.id; $('delete-description').textContent = doc.filename; $('delete-dialog').showModal(); }); actions.append(remove); }
    actionsCell.append(actions); row.append(nameCell, statusCell, node('td', String(doc.chunk_count)), actionsCell); $('document-rows').append(row);
  }
  // Doküman listesindeki ders boş olsa da diğer derslerin notlarında soru sorulabilir.
  updateChatScope();
}
async function actionDocument(id, action) {
  try { await api('/api/documents/' + encodeURIComponent(id) + '/' + action, { method: 'POST' }); toast('Yeniden indeksleme kuyruğa alındı.'); await refreshDocuments(); } catch (e) { toast(e.message, true); }
}
async function uploadFiles(files) {
  if (!currentSubject()?.can_write) return;
  const subject = state.subject; let count = 0;
  $('file-input').disabled = true;
  try {
    for (const file of files) {
      $('upload-progress').textContent = file.name + ' yükleniyor…';
      const body = new FormData(); body.append('file', file);
      try { await api('/api/subjects/' + encodeURIComponent(subject) + '/documents', { method: 'POST', body }); count++; }
      catch (e) { toast(file.name + ': ' + e.message, true); }
    }
    $('upload-progress').textContent = count + ' dosya işleme kuyruğuna alındı. Durumlar otomatik güncellenir.';
    await refreshDocuments();
  } finally { $('file-input').disabled = false; $('file-input').value = ''; }
}
function systemCard(title, status, ok, description) { const card = node('article', undefined, 'system-card'); card.append(node('h3', title), node('span', status, 'badge ' + (ok ? 'ready' : 'error')), node('p', description)); return card; }
async function refreshSystem() {
  if (!state.user) return;
  const requestUserId = state.user.id;
  const [system, metrics] = await Promise.all([api('/api/system'), api('/api/dashboard')]);
  if (state.user?.id !== requestUserId) return;
  const ready = system.model.reachable && system.model.chat_ready && system.model.embed_ready;
  $('model-badge').textContent = ready ? 'Yerel modeller hazır' : 'Model kurulumu gerekli';
  $('model-badge').className = 'status-pill ' + (ready ? 'ok' : 'warning'); $('upload-limit').textContent = String(system.max_upload_mb);
  $('system-cards').replaceChildren(
    systemCard('Dil modeli', system.model.chat_ready ? 'Hazır' : 'Erişilemiyor / yüklü değil', system.model.chat_ready, system.chat_model + ' · Ollama'),
    systemCard('Embedding ve arama', system.model.embed_ready && system.qdrant_ready ? 'Hazır' : 'Kontrol gerekiyor', system.model.embed_ready && system.qdrant_ready, system.embedding_model + ' · ' + system.vector_mode),
    systemCard('Veri ve işleme', system.worker_enabled ? 'İşleyici açık' : 'İşleyici kapalı', system.worker_enabled, system.database + ' · sürüm ' + system.version)
  );
  const cards = [['Hazır doküman', metrics.ready], ['Aranabilir parça', metrics.chunks], ['Sorgu', metrics.query_count], ['Kaynak yetersiz', metrics.insufficient], ['Ortanca süre · p50', metrics.p50_ms === null ? '—' : (metrics.p50_ms / 1000).toFixed(1) + ' sn'], ['Süre · p95', metrics.p95_ms === null ? '—' : (metrics.p95_ms / 1000).toFixed(1) + ' sn'], ['Faydalı geri bildirim', metrics.positive_feedback], ['Hatalı sorgu', metrics.errors]];
  $('metric-cards').replaceChildren(...cards.map(([label, value]) => { const card = node('article', undefined, 'metric-card'); card.append(node('span', label), node('strong', String(value))); return card; }));
}
async function submitQuestion(event) {
  event?.preventDefault(); const question = $('question').value.trim();
  if (state.busy || !state.user || !state.subjects.length || question.length < 3) return;
  const requestUserId = state.user?.id;
  const requestedSubject = state.searchSubject, requestedMode = $('mode').value, requestedScopeName = scopeName();
  state.busy = true; $('send').disabled = true; $('subject-select').disabled = true; $('search-subject-select').disabled = true; $('mode').disabled = true; $('clear-chat').disabled = true; $('add-subject').disabled = true; $('question').value = '';
  $('messages').querySelector('.welcome')?.remove();
  const item = node('article', undefined, 'message'); item.append(node('div', question, 'message-user'), node('p', requestedScopeName + ' · ' + (requestedMode === 'agent' ? 'Araştırma ajanı' : 'RAG'), 'answer-scope'));
  const pending = node('p', requestedMode === 'agent' ? 'Ajan ' + requestedScopeName + ' kapsamındaki kaynakları araştırıyor…' : 'Notlar aranıyor, yerel model yanıtı hazırlıyor…', 'pending'); item.append(pending); $('messages').append(item); pending.scrollIntoView({ block: 'nearest' });
  try {
    const result = await api('/api/questions', { method: 'POST', body: { subject_id: requestedSubject, question, mode: requestedMode } });
    if (state.user?.id !== requestUserId) { pending.remove(); return; }
    pending.remove(); item.append(node('div', 'DERSATLAS / KAYNAKLI ÇALIŞMA', 'answer-label'), node('div', result.answer, 'message-answer'));
    const outcomes = { answered: 'Kaynak referansları kontrol edildi', insufficient: 'Kaynak yetersiz', invalid_output: 'Çıktı biçimi doğrulanamadı', invalid_citations: 'Kaynak referansı geçersiz' };
    item.append(node('p', (outcomes[result.outcome] || result.outcome) + ' · ' + (result.elapsed_ms / 1000).toFixed(1) + ' sn', 'answer-meta'));
    const actions = node('div', undefined, 'answer-actions');
    const sourceButton = node('button', 'Bu cevabın kaynaklarını aç'); sourceButton.addEventListener('click', () => renderSources(result.sources)); actions.append(sourceButton);
    for (const [label, value] of [['Faydalı', 1], ['Kontrol gerekli', -1]]) { const button = node('button', label); button.addEventListener('click', async () => { try { await api('/api/queries/' + result.query_id + '/feedback', { method: 'POST', body: { value } }); toast('Geri bildirimin kaydedildi.'); } catch (e) { toast(e.message, true); } }); actions.append(button); }
    item.append(actions);
    if (requestedMode === 'agent' || result.trace.length > 1) {
      const details = node('details', undefined, 'trace'); details.append(node('summary', 'Arama ve doğrulama adımlarını göster'));
      const list = node('ol');
      const stepNames = { search_notes: 'Notlarda arama', rejected: 'İzin verilmeyen araç veya parametre reddedildi', relevance_gate: 'Kaynak ilgisi kontrolü', extractive_fallback: 'Kaynak metninden destekli alıntı' };
      for (const step of result.trace) list.append(node('li', (stepNames[step.tool] || step.tool) + (step.query ? ': ' + step.query : '') + (step.found !== undefined ? ' · ' + step.found + ' sonuç' : '')));
      details.append(list); item.append(details);
    }
    renderSources(result.sources);
  } catch (e) { pending.remove(); if (state.user?.id === requestUserId) { item.append(node('p', e.message, 'error')); $('question').value = question; } }
  finally { state.busy = false; $('subject-select').disabled = false; $('search-subject-select').disabled = false; $('mode').disabled = false; $('clear-chat').disabled = false; $('add-subject').disabled = false; updateChatScope(); if (state.user) await refreshDocuments().catch(() => {}); }
}
$('login-form').addEventListener('submit', async event => { event.preventDefault(); const button = event.target.querySelector('button'); button.disabled = true; $('login-error').textContent = ''; try { const user = await api('/api/login', { method: 'POST', body: { username: $('username').value.trim(), password: $('password').value } }); $('password').value = ''; await loadApp(user); } catch (e) { $('login-error').textContent = e.message; } finally { button.disabled = false; } });
$('logout').addEventListener('click', async () => { try { await api('/api/logout', { method: 'POST' }); clearChat(); showLogin(); } catch (e) { toast(e.message, true); } });
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => setView(button.dataset.view)));
$('model-badge').addEventListener('click', () => setView('system'));
$('subject-select').addEventListener('change', () => { state.subject = $('subject-select').value; setView(state.view); refreshDocuments().catch(e => toast(e.message, true)); });
$('search-subject-select').addEventListener('change', () => { state.searchSubject = $('search-subject-select').value || null; updateChatScope(); });
$('mode').addEventListener('change', updateChatScope);
$('clear-chat').addEventListener('click', clearChat);
document.querySelectorAll('[data-question]').forEach(button => button.addEventListener('click', () => { $('question').value = button.dataset.question; $('question').focus(); }));
$('question-form').addEventListener('submit', submitQuestion);
$('file-input').addEventListener('change', event => uploadFiles([...event.target.files]).catch(e => toast(e.message, true)));
for (const type of ['dragenter', 'dragover']) $('upload-zone').addEventListener(type, event => { event.preventDefault(); $('upload-zone').classList.add('dragging'); });
for (const type of ['dragleave', 'drop']) $('upload-zone').addEventListener(type, event => { event.preventDefault(); $('upload-zone').classList.remove('dragging'); });
$('upload-zone').addEventListener('drop', event => uploadFiles([...event.dataTransfer.files]).catch(e => toast(e.message, true)));
$('refresh-docs').addEventListener('click', () => refreshDocuments().catch(e => toast(e.message, true)));
$('refresh-system').addEventListener('click', () => refreshSystem().catch(e => toast(e.message, true)));
$('add-subject').addEventListener('click', () => $('subject-dialog').showModal());
document.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => $(button.dataset.close).close()));
$('subject-form').addEventListener('submit', async event => { event.preventDefault(); try { const subject = await api('/api/subjects', { method: 'POST', body: { name: $('subject-name').value.trim() } }); $('subject-dialog').close(); $('subject-name').value = ''; await loadSubjects(subject.id); toast('Yeni ders oluşturuldu; genel aramaya dahil edildi.'); } catch (e) { toast(e.message, true); } });
$('confirm-delete').addEventListener('click', async () => { try { await api('/api/documents/' + encodeURIComponent(state.deleteId), { method: 'DELETE' }); $('delete-dialog').close(); renderSources([]); clearChat(); toast('Silme kuyruğa alındı; doküman artık arama sonuçlarına dahil edilmiyor.'); await refreshDocuments(); } catch (e) { toast(e.message, true); } });
setInterval(() => { if (state.user && state.documents.some(d => ['queued', 'processing', 'deleting'].includes(d.status))) refreshDocuments().catch(() => {}); }, 4000);
// WebMCP isteğe bağlıdır; erişim kontrolleri yine Python API'de uygulanır.
if (document.modelContext?.registerTool) {
  const lifecycle = new AbortController();
  try {
    Promise.resolve(document.modelContext.registerTool({ name: 'select_study_subject', title: 'Sohbetin ders filtresini seç', description: 'Mevcut yetkili bir dersi sohbetin arama filtresi yapar; boş subject_id tüm derslere döner. Veri değiştirmez ve sohbeti silmez.', inputSchema: { type: 'object', properties: { subject_id: { type: 'string' } }, required: ['subject_id'], additionalProperties: false }, annotations: { readOnlyHint: false, untrustedContentHint: true }, async execute(input) { if (state.busy) throw new Error('Soru işlenirken filtre değiştirilemez.'); if (!input || typeof input.subject_id !== 'string' || (input.subject_id && !state.subjects.some(s => s.id === input.subject_id))) throw new Error('Yetkili bir ders veya tüm dersler için boş değer seç.'); state.searchSubject = input.subject_id || null; $('search-subject-select').value = state.searchSubject || ''; setView('study'); return { search_scope: scopeName(), subject_id: state.searchSubject }; } }, { signal: lifecycle.signal })).catch(() => {});
    window.addEventListener('pagehide', () => lifecycle.abort(), { once: true });
  } catch (_) { /* Desteklenmeyen tarayıcıda normal arayüz çalışır. */ }
}
api('/api/me').then(loadApp).catch(showLogin);

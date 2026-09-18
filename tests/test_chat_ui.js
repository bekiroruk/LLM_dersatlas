'use strict';
// DOM test çifti: gerçek tarayıcı/görsel QA değildir; ağ ve ek npm paketi gerekmez.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'dist/index.html'), 'utf8');
const source = fs.readFileSync(path.join(root, 'dist/assets/app.js'), 'utf8');
const elements = new Map();

class Element {
  constructor(tag = 'div') { this.tagName = tag; this.children = []; this.events = {}; this.value = ''; this.disabled = false; this.dataset = {}; this.className = ''; this._text = ''; this.classList = { toggle() {}, add() {}, remove() {} }; }
  set id(value) { this._id = value; elements.set(value, this); }
  get id() { return this._id; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(' '); }
  set innerHTML(_) { throw new Error('Kaynaklar innerHTML ile oluşturulmamalı'); }
  append(...children) { for (const child of children) { child.parent = this; this.children.push(child); } }
  replaceChildren(...children) { this.children = []; this._text = ''; this.append(...children); }
  addEventListener(name, handler) { this.events[name] = handler; }
  setAttribute(name, value) { this[name] = value; }
  removeAttribute(name) { delete this[name]; }
  querySelector(selector) { return this.children.find(child => selector === '.' + child.className) || null; }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter(child => child !== this); }
  scrollIntoView() {}
  focus() {}
}
for (const match of html.matchAll(/\bid="([^"]+)"/g)) {
  assert.ok(!elements.has(match[1]), 'Tekil HTML id: ' + match[1]);
  new Element().id = match[1];
}
for (const match of source.matchAll(/\$\('([^']+)'\)/g)) {
  assert.ok(elements.has(match[1]), 'JS kontrolü HTML içinde bulunmalı: ' + match[1]);
}
elements.get('mode').value = 'rag';
const subjects = [
  { id: '11111111-1111-4111-8111-111111111111', name: 'Tarih', can_write: true },
  { id: '22222222-2222-4222-8222-222222222222', name: 'Coğrafya', can_write: true },
  { id: '33333333-3333-4333-8333-333333333333', name: 'Vatandaşlık', can_write: true },
];
const requests = [];
let availableSubjects = subjects;
let questionAnswer = 'Uydurma UI test cevabı. [K1]';
let questionTrace = null;
let questionError = false, holdQuestion = false, releaseQuestion;
const user = { id: 'user-a', username: 'Test', role: 'admin' };
const context = vm.createContext({
  document: { getElementById: id => elements.get(id) || null, createElement: tag => new Element(tag), querySelectorAll: () => [] },
  window: { addEventListener() {} }, FormData: class {}, AbortController,
  setTimeout: () => 1, clearTimeout() {}, setInterval() {},
  async fetch(url, options) {
    let data;
    if (url === '/api/me') data = user;
    else if (url === '/api/subjects') data = availableSubjects;
    else if (url.endsWith('/documents')) data = [];
    else if (url === '/api/system') data = { model: { reachable: true, chat_ready: true, embed_ready: true }, qdrant_ready: true, max_upload_mb: 20, worker_enabled: true };
    else if (url === '/api/dashboard') data = { ready: 3, chunks: 3, query_count: 0, insufficient: 0, p50_ms: null, p95_ms: null, positive_feedback: 0, errors: 0 };
    else if (url === '/api/questions') {
      const body = JSON.parse(options.body); requests.push(body);
      if (questionError) return { ok: false, status: 503, json: async () => ({ detail: 'Test modeli kapalı' }) };
      if (holdQuestion) await new Promise(resolve => { releaseQuestion = resolve; });
      const subject = subjects.find(s => s.id === body.subject_id) || subjects[1];
      data = { answer: questionAnswer, outcome: 'answered', elapsed_ms: 25, query_id: 'test-id',
        context_used: body.history.length > 0 && body.question.startsWith('Peki'),
        resolved_question: body.question.startsWith('Peki') ? 'Karadeniz ve Akdeniz iklimlerinin bitki örtüsü nasıl farklıdır?' : body.question,
        trace: questionTrace || (body.question.startsWith('Peki')
          ? [{ tool: 'conversation_context', method: 'explicit_reference', query: 'Karadeniz ve Akdeniz iklimi açısından bitki örtüsü nasıl farklı?', found: 1 }]
          : [{ tool: 'search_notes', query: body.question, found: 1 }]),
        sources: [{ source_id: 'K1', subject_id: subject.id, subject_name: subject.name, filename: 'Test.pdf', location: 'PDF sayfa 1', text: '<img src=x onerror=neverExecute()>', document_id: 'doc-id' }] };
    } else data = { ok: true };
    return { ok: true, status: 200, json: async () => data };
  },
});
vm.runInContext(source, context, { filename: 'dist/assets/app.js' });
const get = id => elements.get(id);
let passed = 0;
function check(description, test) { test(); passed++; console.log('OK: ' + description); }
async function main() {
  await new Promise(setImmediate); // Başlangıçtaki sahte API mikro-görevlerini tamamla.
  check('Varsayılan Genel Sohbet, tüm dersler ve boş doküman seçimi gönderimi engellemez', () => {
    assert.equal(get('page-title').textContent, 'Genel Sohbet');
    assert.equal(get('search-subject-select').value, '');
    assert.equal(get('search-subject-select').children.length, 4);
    assert.equal(get('send').disabled, false);
  });
  get('question').value = 'Türkiye iklim tipleri nelerdir?';
  await context.submitQuestion();
  check('Genel RAG isteği ders id yerine null gönderir', () => {
    assert.equal(requests[0].subject_id, null);
    assert.equal(requests[0].mode, 'rag');
    assert.equal(requests[0].history.length, 0);
  });
  check('Kaynak kartında ders, dosya, sayfa ve güvenli düz metin bulunur', () => {
    const text = get('sources').textContent;
    for (const expected of ['Coğrafya', 'Test.pdf', 'PDF sayfa 1', '<img src=x onerror=neverExecute()>']) assert.ok(text.includes(expected));
  });
  const messages = get('messages').children.length;
  get('subject-select').value = subjects[2].id;
  get('subject-select').events.change();
  await new Promise(setImmediate);
  check('Doküman dersi değişimi sohbeti veya genel arama kapsamını değiştirmez', () => {
    assert.equal(get('messages').children.length, messages);
    assert.equal(get('search-subject-select').value, '');
    assert.equal(get('page-title').textContent, 'Genel Sohbet');
    assert.equal(get('send').disabled, false);
  });
  get('search-subject-select').value = subjects[0].id;
  get('search-subject-select').events.change();
  get('question').value = 'Tanzimat ne zaman?';
  await context.submitQuestion();
  check('İsteğe bağlı filtre yalnızca açıkça seçilen ders id değerini gönderir', () => {
    assert.equal(requests[1].subject_id, subjects[0].id);
    assert.ok(get('page-title').textContent.includes('Tarih'));
    assert.equal(requests[1].history.length, 0);
  });
  get('search-subject-select').value = '';
  get('search-subject-select').events.change();
  get('mode').value = 'agent';
  get('mode').events.change();
  get('question').value = 'Notlarıma göre karşılaştırma yap.';
  await context.submitQuestion();
  check('Araştırma ajanı genel kapsamla gönderilir; adımlar ve güvenli araç açıklaması görünür', () => {
    assert.equal(requests[2].subject_id, null);
    assert.equal(requests[2].mode, 'agent');
    assert.equal(requests[2].history.length, 0);
    assert.ok(get('messages').textContent.includes('Arama ve doğrulama adımlarını göster'));
    assert.ok(get('method-hint').textContent.includes('komut çalıştıramaz'));
    assert.equal(get('search-subject-select').disabled, false);
  });
  get('question').value = 'Peki bu iki iklimin bitki örtüsü nasıl farklı?';
  await context.submitQuestion();
  check('Takip sorusu aynı kapsamın önceki mesajını gönderir; eski kaynak/atıf taşımaz', () => {
    const history = requests[3].history;
    assert.equal(history.length, 1);
    assert.equal(history[0].question, 'Notlarıma göre karşılaştırma yap.');
    assert.equal(history[0].subject_id, null);
    assert.ok(!history[0].answer.includes('[K1]'));
    assert.equal(history[0].sources, undefined);
    assert.ok(get('messages').textContent.includes('Bağlamla anlaşılan soru: Karadeniz ve Akdeniz'));
    assert.ok(get('messages').textContent.includes('açık gönderme doğrudan çözüldü'));
  });
  get('mode').value = 'rag'; get('mode').events.change();
  get('question').value = 'Bunu kısalt.';
  await context.submitQuestion();
  check('RAG/ajan geçişi hafızayı korur; takip zincirinde açık soru taşınır', () => {
    assert.equal(requests[4].mode, 'rag');
    assert.equal(requests[4].history.length, 2);
    assert.equal(requests[4].history[1].resolved_question, 'Karadeniz ve Akdeniz iklimlerinin bitki örtüsü nasıl farklıdır?');
  });
  questionTrace = [
    { tool: 'conversation_context', reason: 'invalid_json_or_schema' },
    { tool: 'conversation_context', reason: 'PRIVATE_TEST_MARKER' },
  ];
  get('question').value = 'Başka bir bağlam denemesi';
  await context.submitQuestion();
  questionTrace = null;
  check('Bağlam reddinin güvenli açıklaması görünür; bilinmeyen ham hata kodu basılmaz', () => {
    assert.ok(get('messages').textContent.includes('Modelin bağlam çıktısı JSON şemasına uymadı'));
    assert.ok(get('messages').textContent.includes('Bağlam doğrulaması başarısız'));
    assert.ok(!get('messages').textContent.includes('PRIVATE_TEST_MARKER'));
  });
  questionAnswer = 'Uzun cevap '.repeat(300);
  for (let index = 0; index < 7; index++) {
    get('question').value = 'Uzun soru ' + index + ' ' + 'x'.repeat(1000);
    await context.submitQuestion();
  }
  check('Hafıza en fazla 4 tur / 6000 karakter; cevaplar en fazla 1200 karakter', () => {
    for (const request of requests) {
      assert.ok(request.history.length <= 4);
      assert.ok(request.history.reduce((n, t) => n + t.question.length + t.resolved_question.length + t.answer.length, 0) <= 6000);
      for (const turn of request.history) assert.ok(turn.answer.length <= 1200);
    }
  });
  questionAnswer = 'Uydurma UI test cevabı. [K1]';
  context.clearChat();
  check('Temizle sohbeti, kaynakları ve takip sorusu hafızasını sıfırlar', () => {
    assert.ok(get('memory-hint').textContent.includes('0 önceki soru'));
    assert.equal(get('source-count').textContent, '0');
  });
  questionError = true; get('question').value = 'Başarısız yeni soru';
  await context.submitQuestion(); questionError = false;
  get('question').value = 'Tekrar başarılı soru';
  await context.submitQuestion();
  check('HTTP hatası hafızaya kaydedilmez; Temizle sonrası eski bağlam gönderilmez', () => {
    assert.equal(requests.at(-1).history.length, 0);
  });
  holdQuestion = true; get('question').value = 'Geciken soru';
  const pending = context.submitQuestion();
  await new Promise(setImmediate);
  context.clearChat(); releaseQuestion(); await pending; holdQuestion = false;
  check('Temizlenen sohbetin gecikmiş cevabı hafızayı veya kaynakları geri getirmez', () => {
    assert.ok(get('memory-hint').textContent.includes('0 önceki soru'));
    assert.equal(get('source-count').textContent, '0');
    assert.ok(!get('messages').textContent.includes('Uydurma UI test cevabı'));
  });
  context.showLogin();
  check('Çıkışta önceki kaynaklar, sohbet ve filtre temizlenir', () => {
    assert.equal(get('source-count').textContent, '0');
    assert.ok(!get('messages').textContent.includes('Uydurma UI test cevabı'));
    assert.equal(get('send').disabled, true);
    assert.ok(get('memory-hint').textContent.includes('0 önceki soru'));
  });
  availableSubjects = [];
  await context.loadApp({ id: 'user-b', username: 'Yeni', role: 'student' });
  check('Yeni oturum önceki ders kapsamını devralmaz; erişim yoksa gönderim kapalıdır', () => {
    assert.equal(get('search-subject-select').value, '');
    assert.equal(get('search-subject-select').children.length, 1);
    assert.equal(get('send').disabled, true);
    assert.equal(get('source-count').textContent, '0');
  });
  console.log(passed + ' arayüz mantığı testi başarılı. Gerçek tarayıcı/görsel test yerine geçmez.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });

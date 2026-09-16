# DersAtlas

**Notlarından öğren. Kaynağını gör. Verini yerelde tut.**

DersAtlas, ders dokümanları üzerinden kaynaklı soru-cevap üreten yerel bir çalışma asistanıdır. İlk kullanım alanı KPSS Tarih, Coğrafya ve Vatandaşlık notlarıdır; mimari yeni derslere genişletilebilir.

Python / FastAPI · Ollama · Qwen3 · BGE-M3 · Qdrant · SQLAlchemy

> **Depo durumu:** Bu repoda şu anda dokümantasyon, paylaşım güvenliği kontrolleri ve geliştirme araçları bulunur. Windows'ta çalışan uygulamanın güncel kaynak kodunun ilk aktarımı bekleniyor. Uygulama kodu aktarılmadan bu repodan kurulum yapılamaz. Eski bir uygulama kopyası güncel sürüm gibi yayımlanmamıştır.

## Proje ne yapıyor?

Yerelde çalışan uygulama PDF, DOCX, TXT ve Markdown dokümanlarını derslere göre düzenler; ilgili metin parçalarını bulur ve cevapta dosya/sayfa referanslarını gösterir. Bulut LLM API anahtarı gerektirmez. İlk model ve bağımlılık indirmeleri internet ister; yerel çalışma iddiası ayrıca ağ yapılandırmasıyla doğrulanmalıdır.

| Özellik | Durum |
| --- | --- |
| Ders ve doküman yönetimi | Yerel uygulamada mevcut |
| Dokümanları parçalara ayırma ve indeksleme | Yerel uygulamada mevcut |
| Ders bazlı kaynaklı soru-cevap | Yerel uygulamada mevcut |
| Araştırma ajanı ve sınırlı araç kullanımı | Yerel uygulamada mevcut; ayrı kalite değerlendirmesi gerekli |
| Kullanıcı yetkilendirme ve erişim kontrolleri | Yerel uygulamada mevcut; güvenlik denetimi değildir |
| Dosya/sayfa ve kaynak metni gösterme | Yerel uygulamada mevcut |
| Tüm yetkili derslerde Genel Sohbet | Sıradaki geliştirme; henüz uygulanmadı |
| Takip sorularını anlayan sohbet bağlamı | Planlandı; henüz uygulanmadı |
| OCR, SAP, fine-tuning, SSO, vLLM | Mevcut kapsamın dışında |

## Neden RAG?

LLM genel metin üretir; RAG ise cevap üretmeden önce kullanıcının dokümanlarından ilgili bölümleri getirir. Doküman eklemek modeli yeniden eğitmek değildir. Bir kaynak etiketinin geçerli olması, cümlenin o kaynak tarafından desteklendiğini tek başına kanıtlamaz.

Temel kalite ilkeleri:

- İlgili kaynak bulunmadan notlara dayalı cevap verilmez.
- Soru tekrar edilip cevapmış gibi gösterilmez.
- Tarih, kişi ve olay bilgileri aynı ilgili kaynak bölümü içinde değerlendirilir.
- Dersler arası arama, kullanıcılar arası veri erişimi anlamına gelmez.
- Notlarda olmayan genel bilgi, ileride ayrı bir mod eklenirse açıkça etiketlenir.

## Bileşenler

| Bileşen | Görev |
| --- | --- |
| FastAPI / Uvicorn | API ve yerel web uygulaması |
| Ollama / Qwen3 | Yerel cevap üretimi |
| BGE-M3 | Metinleri embedding vektörlerine dönüştürme |
| Qdrant | Anlamsal arama |
| SQLAlchemy / ilişkisel veritabanı | Kullanıcılar, dersler, dokümanlar, metin parçaları ve ölçümler |
| Python metin araması | Anlamsal aramayı kelime tabanlı eşleşmeyle destekleme |
| Web arayüzü | Doküman yönetimi, soru-cevap ve kaynak inceleme |

Detaylı veri akışı: [Mimari](docs/ARCHITECTURE.md).

## Yerel doğrulama durumu

Kullanıcı, son değişikliklerden sonra şu üç manuel senaryonun beklenen davranışı verdiğini bildirdi:

1. Coğrafya seçiliyken İstanbul'un fethi sorusunda turizm/Fethiye metninin cevap olarak kullanılmaması.
2. Tarih seçiliyken İstanbul'un fethi için tarih ve padişah bilgisinin ilgili kaynaklarla cevaplanması.
3. Coğrafya seçiliyken dağların kıyıya paralel uzanması sorusunun ilgili notlardan cevaplanması.

Bu bildirim üç hedefli kontroldür; tüm veri kümesi için doğruluk oranı, otomatik değerlendirme veya üretime hazır olma kanıtı değildir. [Kalite planı](docs/QUALITY.md) ve [bilinen sınırlamalar](docs/STATUS.md).

## Mevcut Windows kopyasını çalıştırma

Aşağıdaki komutlar yalnızca `app/main.py` ve mevcut sanal ortamın bulunduğu çalışma klasöründe kullanılmalıdır:

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Ollama uygulaması açık olmalı; yerel kopyada `qwen3:4b` ve `bge-m3` kullanılıyor. Uygulama adresi: [http://127.0.0.1:8000](http://127.0.0.1:8000).

Gömülü Qdrant ile aynı veri klasörüne ikinci uygulama süreci açılmaz. `--workers 1` korunur. Bu depo henüz uygulamayı içermediği için yukarıdaki komutlar yeni bir repo klonunda çalışmaz.

## Güvenli sürümleme

**Bu repoya ders PDF'leri, kişisel notlar, .env, veritabanı, vektör indeksleri, model ağırlıkları veya yedekler yüklenmez.**

`.gitignore` yalnızca izlenmeyen dosyalar için koruma sağlar. Ek kontrol, Git indeksindeki dosya adlarını ve bazı bilinen anahtar biçimlerini denetler; eksiksiz bir veri kaybı önleme veya secret tarama ürünü değildir.

Depo araçlarının testleri, Git ve Python 3.12 ile ek paket gerektirmeden çalıştırılabilir:

```powershell
py -3.12 scripts\run_tests.py
py -3.12 scripts\repo_guard.py
```

Uygulama kodu aktarıldıktan sonra gün sonu güncellemesi önce önizlenir:

```powershell
.\.venv\Scripts\python.exe scripts\gun_sonu.py --message "fix(rag): kaynak eşleşmesini düzelt"
```

İnceleme ve onaydan sonra:

```powershell
.\.venv\Scripts\python.exe scripts\gun_sonu.py --message "fix(rag): kaynak eşleşmesini düzelt" --apply --push
```

Araç testler başarısızsa veya atlanırsa commit yapmaz. Varsayılan çalışma hiçbir dosyayı stage etmez, commit veya push yapmaz. Otomatik Windows yüklemesi ya da zamanlanmış görev kurulmuş değildir.

İlk aktarım ve günlük çalışma: [Geliştirme rehberi](docs/DEVELOPMENT.md).

## Yol haritası

1. Güncel çalışan kaynak kodunu güvenli şekilde aktarmak.
2. Genel Sohbet: tüm yetkili derslerde arama, isteğe bağlı ders filtresi.
3. Sınırlı sohbet bağlamı ve takip soruları.
4. Tekrarlanabilir RAG değerlendirmesi ve olumsuz testler.
5. Performans ölçümü ve yerel model optimizasyonu.

Detaylar ve kabul kriterleri: [Roadmap](docs/ROADMAP.md).

## Katkı, güvenlik ve lisans

- [Katkı rehberi](CONTRIBUTING.md)
- [Güvenlik politikası](SECURITY.md)
- [Değişiklik kaydı](CHANGELOG.md)

Henüz bir açık kaynak lisansı seçilmedi. Depo herkese açık olsa da bu, otomatik olarak açık kaynak kullanım lisansı verildiği anlamına gelmez. Kişisel ders materyalleri projenin kodundan ayrı tutulur.

# Doğrulama raporu - 10 Eylül 2026

## Sonuç

**20 çekirdek testi geçti. 18 API/entegrasyon testi atlandı.** Atlanan testler başarılı sayılmamıştır. Kaynak kodu sözdizimi kontrolleri geçti. Gerçek LLM doğruluğu, uçtan uca çalışma, Docker ve SQL Server bu ortamda doğrulanmadı.

## Çalıştırılan kontroller

| Kontrol | Sonuç | Ne gösterir? |
| --- | --- | --- |
| `python -m unittest discover -s tests -v` | 38 test keşfedildi; 20 başarılı, 18 atlandı | Ayrıştırma/arama temel mantığı çalışıyor; API sonucu yok |
| `python -m compileall -q app scripts tests` | Başarılı | Python dosyalarının sözdizimi geçerli |
| `node --check dist/assets/app.js` | Başarılı | Arayüz JavaScript sözdizimi geçerli |
| Gerçek Ollama ve embedding | Çalıştırılmadı | Model ağırlığı/servisi bulunmuyor |
| Docker Compose ve GPU | Çalıştırılmadı | Docker/GPU ortamı bulunmuyor |
| SQL Server | Çalıştırılmadı | SQL Server/ODBC ortamı bulunmuyor |
| Tarayıcı / görsel / uçtan uca UI testi | Çalıştırılmadı | Etkileşimli tarayıcı doğrulaması yapılmadı |
| WebMCP | Çalıştırılmadı | Destekleyen izinli tarayıcı bağlamı yok; temel uygulama için zorunlu değil |

FastAPI, SQLAlchemy, HTTPX, Qdrant istemcisi ve diğer API bağımlılıklarını yükleme girişimi ağ izin engeline takıldı. Yetki sınırı aşılmadı; testler mevcut kitaplıklarla ayrıştırılabilen çekirdek katmanla sınırlı tutuldu.

## Geçen çekirdek testleri

Türkçe I/İ normalizasyonu; tarihle BM25 eşleşmesi; eşleşme bulunmaması; durak sözcükler; RRF sıralama birleşimi; kaynak konumunu koruyan parçalama; uzun sözcük/örtüşme; hatalı parça ayarı; metin temizliği; UTF-8 okuma; hatalı kodlama reddi; metinsiz PDF/OCR uyarısı; DOCX tablo konumu; tuzlu parola hash'i ve doğrulama; parola uzunluğu; token hash'i; geçerli kaynak; bilinmeyen kaynak reddi; metinde kaynak olmaması; metin/metadata kaynak uyumsuzluğu.

## Hazırlanan fakat çalıştırılamayan API testleri

Oturumsuz erişim; CSRF başlığı; çapraz Origin; dersler arası izolasyon; yükleme/işleme/RAG; aynı belge tekrarı; dosya türü; istek boyutu; kaynaksız çekimserlik; uydurma kaynak reddi; model kesintisi; yarım indeksli belgenin dışlanması; silinen kaynağın dışlanması; dosya indirme yetkisi; öğrenci okuma/yazma ayrımı; agent'in shell aracını reddetmesi; geri bildirim sahipliği; logout sonrası oturumun iptali.

API testlerinde embedding/LLM cevabı test çiftidir. Bu testlerin ileride geçmesi bile gerçek modelin tarih bilgisi veya kaynak sadakati kalitesini kanıtlamaz. Gerçek Ollama değerlendirmesi ayrı yürütülür.

## Yerel kabul ölçütleri

1. Tüm bağımlılıklar yüklüyken 38 test geçmeli, 0 atlama olmalı.
2. Model durumu, embedding ve Qdrant hazır görünmeli.
3. Örnek not yüklenip işlenmeli; kaynak konumu doğru açılmalı.
4. Kendi üç tarih dosyanla en az 30 soru insan denetiminden geçmeli. Sayısal hedefler gözlenen başlangıç seviyesine göre belirlenecek.
5. Başka ders ve kullanıcıdan kaynak sızıntısı olmamalı.
6. Model durdurulduğunda sahte cevap değil açık hizmet hatası görünmeli.
7. Yeniden başlatma ve yedek geri yükleme sonrası belgeler ve kaynak referansları korunmalı.
8. Mobil ve masaüstü tarayıcıda giriş, yükleme, ders değişimi, silme onayı ve klavye kullanımı kontrol edilmeli.

Bu kapılar tamamlanmadan README'deki “yerel doğrulama adayı” ibaresi kaldırılmamalı.

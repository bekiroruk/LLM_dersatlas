# Changelog

Yalnızca gerçekten yapılan değişiklikler kaydedilir. Planlanan özellikler [Roadmap](docs/ROADMAP.md) içindedir. Gün değişmesi veya GitHub katkı grafiği için boş commit oluşturulmaz.

## Unreleased

### Tam yağış rejimi kanıtı — 2026-09-20

- Geniş iklim karşılaştırmasında yalnızca yaz/kış geçen kısa parçalar artık tam yağış rejimi sayılmaz. Kaynakta ya açık düzenli/düzensiz-yıl boyu ilişkisi ya da yaz, kış ve en fazla/az yağış dönemi birlikte bulunmalıdır.
- Yapılandırılmış cevap kaynak listesindeki ilk eşleşmeyi kullanmak yerine her iklim için en ayrıntılı geçerli ilişkiyi seçer. Bildirilen yanlış Karadeniz satırı ve eksik Akdeniz cümlesi, doğru ayrıntılı satırlar varken cevaba giremez.
- Tam ilişki bulunamazsa yerel modelin eksik parçaları birleştirmesine izin verilmez; sistem yanlış karşılaştırma yerine kaynak yetersiz sonucuna kapanır.
- 191 Python testi ve 17 JavaScript arayüz mantığı testi başarılıdır.

### Düzleştirilmiş PDF tablo güvenliği — 2026-09-20

- PDF metin çıkarımında sütun ilişkisi kaybolmuş `Karadeniz / Akdeniz / karasal` matrisleri artık tek bir iklimin yağış kanıtı sayılmaz.
- İklim adıyla yağış değeri arasında açık ilişki zorunlu kılındı. Yakındaki toprak açıklamasındaki “yağışla yıkanmış”, yeraltı suyu tablosundaki “rejimi düzensiz” ve yamaç yağışı iklim rejimine bağlanmaz.
- Geçerli açık cümleler ile `Yaz / Kış / En fazla yağış` satırları kabul edilmeye devam eder; yapılandırılmış cevap her iklimin yağış ve bitki örtüsü hücrelerini ayrı kaynak ilişkilerinden kurar.
- 189 Python testi ve 17 JavaScript arayüz mantığı testi başarılıdır. Kullanıcının gerçek bitki PDF'si, doğru yağış satırları ve bildirilen bozuk matris aynı gerçek SQLite/gömülü Qdrant akışında sınandı; sonuç doğru iki kaynağı seçti ve bozuk parçaları dışarıda bıraktı.

### Kararlı yerel çalışma ve tam kanıt kapsaması — 2026-09-20

- SQLite, Qdrant ve `.env` yolları terminalin açıldığı klasörden bağımsız olarak proje köküne sabitlendi; aynı kurulumun yanlışlıkla ikinci bir boş veri alanı açması engellendi.
- Çok ölçütlü karşılaştırmalarda her konu ve ölçüt için gereken açık kanıt, genel benzerlik sıralamasından bağımsız olarak bütün yetkili hazır parçalarda aranır. `TOP_K`, bulunan zorunlu kanıtları artık kesmez.
- Windows başlatıcısı bu projeye ait eski Uvicorn sürecini kapatır, portu denetler, sunucuyu arka planda başlatır ve `/health` üzerinden çalışan RAG sürümünü doğrular. Ayrı güvenli durdurma betiği eklendi.
- Arayüz çalışan RAG sürümünü ve çok parçalı sorulardaki kanıt kapsamasını gösterir.
- 186 Python testi ve 17 JavaScript arayüz mantığı testi başarılıdır. Kullanıcının yüklediği gerçek bitki PDF'si, gerçek ayrıştırma/SQLite/gömülü Qdrant akışıyla sınandı; bildirilen iklim sorusu `4/4` kanıtla yapılandırılmış cevap üretti.

### Karşılaştırma kaynağı kalitesi — 2026-09-19

- Açık iki-konulu takip soruları, her konu için ayrı sözcüksel aramalara bölünür; iki tarafa ait doğrudan kaynaklar genel kategori listelerinden önce sunulur.
- Kaynak doğrulayıcı karşılaştırma kanıtını yetersiz bulduğunda dağınık PDF parçaları artık cevap gibi birleştirilmez. Açık kanıt yoksa sistem kaynak yetersiz sonucuna döner.
- Karşılaştırma istemleri, iki tarafın istenen özelliğini ayrı ayrı doğrulamayı ve ilişkisiz kategori listelerini eşleştirmemeyi açıkça zorunlu kılar.
- Bildirilen iklim örneğini temsil eden katalog/direkt kaynak regresyonları eklendi; 125 Python ve 15 JavaScript mantık testi yerel Linux ortamında başarılı.

### Açık takip göndermelerinin çözümü — 2026-09-18

- “Bu iki iklimin…” gibi açık göndermeler, son bağımsız karşılaştırma sorusunun konu adlarıyla model çağrısı olmadan açılır; “Bunu kısalt” da önceki bağımsız soruya bağlanır. Konu veya cevap bilgisi koda sabitlenmez.
- Daha karmaşık göndermelerde mevcut yerel model ve sıkı çıktı kontrolleri korunur. Reddin güvenli nedeni arama adımlarında gösterilir; ham model çıktısı/geçmiş ifşa edilmez.
- Yeni konu, farklı kapsam, farklı isim veya üçlü karşılaştırma yanlışlıkla bu dar kurala bağlanmaz. Her cevap için yeniden yetkili kaynak araması gerekir.
- 122 Python ve 15 JavaScript mantık testi yerel Linux ortamında başarılı; gerçek Ollama/PDF kabul denemesi kullanıcı bilgisayarında yeniden yapılmalı.

### Oturum içi sohbet bağlamı — 2026-09-17

- Son en fazla 4 tur / 6000 karakter yalnızca açık sayfanın RAM'inde tutulur; kalıcı sohbet tablosu, localStorage veya yeni bağımlılık yok.
- Yerel model takip sorusunu bağımsız arama sorusuna çevirir; RAG/ajan güncel yetkilerle yeniden kaynak arar. Önceki cevap ve atıflar kanıt olarak aktarılmaz.
- Yeni konu kendi sorusuyla aranır; belirsiz/geçersiz bağlam çıktısında açıklama istenir. Kullanıcının sayıları değiştiren veya yeni yıl uyduran yeniden yazım reddedilir.
- Temizle, çıkış, sayfa yenileme ve ders filtresi değişimi hafızayı sıfırlar. Gecikmiş cevap temizlenmiş sohbeti geri getiremez.
- 113 Python ve 14 JavaScript mantık testi yerel Linux ortamında başarılı; model test çiftidir. Gerçek Ollama takip sorusu denemesi ayrıca yapılmalı.

### Genel Sohbet ve araştırma ajanı — 2026-09-17

- İsteğe bağlı subject_id: varsayılan tüm yetkili derslerde hibrit arama.
- Doküman düzenleme seçimi ile sohbet filtresi ayrıldı; kaynaklara ders bilgisi eklendi.
- Araştırma ajanı genel veya tek ders kapsamını korur; ek aramalar yapar, ilk arama boşsa tekrar deneyebilir.
- İzin dışı araç/kapsam parametreleri ve bozuk araç çağrıları reddedilir; tur/arama sınırları korunur.
- Eski SQLite sorgu ölçümleri için yedekli, transaction içinde ve idempotent şema geçişi.
- 92 Python testi ve 8 JavaScript arayüz mantığı testi yerel Linux ortamında başarılı. Gerçek Ollama/PDF değerlendirmesi veya görsel tarayıcı testi değildir.

### İlk kaynak kodu aktarımı

- Güncel yerel uygulamanın API, web arayüzü, testler ve kurulum dosyaları eklendi: [78f052f](https://github.com/bekiroruk/LLM_dersatlas/commit/78f052fe0f16d50d59e1ef10f306d51acb0893ed).
- İlk gönderim öncesinde Windows'ta 60 uygulama/depo testi ve sözdizimi kontrolü başarılı tamamlandı.
- Gün sonu aracına .dockerignore dosyasını paylaşma desteği ve regresyon testi eklendi.
- PDF'ler, .env, veritabanları, vektör indeksleri ve modeller kaynak kodu aktarımının dışında tutuldu.

### Added — 2026-09-16

- Proje tanımı, mevcut durum, mimari, kalite planı ve Genel Sohbet yol haritası.
- Kişisel materyallerin paylaşımını engellemeye yardımcı olan .gitignore kuralları.
- Git indeksini kontrol eden paylaşım güvenliği aracı ve regresyon testleri.
- Önizleme ve kullanıcı onayıyla çalışan gün sonu commit/push aracı.
- Katkı, güvenlik, hata bildirimi ve pull request şablonları.

### Local verification reported

- Coğrafya/turizm metninin İstanbul'un fethi sorusu için kullanılmaması.
- Tarih dersi kapsamında İstanbul'un fethi sorusunun kaynaklı cevaplanması.
- Coğrafya kapsamında dağların kıyıya paralel uzanması sorusunun cevaplanması.

Bu üç sonuç kullanıcı tarafından yerel uygulamada bildirildi; kapsamlı bir RAG doğruluk ölçümü değildir. Güncel uygulama kodu ilk aktarım commit'iyle repoya eklendi.

Henüz yeni sürüm etiketi veya release oluşturulmadı.

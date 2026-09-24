# Changelog

Yalnızca gerçekten yapılan değişiklikler kaydedilir. Planlanan özellikler [Roadmap](docs/ROADMAP.md) içindedir. Gün değişmesi veya GitHub katkı grafiği için boş commit oluşturulmaz.

## Unreleased

### Kişi, süre ve bağlı iddia doğrulaması — 2026-09-24

- Kaynakta yalnızca “etkili” olarak geçen kişi artık fermanı “ilan eden” veya “hazırlayan” kişi gibi sunulamaz; kişi–eylem ilişkisi aynı kaynak biriminde açıkça bulunmalıdır.
- Tanzimat Dönemi'nin 1876'ya kadar sürmesi, Tanzimat Fermanı'nın 1876'ya kadar devam ettiği biçiminde kullanılamaz. `ve` ile bağlanan iki bağımsız iddia tek cümlenin genel sözcük benzerliğine saklanmadan ayrı ayrı denetlenir.
- Kullanıcının paylaştığı gerçek hatalı Tanzimat–Islahat cevabı birebir regresyon testine eklendi. 228 Python testi ve 19 JavaScript arayüz mantığı testi başarılıdır.

### Ferman–dönem ve karşılaştırma öznesi ayrımı — 2026-09-24

- Ferman karşılaştırmalarında konu adı cümlenin başında açık özne olan kanıtlar önceliklendirildi; Tanzimat Dönemi’nin 1839–1876 sınırı artık Tanzimat Fermanı’nın ayırt edici özelliği yerine seçilmez.
- “Tanzimat Fermanı’yla benzer amaçlar taşır” gibi bir tarafı yalnızca karşılaştırma referansı yapan cümleler o tarafa özgü kanıt sayılmaz. Ortak amaçların tek bir fermana ait fark gibi sunulması istem ve kaynak bağlamı düzeyinde engellendi.
- Kullanıcının gerçek üç kaynaklı cevabı dönem sayfası, ortak amaç cümlesi ve iki fermana özgü sayfalarla regresyon testine dönüştürüldü. 224 Python testi ve 19 JavaScript arayüz mantığı testi başarılıdır.

### Temiz ve konu odaklı karşılaştırma geri dönüşü — 2026-09-24

- Yerel modelin cevabı kaynak denetiminden geçmediğinde genel karşılaştırma artık uzun PDF/OCR bloklarını kullanıcıya dökmez; her karşılaştırma tarafı ayrı başlık altında, yalnızca konuya bağlı doğrulanmış maddelerle gösterilir.
- Numaralı ve büyük harfli bölüm başlıkları, Kritik eşleştirme / Tuzak etiketleri, komşu konu cümleleri ve tekrarlanan kısa kanıtlar ayıklanır. Ok yönlü not ilişkileri okunabilir konu: bilgi biçimine dönüştürülür.
- Kullanıcının paylaştığı dört Tanzimat–Islahat kaynak bloğu birebir regresyon testine eklendi. 223 Python testi, 19 JavaScript arayüz mantığı testi ve sözdizimi kontrolleri başarılıdır.

### Dönem–ilan ilişkisi ve kaynak metni temizliği — 2026-09-24

- Kaynaktaki `Tanzimat Dönemi 1839-1876` aralığının `Tanzimat Fermanı 1839-1876 arasında ilan edildi` biçiminde yanlış bir olay ilişkisine dönüştürülmesi artık cevap yayımlanmadan reddedilir.
- PDF bölüm numarası ve başlığı ile `ilgili kaynaklarda` / `gibi detaylar` türü kaynak hakkındaki meta ifadeler cevap sayılmaz; yerel model bunları üretirse güvenli, doğrudan kaynak karşılaştırmasına dönülür.
- Bildirilen hatalı Tanzimat–Islahat çıktısı birebir regresyon testine eklendi. 222 Python testi, 19 JavaScript arayüz mantığı testi ve sözdizimi kontrolleri başarılıdır.

### Genel karşılaştırma kanıt dengesi — 2026-09-24

- `Tanzimat ve Islahat fermanlarının farkları` gibi ortak isimli karşılaştırmalar artık iki ayrı kaynak aramasına bölünür; iki konu farklı PDF sayfalarında olsa da ikisi de cevap bağlamına dengeli biçimde alınır.
- Yerel model açık kaynaklara rağmen çekimser kalırsa iki tarafın doğrulanmış kaynak satırları güvenli karşılaştırma özeti olarak gösterilir. Taraflardan biri gerçekten eksikse kaynak yetersiz sonucu korunur.
- Aynı genel tekrar paragrafı iki taraf için tekrar kullanılmaz: varsa Tanzimat ve Islahat'a özel sayfalar önce seçilir. İki ayrı sayfadaki destekli bilgiler tek karşılaştırma cümlesinde güvenle birleştirilebilir; desteksiz tarih ve ayrıntılar reddedilmeye devam eder.
- Bildirilen Tanzimat–Islahat sorusu ayrı belgeler, ortak özet, çekimser model ve konu dışı kaynakla uçtan uca regresyon testine dönüştürüldü. 219 Python testi, 19 JavaScript arayüz mantığı testi ve sözdizimi kontrolleri başarılıdır.

### Modern çalışma alanı — 2026-09-23

- Kullanıcının gerçek masaüstü ekranındaki taşma ve boşluk sorunları üzerinden giriş, sohbet, kaynak defteri, doküman yönetimi ve sistem ekranları ikinci kez tasarlandı; uygulama kabuğu, kart hiyerarşisi ve tipografi baştan kuruldu.
- Sohbet artık merkezdedir: kırılmayan iki satırlı menü, animasyonlu karşılama alanı, bağımsız öneri kartları, komut çubuğu biçiminde soru alanı ve canlı kanıt paneli kullanılır.
- Canlı karakter sayacı, otomatik yükseklik, `Ctrl/⌘ + Enter`, işlem durumu, hover/geçiş animasyonları ve kaynak sayısı eklendi. Masaüstü, tablet, telefon, klavye odağı ve azaltılmış hareket tercihi desteklenir; harici arayüz servisi eklenmedi.
- HTML ile eski CSS/JavaScript sürümünün tarayıcı önbelleğinde karışması engellendi: arayüz dosyaları sürümlü URL kullanır ve uygulama kabuğu ile statik dosyalar `no-store` döndürür.
- 212 Python testi, 19 JavaScript arayüz mantığı testi, JavaScript sözdizimi ve Git fark kontrolü başarılıdır.

### Fetih sorusunda eksik kanıt tamamlama — 2026-09-23

- Gerçek v15 ajan raporunda İstanbul'un fethi için tarih bulunmasına rağmen hükümdar kanıtı kayboldu ve dağınık PDF metni cevap olarak gösterildi. Bu satır doğrudan regresyon örneğine dönüştürüldü.
- Tarih ve hükümdarı birlikte isteyen fetih sorularında iki açık olay kanıtı, benzerlik kısa listesinden bağımsız olarak bütün yetkili hazır parçalarda aranır ve cevap bütçesine öncelikli alınır.
- İki kanıttan biri yoksa model veya doğrudan alıntı yolu eksik cevabı tamamlayamaz; sistem kaynak yetersiz sonucuna kapanır.
- Windows başlatıcısı erken kapanmada çıkış kodunu, stdout/stderr içeriğini ve günlük yollarını birlikte gösterir; kullanıcı mesajları eski PowerShell'in UTF-8 yorumuna bağlı kalmayacak biçimde düzenlendi. 203 Python testi, 17 JavaScript arayüz mantığı testi ve paylaşım kontrolü başarılıdır.

### Soru kataloğu ve hükümdar adı güvenliği — 2026-09-21

- Gerçek sekiz soruluk ajan kabul raporunda Vatandaşlık kaynağındaki peş peşe soru maddelerinin cevap gibi kopyalandığı ve İstanbul'un fethi cevabında `I. Fatih Sultan` biçiminin seçildiği görüldü.
- Cevap anahtarı taşımayan soru katalogları artık arama adayından ve doğrudan alıntı yolundan çıkarılır; modelin soru listesini yanıt diye döndürmesi ayrıca reddedilir.
- Fetih bilgisinde aynı kaynak kapsamındaki açık tarih ve hükümdar satırları birlikte değerlendirilir; bozuk sıra sayısı + unvan kalıbı reddedilir ve tam kişi adı tercih edilir.
- Kabul veri kümesi `TBMM / Türkiye Büyük Millet Meclisi` ile `Mehmet / Mehmed` gibi doğru yazım alternatiflerini tek doğrulama grubu olarak ölçebilir. 201 Python testi, 17 JavaScript arayüz mantığı testi, sözdizimi ve paylaşım kontrolü başarılıdır.

### Genel ajan kabul ölçümü — 2026-09-20

- `scripts/evaluate.py` artık ders filtresi olmadan tüm erişilebilir notlarda hem `rag` hem `agent` modunu ölçer. Ajan modu gerçek cevap üretimi olmadan çalıştırılamaz.
- Tarih, Coğrafya, Vatandaşlık ve iki kaynak-dışı sorudan oluşan `samples/general_evaluation.json` başlangıç kabul kümesi eklendi.
- Kaynak metni kapsaması, cevap metni kapsaması, cevaplanabilirlik/çekimserlik başarısı ve p50/p95 süreleri ayrı raporlanır; kısa metin eşleşmesi doğruluk olasılığı olarak sunulmaz.
- Değerlendirme veri sözleşmesi, Türkçe büyük/küçük harf eşleşmesi, yüzdelik hesabı ve metrik ayrımı test edildi. 197 Python testi ve 17 JavaScript arayüz mantığı testi başarılıdır.

### Parçalı yağış cümlesi temizliği — 2026-09-20

- Yapılandırılmış iklim cevabı, PDF/OCR parçasının ortasından başlayan `’de azdır` benzeri eksik hücreleri ve `Tuzak / not` açıklamalarını artık kullanıcı yanıtına taşımaz.
- Mevsim değerleri nokta, virgül ve noktalı virgül sınırlarında ayrıştırılır; bitki örneklerinin yağış rejimine karışması engellenir. Açık `yıl boyu yağışlıdır` ve `rejim düzensizdir` ilişkileri kısa, tamamlanmış önermelere dönüştürülür.
- Kullanıcının bildirdiği bozuk Karadeniz ve Akdeniz çıktısı birebir regresyon olarak eklendi. 193 Python testi ve 17 JavaScript arayüz mantığı testi başarılıdır.

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

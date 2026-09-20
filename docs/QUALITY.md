# RAG kalite planı

## Mevcut kanıt

Son üç hedefli senaryonun başarıyla çalıştığı kullanıcı tarafından bildirildi. Bu depo hazırlığının Python araçları ayrıca otomatik test edilir. Bunlar gerçek LLM'in bütün tarih bilgilerini doğru ürettiğini kanıtlamaz.

## İlk regresyon kümesi

| Senaryo | Soru / içerik | Beklenen |
| --- | --- | --- |
| Benzer yazılan farklı sözcükler | fethedildi ile Fethiye | Kelime eşleşmesi sayılmamalı |
| Yanlış ders / ilişkisiz kaynak | Coğrafya turizm metni + İstanbul'un fethi sorusu | Turizm metni cevap olmamalı |
| Olumlu tarih | İstanbul hangi tarihte ve hangi padişah döneminde fethedildi? | İlgili notta bulunan tarih/padişah ve doğru kaynak |
| Olumlu coğrafya | Dağların kıyıya paralel uzanmasının sonuçları | İlgili kaynaklardan açıklama |
| Yanlış öncül | Islahat Fermanı 1876 yılında mı ilan edildi? | Kaynakta açık bilgi varsa öncülü düzeltmek; yoksa yıl uydurmamak |
| Kaynak dışı | Tarih notlarında Python'da liste oluşturma | Kaynak yetersiz; sahte tarih kaynağı yok |
| Soru tekrarı | Karşılaştırma sorusunun aynısını döndüren model | Cevap olarak kabul edilmemeli |
| Yazım varyantı | Kayser-i Rûm / kayseri rum | Eşdeğer konu anlaşılmalı; ilişkisiz kavramlar birleştirilmemeli |
| Yetkisiz kaynak | Başka kullanıcının dersi | Kaynağa veya belge indirmeye erişilememeli |
| Genel Sohbet | Üç farklı dersten ardışık sorular | Ders değiştirmeden, her soru için doğru kaynak |

## Ölçümleri ayrı tut

- Kaynak bulma: etiketli parçalar için Recall@k.
- Cevap doğruluğu: sorunun istenen bilgisine göre insan/etiketli değerlendirme.
- Kaynak desteği: iddiaların atıf verilen bölümde gerçekten bulunması.
- Reddetme: yetersiz veya ilişkisiz kanıtta doğru şekilde cevap vermemek.
- Cevaplanabilirlik: yeterli kaynak bulunduğu halde gereksiz reddetme.
- Gecikme: soğuk/sıcak p50 ve p95; donanım ve model ayarıyla birlikte.

Her sonuç için soru kümesi, model sürümü, doküman sürümü, ölçüm tarihi ve başarısız örnekler kaydedilir. Kaynak kimliği geçerliliği veya benzerlik skoru cevap doğruluğu diye raporlanmaz.

## Otomatik kontroller

- Depo kontrolü yalnızca Git indeksindeki dosyaları tarar; tüm bilgisayarı taramaz.
- Test çalıştırıcısı sıfır test, başarısız test veya atlanan testte başarısız döner.
- Uygulama kaynak kodu bulunmuyorsa depo testlerinin başarısı uygulama testi başarısı olarak adlandırılmaz.
- Gerçek model değerlendirmesi ayrı çalıştırılır; CI için kişisel PDF veya model ağırlığı gerekmez.

Genel Sohbet değişikliğinde 92 Python testi gerçek SQLite/gömülü Qdrant ve bir LLM test çiftiyle başarılı. Yeni testler tüm yetkili derslerin birleşimini, tek ders filtresini, sahiplik/üyelik/üyelik iptalini, bozuk vektör yanıtından ACL korumasını, kaynak metadatasını, araştırma ajanının sınırlarını ve eski şemanın veri koruyan geçişini kapsar.

8 JavaScript testi DOM test çiftiyle sohbet kapsamı, istek gövdesi, kaynak kartları ve oturum temizliğini kontrol eder. Gerçek tarayıcı veya görsel QA değildir. Çalıştırma: node tests/test_chat_ui.js. CI bu kontrolleri Python testlerinden ayrı çalıştırır.

Gerçek Ollama modelleri ve kişisel dokümanlarla kontrollü değerlendirme hâlâ gereklidir; otomatik test başarısı bu değerlendirmeyle karıştırılmaz.

## Sohbet bağlamı regresyonları

Yeni bağlam sürümünde toplam 113 Python ve 14 DOM mantık testi yerel Linux'ta başarılı. Son dört tur / 6000 karakter sınırı, geçersiz rol/kaynak alanlarını reddetme, yalnızca aynı kapsamın son turlarını kullanma, takip zincirinde açık soruyu koruma, eski atıfları çıkarma, yanlış yıl öncülünü yeniden yazımla değiştirmeme ve bozuk model çıktısında açıklama isteme test edildi.

API testleri hem RAG hem ajan için takip sorusunda yeniden gerçek SQLite/Qdrant araması yapıldığını doğrular. Önceki cevap kanıt olarak son modele aktarılmaz; geçmişte Python anlatılması tarih belgelerinden Python cevabı ürettirmez. Güncel yetkiler ve iptal edilmiş üyelikler yine uygulanır. DOM testleri temizleme, filtre/yöntem değişimi, HTTP hatası ve temizlenmiş sohbete gecikmiş cevabın gelmesini kapsar. Bunlar gerçek modelin her göndermeyi doğru anlayacağını kanıtlamaz.

### Bildirilen açık gönderme hatası — 2026-09-18

Kullanıcının “Karadeniz ve Akdeniz iklimini karşılaştır” ardından “Peki bu iki iklimin bitki örtüsü nasıl farklı?” denemesinde bağlam netleştirilemedi. Ham yeniden yazım çıktısı mevcut olmadığından tetiklenen model/JSON kontrolü bilinmiyor. Açık gönderme artık son bağımsız karşılaştırma sorusundan doğrudan açılıyor.

Toplam 122 Python ve 15 DOM mantık testi yerel ortamda başarılı. Yeni regresyonlar bildirilen soruyu yeniden yazım modeli olmadan çözmeyi, başka konu çiftlerini, tırnak/ASCII/sayı varyantlarını, mevcut yıl öncülünü korumayı, son konu değişimini ve yanlış isim/üçlü karşılaştırmada otomatik bağlam eklememeyi kapsar. Model tabanlı yolun bozuk JSON/şema ve sayı değişimi reddi korunur. Arayüz güvenli ret açıklamasını gösterir; bilinmeyen hata içeriğini basmaz.

Bu sonuç takip sorusunun arama metninin çözümünü doğrular; gerçek PDF'lerde bitki örtüsü bilgisinin bulunması ve gerçek Ollama cevabının doğruluğu ayrıca denenmelidir.

### Bildirilen dağınık karşılaştırma cevabı — 2026-09-19

Bağlam çözümü gerçek denemede çalıştı; ancak bitki örtüsü sorusunda iklim, yer şekli ve kategori listelerini taşıyan geniş PDF parçaları cevap gibi birleştirildi. Bu çıktı doğru atıf biçimine sahip olsa da soruyu anlamlı biçimde yanıtlamadığı için başarısız kabul edildi.

Arama artık iki karşılaştırma tarafı için ayrı sorgular üretir ve konuya özel parçaları katalog satırlarından önce sıralar. Doğrulayıcı kanıtı yetersiz bulursa karşılaştırmalarda extractive fallback kapatılır; sistem dağınık metni göstermek yerine kaynak yetersiz döner. Regresyon kümesi, doğrudan Karadeniz/orman ve Akdeniz/maki parçalarının ilk iki sıraya gelmesini ve yalnızca kategori listesi varken cevap üretilmemesini kapsar. Toplam 125 Python ve 15 DOM mantık testi yerel Linux'ta başarılıdır; gerçek PDF/Ollama tekrarı yine gereklidir.

### Tam kanıt kapsaması ve çalışma klasörü bağımsızlığı — 2026-09-20

Çok ölçütlü sorularda gerekli konu × ölçüt hücreleri, vektör/BM25 kısa listesinin dışında kalsa bile bütün yetkili ve hazır parçalardan seçilir. Regresyon testi iki gerçek kanıtı 80 yüksek benzerlikli dikkat dağıtıcı arasından bulur; API testi sıralayıcıların yalnızca yanlış parçayı döndürdüğü durumda bile dört gerekli hücreyi tamamlar. Göreli SQLite/Qdrant yollarının farklı terminal klasörlerinde farklı veri alanlarına dönüşmemesi ayrıca test edilir.

Windows başlatma betiği yalnızca bu proje köküne ait Uvicorn süreçlerini hedefler ve `/health` yanıtındaki RAG sürümünü kaynak kodla karşılaştırır. Gerçek yüklenmiş bitki PDF'siyle yapılan uçtan uca kabul denemesinde bildirilen Karadeniz/Akdeniz sorusu dört kanıt hücresiyle `structured_evidence` sonucu verdi.

Son doğrulamada 186 Python testi ve 17 JavaScript arayüz mantığı testi başarılıdır. Gerçek PDF kabul denemesi metin çıkarma, parçalama, SQLite ve gömülü Qdrant'ı kapsar; yerel Ollama'nın bütün serbest sorulardaki doğruluğuna ilişkin genel bir garanti değildir.

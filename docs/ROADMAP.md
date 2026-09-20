# Yol haritası

Durumlar: tamamlanan depo hazırlığı, yerelde doğrulanan davranış ve planlanan uygulama değişikliği ayrı tutulur.

## 0. Depo ve sürümleme

- [x] README, mimari, kalite ve güvenlik belgeleri.
- [x] Güvenli paylaşım kontrolü ve gün sonu aracı.
- [x] Güncel çalışan uygulama kodunun ilk aktarımı.
- [x] Aktarılan uygulamada otomatik API/RAG testlerini çalıştırmak.
- [ ] Açık kaynak lisansını seçmek.

Kabul: app/main.py ve pyproject.toml depo kökünde bulunur; kişisel materyal yoktur; tam test çıktısı kaydedilir. Uygulamanın aktarımı bitmeden çalışır bir GitHub sürümü ilan edilmez.

## 1. Genel Sohbet

- [x] API'de isteğe bağlı ders filtresi.
- [x] Sunucuda hesaplanan tüm yetkili derslerde hibrit arama.
- [x] Doküman yönetiminin ders bazlı kalması.
- [x] Sohbetin varsayılan kapsamının tüm yetkili dersler olması.
- [x] Ders + dosya + sayfa gösteren kaynak kartları.
- [x] Genel sorgular için veriyi koruyan ölçüm/şema geçişi.
- [x] Araştırma ajanının genel/filtreli kapsamda güvenli arama araçları.

Otomatik API, depolama ve arayüz mantığı kontrolleri başarılı. Gerçek yerel modeller ve kişisel PDF'lerle aşağıdaki kabul senaryoları kullanıcı bilgisayarında ayrıca denenecek.

Kabul:

- Aynı sohbetten Tarih, Coğrafya ve Vatandaşlık soruları ders değiştirmeden cevaplanır.
- Başka kullanıcının yetkisiz dokümanı bulunamaz veya indirilemez.
- İsteğe bağlı filtre, aramayı gerçekten seçilen derse sınırlar.
- Kaynak olmayan soruya ilişkisiz PDF kaynak gösterilmez.

## 2. Sohbet bağlamı

- [x] Sınırlı sayıda tur ve toplam metin boyutu (4 tur / 6000 karakter).
- [x] Takip sorusunu bağımsız arama sorusuna dönüştürmek.
- [x] Oturum ve kullanıcılar arasında bağlam ayrımı.
- [x] Temizle düğmesi ve açık saklama politikası.
- [ ] Bunu kısalt / karşılaştır / örnek ver akışlarını gerçek Ollama ve notlarla doğrulamak.

Kabul: önceki bir cevabı değiştiren takip sorusu çalışır; kaynak etiketleri turlar arasında yanlış bağlanmaz; önceki model cevabı tek başına kanıt kabul edilmez.

## 3. Kalite değerlendirmesi

- [x] Her ders için başlangıç etiketli sorular ve beklenen doğrulama parçaları.
- [ ] Yazım varyantlarını genişletmek; yanlış öncül ve konu dışı başlangıç soruları hazır.
- [ ] Soru tekrarını cevap saymayan kontroller.
- [x] Kaynak bulunmasına rağmen cevap verilememe durumunu sonuç bazında kaydetmek.
- [x] Kaynak kapsaması, cevap kapsaması, çekimserlik başarısı ve gecikmeyi ayrı raporlamak.
- [ ] Başlangıç kümesini gerçek yerel model ve kişisel notlarla çalıştırıp insan değerlendirmesini eklemek.

Kabul: ölçümlerde payda, soru kümesi, model sürümü ve donanım belirtilir; arama puanı doğruluk olasılığı olarak sunulmaz.

## 4. Performans ve işletim

- [ ] Soğuk/sıcak sorgu süresi ve p50/p95.
- [ ] CPU/GPU/VRAM ve context boyutu etkisi.
- [ ] Belgelerde token/parça boyutu ve indeksleme süresi.
- [ ] Yedek geri yükleme denemesi.
- [ ] Bağımlılıkları doğrulanmış sürümlere sabitlemek.

## Daha sonraki seçenekler

OCR, gelişmiş ajan araçları, vLLM, SQL Server, SSO, kurumsal dağıtım veya SAP entegrasyonu ancak kullanım ihtiyacı ve kabul kriterleri belirlenince değerlendirilir. Bu başlıklar mevcut sürümün özellikleri gibi sunulmaz.

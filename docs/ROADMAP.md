# Yol haritası

Durumlar: tamamlanan depo hazırlığı, yerelde doğrulanan davranış ve planlanan uygulama değişikliği ayrı tutulur.

## 0. Depo ve sürümleme

- [x] README, mimari, kalite ve güvenlik belgeleri.
- [x] Güvenli paylaşım kontrolü ve gün sonu aracı.
- [ ] Güncel çalışan uygulama kodunun ilk aktarımı.
- [ ] Aktarılan uygulamada otomatik API/RAG testlerini çalıştırmak.
- [ ] Açık kaynak lisansını seçmek.

Kabul: app/main.py ve pyproject.toml depo kökünde bulunur; kişisel materyal yoktur; tam test çıktısı kaydedilir. Uygulamanın aktarımı bitmeden çalışır bir GitHub sürümü ilan edilmez.

## 1. Genel Sohbet

- [ ] API'de isteğe bağlı ders filtresi.
- [ ] Sunucuda hesaplanan tüm yetkili derslerde hibrit arama.
- [ ] Doküman yönetiminin ders bazlı kalması.
- [ ] Sohbetin varsayılan kapsamının tüm yetkili dersler olması.
- [ ] Ders + dosya + sayfa gösteren kaynak kartları.
- [ ] Genel sorgular için veriyi koruyan ölçüm/şema geçişi.

Kabul:

- Aynı sohbetten Tarih, Coğrafya ve Vatandaşlık soruları ders değiştirmeden cevaplanır.
- Başka kullanıcının yetkisiz dokümanı bulunamaz veya indirilemez.
- İsteğe bağlı filtre, aramayı gerçekten seçilen derse sınırlar.
- Kaynak olmayan soruya ilişkisiz PDF kaynak gösterilmez.

## 2. Sohbet bağlamı

- [ ] Sınırlı sayıda tur ve toplam metin boyutu.
- [ ] Takip sorusunu bağımsız arama sorusuna dönüştürmek.
- [ ] Bunu kısalt / karşılaştır / örnek ver akışları.
- [ ] Oturum ve kullanıcılar arasında bağlam ayrımı.
- [ ] Temizle düğmesi ve açık saklama politikası.

Kabul: önceki bir cevabı değiştiren takip sorusu çalışır; kaynak etiketleri turlar arasında yanlış bağlanmaz; önceki model cevabı tek başına kanıt kabul edilmez.

## 3. Kalite değerlendirmesi

- [ ] Her ders için etiketli sorular ve doğru kaynak parçaları.
- [ ] Yazım varyantları, yanlış öncül ve konu dışı sorular.
- [ ] Soru tekrarını cevap saymayan kontroller.
- [ ] Kaynak bulunmasına rağmen cevap verilememe durumlarını ölçmek.
- [ ] Recall@k, cevap doğruluğu, kaynak desteği ve reddetme başarısını ayrı raporlamak.

Kabul: ölçümlerde payda, soru kümesi, model sürümü ve donanım belirtilir; arama puanı doğruluk olasılığı olarak sunulmaz.

## 4. Performans ve işletim

- [ ] Soğuk/sıcak sorgu süresi ve p50/p95.
- [ ] CPU/GPU/VRAM ve context boyutu etkisi.
- [ ] Belgelerde token/parça boyutu ve indeksleme süresi.
- [ ] Yedek geri yükleme denemesi.
- [ ] Bağımlılıkları doğrulanmış sürümlere sabitlemek.

## Daha sonraki seçenekler

OCR, gelişmiş ajan araçları, vLLM, SQL Server, SSO, kurumsal dağıtım veya SAP entegrasyonu ancak kullanım ihtiyacı ve kabul kriterleri belirlenince değerlendirilir. Bu başlıklar mevcut sürümün özellikleri gibi sunulmaz.

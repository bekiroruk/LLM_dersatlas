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

Uygulama aktarımı sonrası bu örnekler fake model/vector store testlerine eklenmeli ve gerçek dokümanlarla kontrollü bir değerlendirme yapılmalıdır.

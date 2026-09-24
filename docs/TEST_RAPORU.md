# Doğrulama raporu — 24 Eylül 2026

## Sonuç

Yerel Linux/Python 3.12 ortamında **228 Python testi** ve **19 JavaScript
arayüz mantığı testi** başarılıdır. Python testlerinde atlama başarı sayılmaz.
Sözdizimi ve paylaşım kapsamı kontrolleri de geçmiştir.

Kullanıcının Windows/Ollama kabulünde `source-contract-v14`, bildirilen Karadeniz–Akdeniz yağış ve bitki örtüsü karşılaştırmasını doğru, temiz ve kaynaklı üretmiştir.
Son `adaptive-agent-v17` kabulünde hazır kaynaklı uygulama doğruluğu 1,0; p50
8,9 saniye ve p95 15,0 saniyedir.

## Doğrulanan alanlar

| Alan | Sonuç | Kapsam |
| --- | --- | --- |
| API ve oturum güvenliği | Başarılı | Kimlik doğrulama, CSRF/origin, rol ve kaynak erişimi |
| Çok dersli genel arama | Başarılı | Sahiplik/üyelik birleşimi, isteğe bağlı ders filtresi, yetki iptali |
| RAG kaynak sözleşmesi | Başarılı | Kaynaksız çekimserlik, atıf doğrulama, yanlış kaynak reddi |
| Araştırma ajanı | Başarılı | Yalnızca `search_notes`, kapsam aşımı/yazma/shell/ağ/SQL reddi, tur sınırı |
| Uyarlamalı ajan hızı | Başarılı | Yeterli ilk kanıtta planlama atlama, boş aramada devam, kısa araç üretim bütçesi ve süre görünürlüğü |
| Sohbet bağlamı | Başarılı | 4 tur/6000 karakter, takip sorusu, kapsam değişimi, temizleme |
| İklim karşılaştırması regresyonu | Başarılı | Bozuk PDF tablosu, eksik ilişki, kırpılmış hücre ve sınav notu temizliği |
| Soru kataloğu ve kişi adı regresyonu | Başarılı | Cevapsız soru listesini kanıt saymama; bozuk hükümdar adını reddetme |
| Fetih olay kanıtı tamamlama | Başarılı | Tarih ve hükümdarı kısa liste dışında bulma; tek kanıtta güvenli ret |
| Genel karşılaştırma kanıt dengesi | Başarılı | Ortak isimli iki konuyu ayrı arama; ayrı sayfalardaki kanıtları dengeleme; çekimser modelde kaynak satırı; tek taraflı kanıtta güvenli ret |
| Dönem–olay ilişkisi ve kaynak meta temizliği | Başarılı | Dönem aralığını fermanın ilan aralığına dönüştürmeme; PDF başlığı, bölüm numarası ve kaynak hakkındaki meta dili cevapta reddetme |
| Temiz karşılaştırma geri dönüşü | Başarılı | Hatalı model cevabından sonra iki tarafı ayrı başlıklarla sunma; komşu konu, numaralı başlık, çalışma etiketi ve tekrarları ayıklama |
| Karşılaştırma öznesi ve dönem ayrımı | Başarılı | Fermanı açık özne yapan kanıtı dönem sınırından önce seçme; “X ile benzer” referansını X'e özgü fark saymama |
| İddia ilişkisi doğrulaması | Başarılı | “Etkili” kişiyi ilan eden kişiye dönüştürmeme; dönem bitişini ferman süresi yapmama; bağlı bağımsız iddiaları ayrı denetleme |
| Depolama ve geçiş | Başarılı | SQLite şema geçişi, rollback, yedek hatası ve Qdrant yetki filtresi |
| Depo güvenliği | Başarılı | İzinli yollar, büyük dosya/secret biçimleri, indeks ve başlatıcı kontrolleri |
| Arayüz mantığı | 19/19 | Modern tasarım sistemi, karakter sayacı, genel kapsam, filtre, ajan, hafıza, gecikmiş yanıt ve kaynak gösterimi |
| Arayüz önbellek sözleşmesi | Başarılı | Sürümlü CSS/JS URL'leri; HTML ve statik dosyalarda `no-store` / `no-cache` |

## Gerçek model kabul aracı

`samples/general_evaluation.json`, Tarih, Coğrafya, Vatandaşlık ve kaynak-dışı sorulardan oluşan sekiz soruluk başlangıç kümesidir. Aşağıdaki komut uygulamayı doğru sürümle başlatır ve gerçek yerel Ollama modeliyle benzersiz adlı genel ajan raporu üretir:

```powershell
.\scripts\acceptance.ps1
```

Rapor şu ölçüleri ayrı tutar:

- kaynak metninde beklenen kısa parçaların kapsaması;
- cevap metninde beklenen kısa parçaların kapsaması;
- cevaplanabilirlik/çekimserlik sonucu eşleşmesi;
- sorgu p50 ve p95 süresi;
- seçilen kaynakların dersleri ve sayısı.

Kısa metin eşleşmesi semantik doğruluk veya doğruluk olasılığı değildir. Her cevap ve kaynak insan tarafından ayrıca incelenmelidir.

## Sınırlar

- CI, deterministik model test çifti kullanır; gerçek Qwen yanıt kalitesini kanıtlamaz.
- Arayüz kontrolleri DOM mantık testidir; duyarlı CSS ve azaltılmış hareket kuralları doğrulanır ancak gerçek tarayıcıdaki piksel düzeyi görünümün yerini tutmaz.
- SQL Server/ODBC, Docker GPU ve OCR üretim senaryoları bu koşuda çalıştırılmadı.
- Kişisel PDF'ler, veritabanı, Qdrant verisi ve yerel değerlendirme çıktıları GitHub'a gönderilmez.

# Doğrulama raporu — 21 Eylül 2026

## Sonuç

Yerel Linux/Python 3.12 ortamında **201 Python testi** ve **17 JavaScript arayüz mantığı testi** başarılıdır. Python testlerinde atlama başarı sayılmaz. Sözdizimi ve paylaşım kapsamı kontrolleri de geçmiştir.

Kullanıcının Windows/Ollama kabulünde `source-contract-v14`, bildirilen Karadeniz–Akdeniz yağış ve bitki örtüsü karşılaştırmasını doğru, temiz ve kaynaklı üretmiştir.

## Doğrulanan alanlar

| Alan | Sonuç | Kapsam |
| --- | --- | --- |
| API ve oturum güvenliği | Başarılı | Kimlik doğrulama, CSRF/origin, rol ve kaynak erişimi |
| Çok dersli genel arama | Başarılı | Sahiplik/üyelik birleşimi, isteğe bağlı ders filtresi, yetki iptali |
| RAG kaynak sözleşmesi | Başarılı | Kaynaksız çekimserlik, atıf doğrulama, yanlış kaynak reddi |
| Araştırma ajanı | Başarılı | Yalnızca `search_notes`, kapsam aşımı/yazma/shell/ağ/SQL reddi, tur sınırı |
| Sohbet bağlamı | Başarılı | 4 tur/6000 karakter, takip sorusu, kapsam değişimi, temizleme |
| İklim karşılaştırması regresyonu | Başarılı | Bozuk PDF tablosu, eksik ilişki, kırpılmış hücre ve sınav notu temizliği |
| Soru kataloğu ve kişi adı regresyonu | Başarılı | Cevapsız soru listesini kanıt saymama; bozuk hükümdar adını reddetme |
| Depolama ve geçiş | Başarılı | SQLite şema geçişi, rollback, yedek hatası ve Qdrant yetki filtresi |
| Depo güvenliği | Başarılı | İzinli yollar, büyük dosya/secret biçimleri, indeks ve başlatıcı kontrolleri |
| Arayüz mantığı | 17/17 | Genel kapsam, filtre, ajan, hafıza, gecikmiş yanıt ve kaynak gösterimi |

## Gerçek model kabul aracı

`samples/general_evaluation.json`, Tarih, Coğrafya, Vatandaşlık ve kaynak-dışı sorulardan oluşan sekiz soruluk başlangıç kümesidir. Aşağıdaki komut gerçek yerel Ollama modeliyle genel ajan raporu üretir:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate.py `
  --mode agent `
  --with-generation `
  --dataset samples\general_evaluation.json `
  --output output\agent-evaluation.json
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
- Arayüz kontrolleri DOM mantık testidir; görsel tarayıcı ve mobil uyumluluk testi değildir.
- SQL Server/ODBC, Docker GPU ve OCR üretim senaryoları bu koşuda çalıştırılmadı.
- Kişisel PDF'ler, veritabanı, Qdrant verisi ve yerel değerlendirme çıktıları GitHub'a gönderilmez.

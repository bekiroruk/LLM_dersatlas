# Katkı rehberi

## Kapsam

DersAtlas ders dokümanları üzerinden yerel kaynaklı çalışma asistanıdır. Kullanıcı verisi, gerçek ders PDF'leri ve model dosyaları katkıya dahil edilmez.

Henüz bir açık kaynak lisansı seçilmedi. Kodun yeniden kullanımı ve katkıların lisans koşulları yaygın dağıtım öncesinde açıklığa kavuşturulmalıdır.

## Küçük ve doğrulanabilir değişiklikler

- Bir değişiklik bir davranışa odaklansın.
- Yeni özellik ile hata düzeltmesini mümkünse ayrı commit'lerde tut.
- Geçmişteki hatayı tekrar eden negatif test ve doğru davranışı koruyan pozitif test ekle.
- RAG değişikliğinde arama, cevaplama ve kaynak desteğini ayrı değerlendir.
- Kullanıcı yetkilerini Genel Sohbet uğruna kaldırma.
- Test atlamayı başarı sayma.

Commit örnekleri:

- fix(rag): yanlış kelime eşleşmesini engelle
- feat(chat): tüm yetkili derslerde arama ekle
- test(rag): konu dışı kaynak regresyonunu ekle
- docs: mimari ve çalışma durumunu güncelle

## Kontroller

Depo araçlarını test etmek:

```powershell
py -3.12 scripts\run_tests.py
py -3.12 scripts\repo_guard.py
```

Uygulama kodu aktarılınca bağımlılıkların bulunduğu proje sanal ortamıyla aynı kontrolleri çalıştır. Testler gerçek kişisel dosyalar yerine sentetik ve anonim fixture kullanmalı.

## Pull request

Ne değişti, neden değişti, nasıl test edildi ve kalan sınırlamaları yaz. Tamamlanmayan veya çalıştırılmayan kontrolü açıkça belirt. Ekran görüntülerinde isim, kişisel dosya adı, token, belge metni veya hassas bilgiler bulunmamalı.

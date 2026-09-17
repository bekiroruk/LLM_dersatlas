# Proje durumu

İlk uygulama kaynak kodu aktarımı: [78f052f](https://github.com/bekiroruk/LLM_dersatlas/commit/78f052fe0f16d50d59e1ef10f306d51acb0893ed).

## GitHub

Güncel uygulama kodu, web arayüzü, testler, dokümantasyon ve güvenli gün sonu araçları repoda. İlk aktarımda 39 dosya eklendi. Henüz bir release veya yeni sürüm etiketi yayımlanmadı.

Ders materyalleri, yerel ortam ayarları, veritabanı ve vektör indeksleri aktarılmadı.

## Yerel uygulama

- Windows, Python 3.12 ve yerel Ollama modelleriyle kullanılıyor.
- Tarih, Coğrafya ve Vatandaşlık dokümanları yerel uygulamaya yüklenmiş durumda.
- Kaynak kartları ve ders bazlı arama mevcut.
- Fethedildi/Fethiye yanlış eşleşmesi için hedefli düzeltme yapıldı.
- Kullanıcı üç hedefli senaryonun beklenen şekilde cevaplandığını bildirdi.

## Doğrulama

Kullanıcının paylaştığı Windows çıktısında uygulama ve depo araçlarının 60 testi başarılı. Sözdizimi ve Git indeksindeki paylaşım kontrolleri de ilk aktarım öncesinde başarılı tamamlandı.

Bu sonuç, tüm ders belgeleriyle gerçek model doğruluğunu veya güvenlik sertifikasını kanıtlamaz. GitHub Actions sonuçları yerel test kaydından ayrı takip edilir.

## Bilinen sınırlamalar

- Genel Sohbet henüz eklenmedi; mevcut uygulama ders filtresine bağlı.
- Takip soruları için sohbet hafızası henüz eklenmedi.
- Islahat Fermanı'nın tarihi gibi sorularda doğru bilgiyi içeren yeni belgenin bulunması ve yeterli cevabın üretilmesi ayrıca doğrulanmalı.
- İddia düzeyinde kaynak desteği, sınırlı heuristik kontrollerden daha geniş değerlendirme gerektirir.
- Otomatik Windows dosya senkronizasyonu veya zamanlanmış push görevi kurulmadı.

## Sıradaki adım

Genel Sohbet: kullanıcının erişebildiği tüm derslerde arama, isteğe bağlı ders filtresi ve kaynaklarda ders adının gösterilmesi. Takip soruları için sohbet bağlamı daha sonraki aşama.

# Proje durumu

İlk uygulama kaynak kodu aktarımı: [78f052f](https://github.com/bekiroruk/LLM_dersatlas/commit/78f052fe0f16d50d59e1ef10f306d51acb0893ed).

## GitHub

Güncel uygulama kodu, web arayüzü, testler, dokümantasyon ve güvenli gün sonu araçları repoda. İlk aktarımda 39 dosya eklendi. Henüz bir release veya yeni sürüm etiketi yayımlanmadı.

Ders materyalleri, yerel ortam ayarları, veritabanı ve vektör indeksleri aktarılmadı.

## Yerel uygulama

- Windows, Python 3.12 ve yerel Ollama modelleriyle kullanılıyor.
- Tarih, Coğrafya ve Vatandaşlık dokümanları yerel uygulamaya yüklenmiş durumda.
- Genel Sohbet varsayılan tüm erişilebilir derslerde arar; tek ders filtresi isteğe bağlıdır.
- Doküman düzenleme seçimi sohbetin kapsamını değiştirmez; kaynaklarda ders adı, dosya ve konum bulunur.
- Araştırma ajanı mevcut: yalnızca yetkili notlarda ek arama yapar; komut/ağ/veri değiştirme aracı yoktur.
- Fethedildi/Fethiye yanlış eşleşmesi için hedefli düzeltme yapıldı.
- Kullanıcı üç hedefli senaryonun beklenen şekilde cevaplandığını bildirdi.

## Doğrulama

Kullanıcının paylaştığı Windows çıktısında uygulama ve depo araçlarının 60 testi başarılı. Sözdizimi ve Git indeksindeki paylaşım kontrolleri de ilk aktarım öncesinde başarılı tamamlandı.

Bu sonuç, tüm ders belgeleriyle gerçek model doğruluğunu veya güvenlik sertifikasını kanıtlamaz. GitHub Actions sonuçları yerel test kaydından ayrı takip edilir.

Genel Sohbet değişikliğinde yerel Linux/Python 3.12 ortamında 92 Python testi ve Node.js ile 8 arayüz mantığı testi başarılı. Testler gerçek SQLite ve gömülü Qdrant kullanır; LLM deterministik test çiftidir. Eski şemanın yedeği, veri koruması ve yarıda kesilen geçişin rollback'i test edildi. Yerel test adresi bu ortamın tarayıcısında engellendiği için gerçek görsel tarayıcı kontrolü yapılamadı.

Güncel Linux/Windows CI durumu [GitHub Actions](https://github.com/bekiroruk/LLM_dersatlas/actions) üzerinden ayrı doğrulanır.

## Bilinen sınırlamalar

- Takip soruları için sohbet hafızası henüz eklenmedi.
- Genel aramada toplam 30.000 parça koruma sınırı var; aşılırsa ders filtresi kullanılmalı.
- Eski SQL Server şeması için nullable alan geçişi DBA tarafından ayrıca yapılmalı; bu ortamda SQL Server testi çalıştırılmadı.
- Islahat Fermanı'nın tarihi gibi sorularda doğru bilgiyi içeren yeni belgenin bulunması ve yeterli cevabın üretilmesi ayrıca doğrulanmalı.
- İddia düzeyinde kaynak desteği, sınırlı heuristik kontrollerden daha geniş değerlendirme gerektirir.
- Otomatik Windows dosya senkronizasyonu veya zamanlanmış push görevi kurulmadı.

## Sıradaki adım

Önce kullanıcı bilgisayarında [Genel Sohbet kabul denemeleri](GENERAL_CHAT.md). Ardından sınırlı takip soruları/sohbet bağlamı. Yeni proje ZIP'i veya notları yeniden yükleme gerekli değil.

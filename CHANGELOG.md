# Changelog

Yalnızca gerçekten yapılan değişiklikler kaydedilir. Planlanan özellikler [Roadmap](docs/ROADMAP.md) içindedir. Gün değişmesi veya GitHub katkı grafiği için boş commit oluşturulmaz.

## Unreleased

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

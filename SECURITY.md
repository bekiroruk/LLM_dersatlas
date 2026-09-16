# Güvenlik ve veri paylaşımı

## Paylaşılmayan veri

Bu herkese açık repo sadece proje kodu, belgeleri ve anonim örnekleri içindir. Şunlar yüklenmez:

- Kişisel ders notları, gerçek PDF/DOCX ve doküman metinleri.
- .env ve gerçek bağlantı ayarları.
- Kullanıcı/oturum veritabanı, SQL dosyaları ve vektör indeksleri.
- Ollama/model ağırlıkları.
- Yedekler, loglar, kimlik bilgileri ve özel anahtarlar.

.gitignore, daha önce izlenen dosyaları veya Git geçmişini temizlemez. Repo guard, tüm kişisel bilgi ve secret çeşitlerini tespit eden kapsamlı bir ürün değildir.

## Sorun bildirme

Gizli bilgi içermeyen bir güvenlik sorunu için anonim bir yeniden üretim örneği hazırlanabilir.

**Parola, token, gerçek belge metni veya kullanıcı verisi içeren bulguları public issue'ya yapıştırma.** Repo ayarlarında özel güvenlik bildirimi etkinse GitHub'ın private vulnerability reporting yolunu kullan. Bu ayarın etkinleştirildiği varsayılmaz. Özel bir kanal yoksa hassas ayrıntılar olmadan maintainer'a özel kanal talebini ilet.

## Yanlışlıkla secret paylaşıldıysa

Paylaşılan credential yetkili yönetim kanalından iptal edilmeli/değiştirilmeli; sonra erişim ve Git geçmişi temizliği ayrı bir planla ele alınmalıdır. Dosyayı yalnızca son commit'ten silmek, geçmişteki sızıntıyı ortadan kaldırmaz. Otomatik history rewrite veya force-push yapılmaz.

## Yerel çalışma

- Varsayılan servis adresi 127.0.0.1 olarak korunur.
- Genel Sohbet yalnızca kullanıcının yetkili derslerinde arar.
- Yerel LLM çalışması tek başına güvenlik sertifikası değildir; ağ çıkışı, telemetry, dosya izinleri ve yedek erişimi ayrıca denetlenir.
- Doğrulanmamış model cevabı eğitimsel veya hukuki doğruluk garantisi sayılmaz.

Sabit bir güvenlik yanıt süresi veya sertifikalı/üretime hazır sürüm taahhüdü yoktur.

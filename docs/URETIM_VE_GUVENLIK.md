# Kurumsal geçiş, SQL Server ve güvenlik

## 1. İş ilanıyla eşleştirme

| İlandaki beklenti | Bu projede karşılığı | Kalan kurumsal adım |
| --- | --- | --- |
| On-premise LLM | Ollama ve yerel modeller | GPU sunucusu, erişim politikası, yük testi |
| Python otomasyon | Belge işleme, kuyruğu takip, yedek ve değerlendirme betikleri | Zamanlayıcı, ayrı işleyici, merkezi gözlemleme |
| RAG / embedding / vektör DB | BGE-M3, Qdrant, BM25/RRF, kaynaklar | Gerçek doküman değerlendirmesi ve ölçekli lexical indeks |
| API / SQL | FastAPI, SQLAlchemy, SQLite/SQL Server seçeneği | Sürücü, veri geçişi, migration, erişim yönetimi |
| Dashboard | Gerçek sorgu süreleri ve geri bildirim | Prometheus/Grafana, GPU ve kapasite metrikleri |
| Agent | Salt okunur, ders kapsamlı araç çağırma | İşleme özel güvenlik ve onay akışları |
| SAP entegrasyonu | Ayrı adaptör sınırı tasarlandı | Gerçek SAP sandbox, izinler ve bağlantı geliştirmesi |
| PyTorch/Hugging Face deneyimi | Model ekosistemi ve yerel çıkarım kullanımına giriş | Bu kod PyTorch eğitim deneyimi sağlamaz; ayrı eğitim deneyi gerekir |

Bu proje tek başına ilanın bütün maddelerinde profesyonel deneyim kazandığını göstermez. Özellikle gerçek SAP ve model eğitimi bu sürümün dışında kalır.

## 2. SQL Server'a geçiş

Vektörleri Qdrant'ta tutmaya devam edeceğiz; SQL Server hesap, belge, ders ve metin kayıtlarını yönetecek. Bu iki veritabanı farklı görevler yapar.

1. Yetkili SQL Server ortamında boş `DersAtlas` veritabanını DBA ile oluştur.
2. Ayrı uygulama kullanıcısı kullan; `sa` hesabını uygulamaya bağlama.
3. Python'un çalıştığı sisteme Microsoft ODBC Driver 18 kur. Proje ortamına `pip install -e ".[sqlserver]"` uygula.
4. `.env` dosyasında `DATABASE_URL` değerini değiştir. Kullanıcı/parola özel karakterlerini URL-encode et. URI'yi GitHub'a veya ekran görüntüsüne koyma.
5. Örnek şekil: `mssql+pyodbc://dersatlas:URL_ENCODED_PASSWORD@SQL_HOST/DersAtlas?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no`.
6. Sertifika güven zincirini doğru kur. Sertifika doğrulamasını kapatmayı üretim çözümü sayma.
7. Başlangıç şeması `create_all` ile oluşturulur. Sonraki değişiklikler için Alembic migration süreci eklenmelidir; bu sürüm mevcut şemayı otomatik yükseltmez.
8. SQLite'daki mevcut veriler bağlantı adresini değiştirince kendiliğinden SQL Server'a taşınmaz. Yeni boş sistemde hesapları/dersleri oluşturup belgeleri yeniden yüklemek küçük arşiv için en kolay yoldur.
9. Kimlikleri koruyarak veri taşıyacaksan kullanıcılar, dersler, üyelikler, belgeler ve parçaları ilişkili kimlikleriyle aktar; orijinal dosyaları da koru. Qdrant ve SQL kimlik eşleşmesini test et. Doğrulanmış otomatik migration betiği bu pakette yoktur.
10. Kullanıcı izinleri, Türkçe Unicode metinler, yedek/geri yükleme, transaction ve bağlantı kesintisi testlerini tamamla.

Standart Docker imajında ODBC sistem sürücüsü yoktur; Docker içinde SQL Server bağlantısı istiyorsan ayrıca kurumca gözden geçirilmiş ODBC içeren bir imaj gerekir. Hazır compose dosyası SQLite kullanır; yalnızca `.env` içindeki veritabanı adresini değiştirmen Docker ortamındaki sabit ayarı değiştirmez. [SQLAlchemy'nin SQL Server rehberi](https://docs.sqlalchemy.org/en/20/dialects/mssql.html).

## 3. SAP nerede duracak?

Tarih uygulaması SAP'ye ihtiyaç duymaz. İleride kurumsal veriyle aynı RAG altyapısı kullanılacaksa bağlantı, LLM ile SAP arasında serbest bir köprü olarak kurulmaz.

```mermaid
flowchart TD
  A["Yetkili API isteği"] --> P["İş kuralı ve erişim kontrolü"]
  P --> S["SAP adaptörü"]
  S --> R["Salt okunur veri servisi"]
  R --> D["SAP sandbox / ERP"]
  P --> W["Yazma işlemi taslağı"]
  W --> H["İnsan onayı ve denetim"]
  H --> T["Ayrı yetkili işlem yürütücüsü"]
```

| Yöntem | Kullanım alanı | DersAtlas açısından yaklaşım |
| --- | --- | --- |
| OData / REST | HTTP üzerinden izinli veri servisleri | Uygun servis varsa salt okunur başlangıç adayı |
| RFC | SAP fonksiyonlarını uzaktan çağırma | Yetkili fonksiyon allowlist'i; resmi SDK ve sistem kurulumu gerekir |
| BAPI | SAP iş nesnesi işlemleri | Okuma/yazma yetkileri ve transaction semantiği ayrı incelenir |
| IDoc | Asenkron kurumsal mesaj alışverişi | Kuyruk, tekrar deneme, idempotency ve izlenebilirlik gerekir |

Gerçek entegrasyon için SAP sürümü/ürünü, gateway/servis adı, sandbox, ağ erişimi, kullanıcı yetkileri ve iş gereksinimi gerekir. Bu bilgiler olmadan çalışan SAP bağlantısı yapıldığını iddia edemeyiz. LLM'e SAP parolası, serbest RFC adı, arbitrary URL veya serbest SQL verilmeyecek.

## 4. Şimdiden uygulanan kontroller

- Parolalar PBKDF2-HMAC-SHA256, ayrı rastgele salt ve 600.000 iterasyonla saklanır.
- Oturum token'ı rastgele üretilir; tarayıcıda HttpOnly ve SameSite=Strict cookie, SQL'de token hash'i bulunur.
- Kullanıcı kimliği oturumdan çıkarılır. Ders, belge, kaynak indirme ve arama uçlarında sunucu taraflı yetki kontrolü vardır.
- Tarayıcı yazma isteklerinde özel başlık ve Origin kontrolü uygulanır. CORS açılmamıştır; tarayıcıdan doğrudan model servisine çağrı yapılmaz.
- Dosya adı dosya yolu olarak kullanılmaz; dosya boyutu sınırı ve DOCX açılmış boyut kontrolü vardır.
- Metinler arayüze `textContent` ile konur; LLM veya PDF içeriği HTML olarak çalıştırılmaz.
- LLM'in tek aracı ders içinde not aramadır. Adım ve araç sayısı sınırlıdır.
- Belge içi prompt injection'a karşı talimat/veri ayrımı yapılır; bu yöntem bütün saldırıları durdurma garantisi değildir.
- Silme isteği sonrası belge önce aramadan çıkarılır; fiziksel temizleme işleyicide tamamlanır.
- Yerel port sadece loopback'e açılır. Model servisleri için tarayıcıya API anahtarı verilmez.

## 5. Üretime açmadan önce zorunlu kapılar

1. API testlerinin tamamını gerçek bağımlılıklarla çalıştır; herhangi bir atlanan güvenlik testini geçmiş sayma.
2. Bağımlılıkları başarılı kurulumdan sonra tam sürümlerle kilitle. Şu an pyproject sürüm aralıkları içerir; tekrar üretilebilir bir lockfile değildir. İmaj digest'lerini, model digest'lerini ve lisansları kaydet.
3. Kurumsal SSO/OIDC, hesap kapatma, merkezi oturum iptali ve yetki denetimini ekle. Kullanıcı/parola girişi başlangıç içindir; kurumsal kimlik federasyonu değildir.
4. Reverse proxy üzerinde TLS, `COOKIE_SECURE=true`, doğru `ALLOWED_HOSTS` ve güvenilir proxy ayarları kur. Uygulama ve model portlarını internete açma.
5. Dosya ayrıştırmayı izole, CPU/bellek/zaman limitli worker'a taşı; kötü amaçlı dosya taraması ekle. Mevcut boyut sınırları bütün parser/zip bombası risklerini çözmez.
6. Gerçek veri yedekle, başka ortamda geri yükle, erişim ve kaynak eşleşmesini doğrula. SQL, orijinaller ve vektörler için ortak bir tutarlılık planı kur.
7. Merkezi audit, log saklama/silme politikası, disk şifreleme ve sır yönetimi ekle. Yerel audit tablosu değiştirilemez denetim sistemi değildir.
8. GPU bellek tüketimi, p50/p95 gecikme, eşzamanlı kullanıcı, 30.000 parça sınırı ve embedding kuyruğu için yük testi yap.
9. Çoklu süreç gerekiyorsa gömülü Qdrant ve thread kuyruğundan ayrı Qdrant sunucusu + kalıcı görev kuyruğuna geç. Sadece worker sayısını artırma.
10. Notlardan oluşturulmuş sabit test setinde yanlış kaynak, kaynak yetersizliği, çelişki, prompt injection ve kullanıcılar arası sızıntı testlerini yap.
11. Yalnızca yerel modellerin kullanıldığını, dış trafik ve telemetri politikasını ağ katmanında doğrula. `OLLAMA_NO_CLOUD` tüm sistemde interneti kapatmaz.
12. Uygulamayı kimlerin kullanacağı, hangi dokümanları yükleyebileceği ve ders notlarının telif/erişim koşullarını netleştir.

## 6. Model serving ve eğitim yol ayrımı

Ollama ilk kişisel kurulum için seçildi. Çok sayıda eşzamanlı kullanıcıda vLLM gibi serving seçenekleri kapasite ve GPU ölçümüyle değerlendirilir. Bu değişiklik mevcut `Ollama` adaptörünün yanına ayrı bir sağlayıcı implementasyonu gerektirir; config'e sadece yeni URL yazmak API uyumluluğu sağlamaz.

Fine-tuning, notların güncellenmesi için ilk çözüm değildir. Önce extraction ve retrieval başarısını ölç. Sonraki hedef belirli cevap biçimi, sınıflandırma veya uzman görevse PyTorch/Hugging Face/LoRA ile ayrı eğitim deneyi hazırlanır. Eğitim/test veri ayrımı, GPU bütçesi ve model lisansı bu deneyin ön koşullarıdır.

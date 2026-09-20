# Genel Sohbet ve araştırma ajanı

Yeni proje veya model indirmeden mevcut kurulum güncellenir. Yüklenmiş notlar, dersler ve Qdrant koleksiyonu korunur; yeniden yükleme/indeksleme gerekmez.

## Windows güncellemesi

1. Projeye ait çalışan sunucuyu güvenli biçimde durdur:

```powershell
.\scripts\stop.ps1
```
2. Proje köküne geçip Git durumunu kontrol et ve durdurulmuş verinin yedeğini al:

```powershell
cd C:\Users\Bekir\Desktop\DersAtlas_v0.1.0\dersatlas
git status --short
.\.venv\Scripts\python.exe scripts\backup.py --app-stopped --destination ..\DersAtlas_genel_sohbet_yedek
```

Yedek başarılı değilse güncellemeye geçme. ZIP özel doküman ve hesap verisi içerir; GitHub'a yükleme. MANIFEST.sha256 gibi izin listesi dışında kalan untracked dosyalar paylaşılmaz.

3. GitHub değişikliklerini al:

```powershell
git pull --ff-only origin main
```

Git yerel dosya çakışması/ayrışan geçmiş bildirirse dur; değişiklikleri silerek reset veya force-push yapma. Bu özellik bağımlılık listelerini değiştirmez.

4. Kontrol edip tek süreçle çalıştır:

```powershell
.\.venv\Scripts\python.exe -m compileall -q app scripts tests
.\.venv\Scripts\python.exe scripts\run_tests.py
.\scripts\start.ps1
```

Bir kontrol başarısızsa sonraki komutu çalıştırma. Başlatıcı doğru proje klasörünü, tek Uvicorn sürecini ve çalışan RAG sürümünü denetleyip tarayıcıyı açar. Mevcut eski sekmeyi kullanırsan Ctrl+F5 ile JS/HTML önbelleğini yenile.

## Kullanım

| Kontrol | Davranış |
| --- | --- |
| Soldaki ders seçimi | Yükleme ve doküman düzenleme klasörü; sohbet filtresi değildir |
| Arama kapsamı: Tüm dersler | Kullanıcının erişebildiği tüm derslerin hazır notlarında arama |
| Arama kapsamı: tek ders | Aramayı açıkça seçtiğin dersle sınırlar |
| Kaynaklı cevap · RAG | Hibrit arama, yerel model ve kaynak desteği kontrolleri |
| Araştırma ajanı · çok adımlı | Alt sorularla ek aramalar; aynı yetkili kapsam, ardından kaynaklı cevap |
| Kaynak defteri | Ders adı, dosya adı, PDF fiziksel sayfası/metin konumu ve kaynak bölümü |

Ders filtresi değişince görünen mesajlar silinmez; her mesaj gönderildiği kapsamı gösterir. Ancak takip sorusu hafızası sıfırlanır: önceki kapsamdan bir konunun yeni derse taşınması engellenir. Doküman yönetimindeki sol ders seçimi ve RAG/ajan yöntemi değişimi hafızayı sıfırlamaz.

## Sohbet hafızası

Son en fazla 4 tamamlanmış soru/cevap turu, toplam 6000 karakter sınırıyla yalnızca açık sayfanın RAM'inde tutulur. Uzun cevapların en fazla ilk 1200 karakteri bağlama alınır; eski kaynak etiketleri kaldırılır. En eski turlar önce çıkarılır. Görünen sohbet daha uzun olabilir; tamamı modele gönderilmez.

Temizle, çıkış, sayfa yenileme veya arama filtresi değişimi hafızayı sıfırlar. localStorage/sessionStorage, kalıcı sohbet tablosu ve hesaplar arasında paylaşılan geçmiş yoktur. Sunucu gelen bağlamı yalnızca istek sırasında yerel Ollama ile işler; konuşma veritabanına kaydedilmez. Sorgu ölçümleri yine yalnızca süre/sonuç/geri bildirim metadatasını tutar.

Takip sorusunda önce dar, açık gönderme kuralları denenir: son bağımsız soruda iki konu açıkça karşılaştırılmışsa “bu iki …” aynı isimle eşleştirilip konu adları soruya eklenir. Örneğin ikinci kabul sorusu “Karadeniz ve Akdeniz iklimi açısından bitki örtüsü nasıl farklı?” olur. Bu adım model çağrısı veya iklim bilgisi sözlüğü kullanmaz. “Bunu kısalt” da önceki bağımsız soruyu kısa cevap isteğiyle yeniden aratır.

Diğer göndermelerde yerel model konuyu açıkça belirten bir arama sorusu üretir. “Bağlamla anlaşılan soru” arayüzde görünür. Önceki model cevabı yalnızca göndermeleri çözmeye yardımcı olur; gerçek bilgi sayılmaz ve cevap üreten modele kaynak olarak verilmez. Yeni cevap için belgelerde tekrar yetkili arama yapılır ve mevcut kaynak kontrolleri uygulanır. Konu çözülemezse açıklama istenir; arama adımlarında JSON/şema, belirsizlik veya sayı değişimi gibi güvenli ret nedeni görünür. Eski atıflar yeni cevaba yapıştırılmaz.

Yeni ve açık bir soruda eski konu eklenmez. Gönderme çözümü için geçmiş varsa bir ek yerel model çağrısı yapılabilir; ilk soruda bu çağrı yoktur. Takip sorusu gecikmesi gerçek donanımla ayrıca ölçülmelidir.

API'de history isteğe bağlıdır: en fazla dört question/answer/resolved_question/subject_id nesnesi kabul edilir. Rol, kaynak veya kullanıcı kimliği alanları kabul edilmez. Metin/karakter sınırı ihlalinde 422 döner. Sunucu yalnızca mevcut arama kapsamıyla eşleşen ardışık son turları kullanır; history yetki veya kaynak kapsamını değiştiremez. /api/questions takip sorularını çözer; /api/search bağımsız arama uç noktasıdır.

### Peş peşe kabul denemeleri

Tüm dersler veya Coğrafya filtresiyle aynı sayfada sırayla sor:

1. Karadeniz ve Akdeniz iklimini karşılaştır.
2. Peki bu iki iklimin bitki örtüsü nasıl farklı?
3. Bunu kısalt.
4. İstanbul hangi tarihte ve hangi padişah döneminde fethedildi?

İkinci soruda Karadeniz/Akdeniz adlarıyla açık soru ve bitki örtüsünü destekleyen yeni kaynaklar beklenir. Üçüncü soruda aynı konu kısa anlatılır, belgeler yeniden aranır. Dördüncü soruya iklim konusu eklenmez. Ayrıca Temizle sonrası “bu iki iklim” önceki sohbeti hatırlamamalıdır. Kaynakta istenen bilgi yoksa hafıza bu eksikliği doldurmaz; bilgi/örnek uydurmaması gerekir.

Ajanın tek aracı search_notes(query). Varsayılan 3 tur ve tur başına 2 arama sınırı var. Komut, SQL, internet araması, dosya yazma veya silme aracı yok. Geçersiz araç/kapsam parametresi reddedilir. Ajan ek sorgular nedeniyle RAG'den daha yavaş olabilir; kesin doğru cevap garantisi değildir.

Kaynak olmayan sorulara genel model bilgisinden cevap verilmez. Genel Sohbet, bütün yetkili notlarda sohbet demektir; sınırsız genel kültür modu değildir.

## İlk kabul denemeleri

Arama kapsamını Tüm dersler bırak; sol menüdeki ders önemli değil. Yalnızca notlarında bulunan konuları seç.

| Deneme | Beklenen |
| --- | --- |
| İstanbul hangi tarihte ve hangi padişah döneminde fethedildi? | Tarih kaynağı, tarih/padişah bilgisi |
| Türkiye'de dağların kıyıya paralel uzanmasının sonuçları nelerdir? | Coğrafya kaynağı; dersi değiştirmek gerekmez |
| Yasama, yürütme ve yargı görevleri hangi organlara aittir? | Vatandaşlık kaynağı |
| Coğrafya filtresi + İstanbul'un fethi sorusu | İlgisiz turizm metnini cevap saymamalı; yeterli kanıt yoksa kaynak yetersiz |
| Tarih filtresi + Python'da liste nasıl oluşturulur? | Kaynak yetersiz; sahte tarih atfı yok |
| Tüm dersler + ajan + notlarda bulunan bir karşılaştırma sorusu | Kaynaklı cevap; “Arama ve doğrulama adımlarını göster” altında gerçek adımlar |

Ajan kaynakları yeterli bulursa ek araç çağrısı yapmadan durabilir; her soruda mutlaka üç tur çalışmaz. Doğru yıl tek bir PDF'de bulunuyorsa o PDF'nin erişilebilir ve Hazır olması gerekir; doğru parçanın bulunması ayrıca kontrol edilir. Yıl uygulama koduna sabitlenmez.

## Mevcut SQLite şeması

Genel sorgunun QueryMetric.subject_id değeri null olur. Başlangıçta eski NOT NULL sütun tespit edilirse önce SQLite backup API ile data/schema_backups altında benzersiz DB yedeği alınır. Sadece query_metrics tablosunun bu sütunu nullable yapılır; eski kimlikler, geri bildirimler, süreler, indeksler ve trigger'lar korunur.

Geçiş transaction içindedir ve tekrar çalıştırılabilir. Hata olursa başlangıç durur; geçiş rollback edilir. Bilinmeyen sütun/DDL, dış tablo referansı veya görünümde sessizce değişiklik yapılmaz. Yeni kurulumda geçiş gerekmez. Yedek özel veri içerir ve data klasörüyle birlikte Git dışında kalır.

Bu değişiklik doküman/parça tablolarını veya embedding modelini değiştirmez. Genel aramada 30.000 parça koruma sınırı aşılırsa bir ders filtresi kullan.

## SQL Server

Yeni DB şeması nullable alanla oluşturulur. Eski SQL Server şemasında otomatik DDL çalıştırılmaz: uygulama açık geçiş hatasıyla durur. DBA, yedek ve gerçek kolon tipi/şeması doğrulandıktan sonra query_metrics.subject_id alanını nullable yapmalıdır. Bu ortamda SQL Server geçişi test edilmedi; üretimde ayrıca doğrulanmalıdır.

## Doğrulama sınırı

Güncel `source-contract-v12` sürümünde 189 Python testi ve 17 JavaScript arayüz mantığı testi başarılı. API/depolama testleri gerçek SQLite ve gömülü Qdrant kullanır; model gereken senaryolarda deterministik test çifti vardır. Kullanıcının yüklediği gerçek bitki PDF'si, ayrı doğru yağış satırları ve bildirilen bozuk matris aynı gerçek metin çıkarma, parçalama, SQLite ve gömülü Qdrant yolundan geçirilmiştir. Bildirilen çok ölçütlü iklim sorusu dört gerekli kanıt hücresini doğru iki kaynaktan bulmuş; sütunları kaymış tabloyu ve PDF içindeki ilgisiz toprak/yeraltı suyu yağış ifadelerini kullanmamıştır. Arayüz testleri DOM test çiftidir; gerçek görsel tarayıcı testi değildir. Güncel Windows sonucu uygulama çekilip başlatıldıktan sonra ayrıca görülecektir.

Uygulamada değişiklik yaptıktan sonra gün sonu paylaşımı için [geliştirme rehberi](DEVELOPMENT.md) kullanılır.

## Teknik dayanaklar

Yetkili derslerin birleşimi Qdrant MatchAny filtresiyle aranır; boş izin listesi filtresiz aramaya dönüşmez. [Qdrant filtreleme](https://qdrant.tech/documentation/search/filtering/).

SQLite yedeği ve tablo geçişi için: [Python SQLite backup API](https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.backup), [SQLite şema değişikliği](https://www.sqlite.org/lang_altertable.html).

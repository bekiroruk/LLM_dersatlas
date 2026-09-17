# Genel Sohbet ve araştırma ajanı

Yeni proje veya model indirmeden mevcut kurulum güncellenir. Yüklenmiş notlar, dersler ve Qdrant koleksiyonu korunur; yeniden yükleme/indeksleme gerekmez.

## Windows güncellemesi

1. Uvicorn loglarının aktığı mevcut terminalde Ctrl+C ile sunucuyu durdur. İkinci bir sunucu açma.
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
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Bir kontrol başarısızsa sonraki komutu çalıştırma. Ardından mevcut uygulama sekmesinde Ctrl+F5 ile eski JS/HTML önbelleğini yenile.

## Kullanım

| Kontrol | Davranış |
| --- | --- |
| Soldaki ders seçimi | Yükleme ve doküman düzenleme klasörü; sohbet filtresi değildir |
| Arama kapsamı: Tüm dersler | Kullanıcının erişebildiği tüm derslerin hazır notlarında arama |
| Arama kapsamı: tek ders | Aramayı açıkça seçtiğin dersle sınırlar |
| Kaynaklı cevap · RAG | Hibrit arama, yerel model ve kaynak desteği kontrolleri |
| Araştırma ajanı · çok adımlı | Alt sorularla ek aramalar; aynı yetkili kapsam, ardından kaynaklı cevap |
| Kaynak defteri | Ders adı, dosya adı, PDF fiziksel sayfası/metin konumu ve kaynak bölümü |

Ders filtresi değişince önceki mesajlar silinmez; her mesaj gönderildiği kapsamı gösterir. Her yeni soru şimdilik bağımsızdır: “bunu kısalt” gibi önceki cevaba gönderme yapan takip soruları henüz desteklenmez.

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

Yerel Linux ortamında 92 Python testi ve 8 JavaScript arayüz mantığı testi başarılı. API/depolama testlerinde gerçek SQLite ve gömülü Qdrant, modelde test çifti kullanılır. Arayüz testleri DOM test çiftidir; gerçek görsel tarayıcı testi değildir. Güncel Linux/Windows otomatik test sonuçları GitHub Actions'ta ayrıca görülür. Gerçek Ollama ve senin PDF'lerinle bu tablodaki denemeler hâlâ gereklidir.

Uygulamada değişiklik yaptıktan sonra gün sonu paylaşımı için [geliştirme rehberi](DEVELOPMENT.md) kullanılır.

## Teknik dayanaklar

Yetkili derslerin birleşimi Qdrant MatchAny filtresiyle aranır; boş izin listesi filtresiz aramaya dönüşmez. [Qdrant filtreleme](https://qdrant.tech/documentation/search/filtering/).

SQLite yedeği ve tablo geçişi için: [Python SQLite backup API](https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.backup), [SQLite şema değişikliği](https://www.sqlite.org/lang_altertable.html).

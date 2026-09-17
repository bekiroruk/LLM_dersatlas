# Geliştirme ve gün sonu güncellemesi

## İlk kaynak kodu aktarımı

İlk aktarım tamamlandı: güncel uygulama kodu 78f052f commit'iyle repoya eklendi. Aşağıdaki bağlantı kontrolleri ilk kurulum içindir. Mevcut kurulumda Genel Sohbet güncellemesi için [kısa rehber](GENERAL_CHAT.md) kullanılır.

Depo kökü, mevcut projedeki **pyproject.toml ve app klasörünün bulunduğu iç dersatlas klasörü** olmalıdır. Dış ZIP klasörünü, Masaüstü'nü veya kullanıcı klasörünü depo kökü yapma.

İlk bağlantıdan önce:

```powershell
git --version
git rev-parse --show-toplevel
git status --short
git remote
```

Henüz Git yoksa git komutları tanınmaz. Klasör depo değilse bazı komutların "not a git repository" demesi beklenir. Bu çıktı, uygulama hatası değildir.

Mevcut Git geçmişi, stage edilmiş değişiklikler, iç içe repo veya origin varsa korunur. İlk bağlantı komutları bu durum görülmeden topluca çalıştırılmaz. Yeni repodaki README/.gitignore, mevcut yerel dosyalarla çakışabileceğinden bir pull işlemi dosya ezerek zorlanmaz.

Önemli:

- Güncel app/rag.py içindeki son doğrulanmış düzeltmeler korunur.
- app, dist, testler, kurulum dosyaları ve anonymize edilmiş örnekler aktarılır.
- .env, data, özel notlar, modeller ve yedekler aktarılmaz.
- .gitignore önce kontrol edilir; daha önce izlenen hassas dosyaları kendiliğinden çıkarmaz.
- İlk uygulama commit'inden sonra README'deki aktarım bekleniyor uyarısı yalnızca gerçekten tamamlanınca güncellenir.
- Uygulama sürümü, gerçek kod ve testler görülmeden değiştirilmez; release etiketi oluşturulmaz.

Bu ilk bağlantı için mevcut Git durumuna uygun, veri koruyan bir plan uygulanmalıdır. git reset --hard, zorla push veya veri klasörü silme kullanılmaz.

## Her çalışma gününün sonunda

Önce davranış değişikliklerini ve gerçek test sonuçlarını CHANGELOG'un Unreleased bölümüne kaydet. Kişisel sorular veya doküman metinlerini changelog'a yapıştırma.

Güncel kod ve depo araçları aynı çalışma klasöründeyken:

```powershell
.\.venv\Scripts\python.exe scripts\gun_sonu.py --message "fix(rag): yanlış kaynak eşleşmesini engelle"
```

Önizlemedeki dosyaları incele. Ardından:

```powershell
.\.venv\Scripts\python.exe scripts\gun_sonu.py --message "fix(rag): yanlış kaynak eşleşmesini engelle" --apply --push
```

Araç kullanıcıdan EVET onayı ister. Windows Git oturumu/kimlik doğrulaması normal Git yöntemiyle tamamlanmalıdır; repo içine token veya parola yazılmaz.

## Aracın sınırları

1. Sadece beklenen LLM_dersatlas origin adresi ve main dalı kabul edilir.
2. Yeni dosyalar için proje dosyası izin listesi uygulanır.
3. Önceden stage edilmiş değişiklikler otomatik sahiplenilmez.
4. Uzak main yerel geçmişte yoksa otomatik merge/reset yapılmaz.
5. Git indeksindeki içerik taranır; çalışma kopyası sonradan değişse bile staged secret gözden kaçırılmamalıdır.
6. Python sözdizimi ve keşfedilen tests kümesi çalıştırılır; başarısız/atlanmış testte commit yapılmaz.
7. Kontroller sırasında dosyalar değişirse commit yapılmaz.
8. Başarılı commit sonrası push ancak --push verilmişse yapılır.
9. Push başarısızsa yerel commit korunur; geri alma veya force-push yapılmaz.
10. Hiç değişiklik yoksa boş commit/push yapılmaz.

Hata sonrası dosyalar korunur; stage edilmiş içerik veya oluşmuş commit otomatik temizlenmez. git status ile incele.

Araç bilinmeyen bütün kişisel bilgileri veya tüm secret biçimlerini yakalayamaz. Özellikle TXT/Markdown örnekleri ve ekran görüntüleri insan tarafından gözden geçirilmelidir. Ayrıca bu araç hook değildir; manuel Git komutlarıyla atlanabilir.

## CI

Depo araçları Linux ve Windows'ta test edilir. Uygulama app/main.py ve pyproject.toml ile aktarıldıktan sonra uygulama bağımlılıkları kurularak API/çekirdek testleri çalıştırılır. Uygulama yokken uygulama işi açıkça atlanır; depo testlerinin başarısı model kalitesi diye sunulmaz.

CI, gerçek Ollama/model başarımı veya kişisel PDF'lerle RAG değerlendirmesi değildir. JavaScript sözdizimi kontrolü, uygulama kodu aktarılınca CI'da çalıştırılır.

Genel Sohbet ile birlikte node tests/test_chat_ui.js kapsam/istek/kaynak/oturum mantığı testleri CI'a eklendi. Node.js yalnızca bu geliştirici kontrolü içindir; uygulamanın çalışması için yeni bir Node/npm kurulumu gerekmez.

Workflow üçüncü taraf action sürümleri doğrulanmış tam commit SHA değerlerine sabitlenir ve yalnızca contents: read yetkisi kullanır.

## Günlük otomasyon

Bu depoyu hazırlamak, Windows bilgisayarında zamanlanmış görev oluşturmaz. Gün sonu aracı etkileşimlidir; --apply/--push olmadan dışarıya yazmaz. Otomatik, gözetimsiz yerel dosya yükleme kurulmuş değildir.

Uzak GitHub değişikliklerini izlemek veya belgelere göre özet çıkarmak, Windows'ta henüz commit edilmemiş dosyaları yüklemekten farklıdır. Gelecek otomasyonun kapsamı ve çalışacağı ortam ayrıca belirlenmelidir.

## Resmi kaynaklar

- [.gitignore davranışı](https://git-scm.com/docs/gitignore)
- [Git add ve indeks](https://git-scm.com/docs/git-add)
- [GitHub Actions güvenli kullanımı](https://docs.github.com/en/actions/reference/security/secure-use)
- [actions/checkout v6.0.2](https://github.com/actions/checkout/releases/tag/v6.0.2)
- [actions/setup-python v6.2.0](https://github.com/actions/setup-python/releases/tag/v6.2.0)

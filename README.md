# DersAtlas

**Notlarından öğren. Kaynağını gör. Verini yerelde tut.**

Tarih, Coğrafya ve Vatandaşlık notlarından kaynaklı cevaplar üreten yerel yapay zekâ çalışma asistanı.

## Özellikler

- PDF, DOCX, TXT ve Markdown dokümanlarını derslere göre düzenleme.
- Genel Sohbet: ders seçmeden erişebildiğin tüm notlarda RAG araması.
- İsteğe bağlı ders filtresi; kaynaklarda ders, dosya, sayfa ve metin.
- Ollama ile yerel model; alt sorularla notları araştıran, yalnızca okuma yapan ajan.
- Oturum içi sohbet hafızası: takip sorularını bağlamıyla anlama, her cevapta yeniden kaynak arama.

## Teknolojiler

Python · FastAPI · Ollama · Qwen3 · BGE-M3 · Qdrant · SQLAlchemy

## Projenin durumu

Uygulamanın güncel kaynak kodu ve geliştirme araçları bu repoda. Uygulama, yerel Ollama modelleriyle çalışır.

**Genel Sohbet ve takip soruları hazır.** Hafıza yalnızca açık sayfada tutulur; konuşmalar veritabanına kaydedilmez. Mevcut notlarını yeniden yüklemen gerekmez.

## Windows'ta çalıştır

Proje klasöründeki PowerShell'de:

```powershell
.\scripts\start.ps1
```

Bu komut yalnızca bu projeye ait eski sunucuyu kapatır, doğru veri klasörünü kullanır, çalışan RAG sürümünü doğrular ve tarayıcıyı açar. Durdurmak için `.\scripts\stop.ps1` çalıştır. İlk kurulum gerekiyorsa önce `.\scripts\setup.ps1` kullan.

Uygulamayı doğru sürümle başlatıp gerçek yerel modelle üç derslik kabul
raporunu tek komutta üretmek için:

```powershell
.\scripts\acceptance.ps1
```

Parola ekranda görünmeden sorulur. Her çalıştırma zaman damgalı yeni bir yerel
rapor üretir; rapor GitHub'a eklenmez. Sunucu zaten doğru sürümle açıksa
`.\scripts\acceptance.ps1 -NoStart` kullanılabilir.

## Belgeler

- [Mimari](docs/ARCHITECTURE.md)
- [Yol haritası](docs/ROADMAP.md)
- [Geliştirme ve gün sonu güncellemesi](docs/DEVELOPMENT.md)
- [Genel Sohbet ve ajan: güncelleme / kullanım](docs/GENERAL_CHAT.md)
- [Kalite testleri](docs/QUALITY.md)

Ders materyalleri, veritabanları ve kişisel bilgiler repoya dahil edilmez. [Güvenlik politikası](SECURITY.md) · [Değişiklik kaydı](CHANGELOG.md)

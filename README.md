# DersAtlas

**Notlarından öğren. Kaynağını gör. Verini yerelde tut.**

Tarih, Coğrafya ve Vatandaşlık notlarından kaynaklı cevaplar üreten yerel yapay zekâ çalışma asistanı.

## Özellikler

- PDF, DOCX, TXT ve Markdown dokümanlarını derslere göre düzenleme.
- Genel Sohbet: ders seçmeden erişebildiğin tüm notlarda RAG araması.
- İsteğe bağlı ders filtresi; kaynaklarda ders, dosya, sayfa ve metin.
- Ollama ile yerel model; alt sorularla notları araştıran, yalnızca okuma yapan ajan.

## Teknolojiler

Python · FastAPI · Ollama · Qwen3 · BGE-M3 · Qdrant · SQLAlchemy

## Projenin durumu

Uygulamanın güncel kaynak kodu ve geliştirme araçları bu repoda. Uygulama, yerel Ollama modelleriyle çalışır.

**Genel Sohbet hazır.** Mevcut notlarını yeniden yüklemen gerekmez. Her soru şimdilik bağımsızdır; takip soruları için sohbet bağlamı sonraki aşama.

## Belgeler

- [Mimari](docs/ARCHITECTURE.md)
- [Yol haritası](docs/ROADMAP.md)
- [Geliştirme ve gün sonu güncellemesi](docs/DEVELOPMENT.md)
- [Genel Sohbet ve ajan: güncelleme / kullanım](docs/GENERAL_CHAT.md)
- [Kalite testleri](docs/QUALITY.md)

Ders materyalleri, veritabanları ve kişisel bilgiler repoya dahil edilmez. [Güvenlik politikası](SECURITY.md) · [Değişiklik kaydı](CHANGELOG.md)

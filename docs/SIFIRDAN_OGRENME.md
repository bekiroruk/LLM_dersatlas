# Sıfırdan öğrenme ve geliştirme yolu

## A. Önce anlaman gereken farklar

| Kavram | DersAtlas'ta somut karşılığı |
| --- | --- |
| Model | Qwen3, metin üreten sinir ağı |
| Model serving | Ollama'nın modeli belleğe alıp HTTP üzerinden sunması |
| Prompt | Modele rol, sınır ve cevap biçimi vermen |
| Embedding | Bir soru veya paragrafın anlamsal arama vektörü |
| RAG | Soruya kaynak bulup bu kaynağı LLM'e gönderme |
| Veritabanı | Hesaplar, dersler, belgeler ve metin parçalarını yönetme |
| Vektör indeksi | Anlama göre benzer parçaları bulma |
| API | Tarayıcıyla Python ve Python'la model servisinin haberleşme sözleşmesi |
| Agent | Modelin gerektiğinde izinli arama aracını çağırması |
| Fine-tuning | Model ağırlıklarını eğitimle değiştirme; bu sürümde yapılmaz |
| Evaluation | Yanlışları ve ilerlemeyi sistematik ölçme |
| Deployment | Uygulamayı çalışır servis olarak sunma |

## B. Sırayla çalışacağın modüller

Bu bir süre garantisi değildir. Bir aşamanın çıkış ölçütü sağlanmadan sonraki aşamaya geçme.

| Aşama | Öğrenilecekler | Kodda incele | Küçük görev / çıkış ölçütü |
| --- | --- | --- | --- |
| 0 | Python ortamı, terminal, klasör, Git | README, pyproject | Ortamı kur; doctor çıktısını anla |
| 1 | Python fonksiyon, sınıf, istisna, tip | ingestion.py, ranking.py | Tek bir metni parçala; yanlış ayarı yakala |
| 2 | HTTP, JSON, REST, doğrulama | main.py | Bir GET ve POST isteğini okuyabil |
| 3 | SQL, PK/FK, indeks, transaction | db.py | Belge ve parça ilişkisini açıklayabil |
| 4 | LLM, sıcaklık, bağlam, token | providers.py | Ollama'da kısa bir yerel yanıt al |
| 5 | Embedding, cosine benzerliği | providers.py | İki yakın ve bir uzak metni karşılaştır |
| 6 | Metin çıkarma, chunking, metadata | ingestion.py, worker.py | Üç PDF sayfasının referansını doğru koru |
| 7 | BM25, semantic search, RRF | ranking.py, rag.py | Sadece BM25 ve hibrit sonucu karşılaştır |
| 8 | Kaynaklı istem ve abstention | rag.py, citations.py | Notta olmayan soruda güvenli davranışı dene |
| 9 | Oturum, RBAC, CSRF, ACL | passwords.py, security.py | Başka kullanıcının dosyasına erişimi reddet |
| 10 | Araç şeması, sınırlı döngü | agent_search | Agent'in 2 alt aramasını arayüzde izle |
| 11 | Değerlendirme ve hata analizi | evaluate.py, tests | 30 gerçek soru için altın kaynak seti oluştur |
| 12 | Serving, Docker, izleme | compose.yaml, dashboard | Soğuk/sıcak model süresini ayrı ölç |
| 13 | Kurumsal altyapı | üretim rehberi | SQL Server, TLS, SSO, yedek geri yükleme planı |
| 14 | Dış sistem entegrasyonu | SAP mimari bölümü | Yetkili sandbox erişimi varsa salt okunur OData adaptörü |

## C. İlk gerçek deneyi nasıl yapacağız?

1. Tarih notlarından küçük ve temiz üç doküman seç. İlk testte bütün arşivi yükleme.
2. PDF'te metin seçilebiliyor mu kontrol et. Fotoğraftan oluşuyorsa önce OCR gerekir.
3. Dosyaya anlaşılır bir ad ver: `Osmanli_Yenilesme_01.pdf` gibi. Parça kaynaklarında bu ad görünür.
4. DersAtlas'ta yükle, durum `Hazır` olana kadar bekle. Bir uyarı varsa nedenini incele.
5. Bildiğin 10 doğrudan soru sor. Her cevapta kaynak konumu ve metni kontrol et.
6. İki bölüm arasında karşılaştırma gerektiren 5 soru sor. Hem RAG hem Agent modunda dene.
7. Notta cevabı olmayan 5 soru sor. Kaynak yetersizliğini fark etmesini bekle; kaçırırsa bunu hata olarak kaydet.
8. 5 kronoloji/tarih ve 5 özel terim sorusu ekle. Soru setini test amaçlı sabit tut.
9. Hatanın modelden önce veri çıkarma veya yanlış kaynak getirmeden kaynaklanıp kaynaklanmadığını ayır.
10. Aynı test setinde yalnızca tek parametreyi değiştirerek karşılaştır. Aynı anda model, embedding ve chunk boyutunu değiştirme.

## D. Yanlış cevap aldığında nereyi kontrol edeceksin?

| Gözlem | İlk kontrol | Olası düzeltme |
| --- | --- | --- |
| Yükleme hata veriyor | Dosya türü, boyut, UTF-8, PDF şifresi | Dosyayı dönüştür, böl veya şifreyi kaldır |
| Bazı PDF sayfaları yok | OCR uyarısı, metin seçilebilirliği | Yerel OCR; sonra kaynak metni doğrula |
| Doğru bölüm bulunmuyor | Kaynak kartları, ders seçimi, parçalama | Başlık bağlamı, parça boyutu, embedding değerlendirmesi |
| Doğru kaynak var, cevap yanlış | LLM çıktısı ve kaynak anlamı | Daha uygun model/istem, insan değerlendirmesi |
| Kaynak numarası hatalı | Yapılandırılmış çıktı | Modelin JSON uyumu, çıktı bütçesi |
| Çok yavaş | İlk yükleme, CPU/GPU kullanımı, bağlam | Daha küçük model, daha az kaynak, GPU ölçümü |
| “Model hazır değil” | Ollama, model adları, `/api/tags` | Modeli indir; `.env` ve servisi kontrol et |
| Başka ders cevapları geliyor | Ders filtresi ve üyelik testleri | Güvenlik hatası say; dağıtımı durdur ve düzelt |

## E. Donanım seçimini nasıl yapacağız?

İşlemci, RAM, GPU modeli, VRAM ve boş disk bilinmiyor. Qwen3 4B başlangıç adayıdır; cihazında hızlı veya kaliteli çalışacağını henüz ölçmedik. Ağırlık dosyası boyutu toplam çalışma belleği değildir: model, KV cache, embedding, işletim sistemi ve uygulama birlikte bellek kullanır. GPU'suz CPU çalışması mümkün olabilir fakat yavaşlayabilir.

Önce `scripts/doctor.py`, `ollama list` ve `ollama ps` çıktılarını incele. İlk yanıtla sonraki yanıtların sürelerini ayır. Agent'in çok çağrı yaptığını unutma. Modeller aynı anda bellekte kalabildiği için yalnızca sırayla çağrı yapmak VRAM sınırını tek başına garanti etmez; Ollama bellek ayarları ve keep-alive davranışı ayrıca ölçülmelidir.

Bir sonraki model karşılaştırmasında aynı sorularla Qwen3 4B ve donanım uygunsa daha büyük bir yerel model denenebilir. Model seçimini en yeni isim veya en yüksek parametre sayısına göre değil, gerçek notlarda kaynak sadakati, gecikme ve bellek tüketimine göre yap.

**Portföy notu:** GitHub'a yalnızca kod ve anonim örnekleri koy; gerçek notları ve sırları paylaşma. CI dosyası hazır, ancak depoya gönderim yapılmadı.

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
- Sohbet bağlamı eklendi: son en fazla 4 tur / 6000 karakter, yalnızca açık sayfada; takip sorusundan sonra yeniden kaynak arama.
- Fethedildi/Fethiye yanlış eşleşmesi için hedefli düzeltme yapıldı.
- Kullanıcı üç hedefli senaryonun beklenen şekilde cevaplandığını bildirdi.
- Genel Sohbet/ajan/filtre için kullanıcı ilk beş kabul sorusunun beklenen sonucu verdiğini bildirdi.
- Açık iki-konulu takip göndermesi modelden bağımsız çözülür; her cevap için belgelerde yeniden arama yapılır.
- Çok ölçütlü iklim karşılaştırması için konu × ölçüt kanıt kapsaması eklendi. Benzerlik kısa listesi eksik olsa bile bütün yetkili hazır parçalardan gereken açık kanıtlar seçilir.
- Veri yolları proje köküne sabitlendi ve Windows başlatıcısı çalışan kodun RAG sürümünü doğrular; yanlış çalışma klasörü veya eski Uvicorn süreci nedeniyle başka veri alanının açılması engellenir.
- Genel ajan kabul aracı Tarih, Coğrafya, Vatandaşlık ve kaynak-dışı soruları ders seçmeden çalıştıracak şekilde hazırlandı; kaynak/cevap kapsaması, çekimserlik ve gecikme ayrı raporlanır.
- İlk gerçek sekiz soruluk ajan raporu Windows/Ollama üzerinde tamamlandı: cevaplanabilirlik doğruluğu 1,0; kaynak kapsaması 0,833; cevap kapsaması 0,75; p50 23,1 sn ve p95 41,5 sn. İnsan incelemesinde T01'de bozuk hükümdar adı, V01'de cevap anahtarsız soru kataloğu bulundu; ikisi `source-contract-v15` regresyonlarıyla kapatıldı.
- v15 tekrarında kaynak ve cevap kapsaması 0,917'ye, p95 32,9 saniyeye yükseldi. V01 kapandı; T01 ise hükümdar kanıtı kısa listeden düşünce yalnızca tarih ve dağınık PDF satırlarıyla cevaplandı. `source-contract-v16` iki olay kanıtını tüm yetkili parçalarda tamamlar ve eksikse cevap vermeyi reddeder.
- v17 gerçek Windows raporunda hazır kaynaklı sorularda uygulama doğruluğu 1,0 oldu. Tek uyumsuzluk, notlarda hükümdar ilişkisi bulunmayan T01 için güvenli rettir. İlk ölçümde p50 52,1 ve p95 68,2 saniyeydi; uyarlamalı ajan sonrasında aynı kabul akışı p50 8,9 ve p95 15,0 saniyede tamamlandı.
- Giriş, sohbet, kaynak defteri, doküman ve sistem ekranları modern ve ortak bir tasarım sistemiyle yenilendi. Soru önerileri, canlı karakter sayacı, klavye kısayolu, işlem durumu, kaynak sayısı ve uyarlanabilir mobil yerleşim eklendi; çevrimdışı çalışma korunuyor.

## Doğrulama

Kullanıcının paylaştığı Windows çıktısında uygulama ve depo araçlarının 60 testi başarılı. Sözdizimi ve Git indeksindeki paylaşım kontrolleri de ilk aktarım öncesinde başarılı tamamlandı.

Bu sonuç, tüm ders belgeleriyle gerçek model doğruluğunu veya güvenlik sertifikasını kanıtlamaz. GitHub Actions sonuçları yerel test kaydından ayrı takip edilir.

Genel Sohbet değişikliğinde yerel Linux/Python 3.12 ortamında 92 Python testi ve Node.js ile 8 arayüz mantığı testi başarılı. Testler gerçek SQLite ve gömülü Qdrant kullanır; LLM deterministik test çiftidir. Eski şemanın yedeği, veri koruması ve yarıda kesilen geçişin rollback'i test edildi. Yerel test adresi bu ortamın tarayıcısında engellendiği için gerçek görsel tarayıcı kontrolü yapılamadı.

Güncel Linux/Windows CI durumu [GitHub Actions](https://github.com/bekiroruk/LLM_dersatlas/actions) üzerinden ayrı doğrulanır.

Sohbet bağlamı değişikliğinde yerel Linux'ta 113 Python testi ve 14 DOM mantık testi başarılı. Testlerde gerçek SQLite/Qdrant ve bir model test çifti kullanıldı. Takip sorusunu anlama, yeni konu ayrımı, kaynak olarak geçmiş kullanmama, güncel yetkiler, sınırlar, kapsam değişimi ve gecikmiş cevap temizliği kapsandı. Gerçek model/görsel tarayıcı denemesi yerine geçmez.

Açık gönderme düzeltmesiyle toplam 122 Python ve 15 DOM mantık testi yerel Linux'ta başarılı. Bildirilen soru, yeniden yazım modelini çağırmayı hata sayan bir regresyonla doğrulandı; cevap yine güncel SQLite/Qdrant kaynaklarıyla üretilir. Gerçek Ollama/PDF sonucu henüz yeniden doğrulanmadı.

Karşılaştırma kaynak kalitesi düzeltmesiyle toplam 125 Python ve 15 DOM mantık testi yerel Linux'ta başarılı. Gerçekçi katalog metni cevap olarak reddedildi; iki iklime ait açık kanıt parçalarının önceliği doğrulandı. Bu otomatik sonuç gerçek model doğruluk garantisi değildir.

`source-contract-v14` son doğrulamasında 193 Python ve 17 DOM mantık testi başarılı. Kullanıcının yüklediği gerçek bitki PDF'si, ayrı doğru yağış satırları ve bildirilen yanıltıcı/eksik iklim parçaları gerçek metin çıkarma, SQLite ve gömülü Qdrant üzerinden birlikte işlendi. Sistem bozuk matris ile aynı PDF'deki ilgisiz toprak/yeraltı suyu ifadelerini ve tam rejim göstermeyen iklim parçalarını dışarıda bıraktı; ayrıca kırpılmış hücreleri, sınav notlarını ve yağış cümlesine karışan bitki örneklerini temizleyerek dört gerekli kanıttan yapılandırılmış cevap üretti.

Genel ajan kabul aracı eklendikten sonra 197 Python ve 17 DOM mantık testi başarılı. Kullanıcının Windows kabulünde `source-contract-v14` iklim karşılaştırması doğru ve temiz kaynaklı cevap verdi. Ardından gerçek sekiz soruluk ajan raporu yerel Ollama ve notlarla çalıştırıldı; aşağıdaki v15 düzeltmelerine girdi sağladı.

`source-contract-v15` doğrulamasında 201 Python ve 17 DOM mantık testi başarılı. İlk gerçek sekiz soruluk ajan raporundaki T01 ve V01 kusurları birebir regresyona dönüştürüldü. Soru katalogları kanıt sayılmaz; bozuk `I. Fatih Sultan` kalıbı reddedilir ve aynı kanıt kapsamındaki tam hükümdar adı tercih edilir. Düzeltme sonrası gerçek Windows/Ollama raporu yeniden çalıştırılmalıdır.

`source-contract-v16` doğrulamasında 203 Python ve 17 DOM mantık testi başarılı. Fetih tarih ve hükümdar parçalarının genel benzerlik sıralayıcıları boş sonuç verse bile birlikte bulunması, yalnızca tarih varsa güvenli ret verilmesi ve başlatıcının boş günlük yerine çıkış tanısı göstermesi test edildi.

`adaptive-agent-v17` ve modern arayüz doğrulamasında 211 Python ve 19 DOM mantık testi
başarılı. Yeterli ilk kanıtta ajan planlaması atlanır; eksik/boş kanıtta güvenli
arama yolu korunur. Model ve arama adımlarının süreleri arayüzde görünür. Tek
komutluk `scripts/acceptance.ps1`, doğru sürümü başlatır ve benzersiz adlı yerel
kabul raporu üretir. Modern görünümün yapı taşları, karakter sayacı, genel sohbet
akışı, kaynak gösterimi, temizleme ve oturum yalıtımı arayüz testleriyle korunur.

## Bilinen sınırlamalar

- Hafıza sayfa yenilenince silinir; kalıcı sohbet geçmişi yoktur.
- Genel aramada toplam 30.000 parça koruma sınırı var; aşılırsa ders filtresi kullanılmalı.
- Eski SQL Server şeması için nullable alan geçişi DBA tarafından ayrıca yapılmalı; bu ortamda SQL Server testi çalıştırılmadı.
- Islahat Fermanı'nın tarihi gibi sorularda doğru bilgiyi içeren yeni belgenin bulunması ve yeterli cevabın üretilmesi ayrıca doğrulanmalı.
- İddia düzeyinde kaynak desteği, sınırlı heuristik kontrollerden daha geniş değerlendirme gerektirir.
- Otomatik Windows dosya senkronizasyonu veya zamanlanmış push görevi kurulmadı.

## Sıradaki adım

Windows kurulumunda güncel kodu çekip uygulamayı başlatmak; giriş, genel sohbet,
kaynak defteri, doküman ve sistem ekranlarını gerçek tarayıcıda masaüstü ve dar
pencere genişliğinde görsel olarak kontrol etmek. Yeni proje ZIP'i, doküman
yükleme veya yeniden indeksleme gerekli değil.

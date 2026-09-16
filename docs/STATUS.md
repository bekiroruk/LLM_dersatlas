# Proje durumu

Son belge hazırlığı: 2026-09-16.

## GitHub

Bu depo dokümantasyon, güvenli paylaşım kontrolü, regresyon testleri ve geliştirme araçlarını içerir. Güncel çalışan uygulama kodunun ilk aktarımı beklenir. Henüz çalıştırılabilir bir uygulama release'i yayımlanmadı.

## Yerel uygulama

- Windows, Python 3.12 ve yerel Ollama modelleriyle kullanılıyor.
- Tarih, Coğrafya ve Vatandaşlık dokümanları yerel uygulamaya yüklenmiş durumda.
- Kaynak kartları ve ders bazlı arama mevcut.
- Fethedildi/Fethiye yanlış eşleşmesi için hedefli düzeltme yapıldı.
- Kullanıcı üç hedefli senaryonun beklenen şekilde cevaplandığını bildirdi.

## Bilinen sınırlamalar

- Genel Sohbet henüz eklenmedi; mevcut uygulama ders filtresine bağlı.
- Takip soruları için sohbet hafızası henüz eklenmedi.
- Islahat Fermanı'nın tarihi gibi sorularda doğru bilgiyi içeren yeni belgenin bulunması ve yeterli cevabın üretilmesi ayrıca doğrulanmalı.
- İddia düzeyinde kaynak desteği, sınırlı heuristik kontrollerden daha geniş değerlendirme gerektirir.
- Bu repoda henüz kullanıcı tarafından aktarılan güncel app kodu yok; otomatik uygulama testleri çalıştırılmış sayılmaz.
- Üretim, güvenlik sertifikası veya yüzde yüz doğruluk iddiası yok.
- Otomatik Windows dosya senkronizasyonu veya zamanlanmış push görevi kurulmadı.

## Sıradaki kapı

Mevcut Windows çalışma klasörünün Git durumu kontrol edilerek güncel kod güvenli aktarılır. Sonra Genel Sohbet geliştirmesine geçilir.

"""Mevcut Ollama modeliyle üç kaynaklı soruyu geçici örnek notta denetle.

Veritabanını açmaz, belge yüklemez ve model indirmez. Bu kontrol kaynak
seçimi/atıf akışını gerçek sohbet modeliyle sınar; PDF arama testi değildir.
"""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.providers import Ollama, ModelUnavailable
from app.rag import RAGService, RAG_REVISION, _parse_payload


class DiagnosticOllama(Ollama):
    """Yalnızca bu betikteki örnek notlara verilen gerçek çıktıyı gösterir."""
    def __init__(self, settings, details=False):
        super().__init__(settings)
        self.details = details
        self.call_count = 0

    def _post(self, endpoint, payload):
        result = super()._post(endpoint, payload)
        if endpoint != "/api/chat":
            return result
        self.call_count += 1
        message = result.get("message")
        content = message.get("content", "") if isinstance(message, dict) else ""
        try:
            parsed = _parse_payload(content)
            summary = {
                "kanit_yetersiz": parsed.insufficient_evidence,
                "kaynaklar": parsed.source_ids,
                "cevap_karakter": len(parsed.answer),
            }
        except ValueError:
            summary = {"bicim": "gecersiz_json"}
        summary["bitis"] = result.get("done_reason", "bilinmiyor")
        print(f"Model çağrısı {self.call_count}: " + json.dumps(summary, ensure_ascii=False), flush=True)
        if self.details:
            # Prompt, ayarlar ve gerçek belgeler yazdırılmaz. JSON kaçışı
            # terminal kontrol karakterlerini de güvenli biçimde gösterir.
            print("Ham model yanıtı: " + json.dumps(content, ensure_ascii=False), flush=True)
        return result


class ModelCheckRAG(RAGService):
    def retrieve(self, db, user, subject_id, question):
        # İlk parça bilerek daha zayıf: son seçimden sonra K1 eşlemesi
        # yeniden kurulmalı. Bunlar yalnızca bu denemenin örnek notlarıdır.
        records = (
            ("broad", "Karadeniz ve Akdeniz Türkiye'de görülen iklim tipleridir."),
            ("table", "Flora bölgesi Türkiye'de yayılışı Baskın görünüm\n"
                      "Avrupa-Sibirya Karadeniz kıyı kuşağı Nemli ormanlar\n"
                      "Akdeniz Akdeniz iklim sahaları Kızılçam, maki"),
        )
        return [{"chunk_id": key, "document_id": "model-check", "subject_id": "model-check",
                 "subject_name": "Örnek not", "filename": "yerel-model-denemesi.md",
                 "location": "Örnek tablo", "text": text, "retrieval_score": 0.5}
                for key, text in records]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--details", action="store_true", help="Örnek not kontrolündeki ham model yanıtlarını göster")
    parser.add_argument("--require-generated", action="store_true", help="Kaynak alıntısına düşen cevabı model üretimi başarısı sayma; çıkış kodu 1 döndür")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    settings = Settings()
    model = DiagnosticOllama(settings, details=args.details)
    questions = (
        ("Karadeniz ikliminin doğal bitki örtüsü nedir?", ("orman",)),
        ("Akdeniz ikliminin doğal bitki örtüsü nedir?", ("kızılçam", "maki")),
        ("Karadeniz ve Akdeniz iklimlerinin doğal bitki örtülerini karşılaştır.", ("orman", "maki")),
    )
    failures, excerpts, generated = 0, 0, 0
    try:
        print("RAG sürümü:", RAG_REVISION, flush=True)
        print("Gerçek sohbet modeli:", settings.chat_model, flush=True)
        status = model.status()
        if not status["reachable"] or not status["chat_ready"]:
            print("Ollama veya mevcut sohbet modeli hazır değil.")
            return 1
        rag = ModelCheckRAG(settings, model, None)
        for number, (question, expected) in enumerate(questions, 1):
            print(f"\n[{number}/3] {question}", flush=True)
            result = rag.answer(None, None, None, question)
            excerpt = result.get("answer_method") == "source_excerpt"
            okay = (result["outcome"] == "answered"
                    and all(term in result["answer"].lower() for term in expected)
                    and "[K1]" in result["answer"]
                    and {s["chunk_id"] for s in result["sources"]} == {"table"})
            failures += int(not okay)
            excerpts += int(okay and excerpt)
            generated += int(okay and not excerpt)
            method = "doğrudan kaynak alıntısı" if excerpt else "model cevabı"
            status = "ALINTI" if okay and excerpt else "GEÇTİ" if okay else "BAŞARISIZ"
            print(status + " — " + method)
            print(result["answer"], flush=True)
            for step in result["trace"]:
                if step.get("reason"):
                    print("Tanı:", step["tool"], step["reason"])
        print(f"\nModel üretimi: {generated}/3. Kaynak alıntısı: {excerpts}/3. Başarısız: {failures}/3.")
        if excerpts:
            print("Alıntı yolu çalıştı; bu, modelin doğrudan cevap üretiminin başarılı olduğu anlamına gelmez.")
        return int(failures > 0 or (args.require_generated and excerpts > 0))
    except ModelUnavailable as exc:
        print(str(exc))
        return 1
    finally:
        model.close()


if __name__ == "__main__":
    raise SystemExit(main())

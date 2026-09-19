"""Mevcut Ollama modeliyle üç kaynaklı soruyu geçici örnek notta denetle.

Veritabanını açmaz, belge yüklemez ve model indirmez. Bu kontrol kaynak
seçimi/atıf akışını gerçek sohbet modeliyle sınar; PDF arama testi değildir.
"""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.providers import Ollama, ModelUnavailable
from app.rag import RAGService, RAG_REVISION


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    settings = Settings()
    model = Ollama(settings)
    questions = (
        ("Karadeniz ikliminin doğal bitki örtüsü nedir?", ("orman",)),
        ("Akdeniz ikliminin doğal bitki örtüsü nedir?", ("kızılçam", "maki")),
        ("Karadeniz ve Akdeniz iklimlerinin doğal bitki örtülerini karşılaştır.", ("orman", "maki")),
    )
    failures, excerpts = 0, 0
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
            excerpts += int(excerpt)
            okay = (result["outcome"] == "answered"
                    and all(term in result["answer"].lower() for term in expected)
                    and "[K1]" in result["answer"]
                    and {s["chunk_id"] for s in result["sources"]} == {"table"})
            failures += int(not okay)
            method = "doğrudan kaynak alıntısı" if excerpt else "model cevabı"
            print(("GEÇTİ" if okay else "BAŞARISIZ") + " — " + method)
            print(result["answer"], flush=True)
            for step in result["trace"]:
                if step.get("reason"):
                    print("Tanı:", step["tool"], step["reason"])
        print(f"\nSonuç: {3 - failures}/3 başarılı; {excerpts} cevap kaynak alıntısı yolunu kullandı.")
        if excerpts:
            print("Alıntı yolu çalıştı; bu, modelin doğrudan cevap üretiminin başarılı olduğu anlamına gelmez.")
        return int(failures > 0)
    except ModelUnavailable as exc:
        print(str(exc))
        return 1
    finally:
        model.close()


if __name__ == "__main__":
    raise SystemExit(main())

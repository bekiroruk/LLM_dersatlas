"""Çalışan DersAtlas API'sinde RAG/ajan kabul ölçümü üretir."""
import argparse
import getpass
import http.cookiejar
import json
import math
import os
from pathlib import Path
import statistics
import time
import urllib.request


def percentile(values, percent):
    """Küçük kabul kümeleri için doğrusal enterpolasyonlu yüzdelik."""
    ordered = sorted(values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * percent / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def snippet_coverage(text, snippets):
    """Her doğrulama grubunda tek metin veya alternatiflerden birini arar."""
    if not snippets:
        return None
    def fold(value):
        return str(value or "").translate(str.maketrans({"I": "ı", "İ": "i"})).casefold()

    candidate = fold(text)
    groups = [item if isinstance(item, list) else [item] for item in snippets]
    return sum(
        any(fold(alternative) in candidate for alternative in group)
        for group in groups
    ) / len(groups)


def validate_dataset(items):
    """Yanlış raporu engellemek için değerlendirme veri sözleşmesini denetler."""
    if not isinstance(items, list) or not items:
        raise ValueError("Değerlendirme kümesi boş olmayan bir JSON listesi olmalı.")
    identifiers = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{index}. kayıt nesne olmalı.")
        identifier = str(item.get("id") or f"Q{index:02d}")
        if identifier in identifiers:
            raise ValueError(f"Tekrarlı değerlendirme kimliği: {identifier}")
        identifiers.add(identifier)
        question = item.get("question")
        if not isinstance(question, str) or len(question.strip()) < 3:
            raise ValueError(f"{identifier}: geçerli soru yok.")
        if not isinstance(item.get("answerable"), bool):
            raise ValueError(f"{identifier}: answerable true/false olmalı.")
        snippets = item.get("expected_snippets", [])
        valid_snippets = isinstance(snippets, list) and all(
            (isinstance(value, str) and value.strip())
            or (
                isinstance(value, list)
                and value
                and all(isinstance(option, str) and option.strip() for option in value)
            )
            for value in snippets
        )
        if not valid_snippets:
            raise ValueError(
                f"{identifier}: expected_snippets metin veya alternatif metin listeleri içermeli."
            )
        if item["answerable"] and not snippets:
            raise ValueError(f"{identifier}: cevaplanabilir soru doğrulama parçası taşımalı.")


def summarize(results, mode):
    """Arama, cevap ve gecikme ölçülerini birbirine karıştırmadan özetler."""
    answerable = [row for row in results if row["answerable"]]
    generated = [row for row in results if "outcome" in row]
    latencies = [row["duration_ms"] for row in results]
    retrieval_values = [
        row["source_span_coverage"] for row in answerable
        if row["source_span_coverage"] is not None
    ]
    answer_values = [
        row["answer_span_coverage"] for row in answerable
        if row.get("answer_span_coverage") is not None
    ]
    return {
        "mode": mode,
        "questions": len(results),
        "answerable_questions": len(answerable),
        "mean_source_span_coverage": (
            statistics.mean(retrieval_values) if retrieval_values else None
        ),
        "mean_answer_span_coverage": (
            statistics.mean(answer_values) if answer_values else None
        ),
        "answerability_accuracy": (
            statistics.mean(row["answerability_match"] for row in generated)
            if generated else None
        ),
        "p50_ms": round(percentile(latencies, 50)) if latencies else None,
        "p95_ms": round(percentile(latencies, 95)) if latencies else None,
    }


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--username", default="bekir")
    parser.add_argument(
        "--password-env",
        default="DERSATLAS_EVAL_PASSWORD",
        help="Parolayı taşıyan ortam değişkeni; yoksa güvenli giriş istenir.",
    )
    parser.add_argument(
        "--subject-id",
        help="Boş bırakılırsa kullanıcının erişebildiği tüm derslerde aranır.",
    )
    parser.add_argument("--mode", choices=("rag", "agent"), default="rag")
    parser.add_argument("--dataset", default="samples/evaluation.json")
    parser.add_argument("--output", default="output/evaluation.json")
    parser.add_argument("--with-generation", action="store_true")
    parser.add_argument(
        "--delay",
        type=float,
        default=6,
        help="İstekler arasındaki saniye; varsayılan hız sınırlarına uyum sağlar.",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.mode == "agent" and not args.with_generation:
        raise SystemExit("Ajan değerlendirmesi --with-generation gerektirir.")
    target = Path(args.output)
    if target.exists():
        raise SystemExit("Çıktı zaten var; yeni bir --output yolu seç.")

    questions = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    validate_dataset(questions)
    cookie_jar = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar)
    )

    def post(path, body):
        request = urllib.request.Request(
            args.url.rstrip("/") + path,
            data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "X-Requested-With": "DersAtlas",
            },
            method="POST",
        )
        with client.open(request, timeout=900) as response:
            return json.load(response)

    password = os.environ.get(args.password_env) or getpass.getpass("Parola: ")
    post("/api/login", {"username": args.username, "password": password})

    results = []
    for index, item in enumerate(questions, start=1):
        if results:
            time.sleep(max(0, args.delay))
        started = time.perf_counter()
        body = {"question": item["question"], "mode": args.mode}
        if args.subject_id:
            body["subject_id"] = args.subject_id

        if args.with_generation:
            response = post("/api/questions", body)
            sources = response["sources"]
        else:
            response = None
            sources = post("/api/search", body)["sources"]

        source_text = "\n".join(source.get("text", "") for source in sources)
        snippets = item.get("expected_snippets", [])
        row = {
            "id": str(item.get("id") or f"Q{index:02d}"),
            "course": item.get("course"),
            "question": item["question"],
            "answerable": item["answerable"],
            "retrieved": len(sources),
            "source_courses": sorted({
                source.get("subject_name") for source in sources
                if source.get("subject_name")
            }),
            "source_span_coverage": snippet_coverage(source_text, snippets),
            "duration_ms": round((time.perf_counter() - started) * 1000),
        }
        if response is not None:
            expected_outcome = "answered" if item["answerable"] else "insufficient"
            row.update({
                "outcome": response["outcome"],
                "answer": response["answer"],
                "answer_method": response.get("answer_method"),
                "answer_span_coverage": snippet_coverage(
                    response["answer"], snippets
                ),
                "answerability_match": response["outcome"] == expected_outcome,
                "source_count": len(response["sources"]),
            })
        results.append(row)
        print(f"{index}/{len(questions)} {row['id']} tamamlandı")

    report = {
        "note": (
            "Kısa metin kapsamı semantik doğruluk değildir. Yanlış cevap, "
            "eksik iddia ve kaynak desteği ayrıca insan tarafından incelenmelidir."
        ),
        "url": args.url,
        "scope": args.subject_id or "all-accessible-subjects",
        "summary": summarize(results, args.mode),
        "results": results,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print("Rapor:", target)


if __name__ == "__main__":
    main()

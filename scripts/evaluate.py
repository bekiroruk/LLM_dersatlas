"""Çalışan DersAtlas API'sinde RAG/ajan kabul ölçümü üretir."""
import argparse
import getpass
import hashlib
import http.cookiejar
import json
import math
import os
from pathlib import Path
import statistics
import time
import urllib.error
import urllib.request


TRANSIENT_HTTP_CODES = {429, 502, 503, 504}


def post_json(client, url, body, retries=3, retry_wait=10, sleep=time.sleep):
    """Geçici yerel model/API hatalarında sınırlı sayıda yeniden dener."""
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Requested-With": "DersAtlas",
        },
        method="POST",
    )
    for attempt in range(retries + 1):
        try:
            with client.open(request, timeout=900) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            transient = exc.code in TRANSIENT_HTTP_CODES
            if not transient or attempt >= retries:
                raise
            delay = retry_wait * (2 ** attempt)
            print(
                f"HTTP {exc.code}; {delay:g} saniye sonra yeniden deneniyor "
                f"({attempt + 1}/{retries})..."
            )
            sleep(delay)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            if attempt >= retries:
                raise
            delay = retry_wait * (2 ** attempt)
            print(
                f"Geçici bağlantı hatası; {delay:g} saniye sonra yeniden "
                f"deneniyor ({attempt + 1}/{retries})..."
            )
            sleep(delay)


def _checkpoint_key(args, questions):
    encoded = json.dumps(
        questions, ensure_ascii=False, sort_keys=True
    ).encode("utf-8")
    return {
        "dataset_sha256": hashlib.sha256(encoded).hexdigest(),
        "url": args.url.rstrip("/"),
        "subject_id": args.subject_id,
        "mode": args.mode,
        "with_generation": args.with_generation,
    }


def load_checkpoint(path, key, questions):
    """Aynı koşuya ait doğrulanmış ara sonuçları yükler."""
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Ara kayıt okunamadı: {path} ({exc})") from exc
    results = payload.get("results")
    if payload.get("key") != key or not isinstance(results, list):
        raise SystemExit(
            f"Ara kayıt bu koşuyla uyuşmuyor: {path}. Dosyayı sil veya yeni "
            "bir --output yolu seç."
        )
    expected_ids = [
        str(item.get("id") or f"Q{index:02d}")
        for index, item in enumerate(questions, start=1)
    ]
    actual_ids = [str(row.get("id")) for row in results]
    if actual_ids != expected_ids[:len(actual_ids)]:
        raise SystemExit(
            f"Ara kayıttaki soru sırası geçersiz: {path}. Dosyayı sil veya "
            "yeni bir --output yolu seç."
        )
    return results


def save_checkpoint(path, key, results):
    """Ara sonucu yarım JSON bırakmayacak biçimde atomik kaydeder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(
        json.dumps({"key": key, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def resolve_password(env_name, environ=None, prompt=None):
    """Parolayı ortamdan veya görünmez güvenli girişten alır."""
    environ = os.environ if environ is None else environ
    prompt = getpass.getpass if prompt is None else prompt
    password = environ.get(env_name)
    if password is None:
        password = prompt(
            "DersAtlas giriş parolası (yazarken ekranda görünmez): "
        )
    if not password:
        raise SystemExit(
            "Parola boş bırakılamaz. Komutu yeniden çalıştır; Parola satırında "
            "DersAtlas'a giriş yaparken kullandığın parolayı yazıp Enter'a bas."
        )
    return password


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


def source_requirement_coverage(sources, requirements):
    """İlişkili kanıtı aynı kaynak parçası içinde doğrular.

    Birleşik kaynak metninde dağınık geçen doğru sözcükler, tek başına aynı
    olguyu kanıtlamaz. Her gereksinim en az bir kaynak parçasında bütünüyle
    karşılanmalıdır.
    """
    if not requirements:
        return None

    def fold(value):
        return str(value or "").translate(
            str.maketrans({"I": "ı", "İ": "i"})
        ).casefold()

    texts = [fold(source.get("text", "")) for source in sources]
    matched = 0
    for requirement in requirements:
        expected = requirement["expected"]
        alternatives = expected if isinstance(expected, list) else [expected]
        all_terms = requirement.get("all_terms", [])
        any_terms = requirement.get("any_terms", [])
        if any(
            any(fold(option) in text for option in alternatives)
            and all(fold(term) in text for term in all_terms)
            and (not any_terms or any(fold(term) in text for term in any_terms))
            for text in texts
        ):
            matched += 1
    return matched / len(requirements)


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
        requirements = item.get("source_requirements", [])
        valid_requirements = isinstance(requirements, list) and all(
            isinstance(requirement, dict)
            and (
                isinstance(requirement.get("expected"), str)
                and requirement["expected"].strip()
                or isinstance(requirement.get("expected"), list)
                and requirement["expected"]
                and all(
                    isinstance(option, str) and option.strip()
                    for option in requirement["expected"]
                )
            )
            and all(
                isinstance(requirement.get(field, []), list)
                and all(
                    isinstance(term, str) and term.strip()
                    for term in requirement.get(field, [])
                )
                for field in ("all_terms", "any_terms")
            )
            for requirement in requirements
        )
        if not valid_requirements:
            raise ValueError(
                f"{identifier}: source_requirements geçerli kanıt kuralları içermeli."
            )


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
    corpus_ready = [
        row for row in generated if row.get("corpus_ready", True)
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
        "corpus_ready_questions": len(corpus_ready),
        "corpus_gap_questions": sum(
            not row.get("corpus_ready", True) for row in generated
        ),
        "application_accuracy_on_ready_corpus": (
            statistics.mean(row["answerability_match"] for row in corpus_ready)
            if corpus_ready else None
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
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="429/502/503/504 ve bağlantı hatalarında yeniden deneme sayısı.",
    )
    parser.add_argument(
        "--retry-wait",
        type=float,
        default=10,
        help="Yeniden denemeler arasındaki başlangıç bekleme süresi.",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.mode == "agent" and not args.with_generation:
        raise SystemExit("Ajan değerlendirmesi --with-generation gerektirir.")
    if args.retries < 0 or args.retry_wait < 0:
        raise SystemExit("--retries ve --retry-wait negatif olamaz.")
    target = Path(args.output)
    if target.exists():
        raise SystemExit("Çıktı zaten var; yeni bir --output yolu seç.")

    questions = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    validate_dataset(questions)
    checkpoint = Path(str(target) + ".partial")
    checkpoint_key = _checkpoint_key(args, questions)
    results = load_checkpoint(checkpoint, checkpoint_key, questions)
    if results:
        print(
            f"Ara kayıt bulundu: {len(results)}/{len(questions)} soru tamamlanmış; "
            "kaldığı yerden devam ediliyor."
        )
    cookie_jar = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar)
    )

    def post(path, body):
        return post_json(
            client,
            args.url.rstrip("/") + path,
            body,
            retries=args.retries,
            retry_wait=args.retry_wait,
        )

    password = resolve_password(args.password_env)
    try:
        post("/api/login", {"username": args.username, "password": password})
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            message = (
                f"'{args.username}' kullanıcısının parolası hatalı. Komutu "
                "yeniden çalıştır ve DersAtlas giriş parolasını yaz."
            )
        elif exc.code == 422:
            message = (
                "Giriş bilgileri sunucu tarafından geçersiz bulundu. Kullanıcı "
                "adı ve parolanın boş olmadığını kontrol et."
            )
        else:
            message = f"DersAtlas girişi başarısız: HTTP {exc.code}."
        raise SystemExit(message) from None

    for index, item in enumerate(
        questions[len(results):], start=len(results) + 1
    ):
        if results:
            time.sleep(max(0, args.delay))
        started = time.perf_counter()
        body = {"question": item["question"], "mode": args.mode}
        if args.subject_id:
            body["subject_id"] = args.subject_id

        try:
            if args.with_generation:
                response = post("/api/questions", body)
                sources = response["sources"]
            else:
                response = None
                sources = post("/api/search", body)["sources"]
        except urllib.error.HTTPError as exc:
            save_checkpoint(checkpoint, checkpoint_key, results)
            raise SystemExit(
                f"{item.get('id', index)} tamamlanamadı: HTTP {exc.code}. "
                f"Tamamlanan {len(results)} soru {checkpoint} dosyasına "
                "kaydedildi; aynı komutu yeniden çalıştırınca devam eder."
            ) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            save_checkpoint(checkpoint, checkpoint_key, results)
            raise SystemExit(
                f"{item.get('id', index)} tamamlanamadı: {exc}. Tamamlanan "
                f"{len(results)} soru {checkpoint} dosyasına kaydedildi; aynı "
                "komutu yeniden çalıştırınca devam eder."
            ) from None

        source_text = "\n".join(source.get("text", "") for source in sources)
        snippets = item.get("expected_snippets", [])
        fragment_coverage = snippet_coverage(source_text, snippets)
        requirement_coverage = source_requirement_coverage(
            sources, item.get("source_requirements", [])
        )
        evidence_coverage = (
            requirement_coverage
            if requirement_coverage is not None
            else fragment_coverage
        )
        corpus_ready = (
            not item["answerable"]
            or evidence_coverage == 1
        )
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
            "source_span_coverage": evidence_coverage,
            "source_fragment_coverage": fragment_coverage,
            "corpus_ready": corpus_ready,
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
        save_checkpoint(checkpoint, checkpoint_key, results)
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
    checkpoint.unlink(missing_ok=True)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print("Rapor:", target)


if __name__ == "__main__":
    main()

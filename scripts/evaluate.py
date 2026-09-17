"""Gerçek API üzerinde altın metin kapsamı ve isteğe bağlı çekimserlik kontrolü."""
import argparse
import getpass
import http.cookiejar
import json
from pathlib import Path
import statistics
import time
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8000")
parser.add_argument("--username", default="bekir")
parser.add_argument("--subject-id", required=True)
parser.add_argument("--dataset", default="samples/evaluation.json")
parser.add_argument("--output", default="output/evaluation.json")
parser.add_argument("--with-generation", action="store_true")
parser.add_argument("--delay", type=float, default=6, help="İstekler arasındaki saniye; varsayılan hız sınırlarına uyum sağlar.")
args = parser.parse_args()
target = Path(args.output)
if target.exists():
    raise SystemExit("Çıktı zaten var; yeni bir --output yolu seç.")
cookie_jar = http.cookiejar.CookieJar()
client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


def post(path, body):
    request = urllib.request.Request(args.url.rstrip("/") + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "X-Requested-With": "DersAtlas"}, method="POST")
    with client.open(request, timeout=900) as response:
        return json.load(response)


post("/api/login", {"username": args.username, "password": getpass.getpass("Parola: ")})
questions = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
results = []
for item in questions:
    if results:
        time.sleep(max(0, args.delay))
    start = time.perf_counter()
    body = {"subject_id": args.subject_id, "question": item["question"], "mode": "rag"}
    sources = post("/api/search", body)["sources"]
    joined = "\n".join(s["text"] for s in sources).casefold()
    snippets = item["expected_snippets"]
    span_recall = sum(s.casefold() in joined for s in snippets) / len(snippets) if snippets else None
    row = {"question": item["question"], "answerable": item["answerable"], "retrieved": len(sources), "gold_span_coverage_at_k": span_recall,
           "retrieval_ms": round((time.perf_counter() - start) * 1000)}
    if args.with_generation:
        answer = post("/api/questions", body)
        row.update({"outcome": answer["outcome"], "answer": answer["answer"], "answerability_match": (answer["outcome"] == "answered") if item["answerable"] else (answer["outcome"] == "insufficient")})
    results.append(row)
    print(len(results), "/", len(questions), "tamamlandı")
report = {"note": "Altın metin kapsamı, semantik doğruluk veya bilimsel Recall@k ile aynı metrik değildir. İnsan incelemesi gerekir.",
          "mean_gold_span_coverage": statistics.mean(r["gold_span_coverage_at_k"] for r in results if r["gold_span_coverage_at_k"] is not None), "results": results}
target.parent.mkdir(parents=True, exist_ok=True)
with target.open("x", encoding="utf-8") as file:
    json.dump(report, file, ensure_ascii=False, indent=2)
print("Rapor:", target)

import argparse
import io
from pathlib import Path
import tempfile
import unittest
import urllib.error

from scripts.evaluate import (
    percentile,
    load_checkpoint,
    post_json,
    resolve_password,
    save_checkpoint,
    snippet_coverage,
    source_requirement_coverage,
    summarize,
    validate_dataset,
)


class EvaluationToolTests(unittest.TestCase):
    def test_password_prompt_explains_hidden_input_and_rejects_blank(self):
        prompts = []

        def blank_prompt(message):
            prompts.append(message)
            return ""

        with self.assertRaisesRegex(SystemExit, "Parola boş bırakılamaz"):
            resolve_password("DERSATLAS_EVAL_PASSWORD", {}, blank_prompt)
        self.assertIn("ekranda görünmez", prompts[0])

    def test_password_environment_value_skips_prompt(self):
        self.assertEqual(
            resolve_password(
                "DERSATLAS_EVAL_PASSWORD",
                {"DERSATLAS_EVAL_PASSWORD": "secret"},
                lambda _: self.fail("prompt çağrılmamalı"),
            ),
            "secret",
        )

    def test_post_json_retries_transient_503(self):
        class Client:
            calls = 0

            def open(self, request, timeout):
                self.calls += 1
                if self.calls < 3:
                    raise urllib.error.HTTPError(
                        request.full_url, 503, "unavailable", {}, None
                    )
                return io.BytesIO(b'{"ok": true}')

        client = Client()
        waits = []
        result = post_json(
            client,
            "http://127.0.0.1:8000/api/questions",
            {"question": "Soru"},
            retries=3,
            retry_wait=2,
            sleep=waits.append,
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(client.calls, 3)
        self.assertEqual(waits, [2, 4])

    def test_post_json_does_not_retry_permanent_http_error(self):
        class Client:
            def open(self, request, timeout):
                raise urllib.error.HTTPError(
                    request.full_url, 400, "bad request", {}, None
                )

        with self.assertRaises(urllib.error.HTTPError):
            post_json(
                Client(),
                "http://127.0.0.1:8000/api/questions",
                {},
                retries=3,
                retry_wait=0,
                sleep=lambda _: None,
            )

    def test_checkpoint_round_trip_and_run_guard(self):
        args = argparse.Namespace(
            url="http://127.0.0.1:8000",
            subject_id=None,
            mode="agent",
            with_generation=True,
        )
        questions = [
            {"id": "A", "question": "Birinci?"},
            {"id": "B", "question": "İkinci?"},
        ]
        from scripts.evaluate import _checkpoint_key

        key = _checkpoint_key(args, questions)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json.partial"
            save_checkpoint(path, key, [{"id": "A", "answer": "Yanıt"}])
            self.assertEqual(
                load_checkpoint(path, key, questions),
                [{"id": "A", "answer": "Yanıt"}],
            )
            wrong = {**key, "mode": "rag"}
            with self.assertRaises(SystemExit):
                load_checkpoint(path, wrong, questions)

    def test_snippet_coverage_is_case_insensitive_and_has_clear_denominator(self):
        self.assertEqual(snippet_coverage("29 MAYIS 1453 Fatih", ["29 Mayıs 1453", "Fatih"]), 1)
        self.assertEqual(snippet_coverage("Yalnızca Fatih", ["1453", "Fatih"]), 0.5)
        self.assertEqual(
            snippet_coverage("Yasama yetkisi TBMM'ye aittir.", [["Türkiye Büyük Millet Meclisi", "TBMM"]]),
            1,
        )

    def test_source_requirements_reject_unrelated_fragment_matches(self):
        sources = [
            {"text": "İstanbul 29 Mayıs 1453'te fethedildi."},
            {"text": "Kardeş katlini Fatih Sultan Mehmet kanunlaştırdı."},
        ]
        requirements = [
            {
                "expected": "29 Mayıs 1453",
                "all_terms": ["İstanbul", "feth"],
            },
            {
                "expected": ["Fatih Sultan Mehmet", "Fatih Sultan Mehmed"],
                "all_terms": ["İstanbul", "feth"],
                "any_terms": ["padişah", "tarafından", "döneminde"],
            },
        ]
        self.assertEqual(source_requirement_coverage(sources, requirements), 0.5)
        sources.append({
            "text": (
                "İstanbul'un fethi Fatih Sultan Mehmet döneminde "
                "gerçekleşmiştir."
            )
        })
        self.assertEqual(source_requirement_coverage(sources, requirements), 1)
        self.assertIsNone(snippet_coverage("metin", []))

    def test_percentile_uses_linear_interpolation(self):
        self.assertEqual(percentile([100, 200, 300], 50), 200)
        self.assertEqual(percentile([100, 200], 95), 195)
        self.assertIsNone(percentile([], 95))

    def test_dataset_contract_rejects_missing_gold_and_duplicate_ids(self):
        with self.assertRaises(ValueError):
            validate_dataset([{"id": "A", "question": "Soru?", "answerable": True}])
        with self.assertRaises(ValueError):
            validate_dataset([
                {"id": "A", "question": "Soru?", "answerable": False},
                {"id": "A", "question": "Başka?", "answerable": False},
            ])

    def test_summary_keeps_retrieval_answerability_and_latency_separate(self):
        rows = [
            {
                "answerable": True, "source_span_coverage": 1.0,
                "answer_span_coverage": 0.5, "answerability_match": True,
                "outcome": "answered", "duration_ms": 100,
            },
            {
                "answerable": False, "source_span_coverage": None,
                "answer_span_coverage": None, "answerability_match": True,
                "outcome": "insufficient", "duration_ms": 300,
            },
        ]
        result = summarize(rows, "agent")
        self.assertEqual(result["mean_source_span_coverage"], 1.0)
        self.assertEqual(result["mean_answer_span_coverage"], 0.5)
        self.assertEqual(result["answerability_accuracy"], 1.0)
        self.assertEqual(result["p50_ms"], 200)
        self.assertEqual(result["mode"], "agent")


if __name__ == "__main__":
    unittest.main()

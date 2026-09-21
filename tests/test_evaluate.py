import unittest

from scripts.evaluate import percentile, snippet_coverage, summarize, validate_dataset


class EvaluationToolTests(unittest.TestCase):
    def test_snippet_coverage_is_case_insensitive_and_has_clear_denominator(self):
        self.assertEqual(snippet_coverage("29 MAYIS 1453 Fatih", ["29 Mayıs 1453", "Fatih"]), 1)
        self.assertEqual(snippet_coverage("Yalnızca Fatih", ["1453", "Fatih"]), 0.5)
        self.assertEqual(
            snippet_coverage("Yasama yetkisi TBMM'ye aittir.", [["Türkiye Büyük Millet Meclisi", "TBMM"]]),
            1,
        )
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

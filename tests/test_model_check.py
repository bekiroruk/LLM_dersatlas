"""Gerçek model denemesinin kaynak alıntısını üretim başarısı saymaması."""
from contextlib import redirect_stdout
from io import StringIO
import json
import unittest
from unittest.mock import patch

import httpx

from app.config import Settings
from scripts import check_rag_model


class ModelCheckTests(unittest.TestCase):
    def test_http_request_carries_schema_and_debug_output_is_opt_in(self):
        requests = []

        def handle(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={
                "message": {"role": "assistant", "content": json.dumps({
                    "answer": "DEBUG_ANSWER\u001b", "source_ids": ["K1"],
                    "insufficient_evidence": False,
                })},
                "done_reason": "stop",
            })

        for details in (False, True):
            model = check_rag_model.DiagnosticOllama(Settings(_env_file=None), details=details)
            model.client.close()
            model.client = httpx.Client(base_url="http://ollama.test", transport=httpx.MockTransport(handle))
            stream = StringIO()
            try:
                with redirect_stdout(stream):
                    service = check_rag_model.ModelCheckRAG(Settings(_env_file=None), model, None)
                    service._call_structured("Test", "Örnek not", [], "draft", ["K1"])
            finally:
                model.close()
            output = stream.getvalue()
            self.assertIn('"kaynaklar": ["K1"]', output)
            self.assertIn('"bitis": "stop"', output)
            self.assertNotIn("\u001b", output)
            self.assertEqual("DEBUG_ANSWER" in output, details)

        for request in requests:
            self.assertEqual(request["format"]["anyOf"][0]["properties"]["source_ids"]["minItems"], 1)
            self.assertFalse(request["think"])
            self.assertFalse(request["stream"])
            self.assertIn(json.dumps(request["format"], ensure_ascii=False), request["messages"][0]["content"])

    def run_cli(self, argv, result):
        stream = StringIO()
        with patch.object(check_rag_model, "DiagnosticOllama") as factory:
            factory.return_value.status.return_value = {"reachable": True, "chat_ready": True}
            with patch.object(check_rag_model.ModelCheckRAG, "answer", return_value=result):
                with redirect_stdout(stream):
                    code = check_rag_model.main(argv)
            factory.return_value.close.assert_called_once()
        return code, stream.getvalue()

    def test_strict_check_fails_on_excerpts_and_labels_them_clearly(self):
        result = {
            "outcome": "answered", "answer_method": "source_excerpt",
            "answer": "Karadeniz nemli ormanlar; Akdeniz kızılçam, maki. [K1]",
            "sources": [{"chunk_id": "table"}], "trace": [],
        }
        code, output = self.run_cli(["--require-generated"], result)
        self.assertEqual(code, 1)
        self.assertIn("Model üretimi: 0/3. Kaynak alıntısı: 3/3.", output)
        self.assertNotIn("GEÇTİ", output)
        self.assertEqual(self.run_cli([], result)[0], 0)

    def test_strict_check_passes_for_generated_answers(self):
        result = {
            "outcome": "answered", "answer": "Karadeniz nemli ormanlar; Akdeniz kızılçam, maki. [K1]",
            "sources": [{"chunk_id": "table"}], "trace": [],
        }
        code, output = self.run_cli(["--require-generated"], result)
        self.assertEqual(code, 0)
        self.assertIn("Model üretimi: 3/3. Kaynak alıntısı: 0/3.", output)


if __name__ == "__main__":
    unittest.main()

"""Yerel model isteklerinin hız ve doğruluk bütçesi sözleşmeleri."""
import json
import unittest

import httpx

from app.config import Settings
from app.providers import Ollama


class OllamaTests(unittest.TestCase):
    def test_tool_planning_uses_smaller_generation_budget(self):
        requests = []

        def handle(request):
            requests.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={"message": {"role": "assistant", "content": ""}},
            )

        model = Ollama(
            Settings(_env_file=None),
            transport=httpx.MockTransport(handle),
        )
        try:
            messages = [{"role": "user", "content": "Test"}]
            model.chat(messages, tools=[{"type": "function"}])
            model.chat(messages, schema={"type": "object"})
        finally:
            model.close()

        self.assertEqual(requests[0]["options"]["num_predict"], 192)
        self.assertEqual(requests[1]["options"]["num_predict"], 512)
        self.assertFalse(requests[0]["think"])
        self.assertFalse(requests[1]["think"])


if __name__ == "__main__":
    unittest.main()

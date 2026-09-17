"""Gerçek SQLite + gömülü Qdrant; LLM yalnızca bu testte deterministik bir test çiftidir."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REQUIRED = ["fastapi", "httpx", "sqlalchemy", "pydantic_settings", "qdrant_client", "multipart"]
AVAILABLE = all(importlib.util.find_spec(name) for name in REQUIRED)
if AVAILABLE:
    from fastapi.testclient import TestClient
    from sqlalchemy import select
    from app.config import Settings
    from app.db import User, Subject, Membership, Document, Chunk
    from app.main import create_app
    from app.passwords import hash_password
    from app.providers import ModelUnavailable


class FakeModel:
    invalid = False
    unavailable = False
    tool_calls = None

    def embed(self, texts):
        if self.unavailable:
            raise ModelUnavailable("Test modeli kapalı")
        return [[1.0, 0.0, 0.0] for _ in texts]

    def chat(self, messages, tools=None, schema=None):
        if tools:
            calls, self.tool_calls = self.tool_calls, None
            return {"role": "assistant", "content": "", "tool_calls": calls or []}
        key = "K99" if self.invalid else "K1"
        return {"role": "assistant", "content": json.dumps({"answer": "Test yanıtı. [" + key + "]", "source_ids": [key], "insufficient_evidence": False})}

    def status(self):
        return {"reachable": True, "chat_ready": True, "embed_ready": True}

    def close(self):
        pass


@unittest.skipUnless(AVAILABLE, "API bağımlılıkları yok; pip install -r requirements-dev.txt sonrası çalıştır.")
class APITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        folder = Path(self.temp.name)
        config = Settings(_env_file=None, data_dir=folder, database_url="sqlite:///" + str(folder / "test.db"), worker_enabled=False, max_upload_mb=1)
        self.model = FakeModel()
        self.app = create_app(config, model=self.model)
        self.client = TestClient(self.app)
        self.client.__enter__()
        with self.app.state.sessions() as db:
            user = User(username="bekir", password_hash=hash_password("Test-Password-1234"), role="admin")
            other = User(username="other", password_hash=hash_password("Test-Password-1234"), role="admin")
            db.add_all([user, other]); db.flush()
            first, second = Subject(owner_id=user.id, name="Tarih"), Subject(owner_id=other.id, name="Özel")
            db.add_all([first, second]); db.commit()
            self.subject, self.other_subject, self.other_user = first.id, second.id, other.id
        self.headers = {"X-Requested-With": "DersAtlas"}
        self.login()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def login(self, name="bekir"):
        return self.client.post('/api/login', json={"username": name, "password": "Test-Password-1234"}, headers=self.headers)

    def upload(self, subject=None, content=b"Tanzimat Fermani 1839 yilinda ilan edildi. Bu bir test metnidir."):
        return self.client.post(f'/api/subjects/{subject or self.subject}/documents', files={"file": ("tarih.txt", content, "text/plain")}, headers=self.headers)

    def ready_document(self):
        response = self.upload()
        self.assertEqual(response.status_code, 202)
        self.app.state.worker.process_one()
        return response.json()["id"]

    def ask(self, mode="rag"):
        return self.client.post('/api/questions', json={"subject_id": self.subject, "question": "Tanzimat ne zaman?", "mode": mode}, headers=self.headers)

    def test_auth_required(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.get('/api/subjects').status_code, 401)

    def test_csrf_header_required(self):
        self.assertEqual(self.client.post('/api/subjects', json={"name": "Coğrafya"}).status_code, 403)

    def test_cross_origin_rejected(self):
        response = self.client.post('/api/subjects', json={"name": "Coğrafya"}, headers={**self.headers, "Origin": "https://foreign.invalid"})
        self.assertEqual(response.status_code, 403)

    def test_subject_isolation(self):
        self.assertEqual(self.client.get(f'/api/subjects/{self.other_subject}/documents').status_code, 404)
        self.assertEqual(self.upload(self.other_subject).status_code, 404)

    def test_upload_and_rag(self):
        self.ready_document()
        response = self.ask()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outcome"], "answered")
        self.assertEqual(response.json()["sources"][0]["location"], "Metin blok 1")

    def test_duplicate_document(self):
        self.assertEqual(self.upload().status_code, 202)
        self.assertEqual(self.upload().status_code, 409)

    def test_unsupported_extension(self):
        response = self.client.post(f'/api/subjects/{self.subject}/documents', files={"file": ("run.exe", b"hello")}, headers=self.headers)
        self.assertEqual(response.status_code, 415)

    def test_request_body_limit(self):
        self.assertEqual(self.upload(content=b"x" * (2 * 1024 * 1024)).status_code, 413)

    def test_no_sources_no_fabrication(self):
        result = self.ask().json()
        self.assertEqual(result["outcome"], "insufficient")
        self.assertEqual(result["sources"], [])

    def test_invalid_citations(self):
        self.ready_document(); self.model.invalid = True
        result = self.ask().json()
        self.assertEqual(result["outcome"], "invalid_citations")
        self.assertNotIn("Test yanıtı", result["answer"])

    def test_model_failure(self):
        self.ready_document(); self.model.unavailable = True
        self.assertEqual(self.ask().status_code, 503)

    def test_failed_ingestion_not_searchable(self):
        self.upload(); self.model.unavailable = True
        self.app.state.worker.process_one()
        docs = self.client.get(f'/api/subjects/{self.subject}/documents').json()
        self.assertEqual(docs[0]["status"], "error")
        self.assertEqual(self.ask().json()["outcome"], "insufficient")

    def test_delete_excluded_immediately_and_purged(self):
        doc_id = self.ready_document()
        self.assertEqual(self.client.delete(f'/api/documents/{doc_id}', headers=self.headers).status_code, 202)
        self.assertEqual(self.ask().json()["sources"], [])
        self.app.state.worker.process_one()
        self.assertEqual(self.client.get(f'/api/documents/{doc_id}/download').status_code, 404)

    def test_download_acl(self):
        doc_id = self.ready_document()
        self.login("other")
        self.assertEqual(self.client.get(f'/api/documents/{doc_id}/download').status_code, 404)

    def test_reader_can_query_cannot_mutate(self):
        doc_id = self.ready_document()
        with self.app.state.sessions() as db:
            other = db.get(User, self.other_user); other.role = "student"
            db.add(Membership(subject_id=self.subject, user_id=self.other_user)); db.commit()
        self.login("other")
        self.assertEqual(self.ask().status_code, 200)
        self.assertEqual(self.client.delete(f'/api/documents/{doc_id}', headers=self.headers).status_code, 403)

    def test_agent_rejects_shell(self):
        self.ready_document()
        self.model.tool_calls = [{"function": {"name": "shell", "arguments": {"command": "never execute"}}}]
        result = self.ask("agent").json()
        self.assertTrue(any(step["tool"] == "rejected" for step in result["trace"]))

    def test_feedback_owner(self):
        self.ready_document()
        query_id = self.ask().json()["query_id"]
        self.login("other")
        response = self.client.post(f'/api/queries/{query_id}/feedback', json={"value": 1}, headers=self.headers)
        self.assertEqual(response.status_code, 404)

    def test_logout_revokes_session(self):
        token = self.client.cookies.get('dersatlas_session')
        self.client.post('/api/logout', headers=self.headers)
        self.client.cookies.set('dersatlas_session', token)
        self.assertEqual(self.client.get('/api/me').status_code, 401)


if __name__ == '__main__':
    unittest.main()

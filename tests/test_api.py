"""Gerçek SQLite + gömülü Qdrant; LLM yalnızca bu testte deterministik bir test çiftidir."""
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

REQUIRED = ["fastapi", "httpx", "sqlalchemy", "pydantic_settings", "qdrant_client", "multipart"]
AVAILABLE = all(importlib.util.find_spec(name) for name in REQUIRED)
if AVAILABLE:
    from fastapi.testclient import TestClient
    from sqlalchemy import select
    from app.config import Settings
    from app.db import User, Subject, Membership, Document, Chunk, QueryMetric
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

    def owned_subject(self, name="Coğrafya"):
        response = self.client.post('/api/subjects', json={"name": name}, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def ready_in(self, subject, text):
        response = self.upload(subject=subject, content=text.encode("utf-8"))
        self.assertEqual(response.status_code, 202)
        self.app.state.worker.process_one()
        return response.json()["id"]

    def search_notes(self, question="Tanzimat", subject_id=None):
        return self.client.post('/api/search', json={"subject_id": subject_id, "question": question}, headers=self.headers)

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

    def test_general_question_omitted_and_null_subject(self):
        doc_id = self.ready_document()
        for scope in ({}, {"subject_id": None}):
            with self.subTest(scope=scope):
                response = self.client.post('/api/questions', json={**scope, "question": "Tanzimat ne zaman?"}, headers=self.headers)
                self.assertEqual(response.status_code, 200)
                result = response.json()
                self.assertEqual(result["outcome"], "answered")
                self.assertEqual(result["scope"], {"type": "all", "subject_id": None})
                source = result["sources"][0]
                self.assertEqual(source["subject_id"], self.subject)
                self.assertEqual(source["subject_name"], "Tarih")
                self.assertEqual(source["document_id"], doc_id)
                self.assertEqual(source["filename"], "tarih.txt")
                self.assertEqual(source["location"], "Metin blok 1")

    def test_general_search_all_owned_subjects_and_optional_filter(self):
        self.ready_document()
        geography = self.owned_subject()
        self.ready_in(geography, "Türkiye iklim çeşitliliği bakımından zengindir.")
        all_sources = self.search_notes().json()["sources"]
        self.assertEqual({s["subject_id"] for s in all_sources}, {self.subject, geography})
        filtered = self.search_notes(subject_id=geography).json()["sources"]
        self.assertEqual({s["subject_id"] for s in filtered}, {geography})
        self.assertTrue(all(s["subject_name"] == "Coğrafya" for s in filtered))

    def test_general_metric_feedback_and_dashboard(self):
        self.ready_document()
        result = self.client.post('/api/questions', json={"question": "Tanzimat ne zaman?"}, headers=self.headers).json()
        response = self.client.post('/api/queries/' + result["query_id"] + '/feedback', json={"value": 1}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        with self.app.state.sessions() as db:
            metric = db.get(QueryMetric, result["query_id"])
            self.assertIsNone(metric.subject_id)
            self.assertEqual(metric.feedback, 1)
        dashboard = self.client.get('/api/dashboard').json()
        self.assertEqual(dashboard["query_count"], 1)
        self.assertEqual(dashboard["positive_feedback"], 1)
        self.login("other")
        self.assertEqual(self.client.post('/api/queries/' + result["query_id"] + '/feedback', json={"value": -1}, headers=self.headers).status_code, 404)

    def test_filtered_metric_keeps_subject(self):
        self.ready_document()
        result = self.ask().json()
        self.assertEqual(result["scope"], {"type": "subject", "subject_id": self.subject})
        with self.app.state.sessions() as db:
            self.assertEqual(db.get(QueryMetric, result["query_id"]).subject_id, self.subject)

    def test_general_never_leaks_another_owners_notes(self):
        self.ready_document()
        self.login("other")
        private_id = self.ready_in(self.other_subject, "Tanzimat özel kullanıcıya ait gizli not.")
        self.login()
        sources = self.search_notes().json()["sources"]
        self.assertTrue(sources)
        self.assertNotIn(private_id, {s["document_id"] for s in sources})
        self.assertNotIn(self.other_subject, {s["subject_id"] for s in sources})
        for path in ('/api/questions', '/api/search'):
            response = self.client.post(path, json={"subject_id": self.other_subject, "question": "Tanzimat"}, headers=self.headers)
            self.assertEqual(response.status_code, 404)

    def test_general_includes_membership_and_revocation_applies_next_request(self):
        doc_id = self.ready_document()
        with self.app.state.sessions() as db:
            other = db.get(User, self.other_user)
            other.role = "student"
            db.add(Membership(subject_id=self.subject, user_id=self.other_user))
            db.commit()
        self.login("other")
        self.assertIn(doc_id, {s["document_id"] for s in self.search_notes().json()["sources"]})
        with self.app.state.sessions() as db:
            membership = db.get(Membership, (self.subject, self.other_user))
            db.delete(membership)
            db.commit()
        self.assertEqual(self.search_notes().json()["sources"], [])
        self.assertEqual(self.client.get(f'/api/documents/{doc_id}/download').status_code, 404)

    def test_general_rechecks_dense_results_in_relational_acl(self):
        self.ready_document()
        self.login("other")
        private_doc = self.ready_in(self.other_subject, "Özel kullanıcının gizli bilgisi.")
        with self.app.state.sessions() as db:
            private_chunk = db.scalar(select(Chunk).where(Chunk.document_id == private_doc)).id
        self.login()
        # Hatalı/ele geçirilmiş vektör yanıtı bile yetkisiz metin getiremez.
        with patch.object(self.app.state.vectors, "search", return_value=[(private_chunk, 1.0)]):
            self.assertEqual(self.search_notes("gizli bilgisi").json()["sources"], [])

    def test_general_excludes_deleted_failed_and_wrong_embedding_documents(self):
        doc_id = self.ready_document()
        for change in ("deleting", "error", "different-model"):
            with self.subTest(change=change):
                with self.app.state.sessions() as db:
                    doc = db.get(Document, doc_id)
                    doc.status = "ready" if change == "different-model" else change
                    doc.embedding_model = "other-model" if change == "different-model" else self.app.state.rag.settings.embed_model
                    db.commit()
                self.assertEqual(self.search_notes().json()["sources"], [])

    def test_mismatched_chunk_subject_excluded_and_chunk_acl_preserved(self):
        doc_id = self.ready_document()
        with self.app.state.sessions() as db:
            chunk = db.scalar(select(Chunk).where(Chunk.document_id == doc_id))
            chunk.subject_id = self.other_subject
            chunk_id = chunk.id
            db.commit()
        self.assertEqual(self.search_notes().json()["sources"], [])
        self.assertEqual(self.client.get('/api/chunks/' + chunk_id).status_code, 404)

    def test_chunk_has_current_course_name_and_download_stays_protected(self):
        doc_id = self.ready_document()
        with self.app.state.sessions() as db:
            chunk_id = db.scalar(select(Chunk.id).where(Chunk.document_id == doc_id))
            db.get(Subject, self.subject).name = "Tarih notlarım"
            db.commit()
        chunk = self.client.get('/api/chunks/' + chunk_id).json()
        self.assertEqual(chunk["subject_name"], "Tarih notlarım")
        self.assertEqual(self.search_notes().json()["sources"][0]["subject_name"], "Tarih notlarım")
        self.login("other")
        self.assertEqual(self.client.get('/api/chunks/' + chunk_id).status_code, 404)

    def test_no_accessible_courses_agent_does_not_call_models(self):
        with self.app.state.sessions() as db:
            db.add(User(username="emptyuser", password_hash=hash_password("Test-Password-1234"), role="student"))
            db.commit()
        self.login("emptyuser")
        with patch.object(self.model, "embed", side_effect=AssertionError("Embedding çağrılmamalı")), patch.object(self.model, "chat", side_effect=AssertionError("LLM çağrılmamalı")):
            result = self.client.post('/api/questions', json={"question": "Tanzimat nedir?", "mode": "agent"}, headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["outcome"], "insufficient")
        self.assertEqual(result.json()["sources"], [])

    def test_global_blank_question_and_invalid_subject_rejected(self):
        for path in ('/api/questions', '/api/search'):
            self.assertEqual(self.client.post(path, json={"question": "   "}, headers=self.headers).status_code, 422)
            self.assertEqual(self.client.post(path, json={"subject_id": "", "question": "Tanzimat"}, headers=self.headers).status_code, 422)

    def test_agent_researches_across_courses_or_respects_explicit_filter(self):
        self.ready_document()
        geography = self.owned_subject()
        self.ready_in(geography, "Türkiye iklim çeşitliliği bakımından zengindir.")
        for scope, expected in ((None, {self.subject, geography}), (self.subject, {self.subject})):
            with self.subTest(scope=scope), self.app.state.sessions() as db:
                user = db.scalar(select(User).where(User.username == "bekir"))
                self.model.tool_calls = [{"function": {"name": "search_notes", "arguments": {"query": "Türkiye iklim çeşitliliği"}}}]
                sources, trace = self.app.state.rag.agent_search(db, user, scope, "Tanzimat ve iklim", [])
                self.assertEqual({s["subject_id"] for s in sources}, expected)
                self.assertEqual(trace[0]["tool"], "search_notes")

    def test_global_agent_endpoint_executes_read_only_search(self):
        self.ready_document()
        self.model.tool_calls = [{"function": {"name": "search_notes", "arguments": {"query": "Tanzimat Fermani"}}}]
        result = self.client.post('/api/questions', json={"question": "Tanzimat ne zaman?", "mode": "agent"}, headers=self.headers).json()
        self.assertEqual(result["outcome"], "answered")
        self.assertEqual(result["scope"]["type"], "all")
        self.assertTrue(any(s.get("query") == "Tanzimat Fermani" and s["found"] > 0 for s in result["trace"]))

    def test_agent_can_recover_when_initial_search_is_empty(self):
        self.ready_document()
        self.model.tool_calls = [{"function": {"name": "search_notes", "arguments": {"query": "Tanzimat Fermani"}}}]
        retrieve = self.app.state.rag.retrieve
        searches = 0

        def initially_empty(*args):
            nonlocal searches
            searches += 1
            return [] if searches == 1 else retrieve(*args)

        with patch.object(self.app.state.rag, "retrieve", side_effect=initially_empty):
            result = self.client.post('/api/questions', json={"question": "Tanzimat ne zaman?", "mode": "agent"}, headers=self.headers).json()
        self.assertEqual(result["trace"][0]["found"], 0)
        self.assertEqual(result["trace"][1]["found"], 1)
        self.assertEqual(result["outcome"], "answered")

    def test_agent_cannot_override_scope_or_use_write_network_sql_tools(self):
        for name, arguments in (
            ("search_notes", {"query": "Tanzimat", "subject_id": self.other_subject}),
            ("shell", {"command": "never execute"}),
            ("sql", {"query": "never execute"}),
            ("http", {"url": "https://example.invalid"}),
            ("delete_document", {"document_id": "never delete"}),
        ):
            with self.subTest(tool=name), self.app.state.sessions() as db:
                user = db.scalar(select(User).where(User.username == "bekir"))
                self.model.tool_calls = [{"function": {"name": name, "arguments": arguments}}]
                sources, trace = self.app.state.rag.agent_search(db, user, None, "Tanzimat", [])
                self.assertEqual(sources, [])
                self.assertEqual(trace, [{"tool": "rejected", "found": 0}])

    def test_agent_accepts_json_arguments_and_rejects_malformed_calls(self):
        self.ready_document()
        for calls, expected in (
            ([{"function": {"name": "search_notes", "arguments": '{"query":"Tanzimat"}'}}], "search_notes"),
            ([{"function": {"name": "search_notes", "arguments": "{bad"}}], "rejected"),
            ([{"function": None}], "rejected"),
            ([None], "rejected"),
            ({"not": "a list"}, "rejected"),
            ([{"function": {"name": "search_notes", "arguments": {"query": "   "}}}], "rejected"),
        ):
            with self.subTest(calls=calls), self.app.state.sessions() as db:
                user = db.scalar(select(User).where(User.username == "bekir"))
                self.model.tool_calls = calls
                _, trace = self.app.state.rag.agent_search(db, user, None, "Tanzimat", [])
                self.assertEqual(trace[0]["tool"], expected)

    def test_agent_limits_rounds_and_calls_per_round(self):
        self.ready_document()
        calls = [{"function": {"name": "search_notes", "arguments": {"query": "Tanzimat"}}}] * 3
        with self.app.state.sessions() as db, patch.object(self.model, "chat", return_value={"tool_calls": calls}) as mocked:
            user = db.scalar(select(User).where(User.username == "bekir"))
            _, trace = self.app.state.rag.agent_search(db, user, None, "Tanzimat", [])
        self.assertEqual(mocked.call_count, self.app.state.rag.settings.agent_max_rounds)
        self.assertEqual(len(trace), self.app.state.rag.settings.agent_max_rounds * 2)

    def test_source_course_metadata_reaches_answer_model(self):
        self.ready_document()
        with patch.object(self.model, "chat", wraps=self.model.chat) as chat:
            result = self.client.post('/api/questions', json={"question": "Tanzimat ne zaman?"}, headers=self.headers)
        self.assertEqual(result.status_code, 200)
        messages = chat.call_args_list[0].args[0]
        self.assertIn('"subject_name": "Tarih"', messages[1]["content"])

    def test_global_history_notes_do_not_answer_python_from_model_memory(self):
        self.ready_document()
        result = self.client.post('/api/questions', json={"question": "Python'da liste nasıl oluşturulur?"}, headers=self.headers).json()
        self.assertEqual(result["outcome"], "insufficient")
        self.assertEqual(result["sources"], [])


if __name__ == '__main__':
    unittest.main()

import hashlib
import math
import threading
import httpx
from qdrant_client import QdrantClient, models


class ModelUnavailable(RuntimeError):
    pass


class Ollama:
    def __init__(self, settings, transport=None):
        self.settings = settings
        self.client = httpx.Client(base_url=settings.ollama_url, timeout=settings.ollama_timeout, trust_env=False, transport=transport)
        self.lock = threading.Lock()

    def _post(self, endpoint, payload):
        try:
            with self.lock:
                response = self.client.post(endpoint, json=payload)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ModelUnavailable("Yerel model yanıt vermedi. Ollama, model adları ve sistem belleğini kontrol et.") from exc

    def embed(self, texts):
        payload = self._post(
            "/api/embed",
            {
                "model": self.settings.embed_model,
                "input": texts,
                "truncate": False,
                "keep_alive": "15m",
            },
        )
        vectors = payload.get("embeddings", [])
        if len(vectors) != len(texts) or not vectors:
            raise ModelUnavailable("Embedding yanıtı beklenen boyutta değil.")
        for vector in vectors:
            if not vector or not all(isinstance(n, (int, float)) and math.isfinite(n) for n in vector):
                raise ModelUnavailable("Geçersiz embedding vektörü.")
        if len({len(v) for v in vectors}) != 1:
            raise ModelUnavailable("Embedding boyutları tutarsız.")
        return vectors

    def chat(self, messages, tools=None, schema=None):
        payload = {
            "model": self.settings.chat_model,
            "messages": messages,
            "stream": False,
            "think": False,
            "keep_alive": "15m",
            "options": {
                "temperature": 0.0,
                "seed": 42,
                "top_k": 1,
                "top_p": 1.0,
                "num_ctx": 6144,
                "num_predict": 800,
            },
        }
        if tools:
            payload["tools"] = tools
        if schema:
            payload["format"] = schema
        result = self._post("/api/chat", payload)
        if not isinstance(result.get("message"), dict):
            raise ModelUnavailable("Model geçersiz mesaj döndürdü.")
        return result["message"]

    def status(self):
        try:
            response = self.client.get("/api/tags", timeout=3)
            response.raise_for_status()
            names = [m["name"] for m in response.json().get("models", [])]
            def installed(model):
                return model in names or (":" not in model and model + ":latest" in names)
            return {"reachable": True, "chat_ready": installed(self.settings.chat_model), "embed_ready": installed(self.settings.embed_model)}
        except (httpx.HTTPError, ValueError, KeyError):
            return {"reachable": False, "chat_ready": False, "embed_ready": False}

    def close(self):
        self.client.close()


class VectorStore:
    def __init__(self, settings):
        self.settings = settings
        self.lock = threading.RLock()
        self.client = (QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None, timeout=20)
                       if settings.qdrant_url else QdrantClient(path=str(settings.data_dir / "qdrant"), force_disable_check_same_thread=True))

    @staticmethod
    def collection(model):
        return "dersatlas_" + hashlib.sha256((model + "|v1").encode()).hexdigest()[:16]

    def upsert(self, model, chunks, vectors):
        name = self.collection(model)
        with self.lock:
            if not self.client.collection_exists(name):
                self.client.create_collection(name, vectors_config=models.VectorParams(size=len(vectors[0]), distance=models.Distance.COSINE))
                for key in ["subject_id", "document_id"]:
                    if self.settings.qdrant_url:
                        self.client.create_payload_index(name, key, models.PayloadSchemaType.KEYWORD)
            self.client.upsert(name, points=[models.PointStruct(id=c.id, vector=v, payload={"subject_id": c.subject_id, "document_id": c.document_id}) for c, v in zip(chunks, vectors, strict=True)], wait=True)

    def search(self, model, subject_id, vector, limit=20):
        # Tek ders çağrıları geriye uyumlu; genel arama da mutlaka ACL listesi alır.
        subject_ids = [subject_id] if isinstance(subject_id, str) else list(subject_id or [])
        if not subject_ids:
            return []
        match = (models.MatchValue(value=subject_ids[0]) if len(subject_ids) == 1
                 else models.MatchAny(any=subject_ids))
        with self.lock:
            name = self.collection(model)
            if not self.client.collection_exists(name):
                return []
            result = self.client.query_points(name, query=vector, query_filter=models.Filter(must=[models.FieldCondition(key="subject_id", match=match)]), limit=limit, with_payload=False)
            return [(str(p.id), p.score) for p in result.points]

    def delete_document(self, model, document_id):
        if not model:
            return
        with self.lock:
            name = self.collection(model)
            if self.client.collection_exists(name):
                self.client.delete(name, models.FilterSelector(filter=models.Filter(must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))])), wait=True)

    def status(self):
        try:
            with self.lock:
                self.client.get_collections()
            return True
        except Exception:
            return False

    def close(self):
        self.client.close()

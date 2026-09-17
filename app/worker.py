import logging
import threading
from sqlalchemy import delete, select, update
from .db import Document, Chunk, uid
from .ingestion import extract_document, chunk_sections, DocumentError
from .providers import ModelUnavailable

logger = logging.getLogger(__name__)


class IngestWorker:
    """SQL'deki belge durumları kalıcı iş kuyruğudur; yalnızca tek süreç/worker."""
    def __init__(self, settings, session_factory, model, vectors):
        self.settings, self.sessions, self.model, self.vectors = settings, session_factory, model, vectors
        self.stop_event = threading.Event()
        self.work_lock = threading.Lock()
        self.thread = None

    def start(self):
        with self.sessions() as db:
            db.execute(update(Document).where(Document.status == "processing").values(status="queued"))
            db.commit()
        self.thread = threading.Thread(target=self.run, name="document-worker", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=self.settings.ollama_timeout + 25)

    def run(self):
        while not self.stop_event.is_set():
            try:
                if not self.process_one():
                    self.stop_event.wait(1)
            except Exception:
                logger.error("worker_cycle_failed")  # İçerik/parola loglanmaz.
                self.stop_event.wait(3)

    def process_one(self):
        with self.work_lock, self.sessions() as db:
            doc = db.scalar(select(Document).where(Document.status.in_(["queued", "deleting"])).order_by(Document.created_at).limit(1))
            if not doc:
                return False
            deleting = doc.status == "deleting"
            document_id = doc.id
            path = self.settings.data_dir / "originals" / doc.id
            old_model = doc.embedding_model
            try:
                if deleting:
                    self.vectors.delete_document(old_model, doc.id)
                    db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
                    path.unlink(missing_ok=True)
                    db.delete(doc)
                    db.commit()
                    return True
                doc.status, doc.error = "processing", ""
                db.commit()
                self.vectors.delete_document(old_model, doc.id)
                db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
                doc.embedding_model = self.settings.embed_model
                doc.chunk_count = 0
                db.commit()
                sections, warning = extract_document(path, doc.filename, self.settings.max_pages)
                parts = chunk_sections(sections, self.settings.chunk_chars, self.settings.chunk_overlap)
                if len(parts) > 5000:
                    raise DocumentError("Çok fazla metin parçası oluştu; belgeyi böl.")
                for start in range(0, len(parts), 16):
                    if self.stop_event.is_set():
                        # Processing açılışta tekrar kuyruğa alınır; yarım içerik aranamaz.
                        return True
                    batch = parts[start:start + 16]
                    chunks = [Chunk(id=uid(), document_id=doc.id, subject_id=doc.subject_id, location=p.location, ordinal=start + index, text=p.text) for index, p in enumerate(batch)]
                    embeddings = self.model.embed([chunk.text for chunk in chunks])
                    self.vectors.upsert(self.settings.embed_model, chunks, embeddings)
                    db.add_all(chunks)
                    db.commit()
                doc.status, doc.warning, doc.chunk_count = "ready", warning, len(parts)
                db.commit()
            except Exception as exc:
                db.rollback()
                doc = db.get(Document, document_id)
                if doc:
                    doc.status = "delete_error" if deleting else "error"
                    doc.error = str(exc)[:500] if isinstance(exc, (DocumentError, ModelUnavailable)) else "Dosya işlenemedi veya indeks hizmeti kullanılamıyor. Dosyayı ve sistem durumunu kontrol edip tekrar dene."
                    db.commit()
                logger.warning("document_job_failed id=%s type=%s", document_id, type(exc).__name__)
            return True


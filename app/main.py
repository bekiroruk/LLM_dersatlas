import hashlib
import math
import secrets
import statistics
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .config import Settings
from .db import make_database, User, LoginSession, Subject, Document, Chunk, QueryMetric, AuditEvent, uid
from .security import hash_password, check_password, token_hash, require_subject, subject_filter, RateLimiter
from .providers import Ollama, VectorStore, ModelUnavailable
from .worker import IngestWorker
from .rag import RAGService, RAG_REVISION
from .conversation import HistoryTurn, MAX_HISTORY_TURNS, MAX_HISTORY_CHARS, history_size

ROOT = Path(__file__).resolve().parent.parent


class BodyLimitMiddleware:
    """Multipart ayrıştırıcı çalışmadan önce gövdeyi sınırlı boyutta kabul eder."""
    def __init__(self, app, limit):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        maximum = self.limit if b"multipart/form-data" in headers.get(b"content-type", b"") else 64 * 1024
        data = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            data.extend(message.get("body", b""))
            if len(data) > maximum:
                return await JSONResponse({"detail": "İstek boyutu izin verilen sınırı aşıyor."}, status_code=413)(scope, receive, send)
            if not message.get("more_body", False):
                break
        delivered = False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(data), "more_body": False}
            return await receive()
        await self.app(scope, replay, send)


class LoginBody(BaseModel):
    username: str = Field(min_length=3, max_length=60)
    password: str = Field(min_length=1, max_length=256)


class SubjectBody(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class QuestionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str | None = Field(default=None, min_length=36, max_length=36)
    question: str = Field(min_length=3, max_length=1200)
    mode: Literal["rag", "agent"] = "rag"
    history: list[HistoryTurn] = Field(default_factory=list, max_length=MAX_HISTORY_TURNS)

    @model_validator(mode="after")
    def bounded_history(self):
        if history_size(self.history) > MAX_HISTORY_CHARS:
            raise ValueError("Sohbet bağlamı toplam 6000 karakteri aşamaz.")
        return self


class FeedbackBody(BaseModel):
    value: Literal[-1, 1]


def create_app(settings=None, model=None, vectors=None):
    config = settings or Settings()
    limiter = RateLimiter()
    dummy_hash = hash_password(secrets.token_urlsafe(30))

    @asynccontextmanager
    async def lifespan(app):
        engine, sessions = make_database(config)
        app.state.sessions = sessions
        app.state.model = model or Ollama(config)
        app.state.vectors = vectors or VectorStore(config)
        app.state.rag = RAGService(config, app.state.model, app.state.vectors)
        app.state.worker = IngestWorker(config, sessions, app.state.model, app.state.vectors)
        app.state.question_lock = threading.Lock()
        (config.data_dir / "originals").mkdir(parents=True, exist_ok=True)
        if config.worker_enabled:
            app.state.worker.start()
        yield
        app.state.worker.stop()
        app.state.model.close()
        app.state.vectors.close()
        engine.dispose()

    app = FastAPI(title="DersAtlas API", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url="/api/openapi.json")
    app.add_middleware(BodyLimitMiddleware, limit=config.max_upload_mb * 1024 * 1024 + 512 * 1024)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[h.strip() for h in config.allowed_hosts.split(",")])

    @app.middleware("http")
    async def security_headers(request, call_next):
        if request.url.path.startswith("/api/") and request.method not in {"GET", "HEAD", "OPTIONS"}:
            if request.headers.get("x-requested-with") != "DersAtlas":
                return JSONResponse({"detail": "Güvenlik başlığı eksik."}, status_code=403)
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc != request.headers.get("host"):
                return JSONResponse({"detail": "Kaynak siteye izin verilmiyor."}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        if request.url.path.startswith("/api/") or request.url.path.startswith("/assets/") or request.url.path == "/":
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        return response

    def get_db():
        with app.state.sessions() as db:
            yield db

    def get_user(request: Request, db=Depends(get_db)):
        token = request.cookies.get("dersatlas_session", "")
        session = db.get(LoginSession, token_hash(token)) if token else None
        if not session or session.expires_at < time.time():
            raise HTTPException(401, "Oturum açman gerekiyor.")
        user = db.get(User, session.user_id)
        if not user:
            raise HTTPException(401, "Oturum geçersiz.")
        return user

    def get_document(db, user, document_id, write=False):
        doc = db.get(Document, document_id)
        if not doc:
            raise HTTPException(404, "Doküman bulunamadı.")
        require_subject(db, user, doc.subject_id, write)
        return doc

    def document_json(doc):
        return {"id": doc.id, "filename": doc.filename, "status": doc.status, "error": doc.error,
                "warning": doc.warning, "chunk_count": doc.chunk_count, "created_at": doc.created_at,
                "needs_reindex": doc.status == "ready" and doc.embedding_model != config.embed_model}

    @app.get("/health")
    def health():
        return {"status": "alive", "version": "0.1.0", "rag_revision": RAG_REVISION}

    @app.post("/api/login")
    def login(body: LoginBody, request: Request, response: Response, db=Depends(get_db)):
        ip = request.client.host if request.client else "unknown"
        limiter.check("login-ip:" + ip, 15, 300)
        limiter.check("login-user:" + body.username.lower(), 10, 300)
        user = db.scalar(select(User).where(User.username == body.username.lower()))
        valid = check_password(body.password, user.password_hash if user else dummy_hash)
        if not user or not valid:
            raise HTTPException(401, "Kullanıcı adı veya parola hatalı.")
        token = secrets.token_urlsafe(32)
        db.execute(delete(LoginSession).where(LoginSession.expires_at < time.time()))
        db.add(LoginSession(token_hash=token_hash(token), user_id=user.id, expires_at=time.time() + config.session_hours * 3600))
        db.add(AuditEvent(actor_id=user.id, action="login", target_id=user.id))
        db.commit()
        response.set_cookie("dersatlas_session", token, httponly=True, secure=config.cookie_secure, samesite="strict", max_age=config.session_hours * 3600, path="/")
        return {"id": user.id, "username": user.username, "role": user.role}

    @app.get("/api/me")
    def me(user=Depends(get_user)):
        return {"id": user.id, "username": user.username, "role": user.role}

    @app.post("/api/logout")
    def logout(request: Request, response: Response, db=Depends(get_db)):
        db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(request.cookies.get("dersatlas_session", ""))))
        db.commit()
        response.delete_cookie("dersatlas_session", path="/")
        return {"ok": True}

    @app.get("/api/subjects")
    def subjects(user=Depends(get_user), db=Depends(get_db)):
        return [{"id": s.id, "name": s.name, "can_write": s.owner_id == user.id and user.role == "admin"}
                for s in db.scalars(select(Subject).where(subject_filter(user)).order_by(Subject.name))]

    @app.post("/api/subjects", status_code=201)
    def add_subject(body: SubjectBody, user=Depends(get_user), db=Depends(get_db)):
        if user.role != "admin":
            raise HTTPException(403, "Ders eklemek için yönetici rolü gerekir.")
        name = body.name.strip()
        if len(name) < 2:
            raise HTTPException(422, "Ders adı en az iki karakter olmalı.")
        subject = Subject(name=name, owner_id=user.id)
        db.add(subject)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Bu ders zaten var.")
        return {"id": subject.id, "name": subject.name, "can_write": True}

    @app.get("/api/subjects/{subject_id}/documents")
    def documents(subject_id: str, user=Depends(get_user), db=Depends(get_db)):
        require_subject(db, user, subject_id)
        return [document_json(d) for d in db.scalars(select(Document).where(Document.subject_id == subject_id).order_by(Document.created_at.desc()))]

    @app.post("/api/subjects/{subject_id}/documents", status_code=202)
    def upload(subject_id: str, file: UploadFile = File(...), user=Depends(get_user), db=Depends(get_db)):
        require_subject(db, user, subject_id, write=True)
        limiter.check("upload:" + user.id, 30, 60)
        filename = (file.filename or "").replace("\\", "/").split("/")[-1]
        if not filename or len(filename) > 240 or any(ord(c) < 32 for c in filename) or Path(filename).suffix.lower() not in {".pdf", ".docx", ".txt", ".md"}:
            raise HTTPException(415, "Geçerli isimli PDF, DOCX, TXT veya MD dosyası seç.")
        doc_id, digest = uid(), hashlib.sha256()
        path = config.data_dir / "originals" / doc_id
        size = 0
        try:
            with path.open("xb") as target:
                while block := file.file.read(1024 * 1024):
                    size += len(block)
                    if size > config.max_upload_mb * 1024 * 1024:
                        raise HTTPException(413, f"Dosya en fazla {config.max_upload_mb} MB olabilir.")
                    digest.update(block)
                    target.write(block)
            if size == 0:
                raise HTTPException(422, "Boş dosya yüklenemez.")
            doc = Document(id=doc_id, subject_id=subject_id, filename=filename, sha256=digest.hexdigest(), status="queued")
            db.add(doc)
            db.add(AuditEvent(actor_id=user.id, action="upload", target_id=doc_id))
            db.commit()
            return document_json(doc)
        except IntegrityError:
            db.rollback()
            path.unlink(missing_ok=True)
            raise HTTPException(409, "Aynı içerik bu derste zaten yüklü; mevcut belgede Yeniden indeksle kullan.")
        except Exception:
            db.rollback()
            path.unlink(missing_ok=True)
            raise
        finally:
            file.file.close()

    @app.post("/api/documents/{document_id}/reindex", status_code=202)
    def reindex(document_id: str, user=Depends(get_user), db=Depends(get_db)):
        doc = get_document(db, user, document_id, write=True)
        if doc.status in {"queued", "processing", "deleting", "delete_error"}:
            raise HTTPException(409, "İşlem sürüyor veya silme bekliyor.")
        doc.status, doc.error = "queued", ""
        db.add(AuditEvent(actor_id=user.id, action="reindex", target_id=doc.id))
        db.commit()
        return document_json(doc)

    @app.delete("/api/documents/{document_id}", status_code=202)
    def remove(document_id: str, user=Depends(get_user), db=Depends(get_db)):
        doc = get_document(db, user, document_id, write=True)
        if doc.status in {"processing", "queued"}:
            raise HTTPException(409, "Dosya işlenirken silinemez; işlemin bitmesini bekle.")
        doc.status, doc.error = "deleting", ""
        db.add(AuditEvent(actor_id=user.id, action="delete_requested", target_id=doc.id))
        db.commit()
        return {"status": "deleting"}

    @app.get("/api/documents/{document_id}/download")
    def download(document_id: str, user=Depends(get_user), db=Depends(get_db)):
        doc = get_document(db, user, document_id)
        path = config.data_dir / "originals" / doc.id
        if doc.status in {"deleting", "delete_error"} or not path.is_file():
            raise HTTPException(404, "Dosya artık erişilebilir değil.")
        return FileResponse(path, media_type="application/octet-stream", filename=doc.filename)

    @app.get("/api/chunks/{chunk_id}")
    def chunk(chunk_id: str, user=Depends(get_user), db=Depends(get_db)):
        row = db.get(Chunk, chunk_id)
        if not row:
            raise HTTPException(404, "Kaynak bulunamadı.")
        doc = get_document(db, user, row.document_id)
        if doc.status != "ready" or row.subject_id != doc.subject_id:
            raise HTTPException(404, "Kaynak şu anda erişilebilir değil.")
        subject = require_subject(db, user, doc.subject_id)
        return {"text": row.text, "location": row.location, "filename": doc.filename,
                "document_id": doc.id, "subject_id": subject.id, "subject_name": subject.name}

    @app.post("/api/questions")
    def question(body: QuestionBody, user=Depends(get_user), db=Depends(get_db)):
        if body.subject_id is not None:
            require_subject(db, user, body.subject_id)
        limiter.check("question:" + user.id, 12, 60)
        if len(body.question.strip()) < 3:
            raise HTTPException(422, "Soruyu en az üç karakterle yaz.")
        if not app.state.question_lock.acquire(blocking=False):
            raise HTTPException(429, "Model başka bir soruyu işliyor; tamamlanınca tekrar dene.")
        start, result = time.perf_counter(), None
        try:
            result = app.state.rag.answer(db, user, body.subject_id, body.question.strip(), body.mode, history=body.history)
            return_result = result
        except ModelUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            metric = QueryMetric(user_id=user.id, subject_id=body.subject_id, mode=body.mode, outcome=result["outcome"] if result else "error", elapsed_ms=elapsed)
            try:
                db.add(metric)
                db.commit()
            finally:
                app.state.question_lock.release()
        return {**return_result, "elapsed_ms": round(elapsed), "query_id": metric.id,
                "scope": {"type": "all" if body.subject_id is None else "subject",
                          "subject_id": body.subject_id}}

    @app.post("/api/search")
    def search(body: QuestionBody, user=Depends(get_user), db=Depends(get_db)):
        if body.subject_id is not None:
            require_subject(db, user, body.subject_id)
        if len(body.question.strip()) < 3:
            raise HTTPException(422, "Soruyu en az üç karakterle yaz.")
        limiter.check("search:" + user.id, 30, 60)
        try:
            return {"sources": app.state.rag.retrieve(db, user, body.subject_id, body.question.strip())}
        except ModelUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.post("/api/queries/{query_id}/feedback")
    def feedback(query_id: str, body: FeedbackBody, user=Depends(get_user), db=Depends(get_db)):
        metric = db.scalar(select(QueryMetric).where(QueryMetric.id == query_id, QueryMetric.user_id == user.id))
        if not metric:
            raise HTTPException(404, "Sorgu bulunamadı.")
        metric.feedback = body.value
        db.commit()
        return {"ok": True}

    @app.get("/api/dashboard")
    def dashboard(user=Depends(get_user), db=Depends(get_db)):
        subject_ids = select(Subject.id).where(subject_filter(user))
        docs = list(db.scalars(select(Document).where(Document.subject_id.in_(subject_ids))))
        metrics = list(db.scalars(select(QueryMetric).where(QueryMetric.user_id == user.id).order_by(QueryMetric.created_at.desc()).limit(1000)))
        latencies = sorted(m.elapsed_ms for m in metrics)
        return {"documents": len(docs), "ready": sum(d.status == "ready" and d.embedding_model == config.embed_model for d in docs),
                "chunks": sum(d.chunk_count for d in docs if d.status == "ready" and d.embedding_model == config.embed_model),
                "query_count": len(metrics), "insufficient": sum(m.outcome == "insufficient" for m in metrics),
                "errors": sum(m.outcome == "error" for m in metrics),
                "p50_ms": round(statistics.median(latencies)) if latencies else None,
                "p95_ms": round(latencies[max(0, math.ceil(len(latencies) * .95) - 1)]) if latencies else None,
                "positive_feedback": sum(m.feedback == 1 for m in metrics), "negative_feedback": sum(m.feedback == -1 for m in metrics),
                "window": "Kullanıcının son 1000 sorgusu; soru/cevap metinleri saklanmaz."}

    @app.get("/api/system")
    def system(user=Depends(get_user)):
        return {"model": app.state.model.status(), "qdrant_ready": app.state.vectors.status(), "chat_model": config.chat_model,
                "embedding_model": config.embed_model, "database": "SQL Server" if config.database_url.startswith("mssql") else "SQLite",
                "vector_mode": "Qdrant sunucu" if config.qdrant_url else "Qdrant gömülü", "max_upload_mb": config.max_upload_mb,
                "worker_enabled": config.worker_enabled, "version": "0.1.0", "rag_revision": RAG_REVISION}

    app.mount("/assets", StaticFiles(directory=ROOT / "dist" / "assets"), name="assets")

    @app.get("/")
    def home():
        return FileResponse(ROOT / "dist" / "index.html")

    return app


app = create_app()

import time
import uuid
from sqlalchemy import create_engine, event, ForeignKey, String, Unicode, UnicodeText, Float, Integer, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def uid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(16), default="admin")


class LoginSession(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[float] = mapped_column(Float)


class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(Unicode(100))
    __table_args__ = (UniqueConstraint("owner_id", "name"),)


class Membership(Base):
    __tablename__ = "memberships"
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"), index=True)
    filename: Mapped[str] = mapped_column(Unicode(255))
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    error: Mapped[str] = mapped_column(Unicode(500), default="")
    warning: Mapped[str] = mapped_column(Unicode(500), default="")
    embedding_model: Mapped[str] = mapped_column(String(160), default="")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    __table_args__ = (UniqueConstraint("subject_id", "sha256"),)


class Chunk(Base):
    __tablename__ = "chunks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"), index=True)
    location: Mapped[str] = mapped_column(Unicode(100))
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(UnicodeText)


class QueryMetric(Base):
    __tablename__ = "query_metrics"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    subject_id: Mapped[str | None] = mapped_column(ForeignKey("subjects.id"), index=True, nullable=True)
    mode: Mapped[str] = mapped_column(String(16))
    outcome: Mapped[str] = mapped_column(String(24))
    elapsed_ms: Mapped[float] = mapped_column(Float)
    feedback: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(60))
    target_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


def make_database(settings):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    kwargs = {"connect_args": {"check_same_thread": False, "timeout": 30}} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, pool_pre_ping=True, **kwargs)
    if settings.database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def sqlite_config(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")
    Base.metadata.create_all(engine)
    from .migrations import migrate_general_metrics
    try:
        migrate_general_metrics(engine, settings.data_dir)
    except Exception:
        engine.dispose()
        raise
    return engine, sessionmaker(engine, expire_on_commit=False)

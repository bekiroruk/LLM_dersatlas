from pathlib import Path
import re
from urllib.parse import urlparse
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _project_path(value: Path) -> Path:
    """Göreli çalışma yollarını terminalin açık olduğu klasörden ayırır."""
    value = Path(value).expanduser()
    return value.resolve() if value.is_absolute() else (PROJECT_ROOT / value).resolve()


def _project_sqlite_url(value: str) -> str:
    """Göreli SQLite adresini her zaman uygulama köküne sabitler."""
    prefix = "sqlite:///"
    if not value.startswith(prefix):
        return value

    database = value[len(prefix):]
    if database in {"", ":memory:"}:
        return value

    # sqlite:////tmp/x.db ve sqlite:///C:/x.db zaten mutlaktır.
    if database.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", database):
        return value

    resolved = _project_path(Path(database))
    return prefix + resolved.as_posix()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        extra="ignore",
    )
    data_dir: Path = PROJECT_ROOT / "data"
    database_url: str = "sqlite:///./data/dersatlas.db"
    ollama_url: str = "http://127.0.0.1:11434"
    chat_model: str = "qwen3:4b"
    embed_model: str = "bge-m3"
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    cookie_secure: bool = False
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    session_hours: int = 8
    max_upload_mb: int = 20
    max_pages: int = 300
    chunk_chars: int = 1600
    chunk_overlap: int = 220
    dense_threshold: float = 0.35
    top_k: int = 6
    ollama_timeout: int = 180
    agent_max_rounds: int = 3
    worker_enabled: bool = True

    @model_validator(mode="after")
    def validate_settings(self):
        self.data_dir = _project_path(self.data_dir)
        self.database_url = _project_sqlite_url(self.database_url)
        if not 0 <= self.chunk_overlap < self.chunk_chars or self.chunk_chars < 300:
            raise ValueError("Parça boyutu en az 300; örtüşme parça boyutundan küçük olmalı.")
        if not 1 <= self.top_k <= 10 or not 1 <= self.agent_max_rounds <= 4:
            raise ValueError("top_k 1-10 ve agent_max_rounds 1-4 aralığında olmalı.")
        if self.max_upload_mb < 1 or self.max_pages < 1 or self.session_hours < 1:
            raise ValueError("Boyut, sayfa ve oturum sınırları pozitif olmalı.")
        if urlparse(self.ollama_url).scheme not in {"http", "https"}:
            raise ValueError("Geçersiz Ollama URL.")
        if any(":cloud" in m or m.endswith("-cloud") for m in (self.chat_model, self.embed_model)):
            raise ValueError("Bulut model etiketleri bu on-premise uygulamada kapalıdır.")
        return self

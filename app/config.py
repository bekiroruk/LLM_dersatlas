from pathlib import Path
from urllib.parse import urlparse
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    data_dir: Path = Path("data")
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

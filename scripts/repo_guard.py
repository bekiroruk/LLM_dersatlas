"""Inspect the Git index without changing it or printing secret values."""

from __future__ import annotations

import argparse
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

MAX_BYTES = 5 * 1024 * 1024
PRIVATE_DIRS = {
    ".venv", "venv", "env", "data", "output", "uploads", "private",
    "notes", "notlar", "models", "weights", "logs", "backups", "backup",
    "__pycache__", ".pytest_cache", ".idea", ".vscode", "node_modules",
}
PRIVATE_SUFFIXES = {
    ".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".xls", ".csv", ".db",
    ".sqlite", ".sqlite3", ".log", ".pem", ".key", ".p12", ".pfx",
    ".safetensors", ".gguf", ".pt", ".pth", ".onnx", ".bin",
    ".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".pyc",
}
PUBLIC_ENV_NAMES = {".env.example", ".env.template"}
SECRET_PATTERNS = [
    ("GitHub token biçimi", re.compile(
        rb"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})\b"
    )),
    ("API anahtarı biçimi", re.compile(
        rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"
    )),
    ("AWS erişim anahtarı biçimi", re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("Özel anahtar", re.compile(
        rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
    )),
]


class GuardError(RuntimeError):
    pass


def check_path(path: str) -> str | None:
    normalized = path.replace("\\", "/")
    item = PurePosixPath(normalized)
    parts = [part.casefold() for part in item.parts]
    if item.is_absolute() or ".." in parts or any(ord(c) < 32 for c in path):
        return "Geçersiz veya kontrol karakteri içeren dosya yolu"
    if any(part in PRIVATE_DIRS for part in parts[:-1]):
        return "Kişisel veri, bağımlılık veya yedek klasörü"
    name = item.name.casefold()
    if (name == ".env" or name.startswith(".env.")) and name not in PUBLIC_ENV_NAMES:
        return "Yerel ortam ayarı"
    if name.startswith(("id_rsa", "id_ed25519", "credentials.", "secrets.")):
        return "Kimlik bilgisi dosyası"
    if item.suffix.casefold() in PRIVATE_SUFFIXES:
        return "Kişisel materyal, veri, model, arşiv veya anahtar dosyası"
    if re.search(r"\.(?:db|sqlite3?)-(?:wal|shm|journal)$", name):
        return "Veritabanı yan dosyası"
    if re.search(r"(?:\.bak|\.backup|\.old$|\.orig$|\.save$|^backup_|_backup(?:[._-]|\d|$))", name):
        return "Yerel yedek dosyası"
    return None


def check_blob(path: str, content: bytes, mode: str = "100644", stage: str = "0") -> list[str]:
    issues = []
    reason = check_path(path)
    if reason:
        issues.append(reason)
    if mode not in {"100644", "100755"}:
        issues.append("Sembolik bağlantı veya alt depo otomatik paylaşılmaz")
    if stage != "0":
        issues.append("Çözümlenmemiş Git birleştirmesi")
    if len(content) > MAX_BYTES:
        issues.append("Dosya 5 MiB paylaşım sınırını aşıyor")
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(content):
            issues.append(label)
    return issues


def run_git(root: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, check=False,
        )
    except OSError as exc:
        raise GuardError("Git çalıştırılamadı; Git kurulumunu kontrol et.") from exc
    if result.returncode:
        raise GuardError("Git denetimi başarısız; depo kökünü ve Git durumunu kontrol et.")
    return result.stdout


def check_repository(root: Path) -> tuple[int, list[tuple[str, str]]]:
    root = root.resolve()
    actual = Path(os.fsdecode(run_git(root, "rev-parse", "--show-toplevel")).strip()).resolve()
    if actual != root:
        raise GuardError("Araç uygulama kökündeki Git deposunda çalıştırılmalı.")
    records = run_git(root, "ls-files", "--stage", "-z").split(b"\0")
    findings = []
    count = 0
    for record in records:
        if not record:
            continue
        header, path_bytes = record.split(b"\t", 1)
        mode, object_id, stage = (part.decode("ascii") for part in header.split())
        path = os.fsdecode(path_bytes)
        count += 1
        size = int(run_git(root, "cat-file", "-s", object_id))
        if size > MAX_BYTES:
            findings.append((path, "Dosya 5 MiB paylaşım sınırını aşıyor"))
            content = b""
        else:
            content = run_git(root, "cat-file", "-p", object_id)
        findings.extend((path, reason) for reason in check_blob(path, content, mode, stage))
    return count, findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        count, findings = check_repository(args.root)
    except (GuardError, ValueError) as exc:
        print(str(exc))
        return 2
    if not count:
        print("Git indeksinde denetlenecek dosya yok; bu bir başarılı yayın kontrolü sayılmaz.")
        return 2
    for path, reason in findings:
        print(f"ENGELLENDİ {path!r}: {reason}")
    if findings:
        print("Secret değerleri gösterilmedi. Sorunları giderip tekrar kontrol et.")
        return 1
    print(f"Paylaşım kontrolü geçti: {count} izlenen dosya. Bu kontrol eksiksiz bir secret/PII taraması değildir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

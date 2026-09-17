"""Bağımlılıkları, donanımı ve yerel model uç noktasını içerik göndermeden kontrol eder."""
import importlib.util
import json
import platform
import shutil
import subprocess
import urllib.request

print("Python:", platform.python_version(), "Sistem:", platform.system(), platform.machine())
for name in ["fastapi", "uvicorn", "sqlalchemy", "pydantic_settings", "qdrant_client", "httpx", "pypdf", "docx", "multipart"]:
    print(name + ":", "hazır" if importlib.util.find_spec(name) else "eksik")
if shutil.which("nvidia-smi"):
    subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], check=False, timeout=15)
try:
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as response:
        print("Ollama yerel modeller:", [m["name"] for m in json.load(response).get("models", [])])
except Exception:
    print("Ollama varsayılan yerel adresine erişilemiyor. Özel adres ayarı bu betikte okunmaz.")

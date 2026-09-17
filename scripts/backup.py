"""Durdurulmuş yerel kurulumun data dizinini ZIP'e yedekler; üzerine yazmaz."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("--data", default="data")
parser.add_argument("--destination", default="backups")
parser.add_argument("--app-stopped", action="store_true", help="Uygulamayı gerçekten durdurduktan sonra belirt.")
args = parser.parse_args()
if not args.app_stopped:
    raise SystemExit("Önce uygulamayı durdur. Ardından --app-stopped ekle; canlı dosya kopyası tutarlı yedek değildir.")
source = Path(args.data).resolve()
if not source.is_dir() or not (source / "dersatlas.db").is_file():
    raise SystemExit("Varsayılan yerel SQLite data dizini bulunamadı. SQL Server/Docker için rehbere bak.")
destination = Path(args.destination).resolve()
if destination == source or source in destination.parents:
    raise SystemExit("Yedek klasörü data dizininin dışında olmalı.")
destination.mkdir(parents=True, exist_ok=True)
target = destination / ("dersatlas_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".zip")
with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED) as archive:
    for file in sorted(source.rglob("*")):
        if file.is_symlink():
            raise SystemExit("Sembolik bağlantı bulundu; güvenli yedek için kontrol gerekli.")
        if file.is_file():
            archive.write(file, Path("data") / file.relative_to(source))
print("Yedek oluşturuldu:", target)
print("Uyarı: bu ZIP şifrelenmemiştir; özel not ve hesap verisi içerir. Erişimini sınırla.")

"""Preview first; stage/commit/push only with explicit flags and confirmation."""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.repo_guard import GuardError, check_path, check_repository, run_git

EXPECTED_REMOTES = {
    "https://github.com/bekiroruk/llm_dersatlas.git",
    "https://github.com/bekiroruk/llm_dersatlas",
    "git@github.com:bekiroruk/llm_dersatlas.git",
}
PUBLIC_DIRS = {"app", "dist", "tests", "samples", "docs", "scripts", ".github"}
PUBLIC_FILES = {
    "readme.md", "changelog.md", "contributing.md", "security.md",
    ".gitignore", ".gitattributes", ".dockerignore", ".env.example", ".env.template",
    "pyproject.toml", "requirements.txt", "requirements-dev.txt", "dockerfile",
    "compose.yaml", "compose.gpu.yaml", "compose.offline.yaml",
}


def publishable(path: str) -> bool:
    item = PurePosixPath(path.replace("\\", "/"))
    if check_path(path):
        return False
    return item.parts[0].casefold() in PUBLIC_DIRS or str(item).casefold() in PUBLIC_FILES


def candidate_paths(root: Path) -> tuple[list[str], list[str]]:
    raw = (
        run_git(root, "diff", "--name-only", "--no-renames", "-z")
        + run_git(root, "ls-files", "--others", "--exclude-standard", "-z")
    )
    paths = sorted({part.decode("utf-8", "surrogateescape") for part in raw.split(b"\0") if part})
    return (
        [path for path in paths if publishable(path)],
        [path for path in paths if not publishable(path)],
    )


def execute(*args: str) -> None:
    if subprocess.run(list(args), cwd=ROOT, check=False).returncode:
        raise GuardError("Komut başarısız; otomatik reset/merge/force-push yapılmadı.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", required=True, help="Açıklayıcı commit mesajı")
    parser.add_argument("--apply", action="store_true", help="İncelenen değişiklikleri onaydan sonra stage/commit et")
    parser.add_argument("--push", action="store_true", help="Başarılı commit sonrası origin/main'e gönder")
    args = parser.parse_args()
    if len(args.message.strip()) < 8 or "\n" in args.message:
        parser.error("Commit mesajı en az 8 karakter olmalı ve tek satır içermeli.")
    if args.push and not args.apply:
        parser.error("--push ancak --apply ile kullanılabilir.")
    try:
        count, issues = check_repository(ROOT)
        if issues:
            for path, reason in issues:
                print(f"ENGELLENDİ {path!r}: {reason}")
            raise GuardError("Mevcut Git indeksinde paylaşım sorunu var.")
        branch = run_git(ROOT, "symbolic-ref", "--quiet", "--short", "HEAD").decode().strip()
        if branch != "main":
            raise GuardError("Bu gün sonu aracı yalnızca main dalında çalışır.")
        remote = run_git(ROOT, "remote", "get-url", "--push", "origin").decode().strip().casefold()
        if remote not in EXPECTED_REMOTES:
            raise GuardError("origin beklenen DersAtlas reposu değil; uzak adresi kontrol et.")
        selected, omitted = candidate_paths(ROOT)
        print("Paylaşılacak aday dosyalar:")
        for path in selected:
            print(f"  {path!r}")
        if omitted:
            print(f"İzin listesi dışında kalan {len(omitted)} dosya paylaşılmayacak.")
        if not selected:
            print("Yeni değişiklik yok; boş commit veya otomatik push yapılmadı.")
            return 0
        if not args.apply:
            print("ÖNİZLEME: stage, commit ve push yapılmadı.")
            print("Dosyaları inceledikten sonra --apply ve istenirse --push kullan.")
            return 0
        if not (ROOT / "app" / "main.py").exists():
            raise GuardError("Güncel uygulama kodunu önce aktarmalısın; bu depo henüz uygulamayı içermiyor.")
        if run_git(ROOT, "diff", "--cached", "--name-only"):
            raise GuardError("Önceden stage edilmiş değişiklikler var; önce onları incele.")
        for path in selected:
            if (ROOT / path).is_symlink():
                raise GuardError("Sembolik bağlantı otomatik paylaşılmaz.")
        if input("Bu dosyaları test edip commit yapmak için EVET yaz: ").strip() != "EVET":
            print("İptal edildi; stage/commit/push yapılmadı.")
            return 0
        execute("git", "fetch", "origin", "main")
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", "origin/main", "HEAD"],
            cwd=ROOT, check=False,
        )
        if ancestor.returncode:
            raise GuardError("Uzak main değişmiş veya ilk aktarım eksik; önce geçmişleri güvenli birleştir.")
        execute("git", "add", "-A", "--", *selected)
        count, issues = check_repository(ROOT)
        if issues:
            for path, reason in issues:
                print(f"ENGELLENDİ {path!r}: {reason}")
            raise GuardError("Paylaşım kontrolü başarısız; commit/push yapılmadı.")
        execute(sys.executable, "-m", "compileall", "-q", "app", "scripts", "tests")
        execute(sys.executable, str(ROOT / "scripts" / "run_tests.py"))
        changed = subprocess.run(["git", "diff", "--quiet", "--", *selected], cwd=ROOT, check=False)
        if changed.returncode:
            raise GuardError("Kontroller sırasında dosyalar değişti; commit/push yapılmadı.")
        if not run_git(ROOT, "diff", "--cached", "--name-only"):
            print("Stage edilmiş fark yok; boş commit oluşturulmadı.")
            return 0
        execute("git", "commit", "-m", args.message.strip())
        print(f"Commit oluşturuldu. Paylaşım kontrolündeki dosya: {count}.")
        if args.push:
            execute("git", "push", "origin", "HEAD:main")
            print("GitHub main güncellendi.")
        else:
            print("Push istenmedi; commit yalnızca yerelde.")
        return 0
    except (GuardError, OSError, EOFError) as exc:
        print(str(exc), file=sys.stderr)
        print("Dosyalar korunur. Stage veya commit yapıldıysa geri alınmadı; git status ile incele.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

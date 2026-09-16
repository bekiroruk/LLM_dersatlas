"""Run discovered tests; skips and an empty test suite are not a success."""

from pathlib import Path
import sys
import unittest


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    suite = unittest.defaultTestLoader.discover(str(root / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.testsRun == 0:
        print("Hiç test çalıştırılmadı; kontrol başarısız.", file=sys.stderr)
        return 1
    if result.skipped:
        print(
            f"{len(result.skipped)} test atlandı; eksik doğrulama başarılı sayılmaz.",
            file=sys.stderr,
        )
        return 1
    if not result.wasSuccessful():
        return 1
    scope = "Uygulama + depo testleri" if (root / "app" / "main.py").exists() else "Yalnızca depo araçları; uygulama kodu henüz yok"
    print(f"Doğrulama kapsamı: {scope}. Çalışan test: {result.testsRun}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

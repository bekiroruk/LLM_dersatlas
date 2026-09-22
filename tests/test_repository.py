import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.gun_sonu import publishable
from scripts.repo_guard import GuardError, MAX_BYTES, check_blob, check_path, check_repository


class PathGuardTests(unittest.TestCase):
    def test_public_paths(self):
        for path in [
            "app/rag.py", "app/providers.py", "scripts/backup.py",
            ".env.example", ".env.template", "docs/ARCHITECTURE.md",
            "dist/assets/app.js", ".github/workflows/ci.yml",
        ]:
            with self.subTest(path=path):
                self.assertIsNone(check_path(path))

    def test_private_directories(self):
        for path in ["data/originals/id", "app/data/notes.md", "backups/rag.py", ".venv/Scripts/python.exe"]:
            with self.subTest(path=path):
                self.assertIsNotNone(check_path(path))

    def test_env_variants(self):
        for path in [".env", ".env.local", ".env.production", "app/.ENV.local"]:
            with self.subTest(path=path):
                self.assertIsNotNone(check_path(path))

    def test_personal_material(self):
        for path in ["ders.pdf", "notes.docx", "data.db", "vectors.bin", "model.gguf", "export.csv", "backup.zip"]:
            with self.subTest(path=path):
                self.assertIsNotNone(check_path(path))

    def test_database_sidecars(self):
        for path in ["dersatlas.db-wal", "dersatlas.sqlite3-shm", "index.sqlite-journal"]:
            with self.subTest(path=path):
                self.assertIsNotNone(check_path(path))

    def test_timestamped_backups(self):
        for path in ["app/rag.py.bak_20260916", "app/rag_backup_1.py", "backup_rag.py", "rag.py.orig"]:
            with self.subTest(path=path):
                self.assertIsNotNone(check_path(path))

    def test_invalid_paths(self):
        for path in ["../secret.txt", "/secret.txt", "docs/line\nbreak.md"]:
            with self.subTest(path=path):
                self.assertIsNotNone(check_path(path))

    def test_allowlist(self):
        self.assertTrue(publishable("app/rag.py"))
        self.assertTrue(publishable("dist/assets/app.js"))
        self.assertTrue(publishable("pyproject.toml"))
        self.assertFalse(publishable("personal.txt"))
        self.assertFalse(publishable("app/rag.py.bak_1"))
        self.assertFalse(publishable("samples/my_notes.pdf"))

    def test_dockerignore_is_publishable(self):
        self.assertTrue(publishable(".dockerignore"))
        self.assertFalse(publishable(".dockerignore.bak"))
        self.assertFalse(publishable("MANIFEST.sha256"))


class BlobGuardTests(unittest.TestCase):
    def test_known_token_formats(self):
        values = [
            "gh" + "p_" + "a" * 36,
            "github_" + "pat_" + "a" * 50,
            "sk" + "-" + "b" * 24,
            "AK" + "IA" + "A" * 16,
        ]
        for value in values:
            with self.subTest(kind=value[:3]):
                self.assertTrue(check_blob("app/config.py", value.encode()))

    def test_private_key(self):
        value = "-----BEGIN " + "PRIVATE KEY-----"
        self.assertTrue(check_blob("docs/example.md", value.encode()))

    def test_no_secret_echo(self):
        value = ("gh" + "p_" + "c" * 36).encode()
        reasons = check_blob("app/config.py", value)
        self.assertTrue(reasons)
        self.assertNotIn(value.decode(), repr(reasons))

    def test_plain_source(self):
        self.assertEqual(check_blob("app/rag.py", b"def test():\n    return False\n"), [])

    def test_symlink_and_submodule_modes(self):
        for mode in ["120000", "160000"]:
            with self.subTest(mode=mode):
                self.assertTrue(check_blob("docs/reference.md", b"target", mode=mode))

    def test_unmerged_stage(self):
        self.assertTrue(check_blob("README.md", b"text", stage="2"))

    def test_large_file(self):
        self.assertTrue(check_blob("dist/assets/image.png", b"x" * (MAX_BYTES + 1)))


class IndexGuardTests(unittest.TestCase):
    def test_reads_staged_content_not_worktree(self):
        with tempfile.TemporaryDirectory(prefix="dersatlas-index-test-") as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            path = root / "example.py"
            path.write_text("gh" + "p_" + "d" * 36, encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "--", "example.py"], check=True)
            path.write_text("print('safe worktree')", encoding="utf-8")
            count, issues = check_repository(root)
            self.assertEqual(count, 1)
            self.assertTrue(issues)
            self.assertEqual(issues[0][0], "example.py")

    def test_safe_index(self):
        with tempfile.TemporaryDirectory(prefix="dersatlas-index-test-") as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            (root / "README.md").write_text("# Synthetic test fixture\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "--", "README.md"], check=True)
            self.assertEqual(check_repository(root), (1, []))

    def test_rejects_parent_repository(self):
        with tempfile.TemporaryDirectory(prefix="dersatlas-root-test-") as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            child = root / "nested"
            child.mkdir()
            with self.assertRaises(GuardError):
                check_repository(child)

    def test_empty_index_has_no_false_claim(self):
        with tempfile.TemporaryDirectory(prefix="dersatlas-index-test-") as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            self.assertEqual(check_repository(root), (0, []))


class RunnerTests(unittest.TestCase):
    def test_skips_make_runner_fail(self):
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("repo_test_runner", root / "scripts" / "run_tests.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        from unittest.mock import patch
        result = unittest.TestResult()
        result.testsRun = 1
        result.skipped = [(None, "synthetic skip")]
        with patch.object(runner.unittest.defaultTestLoader, "discover", return_value=unittest.TestSuite()):
            with patch.object(runner.unittest.TextTestRunner, "run", return_value=result):
                self.assertEqual(runner.main(), 1)

    def test_zero_tests_make_runner_fail(self):
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("repo_test_runner", root / "scripts" / "run_tests.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        from unittest.mock import patch
        result = unittest.TestResult()
        with patch.object(runner.unittest.defaultTestLoader, "discover", return_value=unittest.TestSuite()):
            with patch.object(runner.unittest.TextTestRunner, "run", return_value=result):
                self.assertEqual(runner.main(), 1)


class WindowsLauncherTests(unittest.TestCase):
    def test_launcher_is_project_scoped_and_revision_checked(self):
        root = Path(__file__).resolve().parents[1]
        start = (root / "scripts" / "start.ps1").read_text(encoding="utf-8")
        stop = (root / "scripts" / "stop.ps1").read_text(encoding="utf-8")

        for script in (start, stop):
            self.assertIn('Resolve-Path (Join-Path $PSScriptRoot "..")', script)
            self.assertIn("Get-CimInstance Win32_Process", script)
            self.assertIn('uvicorn\\s+app\\.main:app', script)
            self.assertNotIn("Get-Process python", script)
            self.assertNotIn("taskkill /im python", script.casefold())

        self.assertIn("Set-Location $projectRoot", start)
        self.assertIn('"-m", "uvicorn", "app.main:app"', start)
        self.assertIn("/health", start)
        self.assertIn("rag_revision", start)
        self.assertIn("Start-Process", start)
        self.assertIn("$process.ExitCode", start)
        self.assertIn("$stdoutLog", start)
        self.assertIn("$stderrLog", start)
        self.assertIn("Remove-Item $pidFile", stop)


if __name__ == "__main__":
    unittest.main()

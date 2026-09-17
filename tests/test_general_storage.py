"""Gerçek SQLite şema geçişi ve gerçek Qdrant çok-ders filtresi testleri."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import MetaData, create_engine, inspect, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db import Base, User, Subject, Document, Chunk, QueryMetric, make_database
from app.migrations import migrate_general_metrics
from app.providers import VectorStore
from app.rag import _same_term, _sources_are_relevant, normalize_question


class MetricsMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.config = Settings(_env_file=None, data_dir=self.folder,
                               database_url="sqlite:///" + str(self.folder / "old.db"),
                               worker_enabled=False)
        self.engine = create_engine(self.config.database_url)
        metadata = MetaData()
        for table in Base.metadata.sorted_tables:
            table.to_metadata(metadata)
        metadata.tables["query_metrics"].c.subject_id.nullable = False
        metadata.create_all(self.engine)
        with sessionmaker(self.engine)() as db:
            user = User(username="migration-user", password_hash="test-only-hash")
            db.add(user); db.flush()
            subject = Subject(owner_id=user.id, name="Tarih")
            db.add(subject); db.flush()
            doc = Document(subject_id=subject.id, filename="test.txt", sha256="0" * 64,
                           status="ready", embedding_model=self.config.embed_model, chunk_count=1)
            db.add(doc); db.flush()
            chunk = Chunk(document_id=doc.id, subject_id=subject.id, location="Metin blok 1",
                          ordinal=0, text="Özel test notu; geçişte aynen korunur.")
            metric = QueryMetric(user_id=user.id, subject_id=subject.id, mode="rag",
                                 outcome="answered", elapsed_ms=123.5, feedback=-1, created_at=1000.0)
            db.add_all([chunk, metric]); db.commit()
            self.user_id, self.subject_id, self.doc_id, self.chunk_id, self.metric_id = user.id, subject.id, doc.id, chunk.id, metric.id

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def is_nullable(self):
        return next(c["nullable"] for c in inspect(self.engine).get_columns("query_metrics")
                    if c["name"] == "subject_id")

    def test_legacy_migration_keeps_rows_foreign_keys_indexes_and_triggers(self):
        with self.engine.begin() as db:
            db.exec_driver_sql("CREATE INDEX custom_metric_outcome ON query_metrics(outcome)")
            db.exec_driver_sql("CREATE TABLE metric_feedback_log(value INTEGER)")
            db.exec_driver_sql("CREATE TRIGGER metric_feedback_trigger AFTER UPDATE OF feedback ON query_metrics BEGIN INSERT INTO metric_feedback_log VALUES(new.feedback); END")
        migrate_general_metrics(self.engine, self.folder)
        self.assertTrue(self.is_nullable())
        with sessionmaker(self.engine)() as db:
            metric = db.get(QueryMetric, self.metric_id)
            self.assertEqual((metric.subject_id, metric.feedback, metric.elapsed_ms, metric.created_at),
                             (self.subject_id, -1, 123.5, 1000.0))
            self.assertEqual(db.get(Chunk, self.chunk_id).text, "Özel test notu; geçişte aynen korunur.")
            self.assertEqual(db.get(Document, self.doc_id).chunk_count, 1)
            self.assertEqual(db.get(Subject, self.subject_id).name, "Tarih")
            db.add(QueryMetric(user_id=self.user_id, subject_id=None, mode="agent",
                               outcome="insufficient", elapsed_ms=50))
            metric.feedback = 1
            db.commit()
        with self.engine.connect() as db:
            self.assertEqual(db.exec_driver_sql("SELECT value FROM metric_feedback_log").scalar_one(), 1)
            self.assertIsNone(db.exec_driver_sql("PRAGMA foreign_key_check").first())
        self.assertIn("custom_metric_outcome", {i["name"] for i in inspect(self.engine).get_indexes("query_metrics")})
        backups = list((self.folder / "schema_backups").glob("*.db"))
        self.assertEqual(len(backups), 1)
        with sqlite3.connect(str(backups[0])) as db:
            self.assertEqual(db.execute("SELECT id, feedback FROM query_metrics").fetchall(), [(self.metric_id, -1)])
            column = next(c for c in db.execute("PRAGMA table_info(query_metrics)") if c[1] == "subject_id")
            self.assertEqual(column[3], 1)

    def test_existing_database_startup_migrates_once_and_keeps_old_id(self):
        self.engine.dispose()
        engine, sessions = make_database(self.config)
        try:
            with sessions() as db:
                self.assertIsNotNone(db.get(QueryMetric, self.metric_id))
            migrate_general_metrics(engine, self.folder)
            self.assertEqual(len(list((self.folder / "schema_backups").glob("*.db"))), 1)
        finally:
            engine.dispose()
        # Yeni bir süreç/bağlantı havuzuyla tekrar başlangıç da idempotenttir.
        engine, _ = make_database(self.config)
        engine.dispose()
        self.assertEqual(len(list((self.folder / "schema_backups").glob("*.db"))), 1)

    def test_backup_failure_does_not_change_old_table(self):
        with patch("app.migrations._sqlite_backup", side_effect=OSError("Test: disk dolu")):
            with self.assertRaises(OSError):
                migrate_general_metrics(self.engine, self.folder)
        self.assertFalse(self.is_nullable())
        with sessionmaker(self.engine)() as db:
            self.assertEqual(db.get(QueryMetric, self.metric_id).feedback, -1)

    def test_failure_after_drop_rolls_back_whole_migration(self):
        execute = Connection.exec_driver_sql

        def fail_rename(connection, statement, *args, **kwargs):
            if statement.startswith("ALTER TABLE query_metrics_general_v1"):
                raise RuntimeError("Test: kesilen geçiş")
            return execute(connection, statement, *args, **kwargs)

        with patch.object(Connection, "exec_driver_sql", new=fail_rename):
            with self.assertRaisesRegex(RuntimeError, "kesilen"):
                migrate_general_metrics(self.engine, self.folder)
        self.assertFalse(self.is_nullable())
        self.assertNotIn("query_metrics_general_v1", inspect(self.engine).get_table_names())
        with sessionmaker(self.engine)() as db:
            self.assertEqual(db.get(QueryMetric, self.metric_id).feedback, -1)
            self.assertEqual(db.get(Chunk, self.chunk_id).document_id, self.doc_id)

    def test_unknown_extra_column_stops_without_data_changes(self):
        with self.engine.begin() as db:
            db.exec_driver_sql("ALTER TABLE query_metrics ADD COLUMN custom_field TEXT")
        with self.assertRaisesRegex(RuntimeError, "Özelleştirilmiş"):
            migrate_general_metrics(self.engine, self.folder)
        self.assertFalse(self.is_nullable())
        self.assertFalse((self.folder / "schema_backups").exists())

    def test_incoming_foreign_key_stops_without_dropping_dependents(self):
        with self.engine.begin() as db:
            db.exec_driver_sql("CREATE TABLE metric_references(id TEXT REFERENCES query_metrics(id))")
            db.exec_driver_sql("INSERT INTO metric_references VALUES(?)", (self.metric_id,))
        with self.assertRaisesRegex(RuntimeError, "dış referans"):
            migrate_general_metrics(self.engine, self.folder)
        self.assertFalse(self.is_nullable())
        with self.engine.connect() as db:
            self.assertEqual(db.exec_driver_sql("SELECT id FROM metric_references").scalar_one(), self.metric_id)

    def test_new_database_has_nullable_metric_without_migration_backup(self):
        config = self.config.model_copy(update={"database_url": "sqlite:///" + str(self.folder / "new.db")})
        engine, _ = make_database(config)
        try:
            subject = next(c for c in inspect(engine).get_columns("query_metrics") if c["name"] == "subject_id")
            self.assertTrue(subject["nullable"])
            self.assertFalse((self.folder / "schema_backups").exists())
        finally:
            engine.dispose()


class MultiSubjectVectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = Settings(_env_file=None, data_dir=Path(self.temp.name), worker_enabled=False)
        self.store = VectorStore(self.settings)
        self.chunks = [
            Chunk(id="11111111-1111-4111-8111-111111111111", subject_id="tarih", document_id="doc-1"),
            Chunk(id="22222222-2222-4222-8222-222222222222", subject_id="cografya", document_id="doc-2"),
            Chunk(id="33333333-3333-4333-8333-333333333333", subject_id="private", document_id="doc-3"),
        ]
        self.store.upsert(self.settings.embed_model, self.chunks, [[1., 0., 0.]] * 3)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_union_of_authorized_subjects_never_returns_private_vector(self):
        results = self.store.search(self.settings.embed_model, ["tarih", "cografya"], [1., 0., 0.])
        self.assertEqual({key for key, _ in results}, {c.id for c in self.chunks[:2]})

    def test_single_subject_string_still_works(self):
        results = self.store.search(self.settings.embed_model, "tarih", [1., 0., 0.])
        self.assertEqual([key for key, _ in results], [self.chunks[0].id])

    def test_empty_scope_never_issues_unfiltered_search(self):
        with patch.object(self.store.client, "query_points", side_effect=AssertionError("Filtresiz çağrı")):
            self.assertEqual(self.store.search(self.settings.embed_model, [], [1., 0., 0.]), [])
            self.assertEqual(self.store.search(self.settings.embed_model, None, [1., 0., 0.]), [])


class PreviousQualityRegressionTests(unittest.TestCase):
    def test_fethedildi_does_not_match_fethiye(self):
        self.assertFalse(_same_term("fethedildi", "fethiye"))
        self.assertFalse(_sources_are_relevant(
            "İstanbul hangi tarihte ve hangi padişah döneminde fethedildi?",
            [{"text": "İstanbul turizm merkezidir. Fethiye yat turizmiyle bilinir."}]
        ))

    def test_kayser_aliases_normalize_to_same_question(self):
        self.assertEqual(normalize_question("kayseri rum"), normalize_question("kayser-i rum"))


if __name__ == "__main__":
    unittest.main()

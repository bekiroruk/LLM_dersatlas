"""Genel sorgular için yalnızca query_metrics.subject_id alanını nullable yapar.

SQLite geçişinden önce tutarlı, özel bir DB yedeği alınır. Dokümanlar ve
vektör koleksiyonları değiştirilmez. Özelleştirilmiş/harici şemada sessizce
veri kaybetmek yerine başlangıç durdurulur.
"""
import logging
import re
import sqlite3
import time
import uuid
from pathlib import Path

from sqlalchemy import inspect

logger = logging.getLogger(__name__)
EXPECTED_COLUMNS = {"id", "user_id", "subject_id", "mode", "outcome",
                    "elapsed_ms", "feedback", "created_at"}


def _sqlite_backup(engine, data_dir):
    folder = Path(data_dir) / "schema_backups"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / ("before_general_chat_" + uuid.uuid4().hex + ".db")
    target.touch(mode=0o600, exist_ok=False)
    deadline = time.monotonic() + 30

    def progress(status, remaining, total):
        if time.monotonic() > deadline:
            raise RuntimeError("Şema yedeği zaman aşımı; uygulamayı durdurup tekrar dene.")

    with engine.connect() as connection:
        destination = sqlite3.connect(str(target))
        try:
            connection.connection.driver_connection.backup(
                destination, pages=256, progress=progress
            )
        finally:
            destination.close()
    logger.warning("Genel sohbet şema geçişi öncesi özel DB yedeği: %s", target)
    return target


def migrate_general_metrics(engine, data_dir):
    inspector = inspect(engine)
    columns = inspector.get_columns("query_metrics")
    subject = next(column for column in columns if column["name"] == "subject_id")
    if subject["nullable"]:
        return  # Yeni kurulum veya daha önce tamamlanmış geçiş.
    if engine.dialect.name != "sqlite":
        raise RuntimeError(
            "Mevcut sunucu DB şeması geçiş gerektiriyor: yedek aldıktan sonra "
            "query_metrics.subject_id alanını nullable yap. "
            "SQL Server adımları docs/GENERAL_CHAT.md dosyasında."
        )
    if {column["name"] for column in columns} != EXPECTED_COLUMNS:
        raise RuntimeError("Özelleştirilmiş query_metrics şeması; otomatik geçiş yapılmadı.")
    for table in inspector.get_table_names():
        if any(fk["referred_table"] == "query_metrics"
               for fk in inspector.get_foreign_keys(table)):
            raise RuntimeError("query_metrics tablosuna dış referans var; manuel geçiş gerekir.")

    _sqlite_backup(engine, data_dir)
    with engine.connect() as connection:
        try:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            # Başka bir başlangıç geçişi tamamladıysa ikinci kez tablo değiştirme.
            info = connection.exec_driver_sql("PRAGMA table_info(query_metrics)").all()
            if not next(column[3] for column in info if column[1] == "subject_id"):
                connection.rollback()
                return
            if connection.exec_driver_sql(
                "SELECT 1 FROM sqlite_schema WHERE name='query_metrics_general_v1'"
            ).first():
                raise RuntimeError("Geçiş tablosu zaten var; otomatik üzerine yazma yapılmadı.")
            views = connection.exec_driver_sql(
                "SELECT sql FROM sqlite_schema WHERE type='view'"
            ).scalars()
            if any("query_metrics" in (sql or "").lower() for sql in views):
                raise RuntimeError("query_metrics görünümü var; manuel geçiş gerekir.")
            indexes_and_triggers = connection.exec_driver_sql(
                "SELECT sql FROM sqlite_schema WHERE tbl_name='query_metrics' "
                "AND type IN ('index', 'trigger') AND sql IS NOT NULL"
            ).scalars().all()
            original_sql = connection.exec_driver_sql(
                "SELECT sql FROM sqlite_schema WHERE type='table' AND name='query_metrics'"
            ).scalar_one()
            # Diğer sütun tiplerini, varsayılanları ve kısıtları aynen koru.
            new_sql, changed = re.subn(
                r'(^\s*"?subject_id"?\s+VARCHAR\(36\))\s+NOT NULL(?=\s*,)',
                r'\1', original_sql, flags=re.MULTILINE | re.IGNORECASE
            )
            new_sql, renamed = re.subn(
                r'^CREATE TABLE "?query_metrics"?\s*\(',
                'CREATE TABLE query_metrics_general_v1 (', new_sql, count=1,
                flags=re.IGNORECASE
            )
            if changed != 1 or renamed != 1:
                raise RuntimeError("Beklenmeyen tablo DDL biçimi; otomatik geçiş yapılmadı.")
            connection.exec_driver_sql(new_sql)
            connection.exec_driver_sql(
                "INSERT INTO query_metrics_general_v1 "
                "(id, user_id, subject_id, mode, outcome, elapsed_ms, feedback, created_at) "
                "SELECT id, user_id, subject_id, mode, outcome, elapsed_ms, feedback, created_at "
                "FROM query_metrics"
            )
            original_count = connection.exec_driver_sql(
                "SELECT COUNT(*) FROM query_metrics"
            ).scalar_one()
            copied_count = connection.exec_driver_sql(
                "SELECT COUNT(*) FROM query_metrics_general_v1"
            ).scalar_one()
            if original_count != copied_count or connection.exec_driver_sql(
                "PRAGMA foreign_key_check(query_metrics_general_v1)"
            ).first():
                raise RuntimeError("Geçiş veri kontrolü başarısız; işlem geri alınır.")
            connection.exec_driver_sql("DROP TABLE query_metrics")
            connection.exec_driver_sql(
                "ALTER TABLE query_metrics_general_v1 RENAME TO query_metrics"
            )
            for sql in indexes_and_triggers:
                connection.exec_driver_sql(sql)
            if connection.exec_driver_sql("PRAGMA foreign_key_check").first():
                raise RuntimeError("Geçiş foreign key kontrolü başarısız; işlem geri alınır.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise

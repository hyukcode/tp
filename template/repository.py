"""SQLite persistence. Every connection is committed/rolled back and closed."""
from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Protocol


class TemplateRepository(Protocol):
    def list(self) -> list[dict]: ...
    def save(self, id: str, revision: int, document: dict) -> int: ...
    def publish(self, id: str, revision: int, check: Callable[[dict], None]) -> int: ...
    def release(self, id: str, version: int) -> dict: ...


class SQLiteTemplateRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS drafts (
                    id TEXT PRIMARY KEY, revision INTEGER NOT NULL, body TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS releases (
                    id TEXT, version INTEGER, body TEXT NOT NULL, PRIMARY KEY(id, version)
                );
            ''')

    @contextmanager
    def transaction(self, *, write: bool = False):
        connection = sqlite3.connect(self.path)
        try:
            with connection:
                if write:
                    connection.execute('BEGIN IMMEDIATE')
                yield connection
        finally:
            connection.close()

    def list(self) -> list[dict]:
        with self.transaction() as db:
            versions = {}
            for id, version in db.execute('SELECT id, version FROM releases ORDER BY version DESC'):
                versions.setdefault(id, []).append(version)
            rows = db.execute('SELECT id, revision, body FROM drafts ORDER BY rowid DESC')
            return [dict(id=id, revision=revision, document=json.loads(body), versions=versions.get(id, []))
                    for id, revision, body in rows]

    def save(self, id: str, revision: int, document: dict) -> int:
        with self.transaction(write=True) as db:
            row = db.execute('SELECT revision FROM drafts WHERE id=?', (id,)).fetchone()
            if (row[0] if row else 0) != revision:
                raise ValueError('草稿已被修改，请重新加载')
            revision += 1
            body = json.dumps(document, ensure_ascii=False)
            db.execute('INSERT OR REPLACE INTO drafts VALUES (?, ?, ?)', (id, revision, body))
        return revision

    def publish(self, id: str, revision: int, check: Callable[[dict], None]) -> int:
        with self.transaction(write=True) as db:
            row = db.execute('SELECT revision, body FROM drafts WHERE id=?', (id,)).fetchone()
            if not row or row[0] != revision:
                raise ValueError('草稿不存在或已变更，请重新加载')
            check(json.loads(row[1]))
            version = db.execute(
                'SELECT COALESCE(MAX(version), 0)+1 FROM releases WHERE id=?', (id,)
            ).fetchone()[0]
            db.execute('INSERT INTO releases VALUES (?, ?, ?)', (id, version, row[1]))
        return version

    def release(self, id: str, version: int) -> dict:
        with self.transaction() as db:
            row = db.execute('SELECT body FROM releases WHERE id=? AND version=?', (id, version)).fetchone()
        if not row:
            raise ValueError('发布版本不存在')
        return json.loads(row[0])

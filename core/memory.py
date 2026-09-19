import json
import sqlite3
import time
from pathlib import Path
from threading import Lock


class MemoryStore:
    def __init__(self, db_path: str = "aria_memory.db") -> None:
        self.db_path = Path(db_path)
        self._lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'owner',
                    created_at INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources TEXT NOT NULL DEFAULT '',
                    created_at INTEGER NOT NULL
                )
                """
            )
            connection.commit()

    def add_memory(
        self,
        content: str,
        kind: str = "note",
        source: str = "owner",
    ) -> int:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO memories(kind, content, source, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (kind, content, source, int(time.time())),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def add_lesson(self, topic: str, content: str, sources: str = "") -> int:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO lessons(topic, content, sources, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (topic, content, sources, int(time.time())),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def search_lessons(self, query: str, limit: int = 5) -> list[dict]:
        q = f"%{query.strip()}%"
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, topic, content, sources, created_at
                FROM lessons
                WHERE topic LIKE ? OR content LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (q, q, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def search(self, query: str, limit: int = 10) -> list[dict]:
        words = [word for word in query.strip().split() if word]
        with self._lock, self._connect() as connection:
            if not words:
                rows = connection.execute(
                    """
                    SELECT id, kind, content, source, created_at
                    FROM memories
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            else:
                conditions = " OR ".join("content LIKE ?" for _ in words)
                params = [f"%{word}%" for word in words] + [limit]
                rows = connection.execute(
                    f"""
                    SELECT id, kind, content, source, created_at
                    FROM memories
                    WHERE {conditions}
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    params,
                ).fetchall()

        return [dict(row) for row in rows]

    def add_conversation(self, role: str, content: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations(role, content, created_at)
                VALUES (?, ?, ?)
                """,
                (role, content, int(time.time())),
            )
            connection.commit()

    def recent_conversation(self, limit: int = 12) -> list[dict]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content, created_at
                FROM conversations
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        items = [dict(row) for row in rows]
        items.reverse()
        return items

    def export_json(self) -> str:
        payload = {
            "memories": self.search("", 1000),
            "conversations": self.recent_conversation(1000),
            "lessons": self.search_lessons("", 200),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

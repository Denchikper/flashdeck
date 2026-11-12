# Flashdeck — подключение к SQLite и схема БД
# by Benovich · https://github.com/Denchikper/flashdeck

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS decks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS cards (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id     INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    word        TEXT NOT NULL,
    translation TEXT NOT NULL,
    example     TEXT NOT NULL DEFAULT '',
    image_path  TEXT NOT NULL DEFAULT '',
    level       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id     INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    started_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    total       INTEGER NOT NULL,
    correct     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS answers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    card_id     INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    is_correct  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cards_deck ON cards(deck_id);
CREATE INDEX IF NOT EXISTS idx_answers_card ON answers(card_id);
"""


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self.conn:
            return self.conn.execute(sql, params)

    def fetch_all(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    def fetch_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self.conn.execute(sql, params).fetchone()

    def close(self) -> None:
        self.conn.close()

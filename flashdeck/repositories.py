# Flashdeck — работа с таблицами БД
# by Benovich · https://github.com/Denchikper/flashdeck

from flashdeck.config import LEARNED_LEVEL, MAX_LEVEL
from flashdeck.database import Database
from flashdeck.models import Card, Deck, Session


class DeckRepository:
    def __init__(self, db: Database):
        self.db = db

    def all(self) -> list[Deck]:
        rows = self.db.fetch_all(
            """
            SELECT d.id, d.name, d.created_at,
                   COUNT(c.id) AS card_count,
                   COALESCE(SUM(c.level >= ?), 0) AS learned_count
            FROM decks d
            LEFT JOIN cards c ON c.deck_id = d.id
            GROUP BY d.id
            ORDER BY d.name COLLATE NOCASE
            """,
            (LEARNED_LEVEL,),
        )
        return [Deck(**dict(row)) for row in rows]

    def get(self, deck_id: int) -> Deck | None:
        row = self.db.fetch_one(
            "SELECT id, name, created_at FROM decks WHERE id = ?", (deck_id,)
        )
        return Deck(**dict(row)) if row else None

    def exists(self, name: str) -> bool:
        row = self.db.fetch_one("SELECT 1 FROM decks WHERE name = ?", (name,))
        return row is not None

    def create(self, name: str) -> int:
        cur = self.db.execute("INSERT INTO decks (name) VALUES (?)", (name,))
        return cur.lastrowid

    def rename(self, deck_id: int, name: str) -> None:
        self.db.execute("UPDATE decks SET name = ? WHERE id = ?", (name, deck_id))

    def delete(self, deck_id: int) -> None:
        self.db.execute("DELETE FROM decks WHERE id = ?", (deck_id,))


class CardRepository:
    def __init__(self, db: Database):
        self.db = db

    def by_deck(self, deck_id: int, search: str = "") -> list[Card]:
        rows = self.db.fetch_all(
            "SELECT * FROM cards WHERE deck_id = ? ORDER BY word COLLATE NOCASE",
            (deck_id,),
        )
        cards = [Card(**dict(row)) for row in rows]
        # LIKE в SQLite не понимает регистр кириллицы, поэтому фильтруем здесь
        query = search.strip().casefold()
        if query:
            cards = [c for c in cards
                     if query in c.word.casefold() or query in c.translation.casefold()]
        return cards

    def get(self, card_id: int) -> Card | None:
        row = self.db.fetch_one("SELECT * FROM cards WHERE id = ?", (card_id,))
        return Card(**dict(row)) if row else None

    def add(self, card: Card) -> int:
        cur = self.db.execute(
            """
            INSERT INTO cards (deck_id, word, translation, example, image_path, level)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (card.deck_id, card.word, card.translation,
             card.example, card.image_path, card.level),
        )
        return cur.lastrowid

    def update(self, card: Card) -> None:
        self.db.execute(
            """
            UPDATE cards
            SET word = ?, translation = ?, example = ?, image_path = ?, level = ?
            WHERE id = ?
            """,
            (card.word, card.translation, card.example,
             card.image_path, card.level, card.id),
        )

    def delete(self, card_id: int) -> None:
        self.db.execute("DELETE FROM cards WHERE id = ?", (card_id,))

    def change_level(self, card_id: int, delta: int) -> None:
        """Поднимает или опускает уровень карточки, не выходя за 0..MAX_LEVEL."""
        self.db.execute(
            "UPDATE cards SET level = MAX(0, MIN(?, level + ?)) WHERE id = ?",
            (MAX_LEVEL, delta, card_id),
        )

    def reset_levels(self, deck_id: int) -> None:
        self.db.execute("UPDATE cards SET level = 0 WHERE deck_id = ?", (deck_id,))

    def hardest(self, deck_id: int, limit: int = 10) -> list[tuple[Card, int, int]]:
        """Карточки с наибольшим числом ошибок: (карточка, ошибок, всего ответов)."""
        rows = self.db.fetch_all(
            """
            SELECT c.*,
                   SUM(a.is_correct = 0) AS mistakes,
                   COUNT(a.id) AS attempts
            FROM cards c
            JOIN answers a ON a.card_id = c.id
            WHERE c.deck_id = ?
            GROUP BY c.id
            HAVING mistakes > 0
            ORDER BY mistakes DESC, attempts ASC
            LIMIT ?
            """,
            (deck_id, limit),
        )
        result = []
        for row in rows:
            data = dict(row)
            mistakes = data.pop("mistakes")
            attempts = data.pop("attempts")
            result.append((Card(**data), mistakes, attempts))
        return result


class SessionRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, deck_id: int, answers: list[tuple[int, bool]]) -> int:
        """Сохраняет тренировку и все ответы одной транзакцией."""
        correct = sum(1 for _, ok in answers if ok)
        with self.db.conn:
            cur = self.db.conn.execute(
                "INSERT INTO sessions (deck_id, total, correct) VALUES (?, ?, ?)",
                (deck_id, len(answers), correct),
            )
            session_id = cur.lastrowid
            self.db.conn.executemany(
                "INSERT INTO answers (session_id, card_id, is_correct) VALUES (?, ?, ?)",
                [(session_id, card_id, int(ok)) for card_id, ok in answers],
            )
        return session_id

    def recent(self, deck_id: int, limit: int = 20) -> list[Session]:
        """Последние тренировки по колоде, от старых к новым — для графика."""
        rows = self.db.fetch_all(
            """
            SELECT * FROM (
                SELECT * FROM sessions WHERE deck_id = ?
                ORDER BY id DESC LIMIT ?
            ) ORDER BY id
            """,
            (deck_id, limit),
        )
        return [Session(**dict(row)) for row in rows]

    def summary(self, deck_id: int) -> tuple[int, int, int]:
        """Всего тренировок, всего ответов, верных ответов."""
        row = self.db.fetch_one(
            """
            SELECT COUNT(*), COALESCE(SUM(total), 0), COALESCE(SUM(correct), 0)
            FROM sessions WHERE deck_id = ?
            """,
            (deck_id,),
        )
        return tuple(row)

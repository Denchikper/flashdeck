# Flashdeck — тесты логики, БД и CSV
# by Benovich · https://github.com/Denchikper/flashdeck

import tempfile
import unittest
from pathlib import Path

from flashdeck import csv_io
from flashdeck.config import MAX_LEVEL
from flashdeck.database import Database
from flashdeck.models import Card
from flashdeck.repositories import Repositories
from flashdeck.trainer import (
    Direction, Mode, TrainingSession, TrainingSettings, normalize, pick_cards,
)


def make_cards() -> list[Card]:
    data = [("house", "дом, здание", 0), ("tree", "ёлка", 1), ("cat", "кошка", 5),
            ("dog", "собака", 4), ("sun", "солнце", 2), ("sea", "море", 0)]
    return [Card(i, 1, word, translation, level=level)
            for i, (word, translation, level) in enumerate(data, start=1)]


class TrainerTest(unittest.TestCase):
    def setUp(self):
        self.cards = make_cards()

    def test_normalize(self):
        self.assertEqual(normalize("  Ёлка   ЗЕЛЁНАЯ "), "елка зеленая")

    def test_weak_cards_first(self):
        picked = pick_cards(self.cards, TrainingSettings(size=3, shuffle=False))
        self.assertEqual([c.level for c in picked], [0, 0, 1])

    def test_only_unlearned(self):
        picked = pick_cards(self.cards, TrainingSettings(size=10, only_unlearned=True))
        self.assertNotIn("cat", [c.word for c in picked])
        self.assertNotIn("dog", [c.word for c in picked])

    def test_answer_variants(self):
        session = TrainingSession(self.cards, TrainingSettings(size=6))
        house, tree = self.cards[0], self.cards[1]
        self.assertTrue(session.is_right(house, "Здание"))
        self.assertTrue(session.is_right(house, "дом, здание"))
        self.assertTrue(session.is_right(tree, "елка"))
        self.assertFalse(session.is_right(house, "дом здание"))

    def test_reverse_direction(self):
        settings = TrainingSettings(size=6, direction=Direction.TRANSLATION_TO_WORD)
        session = TrainingSession(self.cards, settings)
        self.assertEqual(session.question(self.cards[2]), "кошка")
        self.assertTrue(session.is_right(self.cards[2], "CAT"))

    def test_score_and_retry(self):
        session = TrainingSession(self.cards[:3], TrainingSettings(size=3))
        session.answer(session.expected(session.current))
        session.answer("неверно")
        session.answer("")
        self.assertTrue(session.finished)
        self.assertEqual(session.correct_count, 1)
        self.assertEqual(session.accuracy, 33)
        self.assertEqual(session.retry_mistakes().total, 2)

    def test_choices(self):
        settings = TrainingSettings(size=6, mode=Mode.CHOICE)
        session = TrainingSession(self.cards, settings)
        options = session.choices(self.cards[0])
        self.assertEqual(len(set(options)), 4)
        self.assertIn("дом, здание", options)
        self.assertEqual(options, session.choices(self.cards[0]))


class RepositoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "test.db")
        self.repos = Repositories(self.db)
        self.deck_id = self.repos.decks.create("Тест")
        self.repos.cards.add_many(self.deck_id, make_cards())

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_deck_progress(self):
        deck = self.repos.decks.all()[0]
        self.assertEqual(deck.card_count, 6)
        self.assertEqual(deck.learned_count, 2)
        self.assertEqual(deck.progress, 33)

    def test_search_ignores_case(self):
        found = self.repos.cards.by_deck(self.deck_id, "КОШ")
        self.assertEqual([c.word for c in found], ["cat"])

    def test_level_bounds(self):
        card = self.repos.cards.by_deck(self.deck_id, "cat")[0]
        self.repos.cards.change_level(card.id, +1)
        self.assertEqual(self.repos.cards.get(card.id).level, MAX_LEVEL)
        for _ in range(10):
            self.repos.cards.change_level(card.id, -1)
        self.assertEqual(self.repos.cards.get(card.id).level, 0)

    def test_sessions_and_hardest(self):
        cards = self.repos.cards.by_deck(self.deck_id)
        self.repos.sessions.save(self.deck_id, [(cards[0].id, False), (cards[1].id, True)])
        self.repos.sessions.save(self.deck_id, [(cards[0].id, False)])
        self.assertEqual(self.repos.sessions.summary(self.deck_id), (2, 3, 1))
        hardest = self.repos.cards.hardest(self.deck_id)
        self.assertEqual(hardest[0][0].id, cards[0].id)
        self.assertEqual(hardest[0][1:], (2, 2))

    def test_delete_cascade(self):
        card = self.repos.cards.by_deck(self.deck_id)[0]
        self.repos.sessions.save(self.deck_id, [(card.id, True)])
        self.repos.decks.delete(self.deck_id)
        self.assertEqual(self.db.fetch_one("SELECT COUNT(*) FROM cards")[0], 0)
        self.assertEqual(self.db.fetch_one("SELECT COUNT(*) FROM answers")[0], 0)


class CsvTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_roundtrip(self):
        cards = make_cards()
        path = self.dir / "deck.csv"
        csv_io.write_cards(path, cards)
        loaded = csv_io.read_cards(path)
        self.assertEqual([(c.word, c.translation) for c in loaded],
                         [(c.word, c.translation) for c in cards])

    def test_comma_without_header(self):
        path = self.dir / "deck.csv"
        path.write_text('кот,cat\nпёс,dog,"Hello, dog"\n', encoding="utf-8")
        loaded = csv_io.read_cards(path)
        self.assertEqual(loaded[1].example, "Hello, dog")

    def test_bad_files(self):
        path = self.dir / "bad.csv"
        for content in ["", "только_слово\n"]:
            path.write_text(content, encoding="utf-8")
            with self.assertRaises(csv_io.CsvFormatError):
                csv_io.read_cards(path)

    def test_report(self):
        session = TrainingSession(make_cards()[:2], TrainingSettings(size=2))
        session.answer("дом")
        session.answer("нет")
        path = self.dir / "report.txt"
        csv_io.write_report(path, "Тест", session)
        text = path.read_text(encoding="utf-8")
        self.assertIn("1 из 2 (50%)", text)
        self.assertIn("(ответ: нет)", text)


if __name__ == "__main__":
    unittest.main()

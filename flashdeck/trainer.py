# Flashdeck — логика тренировки
# by Benovich · https://github.com/Denchikper/flashdeck

import random
from dataclasses import dataclass
from enum import Enum

from flashdeck.config import CHOICES_COUNT, LEARNED_LEVEL
from flashdeck.models import Card


class Direction(Enum):
    WORD_TO_TRANSLATION = "Слово → перевод"
    TRANSLATION_TO_WORD = "Перевод → слово"


class Mode(Enum):
    TYPING = "Ввод ответа"
    CHOICE = "Выбор из вариантов"


@dataclass
class TrainingSettings:
    size: int
    direction: Direction = Direction.WORD_TO_TRANSLATION
    mode: Mode = Mode.TYPING
    shuffle: bool = True
    only_unlearned: bool = False


@dataclass
class Answer:
    card: Card
    given: str
    is_correct: bool


def normalize(text: str) -> str:
    """Приведение ответа к единому виду: регистр, ё/е, лишние пробелы."""
    return " ".join(text.casefold().replace("ё", "е").split())


def pick_cards(cards: list[Card], settings: TrainingSettings) -> list[Card]:
    """Выбор карточек: сначала самые слабые по уровню."""
    pool = cards
    if settings.only_unlearned:
        pool = [c for c in cards if c.level < LEARNED_LEVEL]
    if settings.shuffle:
        pool = sorted(pool, key=lambda c: (c.level, random.random()))
    else:
        pool = sorted(pool, key=lambda c: c.level)
    chosen = pool[:settings.size]
    if settings.shuffle:
        random.shuffle(chosen)
    return chosen


class TrainingSession:
    def __init__(self, cards: list[Card], settings: TrainingSettings,
                 deck_cards: list[Card] | None = None):
        """cards — карточки тренировки, deck_cards — вся колода (для вариантов ответа)."""
        self.cards = cards
        self.settings = settings
        self.deck_cards = deck_cards or cards
        self.index = 0
        self.answers: list[Answer] = []
        self._choices: dict[int, list[str]] = {}

    @property
    def total(self) -> int:
        return len(self.cards)

    @property
    def finished(self) -> bool:
        return self.index >= self.total

    @property
    def current(self) -> Card:
        return self.cards[self.index]

    @property
    def correct_count(self) -> int:
        return sum(1 for a in self.answers if a.is_correct)

    @property
    def mistakes(self) -> list[Card]:
        return [a.card for a in self.answers if not a.is_correct]

    @property
    def accuracy(self) -> int:
        if not self.answers:
            return 0
        return round(self.correct_count * 100 / len(self.answers))

    def question(self, card: Card) -> str:
        if self.settings.direction == Direction.WORD_TO_TRANSLATION:
            return card.word
        return card.translation

    def expected(self, card: Card) -> str:
        if self.settings.direction == Direction.WORD_TO_TRANSLATION:
            return card.translation
        return card.word

    def choices(self, card: Card) -> list[str]:
        """Варианты ответа: правильный + случайные из той же колоды.
        Запоминаются, чтобы при перерисовке порядок не менялся."""
        if card.id not in self._choices:
            right = self.expected(card)
            others = {self.expected(c) for c in self.deck_cards}
            others = [o for o in others if normalize(o) != normalize(right)]
            options = random.sample(others, min(CHOICES_COUNT - 1, len(others)))
            options.append(right)
            random.shuffle(options)
            self._choices[card.id] = options
        return self._choices[card.id]

    def is_right(self, card: Card, given: str) -> bool:
        """Перевод вида «дом, здание» засчитывается по любому из вариантов."""
        given = normalize(given)
        expected = self.expected(card)
        variants = [expected] + expected.replace(";", ",").split(",")
        return any(given == normalize(v) for v in variants if v.strip())

    def answer(self, given: str) -> Answer:
        card = self.current
        result = Answer(card, given.strip(), self.is_right(card, given))
        self.answers.append(result)
        self.index += 1
        return result

    def retry_mistakes(self) -> "TrainingSession":
        cards = list({c.id: c for c in self.mistakes}.values())
        random.shuffle(cards)
        return TrainingSession(cards, self.settings, self.deck_cards)

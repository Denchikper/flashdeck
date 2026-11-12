# Flashdeck — классы данных
# by Benovich · https://github.com/Denchikper/flashdeck

from dataclasses import dataclass

from flashdeck.config import LEARNED_LEVEL


@dataclass
class Deck:
    id: int
    name: str
    created_at: str = ""
    card_count: int = 0
    learned_count: int = 0

    @property
    def progress(self) -> int:
        """Процент выученных карточек."""
        if not self.card_count:
            return 0
        return round(self.learned_count * 100 / self.card_count)


@dataclass
class Card:
    id: int | None
    deck_id: int
    word: str
    translation: str
    example: str = ""
    image_path: str = ""
    level: int = 0

    @property
    def is_learned(self) -> bool:
        return self.level >= LEARNED_LEVEL


@dataclass
class Session:
    id: int
    deck_id: int
    started_at: str
    total: int
    correct: int

    @property
    def accuracy(self) -> int:
        if not self.total:
            return 0
        return round(self.correct * 100 / self.total)

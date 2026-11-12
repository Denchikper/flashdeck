# Flashdeck — окно настроек тренировки
# by Benovich · https://github.com/Denchikper/flashdeck

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from flashdeck.config import CHOICES_COUNT, DEFAULT_SESSION_SIZE, FORMS_DIR, LEARNED_LEVEL
from flashdeck.models import Card, Deck
from flashdeck.trainer import Direction, Mode, TrainingSettings


class TrainingSetupDialog(QDialog):
    def __init__(self, deck: Deck, cards: list[Card], parent=None):
        super().__init__(parent)
        uic.loadUi(FORMS_DIR / "training_setup.ui", self)
        self.cards = cards
        self.unlearned_count = sum(1 for c in cards if c.level < LEARNED_LEVEL)

        self.deckLabel.setText(deck.name)
        for direction in Direction:
            self.directionCombo.addItem(direction.value, direction)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText("Начать")

        # Для выбора из вариантов нужно хотя бы CHOICES_COUNT разных ответов
        self.choiceRadio.setEnabled(len(cards) >= CHOICES_COUNT)

        self.unlearnedCheck.toggled.connect(self.update_limits)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.update_limits()
        self.sizeSpinBox.setValue(min(DEFAULT_SESSION_SIZE, self.sizeSpinBox.maximum()))

    def update_limits(self) -> None:
        available = self.unlearned_count if self.unlearnedCheck.isChecked() else len(self.cards)
        self.sizeSpinBox.setMaximum(max(1, available))
        self.sizeSpinBox.setSuffix(f" из {available}")

        hints = []
        if not self.choiceRadio.isEnabled():
            hints.append(f"Выбор из вариантов доступен, когда в колоде "
                         f"от {CHOICES_COUNT} карточек.")
        if available == 0:
            hints.append("Все карточки уже выучены — снимите галочку «Только невыученные».")
        self.hintLabel.setText("\n".join(hints))
        self.hintLabel.setVisible(bool(hints))
        ok_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setEnabled(available > 0)

    def settings(self) -> TrainingSettings:
        return TrainingSettings(
            size=self.sizeSpinBox.value(),
            direction=self.directionCombo.currentData(),
            mode=Mode.CHOICE if self.choiceRadio.isChecked() else Mode.TYPING,
            shuffle=self.shuffleCheck.isChecked(),
            only_unlearned=self.unlearnedCheck.isChecked(),
        )

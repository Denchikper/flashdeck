# Flashdeck — окно колоды: список карточек и их редактирование
# by Benovich · https://github.com/Denchikper/flashdeck

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from flashdeck import images
from flashdeck.config import MAX_LEVEL
from flashdeck.models import Card, Deck
from flashdeck.repositories import Repositories
from flashdeck.ui.card_dialog import CardDialog

COLUMNS = ["Слово", "Перевод", "Пример", "Уровень"]
PREVIEW_SIZE = 220


class DeckWindow(QDialog):
    def __init__(self, deck: Deck, repos: Repositories, parent=None):
        super().__init__(parent)
        self.deck = deck
        self.repos = repos
        self.cards: list[Card] = []

        self.setWindowTitle(f"Колода «{deck.name}»")
        self.resize(900, 520)
        self.build_ui()
        self.load_cards()

    def build_ui(self) -> None:
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по слову или переводу…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.load_cards)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.update_preview)
        self.table.cellDoubleClicked.connect(self.edit_card)

        self.preview = QLabel("Выберите карточку")
        self.preview.setFixedSize(PREVIEW_SIZE, PREVIEW_SIZE)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setWordWrap(True)
        self.preview.setStyleSheet("border: 1px solid palette(mid); border-radius: 6px;")

        self.add_button = QPushButton("Добавить")
        self.edit_button = QPushButton("Изменить")
        self.delete_button = QPushButton("Удалить")
        self.reset_button = QPushButton("Сбросить прогресс")
        self.add_button.clicked.connect(self.add_card)
        self.edit_button.clicked.connect(self.edit_card)
        self.delete_button.clicked.connect(self.delete_card)
        self.reset_button.clicked.connect(self.reset_progress)

        self.count_label = QLabel()

        side = QVBoxLayout()
        side.addWidget(self.preview)
        for button in (self.add_button, self.edit_button, self.delete_button):
            side.addWidget(button)
        side.addStretch()
        side.addWidget(self.reset_button)

        left = QVBoxLayout()
        left.addWidget(self.search_edit)
        left.addWidget(self.table)
        left.addWidget(self.count_label)

        layout = QHBoxLayout(self)
        layout.addLayout(left, stretch=1)
        layout.addLayout(side)

    def load_cards(self) -> None:
        selected = self.selected_card()
        self.cards = self.repos.cards.by_deck(self.deck.id, self.search_edit.text())

        self.table.clearSelection()
        self.table.setRowCount(len(self.cards))
        for row, card in enumerate(self.cards):
            values = [card.word, card.translation, card.example,
                      "★" * card.level + "☆" * (MAX_LEVEL - card.level)]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
            if selected and card.id == selected.id:
                self.table.selectRow(row)

        total = self.repos.cards.count(self.deck.id)
        if self.search_edit.text():
            self.count_label.setText(f"Карточек: показано {len(self.cards)} из {total}")
        else:
            self.count_label.setText(f"Карточек: всего {total}")
        self.update_preview()

    def selected_card(self) -> Card | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows or rows[0].row() >= len(self.cards):
            return None
        return self.cards[rows[0].row()]

    def update_preview(self) -> None:
        card = self.selected_card()
        self.edit_button.setEnabled(card is not None)
        self.delete_button.setEnabled(card is not None)
        if card is None:
            self.preview.setText("Выберите карточку")
            return
        pixmap = images.load_pixmap(card.image_path, PREVIEW_SIZE - 10, PREVIEW_SIZE - 10)
        if pixmap:
            self.preview.setPixmap(pixmap)
        else:
            self.preview.setText(f"{card.word}\n—\n{card.translation}")

    def add_card(self) -> None:
        card = Card(None, self.deck.id, "", "")
        if CardDialog(card, self).exec():
            self.repos.cards.add(card)
            self.load_cards()

    def edit_card(self) -> None:
        card = self.selected_card()
        if card and CardDialog(card, self).exec():
            self.repos.cards.update(card)
            self.load_cards()

    def delete_card(self) -> None:
        card = self.selected_card()
        if card is None:
            return
        answer = QMessageBox.question(self, "Удаление", f"Удалить карточку «{card.word}»?")
        if answer == QMessageBox.StandardButton.Yes:
            self.repos.cards.delete(card.id)
            images.remove_image(card.image_path)
            self.load_cards()

    def reset_progress(self) -> None:
        answer = QMessageBox.question(
            self, "Сброс прогресса",
            "Сбросить уровень всех карточек колоды до нуля?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.repos.cards.reset_levels(self.deck.id)
            self.load_cards()

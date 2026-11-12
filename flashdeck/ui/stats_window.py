# Flashdeck — окно статистики по колоде
# by Benovich · https://github.com/Denchikper/flashdeck

from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from flashdeck.config import LEARNED_LEVEL, MAX_LEVEL
from flashdeck.models import Deck
from flashdeck.repositories import Repositories
from flashdeck.ui.chart_widget import BarChart

RECENT_SESSIONS = 15
HARDEST_LIMIT = 15
HARD_COLUMNS = ["Слово", "Перевод", "Ошибок", "Ответов", "Уровень"]


class StatsWindow(QDialog):
    def __init__(self, decks: list[Deck], current: Deck, repos: Repositories, parent=None):
        super().__init__(parent)
        self.decks = decks
        self.repos = repos

        self.setWindowTitle("Статистика")
        self.resize(720, 520)
        self.build_ui()
        self.deck_combo.setCurrentIndex(next(
            (i for i, d in enumerate(decks) if d.id == current.id), 0))
        self.load_stats()

    def build_ui(self) -> None:
        self.deck_combo = QComboBox()
        for deck in self.decks:
            self.deck_combo.addItem(deck.name, deck.id)
        self.deck_combo.currentIndexChanged.connect(self.load_stats)

        top = QHBoxLayout()
        top.addWidget(QLabel("Колода:"))
        top.addWidget(self.deck_combo, stretch=1)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_progress_tab(), "Тренировки")
        self.tabs.addTab(self.build_levels_tab(), "Уровни карточек")
        self.tabs.addTab(self.build_hard_tab(), "Сложные карточки")

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.tabs)

    def build_progress_tab(self) -> QWidget:
        self.sessions_value = QLabel()
        self.answers_value = QLabel()
        self.accuracy_value = QLabel()
        self.last_value = QLabel()

        summary = QGridLayout()
        captions = ["Тренировок", "Ответов", "Средняя точность", "Последняя"]
        values = [self.sessions_value, self.answers_value, self.accuracy_value, self.last_value]
        for col, (caption, value) in enumerate(zip(captions, values)):
            value.setStyleSheet("font-size: 20pt; font-weight: bold;")
            summary.addWidget(value, 0, col)
            summary.addWidget(QLabel(caption), 1, col)

        self.accuracy_chart = BarChart()
        self.accuracy_chart.empty_text = "Тренировок по этой колоде ещё не было"

        layout = QVBoxLayout()
        layout.addLayout(summary)
        layout.addWidget(QLabel(f"Точность последних {RECENT_SESSIONS} тренировок:"))
        layout.addWidget(self.accuracy_chart)
        tab = QWidget()
        tab.setLayout(layout)
        return tab

    def build_levels_tab(self) -> QWidget:
        self.levels_chart = BarChart()
        self.levels_chart.empty_text = "В колоде нет карточек"
        self.levels_hint = QLabel()
        self.levels_hint.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(self.levels_chart)
        layout.addWidget(self.levels_hint)
        tab = QWidget()
        tab.setLayout(layout)
        return tab

    def build_hard_tab(self) -> QWidget:
        self.hard_table = QTableWidget(0, len(HARD_COLUMNS))
        self.hard_table.setHorizontalHeaderLabels(HARD_COLUMNS)
        self.hard_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.hard_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.hard_table.verticalHeader().hide()
        header = self.hard_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for col in range(2, len(HARD_COLUMNS)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.hard_empty = QLabel("Ошибок пока не было — так держать!")

        layout = QVBoxLayout()
        layout.addWidget(self.hard_table)
        layout.addWidget(self.hard_empty)
        tab = QWidget()
        tab.setLayout(layout)
        return tab

    def load_stats(self) -> None:
        deck_id = self.deck_combo.currentData()
        if deck_id is None:
            return
        self.load_progress(deck_id)
        self.load_levels(deck_id)
        self.load_hardest(deck_id)

    def load_progress(self, deck_id: int) -> None:
        sessions_count, answers, correct = self.repos.sessions.summary(deck_id)
        recent = self.repos.sessions.recent(deck_id, RECENT_SESSIONS)

        self.sessions_value.setText(str(sessions_count))
        self.answers_value.setText(str(answers))
        self.accuracy_value.setText(f"{round(correct * 100 / answers)}%" if answers else "—")
        self.last_value.setText(f"{recent[-1].accuracy}%" if recent else "—")

        self.accuracy_chart.set_data(
            [s.accuracy for s in recent],
            [s.started_at[8:10] + "." + s.started_at[5:7] for s in recent],
            max_value=100, suffix="%", highlight_last=True,
        )

    def load_levels(self, deck_id: int) -> None:
        counts = self.repos.cards.level_counts(deck_id)
        total = sum(counts)
        self.levels_chart.set_data(
            counts if total else [],
            [f"ур. {level}" for level in range(MAX_LEVEL + 1)],
        )
        learned = sum(counts[LEARNED_LEVEL:])
        self.levels_hint.setText(
            f"Уровень растёт на 1 за верный ответ и падает на 1 за ошибку. "
            f"Карточка считается выученной с уровня {LEARNED_LEVEL}. "
            f"Выучено: {learned} из {total}."
        )

    def load_hardest(self, deck_id: int) -> None:
        rows = self.repos.cards.hardest(deck_id, HARDEST_LIMIT)
        self.hard_table.setRowCount(len(rows))
        for row, (card, mistakes, attempts) in enumerate(rows):
            values = [card.word, card.translation, str(mistakes), str(attempts), str(card.level)]
            for col, value in enumerate(values):
                self.hard_table.setItem(row, col, QTableWidgetItem(value))
        self.hard_table.setVisible(bool(rows))
        self.hard_empty.setVisible(not rows)

# Flashdeck — главное окно: список колод
# by Benovich · https://github.com/Denchikper/flashdeck

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont, QKeySequence
from PyQt6.QtWidgets import (
    QFileDialog, QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton, QStyle, QVBoxLayout, QWidget,
)

from flashdeck import csv_io
from flashdeck.config import APP_NAME
from flashdeck.models import Deck
from flashdeck.repositories import Repositories
from flashdeck.trainer import TrainingSession, pick_cards
from flashdeck.ui.about_dialog import AboutDialog
from flashdeck.ui.deck_window import DeckWindow
from flashdeck.ui.stats_window import StatsWindow
from flashdeck.ui.training_setup import TrainingSetupDialog
from flashdeck.ui.training_window import TrainingWindow

CSV_FILTER = "CSV-файлы (*.csv);;Все файлы (*)"


class MainWindow(QMainWindow):
    def __init__(self, repos: Repositories):
        super().__init__()
        self.repos = repos
        self.decks: list[Deck] = []

        self.setWindowTitle(APP_NAME)
        self.resize(820, 520)
        self.create_actions()
        self.create_menu()
        self.create_toolbar()
        self.build_ui()
        self.load_decks()

    def create_actions(self) -> None:
        icon = self.style().standardIcon
        pix = QStyle.StandardPixmap

        self.new_action = QAction(icon(pix.SP_FileIcon), "Новая колода", self)
        self.new_action.setShortcut(QKeySequence.StandardKey.New)
        self.new_action.triggered.connect(self.new_deck)

        self.open_action = QAction(icon(pix.SP_DirOpenIcon), "Открыть колоду", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.open_deck)

        self.train_action = QAction(icon(pix.SP_MediaPlay), "Тренировка", self)
        self.train_action.setShortcut("Ctrl+T")
        self.train_action.triggered.connect(self.start_training)

        self.stats_action = QAction(icon(pix.SP_FileDialogInfoView), "Статистика", self)
        self.stats_action.setShortcut("Ctrl+Shift+S")
        self.stats_action.triggered.connect(self.show_stats)

        self.rename_action = QAction(icon(pix.SP_FileDialogDetailedView), "Переименовать", self)
        self.rename_action.setShortcut("F2")
        self.rename_action.triggered.connect(self.rename_deck)

        self.delete_action = QAction(icon(pix.SP_TrashIcon), "Удалить", self)
        self.delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        self.delete_action.triggered.connect(self.delete_deck)

        self.import_action = QAction(icon(pix.SP_ArrowDown), "Импорт из CSV…", self)
        self.import_action.setShortcut("Ctrl+I")
        self.import_action.triggered.connect(self.import_csv)

        self.export_action = QAction(icon(pix.SP_ArrowUp), "Экспорт в CSV…", self)
        self.export_action.setShortcut("Ctrl+E")
        self.export_action.triggered.connect(self.export_csv)

        self.quit_action = QAction("Выход", self)
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.quit_action.triggered.connect(self.close)

        self.about_action = QAction("О программе", self)
        self.about_action.triggered.connect(self.show_about)

        # Действия, которым нужна выбранная колода
        self.deck_actions = [self.open_action, self.train_action, self.stats_action,
                             self.rename_action,
                             self.delete_action, self.export_action]

    def create_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("Файл")
        file_menu.addActions([self.import_action, self.export_action])
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)

        deck_menu = menu.addMenu("Колода")
        deck_menu.addActions([self.new_action, self.open_action, self.train_action,
                              self.stats_action])
        deck_menu.addSeparator()
        deck_menu.addActions([self.rename_action, self.delete_action])

        help_menu = menu.addMenu("Справка")
        help_menu.addAction(self.about_action)

    def create_toolbar(self) -> None:
        toolbar = self.addToolBar("Основное")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toolbar.addActions([self.new_action, self.open_action, self.train_action,
                            self.stats_action])
        toolbar.addSeparator()
        toolbar.addActions([self.import_action, self.export_action])

    def build_ui(self) -> None:
        self.deck_list = QListWidget()
        self.deck_list.setMinimumWidth(280)
        self.deck_list.currentRowChanged.connect(self.show_deck_info)
        self.deck_list.itemDoubleClicked.connect(self.open_deck)
        self.deck_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.deck_list.customContextMenuRequested.connect(self.show_context_menu)

        self.title_label = QLabel()
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setWordWrap(True)

        self.info_label = QLabel()
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("Выучено %p%")

        self.train_button = QPushButton("Начать тренировку")
        self.train_button.setMinimumHeight(40)
        self.train_button.clicked.connect(self.start_training)
        self.open_button = QPushButton("Открыть колоду")
        self.open_button.clicked.connect(self.open_deck)
        self.stats_button = QPushButton("Статистика")
        self.stats_button.clicked.connect(self.show_stats)

        self.empty_label = QLabel("Колод пока нет.\nСоздайте новую или импортируйте из CSV.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        info = QVBoxLayout()
        info.addWidget(self.title_label)
        info.addWidget(self.info_label)
        info.addWidget(self.progress_bar)
        info.addWidget(self.train_button)
        info.addWidget(self.open_button)
        info.addWidget(self.stats_button)
        info.addStretch()
        self.info_panel = QWidget()
        self.info_panel.setLayout(info)

        right = QVBoxLayout()
        right.addWidget(self.info_panel)
        right.addWidget(self.empty_label)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self.deck_list)
        layout.addLayout(right, stretch=1)
        self.setCentralWidget(central)

    def show_context_menu(self, pos) -> None:
        if self.deck_list.itemAt(pos) is None:
            return
        menu = QMenu(self)
        menu.addActions([self.open_action, self.train_action, self.stats_action])
        menu.addSeparator()
        menu.addActions([self.rename_action, self.export_action, self.delete_action])
        menu.exec(self.deck_list.viewport().mapToGlobal(pos))

    def load_decks(self, select_id: int | None = None) -> None:
        if select_id is None and self.current_deck():
            select_id = self.current_deck().id
        self.decks = self.repos.decks.all()

        self.deck_list.blockSignals(True)
        self.deck_list.clear()
        for deck in self.decks:
            item = QListWidgetItem(f"{deck.name}\n{deck.card_count} карт. · {deck.progress}%")
            self.deck_list.addItem(item)
        self.deck_list.blockSignals(False)

        row = next((i for i, d in enumerate(self.decks) if d.id == select_id), 0)
        self.deck_list.setCurrentRow(row if self.decks else -1)
        self.show_deck_info()

        total_cards = sum(d.card_count for d in self.decks)
        self.statusBar().showMessage(f"Колод: {len(self.decks)} · карточек: {total_cards}")

    def current_deck(self) -> Deck | None:
        row = self.deck_list.currentRow()
        return self.decks[row] if 0 <= row < len(self.decks) else None

    def show_deck_info(self) -> None:
        deck = self.current_deck()
        has_deck = deck is not None
        self.info_panel.setVisible(has_deck)
        self.empty_label.setVisible(not has_deck)
        for action in self.deck_actions:
            action.setEnabled(has_deck)
        if not has_deck:
            return

        self.title_label.setText(deck.name)
        self.info_label.setText(
            f"Карточек: {deck.card_count}\n"
            f"Выучено: {deck.learned_count}\n"
            f"Создана: {deck.created_at[:10]}"
        )
        self.progress_bar.setValue(deck.progress)

    def ask_deck_name(self, title: str, text: str = "") -> str | None:
        """Спрашивает имя колоды, пока не введут уникальное или не нажмут «Отмена»."""
        while True:
            name, ok = QInputDialog.getText(self, title, "Название колоды:", text=text)
            name = name.strip()
            if not ok or not name:
                return None
            if not self.repos.decks.exists(name):
                return name
            QMessageBox.warning(self, title, f"Колода «{name}» уже есть.")
            text = name

    def new_deck(self) -> None:
        name = self.ask_deck_name("Новая колода")
        if name:
            self.load_decks(self.repos.decks.create(name))

    def open_deck(self) -> None:
        deck = self.current_deck()
        if deck:
            DeckWindow(deck, self.repos, self).exec()
            self.load_decks()

    def start_training(self) -> None:
        deck = self.current_deck()
        if not deck:
            return
        cards = self.repos.cards.by_deck(deck.id)
        if not cards:
            QMessageBox.information(self, "Тренировка", "В колоде пока нет карточек.")
            return

        setup = TrainingSetupDialog(deck, cards, self)
        if not setup.exec():
            return
        settings = setup.settings()
        session = TrainingSession(pick_cards(cards, settings), settings, cards)
        TrainingWindow(deck, session, self.repos, self).exec()
        self.load_decks()

    def show_stats(self) -> None:
        deck = self.current_deck()
        if deck:
            StatsWindow(self.decks, deck, self.repos, self).exec()

    def rename_deck(self) -> None:
        deck = self.current_deck()
        if not deck:
            return
        name = self.ask_deck_name("Переименование", deck.name)
        if name:
            self.repos.decks.rename(deck.id, name)
            self.load_decks()

    def delete_deck(self) -> None:
        deck = self.current_deck()
        if not deck:
            return
        answer = QMessageBox.question(
            self, "Удаление",
            f"Удалить колоду «{deck.name}» вместе с {deck.card_count} карточками "
            "и историей тренировок?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.repos.decks.delete(deck.id)
            self.load_decks()

    def import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Импорт колоды", "", CSV_FILTER)
        if not path:
            return
        try:
            cards = csv_io.read_cards(Path(path))
        except csv_io.CsvFormatError as e:
            QMessageBox.warning(self, "Импорт", f"Файл не подходит: {e}")
            return
        except (OSError, UnicodeDecodeError):
            QMessageBox.critical(self, "Импорт", "Не удалось прочитать файл.")
            return

        name = self.ask_deck_name("Импорт колоды", Path(path).stem)
        if not name:
            return
        deck_id = self.repos.decks.create(name)
        self.repos.cards.add_many(deck_id, cards)
        self.load_decks(deck_id)
        QMessageBox.information(self, "Импорт", f"Добавлено карточек: {len(cards)}")

    def export_csv(self) -> None:
        deck = self.current_deck()
        if not deck:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт колоды", f"{deck.name}.csv", CSV_FILTER)
        if not path:
            return
        try:
            csv_io.write_cards(Path(path), self.repos.cards.by_deck(deck.id))
        except OSError:
            QMessageBox.critical(self, "Экспорт", "Не удалось сохранить файл.")
            return
        self.statusBar().showMessage(f"Колода сохранена в {path}", 5000)

    def show_about(self) -> None:
        AboutDialog(self).exec()

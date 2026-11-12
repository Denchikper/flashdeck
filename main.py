# Flashdeck — карточки для запоминания слов
# by Benovich · https://github.com/Denchikper/flashdeck

import sys

from PyQt6.QtCore import QLibraryInfo, QLocale, QTranslator
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from flashdeck import csv_io
from flashdeck.config import APP_NAME, ASSETS_DIR, DB_PATH
from flashdeck.database import Database
from flashdeck.repositories import Repositories
from flashdeck.ui.main_window import MainWindow

SAMPLE_DECK_NAME = "Английский: базовые слова"


def add_sample_deck(repos: Repositories) -> None:
    cards = csv_io.read_cards(ASSETS_DIR / "sample_english.csv")
    deck_id = repos.decks.create(SAMPLE_DECK_NAME)
    repos.cards.add_many(deck_id, cards)


def install_translator(app: QApplication) -> None:
    """Русские надписи на стандартных кнопках и диалогах Qt."""
    translator = QTranslator(app)
    path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load(QLocale(QLocale.Language.Russian), "qtbase", "_", path):
        app.installTranslator(translator)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    install_translator(app)
    app.setWindowIcon(QIcon(str(ASSETS_DIR / "icon.png")))

    first_run = not DB_PATH.exists()
    db = Database(DB_PATH)
    repos = Repositories(db)
    if first_run:
        add_sample_deck(repos)

    window = MainWindow(repos)
    window.show()
    code = app.exec()
    db.close()
    sys.exit(code)


if __name__ == "__main__":
    main()

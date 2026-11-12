# Flashdeck — окно тренировки
# by Benovich · https://github.com/Denchikper/flashdeck

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeyEvent
from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMessageBox, QProgressBar, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from flashdeck import csv_io, images
from flashdeck.config import CHOICES_COUNT
from flashdeck.models import Deck
from flashdeck.repositories import Repositories
from flashdeck.trainer import Answer, Direction, Mode, TrainingSession

IMAGE_SIZE = 200
RIGHT_COLOR = "#2e9e5b"
WRONG_COLOR = "#d64545"
ENTER_KEYS = (Qt.Key.Key_Return, Qt.Key.Key_Enter)


def big_font(size: int, bold: bool = False) -> QFont:
    font = QFont()
    font.setPointSize(size)
    font.setBold(bold)
    return font


class TrainingWindow(QDialog):
    def __init__(self, deck: Deck, session: TrainingSession, repos: Repositories, parent=None):
        super().__init__(parent)
        self.deck = deck
        self.session = session
        self.repos = repos
        self.waiting_next = False
        self.saved = False

        self.setWindowTitle(f"Тренировка — {deck.name}")
        self.resize(560, 600)
        self.build_ui()
        self.show_question()

    # ---------- интерфейс ----------

    def build_ui(self) -> None:
        self.pages = QStackedWidget()
        self.pages.addWidget(self.build_question_page())
        self.pages.addWidget(self.build_result_page())
        layout = QVBoxLayout(self)
        layout.addWidget(self.pages)
        # Enter обрабатывается в keyPressEvent, кнопки не должны его перехватывать
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)

    def build_question_page(self) -> QWidget:
        self.progress = QProgressBar()
        self.progress.setFormat("%v / %m")
        self.score_label = QLabel()

        self.task_label = QLabel()
        self.task_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.task_label.setStyleSheet("color: gray;")

        self.question_label = QLabel()
        self.question_label.setFont(big_font(28, bold=True))
        self.question_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.question_label.setWordWrap(True)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedHeight(IMAGE_SIZE)

        self.answer_edit = QLineEdit()
        self.answer_edit.setFont(big_font(16))
        self.answer_edit.setPlaceholderText("Ответ…")
        self.check_button = QPushButton("Проверить")
        self.check_button.clicked.connect(self.submit_typed)
        typing_row = QHBoxLayout()
        typing_row.addWidget(self.answer_edit)
        typing_row.addWidget(self.check_button)
        self.typing_box = QWidget()
        self.typing_box.setLayout(typing_row)

        self.choice_buttons = []
        grid = QGridLayout()
        for i in range(CHOICES_COUNT):
            button = QPushButton()
            button.setMinimumHeight(44)
            button.setFont(big_font(14))
            button.clicked.connect(lambda _, b=button: self.submit_choice(b))
            grid.addWidget(button, i // 2, i % 2)
            self.choice_buttons.append(button)
        self.choice_box = QWidget()
        self.choice_box.setLayout(grid)

        self.feedback_label = QLabel()
        self.feedback_label.setFont(big_font(14, bold=True))
        self.feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback_label.setWordWrap(True)
        self.example_label = QLabel()
        self.example_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.example_label.setWordWrap(True)
        self.example_label.setStyleSheet("font-style: italic;")

        self.next_button = QPushButton("Далее  ⏎")
        self.next_button.clicked.connect(self.go_next)

        top = QHBoxLayout()
        top.addWidget(self.progress, stretch=1)
        top.addWidget(self.score_label)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addSpacing(16)
        layout.addWidget(self.task_label)
        layout.addWidget(self.question_label)
        layout.addWidget(self.image_label)
        layout.addWidget(self.typing_box)
        layout.addWidget(self.choice_box)
        layout.addWidget(self.feedback_label)
        layout.addWidget(self.example_label)
        layout.addStretch()
        layout.addWidget(self.next_button)
        page = QWidget()
        page.setLayout(layout)
        return page

    def build_result_page(self) -> QWidget:
        self.result_label = QLabel()
        self.result_label.setFont(big_font(30, bold=True))
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_comment = QLabel()
        self.result_comment.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.mistakes_title = QLabel("Ошибки:")
        self.mistakes_list = QListWidget()

        self.retry_button = QPushButton("Повторить ошибки")
        self.report_button = QPushButton("Сохранить отчёт…")
        self.close_button = QPushButton("Закрыть")
        self.retry_button.clicked.connect(self.retry_mistakes)
        self.report_button.clicked.connect(self.save_report)
        self.close_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(self.retry_button)
        buttons.addWidget(self.report_button)
        buttons.addStretch()
        buttons.addWidget(self.close_button)

        layout = QVBoxLayout()
        layout.addSpacing(20)
        layout.addWidget(self.result_label)
        layout.addWidget(self.result_comment)
        layout.addSpacing(12)
        layout.addWidget(self.mistakes_title)
        layout.addWidget(self.mistakes_list)
        layout.addLayout(buttons)
        page = QWidget()
        page.setLayout(layout)
        return page

    # ---------- ход тренировки ----------

    def show_question(self) -> None:
        session = self.session
        card = session.current
        self.waiting_next = False
        self.pages.setCurrentIndex(0)

        self.progress.setMaximum(session.total)
        self.progress.setValue(session.index)
        self.score_label.setText(f"Верно: {session.correct_count}")

        if session.settings.direction == Direction.WORD_TO_TRANSLATION:
            self.task_label.setText("Как переводится?")
        else:
            self.task_label.setText("Как это будет на изучаемом языке?")
        self.question_label.setText(session.question(card))
        self.image_label.clear()
        self.image_label.hide()
        self.feedback_label.clear()
        self.example_label.clear()
        self.next_button.hide()

        typing = session.settings.mode == Mode.TYPING
        self.typing_box.setVisible(typing)
        self.choice_box.setVisible(not typing)
        if typing:
            self.answer_edit.clear()
            self.answer_edit.setEnabled(True)
            self.check_button.setEnabled(True)
            self.answer_edit.setFocus()
        else:
            options = session.choices(card)
            for i, button in enumerate(self.choice_buttons):
                has_option = i < len(options)
                button.setVisible(has_option)
                button.setEnabled(True)
                button.setStyleSheet("")
                if has_option:
                    button.setText(f"{i + 1}. {options[i]}")
                    button.setProperty("option", options[i])

    def submit_typed(self) -> None:
        if self.waiting_next:
            return
        self.answer_edit.setEnabled(False)
        self.check_button.setEnabled(False)
        self.handle_answer(self.session.answer(self.answer_edit.text()))

    def submit_choice(self, button: QPushButton) -> None:
        if self.waiting_next:
            return
        result = self.session.answer(button.property("option"))
        for other in self.choice_buttons:
            other.setEnabled(False)
            if self.session.is_right(result.card, other.property("option") or ""):
                other.setStyleSheet(f"background: {RIGHT_COLOR}; color: white;")
        if not result.is_correct:
            button.setStyleSheet(f"background: {WRONG_COLOR}; color: white;")
        self.handle_answer(result)

    def handle_answer(self, result: Answer) -> None:
        self.waiting_next = True
        card = result.card
        self.repos.cards.change_level(card.id, +1 if result.is_correct else -1)

        if result.is_correct:
            self.feedback_label.setText("Верно!")
            self.feedback_label.setStyleSheet(f"color: {RIGHT_COLOR};")
        else:
            self.feedback_label.setText(f"Правильно: {self.session.expected(card)}")
            self.feedback_label.setStyleSheet(f"color: {WRONG_COLOR};")
        self.example_label.setText(card.example)

        pixmap = images.load_pixmap(card.image_path, IMAGE_SIZE, IMAGE_SIZE)
        if pixmap:
            self.image_label.setPixmap(pixmap)
            self.image_label.show()

        self.progress.setValue(self.session.index)
        self.score_label.setText(f"Верно: {self.session.correct_count}")
        self.next_button.setText("Результаты  ⏎" if self.session.finished else "Далее  ⏎")
        self.next_button.show()
        self.next_button.setFocus()

    def go_next(self) -> None:
        if self.session.finished:
            self.finish()
        else:
            self.show_question()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if self.pages.currentIndex() == 0 and key in ENTER_KEYS:
            if self.waiting_next:
                self.go_next()
            elif self.session.settings.mode == Mode.TYPING:
                self.submit_typed()
            return
        if self.pages.currentIndex() == 0 and not self.waiting_next \
                and self.session.settings.mode == Mode.CHOICE \
                and Qt.Key.Key_1 <= key < Qt.Key.Key_1 + CHOICES_COUNT:
            button = self.choice_buttons[key - Qt.Key.Key_1]
            if button.isVisible():
                self.submit_choice(button)
            return
        super().keyPressEvent(event)

    # ---------- итоги ----------

    def save_session(self) -> None:
        if self.saved or not self.session.answers:
            return
        answers = [(a.card.id, a.is_correct) for a in self.session.answers]
        self.repos.sessions.save(self.deck.id, answers)
        self.saved = True

    def finish(self) -> None:
        self.save_session()
        session = self.session
        self.result_label.setText(f"{session.correct_count} из {session.total}")
        if session.accuracy == 100:
            comment = "Без единой ошибки!"
        elif session.accuracy >= 70:
            comment = f"Хороший результат — {session.accuracy}%"
        else:
            comment = f"{session.accuracy}% — стоит повторить"
        self.result_comment.setText(comment)

        self.mistakes_list.clear()
        for answer in session.answers:
            if not answer.is_correct:
                given = answer.given or "—"
                self.mistakes_list.addItem(
                    f"{session.question(answer.card)} → {session.expected(answer.card)}"
                    f"   (ваш ответ: {given})"
                )
        has_mistakes = bool(session.mistakes)
        self.mistakes_title.setVisible(has_mistakes)
        self.mistakes_list.setVisible(has_mistakes)
        self.retry_button.setVisible(has_mistakes)
        self.pages.setCurrentIndex(1)
        self.close_button.setFocus()

    def retry_mistakes(self) -> None:
        self.session = self.session.retry_mistakes()
        self.saved = False
        self.show_question()

    def save_report(self) -> None:
        default_name = f"Отчёт — {self.deck.name}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчёт", default_name, "Текстовые файлы (*.txt)")
        if not path:
            return
        try:
            csv_io.write_report(Path(path), self.deck.name, self.session)
        except OSError:
            QMessageBox.critical(self, "Отчёт", "Не удалось сохранить файл.")
            return
        QMessageBox.information(self, "Отчёт", "Отчёт сохранён.")

    def reject(self) -> None:
        """Закрытие посреди тренировки — с подтверждением, ответы сохраняются."""
        in_progress = self.pages.currentIndex() == 0 and self.session.answers
        if in_progress:
            answer = QMessageBox.question(
                self, "Тренировка",
                "Прервать тренировку? Уже данные ответы будут сохранены.",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.save_session()
        super().reject()

# Flashdeck — окно добавления и изменения карточки
# by Benovich · https://github.com/Denchikper/flashdeck

from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox

from flashdeck import images
from flashdeck.config import FORMS_DIR
from flashdeck.models import Card

IMAGE_FILTER = "Картинки (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
PREVIEW_WIDTH = 400
PREVIEW_HEIGHT = 180


class CardDialog(QDialog):
    def __init__(self, card: Card, parent=None):
        super().__init__(parent)
        uic.loadUi(FORMS_DIR / "card_dialog.ui", self)
        self.card = card
        # Новая картинка копируется в папку приложения только при сохранении
        self.new_image: Path | None = None
        self.image_removed = False

        self.setWindowTitle("Новая карточка" if card.id is None else "Изменить карточку")
        self.wordEdit.setText(card.word)
        self.translationEdit.setText(card.translation)
        self.exampleEdit.setPlainText(card.example)
        self.levelSlider.setValue(card.level)
        self.levelLcd.display(card.level)

        self.levelSlider.valueChanged.connect(self.levelLcd.display)
        self.chooseImageButton.clicked.connect(self.choose_image)
        self.removeImageButton.clicked.connect(self.remove_image)
        self.buttonBox.accepted.connect(self.save)
        self.buttonBox.rejected.connect(self.reject)

        self.show_preview(images.load_pixmap(card.image_path, PREVIEW_WIDTH, PREVIEW_HEIGHT))

    def show_preview(self, pixmap: QPixmap | None) -> None:
        if pixmap is None:
            self.imageLabel.clear()
            self.imageLabel.setText("Нет картинки")
        else:
            self.imageLabel.setPixmap(pixmap)
        self.removeImageButton.setEnabled(pixmap is not None)

    def choose_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выбор картинки", "", IMAGE_FILTER)
        if not path:
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, "Картинка", "Не удалось открыть файл как картинку.")
            return
        self.new_image = Path(path)
        self.show_preview(pixmap.scaled(
            PREVIEW_WIDTH, PREVIEW_HEIGHT, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def remove_image(self) -> None:
        self.new_image = None
        self.image_removed = True
        self.show_preview(None)

    def save(self) -> None:
        word = self.wordEdit.text().strip()
        translation = self.translationEdit.text().strip()
        if not word or not translation:
            QMessageBox.warning(self, "Карточка", "Заполните слово и перевод.")
            return

        if self.new_image or self.image_removed:
            images.remove_image(self.card.image_path)
            self.card.image_path = images.import_image(self.new_image) if self.new_image else ""

        self.card.word = word
        self.card.translation = translation
        self.card.example = self.exampleEdit.toPlainText().strip()
        self.card.level = self.levelSlider.value()
        self.accept()

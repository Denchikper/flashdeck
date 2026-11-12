# Flashdeck — окно «О программе»
# by Benovich · https://github.com/Denchikper/flashdeck

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog

from flashdeck.config import APP_NAME, APP_VERSION, ASSETS_DIR, AUTHOR, FORMS_DIR, REPO_URL

ICON_SIZE = 96


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(FORMS_DIR / "about_dialog.ui", self)

        icon = QPixmap(str(ASSETS_DIR / "icon.png"))
        self.iconLabel.setPixmap(icon.scaled(
            ICON_SIZE, ICON_SIZE, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        self.titleLabel.setText(APP_NAME)
        self.versionLabel.setText(f"Версия {APP_VERSION}")
        self.linkLabel.setText(f"by {AUTHOR} · <a href='{REPO_URL}'>GitHub</a>")
        self.buttonBox.rejected.connect(self.reject)

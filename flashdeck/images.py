# Flashdeck — хранение картинок карточек
# by Benovich · https://github.com/Denchikper/flashdeck

import shutil
import uuid
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from flashdeck.config import IMAGES_DIR


def import_image(source: Path) -> str:
    """Копирует картинку в папку приложения и возвращает её имя."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{source.suffix.lower()}"
    shutil.copy(source, IMAGES_DIR / name)
    return name


def remove_image(name: str) -> None:
    if name:
        (IMAGES_DIR / name).unlink(missing_ok=True)


def load_pixmap(name: str, width: int, height: int) -> QPixmap | None:
    if not name:
        return None
    pixmap = QPixmap(str(IMAGES_DIR / name))
    if pixmap.isNull():
        return None
    return pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)

# Flashdeck — пути и константы приложения
# by Benovich · https://github.com/Denchikper/flashdeck

import sys
from pathlib import Path

APP_NAME = "Flashdeck"
APP_VERSION = "0.1.0"
AUTHOR = "Benovich"
REPO_URL = "https://github.com/Denchikper/flashdeck"


def resource_path(relative: str) -> Path:
    """Путь к файлу ресурсов — работает и из исходников, и из собранного exe."""
    base = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)
    return Path(base) / relative


# Данные пользователя храним в домашней папке: рядом с exe писать нельзя
DATA_DIR = Path.home() / ".flashdeck"
DB_PATH = DATA_DIR / "flashdeck.db"
IMAGES_DIR = DATA_DIR / "images"

FORMS_DIR = resource_path("flashdeck/ui/forms")
ASSETS_DIR = resource_path("assets")

MAX_LEVEL = 5
LEARNED_LEVEL = 4
CHOICES_COUNT = 4
DEFAULT_SESSION_SIZE = 10
CSV_HEADER = ["word", "translation", "example"]

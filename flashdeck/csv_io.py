# Flashdeck — импорт/экспорт колод в CSV
# by Benovich · https://github.com/Denchikper/flashdeck

import csv
from pathlib import Path

from flashdeck.config import CSV_HEADER
from flashdeck.models import Card


class CsvFormatError(Exception):
    pass


def read_cards(path: Path) -> list[Card]:
    """Читает карточки из CSV. Разделитель — запятая или точка с запятой,
    первая строка-заголовок необязательна. deck_id проставляется при сохранении."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        text = f.read()
    if not text.strip():
        raise CsvFormatError("Файл пустой")

    delimiter = ";" if text.count(";") > text.count(",") else ","
    rows = list(csv.reader(text.splitlines(), delimiter=delimiter))
    if rows and rows[0] and rows[0][0].strip().lower() == CSV_HEADER[0]:
        rows = rows[1:]

    cards = []
    for line_no, row in enumerate(rows, start=1):
        row = [cell.strip() for cell in row]
        if not any(row):
            continue
        if len(row) < 2 or not row[0] or not row[1]:
            raise CsvFormatError(f"Строка {line_no}: нужны хотя бы слово и перевод")
        example = row[2] if len(row) > 2 else ""
        cards.append(Card(None, 0, row[0], row[1], example))

    if not cards:
        raise CsvFormatError("В файле нет карточек")
    return cards


def write_cards(path: Path, cards: list[Card]) -> None:
    # utf-8-sig — чтобы Excel открывал кириллицу без кракозябр
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(CSV_HEADER)
        for card in cards:
            writer.writerow([card.word, card.translation, card.example])

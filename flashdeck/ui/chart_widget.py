# Flashdeck — столбчатая диаграмма на QPainter
# by Benovich · https://github.com/Denchikper/flashdeck

import math

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

BAR_COLOR = QColor("#3d5bd9")
HIGHLIGHT_COLOR = QColor("#f2a541")
GRID_LINES = 4
MARGIN_LEFT = 44
MARGIN_RIGHT = 12
MARGIN_TOP = 24
MARGIN_BOTTOM = 32
MAX_BAR_WIDTH = 48
MIN_LABEL_WIDTH = 40


class BarChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values: list[float] = []
        self.labels: list[str] = []
        self.max_value = 100.0
        self.suffix = ""
        self.highlight_last = False
        self.empty_text = "Нет данных"
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, values: list[float], labels: list[str], max_value: float | None = None,
                 suffix: str = "", highlight_last: bool = False) -> None:
        self.values = values
        self.labels = labels
        if max_value is None:
            # Шкала кратна числу линий сетки, чтобы подписи были целыми
            top = max(values, default=0) or 1
            max_value = math.ceil(top / GRID_LINES) * GRID_LINES
        self.max_value = max_value
        self.suffix = suffix
        self.highlight_last = highlight_last
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        text_color = self.palette().text().color()

        if not self.values:
            painter.setPen(text_color)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.empty_text)
            return

        plot = QRectF(MARGIN_LEFT, MARGIN_TOP,
                      self.width() - MARGIN_LEFT - MARGIN_RIGHT,
                      self.height() - MARGIN_TOP - MARGIN_BOTTOM)
        self.draw_grid(painter, plot, text_color)
        self.draw_bars(painter, plot, text_color)

    def draw_grid(self, painter: QPainter, plot: QRectF, text_color: QColor) -> None:
        grid_color = QColor(text_color)
        grid_color.setAlpha(40)
        for i in range(GRID_LINES + 1):
            y = plot.bottom() - plot.height() * i / GRID_LINES
            painter.setPen(QPen(grid_color, 1))
            painter.drawLine(int(plot.left()), int(y), int(plot.right()), int(y))
            value = self.max_value * i / GRID_LINES
            painter.setPen(text_color)
            painter.drawText(QRectF(0, y - 8, MARGIN_LEFT - 6, 16),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             f"{value:g}{self.suffix}")

    def draw_bars(self, painter: QPainter, plot: QRectF, text_color: QColor) -> None:
        count = len(self.values)
        slot = plot.width() / count
        bar_width = min(MAX_BAR_WIDTH, slot * 0.7)
        # Подписи под столбцами прореживаются, если не помещаются
        label_step = max(1, math.ceil(MIN_LABEL_WIDTH / slot))

        for i, value in enumerate(self.values):
            height = plot.height() * min(value, self.max_value) / self.max_value
            x = plot.left() + slot * i + (slot - bar_width) / 2
            bar = QRectF(x, plot.bottom() - height, bar_width, height)

            is_last = i == count - 1
            color = HIGHLIGHT_COLOR if self.highlight_last and is_last else BAR_COLOR
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(bar, 3, 3)

            painter.setPen(text_color)
            if slot >= 28:
                painter.drawText(QRectF(x - 10, bar.top() - 18, bar_width + 20, 16),
                                 Qt.AlignmentFlag.AlignCenter, f"{value:g}{self.suffix}")
            if i % label_step == 0 and i < len(self.labels):
                painter.drawText(QRectF(plot.left() + slot * i, plot.bottom() + 6, slot, 20),
                                 Qt.AlignmentFlag.AlignCenter, self.labels[i])

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QBrush
from PyQt6.QtCore import Qt


class JoystickBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0  # Range: -32768 to 32767
        self.setMinimumHeight(20)

    def set_value(self, value):
        """Update the bar value and trigger repaint."""
        self.value = max(-32768, min(32767, value))  # Clamp
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        center = width // 2

        normalized = self.value / 32768

        if normalized > 0:
            bar_width = int(center * normalized)
            painter.setPen(0)
            painter.setBrush(QBrush(QColor(0, 180, 0)))
            painter.drawRect(center, 0, bar_width, height)
        elif normalized < 0:
            bar_width = int(center * abs(normalized))
            painter.setPen(0)
            painter.setBrush(QBrush(QColor(180, 0, 0)))
            painter.drawRect(center - bar_width, 0, bar_width, height)

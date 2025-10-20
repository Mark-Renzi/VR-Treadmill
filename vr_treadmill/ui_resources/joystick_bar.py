from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt


class JoystickBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0  # Range: -32768 to 32767
        self.setMinimumHeight(25)

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

        # Draw filled bar
        normalized = self.value / 32768

        if normalized > 0:
            bar_width = int((center -1) * normalized)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 180, 0)))
            painter.drawRect(center, 2, bar_width, height - 4)
        elif normalized < 0:
            bar_width = int((center -1) * abs(normalized))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(180, 0, 0)))
            painter.drawRect(center - bar_width, 2, bar_width, height - 4)

        # Draw outer frame
        frame_pen = QPen(self.palette().text().color())
        frame_pen.setWidth(1)
        painter.setPen(frame_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(1, 1, width-2, height-2, 4, 4)

        # Draw center line
        lighter_color = self.palette().text().color()
        lighter_color.setAlpha(30)
        painter.setPen(QPen(lighter_color, 1, Qt.PenStyle.DotLine))
        painter.drawLine(center, 0, center, height)

        # Draw the value as text
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(self.palette().text().color())
        text = str(self.value)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

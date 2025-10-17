from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QPainter, QPen, QColor, QMouseEvent
from PyQt6.QtCore import Qt, QPointF, QRectF


class CurveEditorWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sensitivity Curve Editor")
        self.setMinimumSize(500, 500)

        self.curve_mapping = []
        self.dirty = True

        self.margin = 40  # Padding around graph
        self.graph_width = 400
        self.graph_height = 400

        # 5 draggable control points from left (input=0) to right (input=max)
        self.num_points = 5
        self.point_radius = 6
        self.dragging_point_index = None

        # Initialize control points in a straight line (linear)
        self.points = [
            QPointF(
                self.margin + i * (self.graph_width / (self.num_points - 1)),
                self.margin
                + self.graph_height
                - i * (self.graph_height / (self.num_points - 1)),
            )
            for i in range(self.num_points)
        ]

        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), Qt.GlobalColor.white)

        # Draw graph bounds
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawRect(self.margin, self.margin, self.graph_width, self.graph_height)

        # Draw curve lines
        painter.setPen(QPen(Qt.GlobalColor.blue, 2))
        for i in range(self.num_points - 1):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            painter.drawLine(p1, p2)

        # Draw control points
        painter.setPen(QPen(Qt.GlobalColor.red, 2))
        painter.setBrush(QColor("red"))
        for p in self.points:
            painter.drawEllipse(p, self.point_radius, self.point_radius)

        # Draw labels for input/output ranges
        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.drawText(
            self.margin, self.margin + self.graph_height + 20, "Mouse Input (Y)"
        )
        painter.drawText(
            self.margin + self.graph_width - 60,
            self.margin + self.graph_height + 20,
            "Joystick Output (Y)",
        )

    def mousePressEvent(self, event: QMouseEvent):
        for i, point in enumerate(self.points):
            if (point - event.position()).manhattanLength() < self.point_radius * 2:
                self.dragging_point_index = i
                break

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging_point_index is not None:
            pos = event.position()
            x = self.points[self.dragging_point_index].x()  # Lock X position
            y = min(
                max(pos.y(), self.margin),
                self.margin + self.graph_height,
            )
            self.points[self.dragging_point_index] = QPointF(x, y)
            self.dirty = True  # Mark LUT as dirty
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.dragging_point_index = None

    def get_or_build_curve_mapping(self):
        if self.dirty:
            self.curve_mapping = self.build_curve_mapping()
            self.dirty = False
        return self.curve_mapping

    def build_curve_mapping(self):
        """
        Returns list of (input, output) points.
        Called internally when curve is marked dirty.
        """
        mapping = []
        for p in self.points:
            input_x = ((p.x() - self.margin) / self.graph_width) * 32767
            output_y = (
                ((self.margin + self.graph_height) - p.y()) / self.graph_height * 32767
            )
            mapping.append((int(input_x), int(output_y)))
        return mapping


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    editor = CurveEditorWindow()
    editor.show()
    sys.exit(app.exec())

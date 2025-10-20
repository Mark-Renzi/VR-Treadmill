from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor, QMouseEvent, QIcon
from PyQt6.QtCore import Qt, QPointF


class CurveEditorWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sensitivity Curve Editor")
        self.setWindowIcon(QIcon("./resources/curve.ico"))
        self.setMinimumSize(500, 550)

        self.curve_mapping = []
        self.dirty = True

        self.margin = 40
        self.graph_width = 400
        self.graph_height = 400

        self.point_radius = 6
        self.dragging_point_index = None

        self.current_input: int | None = None

        # Initialize control points: fixed endpoints
        self.points = [
            QPointF(self.margin, self.margin + self.graph_height),
            QPointF(self.margin + self.graph_width, self.margin),
        ]

        self.setMouseTracking(True)

    def serialize_points(self):
        """Convert QPointF list into serializable list of tuples."""
        return [(point.x(), point.y()) for point in self.points]

    def deserialize_points(self, data):
        """Convert list of (x, y) tuples back into QPointF points."""
        if isinstance(data, list):
            try:
                self.points = [QPointF(float(x), float(y)) for x, y in data]
                self.dirty = True
                self.update()
            except Exception as e:
                print(f"Failed to load curve points: {e}")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        graph_rect = self.rect().adjusted(0, 0, 0, 0)
        painter.fillRect(graph_rect, self.palette().window())

        painter.setPen(QPen(self.palette().text().color(), 2))
        painter.drawRect(self.margin, self.margin, self.graph_width, self.graph_height)

        # Draw curve lines
        painter.setPen(QPen(self.palette().text().color(), 2))
        for i in range(len(self.points) - 1):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            painter.drawLine(p1, p2)

        # Draw control points
        painter.setPen(QPen(self.palette().text().color(), 2))
        painter.setBrush(self.palette().highlight().color())
        for p in self.points:
            painter.drawEllipse(p, self.point_radius, self.point_radius)

        painter.setPen(QPen(self.palette().text().color()))
        painter.drawText(
            self.margin,
            self.margin + self.graph_height + 30,
            "Left-click + drag to move. Double-click to add. Right-click to delete.",
        )
        painter.drawText(
            self.margin,
            self.margin + self.graph_height + 50,
            "Keep window open to apply curve.",
        )

        if self.current_input is not None:
            x = self.margin + (self.current_input / 32767) * self.graph_width

            # Interpolate Y position based on self.points
            y = self.interpolate_y_from_points(self.current_input)

            if y is not None:
                painter.setBrush(QColor("green"))
                painter.setPen(QPen(self.palette().text().color()))
                painter.drawEllipse(QPointF(x, y), self.point_radius, self.point_radius)

    def clear_current_input(self):
        self.current_input = None
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        pos = event.position()
        for i, point in enumerate(self.points):
            if (point - pos).manhattanLength() < self.point_radius * 2:
                if event.button() == Qt.MouseButton.RightButton:
                    # Prevent deleting endpoints
                    if i != 0 and i != len(self.points) - 1:
                        del self.points[i]
                        self.dirty = True
                        self.update()
                    return
                elif event.button() == Qt.MouseButton.LeftButton:
                    self.dragging_point_index = i
                    return

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging_point_index is not None:
            pos = event.position()
            # Lock X position for endpoints
            if self.dragging_point_index == 0:
                x = self.margin
            elif self.dragging_point_index == len(self.points) - 1:
                x = self.margin + self.graph_width
            else:
                # Clamp x between neighbors
                left_x = self.points[self.dragging_point_index - 1].x()
                right_x = self.points[self.dragging_point_index + 1].x()
                x = min(max(pos.x(), left_x + 1), right_x - 1)

            # Clamp y within graph
            y = min(max(pos.y(), self.margin), self.margin + self.graph_height)
            self.points[self.dragging_point_index] = QPointF(x, y)
            self.dirty = True
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.dragging_point_index = None

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.position()

        for i in range(len(self.points) - 1):
            a = self.points[i]
            b = self.points[i + 1]
            if self.is_point_near_line(pos, a, b):
                new_x = min(max(pos.x(), a.x() + 1), b.x() - 1)
                ratio = (new_x - a.x()) / (b.x() - a.x())
                new_y = a.y() + ratio * (b.y() - a.y())
                self.points.insert(i + 1, QPointF(new_x, new_y))
                self.dirty = True
                self.update()
                break

    def get_or_build_curve_mapping(self):
        if self.dirty:
            self.curve_mapping = self.build_curve_mapping()
            self.dirty = False
        return self.curve_mapping

    def build_curve_mapping(self):
        mapping = []
        for p in self.points:
            input_x = ((p.x() - self.margin) / self.graph_width) * 32767
            output_y = (
                ((self.margin + self.graph_height) - p.y()) / self.graph_height * 32767
            )
            mapping.append((int(input_x), int(output_y)))
        return mapping

    def is_point_near_line(self, p, a, b, tolerance=5):
        ax, ay = a.x(), a.y()
        bx, by = b.x(), b.y()
        px, py = p.x(), p.y()

        ABx = bx - ax
        ABy = by - ay

        APx = px - ax
        APy = py - ay

        ab_squared = ABx**2 + ABy**2
        if ab_squared == 0:
            return (p - a).manhattanLength() < tolerance

        t = max(0, min(1, (APx * ABx + APy * ABy) / ab_squared))

        closest_x = ax + t * ABx
        closest_y = ay + t * ABy

        dist = ((px - closest_x) ** 2 + (py - closest_y) ** 2) ** 0.5
        return dist < tolerance

    def set_current_input(self, input_value: int) -> None:
        self.current_input = input_value
        self.update()

    def interpolate_y_from_points(self, input_val: int) -> float | None:
        """Given an input value (0-32767), return the Y position for the green dot."""
        px = self.margin + (input_val / 32767) * self.graph_width

        for i in range(len(self.points) - 1):
            x1 = self.points[i].x()
            x2 = self.points[i + 1].x()
            y1 = self.points[i].y()
            y2 = self.points[i + 1].y()

            if x1 <= px <= x2:
                t = (px - x1) / (x2 - x1)
                return y1 + t * (y2 - y1)

        return None


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    editor = CurveEditorWindow()
    editor.show()
    sys.exit(app.exec())

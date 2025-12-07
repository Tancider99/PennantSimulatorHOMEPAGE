# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Chart Widgets
OOTP-Style Visualization Components
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygon, QLinearGradient

import math
import sys
sys.path.insert(0, '..')
from UI.theme import get_theme, Theme


class RadarChart(QWidget):
    """Radar/Spider chart for player abilities (Power Pro style)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.data = {}
        self.labels = []
        self.max_value = 99
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_data(self, data: dict, max_value: int = 99):
        """Set chart data: {"label": value, ...}"""
        self.data = data
        self.labels = list(data.keys())
        self.max_value = max_value
        self.update()

    def set_player_stats(self, player, is_pitcher: bool = False):
        """Set data from player stats"""
        stats = player.stats
        if is_pitcher:
            data = {
                "球速": stats.speed,
                "制球": stats.control,
                "スタミナ": stats.stamina,
                "変化球": stats.breaking,
                "メンタル": stats.mental,
            }
        else:
            data = {
                "ミート": stats.contact,
                "パワー": stats.power,
                "走力": stats.run,
                "肩力": stats.arm,
                "守備": stats.fielding,
                "捕球": stats.catching,
            }
        self.set_data(data)

    def paintEvent(self, event):
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Calculate dimensions
        width = self.width()
        height = self.height()
        center_x = width // 2
        center_y = height // 2
        radius = min(width, height) // 2 - 40

        n = len(self.labels)
        if n < 3:
            return

        angle_step = 2 * math.pi / n

        # Draw background circles
        self._draw_background(painter, center_x, center_y, radius, n)

        # Draw axes
        self._draw_axes(painter, center_x, center_y, radius, n, angle_step)

        # Draw data polygon
        self._draw_data_polygon(painter, center_x, center_y, radius, angle_step)

        # Draw labels
        self._draw_labels(painter, center_x, center_y, radius, angle_step)

        # Draw value labels
        self._draw_values(painter, center_x, center_y, radius, angle_step)

    def _draw_background(self, painter: QPainter, cx: int, cy: int, radius: int, n: int):
        """Draw concentric background circles"""
        levels = [0.2, 0.4, 0.6, 0.8, 1.0]

        for level in levels:
            r = int(radius * level)
            painter.setPen(QPen(QColor(self.theme.border_muted), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPoint(cx, cy), r, r)

    def _draw_axes(self, painter: QPainter, cx: int, cy: int, radius: int, n: int, angle_step: float):
        """Draw axis lines from center"""
        painter.setPen(QPen(QColor(self.theme.border), 1))

        for i in range(n):
            angle = -math.pi / 2 + i * angle_step
            x = cx + int(radius * math.cos(angle))
            y = cy + int(radius * math.sin(angle))
            painter.drawLine(cx, cy, x, y)

    def _draw_data_polygon(self, painter: QPainter, cx: int, cy: int, radius: int, angle_step: float):
        """Draw the data polygon with gradient fill"""
        points = []
        n = len(self.labels)

        for i, label in enumerate(self.labels):
            value = self.data.get(label, 0)
            normalized = value / self.max_value
            angle = -math.pi / 2 + i * angle_step
            r = int(radius * normalized)
            x = cx + int(r * math.cos(angle))
            y = cy + int(r * math.sin(angle))
            points.append(QPoint(x, y))

        if points:
            polygon = QPolygon(points)

            # Fill with semi-transparent gradient
            gradient = QLinearGradient(cx - radius, cy - radius, cx + radius, cy + radius)
            gradient.setColorAt(0, QColor(self.theme.primary + "80"))
            gradient.setColorAt(1, QColor(self.theme.primary_dark + "60"))

            painter.setBrush(QBrush(gradient))
            painter.setPen(QPen(QColor(self.theme.primary), 2))
            painter.drawPolygon(polygon)

            # Draw points
            painter.setBrush(QBrush(QColor(self.theme.primary_light)))
            painter.setPen(QPen(QColor("white"), 2))
            for point in points:
                # 【修正】点のサイズを 5,5 から 3,3 に変更
                painter.drawEllipse(point, 3, 3)

    def _draw_labels(self, painter: QPainter, cx: int, cy: int, radius: int, angle_step: float):
        """Draw labels around the chart"""
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(self.theme.text_primary))

        label_radius = radius + 25

        for i, label in enumerate(self.labels):
            angle = -math.pi / 2 + i * angle_step
            x = cx + int(label_radius * math.cos(angle))
            y = cy + int(label_radius * math.sin(angle))

            # Adjust text position based on angle
            text_rect = painter.fontMetrics().boundingRect(label)
            x -= text_rect.width() // 2
            y += text_rect.height() // 4

            painter.drawText(x, y, label)

    def _draw_values(self, painter: QPainter, cx: int, cy: int, radius: int, angle_step: float):
        """Draw value labels on each point"""
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)

        for i, label in enumerate(self.labels):
            value = self.data.get(label, 0)
            normalized = value / self.max_value
            angle = -math.pi / 2 + i * angle_step
            r = int(radius * normalized) + 15  # Offset from point

            x = cx + int(r * math.cos(angle))
            y = cy + int(r * math.sin(angle))

            # Color based on rating
            color = Theme.get_rating_color(value)
            rank = Theme.get_rating_rank(value)

            # Draw background
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x - 12, y - 10, 24, 18, 4, 4)

            # Draw rank text
            painter.setPen(QColor("white"))
            text_rect = painter.fontMetrics().boundingRect(rank)
            painter.drawText(x - text_rect.width() // 2, y + text_rect.height() // 4, rank)


class BarChart(QWidget):
    """Horizontal bar chart for stat comparison"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.data = []  # [(label, value, max_value), ...]
        self.bar_height = 28
        self.setMinimumHeight(100)

    def set_data(self, data: list):
        """Set data: [(label, value, max_value), ...]"""
        self.data = data
        self.setMinimumHeight(len(data) * (self.bar_height + 8) + 20)
        self.update()

    def paintEvent(self, event):
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        label_width = 80
        bar_start = label_width + 10
        bar_width = width - bar_start - 50

        y = 10
        for label, value, max_value in self.data:
            # Draw label
            painter.setPen(QColor(self.theme.text_secondary))
            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(0, y + self.bar_height - 8, label)

            # Draw background bar
            bg_rect = QRect(bar_start, y, bar_width, self.bar_height)
            painter.setBrush(QBrush(QColor(self.theme.bg_input)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(bg_rect, 4, 4)

            # Draw value bar
            if max_value > 0:
                fill_width = int(bar_width * (value / max_value))
                fill_rect = QRect(bar_start, y, fill_width, self.bar_height)

                # Gradient fill
                gradient = QLinearGradient(bar_start, 0, bar_start + fill_width, 0)
                color = Theme.get_rating_color(int(value / max_value * 99))
                gradient.setColorAt(0, QColor(color))
                gradient.setColorAt(1, QColor(color).darker(120))

                painter.setBrush(QBrush(gradient))
                painter.drawRoundedRect(fill_rect, 4, 4)

            # Draw value text
            painter.setPen(QColor(self.theme.text_primary))
            font.setBold(True)
            painter.setFont(font)
            value_text = f"{value}"
            painter.drawText(bar_start + bar_width + 10, y + self.bar_height - 8, value_text)

            y += self.bar_height + 8


class MiniLineChart(QWidget):
    """Small line chart for trends (win streak, etc.)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.data = []  # List of values
        self.setMinimumSize(100, 40)
        self.setMaximumHeight(60)

    def set_data(self, data: list):
        """Set data points"""
        self.data = data
        self.update()

    def paintEvent(self, event):
        if len(self.data) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        padding = 5

        min_val = min(self.data)
        max_val = max(self.data)
        range_val = max_val - min_val if max_val != min_val else 1

        # Calculate points
        points = []
        n = len(self.data)
        for i, value in enumerate(self.data):
            x = padding + int((width - 2 * padding) * i / (n - 1))
            y = height - padding - int((height - 2 * padding) * (value - min_val) / range_val)
            points.append(QPoint(x, y))

        # Draw line
        painter.setPen(QPen(QColor(self.theme.primary), 2))
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])

        # Draw points
        painter.setBrush(QBrush(QColor(self.theme.primary)))
        for point in points:
            painter.drawEllipse(point, 3, 3)

        # Highlight last point
        if points:
            last_point = points[-1]
            painter.setBrush(QBrush(QColor(self.theme.primary_light)))
            painter.drawEllipse(last_point, 5, 5)


class PieChart(QWidget):
    """Pie chart for distribution data"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.data = []  # [(label, value, color), ...]
        self.setMinimumSize(150, 150)

    def set_data(self, data: list):
        """Set data: [(label, value, color), ...]"""
        self.data = data
        self.update()

    def paintEvent(self, event):
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        size = min(width, height) - 20
        x = (width - size) // 2
        y = (height - size) // 2
        rect = QRect(x, y, size, size)

        total = sum(item[1] for item in self.data)
        if total == 0:
            return

        start_angle = 90 * 16  # Start from top

        for label, value, color in self.data:
            span_angle = int(360 * 16 * value / total)

            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(QPen(QColor(self.theme.bg_card), 2))
            painter.drawPie(rect, start_angle, -span_angle)

            start_angle -= span_angle


class StatMeter(QWidget):
    """Vertical stat meter like Power Pro"""

    def __init__(self, label: str = "", parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.label = label
        self.value = 0
        self.max_value = 99
        self.setFixedSize(50, 120)

    def set_value(self, value: int, max_value: int = 99):
        self.value = value
        self.max_value = max_value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        # Draw label
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QColor(self.theme.text_secondary))
        text_rect = painter.fontMetrics().boundingRect(self.label)
        painter.drawText((width - text_rect.width()) // 2, height - 5, self.label)

        # Meter dimensions
        meter_x = (width - 30) // 2
        meter_y = 10
        meter_width = 30
        meter_height = height - 40

        # Draw background
        painter.setBrush(QBrush(QColor(self.theme.bg_input)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(meter_x, meter_y, meter_width, meter_height, 6, 6)

        # Draw fill
        if self.max_value > 0:
            fill_height = int(meter_height * self.value / self.max_value)
            fill_y = meter_y + meter_height - fill_height

            color = Theme.get_rating_color(self.value)
            gradient = QLinearGradient(0, fill_y, 0, meter_y + meter_height)
            gradient.setColorAt(0, QColor(color))
            gradient.setColorAt(1, QColor(color).darker(130))

            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(meter_x, fill_y, meter_width, fill_height, 6, 6)

        # Draw rank badge
        rank = Theme.get_rating_rank(self.value)
        color = Theme.get_rating_color(self.value)

        badge_size = 24
        badge_x = (width - badge_size) // 2
        badge_y = meter_y + meter_height + 5

        painter.setBrush(QBrush(QColor(color)))
        painter.drawRoundedRect(badge_x, badge_y, badge_size, badge_size, 4, 4)

        painter.setPen(QColor("white"))
        font.setBold(True)
        font.setPointSize(11)
        painter.setFont(font)
        painter.drawText(badge_x, badge_y, badge_size, badge_size, Qt.AlignCenter, rank)

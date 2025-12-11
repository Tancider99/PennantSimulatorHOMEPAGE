# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Chart Widgets
Custom Visualization Components (Unified Design)
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QRect, QPoint, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPolygon, QPolygonF, 
    QLinearGradient, QPainterPath, QRadialGradient
)

import math
import sys
# UI.theme がインポートできない場合の対策
try:
    from UI.theme import get_theme, Theme
except ImportError:
    pass

class RadarChart(QWidget):
    """
    Unified Radar Chart (MLB The Show Style)
    - Polygon Grid
    - No Center Text
    - No Vertex Dots
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.theme = get_theme()
        except:
            pass # フォールバックが必要なら実装
            
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
        """Set data from player stats (Optimized for visualization)"""
        stats = player.stats
        if is_pitcher:
            # 投手: Velocity, Control, Break, Stamina, Fielding, Clutch
            # 球速はスケーリング (130->40, 160->100)
            vel_rate = min(99, max(0, (stats.velocity - 130) * 2 + 40))
            data = {
                "VEL": vel_rate,        # 球速
                "CTRL": stats.control,  # 制球
                "BRK": stats.stuff,     # 変化球 (Stuff)
                "STM": stats.stamina,   # スタミナ
                "FLD": stats.fielding,  # 守備
                "CLU": stats.vs_pinch   # 対ピンチ
            }
        else:
            # 野手: Contact, Power, Speed, Fielding, Arm, Vision
            data = {
                "CON": stats.contact,   # ミート
                "POW": stats.power,     # パワー
                "SPD": stats.speed,     # 走力
                "FLD": stats.fielding,  # 守備
                "ARM": stats.arm,       # 肩力
                "VIS": stats.eye        # 選球眼
            }
        self.set_data(data)

    def paintEvent(self, event):
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2
        cy = h / 2
        radius = min(w, h) / 2 - 30 # マージン

        n = len(self.labels)
        if n < 3: return

        angle_step = 2 * math.pi / n
        start_angle = -math.pi / 2 

        # 1. グリッド描画 (多角形)
        grid_levels = [0.2, 0.4, 0.6, 0.8, 1.0]
        painter.setBrush(Qt.NoBrush)
        
        for level in grid_levels:
            r = radius * level
            points = []
            for i in range(n):
                angle = start_angle + i * angle_step
                p = QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle))
                points.append(p)
            
            # 外枠は少し太く、内側は薄く
            if level == 1.0:
                painter.setPen(QPen(QColor("#666"), 2))
            else:
                painter.setPen(QPen(QColor("#333"), 1))
            
            painter.drawPolygon(QPolygonF(points))

        # 軸線
        painter.setPen(QPen(QColor("#444"), 1))
        for i in range(n):
            angle = start_angle + i * angle_step
            p = QPointF(cx + radius * math.cos(angle), cy + radius * math.sin(angle))
            painter.drawLine(QPointF(cx, cy), p)

        # 2. データエリア描画
        data_points = []
        values = list(self.data.values())
        
        for i, val in enumerate(values):
            angle = start_angle + i * angle_step
            # 視認性のため最低10%は確保
            val_ratio = max(0.1, val / float(self.max_value))
            r = radius * val_ratio
            p = QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle))
            data_points.append(p)

        if data_points:
            path = QPainterPath()
            path.addPolygon(QPolygonF(data_points))
            
            # グラデーション塗り
            base_color = QColor(self.theme.accent_blue)
            painter.setBrush(QColor(base_color.red(), base_color.green(), base_color.blue(), 100)) # 半透明
            painter.setPen(QPen(base_color, 3))
            painter.drawPath(path)
            
            # 頂点マーカーは削除 (要望により)

        # 3. ラベル描画
        painter.setPen(QColor(self.theme.text_secondary))
        font = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(font)
        label_offset = 20
        
        for i, label in enumerate(self.labels):
            angle = start_angle + i * angle_step
            lx = cx + (radius + label_offset) * math.cos(angle)
            ly = cy + (radius + label_offset) * math.sin(angle)
            
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(label)
            th = fm.height()
            
            # 中心位置補正
            painter.drawText(int(lx - tw/2), int(ly + th/4), label)

        # 中央の数値表示は削除 (要望により)


class BarChart(QWidget):
    """Horizontal bar chart for stat comparison"""

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.theme = get_theme()
        except: pass
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
                # Theme依存回避の簡易実装
                color = "#5fbcd3"
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
    """Small line chart for trends"""
    def __init__(self, parent=None):
        super().__init__(parent)
        try: self.theme = get_theme()
        except: pass
        self.data = []
        self.setMinimumSize(100, 40)
        self.setMaximumHeight(60)

    def set_data(self, data: list):
        self.data = data
        self.update()

    def paintEvent(self, event):
        if len(self.data) < 2: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        padding = 5
        min_val = min(self.data)
        max_val = max(self.data)
        rng = max_val - min_val if max_val != min_val else 1
        points = []
        n = len(self.data)
        for i, v in enumerate(self.data):
            x = padding + int((w - 2*padding) * i / (n - 1))
            y = h - padding - int((h - 2*padding) * (v - min_val) / rng)
            points.append(QPoint(x, y))
        painter.setPen(QPen(QColor(self.theme.primary), 2))
        for i in range(len(points)-1):
            painter.drawLine(points[i], points[i+1])
        painter.setBrush(QBrush(QColor(self.theme.primary)))
        for p in points: painter.drawEllipse(p, 3, 3)


class PieChart(QWidget):
    """Pie chart"""
    def __init__(self, parent=None):
        super().__init__(parent)
        try: self.theme = get_theme()
        except: pass
        self.data = []
        self.setMinimumSize(150, 150)

    def set_data(self, data: list):
        self.data = data
        self.update()

    def paintEvent(self, event):
        if not self.data: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        s = min(w, h) - 20
        rect = QRect((w-s)//2, (h-s)//2, s, s)
        total = sum(d[1] for d in self.data)
        if total == 0: return
        start = 90 * 16
        for lbl, val, col in self.data:
            span = int(360 * 16 * val / total)
            painter.setBrush(QBrush(QColor(col)))
            painter.setPen(QPen(QColor(self.theme.bg_card), 2))
            painter.drawPie(rect, start, -span)
            start -= span


class StatMeter(QWidget):
    """Vertical stat meter"""
    def __init__(self, label: str = "", parent=None):
        super().__init__(parent)
        try: self.theme = get_theme()
        except: pass
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
        w, h = self.width(), self.height()
        
        # Label
        painter.setPen(QColor(self.theme.text_secondary))
        painter.drawText(QRect(0, h-15, w, 15), Qt.AlignCenter, self.label)
        
        # Meter
        mx = (w-30)//2
        my = 10
        mw = 30
        mh = h - 30
        painter.setBrush(QBrush(QColor(self.theme.bg_input)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(mx, my, mw, mh, 4, 4)
        
        if self.max_value > 0:
            fh = int(mh * self.value / self.max_value)
            fy = my + mh - fh
            # 簡易色設定
            col = "#5fbcd3"
            painter.setBrush(QBrush(QColor(col)))
            painter.drawRoundedRect(mx, fy, mw, fh, 4, 4)
# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Finance Page
Dashboard Style with Tabs, Stats Cards, and Charts
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QFrame, QPushButton, QScrollArea, QDialog, QSpinBox, QButtonGroup
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme


def format_yen(val: int) -> str:
    oku = val // 100000000
    man = (val % 100000000) // 10000
    if oku > 0:
        if man > 0:
            return f"{oku}億{man}万"
        return f"{oku}億"
    return f"{man}万"


class StatCard(QFrame):
    """Large stat card with title, main value, and details"""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        self.title = QLabel(title)
        self.title.setStyleSheet(f"font-size: 11px; color: {self.theme.text_muted}; font-weight: 600;")
        layout.addWidget(self.title)
        
        self.main_value = QLabel("---")
        self.main_value.setStyleSheet(f"font-size: 32px; font-weight: 800; color: {self.theme.primary};")
        layout.addWidget(self.main_value)
        
        self.sub_text = QLabel("")
        self.sub_text.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted};")
        layout.addWidget(self.sub_text)
        
        self.details_layout = QVBoxLayout()
        self.details_layout.setSpacing(4)
        layout.addLayout(self.details_layout)
    
    def set_main_value(self, val: str, color: str = None):
        self.main_value.setText(val)
        if color:
            self.main_value.setStyleSheet(f"font-size: 32px; font-weight: 800; color: {color};")
    
    def set_sub_text(self, text: str, color: str = None):
        self.sub_text.setText(text)
        c = color or self.theme.text_muted
        self.sub_text.setStyleSheet(f"font-size: 10px; color: {c};")
    
    def add_detail(self, label: str, value: str, color: str = None):
        row = QHBoxLayout()
        row.setSpacing(0)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 10px; color: {self.theme.text_secondary};")
        row.addWidget(lbl)
        row.addStretch()
        val = QLabel(value)
        c = color or self.theme.text_primary
        val.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {c};")
        row.addWidget(val)
        self.details_layout.addLayout(row)


class CircleChart(QFrame):
    """Circular progress chart"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.percentage = 65
        self.label = "使用率"
        self.setMinimumSize(100, 100)
        self.setStyleSheet("background: transparent;")
    
    def set_percentage(self, pct: int, label: str = ""):
        self.percentage = max(0, min(100, pct))
        if label:
            self.label = label
        self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        size = min(w, h) - 20
        x = (w - size) // 2
        y = (h - size) // 2
        
        # Background circle
        painter.setPen(QPen(QColor(self.theme.border), 8))
        painter.drawArc(x, y, size, size, 0, 360 * 16)
        
        # Progress arc
        painter.setPen(QPen(QColor(self.theme.success), 8))
        painter.drawArc(x, y, size, size, 90 * 16, -int(self.percentage * 3.6 * 16))
        
        # Center text
        painter.setPen(QColor(self.theme.text_primary))
        painter.setFont(painter.font())
        painter.drawText(x, y, size, size, Qt.AlignCenter, f"{self.percentage}%")
        
        # Label below
        painter.setPen(QColor(self.theme.text_muted))
        painter.drawText(x, y + size // 2 + 15, size, 20, Qt.AlignCenter, self.label)


class LineChart(QFrame):
    """Simple line chart"""
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.title = title
        self.data = []
        self.setMinimumHeight(120)
        self.setStyleSheet(f"background: {self.theme.bg_card};")
    
    def set_data(self, data: list, title: str = ""):
        """data = [(label, value), ...]"""
        self.data = data
        if title:
            self.title = title
        self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        margin = 40
        chart_w = w - margin * 2
        chart_h = h - 50
        
        # Title
        painter.setPen(QColor(self.theme.text_muted))
        painter.drawText(margin, 5, chart_w, 20, Qt.AlignCenter, self.title)
        
        if not self.data:
            return
        
        max_val = max(d[1] for d in self.data) if self.data else 1
        min_val = min(d[1] for d in self.data) if self.data else 0
        val_range = max_val - min_val if max_val != min_val else 1
        
        # Grid lines
        painter.setPen(QPen(QColor(self.theme.border), 1))
        for i in range(5):
            y = 25 + int(i * chart_h / 4)
            painter.drawLine(margin, y, w - margin, y)
        
        # Line path
        path = QPainterPath()
        points = []
        
        for i, (label, value) in enumerate(self.data):
            x = margin + int(i * chart_w / (len(self.data) - 1)) if len(self.data) > 1 else margin
            y = 25 + int((1 - (value - min_val) / val_range) * chart_h)
            points.append((x, y))
            
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        
        # Draw line
        painter.setPen(QPen(QColor(self.theme.primary), 2))
        painter.drawPath(path)
        
        # Draw points
        painter.setBrush(QBrush(QColor(self.theme.primary)))
        for x, y in points:
            painter.drawEllipse(x - 3, y - 3, 6, 6)
        
        # X-axis labels
        painter.setPen(QColor(self.theme.text_muted))
        for i, (label, _) in enumerate(self.data):
            if i % 2 == 0:
                x = margin + int(i * chart_w / (len(self.data) - 1)) if len(self.data) > 1 else margin
                painter.drawText(x - 20, h - 15, 40, 15, Qt.AlignCenter, label[:3])


class FinancePage(QWidget):
    """Finance Dashboard Page"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.current_team = None
        self.current_tab = 0
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"background: {self.theme.bg_dark};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # === ヘッダー + タブ ===
        header = QFrame()
        header.setStyleSheet(f"background: {self.theme.bg_card}; border-bottom: 1px solid {self.theme.border};")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 0)
        header_layout.setSpacing(8)
        
        title_row = QHBoxLayout()
        title = QLabel("FINANCE")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.theme.text_primary}; letter-spacing: 2px;")
        title_row.addWidget(title)
        title_row.addStretch()
        header_layout.addLayout(title_row)
        
        # タブ
        tabs_row = QHBoxLayout()
        tabs_row.setSpacing(0)
        
        self.tab_buttons = []
        tabs = ["概要", "収入", "支出", "投資", "経営"]
        
        for i, tab_name in enumerate(tabs):
            btn = QPushButton(tab_name)
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {self.theme.text_muted};
                    border: none;
                    border-bottom: 2px solid transparent;
                    padding: 8px 16px;
                    font-size: 11px;
                }}
                QPushButton:checked {{
                    color: {self.theme.primary};
                    border-bottom: 2px solid {self.theme.primary};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    color: {self.theme.text_primary};
                }}
            """)
            btn.clicked.connect(lambda _, idx=i: self._switch_tab(idx))
            self.tab_buttons.append(btn)
            tabs_row.addWidget(btn)
        
        tabs_row.addStretch()
        header_layout.addLayout(tabs_row)
        layout.addWidget(header)
        
        # === メインコンテンツ ===
        self.content_stack = QVBoxLayout()
        self.content_stack.setContentsMargins(12, 12, 12, 12)
        self.content_stack.setSpacing(8)
        
        # 概要タブのコンテンツ
        self._create_overview_content()
        
        layout.addLayout(self.content_stack, 1)
    
    def _create_overview_content(self):
        # 上段: 3つのStatカード
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        
        # 現在の残高
        self.budget_card = StatCard("現在の資金")
        self.budget_card.set_main_value("50億", self.theme.primary)
        self.budget_card.set_sub_text("前年比 +5億", self.theme.success)
        top_row.addWidget(self.budget_card, 1)
        
        # 今期の収支
        self.income_card = StatCard("今期予想収入")
        self.income_card.set_main_value("45億", self.theme.success)
        self.income_card.add_detail("チケット収入", "12億", self.theme.success)
        self.income_card.add_detail("放映権", "10億", self.theme.success)
        self.income_card.add_detail("スポンサー", "15億", self.theme.success)
        self.income_card.add_detail("グッズ", "5億", self.theme.success)
        self.income_card.add_detail("その他", "3億", self.theme.success)
        top_row.addWidget(self.income_card, 1)
        
        # 予算使用率
        usage_card = QFrame()
        usage_card.setStyleSheet(f"background: {self.theme.bg_card};")
        usage_layout = QVBoxLayout(usage_card)
        usage_layout.setContentsMargins(16, 12, 16, 12)
        usage_layout.setSpacing(4)
        
        usage_title = QLabel("予算使用状況")
        usage_title.setStyleSheet(f"font-size: 11px; color: {self.theme.text_muted}; font-weight: 600;")
        usage_layout.addWidget(usage_title)
        
        self.usage_chart = CircleChart()
        self.usage_chart.set_percentage(65, "使用率")
        usage_layout.addWidget(self.usage_chart)
        
        usage_layout.addStretch()
        top_row.addWidget(usage_card, 1)
        
        self.content_stack.addLayout(top_row)
        
        # 下段: 2つのLineChart
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)
        
        self.income_chart = LineChart("月別収入推移")
        self.income_chart.set_data([
            ("4月", 3), ("5月", 4), ("6月", 5), ("7月", 6),
            ("8月", 5), ("9月", 4), ("10月", 3), ("11月", 2)
        ])
        bottom_row.addWidget(self.income_chart, 1)
        
        self.expense_chart = LineChart("月別支出推移")
        self.expense_chart.set_data([
            ("4月", 4), ("5月", 3), ("6月", 3), ("7月", 4),
            ("8月", 4), ("9月", 3), ("10月", 3), ("11月", 3)
        ])
        bottom_row.addWidget(self.expense_chart, 1)
        
        self.content_stack.addLayout(bottom_row, 1)
    
    def _switch_tab(self, idx: int):
        for i, btn in enumerate(self.tab_buttons):
            btn.setChecked(i == idx)
        self.current_tab = idx
        # TODO: タブ切り替え時のコンテンツ変更
    
    def set_game_state(self, game_state):
        self.game_state = game_state
        if game_state:
            self.current_team = game_state.player_team
            self._update_display()
    
    def _update_display(self):
        if not self.current_team:
            return
        
        budget = getattr(self.current_team, 'budget', 5000000000)
        total_salary = sum(getattr(p, 'salary', 10000000) for p in self.current_team.players)
        
        self.budget_card.set_main_value(format_yen(budget))
        
        usage = int((total_salary / budget) * 100) if budget > 0 else 0
        self.usage_chart.set_percentage(usage)
    
    def refresh(self):
        self._update_display()

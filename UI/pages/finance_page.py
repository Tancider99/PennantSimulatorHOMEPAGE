# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Finance Page
Three-tier fan system with management and investment commands
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QFrame, QPushButton, QScrollArea, QDialog, QSpinBox, QSlider,
    QDialogButtonBox, QComboBox
)
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPolygon, QFont
from PySide6.QtCore import QPoint

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


def format_fan_count(val: int) -> str:
    """ファン数を万単位でフォーマット（数値万表記）"""
    man = val / 10000
    if man >= 1:
        return f"{man:.0f}万"
    return f"{val:,}"


class TriangleButton(QPushButton):
    """Triangle-shaped button (left or right)"""
    def __init__(self, direction: str = "left", parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.direction = direction
        self.setFixedSize(24, 24)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")
        self._hovered = False
    
    def enterEvent(self, event):
        self._hovered = True
        self.update()
    
    def leaveEvent(self, event):
        self._hovered = False
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        color = QColor(self.theme.primary) if self._hovered else QColor(self.theme.text_muted)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        
        w, h = self.width(), self.height()
        if self.direction == "left":
            points = [QPoint(w-4, 4), QPoint(w-4, h-4), QPoint(4, h//2)]
        else:
            points = [QPoint(4, 4), QPoint(4, h-4), QPoint(w-4, h//2)]
        
        painter.drawPolygon(QPolygon(points))


class DonutChart(QWidget):
    """Modern donut chart showing fan tier percentages"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.setMinimumSize(180, 180)
        self.light = 0
        self.middle = 0
        self.core = 0
        self.total = 0
    
    def set_data(self, light: int, middle: int, core: int):
        self.light = light
        self.middle = middle
        self.core = core
        self.total = light + middle + core
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        center_x, center_y = w // 2, h // 2
        outer_radius = min(w, h) // 2 - 5
        inner_radius = outer_radius - 18
        
        # Colors for each tier
        colors = [
            QColor("#8BC34A"),  # Light - green
            QColor("#03A9F4"),  # Middle - blue
            QColor("#FF5722"),  # Core - orange
        ]
        values = [self.light, self.middle, self.core]
        
        # Draw donut segments
        if self.total > 0:
            start_angle = 90 * 16  # Start from top
            for i, val in enumerate(values):
                if val > 0:
                    span = int((val / self.total) * 360 * 16)
                    
                    painter.setBrush(QBrush(colors[i]))
                    painter.setPen(Qt.NoPen)
                    
                    # Draw arc as pie slice
                    rect = QRectF(center_x - outer_radius, center_y - outer_radius,
                                  outer_radius * 2, outer_radius * 2)
                    painter.drawPie(rect, start_angle, -span)
                    
                    start_angle -= span
        else:
            # Draw empty circle
            painter.setBrush(QBrush(QColor(self.theme.border)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(center_x - outer_radius, center_y - outer_radius,
                               outer_radius * 2, outer_radius * 2)
        
        # Draw inner circle (donut hole)
        painter.setBrush(QBrush(QColor(self.theme.bg_card)))
        painter.drawEllipse(center_x - inner_radius, center_y - inner_radius,
                           inner_radius * 2, inner_radius * 2)
        
        # Draw total in center
        painter.setPen(QColor(self.theme.text_primary))
        font = QFont()
        font.setPixelSize(14)
        font.setBold(True)
        painter.setFont(font)
        
        total_text = format_fan_count(self.total)
        text_rect = QRectF(center_x - inner_radius, center_y - 10, inner_radius * 2, 20)
        painter.drawText(text_rect, Qt.AlignCenter, total_text)
        
        # Draw label below
        font.setPixelSize(9)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor(self.theme.text_muted))
        label_rect = QRectF(center_x - inner_radius, center_y + 5, inner_radius * 2, 16)
        painter.drawText(label_rect, Qt.AlignCenter, "総ファン")


class StatCard(QFrame):
    """Angular stat card with title, main value, and details"""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        
        # Angular corners (no border-radius, no border)
        self.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)
        
        self.title = QLabel(title)
        self.title.setStyleSheet(f"font-size: 13px; color: {self.theme.text_muted}; font-weight: 600; border: none;")
        layout.addWidget(self.title)
        
        self.main_value = QLabel("---")
        self.main_value.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {self.theme.primary}; border: none;")
        layout.addWidget(self.main_value)
        
        self.details_layout = QVBoxLayout()
        self.details_layout.setSpacing(2)
        layout.addLayout(self.details_layout)
        layout.addStretch()
    
    def set_main_value(self, val: str, color: str = None):
        self.main_value.setText(val)
        if color:
            self.main_value.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {color}; border: none;")
    
    def clear_details(self):
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
    
    def add_detail(self, label: str, value: str, color: str = None, tooltip: str = None):
        row = QHBoxLayout()
        row.setSpacing(0)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 10px; color: {self.theme.text_secondary}; border: none;")
        if tooltip:
            lbl.setToolTip(tooltip)
            lbl.setCursor(Qt.WhatsThisCursor)
        row.addWidget(lbl)
        row.addStretch()
        val = QLabel(value)
        c = color or self.theme.text_primary
        val.setStyleSheet(f"font-size: 10px; font-weight: 600; color: {c}; border: none;")
        if tooltip:
            val.setToolTip(tooltip)
            val.setCursor(Qt.WhatsThisCursor)
        row.addWidget(val)
        self.details_layout.addLayout(row)


class FanTierCard(QFrame):
    """Angular fan tier display card with donut chart"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        
        self.setStyleSheet(f"background: {self.theme.bg_card};")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(20)
        
        # Left side: tier breakdown
        tier_layout = QVBoxLayout()
        tier_layout.setSpacing(10)
        
        tier_title = QLabel("ファン層別人口")
        tier_title.setStyleSheet(f"font-size: 14px; color: {self.theme.text_muted}; font-weight: 600;")
        tier_layout.addWidget(tier_title)
        
        self.light_label, self.light_pct = self._create_tier_row(tier_layout, "ライト層", "#8BC34A")
        self.middle_label, self.middle_pct = self._create_tier_row(tier_layout, "ミドル層", "#03A9F4")
        self.core_label, self.core_pct = self._create_tier_row(tier_layout, "コア層", "#FF5722")
        
        tier_layout.addStretch()
        layout.addLayout(tier_layout, 1)
        
        # Right side: donut chart (larger, takes half width)
        chart_container = QVBoxLayout()
        chart_container.setAlignment(Qt.AlignCenter)
        self.donut_chart = DonutChart()
        chart_container.addWidget(self.donut_chart)
        layout.addLayout(chart_container, 1)
    
    def _create_tier_row(self, parent_layout, name: str, color: str):
        row = QHBoxLayout()
        row.setSpacing(6)
        
        indicator = QLabel("■")
        indicator.setStyleSheet(f"color: {color}; font-size: 10px;")
        row.addWidget(indicator)
        
        label = QLabel(name)
        label.setStyleSheet(f"font-size: 11px; color: {self.theme.text_secondary};")
        row.addWidget(label)
        
        row.addStretch()
        
        value_label = QLabel("0万")
        value_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.theme.text_primary};")
        row.addWidget(value_label)
        
        pct_label = QLabel("(0%)")
        pct_label.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted};")
        pct_label.setMinimumWidth(40)
        row.addWidget(pct_label)
        
        parent_layout.addLayout(row)
        return value_label, pct_label
    
    def set_fans(self, light: int, middle: int, core: int):
        total = light + middle + core
        
        self.light_label.setText(format_fan_count(light))
        self.middle_label.setText(format_fan_count(middle))
        self.core_label.setText(format_fan_count(core))
        
        if total > 0:
            self.light_pct.setText(f"({light*100//total}%)")
            self.middle_pct.setText(f"({middle*100//total}%)")
            self.core_pct.setText(f"({core*100//total}%)")
        else:
            self.light_pct.setText("(0%)")
            self.middle_pct.setText("(0%)")
            self.core_pct.setText("(0%)")
        
        self.donut_chart.set_data(light, middle, core)


class FiveLevelControl(QFrame):
    """5-level control with label and triangle buttons"""
    value_changed = Signal(str, int)
    
    def __init__(self, name: str, initial_value: int = 3, level_names: list = None, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.name = name
        self.value = initial_value
        self.level_names = level_names or ["1", "2", "3", "4", "5"]
        
        self.setStyleSheet(f"background: transparent;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        
        label = QLabel(name)
        label.setStyleSheet(f"font-size: 11px; color: {self.theme.text_primary}; font-weight: 500;")
        label.setMinimumWidth(80)
        layout.addWidget(label)
        
        layout.addStretch()
        
        # Triangle buttons
        self.left_btn = TriangleButton("left")
        self.left_btn.clicked.connect(self._decrease)
        layout.addWidget(self.left_btn)
        
        self.value_label = QLabel(self.level_names[self.value - 1])
        self.value_label.setStyleSheet(f"font-size: 11px; color: {self.theme.primary}; font-weight: 700;")
        self.value_label.setMinimumWidth(40)
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)
        
        self.right_btn = TriangleButton("right")
        self.right_btn.clicked.connect(self._increase)
        layout.addWidget(self.right_btn)
    
    def _decrease(self):
        if self.value > 1:
            self.value -= 1
            self.value_label.setText(self.level_names[self.value - 1])
            self.value_changed.emit(self.name, self.value)
    
    def _increase(self):
        if self.value < 5:
            self.value += 1
            self.value_label.setText(self.level_names[self.value - 1])
            self.value_changed.emit(self.name, self.value)
    
    def set_value(self, val: int):
        self.value = max(1, min(5, val))
        self.value_label.setText(self.level_names[self.value - 1])


class ActionButton(QPushButton):
    """Styled action button with white-on-black hover"""
    def __init__(self, name: str, parent=None):
        super().__init__(name, parent)
        self.theme = get_theme()
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.bg_dark};
                color: {self.theme.text_primary};
                padding: 10px 14px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: white;
                color: black;
            }}
        """)


class StadiumDialog(QDialog):
    """New stadium construction dialog with dome option"""
    def __init__(self, current_stadium, budget, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.result_data = None
        
        self.setWindowTitle("新球場建設")
        self.setMinimumSize(450, 480)
        self.setStyleSheet(f"background: {self.theme.bg_dark}; color: {self.theme.text_primary};")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        
        # Title
        title = QLabel("新球場建設計画")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {self.theme.primary};")
        layout.addWidget(title)
        
        # Current stadium info
        dome_text = "ドーム" if (current_stadium and getattr(current_stadium, 'is_dome', False)) else "屋外"
        current_info = QLabel(f"現在の球場: {current_stadium.name if current_stadium else '不明'} ({dome_text})\n"
                             f"収容人数: {current_stadium.capacity if current_stadium else 0:,}人")
        current_info.setStyleSheet(f"color: {self.theme.text_muted};")
        layout.addWidget(current_info)
        
        # Dome option
        from PySide6.QtWidgets import QCheckBox
        dome_layout = QHBoxLayout()
        dome_label = QLabel("球場タイプ:")
        dome_label.setStyleSheet(f"font-size: 12px; font-weight: 600;")
        dome_layout.addWidget(dome_label)
        
        self.dome_check = QCheckBox("ドーム球場（雨天中止なし・観客+20%・維持費2倍）")
        self.dome_check.setStyleSheet(f"color: {self.theme.text_primary};")
        self.dome_check.stateChanged.connect(self._update_cost)
        dome_layout.addWidget(self.dome_check)
        layout.addLayout(dome_layout)
        
        # Capacity slider
        cap_layout = QVBoxLayout()
        cap_label = QLabel("観客席数")
        cap_label.setStyleSheet(f"font-size: 12px; font-weight: 600;")
        cap_layout.addWidget(cap_label)
        
        self.capacity_slider = QSlider(Qt.Horizontal)
        self.capacity_slider.setRange(10000, 100000)
        self.capacity_slider.setValue(40000)
        self.capacity_slider.setSingleStep(5000)
        self.capacity_slider.valueChanged.connect(self._update_cost)
        cap_layout.addWidget(self.capacity_slider)
        
        self.capacity_display = QLabel("40,000席")
        self.capacity_display.setStyleSheet(f"color: {self.theme.accent};")
        cap_layout.addWidget(self.capacity_display)
        layout.addLayout(cap_layout)
        
        # Field size (affects park factor, not cost)
        field_layout = QHBoxLayout()
        field_label = QLabel("フィールド広さ:")
        field_label.setStyleSheet(f"font-size: 12px; font-weight: 600;")
        field_layout.addWidget(field_label)
        
        self.field_combo = QComboBox()
        self.field_combo.addItems(["1 (狭い/HR有利)", "2 (やや狭い)", "3 (標準)", "4 (やや広い)", "5 (広い/投手有利)"])
        self.field_combo.setCurrentIndex(2)
        self.field_combo.currentIndexChanged.connect(self._update_pf_preview)
        field_layout.addWidget(self.field_combo)
        layout.addLayout(field_layout)
        
        # Park factor preview
        self.pf_label = QLabel("パークファクター: HR 1.0, 3B 1.0")
        self.pf_label.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 10px;")
        layout.addWidget(self.pf_label)
        
        # Cost display
        cost_frame = QFrame()
        cost_frame.setStyleSheet(f"background: {self.theme.bg_card};")
        cost_layout = QVBoxLayout(cost_frame)
        
        self.build_cost_label = QLabel("建設費: 300億円")
        self.build_cost_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {self.theme.error};")
        cost_layout.addWidget(self.build_cost_label)
        
        self.maintenance_label = QLabel("年間維持費: 4000万円")
        self.maintenance_label.setStyleSheet(f"color: {self.theme.text_muted};")
        cost_layout.addWidget(self.maintenance_label)
        
        self.budget_label = QLabel(f"現在の資金: {format_yen(budget)}")
        self.budget_label.setStyleSheet(f"color: {self.theme.text_secondary};")
        cost_layout.addWidget(self.budget_label)
        
        layout.addWidget(cost_frame)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self._update_cost()
        self._update_pf_preview()
    
    def _update_cost(self):
        capacity = self.capacity_slider.value()
        is_dome = self.dome_check.isChecked()
        
        self.capacity_display.setText(f"{capacity:,}席")
        
        # Build cost: 100億 + 500,000円/席
        build_cost = 10000000000 + capacity * 500000
        
        # Dome: +500億 + 席数に応じて10億～100億
        if is_dome:
            dome_extra = 50000000000 + int((capacity - 10000) / 90000 * 90000000000)
            build_cost += dome_extra
        
        # Maintenance preview
        maint = capacity * 1000
        if is_dome:
            maint *= 2
        
        self.build_cost_label.setText(f"建設費: {format_yen(build_cost)}")
        self.maintenance_label.setText(f"年間維持費: {format_yen(maint)}")
        
        field_size = self.field_combo.currentIndex() + 1
        
        self.result_data = {
            "capacity": capacity,
            "field_size": field_size,
            "is_dome": is_dome,
            "build_cost": build_cost
        }
    
    def _update_pf_preview(self):
        field_size = self.field_combo.currentIndex() + 1
        # フィールドサイズによるパークファクター
        hr_pf = 1.0 + (3 - field_size) * 0.1
        tb_pf = 1.0 + (field_size - 3) * 0.15
        self.pf_label.setText(f"パークファクター: HR {hr_pf:.2f}, 3B {tb_pf:.2f}")
        
        if self.result_data:
            self.result_data["field_size"] = field_size
    
    def _on_accept(self):
        self._update_cost()
        self.accept()


class EventDialog(QDialog):
    """Fan event hosting dialog"""
    def __init__(self, budget, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.event_cost = 10000000
        
        self.setWindowTitle("イベント開催")
        self.setMinimumSize(350, 250)
        self.setStyleSheet(f"background: {self.theme.bg_dark}; color: {self.theme.text_primary};")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        title = QLabel("ファンイベント開催")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {self.theme.primary};")
        layout.addWidget(title)
        
        desc = QLabel("イベントを開催してファンを増やします。\n費用が高いほど効果が大きくなります。")
        desc.setStyleSheet(f"color: {self.theme.text_muted};")
        layout.addWidget(desc)
        
        # Cost selection
        cost_layout = QHBoxLayout()
        cost_label = QLabel("開催費用:")
        cost_layout.addWidget(cost_label)
        
        self.cost_combo = QComboBox()
        self.cost_combo.addItems(["500万円", "1000万円", "2000万円", "5000万円", "1億円"])
        self.cost_values = [5000000, 10000000, 20000000, 50000000, 100000000]
        self.cost_combo.setCurrentIndex(1)
        self.cost_combo.currentIndexChanged.connect(self._update_effect)
        cost_layout.addWidget(self.cost_combo)
        layout.addLayout(cost_layout)
        
        self.effect_label = QLabel("効果: ライト層+5%, ミドル層+2%, コア層+1%")
        self.effect_label.setStyleSheet(f"color: {self.theme.success};")
        layout.addWidget(self.effect_label)
        
        budget_label = QLabel(f"現在の資金: {format_yen(budget)}")
        budget_label.setStyleSheet(f"color: {self.theme.text_secondary};")
        layout.addWidget(budget_label)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self._update_effect()
    
    def _update_effect(self):
        idx = self.cost_combo.currentIndex()
        self.event_cost = self.cost_values[idx]
        boost = self.event_cost / 10000000
        light = boost * 5
        middle = boost * 2
        core = boost * 1
        self.effect_label.setText(f"効果: ライト層+{light:.1f}%, ミドル層+{middle:.1f}%, コア層+{core:.1f}%")


class FinancePage(QWidget):
    """Finance Dashboard Page with Fan Tier System"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.current_team = None
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"background: {self.theme.bg_dark};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header (larger)
        header = QFrame()
        header.setStyleSheet(f"background: {self.theme.bg_card}; border-bottom: 1px solid {self.theme.border};")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        
        title = QLabel("FINANCE")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {self.theme.text_primary}; letter-spacing: 3px;")
        header_layout.addWidget(title)
        
        subtitle = QLabel("経営・投資管理")
        subtitle.setStyleSheet(f"font-size: 11px; color: {self.theme.text_muted};")
        header_layout.addWidget(subtitle)
        
        layout.addWidget(header)
        
        # Main content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        self.content_layout.setSpacing(12)
        
        self._create_content()
        
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
    
    def _create_content(self):
        # === Row 1: Budget + Income + Expense ===
        row1 = QHBoxLayout()
        row1.setSpacing(12)
        
        self.budget_card = StatCard("現在の資金")
        self.budget_card.set_main_value("50億", self.theme.primary)
        row1.addWidget(self.budget_card, 1)
        
        self.income_card = StatCard("今期収入")
        self.income_card.set_main_value("0", self.theme.success)
        row1.addWidget(self.income_card, 1)
        
        self.expense_card = StatCard("今期支出")
        self.expense_card.set_main_value("0", self.theme.error)
        row1.addWidget(self.expense_card, 1)
        
        self.content_layout.addLayout(row1)
        
        # === Row 2: Fan Tier with Donut Chart ===
        self.fan_card = FanTierCard()
        self.content_layout.addWidget(self.fan_card)
        
        # === Row 3: Management + Investment Commands ===
        row3 = QHBoxLayout()
        row3.setSpacing(12)
        
        # Management Commands
        mgmt_card = QFrame()
        mgmt_card.setStyleSheet(f"background: {self.theme.bg_card};")
        mgmt_layout = QVBoxLayout(mgmt_card)
        mgmt_layout.setContentsMargins(12, 10, 12, 10)
        mgmt_layout.setSpacing(4)
        
        mgmt_title = QLabel("経営コマンド")
        mgmt_title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {self.theme.text_primary};")
        mgmt_layout.addWidget(mgmt_title)
        
        level_names = ["最安", "安い", "標準", "高い", "最高"]
        
        self.broadcast_ctrl = FiveLevelControl("放映権価格", 3, level_names)
        self.broadcast_ctrl.value_changed.connect(self._on_management_changed)
        mgmt_layout.addWidget(self.broadcast_ctrl)
        
        self.ticket_ctrl = FiveLevelControl("チケット価格", 3, level_names)
        self.ticket_ctrl.value_changed.connect(self._on_management_changed)
        mgmt_layout.addWidget(self.ticket_ctrl)
        
        self.merch_ctrl = FiveLevelControl("グッズ価格", 3, level_names)
        self.merch_ctrl.value_changed.connect(self._on_management_changed)
        mgmt_layout.addWidget(self.merch_ctrl)
        
        # Daily stats for management
        sep1 = QFrame()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet(f"background: {self.theme.border};")
        mgmt_layout.addWidget(sep1)
        
        self.daily_revenue_label = QLabel("日次収益: 0")
        self.daily_revenue_label.setStyleSheet(f"font-size: 10px; color: {self.theme.success};")
        mgmt_layout.addWidget(self.daily_revenue_label)
        
        self.daily_fan_change_label = QLabel("日次ファン増減: 0")
        self.daily_fan_change_label.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted};")
        mgmt_layout.addWidget(self.daily_fan_change_label)
        
        row3.addWidget(mgmt_card, 1)
        
        # Investment Commands
        inv_card = QFrame()
        inv_card.setStyleSheet(f"background: {self.theme.bg_card};")
        inv_layout = QVBoxLayout(inv_card)
        inv_layout.setContentsMargins(12, 10, 12, 10)
        inv_layout.setSpacing(4)
        
        inv_title = QLabel("投資コマンド")
        inv_title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {self.theme.text_primary};")
        inv_layout.addWidget(inv_title)
        
        inv_level_names = ["最低", "低い", "標準", "高い", "最高"]
        
        self.training_ctrl = FiveLevelControl("練習設備", 3, inv_level_names)
        self.training_ctrl.value_changed.connect(self._on_investment_changed)
        inv_layout.addWidget(self.training_ctrl)
        
        self.medical_ctrl = FiveLevelControl("医療設備", 3, inv_level_names)
        self.medical_ctrl.value_changed.connect(self._on_investment_changed)
        inv_layout.addWidget(self.medical_ctrl)
        
        # Daily expense for investment
        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background: {self.theme.border};")
        inv_layout.addWidget(sep2)
        
        self.daily_expense_label = QLabel("日次支出: 0")
        self.daily_expense_label.setStyleSheet(f"font-size: 10px; color: {self.theme.error};")
        inv_layout.addWidget(self.daily_expense_label)
        
        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        
        self.stadium_btn = ActionButton("新球場建設")
        self.stadium_btn.clicked.connect(self._on_stadium_clicked)
        btn_row.addWidget(self.stadium_btn)
        
        self.event_btn = ActionButton("イベント開催")
        self.event_btn.clicked.connect(self._on_event_clicked)
        btn_row.addWidget(self.event_btn)
        
        inv_layout.addLayout(btn_row)
        
        row3.addWidget(inv_card, 1)
        
        self.content_layout.addLayout(row3, 1)
    
    def _calculate_daily_stats(self):
        """経営設定に基づく日次収益とファン増減を計算"""
        if not self.current_team:
            return 0, 0, 0
        
        finance = getattr(self.current_team, 'finance', None)
        settings = getattr(self.current_team, 'management_settings', None)
        inv_settings = getattr(self.current_team, 'investment_settings', None)
        
        if not finance or not settings:
            return 0, 0, 0
        
        fb = finance.fan_base
        
        # 日次収入計算
        broadcast_base = 3000000 + settings.broadcast_price * 1500000
        broadcast_mult = fb.total_fans / 500000
        daily_broadcast = int(broadcast_base * broadcast_mult)
        
        price_mult = 0.6 + settings.merchandise_price * 0.15
        daily_merch = int(
            fb.core_fans * 3 * price_mult +
            fb.middle_fans * 1 * price_mult +
            fb.light_fans * 0.3 * price_mult
        )
        
        daily_revenue = daily_broadcast + daily_merch
        
        # 日次ファン増減推定（勝率0.5想定）
        light_mod = (3 - settings.broadcast_price) * 0.0008
        middle_mod = (3 - settings.ticket_price) * 0.0005
        core_mod = (3 - settings.merchandise_price) * 0.0003
        
        daily_fan_change = int(
            fb.light_fans * light_mod +
            fb.middle_fans * middle_mod +
            fb.core_fans * core_mod
        )
        
        # 日次支出（設備維持費のみ）
        daily_expense = 0
        if inv_settings:
            annual_cost = inv_settings.get_training_cost() + inv_settings.get_medical_cost()
            daily_expense = annual_cost // 365
        
        return daily_revenue, daily_fan_change, daily_expense
    
    def _calculate_annual_estimates(self):
        """予想年間収入/支出を計算（シーズン+オフ約200日ベース）"""
        if not self.current_team:
            return 0, 0
        
        finance = getattr(self.current_team, 'finance', None)
        settings = getattr(self.current_team, 'management_settings', None)
        inv_settings = getattr(self.current_team, 'investment_settings', None)
        
        if not finance:
            return 0, 0
        if not settings:
            from models import ManagementSettings
            settings = ManagementSettings()
        if not inv_settings:
            from models import InvestmentSettings
            inv_settings = InvestmentSettings()
        
        fb = finance.fan_base
        season_days = 200  # シーズン+オフシーズン（ポストシーズン勝ち上がり分は日次加算で反映）
        
        # === 予想年間収入 ===
        # 放映権収入（日次 × シーズン日数）- ファン数の影響を減らす
        broadcast_base = 8000000 + settings.broadcast_price * 2000000  # 1000万〜1800万/日
        broadcast_mult = (fb.total_fans / 500000) ** 0.5  # 平方根で影響を緩やかに
        annual_broadcast = int(broadcast_base * broadcast_mult * season_days)
        
        # グッズ収入（日次 × シーズン日数）
        price_mult = 0.6 + settings.merchandise_price * 0.15
        daily_merch = int(
            fb.core_fans * 3 * price_mult +
            fb.middle_fans * 1 * price_mult +
            fb.light_fans * 0.3 * price_mult
        )
        annual_merch = daily_merch * season_days
        
        # スポンサー収入（日次 × シーズン日数）- ファン数の影響を減らす
        sponsor_mult = (fb.total_fans / 500000) ** 0.5  # 平方根で影響を緩やかに
        daily_sponsor = int(15000000 * sponsor_mult)  # 基本1500万円/日
        annual_sponsor = daily_sponsor * season_days
        
        # チケット収入（ホーム72試合 × 想定観客数 × チケット単価）
        # 最低80%動員率、ファン数に応じて最大100%
        stadium = getattr(self.current_team, 'stadium', None)
        capacity = stadium.capacity if stadium else 35000
        # ファン数に基づく動員率: 100万=85%, 300万=95%, 500万=100%
        fan_fill_rate = 0.80 + min(fb.total_fans / 5000000, 1.0) * 0.20
        avg_attendance = int(capacity * fan_fill_rate)
        ticket_unit_price = 2000 + settings.ticket_price * 300  # 2300〜3500円
        annual_ticket = avg_attendance * ticket_unit_price * 72
        
        estimated_annual_income = annual_broadcast + annual_merch + annual_sponsor + annual_ticket
        
        # === 予想年間支出 ===
        # 選手年俸
        total_player_salary = sum(getattr(p, 'salary', 10000000) for p in self.current_team.players)
        
        # スタッフ年俸
        total_staff_salary = sum(getattr(s, 'salary', 5000000) for s in self.current_team.staff) if hasattr(self.current_team, 'staff') else 0
        
        # 球場維持費（年間）
        stadium_maintenance = stadium.maintenance_cost if stadium else 40000000
        
        # 設備維持費（年間）
        facility_cost = inv_settings.get_training_cost() + inv_settings.get_medical_cost()
        
        # その他支出（遠征費、雑費等）：約100億円/年（基本40億円 + ファン数比例大）
        base_other = 20000000 * season_days  # 基本部分: 2000万円/日
        fan_based_other = int(fb.total_fans * 10 * season_days)  # ファン1人10円/日
        other_expense = base_other + fan_based_other
        
        estimated_annual_expense = total_player_salary + total_staff_salary + stadium_maintenance + facility_cost + other_expense
        
        return estimated_annual_income, estimated_annual_expense
    
    def _get_estimate_breakdowns(self):
        """予想年間収入・支出の内訳テキストを取得（ツールチップ用）"""
        if not self.current_team:
            return "", ""
        
        finance = getattr(self.current_team, 'finance', None)
        settings = getattr(self.current_team, 'management_settings', None)
        inv_settings = getattr(self.current_team, 'investment_settings', None)
        
        if not finance:
            return "", ""
        if not settings:
            from models import ManagementSettings
            settings = ManagementSettings()
        if not inv_settings:
            from models import InvestmentSettings
            inv_settings = InvestmentSettings()
        
        fb = finance.fan_base
        season_days = 200  # シーズン+オフシーズン
        
        # 収入内訳 - ファン数の影響を減らす
        broadcast_base = 8000000 + settings.broadcast_price * 2000000  # 1000万〜1800万/日
        broadcast_mult = (fb.total_fans / 500000) ** 0.5  # 平方根で影響を緩やかに
        annual_broadcast = int(broadcast_base * broadcast_mult * season_days)
        
        price_mult = 0.6 + settings.merchandise_price * 0.15
        daily_merch = int(
            fb.core_fans * 3 * price_mult +
            fb.middle_fans * 1 * price_mult +
            fb.light_fans * 0.3 * price_mult
        )
        annual_merch = daily_merch * season_days
        
        # スポンサー収入 - ファン数の影響を減らす
        sponsor_mult = (fb.total_fans / 500000) ** 0.5  # 平方根で影響を緩やかに
        daily_sponsor = int(15000000 * sponsor_mult)  # 基本1500万円/日
        annual_sponsor = daily_sponsor * season_days
        
        # チケット収入（最低80%動員率、ファン数に応じて最大100%）
        stadium = getattr(self.current_team, 'stadium', None)
        capacity = stadium.capacity if stadium else 35000
        fan_fill_rate = 0.80 + min(fb.total_fans / 5000000, 1.0) * 0.20
        avg_attendance = int(capacity * fan_fill_rate)
        ticket_unit_price = 2000 + settings.ticket_price * 300  # 2300〜3500円
        annual_ticket = avg_attendance * ticket_unit_price * 72
        
        income_breakdown = (
            f"【収入内訳】\n"
            f"放映権: {format_yen(annual_broadcast)}\n"
            f"グッズ: {format_yen(annual_merch)}\n"
            f"スポンサー: {format_yen(annual_sponsor)}\n"
            f"チケット: {format_yen(annual_ticket)}"
        )
        
        # 支出内訳
        total_player_salary = sum(getattr(p, 'salary', 10000000) for p in self.current_team.players)
        total_staff_salary = sum(getattr(s, 'salary', 5000000) for s in self.current_team.staff) if hasattr(self.current_team, 'staff') else 0
        stadium_maintenance = stadium.maintenance_cost if stadium else 40000000
        facility_cost = inv_settings.get_training_cost() + inv_settings.get_medical_cost()
        # その他: 約100億円/年（基本40億円 + ファン数比例大）
        base_other = 20000000 * season_days
        fan_based_other = int(fb.total_fans * 10 * season_days)
        other_expense = base_other + fan_based_other
        
        expense_breakdown = (
            f"【支出内訳】\n"
            f"選手年俸: {format_yen(total_player_salary)}\n"
            f"スタッフ年俸: {format_yen(total_staff_salary)}\n"
            f"球場維持費: {format_yen(stadium_maintenance)}\n"
            f"設備維持費: {format_yen(facility_cost)}\n"
            f"その他: {format_yen(other_expense)}"
        )
        
        return income_breakdown, expense_breakdown
    
    def _update_daily_labels(self):
        daily_revenue, daily_fan_change, daily_expense = self._calculate_daily_stats()
        
        self.daily_revenue_label.setText(f"日次収益: {format_yen(daily_revenue)}")
        
        sign = "+" if daily_fan_change >= 0 else ""
        color = self.theme.success if daily_fan_change >= 0 else self.theme.error
        self.daily_fan_change_label.setText(f"日次ファン増減: {sign}{daily_fan_change:,}人")
        self.daily_fan_change_label.setStyleSheet(f"font-size: 10px; color: {color};")
        
        self.daily_expense_label.setText(f"日次支出: {format_yen(daily_expense)}")
    
    def _on_management_changed(self, name: str, value: int):
        if not self.current_team:
            return
        
        settings = self.current_team.management_settings
        if name == "放映権価格":
            settings.broadcast_price = value
        elif name == "チケット価格":
            settings.ticket_price = value
        elif name == "グッズ価格":
            settings.merchandise_price = value
        
        self._update_daily_labels()
    
    def _on_investment_changed(self, name: str, value: int):
        if not self.current_team:
            return
        
        settings = self.current_team.investment_settings
        if name == "練習設備":
            settings.training_facility = value
        elif name == "医療設備":
            settings.medical_facility = value
        
        self._update_daily_labels()
    
    def _on_stadium_clicked(self):
        if not self.current_team:
            return
        
        budget = getattr(self.current_team, 'budget', 5000000000)
        stadium = self.current_team.stadium
        
        dialog = StadiumDialog(stadium, budget, self)
        if dialog.exec() and dialog.result_data:
            data = dialog.result_data
            if budget >= data["build_cost"]:
                from models import Stadium
                field_size = data["field_size"]
                is_dome = data.get("is_dome", False)
                
                # フィールドサイズによるパークファクター計算
                hr_pf = 1.0 + (3 - field_size) * 0.1
                tb_pf = 1.0 + (field_size - 3) * 0.15
                
                stadium_name = "新ドーム球場" if is_dome else "新本拠地球場"
                
                new_stadium = Stadium(
                    name=stadium_name,
                    capacity=data["capacity"],
                    field_size=field_size,
                    is_dome=is_dome,
                    pf_hr=hr_pf,
                    pf_3b=tb_pf
                )
                self.current_team.stadium = new_stadium
                self.current_team.budget -= data["build_cost"]
                self._update_display()
    
    def _on_event_clicked(self):
        if not self.current_team:
            return
        
        budget = getattr(self.current_team, 'budget', 5000000000)
        
        dialog = EventDialog(budget, self)
        if dialog.exec():
            cost = dialog.event_cost
            if budget >= cost:
                self.current_team.finance.host_event(cost)
                self.current_team.budget -= cost
                self._update_display()
    
    def set_game_state(self, game_state):
        self.game_state = game_state
        if game_state:
            self.current_team = game_state.player_team
            # 初回設定時に財務情報を初期化
            self._initialize_finance_values()
            self._update_display()
    
    def _initialize_finance_values(self):
        """ゲーム開始時に財務情報を初期設定"""
        if not self.current_team:
            return
        
        from models import TeamFinance, ManagementSettings, InvestmentSettings, FanBase
        
        # 財務オブジェクトの確認
        if not hasattr(self.current_team, 'finance') or self.current_team.finance is None:
            self.current_team.finance = TeamFinance()
        
        if not hasattr(self.current_team, 'management_settings') or self.current_team.management_settings is None:
            self.current_team.management_settings = ManagementSettings()
        
        if not hasattr(self.current_team, 'investment_settings') or self.current_team.investment_settings is None:
            self.current_team.investment_settings = InvestmentSettings()
        
        finance = self.current_team.finance
        
        # 支出の初期化（年俸のみ最初から設定、維持費は毎日加算）
        total_player_salary = sum(getattr(p, 'salary', 10000000) for p in self.current_team.players)
        total_staff_salary = sum(getattr(s, 'salary', 5000000) for s in self.current_team.staff) if hasattr(self.current_team, 'staff') else 0
        
        finance.player_salary_expense = total_player_salary
        finance.staff_salary_expense = total_staff_salary
        
        # 球場維持費、設備維持費、その他は毎日加算なので初期値0のまま
    
    def _update_display(self):
        if not self.current_team:
            return
        
        # Budget and annual estimates
        budget = getattr(self.current_team, 'budget', 5000000000)
        est_income, est_expense = self._calculate_annual_estimates()
        income_breakdown, expense_breakdown = self._get_estimate_breakdowns()
        self.budget_card.set_main_value(format_yen(budget))
        self.budget_card.clear_details()
        
        # 予想年間収支を表示（ツールチップ付き）
        net_estimate = est_income - est_expense
        net_color = self.theme.success if net_estimate >= 0 else self.theme.error
        self.budget_card.add_detail("予想年間収入", format_yen(est_income), self.theme.success, income_breakdown)
        self.budget_card.add_detail("予想年間支出", format_yen(est_expense), self.theme.error, expense_breakdown)
        self.budget_card.add_detail("年間収支予想", format_yen(net_estimate), net_color)
        
        # Fans
        finance = getattr(self.current_team, 'finance', None)
        if finance and hasattr(finance, 'fan_base'):
            fb = finance.fan_base
            self.fan_card.set_fans(fb.light_fans, fb.middle_fans, fb.core_fans)
            
            # Income (今期累計)
            self.income_card.set_main_value(format_yen(finance.total_income), self.theme.success)
            self.income_card.clear_details()
            self.income_card.add_detail("チケット", format_yen(finance.ticket_revenue), self.theme.success)
            self.income_card.add_detail("放映権", format_yen(finance.broadcast_revenue), self.theme.success)
            self.income_card.add_detail("グッズ", format_yen(finance.merchandise_revenue), self.theme.success)
            self.income_card.add_detail("スポンサー", format_yen(finance.sponsor_revenue), self.theme.success)
            
            # Expense (今期累計)
            self.expense_card.set_main_value(format_yen(finance.total_expense), self.theme.error)
            self.expense_card.clear_details()
            self.expense_card.add_detail("選手年俸", format_yen(finance.player_salary_expense))
            self.expense_card.add_detail("球場維持", format_yen(finance.stadium_maintenance))
            self.expense_card.add_detail("設備維持", format_yen(finance.facility_expense))
            self.expense_card.add_detail("その他", format_yen(finance.other_expense))
        
        # Management settings
        settings = getattr(self.current_team, 'management_settings', None)
        if settings:
            self.broadcast_ctrl.set_value(settings.broadcast_price)
            self.ticket_ctrl.set_value(settings.ticket_price)
            self.merch_ctrl.set_value(settings.merchandise_price)
        
        # Investment settings
        inv_settings = getattr(self.current_team, 'investment_settings', None)
        if inv_settings:
            self.training_ctrl.set_value(inv_settings.training_facility)
            self.medical_ctrl.set_value(inv_settings.medical_facility)
        
        self._update_daily_labels()
    
    def refresh(self):
        self._update_display()

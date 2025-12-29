# -*- coding: utf-8 -*-
"""
Pennant Simulator - Button Widgets
Custom Action Buttons and Controls
"""
from PySide6.QtWidgets import (
    QPushButton, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QButtonGroup, QAbstractButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, Property, QSize, QRect
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QBrush, QPen, QFont, QIcon

import sys
# Theme import fallback
try:
    from ..theme import get_theme
except ImportError:
    sys.path.insert(0, '..')
    from UI.theme import get_theme


class PremiumButton(QPushButton):
    """Premium styled button with hover effects (Gray to White transition)"""

    def __init__(self, text: str, style: str = "primary", parent=None):
        super().__init__(text, parent)
        self._style = style
        self._hover_progress = 0.0

        # Compact Premium Size
        self.setMinimumHeight(42)
        self.setMinimumWidth(200)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont("Yu Gothic UI", 11, QFont.Medium))

        self._setup_animation()

    def _setup_animation(self):
        self._animation = QPropertyAnimation(self, b"hover_progress")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, value):
        self._hover_progress = value
        self.update()

    hover_progress = Property(float, get_hover_progress, set_hover_progress)

    def enterEvent(self, event):
        self._animation.stop()
        self._animation.setStartValue(self._hover_progress)
        self._animation.setEndValue(1.0)
        self._animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animation.stop()
        self._animation.setStartValue(self._hover_progress)
        self._animation.setEndValue(0.0)
        self._animation.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        # Stylish Gray to White transition
        # Gray color (Normal): R=140, G=145, B=150
        # White color (Hover): R=255, G=255, B=255
        
        start_r, start_g, start_b = 140, 145, 150
        end_r, end_g, end_b = 255, 255, 255
        
        current_r = start_r + (end_r - start_r) * self._hover_progress
        current_g = start_g + (end_g - start_g) * self._hover_progress
        current_b = start_b + (end_b - start_b) * self._hover_progress
        
        current_color = QColor(int(current_r), int(current_g), int(current_b))
        
        # Background fill - Transparent to subtle white
        bg_alpha = int(0 + 20 * self._hover_progress)
        painter.setBrush(QColor(255, 255, 255, bg_alpha))
        
        # Border/Pen
        painter.setPen(QPen(current_color, 1))
        
        # Draw rounded rect
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 4, 4)

        # Glow effect on hover
        if self._hover_progress > 0:
            glow_alpha = int(40 * self._hover_progress)
            glow_color = QColor(255, 255, 255, glow_alpha)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(glow_color, 2))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 4, 4)

        # Draw text
        painter.setPen(current_color)
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignCenter, self.text())


class ActionButton(QPushButton):
    """Large action button with icon and description (OOTP Style)"""
    # ... (Keep existing implementation below) ...
    def __init__(self, text: str, description: str = "", icon: str = "",
                 style: str = "primary", parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._description = description
        self._icon_text = icon
        self._style = style
        self._hover_progress = 0.0

        self.setText(text)
        self.setMinimumHeight(60)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

        self._setup_animation()
        self._apply_style()

    def _setup_animation(self):
        self._animation = QPropertyAnimation(self, b"hover_progress")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, value):
        self._hover_progress = value
        self.update()

    hover_progress = Property(float, get_hover_progress, set_hover_progress)

    def _apply_style(self):
        styles = {
            "primary": (self.theme.primary, self.theme.primary_hover),
            "success": (self.theme.success, self.theme.success_hover),
            "danger": (self.theme.danger, self.theme.danger_hover),
            "secondary": (self.theme.bg_card, self.theme.bg_card_hover),
        }
        self._base_color, self._hover_color = styles.get(self._style, styles["primary"])

    def enterEvent(self, event):
        self._animation.stop()
        self._animation.setStartValue(self._hover_progress)
        self._animation.setEndValue(1.0)
        self._animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animation.stop()
        self._animation.setStartValue(self._hover_progress)
        self._animation.setEndValue(0.0)
        self._animation.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        # Interpolate color
        base = QColor(self._base_color)
        hover = QColor(self._hover_color)
        r = base.red() + (hover.red() - base.red()) * self._hover_progress
        g = base.green() + (hover.green() - base.green()) * self._hover_progress
        b = base.blue() + (hover.blue() - base.blue()) * self._hover_progress
        current_color = QColor(int(r), int(g), int(b))

        # Draw background
        gradient = QLinearGradient(0, 0, 0, rect.height())
        gradient.setColorAt(0, current_color.lighter(110))
        gradient.setColorAt(1, current_color)

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 8, 8)

        # Draw border on hover
        if self._hover_progress > 0:
            border_color = QColor(255, 255, 255, int(30 * self._hover_progress))
            painter.setPen(QPen(border_color, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 7, 7)

        # Draw icon
        x_offset = 20
        if self._icon_text:
            painter.setPen(QColor("white"))
            font = QFont()
            font.setPointSize(24)
            painter.setFont(font)
            painter.drawText(x_offset, rect.height() // 2 + 10, self._icon_text)
            x_offset += 50

        # Draw text
        painter.setPen(QColor("white"))
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(x_offset, rect.height() // 2 - 5, self.text())

        # Draw description
        if self._description:
            painter.setPen(QColor(255, 255, 255, 180))
            font.setPointSize(10)
            font.setBold(False)
            painter.setFont(font)
            painter.drawText(x_offset, rect.height() // 2 + 15, self._description)

class IconButton(QPushButton):
    """Circular icon button"""

    def __init__(self, icon: str = "", size: int = 40, style: str = "default", parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._icon_text = icon
        self._size = size
        self._style = style
        self._hover_progress = 0.0

        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)

        self._setup_animation()

    def _setup_animation(self):
        self._animation = QPropertyAnimation(self, b"hover_progress")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, value):
        self._hover_progress = value
        self.update()

    hover_progress = Property(float, get_hover_progress, set_hover_progress)

    def enterEvent(self, event):
        self._animation.stop()
        self._animation.setStartValue(self._hover_progress)
        self._animation.setEndValue(1.0)
        self._animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animation.stop()
        self._animation.setStartValue(self._hover_progress)
        self._animation.setEndValue(0.0)
        self._animation.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Square, simple color
        if self._style == "primary":
            base_color = QColor("#e0e0e0")  # Light gray
        elif self._style == "danger":
            base_color = QColor("#ff6666")  # Soft red
        else:
            base_color = QColor("#cccccc")  # Neutral gray

        hover_color = base_color.lighter(110)

        r = base_color.red() + (hover_color.red() - base_color.red()) * self._hover_progress
        g = base_color.green() + (hover_color.green() - base_color.green()) * self._hover_progress
        b = base_color.blue() + (hover_color.blue() - base_color.blue()) * self._hover_progress
        current_color = QColor(int(r), int(g), int(b))

        painter.setBrush(QBrush(current_color))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

        # Icon
        painter.setPen(QColor("#222"))
        font = QFont()
        font.setPointSize(self._size // 2 - 4)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self._icon_text)


class SegmentedControl(QWidget):
    """Segmented control for switching between views"""

    selection_changed = Signal(int)

    def __init__(self, options: list, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.options = options
        self._selected_index = 0

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.button_group = QButtonGroup(self)
        self.buttons = []

        for i, option in enumerate(self.options):
            btn = QPushButton(option)
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(36)

            # Style
            self._apply_button_style(btn, i == 0, i, len(self.options))

            self.button_group.addButton(btn, i)
            self.buttons.append(btn)
            layout.addWidget(btn)

        self.button_group.idClicked.connect(self._on_selection)

    def _apply_button_style(self, btn: QPushButton, is_selected: bool, index: int, total: int):
        # Border radius based on position
        if total == 1:
            border_radius = "6px"
        elif index == 0:
            border_radius = "6px 0 0 6px"
        elif index == total - 1:
            border_radius = "0 6px 6px 0"
        else:
            border_radius = "0"

        if is_selected:
            bg = self.theme.primary
            color = "white"
            border = self.theme.primary
        else:
            bg = self.theme.bg_card
            color = self.theme.text_secondary
            border = self.theme.border

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {color};
                border: 1px solid {border};
                border-radius: {border_radius};
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {self.theme.primary_hover if is_selected else self.theme.bg_card_hover};
            }}
        """)

    def _on_selection(self, id: int):
        self._selected_index = id

        # Update all button styles
        for i, btn in enumerate(self.buttons):
            self._apply_button_style(btn, i == id, i, len(self.buttons))

        self.selection_changed.emit(id)

    def get_selected_index(self) -> int:
        return self._selected_index

    def set_selected_index(self, index: int):
        if 0 <= index < len(self.buttons):
            self.buttons[index].setChecked(True)
            self._on_selection(index)


class TabButton(QPushButton):
    """Navigation tab button - Premium minimal design"""

    def __init__(self, text: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._icon_text = icon
        self._is_active = False

        self.setText(text)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)

        self._apply_style()

    def _apply_style(self):
        if self._is_active:
            style = f"""
                QPushButton {{
                    background-color: rgba(0, 102, 204, 0.15);
                    color: {self.theme.primary_light};
                    border: none;
                    border-left: 2px solid {self.theme.primary};
                    border-radius: 0;
                    padding: 10px 12px 10px 14px;
                    text-align: left;
                    font-size: 12px;
                    font-weight: 500;
                    letter-spacing: 1px;
                }}
            """
        else:
            style = f"""
                QPushButton {{
                    background-color: transparent;
                    color: {self.theme.text_muted};
                    border: none;
                    border-left: 2px solid transparent;
                    border-radius: 0;
                    padding: 10px 12px 10px 14px;
                    text-align: left;
                    font-size: 12px;
                    font-weight: 400;
                    letter-spacing: 1px;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.03);
                    color: {self.theme.text_primary};
                    border-left: 2px solid {self.theme.border_light};
                }}
            """
        self.setStyleSheet(style)

    def set_active(self, active: bool):
        self._is_active = active
        self.setChecked(active)
        self._apply_style()


class SimButton(QPushButton):
    """Simulation control button (Play/Pause/Fast Forward)"""

    def __init__(self, mode: str = "play", parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._mode = mode
        self._is_active = False

        self.setFixedSize(48, 48)
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style()

    def _apply_style(self):
        icons = {
            "play": "▶",
            "pause": "⏸",
            "fast": "⏩︎",
            "step": "⏭",
        }
        self._icon = icons.get(self._mode, "▶")

        if self._is_active:
            bg = self.theme.success
        else:
            bg = self.theme.bg_card

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: white;
                border: 1px solid {self.theme.border};
                border-radius: 24px;
                font-size: 18px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.success_hover if self._is_active else self.theme.bg_card_hover};
            }}
        """)

    def set_mode(self, mode: str):
        self._mode = mode
        self._apply_style()
        self.update()

    def set_active(self, active: bool):
        self._is_active = active
        self._apply_style()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor("white"))
        font = QFont()
        font.setPointSize(16)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self._icon)


class SpeedControl(QWidget):
    """Simulation speed control"""

    speed_changed = Signal(int)  # 1, 2, 4, 8, etc.

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._speed = 1
        self._speeds = [1, 2, 4, 8]

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        label = QLabel("速度:")
        label.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 12px;")
        layout.addWidget(label)

        self.buttons = []
        for speed in self._speeds:
            btn = QPushButton(f"x{speed}")
            btn.setFixedSize(36, 28)
            btn.setCheckable(True)
            btn.setChecked(speed == 1)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, s=speed: self._set_speed(s))
            self._apply_button_style(btn, speed == 1)
            self.buttons.append((speed, btn))
            layout.addWidget(btn)

    def _apply_button_style(self, btn: QPushButton, is_active: bool):
        if is_active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme.primary};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 500;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme.bg_card};
                    color: {self.theme.text_secondary};
                    border: 1px solid {self.theme.border};
                    border-radius: 4px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {self.theme.bg_card_hover};
                }}
            """)

    def _set_speed(self, speed: int):
        self._speed = speed
        for s, btn in self.buttons:
            self._apply_button_style(btn, s == speed)
            btn.setChecked(s == speed)
        self.speed_changed.emit(speed)

    def get_speed(self) -> int:
        return self._speed


class PrimaryButton(PremiumButton):
    """Primary Action Button (Blue)"""
    def __init__(self, text: str, parent=None):
        super().__init__(text, style="primary", parent=parent)

class SecondaryButton(PremiumButton):
    """Secondary Action Button (Gray)"""
    def __init__(self, text: str, parent=None):
        super().__init__(text, style="secondary", parent=parent)
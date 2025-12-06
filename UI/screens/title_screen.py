# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Premium Title Screen
Ultra-stylish title screen with elegant design
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QFrame, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, Property, QRect
from PySide6.QtGui import (
    QColor, QPainter, QLinearGradient, QRadialGradient,
    QFont, QPen, QBrush, QPainterPath
)
import math


class PremiumButton(QPushButton):
    """Premium styled button with hover effects"""

    def __init__(self, text: str, style: str = "primary", parent=None):
        super().__init__(text, parent)
        self._style = style
        self._hover_progress = 0.0

        # Smaller size as requested
        self.setMinimumHeight(42)
        self.setMinimumWidth(200)
        self.setCursor(Qt.PointingHandCursor)
        # Slightly smaller font
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
        
        # Draw rounded rect (Smaller radius for sharper look)
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


class TitleScreen(QWidget):
    """Premium title screen"""

    new_game_clicked = Signal()
    continue_clicked = Signal()
    load_game_clicked = Signal()
    settings_clicked = Signal()
    exit_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._has_save = False
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top spacer
        layout.addStretch(2)

        # Logo section
        logo_section = QWidget()
        logo_layout = QVBoxLayout(logo_section)
        logo_layout.setAlignment(Qt.AlignCenter)
        logo_layout.setSpacing(8)

        # Decorative line above
        top_line = QFrame()
        top_line.setFixedSize(80, 1)
        top_line.setStyleSheet("background-color: #3d444d;")
        logo_layout.addWidget(top_line, alignment=Qt.AlignCenter)

        logo_layout.addSpacing(20)

        # Main title
        title_label = QLabel("Pennant Simulator")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 64px;
            font-weight: 200;
            letter-spacing: 15px;
            color: #ffffff;
        """)
        logo_layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel("2027")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("""
            font-size: 18px;
            font-weight: 300;
            letter-spacing: 15px;
            color: #6e7681;
            margin-top: 5px;
        """)
        logo_layout.addWidget(subtitle_label)

        logo_layout.addSpacing(20)

        # Decorative line below
        bottom_line = QFrame()
        bottom_line.setFixedSize(80, 1)
        bottom_line.setStyleSheet("background-color: #3d444d;")
        logo_layout.addWidget(bottom_line, alignment=Qt.AlignCenter)

        layout.addWidget(logo_section)

        # Middle spacer
        layout.addStretch(1)

        # Menu section
        menu_section = QWidget()
        menu_layout = QVBoxLayout(menu_section)
        menu_layout.setAlignment(Qt.AlignCenter)
        menu_layout.setSpacing(16)

        # New Game button
        self.new_game_btn = PremiumButton("NEW GAME", "primary")
        self.new_game_btn.clicked.connect(self.new_game_clicked.emit)
        menu_layout.addWidget(self.new_game_btn, alignment=Qt.AlignCenter)

        # Continue button (shown if save exists)
        self.continue_btn = PremiumButton("CONTINUE", "primary")
        self.continue_btn.clicked.connect(self.continue_clicked.emit)
        self.continue_btn.setVisible(False)
        menu_layout.addWidget(self.continue_btn, alignment=Qt.AlignCenter)

        # Load Game button
        self.load_btn = PremiumButton("LOAD GAME", "secondary")
        self.load_btn.clicked.connect(self.load_game_clicked.emit)
        menu_layout.addWidget(self.load_btn, alignment=Qt.AlignCenter)

        # Settings button
        self.settings_btn = PremiumButton("SETTINGS", "secondary")
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        menu_layout.addWidget(self.settings_btn, alignment=Qt.AlignCenter)

        # Exit button
        self.exit_btn = PremiumButton("EXIT", "secondary")
        self.exit_btn.clicked.connect(self.exit_clicked.emit)
        menu_layout.addWidget(self.exit_btn, alignment=Qt.AlignCenter)

        layout.addWidget(menu_section)

        # Bottom spacer
        layout.addStretch(2)

        # Copyright
        copyright_label = QLabel("2025 Pennant Simulator PROJECT")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("""
            font-size: 10px;
            font-weight: 400;
            color: #3d444d;
            letter-spacing: 2px;
            padding: 30px;
        """)
        layout.addWidget(copyright_label)

    def set_has_save(self, has_save: bool):
        """Show/hide continue button based on save existence"""
        self._has_save = has_save
        self.continue_btn.setVisible(has_save)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Dark gradient background
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(6, 8, 12))
        gradient.setColorAt(0.3, QColor(13, 17, 23))
        gradient.setColorAt(0.7, QColor(13, 17, 23))
        gradient.setColorAt(1.0, QColor(8, 10, 14))

        painter.fillRect(self.rect(), gradient)

        # Subtle radial glow at top
        center_x = self.width() / 2
        center_y = self.height() * 0.25

        glow = QRadialGradient(center_x, center_y, 400)
        glow.setColorAt(0, QColor(0, 102, 204, 15))
        glow.setColorAt(0.5, QColor(0, 102, 204, 8))
        glow.setColorAt(1, QColor(0, 0, 0, 0))

        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(center_x - 400), int(center_y - 400), 800, 800)

        # Subtle vignette effect
        vignette = QRadialGradient(self.width() / 2, self.height() / 2,
                                   max(self.width(), self.height()) * 0.8)
        vignette.setColorAt(0.5, QColor(0, 0, 0, 0))
        vignette.setColorAt(1.0, QColor(0, 0, 0, 100))

        painter.setBrush(QBrush(vignette))
        painter.drawRect(self.rect())
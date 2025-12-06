# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Premium Title Screen
Ultra-stylish animated title screen with OOTP-inspired design
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QFrame, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import (
    QColor, QPainter, QLinearGradient, QRadialGradient,
    QFont, QPen, QBrush, QPainterPath
)
import math

from UI.theme import get_theme


class AnimatedBaseball(QWidget):
    """Animated floating baseball with glow effect"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._float_offset = 0
        self._glow_intensity = 0.5
        self.setFixedSize(80, 80)

        # Animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_animation)
        self._timer.start(16)  # ~60fps

    def _update_animation(self):
        self._angle = (self._angle + 1) % 360
        self._float_offset = math.sin(self._angle * math.pi / 90) * 5
        self._glow_intensity = 0.4 + 0.2 * math.sin(self._angle * math.pi / 180)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center_x = self.width() / 2
        center_y = self.height() / 2 + self._float_offset
        radius = 25

        # Outer glow
        glow_gradient = QRadialGradient(center_x, center_y, radius + 20)
        glow_gradient.setColorAt(0, QColor(255, 255, 255, int(60 * self._glow_intensity)))
        glow_gradient.setColorAt(0.5, QColor(255, 255, 255, int(30 * self._glow_intensity)))
        glow_gradient.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(glow_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(center_x - radius - 20), int(center_y - radius - 20),
                           int((radius + 20) * 2), int((radius + 20) * 2))

        # Baseball body
        ball_gradient = QRadialGradient(center_x - 10, center_y - 10, radius * 2)
        ball_gradient.setColorAt(0, QColor(255, 255, 255))
        ball_gradient.setColorAt(0.3, QColor(245, 245, 245))
        ball_gradient.setColorAt(1, QColor(200, 200, 200))
        painter.setBrush(QBrush(ball_gradient))
        painter.setPen(QPen(QColor(180, 180, 180), 1))
        painter.drawEllipse(int(center_x - radius), int(center_y - radius),
                           int(radius * 2), int(radius * 2))

        # Seams
        pen = QPen(QColor(200, 50, 50), 2)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        # Left seam
        path1 = QPainterPath()
        path1.moveTo(center_x - 15, center_y - 20)
        path1.cubicTo(center_x - 25, center_y - 10, center_x - 25, center_y + 10, center_x - 15, center_y + 20)
        painter.drawPath(path1)

        # Right seam
        path2 = QPainterPath()
        path2.moveTo(center_x + 15, center_y - 20)
        path2.cubicTo(center_x + 25, center_y - 10, center_x + 25, center_y + 10, center_x + 15, center_y + 20)
        painter.drawPath(path2)


class TitleButton(QPushButton):
    """Premium styled title screen button"""

    def __init__(self, text: str, is_primary: bool = False, parent=None):
        super().__init__(text, parent)
        self.theme = get_theme()
        self._is_primary = is_primary
        self._hover_progress = 0.0

        self.setFixedSize(280, 56)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_style()
        self._setup_animation()

    def _setup_style(self):
        if self._is_primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {self.theme.primary_light}, stop:1 {self.theme.primary});
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 18px;
                    font-weight: 700;
                    letter-spacing: 2px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {self.theme.primary_hover}, stop:1 {self.theme.primary_light});
                }}
                QPushButton:pressed {{
                    background: {self.theme.primary_dark};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {self.theme.bg_card_elevated}, stop:1 {self.theme.bg_card});
                    color: {self.theme.text_primary};
                    border: 1px solid {self.theme.border};
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: 600;
                    letter-spacing: 1px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {self.theme.bg_card_hover}, stop:1 {self.theme.bg_card_elevated});
                    border-color: {self.theme.primary};
                }}
                QPushButton:pressed {{
                    background: {self.theme.bg_card};
                }}
            """)

        # Add shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def _setup_animation(self):
        self._animation = QPropertyAnimation(self, b"hover_progress")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, value):
        self._hover_progress = value

    hover_progress = Property(float, get_hover_progress, set_hover_progress)


class TitleScreen(QWidget):
    """Premium title screen with menu options"""

    new_game_clicked = Signal()
    load_game_clicked = Signal()
    settings_clicked = Signal()
    exit_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._setup_ui()
        self._start_animations()

    def _setup_ui(self):
        self.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top spacer
        layout.addStretch(2)

        # Logo area
        logo_container = QWidget()
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setAlignment(Qt.AlignCenter)
        logo_layout.setSpacing(8)

        # Animated baseball
        baseball_container = QWidget()
        baseball_layout = QHBoxLayout(baseball_container)
        baseball_layout.setAlignment(Qt.AlignCenter)
        self.baseball = AnimatedBaseball()
        baseball_layout.addWidget(self.baseball)
        logo_layout.addWidget(baseball_container)

        # Main title
        self.title_label = QLabel("Pennant Simulator")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            font-size: 64px;
            font-weight: 300;
            letter-spacing: 15px;
            color: #ffffff;
        """)
        logo_layout.addWidget(self.title_label)

        # Subtitle
        self.subtitle_label = QLabel("2027")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet("""
            font-size: 28px;
            font-weight: 200;
            letter-spacing: 15px;
            color: #8b949e;
            margin-top: 0px;
        """)
        logo_layout.addWidget(self.subtitle_label)

        # Tagline
        self.tagline_label = QLabel("Experience the thrill of Japanese Professional Baseball")
        self.tagline_label.setAlignment(Qt.AlignCenter)
        self.tagline_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 400;
            color: {self.theme.text_muted};
            margin-top: 20px;
            letter-spacing: 1px;
        """)
        logo_layout.addWidget(self.tagline_label)

        layout.addWidget(logo_container)

        # Spacer between logo and buttons
        layout.addSpacing(60)

        # Button container
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.setSpacing(16)

        # New Game button (primary)
        self.new_game_btn = TitleButton("NEW GAME", is_primary=True)
        self.new_game_btn.clicked.connect(self.new_game_clicked.emit)
        button_layout.addWidget(self.new_game_btn, alignment=Qt.AlignCenter)

        # Load Game button
        self.load_game_btn = TitleButton("LOAD GAME")
        self.load_game_btn.clicked.connect(self.load_game_clicked.emit)
        button_layout.addWidget(self.load_game_btn, alignment=Qt.AlignCenter)

        # Settings button
        self.settings_btn = TitleButton("SETTINGS")
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        button_layout.addWidget(self.settings_btn, alignment=Qt.AlignCenter)

        # Exit button
        self.exit_btn = TitleButton("EXIT")
        self.exit_btn.clicked.connect(self.exit_clicked.emit)
        button_layout.addWidget(self.exit_btn, alignment=Qt.AlignCenter)

        layout.addWidget(button_container)

        # Bottom spacer
        layout.addStretch(3)

        # Footer
        footer_container = QWidget()
        footer_layout = QVBoxLayout(footer_container)
        footer_layout.setAlignment(Qt.AlignCenter)
        footer_layout.setSpacing(8)

        # Version
        version_label = QLabel("VERSION 1.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("""
            font-size: 11px;
            font-weight: 500;
            color: #3d444d;
            letter-spacing: 3px;
        """)
        footer_layout.addWidget(version_label)

        # Copyright
        copyright_label = QLabel("Baseball Simulation")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("""
            font-size: 10px;
            font-weight: 400;
            color: #30363d;
            letter-spacing: 1px;
            padding-bottom: 30px;
        """)
        footer_layout.addWidget(copyright_label)

        layout.addWidget(footer_container)

    def _start_animations(self):
        # Could add fade-in animations here
        pass

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Create dark gradient background
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(8, 10, 14))
        gradient.setColorAt(0.3, QColor(13, 17, 23))
        gradient.setColorAt(0.7, QColor(13, 17, 23))
        gradient.setColorAt(1.0, QColor(6, 8, 12))

        painter.fillRect(self.rect(), gradient)

        # Subtle radial glow in center-top
        center_x = self.width() / 2
        center_y = self.height() / 3

        glow = QRadialGradient(center_x, center_y, 400)
        glow.setColorAt(0, QColor(0, 102, 204, 25))
        glow.setColorAt(0.3, QColor(0, 102, 204, 15))
        glow.setColorAt(0.6, QColor(0, 102, 204, 5))
        glow.setColorAt(1, QColor(0, 0, 0, 0))

        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(center_x - 400), int(center_y - 400), 800, 800)

        # Secondary glow (gold accent) below
        glow2 = QRadialGradient(center_x, center_y + 200, 300)
        glow2.setColorAt(0, QColor(255, 215, 0, 10))
        glow2.setColorAt(0.5, QColor(255, 215, 0, 5))
        glow2.setColorAt(1, QColor(0, 0, 0, 0))

        painter.setBrush(QBrush(glow2))
        painter.drawEllipse(int(center_x - 300), int(center_y - 100), 600, 600)

        # Corner decorations - subtle lines
        pen = QPen(QColor(0, 102, 204, 40), 1)
        painter.setPen(pen)

        # Top-left corner
        painter.drawLine(0, 60, 60, 60)
        painter.drawLine(60, 0, 60, 60)

        # Top-right corner
        painter.drawLine(self.width() - 60, 60, self.width(), 60)
        painter.drawLine(self.width() - 60, 0, self.width() - 60, 60)

        # Bottom-left corner
        painter.drawLine(0, self.height() - 60, 60, self.height() - 60)
        painter.drawLine(60, self.height() - 60, 60, self.height())

        # Bottom-right corner
        painter.drawLine(self.width() - 60, self.height() - 60, self.width(), self.height() - 60)
        painter.drawLine(self.width() - 60, self.height() - 60, self.width() - 60, self.height())

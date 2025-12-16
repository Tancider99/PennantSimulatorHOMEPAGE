# -*- coding: utf-8 -*-
"""
Pennant Simulator 2027 - Premium Loading Screen
Ultra-stylish animated loading screen
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QGraphicsDropShadowEffect, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import (
    QColor, QPainter, QLinearGradient, QRadialGradient,
    QFont, QPen, QBrush, QPainterPath
)
import math


class AnimatedRing(QWidget):
    """Animated loading ring with glow effect"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._glow_intensity = 0.5
        self.setFixedSize(120, 120)

        # Animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_animation)
        self._timer.start(16)  # ~60fps

    def _update_animation(self):
        self._angle = (self._angle + 3) % 360
        self._glow_intensity = 0.5 + 0.3 * math.sin(self._angle * math.pi / 180)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(center_x, center_y) - 10

        # Outer glow
        glow_gradient = QRadialGradient(center_x, center_y, radius + 20)
        glow_gradient.setColorAt(0, QColor(0, 102, 204, int(100 * self._glow_intensity)))
        glow_gradient.setColorAt(0.5, QColor(0, 102, 204, int(50 * self._glow_intensity)))
        glow_gradient.setColorAt(1, QColor(0, 102, 204, 0))
        painter.setBrush(QBrush(glow_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(center_x - radius - 20), int(center_y - radius - 20),
                           int((radius + 20) * 2), int((radius + 20) * 2))

        # Background ring
        pen = QPen(QColor(30, 40, 50), 4)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(int(center_x - radius), int(center_y - radius),
                           int(radius * 2), int(radius * 2))

        # Animated arc with gradient
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor(0, 102, 204))
        gradient.setColorAt(0.5, QColor(0, 180, 255))
        gradient.setColorAt(1, QColor(100, 200, 255))

        pen = QPen(QBrush(gradient), 4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        # Draw arc
        rect = self.rect().adjusted(10, 10, -10, -10)
        painter.drawArc(rect, int(self._angle * 16), int(120 * 16))

        # Secondary arc
        pen2 = QPen(QColor(0, 102, 204, 100), 2)
        pen2.setCapStyle(Qt.RoundCap)
        painter.setPen(pen2)
        painter.drawArc(rect, int((self._angle + 180) * 16), int(60 * 16))


class LoadingScreen(QWidget):
    """Premium loading screen with animations"""

    loading_complete = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0
        self._current_message = "Initializing..."
        self._messages = []
        self._message_index = 0

        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(40)

        # Spacer
        layout.addStretch(2)

        # Logo area
        logo_container = QWidget()
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setAlignment(Qt.AlignCenter)
        logo_layout.setSpacing(16)

        # Main title
        self.title_label = QLabel("Pennant Simulator")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            font-size: 52px;
            font-weight: 300;
            letter-spacing: 15px;
            color: #ffffff;
        """)
        logo_layout.addWidget(self.title_label)

        # Subtitle
        self.subtitle_label = QLabel("2027")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet("""
            font-size: 24px;
            font-weight: 200;
            letter-spacing: 12px;
            color: #8b949e;
            margin-top: 0px;
        """)
        logo_layout.addWidget(self.subtitle_label)

        layout.addWidget(logo_container)

        # Animated ring
        ring_container = QWidget()
        ring_layout = QHBoxLayout(ring_container)
        ring_layout.setAlignment(Qt.AlignCenter)

        self.loading_ring = AnimatedRing()
        ring_layout.addWidget(self.loading_ring)

        layout.addWidget(ring_container)

        # Progress section
        progress_container = QWidget()
        progress_container.setFixedWidth(400)
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setSpacing(12)

        # Message label
        self.message_label = QLabel("Initializing...")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 400;
            color: #8b949e;
            letter-spacing: 1px;
        """)
        progress_layout.addWidget(self.message_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1c2128;
                border: none;
                border-radius: 0px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0066cc, stop:0.5 #00b4ff, stop:1 #0066cc);
                border-radius: 0px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        # Percentage (Hidden)
        self.percent_label = QLabel("0%")
        self.percent_label.setAlignment(Qt.AlignCenter)
        self.percent_label.setVisible(False) # Hide percent display
        self.percent_label.setStyleSheet("""
            font-size: 11px;
            font-weight: 500;
            color: #6e7681;
            letter-spacing: 2px;
        """)
        progress_layout.addWidget(self.percent_label)

        layout.addWidget(progress_container, alignment=Qt.AlignCenter)

        # Spacer
        layout.addStretch(3)

        # Version info
        version_label = QLabel("VERSION 1.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("""
            font-size: 10px;
            font-weight: 400;
            color: #3d444d;
            letter-spacing: 3px;
            padding-bottom: 30px;
        """)
        layout.addWidget(version_label)

    def set_progress(self, value: int, message: str = None):
        """Update loading progress"""
        self._progress = min(100, max(0, value))
        self.progress_bar.setValue(self._progress)
        self.percent_label.setText(f"{self._progress}%")

        if message:
            self._current_message = message
            self.message_label.setText(message)

        if self._progress >= 100:
            QTimer.singleShot(500, self.loading_complete.emit)

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

        # Subtle radial glow in center
        center_x = self.width() / 2
        center_y = self.height() / 2 - 50

        glow = QRadialGradient(center_x, center_y, 300)
        glow.setColorAt(0, QColor(0, 102, 204, 20))
        glow.setColorAt(0.5, QColor(0, 102, 204, 10))
        glow.setColorAt(1, QColor(0, 0, 0, 0))

        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(center_x - 300), int(center_y - 300), 600, 600)

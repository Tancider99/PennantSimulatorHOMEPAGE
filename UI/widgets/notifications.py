# -*- coding: utf-8 -*-
"""
Pennant Simulator - Notification System
Non-blocking "Toast" notifications with square industrial design.
"""
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGraphicsOpacityEffect, QApplication
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, Signal, QRect
from PySide6.QtGui import QColor, QPainter, QPen, QFont

import sys
# Theme import fallback
try:
    from UI.theme import get_theme
except ImportError:
    sys.path.insert(0, '..')
    from UI.theme import get_theme


class ToastWidget(QWidget):
    """
    Square, industrial-styled notification toast.
    Slides in, waits, fades out.
    """
    closed = Signal(QWidget) # Signal to manager when ready to be removed

    def __init__(self, title: str, message: str, type: str = "info", parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._title = title
        self._message = message
        self._type = type
        
        # Setup aesthetic properties
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Size
        self.setFixedWidth(320)
        self.setFixedHeight(100) # Fixed height for cleaner stacking
        
        self._setup_ui()
        self._setup_animations()

        # Auto-close timer
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._start_close_animation)
        self.timer.start(3500) # 3.5 seconds

    def _setup_ui(self):
        # Determine colors based on type
        if self._type == "success":
            self.accent_color = self.theme.success
        elif self._type == "warning":
            self.accent_color = self.theme.warning
        elif self._type == "error":
            self.accent_color = self.theme.danger
        else:
            self.accent_color = self.theme.primary

        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        # Title Row
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        
        # Icon (Just a colored square for now, or text)
        icon_marker = QLabel("■")
        icon_marker.setStyleSheet(f"color: {self.accent_color}; font-size: 14px;")
        title_row.addWidget(icon_marker)
        
        title_lbl = QLabel(self._title.upper())
        title_lbl.setStyleSheet(f"""
            color: {self.theme.text_primary};
            font-weight: 700;
            font-size: 13px;
            letter-spacing: 1px;
        """)
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        
        layout.addLayout(title_row)
        
        # Message
        msg_lbl = QLabel(self._message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"""
            color: {self.theme.text_secondary};
            font-size: 12px;
            font-family: 'Yu Gothic UI';
        """)
        layout.addWidget(msg_lbl)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        
        # Background (Dark, semi-transparent)
        bg_color = QColor(self.theme.bg_card)
        bg_color.setAlpha(245) # Almost opaque
        painter.setBrush(bg_color)
        
        # Border (Square, Sharp)
        painter.setPen(QPen(QColor(self.accent_color), 1))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        
        # Accent Line on Left
        painter.fillRect(0, 0, 4, rect.height(), QColor(self.accent_color))

    def _setup_animations(self):
        # Opacity Effect
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        # Entry Animation (Fade In + Slide slightly?)
        self.anim_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_in.setDuration(300)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.setEasingCurve(QEasingCurve.OutQuad)
        self.anim_in.start()
        
    def _start_close_animation(self):
        self.anim_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_out.setDuration(300)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.setEasingCurve(QEasingCurve.InQuad)
        self.anim_out.finished.connect(self.close_notification)
        self.anim_out.start()
        
    def close_notification(self):
        self.closed.emit(self)
        self.close()

class NotificationManager(QWidget):
    """
    Manages the display and stacking of notifications.
    Transparent overlay widget.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents) # Let clicks pass through
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        self._active_notifications = []
        
    def show_toast(self, title, message, type="info"):
        # Create toast
        # Note: Toast parent is 'None' for Window-based, or 'self' for widget-based?
        # If we use Window/Tool flag on Toast, position can be global.
        # But prefer widget-based to stick to main window.
        
        # Better approach: Toasts are children of this overlay manager
        toast = ToastWidget(title, message, type, self.parent()) # Parent is MainWindow
        
        # Position logic
        # Bottom Right of the PARENT window
        parent_geo = self.parent().geometry()
        
        # Stacking logic
        # We need to manage positions of multiple toasts
        # For simplicity, just stack from bottom right
        
        self._active_notifications.append(toast)
        toast.closed.connect(lambda: self._remove_toast(toast))
        
        self._reposition_toasts()
        toast.show()
        
    def _remove_toast(self, toast):
        if toast in self._active_notifications:
            self._active_notifications.remove(toast)
        self._reposition_toasts()
            
    def _reposition_toasts(self):
        if not self.parent(): return
        
        parent_rect = self.parent().rect()
        margin_x = 24
        margin_y = 24
        spacing = 10
        
        bottom_y = parent_rect.bottom() - margin_y
        right_x = parent_rect.right() - margin_x
        
        current_y = bottom_y
        
        # Iterate backwards (newest at bottom)
        for toast in reversed(self._active_notifications):
            toast_w = toast.width()
            toast_h = toast.height()
            
            target_pos = QPoint(right_x - toast_w, current_y - toast_h)
            toast.move(target_pos)
            
            current_y -= (toast_h + spacing)

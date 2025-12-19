# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Starfield Panels
Industrial Sci-Fi Layout Containers
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QStackedWidget, QSplitter, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QLinearGradient

import sys
sys.path.insert(0, '..')
try:
    from UI.theme import get_theme
except ImportError:
    pass


class PageHeader(QFrame):
    """Industrial Page Header"""

    def __init__(self, title: str, subtitle: str = "", icon: str = "", parent=None):
        # 【修正】QFrameにはparentのみ渡す
        super().__init__(parent)
        try:
            self.theme = get_theme()
        except:
            from UI.theme import get_theme
            self.theme = get_theme()
            
        self._title = title
        self._subtitle = subtitle
        self._icon = icon
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedHeight(80)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_header};
                border-bottom: 1px solid {self.theme.border};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)

        # Decoration Marker
        marker = QFrame()
        marker.setFixedSize(4, 32)
        marker.setStyleSheet(f"background-color: {self.theme.accent_orange};")
        layout.addWidget(marker)

        # Title area
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title_layout.setAlignment(Qt.AlignVCenter)

        title_text = f"{self._title}"
        self.title_label = QLabel(title_text)
        self.title_label.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 300;
            color: {self.theme.text_primary};
            letter-spacing: 2px;
            text-transform: uppercase;
        """)
        title_layout.addWidget(self.title_label)

        if self._subtitle:
            self.subtitle_label = QLabel(self._subtitle)
            self.subtitle_label.setStyleSheet(f"""
                font-size: 11px;
                color: {self.theme.text_secondary};
                letter-spacing: 1px;
                text-transform: uppercase;
            """)
            title_layout.addWidget(self.subtitle_label)

        layout.addLayout(title_layout)
        layout.addStretch()

        # Actions area
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(12)
        layout.addLayout(self.actions_layout)

    def set_title(self, title: str, icon: str = None):
        self._title = title
        self.title_label.setText(title)

    def add_action(self, widget):
        self.actions_layout.addWidget(widget)

class InfoPanel(QFrame):
    """Industrial Info Display"""
    def __init__(self, title: str = "", parent=None):
        # 【修正】QFrameにはparentのみ渡す
        super().__init__(parent)
        try:
            self.theme = get_theme()
        except:
            from UI.theme import get_theme
            self.theme = get_theme()
            
        self._title = title
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
            }}
        """)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 12, 16, 12)
        self.main_layout.setSpacing(8)

        if self._title:
            t = QLabel(self._title)
            t.setStyleSheet(f"""
                font-size: 11px; font-weight: 700; color: {self.theme.text_secondary};
                letter-spacing: 1px; border-bottom: 1px solid {self.theme.border};
                padding-bottom: 4px; margin-bottom: 4px;
            """)
            self.main_layout.addWidget(t)
        
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(4)
        self.main_layout.addLayout(self.content_layout)

    def add_row(self, label: str, value: str, value_color: str = None):
        row = QHBoxLayout()
        l = QLabel(label)
        l.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 11px;")
        v = QLabel(value)
        c = value_color or self.theme.text_primary
        v.setStyleSheet(f"color: {c}; font-size: 13px; font-weight: 600; font-family: 'Consolas';")
        row.addWidget(l)
        row.addStretch()
        row.addWidget(v)
        self.content_layout.addLayout(row)

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)


class SidebarPanel(QWidget):
    """Starfield Navigation Sidebar"""

    def add_stretch(self):
        self.nav_layout.addStretch()

    navigation_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.theme = get_theme()
        except:
            from UI.theme import get_theme
            self.theme = get_theme()
        self.setFixedWidth(220)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            background-color: {self.theme.bg_sidebar};
            border-right: 1px solid {self.theme.border};
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo Area - Use QPalette for reliable background color
        logo_area = QWidget()
        logo_area.setObjectName("SidebarLogoArea")
        logo_area.setAutoFillBackground(True)
        logo_area.setFixedHeight(100)  # Extended height
        
        # Set background using QPalette (more reliable than stylesheet)
        from PySide6.QtGui import QPalette, QColor
        palette = logo_area.palette()
        palette.setColor(QPalette.Window, QColor(self.theme.bg_darkest))
        logo_area.setPalette(palette)
        
        logo_layout = QVBoxLayout(logo_area)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setAlignment(Qt.AlignCenter)
        
        lbl = QLabel("Pennant SIM")
        lbl.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 700;
            letter-spacing: 4px;
            color: {self.theme.text_primary};
            background-color: transparent;
        """)
        logo_layout.addWidget(lbl)
        layout.addWidget(logo_area)

        # Nav Area - Remove top margin to avoid gap showing different background
        self.nav_layout = QVBoxLayout()
        self.nav_layout.setContentsMargins(0, 0, 0, 20)  # Only bottom margin
        self.nav_layout.setSpacing(4)
        layout.addLayout(self.nav_layout)

        layout.addStretch()
        
        # Bottom Tech Status
        status_area = QFrame()
        status_area.setFixedHeight(40)
        status_area.setStyleSheet(f"border-top: 1px solid {self.theme.border}; background-color: {self.theme.bg_darkest};")
        s_layout = QHBoxLayout(status_area)
        s_layout.setContentsMargins(16, 0, 16, 0)
        
        status_lbl = QLabel("SYS: ONLINE")
        status_lbl.setStyleSheet(f"font-size: 10px; color: {self.theme.success}; letter-spacing: 1px;")
        s_layout.addWidget(status_lbl)
        
        layout.addWidget(status_area)

    def add_nav_item(self, icon: str, text: str, section: str):
        # 循環インポート回避のため関数内でインポート
        from .buttons import TabButton
        btn = TabButton(text)
        btn.clicked.connect(lambda: self._on_nav_click(section, btn))
        btn.setProperty("section", section)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-left: 3px solid transparent;
                color: {self.theme.text_secondary};
                text-align: left;
                padding: 12px 24px;
                font-size: 13px;
                letter-spacing: 1px;
                border-radius: 0;
            }}
            QPushButton:hover {{
                background-color: {self.theme.bg_card_hover};
                color: {self.theme.text_primary};
            }}
            QPushButton[active="true"] {{
                background-color: {self.theme.bg_card_elevated};
                color: {self.theme.primary};
                border-left: 3px solid {self.theme.primary};
            }}
        """)
        self.nav_layout.addWidget(btn)
        return btn

    def add_separator(self, label: str = ""):
        if label:
            lbl = QLabel(label)
            lbl.setStyleSheet(f"""
                padding: 16px 24px 8px 24px;
                color: {self.theme.text_muted};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                text-transform: uppercase;
            """)
            self.nav_layout.addWidget(lbl)
        else:
            line = QFrame()
            line.setFixedHeight(1)
            line.setStyleSheet(f"background-color: {self.theme.border}; margin: 8px 0;")
            self.nav_layout.addWidget(line)

    def _on_nav_click(self, section: str, clicked_btn):
        for i in range(self.nav_layout.count()):
            item = self.nav_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if isinstance(w, QFrame) or isinstance(w, QWidget):
                    w.setProperty("active", False)
                    w.style().unpolish(w)
                    w.style().polish(w)

        clicked_btn.setProperty("active", True)
        clicked_btn.style().unpolish(clicked_btn)
        clicked_btn.style().polish(clicked_btn)
        self.navigation_clicked.emit(section)

class ContentPanel(QScrollArea):
    """Clean Content Container"""

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.theme = get_theme()
        except:
            from UI.theme import get_theme
            self.theme = get_theme()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(f"background-color: {self.theme.bg_dark}; border: none;")

        self.content = QWidget()
        self.content.setStyleSheet("background: transparent;")
        self.setWidget(self.content)

        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(32, 32, 32, 32)
        self.content_layout.setSpacing(24)

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        self.content_layout.addLayout(layout)

    def add_stretch(self):
        self.content_layout.addStretch()

    def clear(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

class HeaderPanel(QWidget):
    """Simple Top Bar"""
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        try:
            self.theme = get_theme()
        except:
            from UI.theme import get_theme
            self.theme = get_theme()
        self.setFixedHeight(60)
        self.setStyleSheet(f"background-color: {self.theme.bg_header}; border-bottom: 1px solid {self.theme.border};")
        
        l = QHBoxLayout(self)
        l.setContentsMargins(24, 0, 24, 0)
        
        self.title_label = QLabel(title.upper())
        self.title_label.setStyleSheet(f"font-size: 14px; font-weight: 700; letter-spacing: 2px; color: {self.theme.text_secondary};")
        l.addWidget(self.title_label)
        l.addStretch()

    def set_title(self, title: str):
        self.title_label.setText(title.upper())

class StatusPanel(QWidget):
    """Bottom Status Bar"""
    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.theme = get_theme()
        except:
            from UI.theme import get_theme
            self.theme = get_theme()
        self.setFixedHeight(28)
        self.setStyleSheet(f"background-color: {self.theme.bg_darkest}; border-top: 1px solid {self.theme.border};")
        
        l = QHBoxLayout(self)
        l.setContentsMargins(16, 0, 16, 0)
        
        self.left = QLabel("READY")
        self.left.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 10px; font-family: 'Consolas';")
        l.addWidget(self.left)
        l.addStretch()
        
        self.right = QLabel("")
        self.right.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 10px; font-family: 'Consolas';")
        l.addWidget(self.right)

    def set_left_text(self, text):
        self.left.setText(text.upper())
    
    def set_right_text(self, text):
        self.right.setText(text)

    def show_message(self, message, timeout=0):
        """Show temporary message (timeout in ms not implemented fully here but kept for API compat)"""
        # For now, just set the text. In full implementation, usage of QTimer to clear would be ideal.
        # But simple text setting solves the crash.
        self.right.setText(message)
        # Optional: Clear after timeout if needed, but simple is fine for now.
        if timeout > 0:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(timeout, lambda: self.right.setText(""))

class PageContainer(QStackedWidget):

    page_changed = Signal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pages = {}

    def add_page(self, name, widget):
        idx = self.addWidget(widget)
        self._pages[name] = idx
        return idx

    def show_page(self, name):
        if name in self._pages:
            self.setCurrentIndex(self._pages[name])
            self.page_changed.emit(self._pages[name])

class SplitPanel(QSplitter):
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        try:
            self.theme = get_theme()
        except:
            from UI.theme import get_theme
            self.theme = get_theme()
        self.setStyleSheet(f"QSplitter::handle {{ background-color: {self.theme.border}; }} QSplitter::handle:hover {{ background-color: {self.theme.primary}; }}")

class FloatingPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.theme = get_theme()
        except:
            from UI.theme import get_theme
            self.theme = get_theme()
        self.setStyleSheet(f"background-color: {self.theme.bg_card}; border: 1px solid {self.theme.border};")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0,0,0,100))
        self.setGraphicsEffect(shadow)
        self.main_layout = QVBoxLayout(self)
        
    def add_widget(self, widget):
        self.main_layout.addWidget(widget)

class ToolbarPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.theme = get_theme()
        except:
            from UI.theme import get_theme
            self.theme = get_theme()
        self.setStyleSheet(f"background-color: {self.theme.bg_card}; border: 1px solid {self.theme.border};")
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 0, 8, 0)
    
    def add_widget(self, widget):
        self.layout.addWidget(widget)
        
    def add_separator(self):
        line = QFrame()
        line.setFixedWidth(1)
        line.setStyleSheet(f"background-color: {self.theme.border};")
        self.layout.addWidget(line)
        
    def add_stretch(self):
        self.layout.addStretch()

    def add_spacing(self, size):
        self.layout.addSpacing(size)

class GradientPanel(QWidget):
    def __init__(self, colors=None, parent=None):
        super().__init__(parent)
        self.colors = colors or ["#000000", "#111111"]

    def set_colors(self, colors):
        self.colors = colors
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        for i, c in enumerate(self.colors):
            gradient.setColorAt(i/(len(self.colors)-1), QColor(c))
        painter.fillRect(self.rect(), gradient)

class Card(QFrame):
    """Simple Card with Title"""
    def __init__(self, title: str = "", parent=None, bordered: bool = True):
        super().__init__(parent)
        try:
            self.theme = get_theme()
        except:
            from UI.theme import get_theme
            self.theme = get_theme()
            
        self._title = title
        self._bordered = bordered
        self._setup_ui()

    def _setup_ui(self):
        border_str = f"1px solid {self.theme.border}" if self._bordered else "none"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: {border_str};
                border-radius: 4px;
            }}
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(8)

        if self._title:
            t = QLabel(self._title)
            t.setStyleSheet(f"""
                font-size: 11px; font-weight: 700; color: {self.theme.text_secondary};
                letter-spacing: 1px; border-bottom: 1px solid {self.theme.border};
                padding-bottom: 4px; margin-bottom: 4px;
            """)
            self.layout.addWidget(t)